import subprocess
from fastapi import APIRouter, HTTPException, Request
from app.middleware.auth_middleware import verify_jwt_admin
from app.config import (
    LDAP_SERVER, LDAP_BASE_DN, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD,
    ALLOW_NO_AUTH_ADD_USER, ENVIRONMENT
)
from app.core.ldap_client import get_user_attributes
from app.logger import logger
import ldap3

router = APIRouter(prefix="/admin", tags=["Admin"])

LDAP_BASE_PEOPLE = f"ou=people,{LDAP_BASE_DN}"


def ldap_add_user(username: str, password: str, uid_number: int, max_devices: int = 3) -> bool:
    """
    Tambah user ke LDAP dengan password SSHA hash
    Set wireguardEnabled = FALSE default
    Tambahkan objectClass wireguardUser
    """
    logger.info(f"[LDAP] Starting user creation for: {username}")
    logger.debug(f"[LDAP] Parameters - uid_number: {uid_number}, max_devices: {max_devices}")
    
    # Hash password via slappasswd
    logger.debug(f"[LDAP] Hashing password for user: {username}")
    try:
        hashed_pass = subprocess.check_output(
            ["slappasswd", "-s", password]
        ).decode().strip()
        logger.debug(f"[LDAP] Password hashed successfully (length: {len(hashed_pass)})")
    except FileNotFoundError:
        logger.error(f"[LDAP] slappasswd command not found! Make sure openldap-utils is installed")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"[LDAP] Error hashing password (exit code {e.returncode}): {e}")
        return False
    except Exception as e:
        logger.error(f"[LDAP] Unexpected error hashing password: {e}", exc_info=True)
        return False

    dn = f"uid={username},{LDAP_BASE_PEOPLE}"
    logger.debug(f"[LDAP] User DN: {dn}")
    logger.debug(f"[LDAP] LDAP_BASE_PEOPLE: {LDAP_BASE_PEOPLE}")

    # Attributes dengan wireguardUser objectClass
    attr = {
        "objectClass": [
            "inetOrgPerson", "organizationalPerson",
            "person", "posixAccount", "top", "wireguardUser"
        ],
        "cn": username,
        "sn": username,
        "uid": username,
        "uidNumber": str(uid_number),
        "gidNumber": str(uid_number),
        "homeDirectory": f"/home/{username}",
        "loginShell": "/bin/bash",
        "userPassword": hashed_pass,
        "wireguardEnabled": "FALSE",  # Default disabled
        "maxWireguardDevices": str(max_devices)  # Default 3 devices
    }
    logger.debug(f"[LDAP] Attributes prepared: {list(attr.keys())}")

    try:
        logger.info(f"[LDAP] Connecting to server: {LDAP_SERVER}")
        logger.debug(f"[LDAP] Admin DN: {LDAP_ADMIN_DN}")
        logger.debug(f"[LDAP] Admin password: {'[SET]' if LDAP_ADMIN_PASSWORD else '[NOT SET]'}")
        
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        logger.info(f"[LDAP] Connection established successfully")
        
        logger.info(f"[LDAP] Adding user to LDAP: {dn}")
        conn.add(dn, attributes=attr)

        result_description = conn.result.get("description", "unknown")
        result_code = conn.result.get("result", -1)
        
        if result_description != "success":
            logger.error(f"[LDAP] Add user failed!")
            logger.error(f"[LDAP] Result code: {result_code}")
            logger.error(f"[LDAP] Result description: {result_description}")
            logger.error(f"[LDAP] Full result: {conn.result}")
            logger.error(f"[LDAP] Message: {conn.result.get('message', 'No message')}")
            logger.error(f"[LDAP] DN: {dn}")
            raise Exception(f"LDAP add failed: {result_description} (code: {result_code})")

        logger.info(f"[LDAP] User {username} added successfully to LDAP")
        conn.unbind()
        logger.info(f"[LDAP] User {username} created with wireguardEnabled=FALSE, max_devices={max_devices}")
        return True

    except ldap3.core.exceptions.LDAPException as e:
        logger.error(f"[LDAP] LDAP exception for {username}: {type(e).__name__}: {e}")
        logger.error(f"[LDAP] Exception details: {str(e)}")
        if hasattr(e, 'result'):
            logger.error(f"[LDAP] LDAP result: {e.result}")
        return False
    except Exception as e:
        logger.error(f"[LDAP] Unexpected error creating user {username}: {e}", exc_info=True)
        logger.error(f"[LDAP] Error type: {type(e).__name__}")
        return False


@router.post("/add-user")
def admin_add_user(data: dict, request: Request):
    """
    Admin add user ke LDAP
    User dibuat dengan wireguardEnabled = FALSE (default)
    User harus enable VPN access dan add device sendiri setelah login
    
    ⚠️ SECURITY WARNING: If ALLOW_NO_AUTH_ADD_USER=true, this endpoint
    can be accessed without authentication. Use only for initial setup
    or development. NOT RECOMMENDED for production!
    """
    # Conditional auth check
    if not ALLOW_NO_AUTH_ADD_USER:
        verify_jwt_admin(request)  # Verify admin access
    else:
        # Log warning if auth is disabled
        if ENVIRONMENT == "production":
            logger.warning("⚠️ SECURITY RISK: /admin/add-user accessed without auth in PRODUCTION!")
        else:
            logger.info("ℹ️ /admin/add-user accessed without auth (ALLOW_NO_AUTH_ADD_USER=true)")
    
    username = data.get("username")
    password = data.get("password")
    max_devices = data.get("max_devices", 3)  # Default 3 devices

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username/password")

    # Validate username (alphanumeric + underscore, max 50 chars)
    if not username.replace("_", "").isalnum() or len(username) > 50:
        raise HTTPException(status_code=400, detail="Invalid username format")

    # Validate max_devices
    try:
        max_devices = int(max_devices)
        if max_devices < 1 or max_devices > 10:
            raise HTTPException(status_code=400, detail="max_devices must be between 1 and 10")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="max_devices must be a number")

    # Check if user already exists
    logger.info(f"[ADD-USER] Checking if user '{username}' already exists")
    existing_user = get_user_attributes(username, ['uid'])
    if existing_user:
        logger.warning(f"[ADD-USER] User '{username}' already exists in LDAP")
        raise HTTPException(status_code=400, detail=f"User {username} already exists")
    logger.info(f"[ADD-USER] User '{username}' does not exist, proceeding with creation")

    # Generate uid_number (simple increment, bisa diperbaiki nanti)
    # Untuk sekarang, kita bisa query LDAP untuk get next uid_number
    uid_number = 2000  # Default, bisa di-improve dengan query LDAP untuk get max uidNumber
    logger.debug(f"[ADD-USER] Using uid_number: {uid_number}")

    # Tambah user ke LDAP dengan wireguardEnabled = FALSE
    logger.info(f"[ADD-USER] Calling ldap_add_user for '{username}'")
    ok = ldap_add_user(username, password, uid_number, max_devices)

    if not ok:
        logger.error(f"[ADD-USER] Failed to create user '{username}' in LDAP")
        raise HTTPException(status_code=500, detail="Failed to create LDAP user. Check server logs for details.")

    logger.info(f"User {username} created by admin. wireguardEnabled=FALSE, max_devices={max_devices}")

    return {
        "status": "ok",
        "message": f"User {username} created in LDAP",
        "username": username,
        "wireguard_enabled": False,
        "max_devices": max_devices,
        "note": "User must enable VPN access and add device after login"
    }
