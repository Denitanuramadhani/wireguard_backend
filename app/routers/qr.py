from fastapi import APIRouter, Request, Depends
from app.middleware.auth_middleware import verify_jwt
from fastapi_limiter.depends import RateLimiter
import base64

router = APIRouter(prefix="/qr", tags=["QR"])

@router.get("/", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def generate_qr(request: Request):
    username = verify_jwt(request)

    path = f"generated_configs/{username}.png"

    try:
        with open(path, "rb") as f:
            qr_data = base64.b64encode(f.read()).decode()
    except:
        return {"status": "error", "message": "QR not found"}

    return {"status": "ok", "qr_base64": qr_data}