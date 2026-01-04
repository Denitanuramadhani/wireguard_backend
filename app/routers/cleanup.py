import os
import json
import subprocess
from fastapi import APIRouter, Request
from app.middleware.auth_middleware import verify_jwt

router = APIRouter(prefix="/cleanup", tags=["Cleanup"])

@router.delete("/")
def cleanup(request: Request):
    username = verify_jwt(request)

    conf_path = f"generated_configs/{username}.conf"
    qr_path = f"generated_configs/{username}.png"

    removed_conf = removed_qr = False

    # Remove config
    if os.path.exists(conf_path):
        os.remove(conf_path)
        removed_conf = True

    # Remove QR
    if os.path.exists(qr_path):
        os.remove(qr_path)
        removed_qr = True

    # Remove allocated IP
    try:
        with open("allocated_ips.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    client_ip = data.get(username)

    if client_ip:
        subprocess.run(["sudo", "wg", "set", "wg0", "peer", client_ip, "remove"], check=False)
        del data[username]

        with open("allocated_ips.json", "w") as f:
            json.dump(data, f, indent=2)

    return {
        "status": "success",
        "config_deleted": removed_conf,
        "qr_deleted": removed_qr,
        "peer_removed": True if client_ip else False
    }
