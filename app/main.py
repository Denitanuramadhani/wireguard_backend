from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis
from app.config import CORS_ORIGINS
from app.logger import logger

app = FastAPI(title="WireGuard VPN Portal Backend")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if "*" not in CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === RATE LIMIT INIT ===
from app.config import REDIS_URL

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    await FastAPILimiter.init(redis)
    
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

@app.get("/")
def home():
    return {"message": "Backend is running"}

# === ROUTERS ===
from app.routers import (
    auth, wg, qr, myaccess, downloads, users, delete_user, peers,
    admin, admin_add_user, admin_devices, admin_users, admin_monitoring,
    devices, analytics
)

app.include_router(auth.router)
app.include_router(devices.router)  # Device management
app.include_router(analytics.router)  # Analytics & traffic monitoring
app.include_router(wg.router)  # Legacy: Keep for backward compatibility
app.include_router(qr.router)  # Legacy: Deprecated
app.include_router(myaccess.router)
app.include_router(downloads.router)
app.include_router(users.router)
app.include_router(delete_user.router)
app.include_router(peers.router)
app.include_router(admin.router)
app.include_router(admin_add_user.router)
app.include_router(admin_devices.router)  # Admin device management
app.include_router(admin_users.router)  # Admin user management
app.include_router(admin_monitoring.router)  # Admin monitoring