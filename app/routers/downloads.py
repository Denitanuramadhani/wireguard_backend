from fastapi import APIRouter, Request, Depends
from fastapi.responses import FileResponse
from app.middleware.auth_middleware import verify_jwt
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/download", tags=["Download"])

@router.get("/conf/{username}", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def download_config(username: str, request: Request):
    token_user = verify_jwt(request)

    # pastikan user hanya bisa download miliknya sendiri
    if username != token_user:
        return {"status": "error", "message": "Unauthorized"}

    path = f"generated_configs/{username}.conf"
    return FileResponse(path, filename=f"{username}.conf")

