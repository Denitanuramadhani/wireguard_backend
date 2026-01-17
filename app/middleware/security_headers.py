from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

EXCLUDE_PATHS = ["/docs", "/redoc", "/openapi.json"]

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ✅ BIAR SWAGGER NGGAK KEHALANG
        if request.url.path in EXCLUDE_PATHS:
            return await call_next(request)

        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # ⚠️ CSP terlalu ketat bikin Swagger blank
        # Jadi JANGAN dipasang ke /docs
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' http: https:; "
        )

        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response