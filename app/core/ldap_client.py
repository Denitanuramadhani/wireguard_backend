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
    FIXED: Safe error handling - tidak pernah raise exception, selalu return None jika error
    
    Returns dict dengan attributes atau None jika user tidak ditemukan atau error
    Uses connection pool
    """
    if not username:
        logger.warning("[LDAP CLIENT] get_user_attributes called with empty username")
        return None
    
    if attributes is None:
        attributes = ['*']  # Get all attributes
    
    pool = None
    conn = None
    
    # FIXED: Handle pool initialization error
    try:
        pool = get_ldap_pool()
    except Exception as e:
        logger.error(
            f"[LDAP CLIENT ERROR] Failed to get LDAP pool for {username}: {e}",
            exc_info=True
        )
        return None
    
    try:
        # FIXED: Handle connection get error
        try:
            conn = pool.get_connection(admin=True)
        except Exception as e:
            logger.error(
                f"[LDAP CLIENT ERROR] Failed to get LDAP connection for {username}: {e}",
                exc_info=True
            )
            return None
        
        # FIXED: Handle DN formatting error
        try:
            user_dn = LDAP_USER_DN.format(username)
        except Exception as e:
            logger.error(
                f"[LDAP CLIENT ERROR] Failed to format user DN for {username}: {e}",
                exc_info=True
            )
            return None
        
        # FIXED: Handle search error
        try:
            conn.search(
                search_base=LDAP_BASE_DN,
                search_filter=f"(uid={username})",
                attributes=attributes
            )
        except Exception as e:
            logger.error(
                f"[LDAP CLIENT ERROR] LDAP search failed for {username}: {e}",
                exc_info=True
            )
            return None
        
        # FIXED: Safe attribute extraction
        if conn.entries:
            try:
                entry = conn.entries[0]
                result = {}
                for attr in attributes:
                    try:
                        if attr == '*':
                            # Get all attributes
                            for key in entry.entry_attributes:
                                try:
                                    result[key] = str(entry[key]) if entry[key] else None
                                except Exception as e:
                                    logger.warning(f"[LDAP CLIENT] Error getting attribute {key} for {username}: {e}")
                                    result[key] = None
                        else:
                            try:
                                result[attr] = str(entry[attr]) if entry[attr] else None
                            except Exception as e:
                                logger.warning(f"[LDAP CLIENT] Error getting attribute {attr} for {username}: {e}")
                                result[attr] = None
                    except Exception as e:
                        logger.warning(f"[LDAP CLIENT] Error processing attribute {attr} for {username}: {e}")
                return result
            except Exception as e:
                logger.error(
                    f"[LDAP CLIENT ERROR] Error processing entry for {username}: {e}",
                    exc_info=True
                )
                return None
        
        return None
        
    except Exception as e:
        # FIXED: Catch-all dengan logging detail
        logger.error(
            f"[LDAP CLIENT ERROR] Unexpected error getting user attributes for {username}: {e}",
            exc_info=True
        )
        return None
    finally:
        # FIXED: Safe connection cleanup
        if conn and pool:
            try:
                pool.return_connection(conn, admin=True)
            except Exception as e:
                logger.warning(f"[LDAP CLIENT] Error returning connection to pool: {e}")


# FIXED: Cache decorator sudah handle Redis error dengan fallback ke direct execution
# Jika cache error, function tetap jalan tanpa cache
@cached(ttl=600, key_prefix="ldap:wireguard_enabled")  # Cache 10 menit
def check_wireguard_enabled(username: str) -> bool:
    """
    Check if user has WireGuard access enabled
    Returns True jika wireguardEnabled = TRUE, False jika FALSE atau tidak set
    Cached for 10 minutes
    
    Safe: Tidak pernah raise exception, selalu return False jika error
    """
    if not username:
        logger.warning("[LDAP CLIENT] check_wireguard_enabled called with empty username")
        return False
    
    try:
        attrs = get_user_attributes(username, ['wireguardEnabled', 'objectClass'])
        
        if not attrs:
            logger.debug(f"[LDAP CLIENT] User {username} not found or no attributes")
            return False
        
        # Check if user has wireguardUser objectClass
        try:
            object_classes = attrs.get('objectClass', '')
            if isinstance(object_classes, list):
                has_wireguard_user = 'wireguardUser' in object_classes
            elif isinstance(object_classes, str):
                has_wireguard_user = 'wireguardUser' in object_classes
            else:
                # Try to convert to string
                has_wireguard_user = 'wireguardUser' in str(object_classes)
        except Exception as e:
            logger.warning(
                f"[LDAP CLIENT] Error checking objectClass for {username}: {e}. "
                "Assuming no wireguardUser objectClass"
            )
            has_wireguard_user = False
        
        if not has_wireguard_user:
            logger.debug(f"[LDAP CLIENT] User {username} does not have wireguardUser objectClass")
            return False
        
        # Check wireguardEnabled attribute
        try:
            enabled = attrs.get('wireguardEnabled', 'FALSE')
            if isinstance(enabled, list):
                enabled = enabled[0] if enabled else 'FALSE'
            enabled_str = str(enabled).upper()
            result = enabled_str == 'TRUE'
            logger.debug(f"[LDAP CLIENT] wireguardEnabled for {username}: {enabled_str} -> {result}")
            return result
        except Exception as e:
            logger.warning(
                f"[LDAP CLIENT] Error parsing wireguardEnabled for {username}: {e}. "
                "Defaulting to FALSE"
            )
            return False
            
    except Exception as e:
        # Catch-all: return False jika ada error (tidak block login)
        logger.error(
            f"[LDAP CLIENT ERROR] Error checking wireguardEnabled for {username}: {e}",
            exc_info=True
        )
        return False


# FIXED: Cache decorator sudah handle Redis error dengan fallback ke direct execution
# Jika cache error, function tetap jalan tanpa cache
@cached(ttl=600, key_prefix="ldap:max_devices")  # Cache 10 menit
def get_max_devices(username: str) -> int:
    """
    Get maximum devices allowed for user
    Returns int, default 3 jika tidak set atau error
    
    Safe: Tidak pernah raise exception, selalu return 3 jika error
    Cached for 10 minutes
    """
    DEFAULT_MAX_DEVICES = 3
    
    if not username:
        logger.warning("[LDAP CLIENT] get_max_devices called with empty username")
        return DEFAULT_MAX_DEVICES
    
    try:
        attrs = get_user_attributes(username, ['maxWireguardDevices'])
        
        if not attrs:
            logger.debug(f"[LDAP CLIENT] User {username} not found or no maxWireguardDevices attribute")
            return DEFAULT_MAX_DEVICES
        
        try:
            max_devices = attrs.get('maxWireguardDevices')
            
            if max_devices is None:
                logger.debug(f"[LDAP CLIENT] maxWireguardDevices is None for {username}")
                return DEFAULT_MAX_DEVICES
            
            # Handle list (jika attribute multi-valued)
            if isinstance(max_devices, list):
                max_devices = max_devices[0] if max_devices else None
            
            if max_devices is None:
                return DEFAULT_MAX_DEVICES
            
            # Convert to int
            try:
                result = int(max_devices)
                # Validate range (1-100)
                if result < 1:
                    logger.warning(
                        f"[LDAP CLIENT] maxWireguardDevices for {username} is {result}, "
                        f"using default {DEFAULT_MAX_DEVICES}"
                    )
                    return DEFAULT_MAX_DEVICES
                if result > 100:
                    logger.warning(
                        f"[LDAP CLIENT] maxWireguardDevices for {username} is {result}, "
                        f"capping at 100"
                    )
                    return 100
                
                logger.debug(f"[LDAP CLIENT] maxWireguardDevices for {username}: {result}")
                return result
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"[LDAP CLIENT] Invalid maxWireguardDevices value for {username}: "
                    f"{max_devices} ({type(max_devices).__name__}). Error: {e}. "
                    f"Using default {DEFAULT_MAX_DEVICES}"
                )
                return DEFAULT_MAX_DEVICES
                
        except Exception as e:
            logger.warning(
                f"[LDAP CLIENT] Error parsing maxWireguardDevices for {username}: {e}. "
                f"Using default {DEFAULT_MAX_DEVICES}"
            )
            return DEFAULT_MAX_DEVICES
            
    except Exception as e:
        # Catch-all: return default jika ada error (tidak block login)
        logger.error(
            f"[LDAP CLIENT ERROR] Error getting maxWireguardDevices for {username}: {e}",
            exc_info=True
        )
        return DEFAULT_MAX_DEVICES


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
