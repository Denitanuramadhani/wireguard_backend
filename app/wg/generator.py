"""
WireGuard Key Generation and Config Generation
"""

import subprocess
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta
from app.config import WG_SERVER_PUBLIC_KEY, WG_ENDPOINT, QR_CODE_EXPIRATION_MINUTES

# ========================
# GENERATE WIREGUARD KEYS
# ========================
def generate_keypair():
    """
    Generate WireGuard keypair
    Returns (private_key, public_key)
    """
    private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public_key = subprocess.check_output(["wg", "pubkey"], input=private_key.encode()).decode().strip()
    return private_key, public_key

# ========================
# BUILD CLIENT CONFIG TEXT
# ========================
def generate_client_config_text(private_key: str, public_key: str, client_ip: str) -> str:
    """
    Generate WireGuard client config text
    Returns config text string
    """
    config_text = f"""# ClientPublicKey = {public_key}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
    return config_text

# ========================
# GENERATE QR CODE (Base64)
# ========================
def generate_qr_base64(config_text: str) -> dict:
    """
    Generate QR code dari config text
    Returns dict dengan base64 encoded QR dan expiration info
    """
    img = qrcode.make(config_text)
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Calculate expiration
    expires_at = datetime.now() + timedelta(minutes=QR_CODE_EXPIRATION_MINUTES)
    
    return {
        "qr_base64": qr_base64,
        "expires_at": expires_at.isoformat(),
        "expires_in_minutes": QR_CODE_EXPIRATION_MINUTES
    }

# ========================
# LEGACY FUNCTIONS (for backward compatibility)
# ========================
def generate_client_config(username, client_ip):
    """
    Legacy function - untuk backward compatibility
    Deprecated: Use generate_client_config_text instead
    """
    private_key, public_key = generate_keypair()
    config_text = generate_client_config_text(private_key, public_key, client_ip)
    
    return {
        "username": username,
        "private_key": private_key,
        "public_key": public_key,
        "ip": client_ip,
        "config": config_text
    }
