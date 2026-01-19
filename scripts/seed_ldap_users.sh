#!/bin/bash

# ============================================
# LDAP Users Seeder Script
# WireGuard VPN Portal Backend
# ============================================
#
# Script untuk create/seed LDAP users dari file CSV atau JSON
# Safe to run multiple times (idempotent - skip jika user sudah exists)
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
LDAP_SERVER=${LDAP_SERVER:-"ldap://117.53.44.59:389"}
LDAP_BASE_DN=${LDAP_BASE_DN:-"dc=wireguard,dc=local"}
LDAP_USER_DN=${LDAP_USER_DN:-"uid={},ou=people,dc=wireguard,dc=local"}
LDAP_ADMIN_DN=${LDAP_ADMIN_DN:-"cn=admin,dc=wireguard,dc=local"}
LDAP_ADMIN_PASSWORD=${LDAP_ADMIN_PASSWORD:-"123"}

# Derive LDAP_BASE_PEOPLE from LDAP_USER_DN or use default
if [[ "$LDAP_USER_DN" == *"ou=people"* ]]; then
    LDAP_BASE_PEOPLE=$(echo "$LDAP_USER_DN" | sed -E 's/^[^,]+,//' | sed 's/{},//')
else
    LDAP_BASE_PEOPLE=${LDAP_BASE_PEOPLE:-"ou=people,${LDAP_BASE_DN}"}
fi

WIREGUARD_ENABLED_DEFAULT=${WIREGUARD_ENABLED_DEFAULT:-"FALSE"}
MAX_DEVICES_DEFAULT=${MAX_DEVICES_DEFAULT:-"3"}
UID_NUMBER_START=${UID_NUMBER_START:-"2000"}

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

# Function to check if user exists
user_exists() {
    local username=$1
    ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -b "$LDAP_BASE_PEOPLE" "(uid=$username)" dn >/dev/null 2>&1
    return $?
}

# Function to get next available uidNumber
get_next_uid_number() {
    local max_uid=$(ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -b "$LDAP_BASE_PEOPLE" "(objectClass=posixAccount)" uidNumber 2>/dev/null | \
        grep "^uidNumber:" | awk '{print $2}' | sort -n | tail -1)
    
    if [ -z "$max_uid" ]; then
        echo "$UID_NUMBER_START"
    else
        echo $((max_uid + 1))
    fi
}

# Function to create user from LDIF
create_user_ldif() {
    local username=$1
    local password=$2
    local uid_number=$3
    local max_devices=${4:-$MAX_DEVICES_DEFAULT}
    local wireguard_enabled=${5:-$WIREGUARD_ENABLED_DEFAULT}
    
    # Hash password
    local hashed_pass
    if command -v slappasswd &> /dev/null; then
        hashed_pass=$(slappasswd -s "$password" 2>/dev/null)
    else
        print_error "slappasswd not found. Please install openldap-utils"
        return 1
    fi
    
    # Create temporary LDIF file
    local tmp_ldif=$(mktemp)
    local user_dn="uid=$username,$LDAP_BASE_PEOPLE"
    
    cat > "$tmp_ldif" <<EOF
dn: $user_dn
objectClass: inetOrgPerson
objectClass: organizationalPerson
objectClass: person
objectClass: posixAccount
objectClass: top
objectClass: wireguardUser
cn: $username
sn: $username
uid: $username
uidNumber: $uid_number
gidNumber: $uid_number
homeDirectory: /home/$username
loginShell: /bin/bash
userPassword: $hashed_pass
wireguardEnabled: $wireguard_enabled
maxWireguardDevices: $max_devices
EOF
    
    # Add user
    if ldapadd -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
        -f "$tmp_ldif" >/dev/null 2>&1; then
        rm -f "$tmp_ldif"
        return 0
    else
        rm -f "$tmp_ldif"
        return 1
    fi
}

# Function to create user
create_user() {
    local username=$1
    local password=$2
    local uid_number=$3
    local max_devices=${4:-$MAX_DEVICES_DEFAULT}
    local wireguard_enabled=${5:-$WIREGUARD_ENABLED_DEFAULT}
    
    # Check if user already exists
    if user_exists "$username"; then
        print_warn "User $username already exists, skipping..."
        return 0
    fi
    
    # Create user
    if create_user_ldif "$username" "$password" "$uid_number" "$max_devices" "$wireguard_enabled"; then
        print_info "  ✓ User $username created successfully"
        return 0
    else
        print_error "  ✗ Failed to create user $username"
        return 1
    fi
}

