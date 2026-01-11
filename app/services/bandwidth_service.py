"""
Bandwidth Limit Enforcement Service
Handle bandwidth limits per device/user dan enforcement
"""

from datetime import datetime, timedelta
from app.database.queries import get_device_by_id
from app.database.connection import get_db_connection
from app.logger import logger


def check_bandwidth_limit(device_id: int) -> tuple[bool, dict]:
    """
    Check if device has exceeded bandwidth limit
    Returns (is_exceeded, limit_info)
    """
    device = get_device_by_id(device_id)
    if not device:
        return False, {"error": "Device not found"}
    
    bandwidth_limit = device.get('bandwidth_limit')
    bandwidth_used = device.get('bandwidth_used', 0)
    
    # Jika tidak ada limit, unlimited
    if bandwidth_limit is None:
        return False, {
            "limited": False,
            "limit": None,
            "used": bandwidth_used,
            "remaining": None,
            "percentage": 0
        }
    
    # Check if exceeded
    is_exceeded = bandwidth_used >= bandwidth_limit
    remaining = max(0, bandwidth_limit - bandwidth_used)
    percentage = (bandwidth_used / bandwidth_limit * 100) if bandwidth_limit > 0 else 0
    
    return is_exceeded, {
        "limited": True,
        "limit": bandwidth_limit,
        "used": bandwidth_used,
        "remaining": remaining,
        "percentage": round(percentage, 2),
        "exceeded": is_exceeded
    }


def update_bandwidth_usage(device_id: int, bytes_used: int) -> bool:
    """
    Update bandwidth usage untuk device
    Returns True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Get current usage
            cursor.execute(
                "SELECT bandwidth_used FROM vpn_devices WHERE id = %s",
                (device_id,)
            )
            result = cursor.fetchone()
            if not result:
                return False
            
            current_used = result['bandwidth_used'] or 0
            new_used = current_used + bytes_used
            
            # Update usage
            cursor.execute(
                "UPDATE vpn_devices SET bandwidth_used = %s WHERE id = %s",
                (new_used, device_id)
            )
            conn.commit()
            
            # Check if exceeded limit
            cursor.execute(
                "SELECT bandwidth_limit FROM vpn_devices WHERE id = %s",
                (device_id,)
            )
            device = cursor.fetchone()
            if device and device['bandwidth_limit']:
                if new_used >= device['bandwidth_limit']:
                    logger.warning(f"Device {device_id} exceeded bandwidth limit: {new_used}/{device['bandwidth_limit']}")
            
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating bandwidth usage: {e}")
            return False


def reset_bandwidth_usage(device_id: int = None, ldap_uid: str = None) -> bool:
    """
    Reset bandwidth usage untuk device atau user
    Biasanya dipanggil setiap bulan
    Returns True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            if device_id:
                cursor.execute(
                    "UPDATE vpn_devices SET bandwidth_used = 0 WHERE id = %s",
                    (device_id,)
                )
            elif ldap_uid:
                cursor.execute(
                    "UPDATE vpn_devices SET bandwidth_used = 0 WHERE ldap_uid = %s",
                    (ldap_uid,)
                )
            else:
                # Reset all devices
                cursor.execute("UPDATE vpn_devices SET bandwidth_used = 0")
            
            conn.commit()
            logger.info(f"Bandwidth usage reset: device_id={device_id}, ldap_uid={ldap_uid}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error resetting bandwidth usage: {e}")
            return False


def set_bandwidth_limit(device_id: int = None, ldap_uid: str = None, limit_bytes: int = None) -> bool:
    """
    Set bandwidth limit untuk device atau user
    limit_bytes: bytes per month, None = unlimited
    Returns True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            if device_id:
                cursor.execute(
                    "UPDATE vpn_devices SET bandwidth_limit = %s WHERE id = %s",
                    (limit_bytes, device_id)
                )
            elif ldap_uid:
                cursor.execute(
                    "UPDATE vpn_devices SET bandwidth_limit = %s WHERE ldap_uid = %s",
                    (limit_bytes, ldap_uid)
                )
            else:
                return False
            
            conn.commit()
            logger.info(f"Bandwidth limit set: device_id={device_id}, ldap_uid={ldap_uid}, limit={limit_bytes}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error setting bandwidth limit: {e}")
            return False
