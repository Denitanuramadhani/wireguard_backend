"""
Admin Device Management Endpoints
Admin dapat manage semua devices
"""

from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt_admin
from app.database.queries import (
    get_all_devices,
    get_device_by_id,
    revoke_device,
    get_device_by_public_key
)
from app.wg.utils import remove_peer_from_wg
from app.core.audit_logger import log_audit_event
from app.core.alert_system import send_alert
from app.logger import logger

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/devices", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def list_all_devices(
    request: Request,
    status: str = Query(None, description="Filter by status: active, revoked, expired"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    List all devices (admin only)
    """
    verify_jwt_admin(request)
    
    devices = get_all_devices(status=status, limit=limit, offset=offset)
    
    device_list = []
    for device in devices:
        device_list.append({
            "device_id": device['id'],
            "ldap_uid": device['ldap_uid'],
            "device_name": device['device_name'],
            "vpn_ip": device['vpn_ip'],
            "public_key": device['public_key'],
            "status": device['status'],
            "created_at": device['created_at'].isoformat() if isinstance(device['created_at'], datetime) else str(device['created_at']),
            "last_seen": device['last_seen'].isoformat() if device['last_seen'] and isinstance(device['last_seen'], datetime) else (str(device['last_seen']) if device['last_seen'] else None),
            "transfer_rx": device.get('transfer_rx', 0),
            "transfer_tx": device.get('transfer_tx', 0),
            "transfer_total": device.get('transfer_total', 0)
        })
    
    return {
        "status": "ok",
        "devices": device_list,
        "count": len(device_list),
        "limit": limit,
        "offset": offset
    }


@router.get("/devices/{device_id}")
def get_device_details(device_id: int, request: Request):
    """
    Get device details (admin only)
    """
    verify_jwt_admin(request)
    
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {
        "status": "ok",
        "device": {
            "device_id": device['id'],
            "ldap_uid": device['ldap_uid'],
            "device_name": device['device_name'],
            "vpn_ip": device['vpn_ip'],
            "public_key": device['public_key'],
            "status": device['status'],
            "created_at": device['created_at'].isoformat() if isinstance(device['created_at'], datetime) else str(device['created_at']),
            "last_seen": device['last_seen'].isoformat() if device['last_seen'] and isinstance(device['last_seen'], datetime) else (str(device['last_seen']) if device['last_seen'] else None),
            "transfer_rx": device.get('transfer_rx', 0),
            "transfer_tx": device.get('transfer_tx', 0),
            "transfer_total": device.get('transfer_total', 0),
            "revoked_at": device.get('revoked_at'),
            "revoked_by": device.get('revoked_by'),
            "revoke_reason": device.get('revoke_reason')
        }
    }


@router.delete("/devices/{device_id}")
def admin_revoke_device(device_id: int, request: Request):
    """
    Admin revoke device
    """
    admin_username = verify_jwt_admin(request)
    
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device['status'] != 'active':
        raise HTTPException(status_code=400, detail=f"Device is already {device['status']}")
    
    public_key = device['public_key']
    
    try:
        # Remove peer dari WireGuard
        remove_peer_from_wg(public_key)
        
        # Revoke di MySQL
        success = revoke_device(device_id, admin_username, "Revoked by admin")
        
        if success:
            logger.info(f"Device {device_id} revoked by admin {admin_username}")
            
            # Audit log
            log_audit_event(
                action="device_revoked_by_admin",
                performed_by=admin_username,
                ldap_uid=device.get('ldap_uid'),
                device_id=device_id,
                ip_address=request.client.host if request.client else None,
                details={
                    "device_name": device.get('device_name'),
                    "username": device.get('ldap_uid')
                }
            )
            
            # Send alert
            send_alert(
                alert_type="device_revoked_by_admin",
                severity="medium",
                message=f"Device '{device.get('device_name')}' revoked by admin {admin_username}",
                details={
                    "device_id": device_id,
                    "username": device.get('ldap_uid'),
                    "admin": admin_username
                }
            )
            
            return {
                "status": "ok",
                "message": "Device revoked successfully",
                "device_id": device_id,
                "revoked_by": admin_username
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to revoke device")
    except Exception as e:
        logger.error(f"Error revoking device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/user/{username}")
def get_user_devices_admin(username: str, request: Request):
    """
    Get all devices for a specific user (admin only)
    """
    verify_jwt_admin(request)
    
    from app.database.queries import get_user_devices
    
    devices = get_user_devices(username, include_revoked=True)
    
    device_list = []
    for device in devices:
        device_list.append({
            "device_id": device['id'],
            "device_name": device['device_name'],
            "vpn_ip": device['vpn_ip'],
            "public_key": device['public_key'],
            "status": device['status'],
            "created_at": device['created_at'].isoformat() if isinstance(device['created_at'], datetime) else str(device['created_at']),
            "last_seen": device['last_seen'].isoformat() if device['last_seen'] and isinstance(device['last_seen'], datetime) else (str(device['last_seen']) if device['last_seen'] else None)
        })
    
    return {
        "status": "ok",
        "username": username,
        "devices": device_list,
        "count": len(device_list)
    }
