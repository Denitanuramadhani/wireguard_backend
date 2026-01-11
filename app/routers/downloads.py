"""
Download Endpoints
Device-specific config download
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import Response
from app.middleware.auth_middleware import verify_jwt
from app.services.device_service import get_device_info
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/download", tags=["Download"])


@router.get("/conf/{device_id}", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def download_config(device_id: int, request: Request):
    """
    Download device config
    Note: Private key tidak tersedia karena tidak disimpan
    Config file hanya bisa dibuat saat device pertama kali dibuat
    """
    username = verify_jwt(request)
    
    try:
        device = get_device_info(device_id, username)
        
        if device['status'] != 'active':
            raise HTTPException(status_code=400, detail=f"Cannot download config for {device['status']} device")
        
        # Return info bahwa config tidak tersedia
        # User perlu revoke dan create device baru jika kehilangan private key
        raise HTTPException(
            status_code=404,
            detail="Config file tidak tersedia karena private key tidak disimpan untuk keamanan. Config hanya tersedia saat device pertama kali dibuat. Jika kehilangan config, revoke device ini dan buat device baru."
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/conf/{username}", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def download_config_legacy(username: str, request: Request):
    """
    Legacy endpoint - Deprecated
    Use /download/conf/{device_id} instead
    """
    token_user = verify_jwt(request)
    
    if username != token_user:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    raise HTTPException(
        status_code=410,  # Gone
        detail="This endpoint is deprecated. Use /download/conf/{device_id} instead. Config files are device-specific now."
    )

