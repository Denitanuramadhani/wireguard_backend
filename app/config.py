import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ======================
# LDAP CONFIG
# ======================
LDAP_SERVER = os.getenv("LDAP_SERVER", "ldap://117.53.44.59:389")
LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "dc=example,dc=com")
LDAP_USER_DN = os.getenv("LDAP_USER_DN", "uid={},ou=people,dc=example,dc=com")
LDAP_ADMIN_DN = os.getenv("LDAP_ADMIN_DN", "cn=admin,dc=example,dc=com")
LDAP_ADMIN_PASSWORD = os.getenv("LDAP_ADMIN_PASSWORD", "")

# ======================
# MYSQL CONFIG
# MySQL server berada di VPS terpisah (117.53.45.105)
# Hanya menyimpan: device, key, IP, status VPN
# User identity & role tetap di LDAP (117.53.44.59)
# ======================
# MYSQL_HOST = os.getenv("MYSQL_HOST", "117.53.45.105")  # Remote MySQL server
MYSQL_HOST = os.getenv("MYSQL_HOST", "43.129.55.182")  # Remote MySQL server
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "wgadmin")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "wireguard_vpn")
MYSQL_POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", "10"))
MYSQL_MAX_OVERFLOW = int(os.getenv("MYSQL_MAX_OVERFLOW", "20"))
MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10"))  # Timeout untuk remote connection

# MySQL Connection String
MYSQL_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"

# ======================
# WIREGUARD CONFIG
# ======================
WG_INTERFACE = os.getenv("WG_INTERFACE", "wg0")
WG_CONF_PATH = os.getenv("WG_CONF_PATH", "/etc/wireguard/wg0.conf")
WG_SERVER_PUBLIC_KEY = os.getenv("WG_SERVER_PUBLIC_KEY", "w+JEv1CDgtrOduepTLLW90rekFgHwvKoJTBsPEBOXDo=")
WG_ENDPOINT = os.getenv("WG_ENDPOINT", "117.53.44.59:51820")

# ======================
# JWT CONFIG
# ======================
JWT_SECRET = os.getenv("JWT_SECRET", "6fa6969e55e9b8d5fce4e1117fe1f95ee42e47f50dd6d5dc781a9423e70b3e7f")
JWT_ALGO = os.getenv("JWT_ALGO", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "1"))

# ======================
# REDIS CONFIG (untuk rate limiting)
# ======================
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# ======================
# APPLICATION CONFIG
# ======================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ======================
# SECURITY CONFIG
# ======================
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
MAX_DEVICES_PER_USER = int(os.getenv("MAX_DEVICES_PER_USER", "3"))
QR_CODE_EXPIRATION_MINUTES = int(os.getenv("QR_CODE_EXPIRATION_MINUTES", "30"))

# IP Pool Configuration
VPN_NETWORK_PREFIX = "10.8.0."
VPN_START_IP = 2
VPN_END_IP = 250

# ======================
# ENCRYPTION CONFIG (for private key encryption)
# ======================
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")  # 32-byte key untuk Fernet encryption
# Jika tidak ada ENCRYPTION_KEY, gunakan JWT_SECRET sebagai fallback (kurang aman tapi OK untuk development)
if not ENCRYPTION_KEY:
    import hashlib
    ENCRYPTION_KEY = hashlib.sha256(JWT_SECRET.encode()).digest()[:32]

# ======================
# DEVICE EXPIRATION CONFIG
# ======================
DEVICE_EXPIRATION_DAYS = int(os.getenv("DEVICE_EXPIRATION_DAYS", "90"))  # Auto-revoke setelah 90 hari tidak digunakan

# ======================
# SECURITY OVERRIDES (USE WITH CAUTION!)
# ======================
# Allow /admin/add-user without authentication (NOT RECOMMENDED for production!)
# Set to "true" to disable auth requirement for add-user endpoint
ALLOW_NO_AUTH_ADD_USER = os.getenv("ALLOW_NO_AUTH_ADD_USER", "false").lower() == "true"