#!/bin/bash

# ============================================
# Database Migration Script
# WireGuard VPN Portal Backend
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (can be overridden by environment variables)
MYSQL_HOST=${MYSQL_HOST:-mysql}
MYSQL_PORT=${MYSQL_PORT:-3306}
MYSQL_USER=${MYSQL_USER:-wgadmin}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-wgpassword}
MYSQL_DATABASE=${MYSQL_DATABASE:-wireguard_vpn}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATIONS_DIR="$PROJECT_DIR/database/migrations"
SCHEMA_FILE="$PROJECT_DIR/database/schema.sql"

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

# Function to check MySQL connection
check_mysql_connection() {
    print_info "Checking MySQL connection..."
    
    if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" "$MYSQL_DATABASE" >/dev/null 2>&1; then
        print_info "MySQL connection successful"
        return 0
    else
        print_error "MySQL connection failed!"
        print_error "Please check:"
        print_error "  - MySQL service is running"
        print_error "  - Host: $MYSQL_HOST"
        print_error "  - Port: $MYSQL_PORT"
        print_error "  - User: $MYSQL_USER"
        print_error "  - Database: $MYSQL_DATABASE"
        return 1
    fi
}

# Function to check if database exists
check_database_exists() {
    if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "USE $MYSQL_DATABASE;" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to create database
create_database() {
    print_info "Creating database '$MYSQL_DATABASE'..."
    
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" <<EOF
CREATE DATABASE IF NOT EXISTS $MYSQL_DATABASE 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
EOF
    
    if [ $? -eq 0 ]; then
        print_info "Database created successfully"
        return 0
    else
        print_error "Failed to create database"
        return 1
    fi
}

# Function to check if table exists
table_exists() {
    local table_name=$1
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" \
        -e "SHOW TABLES LIKE '$table_name';" 2>/dev/null | grep -q "$table_name"
}

# Function to run schema.sql
run_schema() {
    if [ ! -f "$SCHEMA_FILE" ]; then
        print_error "Schema file not found: $SCHEMA_FILE"
        return 1
    fi
    
    print_info "Running schema.sql..."
    
    # Check if tables already exist
    if table_exists "vpn_devices"; then
        print_warn "Tables already exist. Skipping schema.sql"
        print_warn "If you want to recreate tables, drop them first or use --force flag"
        return 0
    fi
    
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$SCHEMA_FILE"
    
    if [ $? -eq 0 ]; then
        print_info "Schema applied successfully"
        return 0
    else
        print_error "Failed to apply schema"
        return 1
    fi
}

# Function to run migrations
run_migrations() {
    if [ ! -d "$MIGRATIONS_DIR" ]; then
        print_warn "Migrations directory not found: $MIGRATIONS_DIR"
        return 0
    fi
    
    print_info "Running migrations..."
    
    # Get list of migration files sorted by name
    local migration_files=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort)
    
    if [ -z "$migration_files" ]; then
        print_warn "No migration files found"
        return 0
    fi
    
    local count=0
    for migration_file in $migration_files; do
        local filename=$(basename "$migration_file")
        print_info "Running migration: $filename"
        
        mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$migration_file"
        
        if [ $? -eq 0 ]; then
            print_info "Migration $filename applied successfully"
            ((count++))
        else
            print_error "Failed to apply migration: $filename"
            print_error "Migration stopped. Please fix the error and run again."
            return 1
        fi
    done
    
    print_info "All migrations applied successfully ($count migrations)"
    return 0
}

# Function to verify migration
verify_migration() {
    print_info "Verifying migration..."
    
    local required_tables=("vpn_devices" "vpn_traffic_logs" "vpn_revoke_history" "vpn_bandwidth_limits" "vpn_audit_logs")
    local missing_tables=()
    
    for table in "${required_tables[@]}"; do
        if ! table_exists "$table"; then
            missing_tables+=("$table")
        fi
    done
    
    if [ ${#missing_tables[@]} -eq 0 ]; then
        print_info "All required tables exist"
        
        # Count records
        local device_count=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" \
            -se "SELECT COUNT(*) FROM vpn_devices;" 2>/dev/null || echo "0")
        
        print_info "Current device count: $device_count"
        return 0
    else
        print_error "Missing tables: ${missing_tables[*]}"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --force          Force recreate database (WARNING: This will drop existing data!)"
    echo "  --schema-only    Only run schema.sql, skip migrations"
    echo "  --migrations-only Only run migrations, skip schema.sql"
    echo "  --verify-only    Only verify migration status"
    echo "  --help           Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  MYSQL_HOST       MySQL host (default: mysql)"
    echo "  MYSQL_PORT       MySQL port (default: 3306)"
    echo "  MYSQL_USER       MySQL user (default: wgadmin)"
    echo "  MYSQL_PASSWORD   MySQL password (default: wgpassword)"
    echo "  MYSQL_DATABASE   MySQL database (default: wireguard_vpn)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run full migration"
    echo "  $0 --schema-only                      # Only run schema"
    echo "  $0 --migrations-only                  # Only run migrations"
    echo "  MYSQL_HOST=localhost $0               # Use different host"
}

# Main function
main() {
    local force=false
    local schema_only=false
    local migrations_only=false
    local verify_only=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force=true
                shift
                ;;
            --schema-only)
                schema_only=true
                shift
                ;;
            --migrations-only)
                migrations_only=true
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
    
    print_info "Starting database migration..."
    print_info "MySQL Host: $MYSQL_HOST"
    print_info "MySQL Port: $MYSQL_PORT"
    print_info "MySQL User: $MYSQL_USER"
    print_info "MySQL Database: $MYSQL_DATABASE"
    echo ""
    
    # Check MySQL connection
    if ! check_mysql_connection; then
        exit 1
    fi
    
    # Verify only mode
    if [ "$verify_only" = true ]; then
        verify_migration
        exit $?
    fi
    
    # Check if database exists
    if ! check_database_exists; then
        print_warn "Database '$MYSQL_DATABASE' does not exist"
        if ! create_database; then
            exit 1
        fi
    else
        print_info "Database '$MYSQL_DATABASE' exists"
    fi
    
    # Force mode: drop and recreate
    if [ "$force" = true ]; then
        print_warn "FORCE mode: Dropping existing database..."
        read -p "Are you sure? This will delete all data! (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            print_info "Aborted"
            exit 0
        fi
        
        mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" \
            -e "DROP DATABASE IF EXISTS $MYSQL_DATABASE;"
        
        if ! create_database; then
            exit 1
        fi
    fi
    
    # Run schema
    if [ "$migrations_only" != true ]; then
        if ! run_schema; then
            exit 1
        fi
    fi
    
    # Run migrations
    if [ "$schema_only" != true ]; then
        if ! run_migrations; then
            exit 1
        fi
    fi
    
    # Verify
    if ! verify_migration; then
        exit 1
    fi
    
    print_info "Migration completed successfully!"
}

# Run main function
main "$@"

