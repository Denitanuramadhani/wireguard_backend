import subprocess
from fastapi import APIRouter, HTTPException, Request
from app.middleware.auth_middleware import verify_jwt_admin
from app.config import (
    LDAP_SERVER, LDAP_BASE_DN, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD,
    ALLOW_NO_AUTH_ADD_USER, ENVIRONMENT
)
from app.database.connection import get_db_connection
from app.logger import logger
from app.security.password_hasher import hash_password
from app.config import PASSWORD_HASHER
import ldap3
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])

# Base DN untuk users dan groups OU
LDAP_USERS_BASE = f"ou=users,{LDAP_BASE_DN}"
LDAP_GROUPS_BASE = f"ou=groups,{LDAP_BASE_DN}"
WIREGUARD_GROUP_DN = f"cn=wireguard,{LDAP_GROUPS_BASE}"

# UID Number starting point jika belum ada user
UID_NUMBER_START = 1000


def get_wireguard_gid_number() -> int:
    """
    Ambil gidNumber dari group cn=wireguard,ou=groups,dc=wireguard,dc=local
    Return gidNumber dari group, atau None jika group tidak ditemukan
    
    Menggunakan admin DN untuk bind
    """
    logger.debug(f"[LDAP] Getting gidNumber from group: {WIREGUARD_GROUP_DN}")
    
    try:
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        
        # Search group wireguard di ou=groups
        conn.search(
            search_base=LDAP_GROUPS_BASE,
            search_filter="(cn=wireguard)",
            attributes=['gidNumber']
        )
        
        if not conn.entries:
            logger.error(f"[LDAP] Group {WIREGUARD_GROUP_DN} not found")
            conn.unbind()
            return None
        
        entry = conn.entries[0]
        
        # Extract gidNumber
        gid_number = None
        if hasattr(entry, 'gidNumber'):
            gid_attr = entry.gidNumber
            if hasattr(gid_attr, 'value'):
                gid_number = gid_attr.value
            else:
                gid_number = gid_attr
        elif 'gidNumber' in entry.entry_attributes:
            gid_number = entry['gidNumber']
        
        conn.unbind()
        
        if gid_number:
            try:
                gid_int = int(gid_number) if not isinstance(gid_number, list) else int(gid_number[0])
                logger.info(f"[LDAP] Found gidNumber: {gid_int} from group wireguard")
                return gid_int
            except (ValueError, TypeError) as e:
                logger.error(f"[LDAP] Invalid gidNumber in group: {gid_number}, error: {e}")
                return None
        
        logger.error(f"[LDAP] gidNumber not found in group {WIREGUARD_GROUP_DN}")
        return None
        
    except ldap3.core.exceptions.LDAPException as e:
        logger.error(f"[LDAP] LDAP exception getting gidNumber: {type(e).__name__}: {e}")
        if hasattr(e, 'result'):
            logger.error(f"[LDAP] LDAP result: {e.result}")
        return None
    except Exception as e:
        logger.error(f"[LDAP] Unexpected error getting gidNumber: {e}", exc_info=True)
        return None


def get_next_uid_number() -> int:
    """
    Query LDAP untuk mendapatkan uidNumber terbesar dari ou=users
    Return uidNumber berikutnya (max + 1)
    Jika belum ada user, return UID_NUMBER_START (1000)
    
    Menggunakan admin DN untuk bind
    """
    logger.debug("[LDAP] Getting next uidNumber from LDAP")
    
    try:
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        
        # Search di ou=users untuk semua user dengan uidNumber
        search_base = LDAP_USERS_BASE
        search_filter = "(uidNumber=*)"
        
        logger.debug(f"[LDAP] Searching for uidNumber in: {search_base}")
        
        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=['uidNumber']
        )
        
        # Extract semua uidNumber
        uid_numbers = []
        if conn.entries:
            for entry in conn.entries:
                uid_number = None
                if hasattr(entry, 'uidNumber'):
                    uid_attr = entry.uidNumber
                    if hasattr(uid_attr, 'value'):
                        uid_number = uid_attr.value
                    else:
                        uid_number = uid_attr
                elif 'uidNumber' in entry.entry_attributes:
                    uid_number = entry['uidNumber']
                
                if uid_number:
                    try:
                        if isinstance(uid_number, list):
                            for uid in uid_number:
                                uid_numbers.append(int(uid))
                        else:
                            uid_numbers.append(int(uid_number))
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[LDAP] Invalid uidNumber found: {uid_number}, skipping: {e}")
        
        conn.unbind()
        
        # Jika tidak ada user, mulai dari UID_NUMBER_START
        if not uid_numbers:
            logger.info(f"[LDAP] No users found, starting uidNumber from {UID_NUMBER_START}")
            return UID_NUMBER_START
        
        # Cari max dan return max + 1
        max_uid = max(uid_numbers)
        next_uid = max_uid + 1
        logger.info(f"[LDAP] Max uidNumber found: {max_uid}, next uidNumber: {next_uid}")
        return next_uid
        
    except ldap3.core.exceptions.LDAPException as e:
        logger.error(f"[LDAP] LDAP exception getting next uidNumber: {type(e).__name__}: {e}")
        if hasattr(e, 'result'):
            logger.error(f"[LDAP] LDAP result: {e.result}")
        logger.warning(f"[LDAP] Falling back to default uidNumber: {UID_NUMBER_START}")
        return UID_NUMBER_START
    except Exception as e:
        logger.error(f"[LDAP] Unexpected error getting next uidNumber: {e}", exc_info=True)
        logger.warning(f"[LDAP] Falling back to default uidNumber: {UID_NUMBER_START}")
        return UID_NUMBER_START


