from fastapi import Request, HTTPException
from fastapi.security.utils import get_authorization_scheme_param
import jwt
import time
from app.config import JWT_SECRET, JWT_ALGO


# ====================================================
# --------- VERIFY ACCESS TOKEN (BEARER JWT) ---------
# ====================================================
def verify_jwt(request: Request):
    auth = request.headers.get("Authorization")

    if not auth:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    scheme, token = get_authorization_scheme_param(auth)

    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token scheme")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload["sub"]  # return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# ====================================================
# ---------------- REFRESH TOKEN SYSTEM --------------
# ====================================================

def create_refresh_token(username: str):
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400  # refresh token berlaku 1 hari
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ====================================================
# ------------------- ADMIN ACCESS -------------------
# ====================================================

ADMIN_LIST = ["denita"]   # nanti bisa diganti LDAP group atau DB


def verify_jwt_admin(request: Request):
    username = verify_jwt(request)

    if username not in ADMIN_LIST:
        raise HTTPException(status_code=403, detail="Not allowed")

    return username