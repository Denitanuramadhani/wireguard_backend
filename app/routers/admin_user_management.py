"""
Admin User Management Endpoint
CRUD operations untuk user management:
- Create: /admin/add-user (di admin_add_user.py)
- Read: /admin/users (di admin.py)
- Update: /admin/users/{username}/role (di sini)
- Delete: /admin/users/{username} (di sini) - Hard delete dari LDAP dan MySQL

SECURITY:
- Semua endpoint memerlukan JWT token (Authorization: Bearer <token>)
- Hanya user dengan role 'admin' yang bisa akses (via verify_jwt_admin)
- Admin check: MySQL role dulu, lalu fallback ke LDAP group membership
"""

from fastapi import APIRouter, HTTPException, Request
from app.middleware.auth_middleware import verify_jwt_admin
from app.database.connection import get_db_connection
from app.core.ldap_client import get_user_attributes
from app.core.cache import clear_cache_prefix
from app.logger import logger
from app.core.audit_logger import log_audit_event
from datetime import datetime
import ldap3
from app.config import (
    LDAP_SERVER, LDAP_BASE_DN, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# Import check_ldap_user_exists dari admin_add_user
from app.routers.admin_add_user import check_ldap_user_exists


@router.put("/users/{username}/role")
def update_user_role(username: str, data: dict, request: Request):
    """
    Update role user di MySQL
    Role: 'user' atau 'admin'
    
    SECURITY: Requires JWT token + Admin role
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Payload:
    {
        "role": "admin"  // atau "user"
    }
    
    Note: Menggunakan username (bukan ID) karena:
    - Username konsisten antara LDAP dan MySQL
    - Lebih mudah diingat dan digunakan
    - ID hanya ada di MySQL, tidak ada di LDAP
    """
    admin_username = verify_jwt_admin(request)
    
    # Validate role
    role = data.get("role")
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")
    
    # Check if user exists in LDAP
    if not check_ldap_user_exists(username):
        raise HTTPException(status_code=404, detail=f"User {username} not found in LDAP")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists in MySQL
            cursor.execute("SELECT id, role FROM users WHERE username = %s", (username,))
            existing = cursor.fetchone()
            
            if not existing:
                # User tidak ada di MySQL, insert baru
                cursor.execute("""
                    INSERT INTO users (username, role, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                """, (username, role, datetime.now(), datetime.now()))
                conn.commit()
                logger.info(f"[UPDATE-ROLE] Inserted new user '{username}' with role '{role}'")
                action = "inserted"
            else:
                # Update role
                old_role = existing.get('role')
                if old_role == role:
                    logger.info(f"[UPDATE-ROLE] User '{username}' already has role '{role}', no change needed")
                    return {
                        "status": "ok",
                        "message": f"User {username} already has role {role}",
                        "username": username,
                        "role": role
                    }
                
                cursor.execute("""
                    UPDATE users 
                    SET role = %s, updated_at = %s 
                    WHERE username = %s
                """, (role, datetime.now(), username))
                conn.commit()
                logger.info(f"[UPDATE-ROLE] Updated user '{username}' role: {old_role} -> {role}")
                action = "updated"
            
            # Clear cache untuk is_admin
            clear_cache_prefix("ldap:is_admin")
            
            # Audit log
            try:
                log_audit_event(
                    action="update_user_role",
                    performed_by=admin_username,
                    ip_address=request.client.host if request.client else None,
                    details={
                        "username": username,
                        "old_role": existing.get('role') if existing else None,
                        "new_role": role,
                        "action": action
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log audit event: {audit_error}")
            
            return {
                "status": "ok",
                "message": f"User {username} role {action} successfully",
                "username": username,
                "role": role,
                "old_role": existing.get('role') if existing else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPDATE-ROLE] Error updating role for user '{username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update user role: {str(e)}")


@router.delete("/users/{username}")
def delete_user(username: str, request: Request):
    """
    Delete user dari LDAP dan MySQL (hard delete)
    Hapus user sepenuhnya dari LDAP dan MySQL
    WARNING: This will permanently delete the user!
    
    SECURITY: Requires JWT token + Admin role
    
    Headers:
        Authorization: Bearer <jwt_token>
    """
    admin_username = verify_jwt_admin(request)
    
    # Check if user exists in LDAP
    if not check_ldap_user_exists(username):
        raise HTTPException(status_code=404, detail=f"User {username} not found in LDAP")
    
    try:
        # Step 1: Delete from MySQL first
        mysql_deleted = False
        deleted_role = None
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
                existing = cursor.fetchone()
                if existing:
                    deleted_role = existing.get('role')
                    cursor.execute("DELETE FROM users WHERE username = %s", (username,))
                    conn.commit()
                    mysql_deleted = True
                    logger.info(f"[DELETE-USER] Deleted user '{username}' from MySQL")
        except Exception as e:
            logger.warning(f"[DELETE-USER] Error deleting from MySQL (non-critical): {e}")
        
        # Step 2: Delete from LDAP
        ldap_deleted = False
        try:
            server = ldap3.Server(LDAP_SERVER)
            conn = ldap3.Connection(
                server,
                user=LDAP_ADMIN_DN,
                password=LDAP_ADMIN_PASSWORD,
                auto_bind=True
            )
            
            # Get user DN
            from app.config import LDAP_USER_DN
            user_dn = LDAP_USER_DN.format(username)
            
            # Delete user from LDAP
            if conn.delete(user_dn):
                logger.info(f"[DELETE-USER] Deleted user '{username}' from LDAP")
                ldap_deleted = True
            else:
                logger.error(f"[DELETE-USER] Failed to delete user '{username}' from LDAP: {conn.result}")
                raise HTTPException(status_code=500, detail=f"Failed to delete user from LDAP: {conn.result}")
            
            conn.unbind()
            
        except ldap3.core.exceptions.LDAPException as e:
            logger.error(f"[DELETE-USER] LDAP error deleting user '{username}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to delete user from LDAP: {str(e)}")
        
        # Clear cache
        clear_cache_prefix("ldap:is_admin")
        
        # Audit log
        try:
            log_audit_event(
                action="delete_user",
                performed_by=admin_username,
                ip_address=request.client.host if request.client else None,
                details={
                    "username": username,
                    "deleted_role": deleted_role,
                    "mysql_deleted": mysql_deleted,
                    "ldap_deleted": True,
                    "note": "User permanently deleted from LDAP and MySQL"
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log audit event: {audit_error}")
        
        return {
            "status": "ok",
            "message": f"User {username} deleted from LDAP and MySQL successfully",
            "username": username,
            "mysql_deleted": mysql_deleted,
            "ldap_deleted": True,
            "warning": "User has been permanently deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DELETE-USER] Error deleting user '{username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.get("/users/{username}")
def get_user_detail(username: str, request: Request):
    """
    Get detail user dari LDAP dan MySQL
    Returns: username, role, LDAP attributes, device count, etc.
    
    SECURITY: Requires JWT token + Admin role
    
    Headers:
        Authorization: Bearer <jwt_token>
    """
    verify_jwt_admin(request)
    
    # Check if user exists in LDAP
    if not check_ldap_user_exists(username):
        raise HTTPException(status_code=404, detail=f"User {username} not found in LDAP")
    
    try:
        # Get LDAP attributes
        user_attrs = get_user_attributes(username, ['uid', 'cn', 'mail', 'wireguardEnabled', 'maxWireguardDevices'])
        
        # Get MySQL role
        role = None
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role, created_at, updated_at FROM users WHERE username = %s", (username,))
                mysql_user = cursor.fetchone()
                if mysql_user:
                    role = mysql_user.get('role')
        except Exception as e:
            logger.debug(f"Error getting MySQL role for {username}: {e}")
        
        # Get device count
        from app.database.queries import get_user_devices
        devices = get_user_devices(username, include_revoked=False)
        
        return {
            "status": "ok",
            "username": username,
            "role": role or "user",  # Default jika tidak ada di MySQL
            "ldap": {
                "cn": user_attrs.get('cn') if user_attrs else None,
                "mail": user_attrs.get('mail') if user_attrs else None,
                "wireguard_enabled": user_attrs.get('wireguardEnabled') == 'TRUE' if user_attrs else False,
                "max_devices": int(user_attrs.get('maxWireguardDevices', 3)) if user_attrs else 3
            },
            "mysql": {
                "role": role,
                "created_at": mysql_user.get('created_at').isoformat() if mysql_user and mysql_user.get('created_at') else None,
                "updated_at": mysql_user.get('updated_at').isoformat() if mysql_user and mysql_user.get('updated_at') else None
            } if mysql_user else None,
            "devices": {
                "count": len(devices),
                "active": len([d for d in devices if d.get('status') == 'active'])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GET-USER] Error getting user detail for '{username}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get user detail: {str(e)}")

