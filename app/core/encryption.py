"""
Encryption Utility for Private Key Storage
Menggunakan Fernet (symmetric encryption) untuk encrypt private key
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from app.config import ENCRYPTION_KEY
from app.logger import logger


def get_fernet_key(key: bytes) -> Fernet:
    """
    Generate Fernet key dari raw key bytes
    """
    # Fernet requires 32-byte key, encode to base64
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'wireguard_vpn_salt',  # Fixed salt untuk consistency
        iterations=100000,
    )
    key_material = kdf.derive(key)
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)


def encrypt_private_key(private_key: str) -> str:
    """
    Encrypt WireGuard private key untuk storage
    Returns encrypted string (base64)
    """
    try:
        fernet = get_fernet_key(ENCRYPTION_KEY)
        encrypted = fernet.encrypt(private_key.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Error encrypting private key: {e}")
        raise


def decrypt_private_key(encrypted_key: str) -> str:
    """
    Decrypt WireGuard private key dari storage
    Returns decrypted private key string
    """
    try:
        fernet = get_fernet_key(ENCRYPTION_KEY)
        decrypted = fernet.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Error decrypting private key: {e}")
        raise
