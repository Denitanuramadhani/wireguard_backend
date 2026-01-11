"""
LDAP Client Module
Handles LDAP operations untuk WireGuard VPN Portal
Uses connection pooling dan caching untuk performance
"""

from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from app.config import LDAP_SERVER, LDAP_BASE_DN, LDAP_USER_DN, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD
from app.core.ldap_pool import get_ldap_pool
from app.core.cache import cached
from app.core.audit_logger import log_audit_event
from app.logger import logger


def get_ldap_connection(admin: bool = False):
    """
    Get LDAP connection from pool
    admin=True: Use admin credentials
    admin=False: Anonymous connection (untuk read-only)
    """
    pool = get_ldap_pool()
    return pool.get_connection(admin=admin)


def get_user_attributes(username: str, attributes: list = None):
    """
    Get user attributes from LDAP
    Returns dict dengan attributes atau None jika user tidak ditemukan
    Uses connection pool
    """
    if attributes is None:
        attributes = ['*']  # Get all attributes
    
    pool = get_ldap_pool()
    conn = None
    try:
        conn = pool.get_connection(admin=False)
        user_dn = LDAP_USER_DN.format(username)
        
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter=f"(uid={username})",
            attributes=attributes
        )
        
        if conn.entries:
            entry = conn.entries[0]
            result = {}
            for attr in attributes:
                if attr == '*':
                    # Get all attributes
                    for key in entry.entry_attributes:
                        result[key] = str(entry[key]) if entry[key] else None
                else:
                    result[attr] = str(entry[attr]) if entry[attr] else None
            return result
        
        return None
    except Exception as e:
        logger.error(f"Error getting user attributes for {username}: {e}")
        return None
    finally:
        if conn:
            pool.return_connection(conn, admin=False)


@cached(ttl=600, key_prefix="ldap:wireguard_enabled")  # Cache 10 menit
def check_wireguard_enabled(username: str) -> bool:
    """
    Check if user has WireGuard access enabled
    Returns True jika wireguardEnabled = TRUE, False jika FALSE atau tidak set
    Cached for 10 minutes
    """
    try:
        attrs = get_user_attributes(username, ['wireguardEnabled', 'objectClass'])
        
        if not attrs:
            return False
        
        # Check if user has wireguardUser objectClass
        object_classes = attrs.get('objectClass', '')
        if isinstance(object_classes, list):
            has_wireguard_user = 'wireguardUser' in object_classes
        else:
            has_wireguard_user = 'wireguardUser' in str(object_classes)
        
        if not has_wireguard_user:
            return False
        
        # Check wireguardEnabled attribute
        enabled = attrs.get('wireguardEnabled', 'FALSE')
        return str(enabled).upper() == 'TRUE'
    except Exception as e:
        logger.error(f"Error checking wireguardEnabled for {username}: {e}")
        return False


@cached(ttl=600, key_prefix="ldap:max_devices")  # Cache 10 menit
def get_max_devices(username: str) -> int:
    """
    Get maximum devices allowed for user
    Returns int, default 3 jika tidak set
    Cached for 10 minutes
    """
    try:
        attrs = get_user_attributes(username, ['maxWireguardDevices'])
        
        if not attrs:
            return 3  # Default
        
        max_devices = attrs.get('maxWireguardDevices')
        if max_devices:
            try:
                return int(max_devices)
            except:
                return 3
        
        return 3  # Default
    except Exception as e:
        logger.error(f"Error getting maxWireguardDevices for {username}: {e}")
        return 3


