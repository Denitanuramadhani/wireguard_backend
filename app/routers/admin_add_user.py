import subprocess
from fastapi import APIRouter, HTTPException, Request
from app.middleware.auth_middleware import verify_jwt_admin
from app.config import LDAP_SERVER, LDAP_BASE_DN, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD
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
    # Hash password via slappasswd
    try:
        hashed_pass = subprocess.check_output(
            ["slappasswd", "-s", password]
        ).decode().strip()
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        return False

    dn = f"uid={username},{LDAP_BASE_PEOPLE}"

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

    try:
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        
        conn.add(dn, attributes=attr)

        if not conn.result["description"] == "success":
            logger.error(f"LDAP add user failed: {conn.result}")
            raise Exception(conn.result)

        conn.unbind()
        logger.info(f"User {username} created in LDAP with wireguardEnabled=FALSE")
        return True

    except Exception as e:
        logger.error(f"LDAP CREATE ERROR for {username}: {e}")
        return False


@router.post("/add-user")
def admin_add_user(data: dict, request: Request):
    """
    Admin add user ke LDAP
    User dibuat dengan wireguardEnabled = FALSE (default)
    User harus enable VPN access dan add device sendiri setelah login
    """
    verify_jwt_admin(request)  # Verify admin access
    
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
    existing_user = get_user_attributes(username, ['uid'])
    if existing_user:
        raise HTTPException(status_code=400, detail=f"User {username} already exists")

    # Generate uid_number (simple increment, bisa diperbaiki nanti)
    # Untuk sekarang, kita bisa query LDAP untuk get next uid_number
    uid_number = 2000  # Default, bisa di-improve dengan query LDAP untuk get max uidNumber

    # Tambah user ke LDAP dengan wireguardEnabled = FALSE
    ok = ldap_add_user(username, password, uid_number, max_devices)

    if not ok:
        raise HTTPException(status_code=500, detail="Failed to create LDAP user")

    logger.info(f"User {username} created by admin. wireguardEnabled=FALSE, max_devices={max_devices}")

    return {
        "status": "ok",
        "message": f"User {username} created in LDAP",
        "username": username,
        "wireguard_enabled": False,
        "max_devices": max_devices,
        "note": "User must enable VPN access and add device after login"
    }
