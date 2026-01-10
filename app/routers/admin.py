"""
Admin User List Endpoint
List all users dengan info dari LDAP dan MySQL
"""

from fastapi import APIRouter, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt_admin
from app.core.ldap_client import get_user_attributes, check_wireguard_enabled, get_max_devices
from app.database.queries import get_user_devices
from app.logger import logger

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def list_users(request: Request):
    """
    List all users dengan info dari LDAP dan MySQL
    """
    verify_jwt_admin(request)
    
    # TODO: Query semua users dari LDAP
    # Untuk sekarang, kita bisa query dari MySQL devices untuk get list users yang punya device
    # Atau bisa query langsung dari LDAP jika ada endpoint untuk list all users
    
    # Get unique users dari MySQL devices
    from app.database.queries import get_all_devices
    
    all_devices = get_all_devices(status=None, limit=10000)  # Get all untuk unique users
    unique_users = {}
    
    for device in all_devices:
        username = device['ldap_uid']
        if username not in unique_users:
            # Get user info dari LDAP
            user_attrs = get_user_attributes(username, ['uid', 'cn', 'mail'])
            
            # Get device count
            user_devices = get_user_devices(username, include_revoked=False)
            
            unique_users[username] = {
                "username": username,
                "cn": user_attrs.get('cn') if user_attrs else None,
                "mail": user_attrs.get('mail') if user_attrs else None,
                "wireguard_enabled": check_wireguard_enabled(username),
                "max_devices": get_max_devices(username),
                "device_count": len(user_devices),
                "has_devices": len(user_devices) > 0
            }
    
    users_list = list(unique_users.values())
    
    logger.info(f"Admin listed {len(users_list)} users")
    
    return {
        "status": "ok",
        "users": users_list,
        "count": len(users_list),
        "note": "Users listed from devices database. Users without devices may not appear."
    }