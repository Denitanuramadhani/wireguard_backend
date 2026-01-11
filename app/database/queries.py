"""
Database Query Functions
All database operations for VPN devices
"""

from datetime import datetime, timedelta
from app.database.connection import get_db_connection
from app.config import VPN_NETWORK_PREFIX, VPN_START_IP, VPN_END_IP, MAX_DEVICES_PER_USER
from app.logger import logger


def allocate_ip(username: str) -> str:
    """
    Allocate an available IP address from the pool
    Returns IP address string (e.g., "10.8.0.5")
    Raises Exception if no IP available
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find available IP
        for i in range(VPN_START_IP, VPN_END_IP + 1):
            candidate_ip = f"{VPN_NETWORK_PREFIX}{i}"
            
            # Check if IP is already allocated
            cursor.execute(
                "SELECT id FROM vpn_devices WHERE vpn_ip = %s AND status = 'active'",
                (candidate_ip,)
            )
            if cursor.fetchone() is None:
                return candidate_ip
        
        raise Exception("No IP available in WireGuard pool")


def create_device(
    ldap_uid: str,
    device_name: str,
    public_key: str,
    vpn_ip: str,
    private_key_encrypted: str = None,
    qr_code_base64: str = None,
    qr_code_expires_at: datetime = None,
    first_seen_ip: str = None,
    user_agent: str = None
) -> int:
    """
    Create a new VPN device
    Returns device ID
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO vpn_devices 
                (ldap_uid, device_name, public_key, vpn_ip, private_key_encrypted, 
                 qr_code_base64, qr_code_expires_at, first_seen_ip, user_agent, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                """,
                (ldap_uid, device_name, public_key, vpn_ip, private_key_encrypted,
                 qr_code_base64, qr_code_expires_at, first_seen_ip, user_agent)
            )
            device_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Device created: ID={device_id}, User={ldap_uid}, Device={device_name}, IP={vpn_ip}")
            return device_id
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating device: {e}")
            raise


def get_user_devices(ldap_uid: str, include_revoked: bool = False) -> list:
    """
    Get all devices for a user
    Returns list of device dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if include_revoked:
            cursor.execute(
                """
                SELECT * FROM vpn_devices 
                WHERE ldap_uid = %s 
                ORDER BY created_at DESC
                """,
                (ldap_uid,)
            )
        else:
            cursor.execute(
                """
                SELECT * FROM vpn_devices 
                WHERE ldap_uid = %s AND status = 'active'
                ORDER BY created_at DESC
                """,
                (ldap_uid,)
            )
        
        devices = cursor.fetchall()
        return [dict(device) for device in devices]


def get_device_by_id(device_id: int, ldap_uid: str = None) -> dict:
    """
    Get device by ID
    If ldap_uid is provided, verify ownership
    Returns device dictionary or None
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if ldap_uid:
            cursor.execute(
                "SELECT * FROM vpn_devices WHERE id = %s AND ldap_uid = %s",
                (device_id, ldap_uid)
            )
        else:
            cursor.execute(
                "SELECT * FROM vpn_devices WHERE id = %s",
                (device_id,)
            )
        
        device = cursor.fetchone()
        return dict(device) if device else None


def get_device_by_public_key(public_key: str) -> dict:
    """Get device by public key"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM vpn_devices WHERE public_key = %s",
            (public_key,)
        )
        device = cursor.fetchone()
        return dict(device) if device else None


def revoke_device(device_id: int, revoked_by: str, revoke_reason: str = None) -> bool:
    """
    Revoke a device (soft delete)
    Returns True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Get device info before revoking
            device = get_device_by_id(device_id)
            if not device:
                return False
            
            # Update device status
            cursor.execute(
                """
                UPDATE vpn_devices 
                SET status = 'revoked',
                    revoked_at = NOW(),
                    revoked_by = %s,
                    revoke_reason = %s
                WHERE id = %s
                """,
                (revoked_by, revoke_reason, device_id)
            )
            
            # Insert into revoke history
            cursor.execute(
                """
                INSERT INTO vpn_revoke_history 
                (device_id, ldap_uid, public_key, device_name, revoked_by, revoke_reason)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    device_id,
                    device['ldap_uid'],
                    device['public_key'],
                    device['device_name'],
                    revoked_by,
                    revoke_reason
                )
            )
            
            conn.commit()
            logger.info(f"Device revoked: ID={device_id}, Revoked by={revoked_by}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error revoking device: {e}")
            return False