# Function to seed from CSV file
seed_from_csv() {
    local csv_file=$1
    local created=0
    local skipped=0
    local failed=0
    local current_uid=$UID_NUMBER_START
    
    print_step "Seeding users from CSV file: $csv_file"
    
    if [ ! -f "$csv_file" ]; then
        print_error "CSV file not found: $csv_file"
        return 1
    fi
    
    # Get next available uidNumber
    current_uid=$(get_next_uid_number)
    
    # Read CSV file (format: username,password,max_devices,wireguard_enabled)
    # Skip header if exists
    local line_num=0
    while IFS=',' read -r username password max_devices wireguard_enabled || [ -n "$username" ]; do
        ((line_num++))
        
        # Skip header
        if [ $line_num -eq 1 ] && [[ "$username" =~ ^[Uu]sername ]]; then
            continue
        fi
        
        # Skip empty lines
        [[ -z "${username// }" ]] && continue
        
        # Trim whitespace
        username=$(echo "$username" | xargs)
        password=$(echo "$password" | xargs)
        max_devices=$(echo "$max_devices" | xargs)
        wireguard_enabled=$(echo "$wireguard_enabled" | xargs)
        
        # Set defaults
        max_devices=${max_devices:-$MAX_DEVICES_DEFAULT}
        wireguard_enabled=${wireguard_enabled:-$WIREGUARD_ENABLED_DEFAULT}
        
        # Validate username
        if [[ ! "$username" =~ ^[a-zA-Z0-9_]+$ ]]; then
            print_error "  ✗ Invalid username format: $username (line $line_num)"
            ((failed++))
            continue
        fi
        
        # Validate password
        if [ -z "$password" ]; then
            print_error "  ✗ Password required for user: $username (line $line_num)"
            ((failed++))
            continue
        fi
        
        # Create user
        if create_user "$username" "$password" "$current_uid" "$max_devices" "$wireguard_enabled"; then
            if user_exists "$username"; then
                ((created++))
            else
                ((skipped++))
            fi
            ((current_uid++))
        else
            ((failed++))
        fi
        
    done < "$csv_file"
    
    print_info ""
    print_info "Seeding Summary:"
    print_info "  Created: $created"
    print_info "  Skipped: $skipped"
    print_info "  Failed: $failed"
    
    if [ $failed -gt 0 ]; then
        return 1
    fi
    
    return 0
}

# Function to create sample CSV file
create_sample_csv() {
    local csv_file=${1:-"users_sample.csv"}
    
    print_info "Creating sample CSV file: $csv_file"
    
    cat > "$csv_file" <<EOF
username,password,max_devices,wireguard_enabled
user1,password123,3,FALSE
user2,password123,5,TRUE
admin,admin123,10,TRUE
EOF
    
    print_info "Sample CSV file created: $csv_file"
    print_info "Format: username,password,max_devices,wireguard_enabled"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [CSV_FILE]"
    echo ""
    echo "Options:"
    echo "  --sample          Create sample CSV file"
    echo "  --help            Show this help message"
    echo ""
    echo "Arguments:"
    echo "  CSV_FILE          Path to CSV file with users (default: users.csv)"
    echo ""
    echo "CSV Format:"
    echo "  username,password,max_devices,wireguard_enabled"
    echo "  user1,password123,3,FALSE"
    echo "  user2,password123,5,TRUE"
    echo ""
    echo "Environment Variables:"
    echo "  LDAP_SERVER         LDAP server URI"
    echo "  LDAP_BASE_DN        LDAP base DN"
    echo "  LDAP_ADMIN_DN       LDAP admin DN"
    echo "  LDAP_ADMIN_PASSWORD LDAP admin password"
    echo "  UID_NUMBER_START    Starting UID number (default: 2000)"
    echo ""
    echo "Examples:"
    echo "  $0 users.csv                    # Seed users from CSV"
    echo "  $0 --sample                     # Create sample CSV"
    echo "  LDAP_ADMIN_PASSWORD=secret $0 users.csv"
}

# Main function
main() {
    local csv_file=""
    local create_sample=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --sample)
                create_sample=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                csv_file=$1
                shift
                ;;
        esac
    done
    
    # Create sample CSV if requested
    if [ "$create_sample" = true ]; then
        create_sample_csv
        exit 0
    fi
    
    # Default CSV file
    if [ -z "$csv_file" ]; then
        csv_file="users.csv"
    fi
    
    print_info "LDAP Users Seeder Script"
    print_info "LDAP Server: $LDAP_SERVER"
    print_info "LDAP Base DN: $LDAP_BASE_DN"
    print_info "LDAP Base People: $LDAP_BASE_PEOPLE"
    echo ""
    
    # Check if CSV file exists
    if [ ! -f "$csv_file" ]; then
        print_error "CSV file not found: $csv_file"
        print_info ""
        print_info "Create sample CSV file with: $0 --sample"
        exit 1
    fi
    
    # Seed users
    if seed_from_csv "$csv_file"; then
        print_info ""
        print_info "Seeding completed successfully!"
    else
        print_error ""
        print_error "Seeding completed with errors"
        exit 1
    fi
}

# Run main function
main "$@"

