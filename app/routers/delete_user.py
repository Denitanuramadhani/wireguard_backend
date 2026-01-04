from fastapi import APIRouter
import os
from app.wg.ip_manager import load_ips, save_ips
from app.config import WG_INTERFACE
import subprocess

router = APIRouter(prefix="/wg", tags=["WireGuard"])

def remove_peer_from_wg(public_key):
    subprocess.run([
        "sudo", "wg", "set", WG_INTERFACE,
        "peer", public_key,
        "remove"
    ], check=True)

@router.delete("/delete/{username}")
def delete_user(username: str):
    ips = load_ips()

    # cek apakah user ada
    if username not in ips:
        return {"status": "error", "msg": "User not found"}

    # ===========================================
    # 1. HAPUS PEER DARI WIREGUARD SERVER
    # ===========================================
    # ambil public key dari file user
    conf_path = f"generated_configs/{username}.conf"
    public_key = None

    if os.path.exists(conf_path):
        with open(conf_path, "r") as f:
            for line in f:
                if "PublicKey" in line:
                    public_key = line.split("=")[1].strip()

    if public_key:
        try:
            remove_peer_from_wg(public_key)
        except:
            pass

    # ===========================================
    # 2. HAPUS FILE CONFIG
    # ===========================================                 
    if os.path.exists(conf_path):
        os.remove(conf_path)

    # ===========================================
    # 3. HAPUS IP DARI ALLOCATED LIST
    # =========================================== 
    ip = ips.pop(username)
    save_ips(ips)

    # ===========================================
    # 4. HAPUS QR CODE (kalau ada)
    # ===========================================
    qr_path = f"generated_qr/{username}.png"
    if os.path.exists(qr_path):
        os.remove(qr_path)

    return {
        "status": "success",
        "user": username,
        "deleted_ip": ip,
        "config_deleted": True,
        "qr_deleted": os.path.exists(qr_path) == False
    }
