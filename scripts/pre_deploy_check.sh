#!/bin/bash

# ============================================
# Pre-Deployment Check Script
# WireGuard VPN Portal Backend
# ============================================
#
# Script untuk check apakah semua sudah siap untuk production deployment
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

print_pass() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================"
echo "Pre-Deployment Check"
echo "WireGuard VPN Portal Backend"
echo "============================================"
echo ""

# Check 1: .env file exists
print_info "Checking .env file..."
if [ -f "$PROJECT_DIR/.env" ]; then
    print_pass ".env file exists"
else
    print_fail ".env file not found (copy from env.example.txt)"
fi

# Check 2: Required environment variables
print_info "Checking required environment variables..."
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env" 2>/dev/null || true
    
    REQUIRED_VARS=(
        "LDAP_SERVER"
        "LDAP_BASE_DN"
        "LDAP_ADMIN_DN"
        "LDAP_ADMIN_PASSWORD"
        "MYSQL_HOST"
        "MYSQL_USER"
        "MYSQL_PASSWORD"
        "MYSQL_DATABASE"
        "JWT_SECRET"
    )
    
    MISSING_VARS=()
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [ ${#MISSING_VARS[@]} -eq 0 ]; then
        print_pass "All required environment variables are set"
    else
        print_fail "Missing environment variables: ${MISSING_VARS[*]}"
    fi
fi

# Check 3: JWT_SECRET strength
print_info "Checking JWT_SECRET strength..."
if [ -n "$JWT_SECRET" ]; then
    if [ ${#JWT_SECRET} -ge 32 ]; then
        print_pass "JWT_SECRET is strong (${#JWT_SECRET} chars)"
    else
        print_warn "JWT_SECRET is weak (${#JWT_SECRET} chars, recommend >= 32)"
    fi
else
    print_fail "JWT_SECRET not set"
fi

# Check 4: ENCRYPTION_KEY
print_info "Checking ENCRYPTION_KEY..."
if [ -n "$ENCRYPTION_KEY" ]; then
    if [ ${#ENCRYPTION_KEY} -ge 32 ]; then
        print_pass "ENCRYPTION_KEY is set (${#ENCRYPTION_KEY} chars)"
    else
        print_warn "ENCRYPTION_KEY might be weak (${#ENCRYPTION_KEY} chars)"
    fi
else
    print_warn "ENCRYPTION_KEY not set (will use JWT_SECRET hash as fallback)"
fi

# Check 5: CORS_ORIGINS
print_info "Checking CORS_ORIGINS..."
if [ -n "$CORS_ORIGINS" ]; then
    if [[ "$CORS_ORIGINS" == *"*"* ]]; then
        print_warn "CORS_ORIGINS contains '*' (not recommended for production)"
    else
        print_pass "CORS_ORIGINS is configured"
    fi
else
    print_warn "CORS_ORIGINS not set (defaults to '*')"
fi

# Check 6: Database connection
print_info "Checking database connection..."
if command -v mysql &> /dev/null; then
    if mysql -h "${MYSQL_HOST:-localhost}" -u "${MYSQL_USER:-wgadmin}" -p"${MYSQL_PASSWORD}" \
        -e "SELECT 1;" "${MYSQL_DATABASE:-wireguard_vpn}" >/dev/null 2>&1; then
        print_pass "Database connection successful"
    else
        print_fail "Database connection failed"
    fi
else
    print_warn "mysql client not found (skipping database check)"
fi

# Check 7: Database migrations
print_info "Checking database migrations..."
if [ -d "$PROJECT_DIR/database/migrations" ]; then
    MIGRATION_FILES=$(find "$PROJECT_DIR/database/migrations" -name "*.sql" | wc -l)
    if [ "$MIGRATION_FILES" -gt 0 ]; then
        print_pass "Migration files found ($MIGRATION_FILES files)"
    else
        print_warn "No migration files found"
    fi
else
    print_fail "Migrations directory not found"
fi

# Check 8: Schema file
print_info "Checking schema.sql..."
if [ -f "$PROJECT_DIR/database/schema.sql" ]; then
    print_pass "schema.sql exists"
else
    print_fail "schema.sql not found"
fi

# Check 9: LDAP connection (if ldapsearch available)
print_info "Checking LDAP connection..."
if command -v ldapsearch &> /dev/null; then
    if [ -n "$LDAP_ADMIN_PASSWORD" ] && [ -n "$LDAP_SERVER" ] && [ -n "$LDAP_ADMIN_DN" ] && [ -n "$LDAP_BASE_DN" ]; then
        if ldapsearch -x -H "$LDAP_SERVER" -D "$LDAP_ADMIN_DN" -w "$LDAP_ADMIN_PASSWORD" \
            -b "$LDAP_BASE_DN" -s base "(objectClass=*)" >/dev/null 2>&1; then
            print_pass "LDAP connection successful"
        else
            print_fail "LDAP connection failed"
        fi
    else
        print_warn "LDAP credentials not set (skipping LDAP check)"
    fi
else
    print_warn "ldapsearch not found (skipping LDAP check)"
fi

# Check 10: Python dependencies
print_info "Checking Python dependencies..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    if [ -d "$PROJECT_DIR/venv" ]; then
        print_pass "Virtual environment exists"
        
        # Check if key packages are installed
        if [ -f "$PROJECT_DIR/venv/bin/python" ]; then
            if "$PROJECT_DIR/venv/bin/python" -c "import fastapi, pymysql, ldap3" 2>/dev/null; then
                print_pass "Key Python packages installed"
            else
                print_fail "Some Python packages missing (run: pip install -r requirements.txt)"
            fi
        fi
    else
        print_warn "Virtual environment not found (create with: python -m venv venv)"
    fi
else
    print_fail "requirements.txt not found"
fi

# Check 11: Docker files (if using Docker)
print_info "Checking Docker configuration..."
if [ -f "$PROJECT_DIR/Dockerfile" ]; then
    print_pass "Dockerfile exists"
    
    if [ -f "$PROJECT_DIR/docker-compose.prod.yml" ]; then
        print_pass "docker-compose.prod.yml exists"
    else
        print_warn "docker-compose.prod.yml not found (optional for Docker deployment)"
    fi
else
    print_warn "Dockerfile not found (optional if not using Docker)"
fi

# Check 12: Systemd service file
print_info "Checking systemd service file..."
if [ -f "$PROJECT_DIR/systemd/wireguard-backend.service" ]; then
    print_pass "systemd service file exists"
else
    print_warn "systemd service file not found (optional if not using systemd)"
fi

# Check 13: Log directory
print_info "Checking log directory..."
if [ -d "$PROJECT_DIR/logs" ] || [ -w "$PROJECT_DIR" ]; then
    print_pass "Log directory is writable"
else
    print_warn "Log directory might not be writable"
fi

# Check 14: Security checklist
print_info "Checking security settings..."
SECURITY_ISSUES=0

if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    print_warn "DEBUG is enabled (should be False in production)"
    ((SECURITY_ISSUES++))
fi

if [ "$ENVIRONMENT" != "production" ]; then
    print_warn "ENVIRONMENT is not set to 'production'"
    ((SECURITY_ISSUES++))
fi

if [ $SECURITY_ISSUES -eq 0 ]; then
    print_pass "Security settings look good"
fi

# Summary
echo ""
echo "============================================"
echo "Summary"
echo "============================================"
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✓ Ready for production deployment!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ Ready with warnings. Review warnings above.${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Not ready for production. Fix errors above.${NC}"
    exit 1
fi