def update_device_traffic(
    public_key: str,
    transfer_rx: int,
    transfer_tx: int,
    last_seen: datetime = None
) -> bool:
    """
    Update device traffic statistics
    Returns True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            transfer_total = transfer_rx + transfer_tx
            
            if last_seen:
                cursor.execute(
                    """
                    UPDATE vpn_devices 
                    SET transfer_rx = %s,
                        transfer_tx = %s,
                        transfer_total = %s,
                        last_seen = %s
                    WHERE public_key = %s
                    """,
                    (transfer_rx, transfer_tx, transfer_total, last_seen, public_key)
                )
            else:
                cursor.execute(
                    """
                    UPDATE vpn_devices 
                    SET transfer_rx = %s,
                        transfer_tx = %s,
                        transfer_total = %s
                    WHERE public_key = %s
                    """,
                    (transfer_rx, transfer_tx, transfer_total, public_key)
                )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating device traffic: {e}")
            return False


def batch_update_device_traffic(updates: list) -> int:
    """
    Batch update device traffic statistics
    updates: List of dicts dengan keys: public_key, transfer_rx, transfer_tx, last_seen
    Returns number of successful updates
    """
    if not updates:
        return 0
    
    success_count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            for update in updates:
                public_key = update['public_key']
                transfer_rx = update['transfer_rx']
                transfer_tx = update['transfer_tx']
                transfer_total = transfer_rx + transfer_tx
                last_seen = update.get('last_seen')
                
                if last_seen:
                    cursor.execute(
                        """
                        UPDATE vpn_devices 
                        SET transfer_rx = %s,
                            transfer_tx = %s,
                            transfer_total = %s,
                            last_seen = %s
                        WHERE public_key = %s
                        """,
                        (transfer_rx, transfer_tx, transfer_total, last_seen, public_key)
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE vpn_devices 
                        SET transfer_rx = %s,
                            transfer_tx = %s,
                            transfer_total = %s
                        WHERE public_key = %s
                        """,
                        (transfer_rx, transfer_tx, transfer_total, public_key)
                    )
                
                if cursor.rowcount > 0:
                    success_count += 1
            
            conn.commit()
            logger.debug(f"Batch updated {success_count}/{len(updates)} devices")
            return success_count
        except Exception as e:
            conn.rollback()
            logger.error(f"Error batch updating device traffic: {e}")
            return success_count


def batch_insert_traffic_logs(logs: list) -> int:
    """
    Batch insert traffic logs
    logs: List of dicts dengan keys: device_id, ldap_uid, public_key, transfer_rx, transfer_tx
    Returns number of successful inserts
    """
    if not logs:
        return 0
    
    success_count = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            for log in logs:
                transfer_total = log['transfer_rx'] + log['transfer_tx']
                cursor.execute(
                    """
                    INSERT INTO vpn_traffic_logs 
                    (device_id, ldap_uid, public_key, transfer_rx, transfer_tx, transfer_total)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        log['device_id'],
                        log['ldap_uid'],
                        log['public_key'],
                        log['transfer_rx'],
                        log['transfer_tx'],
                        transfer_total
                    )
                )
                success_count += 1
            
            conn.commit()
            logger.debug(f"Batch inserted {success_count}/{len(logs)} traffic logs")
            return success_count
        except Exception as e:
            conn.rollback()
            logger.error(f"Error batch inserting traffic logs: {e}")
            return success_count


def get_all_devices(status: str = None, limit: int = None, offset: int = 0) -> list:
    """
    Get all devices (admin function)
    Returns list of device dictionaries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM vpn_devices"
        params = []
        
        if status:
            query += " WHERE status = %s"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])
        
        cursor.execute(query, params)
        devices = cursor.fetchall()
        return [dict(device) for device in devices]


def check_ip_available(vpn_ip: str) -> bool:
    """Check if IP address is available"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM vpn_devices WHERE vpn_ip = %s AND status = 'active'",
            (vpn_ip,)
        )
        return cursor.fetchone() is None


def count_user_devices(ldap_uid: str, active_only: bool = True) -> int:
    """Count devices for a user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute(
                "SELECT COUNT(*) as count FROM vpn_devices WHERE ldap_uid = %s AND status = 'active'",
                (ldap_uid,)
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) as count FROM vpn_devices WHERE ldap_uid = %s",
                (ldap_uid,)
            )
        
        result = cursor.fetchone()
        return result['count'] if result else 0


