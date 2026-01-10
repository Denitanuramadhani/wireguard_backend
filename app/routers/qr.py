"""
QR Code Endpoints
Legacy endpoint - QR code sekarang di-generate saat create device
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from app.middleware.auth_middleware import verify_jwt
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/qr", tags=["QR"])


@router.get("/", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def generate_qr(request: Request):
    """
    Legacy endpoint - Deprecated
    QR code sekarang di-generate saat create device di /devices/add
    Private key tidak disimpan, jadi QR tidak bisa di-regenerate
    """
    username = verify_jwt(request)
    
    raise HTTPException(
        status_code=410,  # Gone
        detail="This endpoint is deprecated. QR code is generated when creating a device at /devices/add. Private key is not stored for security, so QR cannot be regenerated. If you need a new QR code, revoke the device and create a new one."
    )