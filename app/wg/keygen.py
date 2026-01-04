#import subprocess
#
#def generate_private_key():
#    result = subprocess.run(["wg", "genkey"], capture_output=True, text=True)
#    return result.stdout.strip()
#
#def generate_public_key(private_key):
#    result = subprocess.run(["wg", "pubkey"], input=private_key, capture_output=True, text=True)
#    return result.stdout.strip()
import secrets
import base64

def mock_key():
    # generate 32 bytes random → base64 → mirip key WireGuard
    return base64.b64encode(secrets.token_bytes(32)).decode()

def generate_private_key():
    return mock_key()

def generate_public_key(private_key):
    # untuk mock, public key = hash dari private key
    return mock_key()