def enable_wireguard_user(username: str) -> bool:
    """
    Enable WireGuard access untuk user
    Returns True jika berhasil
    Invalidates cache setelah success
    """
    pool = get_ldap_pool()
    conn = None
    try:
        conn = pool.get_connection(admin=True)
        user_dn = LDAP_USER_DN.format(username)
        
        # Check if user exists
        conn.search(search_base=LDAP_BASE_DN, search_filter=f"(uid={username})", attributes=['dn', 'objectClass'])
        if not conn.entries:
            logger.error(f"User {username} not found")
            return False
        
        entry = conn.entries[0]
        current_object_classes = entry.objectClass.values if hasattr(entry.objectClass, 'values') else []
        
        # Prepare changes
        changes = {}
        
        # Add wireguardUser objectClass if not present
        if 'wireguardUser' not in current_object_classes:
            new_object_classes = list(current_object_classes) + ['wireguardUser']
            changes['objectClass'] = [(MODIFY_REPLACE, new_object_classes)]
        
        # Set wireguardEnabled = TRUE
        changes['wireguardEnabled'] = [(MODIFY_REPLACE, ['TRUE'])]
        
        # Check if maxWireguardDevices sudah ada, jika tidak tambahkan
        attrs = get_user_attributes(username, ['maxWireguardDevices'])
        if not attrs or not attrs.get('maxWireguardDevices'):
            changes['maxWireguardDevices'] = [(MODIFY_REPLACE, ['3'])]
        
        conn.modify(user_dn, changes)
        
        if conn.result['description'] == 'success':
            logger.info(f"WireGuard enabled for user {username}")
            # Invalidate cache
            check_wireguard_enabled.invalidate(username)
            get_max_devices.invalidate(username)
            
            # Audit log (performed_by akan di-set oleh caller)
            # Note: Caller harus pass performed_by untuk audit log
            return True
        else:
            logger.error(f"Failed to enable WireGuard for {username}: {conn.result}")
            return False
    except Exception as e:
        logger.error(f"Error enabling WireGuard for {username}: {e}")
        return False
    finally:
        if conn:
            pool.return_connection(conn, admin=True)


def disable_wireguard_user(username: str) -> bool:
    """
    Disable WireGuard access untuk user
    Returns True jika berhasil
    Invalidates cache setelah success
    """
    pool = get_ldap_pool()
    conn = None
    try:
        conn = pool.get_connection(admin=True)
        user_dn = LDAP_USER_DN.format(username)
        
        # Modify user: set wireguardEnabled = FALSE
        changes = {
            'wireguardEnabled': [(MODIFY_REPLACE, ['FALSE'])]
        }
        
        conn.modify(user_dn, changes)
        
        if conn.result['description'] == 'success':
            logger.info(f"WireGuard disabled for user {username}")
            # Invalidate cache
            check_wireguard_enabled.invalidate(username)
            return True
        else:
            logger.error(f"Failed to disable WireGuard for {username}: {conn.result}")
            return False
    except Exception as e:
        logger.error(f"Error disabling WireGuard for {username}: {e}")
        return False
    finally:
        if conn:
            pool.return_connection(conn, admin=True)


def set_max_devices(username: str, max_devices: int) -> bool:
    """
    Set maximum devices untuk user
    Returns True jika berhasil
    Invalidates cache setelah success
    """
    pool = get_ldap_pool()
    conn = None
    try:
        conn = pool.get_connection(admin=True)
        user_dn = LDAP_USER_DN.format(username)
        
        changes = {
            'maxWireguardDevices': [(MODIFY_REPLACE, [str(max_devices)])]
        }
        
        conn.modify(user_dn, changes)
        
        if conn.result['description'] == 'success':
            logger.info(f"Max devices set to {max_devices} for user {username}")
            # Invalidate cache
            get_max_devices.invalidate(username)
            return True
        else:
            logger.error(f"Failed to set max devices for {username}: {conn.result}")
            return False
    except Exception as e:
        logger.error(f"Error setting max devices for {username}: {e}")
        return False
    finally:
        if conn:
            pool.return_connection(conn, admin=True)


def check_user_in_group(username: str, group_dn: str) -> bool:
    """
    Check if user is member of a group
    Returns True jika user adalah member
    """
    try:
        attrs = get_user_attributes(username, ['memberOf'])
        
        if not attrs:
            return False
        
        member_of = attrs.get('memberOf', '')
        if isinstance(member_of, list):
            return group_dn in member_of
        else:
            return group_dn in str(member_of)
    except Exception as e:
        logger.error(f"Error checking group membership for {username}: {e}")
        return False


@cached(ttl=900, key_prefix="ldap:is_admin")  # Cache 15 menit
def is_admin(username: str) -> bool:
    """
    Check if user is admin
    Checks memberOf attribute untuk admin group
    Cached for 15 minutes
    """
    admin_group_dn = f"cn=admins,ou=groups,{LDAP_BASE_DN}"
    return check_user_in_group(username, admin_group_dn)
