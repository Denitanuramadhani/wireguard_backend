import subprocess
import json
from fastapi import APIRouter, HTTPException
from app.middleware.auth_middleware import verify_jwt_admin
from app.wg.generator import generate_client_config, save_config, add_peer_to_wg, generate_qr
from app.wg.ip_manager import allocate_ip
import ldap3
import os

router = APIRouter(prefix="/admin", tags=["Admin"])


LDAP_ADMIN_DN = "cn=admin,dc=example,dc=com"
LDAP_ADMIN_PASS = "_l3Rum*Foca"  # ganti sesuai LDAP kamu
LDAP_BASE_PEOPLE = "ou=people,dc=example,dc=com"
LDAP_SERVER = "ldap://127.0.0.1:389"


def ldap_add_user(username: str, password: str, uid_number: int):
    """
    Tambah user ke LDAP dengan password SSHA hash
    """
    # Hash password via slappasswd
    hashed_pass = subprocess.check_output(
        ["slappasswd", "-s", password]
    ).decode().strip()

    dn = f"uid={username},{LDAP_BASE_PEOPLE}"

    attr = {
        "objectClass": [
            "inetOrgPerson", "organizationalPerson",
            "person", "posixAccount", "top"
        ],
        "cn": username,
        "sn": username,
        "uid": username,
        "uidNumber": str(uid_number),
        "gidNumber": str(uid_number),
        "homeDirectory": f"/home/{username}",
        "loginShell": "/bin/bash",
        "userPassword": hashed_pass
    }

    try:
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(server, LDAP_ADMIN_DN, LDAP_ADMIN_PASS, auto_bind=True)
        conn.add(dn, attributes=attr)

        if not conn.result["description"] == "success":
            raise Exception(conn.result)

        conn.unbind()
        return True

    except Exception as e:
        print("LDAP CREATE ERROR:", e)
        return False


@router.post("/add-user")
def admin_add_user(data: dict):
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username/password")

    # 1. Tambah user ke LDAP
    uid_number = 2000 + len(os.listdir("generated_configs"))
    ok = ldap_add_user(username, password, uid_number)

    if not ok:
        raise HTTPException(status_code=500, detail="Failed create LDAP user")

    # 2. Allocate IP
    client_ip = allocate_ip(username)

    # 3. Generate WireGuard config
    result = generate_client_config(username, client_ip)

    # 4. Add peer to server
    add_peer_to_wg(result["public_key"], f"{client_ip}/32")

    # 5. Save config + QR
    save_config(username, result["config"])
    generate_qr(username, result["config"])

    return {
        "status": "ok",
        "message": f"User {username} created in LDAP & WireGuard",
        "ip": client_ip,
        "public_key": result["public_key"]
    }
