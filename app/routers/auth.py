import time
import jwt
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.services.ldap_auth import ldap_authenticate
from app.config import JWT_SECRET, JWT_ALGO
from app.logger import logger
from app.middleware.auth_middleware import create_refresh_token, verify_refresh_token

router = APIRouter(prefix="/auth", tags=["Auth"])


def create_jwt(username: str):
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


@router.post("/login", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
def login(data: dict, request: Request):

    username = data.get("username")
    password = data.get("password")

    logger.info(f"LOGIN attempt by username={username} from IP={request.client.host}")

    if not ldap_authenticate(username, password):
        logger.warning(f"LOGIN FAILED for username={username}")
        raise HTTPException(status_code=401, detail="Invalid LDAP credentials")

    access = create_jwt(username)
    refresh = create_refresh_token(username)

    logger.info(f"LOGIN SUCCESS username={username}")

    return {
        "status": "ok",
        "username": username,
        "access_token": access,
        "refresh_token": refresh
    }


@router.post("/refresh")
def refresh_token(data: dict):
    token = data.get("refresh_token")

    username = verify_refresh_token(token)

    logger.info(f"REFRESH TOKEN used by username={username}")

    return {
        "status": "ok",
        "access_token": create_jwt(username)
    }