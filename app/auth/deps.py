from fastapi import Depends, HTTPException, Header
from app.auth.jwt_handler import verify_token

def auth_required(Authorization: str = Header(None)):
    if Authorization is None or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token missing")

    token = Authorization.split(" ")[1]
    username = verify_token(token)

    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return username