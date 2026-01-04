import os
import subprocess
import qrcode
from app.config import WG_SERVER_PUBLIC_KEY, WG_ENDPOINT

BASE_DIR = "generated_configs"
os.makedirs(BASE_DIR, exist_ok=True)

# ========================
# GENERATE WIREGUARD KEYS
# ========================
def generate_keypair():
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key.encode()).decode().strip()
    return private_key, public_key

# ========================
# SAVE CONFIG FILE
# ========================
def save_config(username, config_text):
    path = f"{BASE_DIR}/{username}.conf"
    with open(path, "w") as f:
        f.write(config_text)

# ========================
# ADD PEER TO SERVER
# ========================
def add_peer_to_wg(public_key: str, allowed_ip: str):
    subprocess.run([
        "sudo", "wg", "set", "wg0",
        "peer", public_key,
        "allowed-ips", allowed_ip
    ], check=True)

# ========================
# BUILD CLIENT CONFIG
# ========================
def generate_client_config(username, client_ip):
    private_key, public_key = generate_keypair()

    config_text = f"""# ClientPublicKey = {public_key}

[Interface]
PrivateKey = {private_key}
Address = {client_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {WG_SERVER_PUBLIC_KEY}
Endpoint = {WG_ENDPOINT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

    return {
        "username": username,
        "private_key": private_key,
        "public_key": public_key,
        "ip": client_ip,
        "config": config_text
    }

# ========================
# GENERATE QR CODE
# ========================
def generate_qr(username, config_text):
    img = qrcode.make(config_text)
    path = f"{BASE_DIR}/{username}.png"
    img.save(path)
    return path
