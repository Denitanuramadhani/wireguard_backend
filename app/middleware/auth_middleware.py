from fastapi import Request, HTTPException
from fastapi.security.utils import get_authorization_scheme_param
import jwt
import time
from app.config import JWT_SECRET, JWT_ALGO
from app.core.ldap_client import is_admin
from app.logger import logger


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
# Check admin dari LDAP group (cn=admins,ou=groups,dc=example,dc=com)
# ====================================================

def verify_jwt_admin(request: Request):
    """
    Verify JWT dan check jika user adalah admin
    Admin ditentukan dari LDAP group membership
    """
    username = verify_jwt(request)

    try:
        if not is_admin(username):
            logger.warning(f"Admin access denied for user {username}")
            raise HTTPException(status_code=403, detail="Not allowed: Admin access required")
        
        logger.debug(f"Admin access granted for user {username}")
        return username
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking admin status for {username}: {e}")
        raise HTTPException(status_code=403, detail="Not allowed: Error checking admin status")