def check_ldap_user_exists(username: str) -> bool:
    """
    Cek apakah user dengan cn sudah ada di ou=users
    Return True jika user sudah ada, False jika belum ada
    
    Menggunakan admin DN untuk bind
    """
    logger.debug(f"[LDAP] Checking if user '{username}' exists")
    
    try:
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        
        # Search user berdasarkan cn
        search_base = LDAP_USERS_BASE
        search_filter = f"(cn={username})"
        
        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=['cn']
        )
        
        exists = len(conn.entries) > 0
        conn.unbind()
        
        if exists:
            logger.info(f"[LDAP] User '{username}' already exists in LDAP")
        else:
            logger.debug(f"[LDAP] User '{username}' does not exist")
        
        return exists
        
    except ldap3.core.exceptions.LDAPException as e:
        logger.error(f"[LDAP] LDAP exception checking user: {type(e).__name__}: {e}")
        if hasattr(e, 'result'):
            logger.error(f"[LDAP] LDAP result: {e.result}")
        # Jika error, assume user tidak ada (lebih aman)
        return False
    except Exception as e:
        logger.error(f"[LDAP] Unexpected error checking user: {e}", exc_info=True)
        return False


def create_ldap_user(username: str, password: str, uid_number: int, gid_number: int) -> bool:
    """
    Create user di LDAP dengan password SSHA hash
    
    Args:
        username: Username untuk user baru (cn)
        password: Plain text password (akan di-hash)
        uid_number: UID Number untuk user (harus unik)
        gid_number: GID Number dari group wireguard
    
    Returns:
        True jika berhasil, False jika gagal
    """
    logger.info(f"[LDAP] Starting user creation for: {username}")
    logger.debug(f"[LDAP] Parameters - uid_number: {uid_number}, gid_number: {gid_number}")
    
    # Hash password via slappasswd
