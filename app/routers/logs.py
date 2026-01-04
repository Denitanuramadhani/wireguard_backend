from fastapi import APIRouter
from app.core.ldap_client import ldap_login

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login")
def login(data: dict):
    username = data.get("username")
    password = data.get("password")

    if ldap_login(username, password):
        return {"status": "ok", "username": username}
    else:
        return {"status": "failed"}