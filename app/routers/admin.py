import json
from fastapi import APIRouter, Request
from app.middleware.auth_middleware import verify_jwt_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users")
def list_users(request: Request):

    verify_jwt_admin(request)

    try:
        with open("allocated_ips.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    users = [
        {"username": username, "ip": ip}
        for username, ip in data.items()
    ]

    return {"status": "ok", "users": users}