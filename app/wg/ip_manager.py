"""
IP Manager - MySQL-based IP allocation
Legacy JSON-based functions removed, now using MySQL
"""

from app.database.queries import allocate_ip as mysql_allocate_ip
from app.config import VPN_NETWORK_PREFIX, VPN_START_IP, VPN_END_IP

# Legacy compatibility - redirect to MySQL function
def allocate_ip(username: str) -> str:
    """
    Allocate IP address untuk device
    Now using MySQL instead of JSON file
    Each device gets its own IP (not per user)
    """
    return mysql_allocate_ip(username)

# Keep constants for reference
NETWORK_PREFIX = VPN_NETWORK_PREFIX
START_IP = VPN_START_IP
END_IP = VPN_END_IP