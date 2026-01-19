#!/bin/bash

# ============================================
# LDAP Users Migration Script
# WireGuard VPN Portal Backend
# ============================================
#
# Script untuk migrate existing LDAP users dengan wireguardUser objectClass
# Safe to run multiple times (idempotent)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"

# Load .env file if exists (from project root)
# Safely load environment variables from .env file
if [ -f "$ENV_FILE" ]; then
    # Read .env file line by line and export variables
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Export variable (handle values with spaces and special chars)
        if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            var_name="${BASH_REMATCH[1]}"
            var_value="${BASH_REMATCH[2]}"
            # Remove quotes if present
            var_value="${var_value#\"}"
            var_value="${var_value%\"}"
            var_value="${var_value#\'}"
            var_value="${var_value%\'}"
            # Trim whitespace
            var_value="${var_value#"${var_value%%[![:space:]]*}"}"
            var_value="${var_value%"${var_value##*[![:space:]]}"}"
            export "$var_name=$var_value"
        fi
    done < "$ENV_FILE"
fi

# Configuration (can be overridden by environment variables)
# Default values match app/config.py
LDAP_SERVER=${LDAP_SERVER:-"ldap://117.53.44.59:389"}
LDAP_BASE_DN=${LDAP_BASE_DN:-"dc=wireguard,dc=local"}
LDAP_USER_DN=${LDAP_USER_DN:-"uid={},ou=people,dc=wireguard,dc=local"}
LDAP_ADMIN_DN=${LDAP_ADMIN_DN:-"cn=admin,dc=wireguard,dc=local"}
LDAP_ADMIN_PASSWORD=${LDAP_ADMIN_PASSWORD:-"123"}

# Derive LDAP_BASE_PEOPLE from LDAP_USER_DN or use default
# LDAP_USER_DN format: uid={},ou=people,dc=example,dc=com
if [[ "$LDAP_USER_DN" == *"ou=users"* ]]; then
    # Extract ou=people,dc=... from LDAP_USER_DN (remove uid={}, prefix)
    LDAP_BASE_PEOPLE=$(echo "$LDAP_USER_DN" | sed -E 's/^[^,]+,//' | sed 's/{},//')
else
    LDAP_BASE_PEOPLE=${LDAP_BASE_PEOPLE:-"ou=users,${LDAP_BASE_DN}"}
fi

WIREGUARD_ENABLED_DEFAULT=${WIREGUARD_ENABLED_DEFAULT:-"FALSE"}
MAX_DEVICES_DEFAULT=${MAX_DEVICES_DEFAULT:-"3"}

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Function to check LDAP connection
check_ldap_connection() {
    print_info "Checking LDAP connection..."
    
    # Debug: Show actual values being used (hide password)
    print_info "  Server: $LDAP_SERVER"
    print_info "  Admin DN: $LDAP_ADMIN_DN"
    print_info "  Base DN: $LDAP_BASE_DN"
    if [ -n "$LDAP_ADMIN_PASSWORD" ]; then
        print_info "  Password: [SET - length: ${#LDAP_ADMIN_PASSWORD}]"
    else
        print_warn "  Password: [NOT SET]"
    fi
    
    # Test connection with verbose error output
    local error_output=$(mktemp)
    if ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -b "$LDAP_BASE_DN" -s base "(objectClass=*)" >/dev/null 2>"$error_output"; then
        print_info "LDAP connection successful"
        rm -f "$error_output"
        return 0
    else
        print_error "LDAP connection failed!"
        print_error "Error details:"
        cat "$error_output" | while IFS= read -r line; do
            print_error "  $line"
        done
        rm -f "$error_output"
        print_error ""
        print_error "Please check:"
        print_error "  - LDAP server is running: $LDAP_SERVER"
        print_error "  - Admin DN: $LDAP_ADMIN_DN"
        print_error "  - Base DN: $LDAP_BASE_DN"
        print_error "  - Admin password is correct"
        return 1
    fi
}

# Function to check if schema is installed
check_schema() {
    print_info "Checking if wireguard schema is installed..."
    
    if ldapsearch -x -H ldapi:/// -b "cn=schema,cn=config" "(cn=wireguard)" 2>/dev/null | grep -q "wireguard"; then
        print_info "WireGuard schema is installed"
        return 0
    else
        print_warn "WireGuard schema not found (or ldapi:// not accessible)"
        print_warn "Make sure schema is installed: sudo bash scripts/setup_ldap_schema.sh"
        return 1
    fi
}

# Function to get all users without wireguardUser objectClass
get_users_to_migrate() {
    print_info "Finding users that need migration..."
    
    # Get all users that don't have wireguardUser objectClass
    ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -b "$LDAP_BASE_PEOPLE" \
        "(&(objectClass=inetOrgPerson)(!(objectClass=wireguardUser)))" \
        dn 2>/dev/null | grep "^dn:" | sed 's/^dn: //' || true
}

# Function to migrate single user
migrate_user() {
    local user_dn=$1
    
    # Extract username from DN (uid=username,ou=people,...)
    local username=$(echo "$user_dn" | sed -n 's/.*uid=\([^,]*\).*/\1/p')
    
    if [ -z "$username" ]; then
        print_error "Could not extract username from DN: $user_dn"
        return 1
    fi
    
    print_info "Migrating user: $username"
    
    # Create temporary LDIF file
    local tmp_ldif=$(mktemp)
    
    cat > "$tmp_ldif" <<EOF
dn: $user_dn
changetype: modify
add: objectClass
objectClass: wireguardUser
-
EOF

    # Only add wireguardEnabled if it doesn't exist
    if ! ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -b "$user_dn" "(objectClass=*)" wireguardEnabled 2>/dev/null | grep -q "wireguardEnabled"; then
        cat >> "$tmp_ldif" <<EOF
add: wireguardEnabled
wireguardEnabled: $WIREGUARD_ENABLED_DEFAULT
-
EOF
    fi
    
    # Only add maxWireguardDevices if it doesn't exist
    if ! ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -b "$user_dn" "(objectClass=*)" maxWireguardDevices 2>/dev/null | grep -q "maxWireguardDevices"; then
        cat >> "$tmp_ldif" <<EOF
add: maxWireguardDevices
maxWireguardDevices: $MAX_DEVICES_DEFAULT
-
EOF
    fi
    
    # Apply changes
    if ldapmodify -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -f "$tmp_ldif" >/dev/null 2>&1; then
        print_info "  ✓ User $username migrated successfully"
        rm -f "$tmp_ldif"
        return 0
    else
        print_error "  ✗ Failed to migrate user $username"
        rm -f "$tmp_ldif"
        return 1
    fi
}

# Function to migrate all users
migrate_all_users() {
    print_step "Starting LDAP users migration..."
    
    local users=$(get_users_to_migrate)
    
    if [ -z "$users" ]; then
        print_info "No users need migration (all users already have wireguardUser objectClass)"
        return 0
    fi
    
    local user_count=$(echo "$users" | wc -l)
    print_info "Found $user_count user(s) to migrate"
    
    local migrated=0
    local failed=0
    
    while IFS= read -r user_dn; do
        if [ -n "$user_dn" ]; then
            if migrate_user "$user_dn"; then
                ((migrated++))
            else
                ((failed++))
            fi
        fi
    done <<< "$users"
    
    print_info ""
    print_info "Migration Summary:"
    print_info "  Total users found: $user_count"
    print_info "  Successfully migrated: $migrated"
    print_info "  Failed: $failed"
    
    if [ $failed -gt 0 ]; then
        return 1
    fi
    
    return 0
}

# Function to verify migration
verify_migration() {
    print_step "Verifying migration..."
    
    local users_without_schema=$(ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -b "$LDAP_BASE_PEOPLE" \
        "(&(objectClass=inetOrgPerson)(!(objectClass=wireguardUser)))" \
        dn 2>/dev/null | grep -c "^dn:" || echo "0")
    
    if [ "$users_without_schema" -eq 0 ]; then
        print_info "✓ All users have wireguardUser objectClass"
        return 0
    else
        print_warn "⚠ $users_without_schema user(s) still need migration"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run          Show what would be migrated without executing"
    echo "  --verify-only      Only verify migration status"
    echo "  --help             Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  LDAP_SERVER         LDAP server URI (default: ldap://117.53.44.59:389)"
    echo "  LDAP_BASE_DN        LDAP base DN (default: dc=example,dc=com)"
    echo "  LDAP_ADMIN_DN       LDAP admin DN (default: cn=admin,dc=example,dc=com)"
    echo "  LDAP_ADMIN_PASSWORD LDAP admin password (required)"
    echo "  WIREGUARD_ENABLED_DEFAULT Default wireguardEnabled value (default: FALSE)"
    echo "  MAX_DEVICES_DEFAULT Default maxWireguardDevices value (default: 3)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run migration"
    echo "  $0 --dry-run                          # Preview migration"
    echo "  $0 --verify-only                      # Check status"
    echo "  LDAP_ADMIN_PASSWORD=secret $0         # With password"
}

# Main function
main() {
    local dry_run=false
    local verify_only=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run=true
                shift
                ;;
            --verify-only)
                verify_only=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_info "LDAP Users Migration Script"
    print_info "LDAP Server: $LDAP_SERVER"
    print_info "LDAP Base DN: $LDAP_BASE_DN"
    print_info "LDAP User DN: $LDAP_USER_DN"
    print_info "LDAP Admin DN: $LDAP_ADMIN_DN"
    print_info "LDAP Base People: $LDAP_BASE_PEOPLE"
    if [ -n "$LDAP_ADMIN_PASSWORD" ]; then
        print_info "LDAP Admin Password: [SET]"
    else
        print_warn "LDAP Admin Password: [NOT SET]"
    fi
    echo ""
    
    # Check LDAP connection
    if ! check_ldap_connection; then
        exit 1
    fi
    
    # Verify only mode
    if [ "$verify_only" = true ]; then
        verify_migration
        exit $?
    fi
    
    # Check schema (warning only)
    check_schema || print_warn "Continuing anyway..."
    
    # Dry run mode
    if [ "$dry_run" = true ]; then
        print_info "DRY RUN MODE - No changes will be made"
        echo ""
        local users=$(get_users_to_migrate)
        if [ -z "$users" ]; then
            print_info "No users need migration"
        else
            local user_count=$(echo "$users" | wc -l)
            print_info "Would migrate $user_count user(s):"
            while IFS= read -r user_dn; do
                if [ -n "$user_dn" ]; then
                    local username=$(echo "$user_dn" | sed -n 's/.*uid=\([^,]*\).*/\1/p')
                    echo "  - $username ($user_dn)"
                fi
            done <<< "$users"
        fi
        exit 0
    fi
    
    # Run migration
    if migrate_all_users; then
        print_info ""
        verify_migration
        print_info ""
        print_info "Migration completed successfully!"
    else
        print_error ""
        print_error "Migration completed with errors"
        exit 1
    fi
}

# Run main function
main "$@"

