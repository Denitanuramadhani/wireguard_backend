"""
Device Service
Business logic untuk VPN device management
"""

from datetime import datetime, timedelta
from app.database.queries import (
    allocate_ip,
    create_device,
    get_user_devices,
    get_device_by_id,
    revoke_device,
    count_user_devices,
    get_device_by_public_key,
    save_qr_code,
    get_qr_code,
    clear_qr_code
)
from app.core.ldap_client import check_wireguard_enabled, get_max_devices
from app.core.encryption import encrypt_private_key, decrypt_private_key
from app.core.audit_logger import log_audit_event
from app.core.alert_system import send_alert
from app.wg.generator import generate_keypair, generate_client_config_text, generate_qr_base64
from app.wg.utils import add_peer_to_wg, remove_peer_from_wg
from app.config import QR_CODE_EXPIRATION_MINUTES, MAX_DEVICES_PER_USER
from app.logger import logger


def validate_device_name(device_name: str) -> bool:
    """
    Validate device name
    Rules: alphanumeric + dash/underscore, max 50 chars, not empty
    """
    if not device_name or len(device_name) == 0:
        return False
    
    if len(device_name) > 50:
        return False
    
    # Allow alphanumeric, dash, underscore
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', device_name):
        return False
    
    return True


def can_add_device(username: str) -> tuple[bool, str]:
    """
    Check if user can add device
    Returns (can_add, reason)
    """
    # Check wireguardEnabled
    if not check_wireguard_enabled(username):
        return False, "WireGuard access is disabled. Please contact administrator."
    
    # Check device count
    current_count = count_user_devices(username, active_only=True)
    max_allowed = get_max_devices(username)
    
    if current_count >= max_allowed:
        return False, f"Maximum device limit reached ({max_allowed} devices)"
    
    return True, "OK"


def create_user_device(username: str, device_name: str, user_agent: str = None, client_ip: str = None) -> dict:
    """
    Create a new VPN device untuk user
    Returns device info dengan config dan QR
    Note: Private key hanya dikembalikan sekali saat create, tidak disimpan di MySQL
    """
    # Validate device name
    if not validate_device_name(device_name):
        raise ValueError("Invalid device name. Use alphanumeric, dash, or underscore. Max 50 characters.")
    
    # Check if user can add device
    can_add, reason = can_add_device(username)
    if not can_add:
        raise PermissionError(reason)
    
    # Check if device name already exists for this user
    existing_devices = get_user_devices(username, include_revoked=False)
    for device in existing_devices:
        if device['device_name'].lower() == device_name.lower():
            raise ValueError(f"Device name '{device_name}' already exists")
    
    public_key = None
    try:
        # Generate WireGuard keypair
        private_key, public_key = generate_keypair()
        
        # Encrypt private key untuk storage
        private_key_encrypted = encrypt_private_key(private_key)
        
        # Allocate IP dari MySQL
        vpn_ip = allocate_ip(username)
        
        # Generate config text untuk QR code
        config_text = generate_client_config_text(
            private_key=private_key,
            public_key=public_key,
            client_ip=vpn_ip
        )
        
        # Generate QR code dengan expiration
        qr_data = generate_qr_base64(config_text)
        qr_code_base64 = qr_data['qr_base64']
        qr_expires_at = datetime.fromisoformat(qr_data['expires_at'])
        
        # Create device di MySQL dengan encrypted private key dan QR code
        device_id = create_device(
            ldap_uid=username,
            device_name=device_name,
            public_key=public_key,
            vpn_ip=vpn_ip,
            private_key_encrypted=private_key_encrypted,
            qr_code_base64=qr_code_base64,
            qr_code_expires_at=qr_expires_at,
            first_seen_ip=client_ip,
            user_agent=user_agent
        )
        
        # Add peer ke WireGuard server
        add_peer_to_wg(public_key, f"{vpn_ip}/32")
        
        logger.info(f"Device created: ID={device_id}, User={username}, Device={device_name}, IP={vpn_ip}")
        
        # Audit log
        log_audit_event(
            action="device_created",
            performed_by=username,
            ldap_uid=username,
            device_id=device_id,
            details={
                "device_name": device_name,
                "vpn_ip": vpn_ip,
                "public_key": public_key[:20] + "..."
            }
        )
        
        # Send alert untuk admin
        send_alert(
            alert_type="device_added",
            severity="low",
            message=f"New device '{device_name}' added by user {username}",
            details={
                "device_id": device_id,
                "username": username,
                "device_name": device_name,
                "vpn_ip": vpn_ip
            }
        )
        
        return {
            "device_id": device_id,
            "device_name": device_name,
            "public_key": public_key,
            "private_key": private_key,  # Hanya dikembalikan sekali
            "vpn_ip": vpn_ip,
            "config": config_text,
            "qr_code": qr_code_base64,
            "qr_expires_at": qr_data['expires_at'],
            "qr_expires_in_minutes": qr_data['expires_in_minutes'],
            "created_at": datetime.now().isoformat(),
            "warning": "Private key hanya ditampilkan sekali. QR code akan expire dalam 30 menit. Simpan dengan aman!"
        }
        
    except Exception as e:
        logger.error(f"Error creating device for {username}: {e}")
        # Rollback: remove peer jika sudah ditambahkan
        if public_key:
            try:
                remove_peer_from_wg(public_key)
            except:
                pass
        raise


