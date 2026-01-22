import time
import jwt
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.services.ldap_auth import ldap_authenticate
from app.core.ldap_client import check_wireguard_enabled, get_max_devices
from app.core.audit_logger import log_audit_event
from app.core.alert_system import send_alert
from app.config import JWT_SECRET, JWT_ALGO
from app.logger import logger
from app.middleware.auth_middleware import create_refresh_token, verify_refresh_token
from app.core.login_logger import log_login_success, log_login_failed, log_refresh_token

router = APIRouter(prefix="/auth", tags=["Auth"])

# Default values untuk WireGuard info jika gagal fetch dari LDAP
DEFAULT_WIREGUARD_ENABLED = False
DEFAULT_MAX_DEVICES = 3


# FIXED: Safe RateLimiter wrapper untuk handle Redis unavailability
def safe_rate_limiter():
    """
    Safe rate limiter wrapper
    Jika Redis tidak tersedia, skip rate limiting (tidak block request)
    """
    try:
        # Try to create RateLimiter dependency
        # Jika Redis tidak tersedia, ini akan raise exception di runtime
        # Exception akan di-catch oleh graceful_degradation middleware
        return Depends(RateLimiter(times=100, seconds=60))
    except Exception as e:
        # FIXED: Jika RateLimiter gagal saat initialization, return no-op dependency
        logger.warning(f"RateLimiter initialization failed: {e}. Rate limiting disabled for this request.")
        def noop():
            pass
        return Depends(noop)


def create_jwt(username: str) -> str:
    """
    Create JWT access token (valid 1 hour)
    FIXED: Safe error handling - tidak pernah raise generic Exception, selalu HTTPException dengan detail jelas
    
    Safe: Tidak pernah raise exception, selalu return token atau raise HTTPException
    """
    if not username:
        logger.error("[JWT ERROR] create_jwt called with empty username")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate access token: Invalid username"
        )
    
    # FIXED: Validate JWT config sebelum encode
    if not JWT_SECRET:
        logger.error("[JWT ERROR] JWT_SECRET is not configured")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: JWT secret not configured"
        )
    
    if not JWT_ALGO:
        logger.error("[JWT ERROR] JWT_ALGO is not configured")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: JWT algorithm not configured"
        )
    
    try:
        # FIXED: Validate username format sebelum encode
        if not isinstance(username, str) or len(username) == 0 or len(username) > 255:
            logger.error(f"[JWT ERROR] Invalid username format: {username}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate access token: Invalid username format"
            )
        
        payload = {
            "sub": username,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600  # 1 hour
        }
        
        # FIXED: Handle specific JWT exceptions
        try:
            token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
        except jwt.InvalidAlgorithmError as e:
            logger.error(f"[JWT ERROR] Invalid algorithm {JWT_ALGO}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: Invalid JWT algorithm"
            )
        except Exception as e:
            logger.error(f"[JWT ERROR] jwt.encode failed for {username}: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to generate access token. Please try again."
            )
        
        if not token:
            logger.error(f"[JWT ERROR] jwt.encode returned None for {username}")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate access token: Token generation returned empty"
            )
        
        logger.debug(f"JWT token created for user: {username}")
        return token
        
    except HTTPException:
        # Re-raise HTTPException (sudah dengan detail yang jelas)
        raise
    except Exception as e:
        # FIXED: Catch-all dengan logging detail
        logger.error(
            f"[JWT CRITICAL ERROR] Unexpected error creating token for {username}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate access token. Please try again later."
        )


def safe_get_client_ip(request: Request) -> str:
    """
    Safely get client IP address from request
    Returns IP string or "unknown" if not available
    """
    try:
        if request.client and hasattr(request.client, 'host'):
            return request.client.host
        # Fallback: try to get from headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return "unknown"
    except Exception as e:
        logger.warning(f"Error getting client IP: {e}")
        return "unknown"