#    logger.debug(f"[LDAP] Hashing password for user: {username}")
#    try:
#        hashed_pass = subprocess.check_output(
#            ["slappasswd", "-s", password]
#        ).decode().strip()
#        logger.debug(f"[LDAP] Password hashed successfully (length: {len(hashed_pass)})")
#    except FileNotFoundError:
#        logger.error(f"[LDAP] slappasswd command not found! Make sure openldap-utils is installed")
#        return False
#    except subprocess.CalledProcessError as e:
#        logger.error(f"[LDAP] Error hashing password (exit code {e.returncode}): {e}")#
#        return False
#    except Exception as e:
#        logger.error(f"[LDAP] Unexpected error hashing password: {e}", exc_info=True)
#        return False

    # Hash password (auto: slappasswd → python SSHA fallback)
    logger.info(f"[LDAP] Hashing password for user: {username} (mode: {PASSWORD_HASHER})")
    try:
        hashed_pass = hash_password(password, PASSWORD_HASHER)
        logger.info(f"[LDAP] Password hashed successfully (hash length: {len(hashed_pass)}, prefix: {hashed_pass[:10]}...)")
    except Exception as e:
        logger.error(f"[LDAP] Failed to hash password: {e}", exc_info=True)
        return False

    # DN structure: cn=<username>,ou=users,dc=wireguard,dc=local
    dn = f"cn={username},{LDAP_USERS_BASE}"
    logger.debug(f"[LDAP] User DN: {dn}")

    # Attributes dengan objectClass yang diperlukan
    attr = {
        "objectClass": [
            "inetOrgPerson",
            "posixAccount",
            "shadowAccount"
        ],
        "cn": username,
        "sn": username,
        "uid": username,
        "uidNumber": str(uid_number),
        "gidNumber": str(gid_number),
        "homeDirectory": f"/home/{username}",
        "loginShell": "/bin/bash",
        "userPassword": hashed_pass
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
        logger.info(f"[LDAP] User {username} created with uidNumber={uid_number}, gidNumber={gid_number}")
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


def insert_user_to_mysql(username: str, role: str = "user") -> bool:
    """
    Insert data user ke MySQL setelah LDAP user berhasil dibuat
    Hanya menyimpan: username, role, created_at
    TIDAK menyimpan password (tetap di LDAP)
    
    Args:
        username: Username dari LDAP
        role: Role user (default: "user")
    
    Returns:
        True jika berhasil, False jika gagal
    """
    logger.info(f"[MySQL] Inserting user '{username}' to MySQL")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Cek apakah tabel users ada
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'users'
            """)
            table_exists = cursor.fetchone()['count'] > 0
            
            if not table_exists:
                logger.warning(f"[MySQL] Table 'users' does not exist, skipping MySQL insert")
                logger.info(f"[MySQL] User data will be stored only in LDAP")
                return True  # Tidak error, hanya skip
            
            # Cek apakah user sudah ada
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing = cursor.fetchone()
            
            if existing:
                logger.warning(f"[MySQL] User '{username}' already exists in MySQL, skipping insert")
                return True  # Tidak error, hanya skip
            
            # Insert user baru
            cursor.execute("""
                INSERT INTO users (username, role, created_at)
                VALUES (%s, %s, %s)
            """, (username, role, datetime.now()))
            
            conn.commit()
            logger.info(f"[MySQL] User '{username}' inserted successfully to MySQL")
            return True
            
    except Exception as e:
        logger.error(f"[MySQL] Error inserting user to MySQL: {e}", exc_info=True)
        # Jangan raise error, karena user sudah dibuat di LDAP
        # MySQL insert adalah opsional
        return False


@router.post("/add-user")
def admin_add_user(data: dict, request: Request):
    """
    """
    # Conditional auth check
    if not ALLOW_NO_AUTH_ADD_USER:
        verify_jwt_admin(request)  # Verify admin access
    else:
        # Log warning if auth is disabled
        if ENVIRONMENT == "production":
            logger.warning("SECURITY RISK: /admin/add-user accessed without auth in PRODUCTION!")
        else:
            logger.info("/admin/add-user accessed without auth (ALLOW_NO_AUTH_ADD_USER=true)")
    
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "user")  # Default role: user

    if not username or not password:
        raise HTTPException(status_code=400, detail="Missing username/password")

    # Validate username (alphanumeric + underscore, max 50 chars)
    if not username.replace("_", "").isalnum() or len(username) > 50:
        raise HTTPException(status_code=400, detail="Invalid username format")

    # Validate role
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    # Step 1: Bind sebagai LDAP admin dan ambil gidNumber dari group wireguard
    logger.info(f"[ADD-USER] Step 1: Getting gidNumber from group wireguard")
    gid_number = get_wireguard_gid_number()
    
    if gid_number is None:
        logger.error(f"[ADD-USER] Failed to get gidNumber from group wireguard")
        raise HTTPException(
            status_code=500, 
            detail="Failed to get gidNumber from wireguard group. Please ensure the group exists in LDAP."
        )
    
    logger.info(f"[ADD-USER] Got gidNumber: {gid_number}")

    # Step 2: Cek apakah user sudah ada
    logger.info(f"[ADD-USER] Step 2: Checking if user '{username}' already exists")
    if check_ldap_user_exists(username):
        logger.warning(f"[ADD-USER] User '{username}' already exists in LDAP")
        raise HTTPException(status_code=400, detail=f"User {username} already exists")
    
    logger.info(f"[ADD-USER] User '{username}' does not exist, proceeding with creation")

    # Step 3: Get next uidNumber
    logger.info(f"[ADD-USER] Step 3: Getting next uidNumber from LDAP")
    uid_number = get_next_uid_number()
    logger.info(f"[ADD-USER] Using uid_number: {uid_number}")

    # Step 4: Create LDAP user
    logger.info(f"[ADD-USER] Step 4: Creating LDAP user for '{username}'")
    ldap_success = create_ldap_user(username, password, uid_number, gid_number)

    if not ldap_success:
        logger.error(f"[ADD-USER] Failed to create user '{username}' in LDAP")
        raise HTTPException(status_code=500, detail="Failed to create LDAP user. Check server logs for details.")

    logger.info(f"[ADD-USER] LDAP user '{username}' created successfully")

    # Step 5: Insert user ke MySQL (opsional, tidak critical)
    logger.info(f"[ADD-USER] Step 5: Inserting user '{username}' to MySQL")
    mysql_success = insert_user_to_mysql(username, role)
    
    if not mysql_success:
        logger.warning(f"[ADD-USER] Failed to insert user '{username}' to MySQL, but LDAP user was created successfully")
        # Tidak raise error karena user sudah dibuat di LDAP
        # MySQL insert adalah opsional

    logger.info(f"User {username} created successfully. LDAP: OK, MySQL: {'OK' if mysql_success else 'SKIPPED'}")

    return {
        "status": "ok",
        "message": f"User {username} created successfully",
        "username": username,
        "uid_number": uid_number,
        "gid_number": gid_number,
        "role": role,
        "ldap_created": True,
        "mysql_created": mysql_success
    }
