#!/usr/bin/env python3
"""
Script untuk sync existing LDAP users ke MySQL users table
- Query semua users dari LDAP
- Insert ke MySQL dengan role default 'user'
- Jika user di LDAP group 'admins', set role 'admin'
- Skip jika user sudah ada di MySQL
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ldap3 import Server, Connection, ALL
from app.config import (
    LDAP_SERVER, LDAP_BASE_DN,
    LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD
)

# Base DN untuk users (sama seperti di admin_add_user.py)
LDAP_USERS_BASE = f"ou=users,{LDAP_BASE_DN}"
from app.database.connection import get_db_connection
from app.core.ldap_client import check_user_in_group
from app.logger import logger
from datetime import datetime


def get_all_ldap_users():
    """
    Get semua users dari LDAP
    Returns list of usernames
    """
    logger.info("[SYNC] Fetching all users from LDAP...")
    
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        
        # Search di ou=users untuk semua users
        search_base = LDAP_USERS_BASE
        search_filter = "(uid=*)"
        
        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=['uid']
        )
        
        usernames = []
        if conn.entries:
            for entry in conn.entries:
                try:
                    uid = str(entry['uid']) if 'uid' in entry else None
                    if uid:
                        usernames.append(uid)
                except Exception as e:
                    logger.warning(f"[SYNC] Error extracting uid from entry: {e}")
                    continue
        
        conn.unbind()
        logger.info(f"[SYNC] Found {len(usernames)} users in LDAP")
        return usernames
        
    except Exception as e:
        logger.error(f"[SYNC] Error fetching users from LDAP: {e}", exc_info=True)
        return []


def get_user_role_from_ldap(username: str) -> str:
    """
    Check apakah user di LDAP group 'admins'
    Returns 'admin' jika ya, 'user' jika tidak
    """
    try:
        admin_group_dn = f"cn=admins,ou=groups,{LDAP_BASE_DN}"
        is_admin = check_user_in_group(username, admin_group_dn)
        return 'admin' if is_admin else 'user'
    except Exception as e:
        logger.debug(f"[SYNC] Error checking LDAP group for {username}: {e}")
        return 'user'  # Default to 'user' if error


def sync_user_to_mysql(username: str, role: str = None):
    """
    Sync single user ke MySQL
    - Check apakah sudah ada
    - Insert jika belum ada
    - Update role jika berbeda (optional)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Cek apakah user sudah ada
            cursor.execute("SELECT id, role FROM users WHERE username = %s", (username,))
            existing = cursor.fetchone()
            
            if existing:
                existing_role = existing.get('role')
                if role and role != existing_role:
                    # Update role jika berbeda
                    cursor.execute(
                        "UPDATE users SET role = %s, updated_at = %s WHERE username = %s",
                        (role, datetime.now(), username)
                    )
                    conn.commit()
                    logger.info(f"[SYNC] Updated user '{username}' role: {existing_role} -> {role}")
                else:
                    logger.debug(f"[SYNC] User '{username}' already exists in MySQL, skipping")
                return True
            
            # Insert user baru
            if not role:
                role = get_user_role_from_ldap(username)
            
            cursor.execute("""
                INSERT INTO users (username, role, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
            """, (username, role, datetime.now(), datetime.now()))
            
            conn.commit()
            logger.info(f"[SYNC] Inserted user '{username}' with role '{role}' to MySQL")
            return True
            
    except Exception as e:
        logger.error(f"[SYNC] Error syncing user '{username}' to MySQL: {e}", exc_info=True)
        return False


def main():
    """
    Main function untuk sync semua LDAP users ke MySQL
    """
    print("=" * 60)
    print("Starting LDAP to MySQL users sync...")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info("Starting LDAP to MySQL users sync...")
    logger.info("=" * 60)
    
    # Get all LDAP users
    ldap_users = get_all_ldap_users()
    
    if not ldap_users:
        logger.warning("[SYNC] No users found in LDAP")
        return
    
    logger.info(f"[SYNC] Processing {len(ldap_users)} users...")
    
    # Sync each user
    synced = 0
    skipped = 0
    failed = 0
    
    for username in ldap_users:
        try:
            # Get role from LDAP (check admin group)
            role = get_user_role_from_ldap(username)
            
            # Check if already exists
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                exists = cursor.fetchone() is not None
            
            if exists:
                skipped += 1
                logger.debug(f"[SYNC] User '{username}' already exists, skipping")
            else:
                if sync_user_to_mysql(username, role):
                    synced += 1
                else:
                    failed += 1
                    
        except Exception as e:
            logger.error(f"[SYNC] Error processing user '{username}': {e}", exc_info=True)
            failed += 1
    
    # Summary
    print("=" * 60)
    print("Sync Summary:")
    print(f"  Total LDAP users: {len(ldap_users)}")
    print(f"  Synced (new): {synced}")
    print(f"  Skipped (existing): {skipped}")
    print(f"  Failed: {failed}")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info("Sync Summary:")
    logger.info(f"  Total LDAP users: {len(ldap_users)}")
    logger.info(f"  Synced (new): {synced}")
    logger.info(f"  Skipped (existing): {skipped}")
    logger.info(f"  Failed: {failed}")
    logger.info("=" * 60)
    
    if failed > 0:
        print(f"[SYNC] {failed} user(s) failed to sync. Check logs for details.")
        logger.warning(f"[SYNC] {failed} user(s) failed to sync. Check logs for details.")
        sys.exit(1)
    else:
        print("[SYNC] All users synced successfully!")
        logger.info("[SYNC] All users synced successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()

