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
def verify_jwt(request: Request) -> str:
    """
    Verify JWT access token
    FIXED: Safe error handling - semua exception di-handle dengan HTTPException yang jelas
    
    Returns username if valid
    Raises HTTPException dengan detail yang jelas jika invalid/expired
    """
    # FIXED: Validate request object
    if not request:
        logger.warning("[AUTH MIDDLEWARE] verify_jwt called with None request")
        raise HTTPException(status_code=401, detail="Invalid request")
    
    # FIXED: Safe access to headers
    try:
        auth = request.headers.get("Authorization")
    except Exception as e:
        logger.warning(f"[AUTH MIDDLEWARE] Error accessing request headers: {e}")
        raise HTTPException(status_code=401, detail="Invalid request headers")

    if not auth:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # FIXED: Safe token extraction
    try:
        scheme, token = get_authorization_scheme_param(auth)
    except Exception as e:
        logger.warning(f"[AUTH MIDDLEWARE] Error parsing Authorization header: {e}")
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token scheme. Use 'Bearer' token.")

    if not token:
        raise HTTPException(status_code=401, detail="Token is required")

    # FIXED: Validate JWT config sebelum decode
    if not JWT_SECRET:
        logger.error("[AUTH MIDDLEWARE ERROR] JWT_SECRET is not configured")
        raise HTTPException(status_code=500, detail="Server configuration error: JWT secret not configured")
    
    if not JWT_ALGO:
        logger.error("[AUTH MIDDLEWARE ERROR] JWT_ALGO is not configured")
        raise HTTPException(status_code=500, detail="Server configuration error: JWT algorithm not configured")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        
        # FIXED: Validate payload structure
        if not isinstance(payload, dict):
            logger.warning("[AUTH MIDDLEWARE] JWT payload is not a dictionary")
            raise HTTPException(status_code=401, detail="Invalid token structure")
        
        username = payload.get("sub")
        if not username:
            logger.warning("[AUTH MIDDLEWARE] JWT payload missing 'sub' field")
            raise HTTPException(status_code=401, detail="Invalid token: missing username")
        
        if not isinstance(username, str) or len(username) == 0:
            logger.warning(f"[AUTH MIDDLEWARE] Invalid username in token: {username}")
            raise HTTPException(status_code=401, detail="Invalid token: invalid username")
        
        return username
        
    except jwt.ExpiredSignatureError:
        logger.debug("[AUTH MIDDLEWARE] Token expired")
        raise HTTPException(status_code=401, detail="Token has expired. Please login again.")
    except jwt.InvalidTokenError as e:
        logger.warning(f"[AUTH MIDDLEWARE] Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.DecodeError as e:
        logger.warning(f"[AUTH MIDDLEWARE] Failed to decode token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token format")
    except Exception as e:
        # FIXED: Catch-all dengan logging detail
        logger.error(
            f"[AUTH MIDDLEWARE ERROR] Unexpected error verifying token: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=401, detail="Failed to verify token")


# ====================================================
# ---------------- REFRESH TOKEN SYSTEM --------------
# ====================================================

def create_refresh_token(username: str) -> str:
    """
    Create refresh token (valid 1 day)
    FIXED: Safe error handling - tidak pernah raise generic Exception, selalu return token atau raise HTTPException
    
    Safe: Tidak pernah raise exception, selalu return token atau raise HTTPException
    """
    if not username:
        logger.error("[AUTH MIDDLEWARE ERROR] create_refresh_token called with empty username")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate refresh token: Invalid username"
        )
    
    # FIXED: Validate JWT config sebelum encode
    if not JWT_SECRET:
        logger.error("[AUTH MIDDLEWARE ERROR] JWT_SECRET is not configured")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: JWT secret not configured"
        )
    
    if not JWT_ALGO:
        logger.error("[AUTH MIDDLEWARE ERROR] JWT_ALGO is not configured")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: JWT algorithm not configured"
        )
    
    try:
        # FIXED: Validate username format sebelum encode
        if not isinstance(username, str) or len(username) == 0 or len(username) > 255:
            logger.error(f"[AUTH MIDDLEWARE ERROR] Invalid username format: {username}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate refresh token: Invalid username format"
            )
        
        payload = {
            "sub": username,
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400  # refresh token berlaku 1 hari
        }
        
        # FIXED: Handle specific JWT exceptions
        try:
            token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
        except jwt.InvalidAlgorithmError as e:
            logger.error(f"[AUTH MIDDLEWARE ERROR] Invalid algorithm {JWT_ALGO}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: Invalid JWT algorithm"
            )
        except Exception as e:
            logger.error(f"[AUTH MIDDLEWARE ERROR] jwt.encode failed for refresh token: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to generate refresh token. Please try again."
            )
        
        if not token:
            logger.error(f"[AUTH MIDDLEWARE ERROR] jwt.encode returned None for refresh token")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate refresh token: Token generation returned empty"
            )
        
        logger.debug(f"Refresh token created for user: {username}")
        return token
        
    except HTTPException:
        # Re-raise HTTPException (sudah dengan detail yang jelas)
        raise
    except Exception as e:
        # FIXED: Catch-all dengan logging detail
        logger.error(
            f"[AUTH MIDDLEWARE CRITICAL ERROR] Unexpected error creating refresh token for {username}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate refresh token. Please try again later."
        )


def verify_refresh_token(token: str) -> str:
    """
    Verify refresh token
    Returns username if valid
    Raises HTTPException dengan detail yang jelas jika invalid/expired
    
    Safe: Tidak pernah return None atau raise generic Exception
    """
    if not token:
        logger.warning("[AUTH MIDDLEWARE] verify_refresh_token called with empty token")
        raise HTTPException(status_code=401, detail="Refresh token is required")
    
    if not isinstance(token, str):
        logger.warning(f"[AUTH MIDDLEWARE] verify_refresh_token called with invalid token type: {type(token)}")
        raise HTTPException(status_code=401, detail="Invalid refresh token format")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        
        # Validate payload structure
        if not isinstance(payload, dict):
            logger.warning("[AUTH MIDDLEWARE] JWT payload is not a dictionary")
            raise HTTPException(status_code=401, detail="Invalid refresh token structure")
        
        username = payload.get("sub")
        if not username:
            logger.warning("[AUTH MIDDLEWARE] JWT payload missing 'sub' field")
            raise HTTPException(status_code=401, detail="Invalid refresh token: missing username")
        
        if not isinstance(username, str) or len(username) == 0:
            logger.warning(f"[AUTH MIDDLEWARE] Invalid username in token: {username}")
            raise HTTPException(status_code=401, detail="Invalid refresh token: invalid username")
        
        logger.debug(f"[AUTH MIDDLEWARE] Refresh token verified for user: {username}")
        return username
        
    except jwt.ExpiredSignatureError:
        logger.debug("[AUTH MIDDLEWARE] Refresh token expired")
        raise HTTPException(status_code=401, detail="Refresh token has expired. Please login again.")
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"[AUTH MIDDLEWARE] Invalid refresh token: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    except jwt.DecodeError as e:
        logger.warning(f"[AUTH MIDDLEWARE] Failed to decode refresh token: {e}")
        raise HTTPException(status_code=401, detail="Invalid refresh token format")
        
    except Exception as e:
        logger.error(
            f"[AUTH MIDDLEWARE ERROR] Unexpected error verifying refresh token: {e}",
            exc_info=True
        )
        raise HTTPException(status_code=401, detail="Failed to verify refresh token")


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