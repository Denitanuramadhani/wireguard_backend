from fastapi import APIRouter, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.wg.generator import generate_client_config, generate_qr_base64
from app.wg.ip_manager import allocate_ip
from app.middleware.auth_middleware import verify_jwt
from app.logger import logger

router = APIRouter(prefix="/wg", tags=["WireGuard"])


@router.post("/generate", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def generate(request: Request):

    username = verify_jwt(request)
    logger.info(f"WG GENERATE requested by {username} from IP={request.client.host}")

    client_ip = allocate_ip(username)

    # generate key + config (legacy function memang ada)
    result = generate_client_config(username, client_ip)

    # generate QR (base64)
    qr = generate_qr_base64(result["config"])

    logger.info(f"WG CONFIG GENERATED username={username} ip={client_ip}")

    return {
        "username": username,
        "ip": client_ip,
        "public_key": result["public_key"],
        "config": result["config"],
        "qr": qr
    }
