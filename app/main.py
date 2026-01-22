from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis
from app.config import CORS_ORIGINS
from app.logger import logger

app = FastAPI(
    title="WireGuard VPN Portal Backend",
    description="Backend API untuk WireGuard VPN Portal dengan LDAP Authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if "*" not in CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === RATE LIMIT INIT ===
from app.config import REDIS_URL, ENVIRONMENT

@app.on_event("startup")
async def startup():
    # Initialize Redis for rate limiting
    from app.core.optional_rate_limiter import set_redis_available
    
    try:
        redis = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        await FastAPILimiter.init(redis)
        set_redis_available(True)
        logger.info("Redis connection successful - Rate limiting enabled")
    except Exception as e:
        set_redis_available(False)
        if ENVIRONMENT == "development":
            logger.warning(f"Redis connection failed: {e}. Rate limiting disabled. This is OK for development.")
            logger.warning("To enable rate limiting, start Redis: redis-server")
        else:
            logger.error(f"Redis connection failed: {e}. Rate limiting disabled.")
            # In production, you might want to raise the error
            # raise
    
    # Test database connection
    from app.database.connection import test_connection
    if test_connection():
        logger.info("Database connection successful")
    else:
        logger.error("Database connection failed!")
    
    # Start background jobs
    from app.core.background_jobs import start_background_jobs
    start_background_jobs()
    logger.info("Background jobs started")

@app.on_event("shutdown")
async def shutdown():
    # Stop background jobs
    from app.core.background_jobs import stop_background_jobs
    stop_background_jobs()
    logger.info("Background jobs stopped")
    
    # Close LDAP connection pool
    from app.core.ldap_pool import close_ldap_pool
    close_ldap_pool()
    logger.info("LDAP connection pool closed")

@app.get("/")
def home():
    return {"message": "Backend is running"}

# === ROUTERS ===
from app.routers import (
    auth, wg, qr, myaccess, downloads, users, peers,
    admin, admin_add_user, admin_devices, admin_users, admin_monitoring,
    devices, analytics, health, admin_bandwidth, admin_user_management
)

# Authentication
from app.routers import auth
app.include_router(auth.router)

# User endpoints
from app.routers import devices, myaccess, downloads, users, peers, analytics
app.include_router(devices.router)  # Device management
app.include_router(analytics.router)  # Analytics & traffic monitoring
app.include_router(myaccess.router)
app.include_router(downloads.router)
app.include_router(users.router)
# app.include_router(delete_user.router)
app.include_router(peers.router)

# Admin endpoints
from app.routers import (
    admin, admin_add_user, admin_devices, admin_users, 
    admin_monitoring, admin_bandwidth, admin_user_management
)
app.include_router(admin.router)
app.include_router(admin_add_user.router)
app.include_router(admin_user_management.router)  # User CRUD operations
app.include_router(admin_devices.router)  # Admin device management
app.include_router(admin_users.router)  # Admin user management
app.include_router(admin_monitoring.router)  # Admin monitoring
app.include_router(admin_bandwidth.router)  # Admin bandwidth management

# Legacy endpoints (deprecated, kept for backward compatibility)
from app.routers import wg, qr
app.include_router(wg.router)  # Legacy: Keep for backward compatibility
app.include_router(qr.router)  # Legacy: Deprecated