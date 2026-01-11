"""
My Access Endpoint
List devices untuk logged-in user
"""

from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt
from app.database.queries import get_user_devices
from app.core.ldap_client import check_wireguard_enabled, get_max_devices

router = APIRouter(prefix="/myaccess", tags=["My Access"])


@router.get("/", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def my_access(request: Request):
    """
    Get user's devices and access info
    """
    username = verify_jwt(request)
    
    # Get devices dari MySQL
    devices = get_user_devices(username, include_revoked=False)
    
    # Format devices
    device_list = []
    for device in devices:
        device_list.append({
            "device_id": device['id'],
            "device_name": device['device_name'],
            "vpn_ip": device['vpn_ip'],
            "status": device['status'],
            "created_at": device['created_at'].isoformat() if isinstance(device['created_at'], datetime) else str(device['created_at']),
            "last_seen": device['last_seen'].isoformat() if device['last_seen'] and isinstance(device['last_seen'], datetime) else (str(device['last_seen']) if device['last_seen'] else None)
        })
    
    return {
        "status": "ok",
        "username": username,
        "wireguard_enabled": check_wireguard_enabled(username),
        "max_devices": get_max_devices(username),
        "device_count": len(device_list),
        "devices": device_list
    }
