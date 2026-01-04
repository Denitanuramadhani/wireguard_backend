from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis

app = FastAPI(title="WireGuard VPN Portal Backend")

# === CORS ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# === RATE LIMIT INIT ===
@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(
        "redis://127.0.0.1:6379",
        encoding="utf-8",
        decode_responses=True
    )
    await FastAPILimiter.init(redis)

@app.get("/")
def home():
    return {"message": "Backend is running"}

# === ROUTERS ===
from app.routers import auth, wg, qr, myaccess, downloads, users, delete_user, peers, admin, admin_add_user

app.include_router(auth.router)
app.include_router(wg.router)
app.include_router(qr.router)
app.include_router(myaccess.router)
app.include_router(downloads.router)
app.include_router(users.router)
app.include_router(delete_user.router)
app.include_router(peers.router)
app.include_router(admin.router)
app.include_router(admin_add_user.router)
