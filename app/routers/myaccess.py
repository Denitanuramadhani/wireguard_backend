import json
from fastapi import APIRouter, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt

router = APIRouter(prefix="/myaccess", tags=["My Access"])

@router.get("/{username}", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def my_access(request: Request):
    username = verify_jwt(request)

    try:
        with open("allocated_ips.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    if username not in data:
        return {"status": "error", "devices": []}

    return {
        "status": "ok",
        "username": username,
        "ip": data[username]
    }
