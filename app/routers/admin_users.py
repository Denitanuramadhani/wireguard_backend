"""
Admin User Management Endpoints
Enable/disable VPN access untuk users
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt_admin
from app.core.ldap_client import (
    enable_wireguard_user,
    disable_wireguard_user,
    check_wireguard_enabled,
    get_max_devices,
    set_max_devices,
    get_user_attributes
)
from app.database.queries import get_user_devices, revoke_device
from app.wg.utils import remove_peer_from_wg
from app.core.audit_logger import log_audit_event
from app.core.alert_system import send_alert
from app.logger import logger

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/users/{username}/enable")
def enable_user_vpn(username: str, request: Request):
    """
    Enable VPN access untuk user
    """
    admin_username = verify_jwt_admin(request)
    
    # Check if user exists
    user_attrs = get_user_attributes(username, ['uid'])
    if not user_attrs:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    
    # Enable VPN access
    success = enable_wireguard_user(username)
    
    if success:
        logger.info(f"VPN access enabled for user {username} by admin {admin_username}")
        
        # Audit log
        log_audit_event(
            action="user_enabled",
            performed_by=admin_username,
            ldap_uid=username,
            ip_address=request.client.host if request.client else None,
            details={"username": username}
        )
        
        # Send alert
        send_alert(
            alert_type="user_enabled",
            severity="low",
            message=f"VPN access enabled for user {username} by admin {admin_username}",
            details={
                "username": username,
                "admin": admin_username
            }
        )
        
        return {
            "status": "ok",
            "message": f"VPN access enabled for user {username}",
            "username": username,
            "wireguard_enabled": True
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to enable VPN access")


@router.post("/users/{username}/disable")
def disable_user_vpn(username: str, request: Request):
    """
    Disable VPN access untuk user
    Akan revoke semua active devices user tersebut
    """
    admin_username = verify_jwt_admin(request)
    
    # Check if user exists
    user_attrs = get_user_attributes(username, ['uid'])
    if not user_attrs:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    
    # Get all active devices untuk user ini
    active_devices = get_user_devices(username, include_revoked=False)
    
    # Revoke semua active devices
    revoked_count = 0
    for device in active_devices:
        try:
            public_key = device['public_key']
            device_id = device['id']
            
            # Remove peer dari WireGuard
            remove_peer_from_wg(public_key)
            
            # Revoke di MySQL
            revoke_device(device_id, admin_username, "VPN access disabled by admin")
            revoked_count += 1
        except Exception as e:
            logger.error(f"Error revoking device {device['id']} for user {username}: {e}")
    
    # Disable VPN access di LDAP
    success = disable_wireguard_user(username)
    
    if success:
        logger.info(f"VPN access disabled for user {username} by admin {admin_username}. {revoked_count} devices revoked.")
        
        # Audit log
        log_audit_event(
            action="user_disabled",
            performed_by=admin_username,
            ldap_uid=username,
            ip_address=request.client.host if request.client else None,
            details={
                "username": username,
                "devices_revoked": revoked_count
            }
        )
        
        # Send alert
        send_alert(
            alert_type="user_disabled",
            severity="medium",
            message=f"VPN access disabled for user {username} by admin {admin_username}. {revoked_count} devices revoked.",
            details={
                "username": username,
                "admin": admin_username,
                "devices_revoked": revoked_count
            }
        )
        
        return {
            "status": "ok",
            "message": f"VPN access disabled for user {username}",
            "username": username,
            "wireguard_enabled": False,
            "devices_revoked": revoked_count
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to disable VPN access")


@router.get("/users/{username}/status")
def get_user_status(username: str, request: Request):
    """
    Get user VPN status dan device info
    """
    verify_jwt_admin(request)
    
    # Check if user exists
    user_attrs = get_user_attributes(username, ['uid', 'wireguardEnabled', 'maxWireguardDevices'])
    if not user_attrs:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    
    # Get devices
    devices = get_user_devices(username, include_revoked=True)
    active_devices = [d for d in devices if d['status'] == 'active']
    
    return {
        "status": "ok",
        "username": username,
        "wireguard_enabled": check_wireguard_enabled(username),
        "max_devices": get_max_devices(username),
        "device_count": {
            "active": len(active_devices),
            "total": len(devices)
        },
        "devices": [
            {
                "device_id": d['id'],
                "device_name": d['device_name'],
                "vpn_ip": d['vpn_ip'],
                "status": d['status']
            }
            for d in devices
        ]
    }


@router.post("/users/{username}/max-devices")
def set_user_max_devices(username: str, data: dict, request: Request):
    """
    Set maximum devices untuk user
    """
    verify_jwt_admin(request)
    
    max_devices = data.get("max_devices")
    if not max_devices:
        raise HTTPException(status_code=400, detail="max_devices is required")
    
    try:
        max_devices = int(max_devices)
        if max_devices < 1 or max_devices > 10:
            raise HTTPException(status_code=400, detail="max_devices must be between 1 and 10")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="max_devices must be a number")
    
    # Check if user exists
    user_attrs = get_user_attributes(username, ['uid'])
    if not user_attrs:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    
    # Set max devices
    success = set_max_devices(username, max_devices)
    
    if success:
        logger.info(f"Max devices set to {max_devices} for user {username}")
        
        # Audit log
        log_audit_event(
            action="max_devices_set",
            performed_by=admin_username,
            ldap_uid=username,
            ip_address=request.client.host if request.client else None,
            details={
                "username": username,
                "max_devices": max_devices
            }
        )
        
        return {
            "status": "ok",
            "message": f"Max devices set to {max_devices} for user {username}",
            "username": username,
            "max_devices": max_devices
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to set max devices")
