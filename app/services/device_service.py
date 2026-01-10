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
    get_device_by_public_key
)
from app.core.ldap_client import check_wireguard_enabled, get_max_devices
from app.wg.generator import generate_keypair, generate_client_config_text
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


def create_user_device(username: str, device_name: str) -> dict:
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
        
        # Allocate IP dari MySQL
        vpn_ip = allocate_ip(username)
        
        # Create device di MySQL (tanpa private key)
        device_id = create_device(
            ldap_uid=username,
            device_name=device_name,
            public_key=public_key,
            vpn_ip=vpn_ip
        )
        
        # Add peer ke WireGuard server
        add_peer_to_wg(public_key, f"{vpn_ip}/32")
        
        # Generate config text
        config_text = generate_client_config_text(
            private_key=private_key,
            public_key=public_key,
            client_ip=vpn_ip
        )
        
        logger.info(f"Device created: ID={device_id}, User={username}, Device={device_name}, IP={vpn_ip}")
        
        return {
            "device_id": device_id,
            "device_name": device_name,
            "public_key": public_key,
            "private_key": private_key,  # Hanya dikembalikan sekali
            "vpn_ip": vpn_ip,
            "config": config_text,
            "created_at": datetime.now().isoformat(),
            "warning": "Private key hanya ditampilkan sekali. Simpan dengan aman!"
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
        
        # Update status di MySQL
        success = revoke_device(device_id, username, revoke_reason)
        
        if success:
            logger.info(f"Device revoked: ID={device_id}, User={username}")
        
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
        "transfer_total": device.get('transfer_total', 0)
    }
