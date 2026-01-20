#!/usr/bin/env python3
"""
Script untuk test koneksi LDAP dengan detail lengkap
Digunakan untuk debugging masalah koneksi LDAP
"""

import sys
import os
import subprocess

# Add parent directory to path untuk import app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import (
    LDAP_SERVER, LDAP_BASE_DN, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD,
    LDAP_USERS_BASE, LDAP_GROUPS_BASE
)
import ldap3

def print_section(title):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_success(msg):
    """Print success message"""
    print(f"✅ {msg}")

def print_error(msg):
    """Print error message"""
    print(f"❌ {msg}")

def print_info(msg):
    """Print info message"""
    print(f"ℹ️  {msg}")

def print_warning(msg):
    """Print warning message"""
    print(f"⚠️  {msg}")

def test_ldap_config():
    """Test dan tampilkan konfigurasi LDAP"""
    print_section("LDAP Configuration")
    print_info(f"LDAP_SERVER: {LDAP_SERVER}")
    print_info(f"LDAP_BASE_DN: {LDAP_BASE_DN}")
    print_info(f"LDAP_ADMIN_DN: {LDAP_ADMIN_DN}")
    print_info(f"LDAP_ADMIN_PASSWORD: {'[SET]' if LDAP_ADMIN_PASSWORD else '[NOT SET]'}")
    print_info(f"LDAP_USERS_BASE: {LDAP_USERS_BASE}")
    print_info(f"LDAP_GROUPS_BASE: {LDAP_GROUPS_BASE}")

def test_slappasswd():
    """Test apakah slappasswd tersedia"""
    print_section("Testing slappasswd")
    try:
        result = subprocess.run(
            ["slappasswd", "-h"],
            capture_output=True,
            timeout=5,
            text=True
        )
        if result.returncode == 0 or "slappasswd" in result.stderr or "slappasswd" in result.stdout:
            print_success("slappasswd command is available")
            return True
        else:
            print_error("slappasswd command not found")
            return False
    except FileNotFoundError:
        print_error("slappasswd command not found!")
        print_warning("Please install openldap-utils:")
        print_warning("  Ubuntu/Debian: sudo apt-get install openldap-utils")
        print_warning("  CentOS/RHEL: sudo yum install openldap-clients")
        return False
    except Exception as e:
        print_error(f"Error testing slappasswd: {e}")
        return False

