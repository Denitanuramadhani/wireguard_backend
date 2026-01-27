"""
WireGuard Peers Endpoint
List active peers dengan info dari MySQL
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt
from app.database.queries import get_device_by_public_key
from app.logger import logger
import subprocess

router = APIRouter(prefix="/peers", tags=["Peers"])


@router.get("/", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def list_peers(request: Request):
    """
    List active WireGuard peers dengan info dari MySQL
    User bisa lihat peers mereka sendiri
    """
    username = verify_jwt(request)
    try:
        result = subprocess.check_output(
            ["sudo", "wg", "show", "wg0", "dump"],
            stderr=subprocess.STDOUT
        )
        lines = result.decode().strip().split("\n")

        peers = []

        for line in lines:
            if not line.strip():
                continue
            
            cols = line.split("\t")
            if len(cols) < 4:
                continue

            public_key = cols[0]
            preshared_key = cols[1] if cols[1] != "(none)" else None
            endpoint = cols[2] if cols[2] != "(none)" else None
            allowed_ips = cols[3]
            latest_handshake = cols[4] if len(cols) > 4 and cols[4] != "0" else None
            transfer_rx = int(cols[5]) if len(cols) > 5 else 0
            transfer_tx = int(cols[6]) if len(cols) > 6 else 0
            
            # Parse latest handshake
            handshake_time = None
            if latest_handshake and latest_handshake != "0":
                try:
                    seconds_ago = int(latest_handshake)
                    handshake_time = datetime.now() - timedelta(seconds=seconds_ago)
                except:
                    pass
            
            # Get device info dari MySQL
            device = get_device_by_public_key(public_key)
            
            # Filter: User hanya bisa lihat peers device mereka sendiri
            if device and device.get('ldap_uid') != username:
                continue  # Skip peers yang bukan milik user
            
            peer_info = {
                "public_key": public_key,
                "preshared_key": preshared_key,
                "endpoint": endpoint,
                "allowed_ips": allowed_ips,
                "latest_handshake": handshake_time.isoformat() if handshake_time else None,
                "transfer_rx": transfer_rx,
                "transfer_tx": transfer_tx,
                "transfer_total": transfer_rx + transfer_tx
            }
            
            # Add device info jika ada
            if device:
                peer_info["device_id"] = device['id']
                peer_info["ldap_uid"] = device['ldap_uid']
                peer_info["device_name"] = device['device_name']
                peer_info["vpn_ip"] = device['vpn_ip']
                peer_info["status"] = device['status']
            
            peers.append(peer_info)

        return {
            "status": "ok",
            "peers": peers,
            "count": len(peers),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error listing peers: {e}")
        return {"status": "error", "msg": str(e)}