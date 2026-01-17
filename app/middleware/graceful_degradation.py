"""
Graceful Degradation Middleware
Handles service failures dengan graceful degradation
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import logger


class GracefulDegradationMiddleware(BaseHTTPMiddleware):
    """
    Middleware untuk handle service failures dengan graceful degradation
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Check if it's a service dependency error
            error_str = str(e).lower()
            
            # LDAP errors
            if "ldap" in error_str or "connection" in error_str:
                logger.error(f"LDAP service error: {e}")
                # Return 503 Service Unavailable dengan maintenance message
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "service_unavailable",
                        "message": "LDAP service is temporarily unavailable. Please try again later.",
                        "error": "LDAP_CONNECTION_ERROR",
                        "retry_after": 60
                    }
                )
            
            # Database errors
            if "mysql" in error_str or "database" in error_str or "connection" in error_str:
                logger.error(f"Database service error: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "service_unavailable",
                        "message": "Database service is temporarily unavailable. Please try again later.",
                        "error": "DATABASE_CONNECTION_ERROR",
                        "retry_after": 60
                    }
                )
            
            # Redis/RateLimiter errors (non-critical, bisa bypass)
            if "redis" in error_str or "ratelimiter" in error_str or "rate limit" in error_str:
                logger.warning(f"Redis/RateLimiter error (non-critical): {e}")
                # Return 503 but with message that rate limiting is disabled
                # Request can still be processed if rate limiting is optional
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "service_unavailable",
                        "message": "Rate limiting service is temporarily unavailable. Please try again later.",
                        "error": "RATE_LIMIT_UNAVAILABLE",
                        "note": "This is non-critical. If rate limiting is optional, the request may still be processed."
                    }
                )
            
            # Re-raise untuk other errors
            raise
