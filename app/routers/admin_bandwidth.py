"""
Admin Bandwidth Management Endpoints
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt_admin
from app.services.bandwidth_service import (
    check_bandwidth_limit,
    set_bandwidth_limit,
    reset_bandwidth_usage
)
from app.database.queries import get_device_by_id
from app.logger import logger

router = APIRouter(prefix="/admin/bandwidth", tags=["Admin - Bandwidth"])


@router.post("/device/{device_id}/limit")
def set_device_bandwidth_limit(device_id: int, data: dict, request: Request):
    """
    Set bandwidth limit untuk device (admin only)
    Body: {"limit_bytes": 107374182400}  # 100 GB dalam bytes, atau null untuk unlimited
    """
    verify_jwt_admin(request)
    
    limit_bytes = data.get("limit_bytes")
    if limit_bytes is not None and (not isinstance(limit_bytes, int) or limit_bytes < 0):
        raise HTTPException(status_code=400, detail="limit_bytes must be positive integer or null")
    
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    success = set_bandwidth_limit(device_id=device_id, limit_bytes=limit_bytes)
    
    if success:
        return {
            "status": "ok",
            "message": f"Bandwidth limit set to {limit_bytes} bytes" if limit_bytes else "Bandwidth limit removed (unlimited)",
            "device_id": device_id,
            "limit_bytes": limit_bytes
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to set bandwidth limit")


@router.post("/user/{username}/limit")
def set_user_bandwidth_limit(username: str, data: dict, request: Request):
    """
    Set bandwidth limit untuk semua device user (admin only)
    Body: {"limit_bytes": 107374182400}  # 100 GB dalam bytes, atau null untuk unlimited
    """
    verify_jwt_admin(request)
    
    limit_bytes = data.get("limit_bytes")
    if limit_bytes is not None and (not isinstance(limit_bytes, int) or limit_bytes < 0):
        raise HTTPException(status_code=400, detail="limit_bytes must be positive integer or null")
    
    success = set_bandwidth_limit(ldap_uid=username, limit_bytes=limit_bytes)
    
    if success:
        return {
            "status": "ok",
            "message": f"Bandwidth limit set to {limit_bytes} bytes for user {username}" if limit_bytes else f"Bandwidth limit removed (unlimited) for user {username}",
            "username": username,
            "limit_bytes": limit_bytes
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to set bandwidth limit")


@router.get("/device/{device_id}/status")
def get_device_bandwidth_status(device_id: int, request: Request):
    """
    Get bandwidth status untuk device (admin only)
    """
    verify_jwt_admin(request)
    
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    exceeded, limit_info = check_bandwidth_limit(device_id)
    
    return {
        "status": "ok",
        "device_id": device_id,
        "ldap_uid": device['ldap_uid'],
        "device_name": device['device_name'],
        **limit_info
    }


@router.post("/device/{device_id}/reset")
def reset_device_bandwidth(device_id: int, request: Request):
    """
    Reset bandwidth usage untuk device (admin only)
    """
    verify_jwt_admin(request)
    
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    success = reset_bandwidth_usage(device_id=device_id)
    
    if success:
        return {
            "status": "ok",
            "message": "Bandwidth usage reset successfully",
            "device_id": device_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to reset bandwidth usage")


@router.post("/user/{username}/reset")
def reset_user_bandwidth(username: str, request: Request):
    """
    Reset bandwidth usage untuk semua device user (admin only)
    """
    verify_jwt_admin(request)
    
    success = reset_bandwidth_usage(ldap_uid=username)
    
    if success:
        return {
            "status": "ok",
            "message": f"Bandwidth usage reset successfully for user {username}",
            "username": username
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to reset bandwidth usage")