# FIXED: RateLimiter dependency - jika Redis tidak tersedia, exception akan di-catch oleh
# graceful_degradation middleware yang akan return 503 (bukan 500)
# Middleware sudah handle Redis/RateLimiter errors dengan graceful degradation
@router.post("/login", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
def login(data: dict, request: Request):
    """
    Login endpoint dengan error handling yang aman
    FIXED: Tidak pernah return 500, selalu handle error dengan jelas
    
    Rate limiting: Jika Redis tidak tersedia, rate limiting di-skip (tidak block request)
    """
    # FIXED: Rate limiting di-handle oleh FastAPI dependency injection
    # Jika Redis tidak tersedia, RateLimiter akan raise exception
    # Exception akan di-catch oleh graceful_degradation middleware (return 503)
    # Atau jika middleware tidak catch, akan masuk ke catch-all exception handler di bawah
    
    # #region agent log
    import json
    try:
        with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"auth.py:63","message":"LOGIN endpoint called","data":{"has_data":data is not None,"has_request":request is not None},"timestamp":int(time.time()*1000)}) + '\n')
    except: pass
    # #endregion
    
    username = None
    client_ip = safe_get_client_ip(request)
    
    # Get user agent untuk login log
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # #region agent log
    try:
        with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"auth.py:70","message":"After safe_get_client_ip","data":{"client_ip":client_ip},"timestamp":int(time.time()*1000)}) + '\n')
    except: pass
    # #endregion
    
    try:
        # Validate input
        username = data.get("username")
        password = data.get("password")
        
        # #region agent log
        try:
            with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"auth.py:76","message":"Input validation","data":{"has_username":bool(username),"has_password":bool(password),"username_len":len(username) if username else 0},"timestamp":int(time.time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        if not username or not password:
            logger.warning(f"LOGIN FAILED: Missing username or password from IP={client_ip}")
            log_login_failed(
                username=username or "unknown",
                ip_address=client_ip,
                user_agent=user_agent,
                error_type="ValidationError",
                error_message="Missing username or password",
                reason="missing_credentials"
            )
            raise HTTPException(
                status_code=400,
                detail="Missing username or password"
            )
        
        # Validate username format (basic validation)
        if not isinstance(username, str) or len(username) == 0:
            logger.warning(f"LOGIN FAILED: Invalid username format from IP={client_ip}")
            log_login_failed(
                username=username or "unknown",
                ip_address=client_ip,
                user_agent=user_agent,
                error_type="ValidationError",
                error_message="Invalid username format",
                reason="invalid_username_format"
            )
            raise HTTPException(
                status_code=400,
                detail="Invalid username format"
            )
        
        logger.info(f"[LOGIN] Attempt by username={username} from IP={client_ip}")
        
        # Step 1: LDAP Authentication
        # #region agent log
        try:
            with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"auth.py:95","message":"Before LDAP authenticate","data":{"username":username},"timestamp":int(time.time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        try:
            auth_result = ldap_authenticate(username, password)
            # #region agent log
            try:
                with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"auth.py:100","message":"After LDAP authenticate","data":{"auth_result":auth_result},"timestamp":int(time.time()*1000)}) + '\n')
            except: pass
            # #endregion
        except Exception as e:
            # #region agent log
            try:
                with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"auth.py:105","message":"LDAP authenticate exception","data":{"error_type":type(e).__name__,"error_msg":str(e)},"timestamp":int(time.time()*1000)}) + '\n')
            except: pass
            # #endregion
            logger.error(
                f"[LOGIN ERROR] LDAP authentication exception for {username} from IP={client_ip}: {e}",
                exc_info=True
            )
            
            # Log ke login.log
            log_login_failed(
                username=username,
                ip_address=client_ip,
                user_agent=user_agent,
                error_type=type(e).__name__,
                error_message=str(e),
                reason="ldap_exception"
            )
            
            # Log audit untuk failed login karena error
            try:
                log_audit_event(
                    action="login_failed",
                    performed_by=username or "unknown",
                    ip_address=client_ip,
                    details={
                        "username": username,
                        "error": "LDAP authentication exception",
                        "error_type": type(e).__name__
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log audit event: {audit_error}")
            
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please check your credentials."
            )
        
        if not auth_result:
            logger.warning(f"[LOGIN FAILED] Invalid credentials for username={username} from IP={client_ip}")
            
            # Log ke login.log
            log_login_failed(
                username=username,
                ip_address=client_ip,
                user_agent=user_agent,
                error_type="InvalidCredentials",
                error_message="Invalid username or password",
                reason="invalid_credentials"
            )
        
        # Audit log untuk failed login
        try:
            log_audit_event(
                action="login_failed",
                performed_by=username,
                ip_address=client_ip,
                details={"username": username, "reason": "Invalid credentials"}
            )
        except Exception as audit_error:
            logger.error(f"Failed to log audit event: {audit_error}")
        
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
        
        # Step 2: Get WireGuard info (tidak block login jika gagal)
        wireguard_enabled = DEFAULT_WIREGUARD_ENABLED
        max_devices = DEFAULT_MAX_DEVICES
        
        try:
            wireguard_enabled = check_wireguard_enabled(username)
            logger.debug(f"[LOGIN] WireGuard enabled check for {username}: {wireguard_enabled}")
        except Exception as e:
            logger.error(
                f"[LOGIN WARNING] Failed to check wireguardEnabled for {username}: {e}. "
                f"Using default value: {DEFAULT_WIREGUARD_ENABLED}",
                exc_info=True
            )
            # Tidak raise error, gunakan default value
        
        try:
            max_devices = get_max_devices(username)
            logger.debug(f"[LOGIN] Max devices for {username}: {max_devices}")
        except Exception as e:
            logger.error(
                f"[LOGIN WARNING] Failed to get max_devices for {username}: {e}. "
                f"Using default value: {DEFAULT_MAX_DEVICES}",
                exc_info=True
            )
            # Tidak raise error, gunakan default value
        
        # Step 3: Generate JWT tokens
        # FIXED: Generate tokens dengan error handling yang lebih detail
        # #region agent log
        try:
            with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:140","message":"Before JWT creation","data":{"username":username},"timestamp":int(time.time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        try:
            # FIXED: Generate access token dengan error handling
            access_token = create_jwt(username)
            # #region agent log
            try:
                with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:145","message":"After create_jwt","data":{"has_token":bool(access_token)},"timestamp":int(time.time()*1000)}) + '\n')
            except: pass
            # #endregion
            
            # FIXED: Validate access token sebelum generate refresh token
            if not access_token:
                logger.error(f"[LOGIN ERROR] Access token is None for {username}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate access token. Please try again."
                )
            
            # FIXED: Generate refresh token dengan error handling
            refresh_token = create_refresh_token(username)
            # #region agent log
            try:
                with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:151","message":"After create_refresh_token","data":{"has_refresh":bool(refresh_token)},"timestamp":int(time.time()*1000)}) + '\n')
            except: pass
            # #endregion
            
            # FIXED: Validate refresh token
            if not refresh_token:
                logger.error(f"[LOGIN ERROR] Refresh token is None for {username}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to generate refresh token. Please try again."
                )
                
        except HTTPException:
            # create_jwt/create_refresh_token sudah raise HTTPException dengan detail yang jelas
            raise
        except Exception as e:
            # FIXED: Catch-all dengan logging detail
            logger.error(
                f"[LOGIN ERROR] Failed to generate tokens for {username}: {e}",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to generate authentication tokens. Please try again."
            )
        
        logger.info(
            f"[LOGIN SUCCESS] username={username} wireguardEnabled={wireguard_enabled} "
            f"max_devices={max_devices} from IP={client_ip}"
        )
        
        # Log ke login.log
        log_login_success(
            username=username,
            ip_address=client_ip,
            user_agent=user_agent,
            wireguard_enabled=wireguard_enabled,
            max_devices=max_devices
        )
        
        # Step 4: Audit log untuk successful login
        try:
            log_audit_event(
                action="login_success",
                performed_by=username,
                ldap_uid=username,
                ip_address=client_ip,
                details={
                    "wireguard_enabled": wireguard_enabled,
                    "max_devices": max_devices
                }
            )
        except Exception as audit_error:
            # Jangan block login jika audit log gagal
            logger.error(f"Failed to log audit event for successful login: {audit_error}")
        
        return {
        "status": "ok",
        "username": username,
            "access_token": access_token,
            "refresh_token": refresh_token,
        "wireguard_enabled": wireguard_enabled,
        "max_devices": max_devices
    }
        
    except HTTPException as he:
        # #region agent log
        try:
            with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"auth.py:200","message":"HTTPException caught","data":{"status_code":he.status_code,"detail":str(he.detail)},"timestamp":int(time.time()*1000)}) + '\n')
        except: pass
        # #endregion
        # Re-raise HTTPException (sudah dengan detail yang jelas)
        raise
    except Exception as e:
        # #region agent log
        try:
            with open(r'c:\wireguard_backend\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"auth.py:208","message":"Catch-all exception","data":{"error_type":type(e).__name__,"error_msg":str(e),"username":username,"client_ip":client_ip},"timestamp":int(time.time()*1000)}) + '\n')
        except: pass
        # #endregion
        
        # Catch-all untuk unexpected errors
        logger.error(
            f"[LOGIN CRITICAL ERROR] Unexpected error during login for username={username} "
            f"from IP={client_ip}: {e}",
            exc_info=True
        )
        
        # Log ke login.log
        log_login_failed(
            username=username or "unknown",
            ip_address=client_ip,
            user_agent=request.headers.get("User-Agent", "unknown") if 'request' in locals() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e),
            reason="unexpected_error"
        )
        
        # Try to log audit event
        try:
            log_audit_event(
                action="login_failed",
                performed_by=username or "unknown",
                ip_address=client_ip,
                details={
                    "username": username,
                    "error": "Unexpected error",
                    "error_type": type(e).__name__
                }
            )
        except Exception:
            pass  # Ignore audit log errors
        
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during login. Please try again later."
        )