def insert_traffic_log(device_id: int, ldap_uid: str, public_key: str, transfer_rx: int, transfer_tx: int) -> bool:
    """Insert traffic log entry for analytics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            transfer_total = transfer_rx + transfer_tx
            cursor.execute(
                """
                INSERT INTO vpn_traffic_logs 
                (device_id, ldap_uid, public_key, transfer_rx, transfer_tx, transfer_total)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (device_id, ldap_uid, public_key, transfer_rx, transfer_tx, transfer_total)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error inserting traffic log: {e}")
            return False


def get_traffic_logs(
    device_id: int = None,
    ldap_uid: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = 1000
) -> list:
    """
    Get traffic logs untuk analytics
    Returns list of log entries
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM vpn_traffic_logs WHERE 1=1"
        params = []
        
        if device_id:
            query += " AND device_id = %s"
            params.append(device_id)
        
        if ldap_uid:
            query += " AND ldap_uid = %s"
            params.append(ldap_uid)
        
        if start_time:
            query += " AND recorded_at >= %s"
            params.append(start_time)
        
        if end_time:
            query += " AND recorded_at <= %s"
            params.append(end_time)
        
        query += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        return [dict(log) for log in logs]


def get_traffic_summary(
    device_id: int = None,
    ldap_uid: str = None,
    hours: int = 24
) -> dict:
    """
    Get traffic summary statistics
    Returns summary dengan total rx, tx, total
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        
        query = """
            SELECT 
                SUM(transfer_rx) as total_rx,
                SUM(transfer_tx) as total_tx,
                SUM(transfer_total) as total,
                COUNT(*) as log_count,
                AVG(transfer_rx) as avg_rx,
                AVG(transfer_tx) as avg_tx
            FROM vpn_traffic_logs
            WHERE recorded_at >= %s
        """
        params = [since]
        
        if device_id:
            query += " AND device_id = %s"
            params.append(device_id)
        elif ldap_uid:
            query += " AND ldap_uid = %s"
            params.append(ldap_uid)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        return {
            "total_rx": result['total_rx'] or 0,
            "total_tx": result['total_tx'] or 0,
            "total": result['total'] or 0,
            "log_count": result['log_count'] or 0,
            "avg_rx": float(result['avg_rx']) if result['avg_rx'] else 0,
            "avg_tx": float(result['avg_tx']) if result['avg_tx'] else 0,
            "hours": hours,
            "since": since.isoformat()
        }


def save_qr_code(device_id: int, qr_code_base64: str, expires_at: datetime) -> bool:
    """
    Save QR code dengan expiration timestamp
    Returns True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                UPDATE vpn_devices 
                SET qr_code_base64 = %s,
                    qr_code_expires_at = %s
                WHERE id = %s
                """,
                (qr_code_base64, expires_at, device_id)
            )
            conn.commit()
            logger.info(f"QR code saved for device ID={device_id}, expires_at={expires_at}")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving QR code: {e}")
            return False


def get_qr_code(device_id: int) -> dict:
    """
    Get QR code untuk device
    Returns dict dengan qr_code_base64 dan expires_at, atau None jika tidak ada/expired
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT qr_code_base64, qr_code_expires_at 
            FROM vpn_devices 
            WHERE id = %s
            """,
            (device_id,)
        )
        result = cursor.fetchone()
        
        if not result or not result['qr_code_base64']:
            return None
        
        # Check expiration
        expires_at = result['qr_code_expires_at']
        if expires_at and datetime.now() > expires_at:
            # QR expired, clear it
            cursor.execute(
                "UPDATE vpn_devices SET qr_code_base64 = NULL, qr_code_expires_at = NULL WHERE id = %s",
                (device_id,)
            )
            conn.commit()
            return None
        
        return {
            "qr_code_base64": result['qr_code_base64'],
            "expires_at": expires_at.isoformat() if expires_at else None
        }


def clear_qr_code(device_id: int) -> bool:
    """
    Clear QR code dari database (setelah expired atau revoked)
    Returns True if successful
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE vpn_devices SET qr_code_base64 = NULL, qr_code_expires_at = NULL WHERE id = %s",
                (device_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error clearing QR code: {e}")
            return False
