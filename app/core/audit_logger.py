"""
Audit Logger
Logs all security-relevant operations untuk audit trail
"""

from datetime import datetime
from typing import Optional, Dict, Any
from app.database.connection import get_db_connection
from app.logger import logger


def log_audit_event(
    action: str,
    performed_by: str,
    ldap_uid: Optional[str] = None,
    device_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Log audit event ke database
    action: Type of action (device_created, device_revoked, user_enabled, etc.)
    performed_by: Username who performed the action
    Returns True if successful
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Convert details dict to JSON string
            details_json = None
            if details:
                import json
                details_json = json.dumps(details, default=str)
            
            cursor.execute(
                """
                INSERT INTO vpn_audit_logs 
                (action, ldap_uid, device_id, performed_by, ip_address, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (action, ldap_uid, device_id, performed_by, ip_address, details_json)
            )
            
            conn.commit()
            logger.debug(f"Audit log: {action} by {performed_by}")
            return True
            
    except Exception as e:
        logger.error(f"Error logging audit event: {e}")
        return False


def get_audit_logs(
    action: Optional[str] = None,
    ldap_uid: Optional[str] = None,
    performed_by: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Get audit logs dengan filtering
    Returns list of audit log entries
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM vpn_audit_logs WHERE 1=1"
            params = []
            
            if action:
                query += " AND action = %s"
                params.append(action)
            
            if ldap_uid:
                query += " AND ldap_uid = %s"
                params.append(ldap_uid)
            
            if performed_by:
                query += " AND performed_by = %s"
                params.append(performed_by)
            
            query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            # Parse JSON details
            result = []
            for log in logs:
                log_dict = dict(log)
                if log_dict.get('details'):
                    import json
                    try:
                        log_dict['details'] = json.loads(log_dict['details'])
                    except:
                        pass
                result.append(log_dict)
            
            return result
            
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return []