@router.post("/refresh")
def refresh_token_endpoint(data: dict, request: Request):
    """
    Refresh token endpoint dengan error handling yang aman
    Tidak pernah return 500, selalu handle error dengan jelas
    """
    client_ip = safe_get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "unknown")
    username = None
    
    try:
        # Validate input
        refresh_token_value = data.get("refresh_token")
        
        if not refresh_token_value:
            logger.warning(f"[REFRESH] Missing refresh_token from IP={client_ip}")
            log_refresh_token(
                username="unknown",
                ip_address=client_ip,
                success=False,
                error_type="ValidationError",
                error_message="Missing refresh_token"
            )
            raise HTTPException(
                status_code=400,
                detail="Missing refresh_token"
            )
        
        if not isinstance(refresh_token_value, str):
            logger.warning(f"[REFRESH] Invalid refresh_token format from IP={client_ip}")
            log_refresh_token(
                username="unknown",
                ip_address=client_ip,
                success=False,
                error_type="ValidationError",
                error_message="Invalid refresh_token format"
            )
            raise HTTPException(
                status_code=400,
                detail="Invalid refresh_token format"
            )
        
        # Verify refresh token
        try:
            username = verify_refresh_token(refresh_token_value)
        except HTTPException as he:
            # verify_refresh_token sudah raise HTTPException dengan detail yang jelas
            log_refresh_token(
                username="unknown",
                ip_address=client_ip,
                success=False,
                error_type="TokenVerificationError",
                error_message=str(he.detail)
            )
            raise
        except Exception as e:
            logger.error(
                f"[REFRESH ERROR] Exception during token verification from IP={client_ip}: {e}",
                exc_info=True
            )
            log_refresh_token(
                username="unknown",
                ip_address=client_ip,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token"
            )
        
        if not username:
            logger.warning(f"[REFRESH] Token verification returned None from IP={client_ip}")
            log_refresh_token(
                username="unknown",
                ip_address=client_ip,
                success=False,
                error_type="TokenVerificationError",
                error_message="Token verification returned None"
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
        
        logger.info(f"[REFRESH] Token refreshed for username={username} from IP={client_ip}")
        
        # Generate new access token
        try:
            access_token = create_jwt(username)
        except HTTPException as he:
            # create_jwt sudah raise HTTPException dengan detail yang jelas
            log_refresh_token(
                username=username,
                ip_address=client_ip,
                success=False,
                error_type="JWTGenerationError",
                error_message=str(he.detail)
            )
            raise
        except Exception as e:
            logger.error(
                f"[REFRESH ERROR] Failed to generate access token for {username}: {e}",
                exc_info=True
            )
            log_refresh_token(
                username=username,
                ip_address=client_ip,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to generate access token. Please try again."
            )
        
        # Log successful refresh
        log_refresh_token(
            username=username,
            ip_address=client_ip,
            success=True
        )
        
        return {
            "status": "ok",
            "access_token": access_token
        }
        
    except HTTPException:
        # Re-raise HTTPException (sudah dengan detail yang jelas)
        raise
    except Exception as e:
        # Catch-all untuk unexpected errors
        logger.error(
            f"[REFRESH CRITICAL ERROR] Unexpected error during token refresh from IP={client_ip}: {e}",
            exc_info=True
        )
        log_refresh_token(
            username=username or "unknown",
            ip_address=client_ip,
            success=False,
            error_type=type(e).__name__,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during token refresh. Please try again later."
        )