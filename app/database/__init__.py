"""
Database module for WireGuard VPN Portal
Handles MySQL connection and database operations
"""

from app.database.connection import get_db_connection, close_db_connection
from app.database.queries import (
    allocate_ip,
    create_device,
    get_user_devices,
    get_device_by_id,
    revoke_device,
    update_device_traffic,
    get_all_devices,
    check_ip_available
)

__all__ = [
    "get_db_connection",
    "close_db_connection",
    "allocate_ip",
    "create_device",
    "get_user_devices",
    "get_device_by_id",
    "revoke_device",
    "update_device_traffic",
    "get_all_devices",
    "check_ip_available"
]
