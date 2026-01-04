from fastapi import APIRouter
import subprocess

router = APIRouter(prefix="/wg", tags=["WireGuard"])

@router.get("/peers")
def list_peers():
    try:
        result = subprocess.check_output(["sudo", "wg", "show", "wg0", "dump"])
        lines = result.decode().strip().split("\n")

        peers = []

        for row in lines[1:]:  # skip header
            cols = row.split("\t")
            if len(cols) < 4:
                continue

            peers.append({
                "public_key": cols[0],
                "preshared_key": cols[1],
                "endpoint": cols[2],
                "allowed_ips": cols[3],
                "latest_handshake": cols[4],
                "transfer_rx": cols[5],
                "transfer_tx": cols[6],
            })

        return {"status": "ok", "peers": peers}

    except Exception as e:
        return {"status": "error", "msg": str(e)}