def test_ldap_connection():
    """Test koneksi LDAP dengan admin credentials"""
    print_section("Testing LDAP Connection")
    
    if not LDAP_ADMIN_PASSWORD:
        print_error("LDAP_ADMIN_PASSWORD is not set!")
        return False
    
    try:
        print_info(f"Connecting to {LDAP_SERVER}...")
        print_info(f"Using admin DN: {LDAP_ADMIN_DN}")
        
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        
        print_success("LDAP connection successful!")
        print_info(f"Server info: {server.info}")
        
        # Test search base DN
        print_info(f"Testing base DN: {LDAP_BASE_DN}")
        conn.search(
            search_base=LDAP_BASE_DN,
            search_filter="(objectClass=*)",
            search_scope=ldap3.BASE,
            attributes=['*']
        )
        
        if conn.entries:
            print_success(f"Base DN '{LDAP_BASE_DN}' exists")
            print_info(f"Found {len(conn.entries)} entries")
        else:
            print_warning(f"Base DN '{LDAP_BASE_DN}' not found or empty")
        
        conn.unbind()
        return True
        
    except ldap3.core.exceptions.LDAPSocketOpenError as e:
        print_error(f"Failed to connect to LDAP server: {e}")
        print_warning("Possible causes:")
        print_warning("  - LDAP server is not running")
        print_warning("  - Wrong LDAP_SERVER address")
        print_warning("  - Firewall blocking port 389")
        return False
        
    except ldap3.core.exceptions.LDAPBindError as e:
        print_error(f"LDAP bind failed: {e}")
        print_warning("Possible causes:")
        print_warning("  - Wrong LDAP_ADMIN_DN")
        print_warning("  - Wrong LDAP_ADMIN_PASSWORD")
        print_warning("  - Admin account is locked or disabled")
        return False
        
    except ldap3.core.exceptions.LDAPException as e:
        print_error(f"LDAP error: {type(e).__name__}: {e}")
        if hasattr(e, 'result'):
            print_error(f"LDAP result: {e.result}")
        return False
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ldap_structure():
    """Test struktur LDAP (OU, groups, dll)"""
    print_section("Testing LDAP Structure")
    
    if not LDAP_ADMIN_PASSWORD:
        print_error("LDAP_ADMIN_PASSWORD is not set!")
        return False
    
    try:
        server = ldap3.Server(LDAP_SERVER)
        conn = ldap3.Connection(
            server,
            user=LDAP_ADMIN_DN,
            password=LDAP_ADMIN_PASSWORD,
            auto_bind=True
        )
        
        # Test ou=users
        print_info(f"Testing OU: {LDAP_USERS_BASE}")
        conn.search(
            search_base=LDAP_USERS_BASE,
            search_filter="(objectClass=*)",
            search_scope=ldap3.BASE,
            attributes=['*']
        )
        
        if conn.entries:
            print_success(f"OU '{LDAP_USERS_BASE}' exists")
            # Count users
            conn.search(
                search_base=LDAP_USERS_BASE,
                search_filter="(objectClass=*)",
                attributes=['cn']
            )
            user_count = len(conn.entries)
            print_info(f"Found {user_count} entries in ou=users")
        else:
            print_warning(f"OU '{LDAP_USERS_BASE}' not found")
            print_warning("You may need to create this OU first")
        
        # Test ou=groups
        print_info(f"Testing OU: {LDAP_GROUPS_BASE}")
        conn.search(
            search_base=LDAP_GROUPS_BASE,
            search_filter="(objectClass=*)",
            search_scope=ldap3.BASE,
            attributes=['*']
        )
        
        if conn.entries:
            print_success(f"OU '{LDAP_GROUPS_BASE}' exists")
        else:
            print_warning(f"OU '{LDAP_GROUPS_BASE}' not found")
            print_warning("You may need to create this OU first")
        
        # Test group wireguard
        wireguard_group_dn = f"cn=wireguard,{LDAP_GROUPS_BASE}"
        print_info(f"Testing group: {wireguard_group_dn}")
        conn.search(
            search_base=LDAP_GROUPS_BASE,
            search_filter="(cn=wireguard)",
            attributes=['gidNumber', 'cn']
        )
        
        if conn.entries:
            print_success(f"Group 'cn=wireguard' exists")
            entry = conn.entries[0]
            
            # Get gidNumber
            gid_number = None
            if hasattr(entry, 'gidNumber'):
                gid_attr = entry.gidNumber
                if hasattr(gid_attr, 'value'):
                    gid_number = gid_attr.value
                else:
                    gid_number = gid_attr
            elif 'gidNumber' in entry.entry_attributes:
                gid_number = entry['gidNumber']
            
            if gid_number:
                print_success(f"Group gidNumber: {gid_number}")
            else:
                print_warning("Group 'cn=wireguard' does not have gidNumber attribute")
                print_warning("You need to add gidNumber to the group")
        else:
            print_error(f"Group 'cn=wireguard' not found!")
            print_warning("You need to create this group first:")
            print_warning(f"  DN: {wireguard_group_dn}")
            print_warning("  objectClass: posixGroup")
            print_warning("  gidNumber: 2000 (or your preferred GID)")
        
        conn.unbind()
        return True
        
    except ldap3.core.exceptions.LDAPException as e:
        print_error(f"LDAP error: {type(e).__name__}: {e}")
        if hasattr(e, 'result'):
            print_error(f"LDAP result: {e.result}")
        return False
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("\n" + "="*60)
    print("  LDAP Connection Test Script")
    print("="*60)
    
    # Test configuration
    test_ldap_config()
    
    # Test slappasswd
    slappasswd_ok = test_slappasswd()
    
    # Test LDAP connection
    ldap_ok = test_ldap_connection()
    
    # Test LDAP structure
    structure_ok = False
    if ldap_ok:
        structure_ok = test_ldap_structure()
    
    # Summary
    print_section("Summary")
    
    if slappasswd_ok:
        print_success("slappasswd: OK")
    else:
        print_error("slappasswd: FAILED")
    
    if ldap_ok:
        print_success("LDAP Connection: OK")
    else:
        print_error("LDAP Connection: FAILED")
    
    if structure_ok:
        print_success("LDAP Structure: OK")
    else:
        print_error("LDAP Structure: FAILED")
    
    if slappasswd_ok and ldap_ok and structure_ok:
        print("\n✅ All tests passed! LDAP is ready to use.")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
