from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.logger import logger

EXCLUDE_PATHS = ["/docs", "/redoc", "/openapi.json"]

class GracefulDegradationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ✅ JANGAN INTERCEPT SWAGGER
        if request.url.path in EXCLUDE_PATHS:
            return await call_next(request)

        try:
            return await call_next(request)
        except Exception as e:
            error_str = str(e).lower()

            if "ldap" in error_str:
                logger.error(f"LDAP service error: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "service_unavailable",
                        "message": "LDAP service is temporarily unavailable",
                        "error": "LDAP_CONNECTION_ERROR"
                    }
                )

            if "mysql" in error_str or "database" in error_str:
                logger.error(f"Database service error: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "service_unavailable",
                        "message": "Database service is temporarily unavailable",
                        "error": "DATABASE_CONNECTION_ERROR"
                    }
                )
<<<<<<< HEAD

            # other error → biarin FastAPI handle
            raise
=======
            
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
>>>>>>> a26638eb4b8af0e3d06c3e2f99de8ce21e12449f