def revoke_user_device(device_id: int, username: str, revoke_reason: str = None) -> bool:
    """
    Revoke a device (user can revoke their own device)
    Returns True jika berhasil
    """
    # Verify device ownership
    device = get_device_by_id(device_id, ldap_uid=username)
    if not device:
        raise ValueError("Device not found or access denied")
    
    if device['status'] != 'active':
        raise ValueError(f"Device is already {device['status']}")
    
    # Get public key
    public_key = device['public_key']
    
    try:
        # Remove peer dari WireGuard
        remove_peer_from_wg(public_key)
        
        # Clear QR code dari database
        clear_qr_code(device_id)
        
        # Update status di MySQL
        success = revoke_device(device_id, username, revoke_reason)
        
        if success:
            logger.info(f"Device revoked: ID={device_id}, User={username}")
            
            # Audit log
            log_audit_event(
                action="device_revoked",
                performed_by=username,
                ldap_uid=username,
                device_id=device_id,
                details={
                    "device_name": device.get('device_name'),
                    "revoke_reason": revoke_reason
                }
            )
            
            # Send alert
            send_alert(
                alert_type="device_revoked",
                severity="low",
                message=f"Device '{device.get('device_name')}' revoked by user {username}",
                details={
                    "device_id": device_id,
                    "username": username,
                    "revoke_reason": revoke_reason
                }
            )
        
        return success
        
    except Exception as e:
        logger.error(f"Error revoking device {device_id}: {e}")
        raise


def get_device_info(device_id: int, username: str) -> dict:
    """
    Get device info (tanpa private key)
    Returns device metadata
    """
    device = get_device_by_id(device_id, ldap_uid=username)
    if not device:
        raise ValueError("Device not found or access denied")
    
    # Check QR code status
    qr_data = get_qr_code(device_id)
    qr_available = qr_data is not None
    
    return {
        "device_id": device_id,
        "device_name": device['device_name'],
        "vpn_ip": device['vpn_ip'],
        "public_key": device['public_key'],
        "status": device['status'],
        "created_at": device['created_at'].isoformat() if isinstance(device['created_at'], datetime) else str(device['created_at']),
        "last_seen": device['last_seen'].isoformat() if device['last_seen'] and isinstance(device['last_seen'], datetime) else (str(device['last_seen']) if device['last_seen'] else None),
        "transfer_rx": device.get('transfer_rx', 0),
        "transfer_tx": device.get('transfer_tx', 0),
        "transfer_total": device.get('transfer_total', 0),
        "qr_available": qr_available,
        "qr_expires_at": qr_data['expires_at'] if qr_available else None
    }


def regenerate_qr_code(device_id: int, username: str) -> dict:
    """
    Regenerate QR code untuk device (jika expired atau tidak ada)
    Returns QR code data dengan expiration
    """
    # Verify device ownership
    device = get_device_by_id(device_id, ldap_uid=username)
    if not device:
        raise ValueError("Device not found or access denied")
    
    if device['status'] != 'active':
        raise ValueError(f"Cannot regenerate QR for {device['status']} device")
    
    # Check if private key encrypted exists
    if not device.get('private_key_encrypted'):
        raise ValueError("Private key not available. Cannot regenerate QR code.")
    
    try:
        # Decrypt private key
        private_key = decrypt_private_key(device['private_key_encrypted'])
        
        # Generate config text
        config_text = generate_client_config_text(
            private_key=private_key,
            public_key=device['public_key'],
            client_ip=device['vpn_ip']
        )
        
        # Generate new QR code dengan expiration
        qr_data = generate_qr_base64(config_text)
        qr_code_base64 = qr_data['qr_base64']
        qr_expires_at = datetime.fromisoformat(qr_data['expires_at'])
        
        # Save QR code ke database
        save_qr_code(device_id, qr_code_base64, qr_expires_at)
        
        logger.info(f"QR code regenerated for device ID={device_id}, User={username}")
        
        return {
            "device_id": device_id,
            "qr_code": qr_code_base64,
            "expires_at": qr_data['expires_at'],
            "expires_in_minutes": qr_data['expires_in_minutes']
        }
        
    except Exception as e:
        logger.error(f"Error regenerating QR code for device {device_id}: {e}")
        raise
