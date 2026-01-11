"""
Device Expiration Service
Auto-revoke devices yang tidak digunakan dalam periode tertentu
"""

from datetime import datetime, timedelta
from app.database.connection import get_db_connection
from app.database.queries import get_device_by_id, revoke_device
from app.wg.utils import remove_peer_from_wg
from app.core.audit_logger import log_audit_event
from app.core.alert_system import send_alert
from app.config import DEVICE_EXPIRATION_DAYS
from app.logger import logger


def check_and_revoke_expired_devices() -> dict:
    """
    Check dan revoke devices yang tidak digunakan lebih dari DEVICE_EXPIRATION_DAYS
    Returns dict dengan statistics
    """
    stats = {
        "checked": 0,
        "revoked": 0,
        "errors": 0,
        "timestamp": datetime.now().isoformat()
    }
    
    expiration_threshold = datetime.now() - timedelta(days=DEVICE_EXPIRATION_DAYS)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Find active devices yang last_seen lebih lama dari threshold
            cursor.execute(
                """
                SELECT id, ldap_uid, device_name, public_key, last_seen
                FROM vpn_devices
                WHERE status = 'active'
                  AND (last_seen IS NULL OR last_seen < %s)
                """,
                (expiration_threshold,)
            )
            
            expired_devices = cursor.fetchall()
            stats["checked"] = len(expired_devices)
            
            for device in expired_devices:
                device_id = device['id']
                ldap_uid = device['ldap_uid']
                device_name = device['device_name']
                public_key = device['public_key']
                last_seen = device['last_seen']
                
                try:
                    # Remove peer dari WireGuard
                    remove_peer_from_wg(public_key)
                    
                    # Revoke device di MySQL
                    revoke_reason = f"Auto-revoked: Device tidak digunakan lebih dari {DEVICE_EXPIRATION_DAYS} hari. Last seen: {last_seen or 'Never'}"
                    success = revoke_device(device_id, "system", revoke_reason)
                    
                    if success:
                        stats["revoked"] += 1
                        logger.info(
                            f"Auto-revoked expired device: ID={device_id}, "
                            f"User={ldap_uid}, Device={device_name}, "
                            f"Last seen: {last_seen}"
                        )
                        
                        # Audit log
                        log_audit_event(
                            action="device_expired",
                            performed_by="system",
                            ldap_uid=ldap_uid,
                            device_id=device_id,
                            details={
                                "device_name": device_name,
                                "last_seen": str(last_seen) if last_seen else None,
                                "expiration_days": DEVICE_EXPIRATION_DAYS
                            }
                        )
                        
                        # Send alert
                        send_alert(
                            alert_type="device_expired",
                            severity="low",
                            message=f"Device '{device_name}' auto-revoked due to inactivity (>{DEVICE_EXPIRATION_DAYS} days)",
                            details={
                                "device_id": device_id,
                                "username": ldap_uid,
                                "device_name": device_name,
                                "last_seen": str(last_seen) if last_seen else "Never"
                            }
                        )
                    else:
                        stats["errors"] += 1
                        logger.error(f"Failed to revoke expired device {device_id}")
                        
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Error revoking expired device {device_id}: {e}")
            
            logger.info(f"Device expiration check completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error checking expired devices: {e}")
            stats["errors"] += 1
            return stats
