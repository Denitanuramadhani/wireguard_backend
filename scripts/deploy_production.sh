#!/bin/bash

# ============================================
# Production Deployment Script
# WireGuard VPN Portal Backend
# ============================================
#
# Automated deployment script untuk production
# Run pre-deployment checks, migrations, dan start services
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    source "$PROJECT_DIR/.env" 2>/dev/null || true
fi

# Configuration
DEPLOY_MODE=${DEPLOY_MODE:-"systemd"}  # systemd or docker
SKIP_CHECKS=${SKIP_CHECKS:-"false"}
SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-"false"}
BACKUP_DB=${BACKUP_DB:-"true"}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --mode MODE          Deployment mode: systemd or docker (default: systemd)"
    echo "  --skip-checks        Skip pre-deployment checks"
    echo "  --skip-migrations    Skip database migrations"
    echo "  --no-backup         Skip database backup"
    echo "  --help              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                           # Full deployment with checks"
    echo "  $0 --mode docker             # Deploy using Docker"
    echo "  $0 --skip-checks             # Skip pre-deployment checks"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            DEPLOY_MODE="$2"
            shift 2
            ;;
        --skip-checks)
            SKIP_CHECKS="true"
            shift
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS="true"
            shift
            ;;
        --no-backup)
            BACKUP_DB="false"
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

echo "============================================"
echo "Production Deployment"
echo "WireGuard VPN Portal Backend"
echo "============================================"
echo ""

# Step 1: Pre-deployment checks
if [ "$SKIP_CHECKS" != "true" ]; then
    print_step "Step 1: Running pre-deployment checks..."
    if "$SCRIPT_DIR/pre_deploy_check.sh"; then
        print_info "Pre-deployment checks passed"
    else
        print_error "Pre-deployment checks failed!"
        print_error "Fix errors before deploying"
        exit 1
    fi
else
    print_warn "Skipping pre-deployment checks"
fi

# Step 2: Backup database
if [ "$BACKUP_DB" = "true" ] && [ "$SKIP_MIGRATIONS" != "true" ]; then
    print_step "Step 2: Backing up database..."
    BACKUP_DIR="$PROJECT_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if command -v mysqldump &> /dev/null; then
        if mysqldump -h "${MYSQL_HOST:-localhost}" -u "${MYSQL_USER:-wgadmin}" \
            -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE:-wireguard_vpn}" > "$BACKUP_FILE" 2>/dev/null; then
            print_info "Database backup created: $BACKUP_FILE"
        else
            print_warn "Database backup failed (continuing anyway)"
        fi
    else
        print_warn "mysqldump not found (skipping backup)"
    fi
fi

# Step 3: Database migrations
if [ "$SKIP_MIGRATIONS" != "true" ]; then
    print_step "Step 3: Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Activate venv if exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Run migrations
    if python -m database.migrations.migration_runner 2>/dev/null; then
        print_info "Database migrations completed"
    else
        print_error "Database migrations failed!"
        exit 1
    fi
else
    print_warn "Skipping database migrations"
fi

# Step 4: LDAP migrations (if needed)
print_step "Step 4: Checking LDAP setup..."
if command -v ldapsearch &> /dev/null && [ -n "$LDAP_ADMIN_PASSWORD" ]; then
    # Check if schema needs to be installed
    if ! ldapsearch -x -H ldapi:/// -b "cn=schema,cn=config" "(cn=wireguard)" 2>/dev/null | grep -q "wireguard"; then
        print_warn "WireGuard LDAP schema not found"
        print_info "Run: sudo bash scripts/setup_ldap_schema.sh"
    else
        print_info "LDAP schema is installed"
    fi
    
    # Check if users need migration
    if bash "$SCRIPT_DIR/migrate_ldap_users.sh" --verify-only 2>/dev/null | grep -q "PENDING"; then
        print_warn "Some LDAP users need migration"
        print_info "Run: bash scripts/migrate_ldap_users.sh"
    else
        print_info "LDAP users are up to date"
    fi
else
    print_warn "LDAP tools not available (skipping LDAP checks)"
fi

# Step 5: Deploy based on mode
print_step "Step 5: Deploying application..."

if [ "$DEPLOY_MODE" = "docker" ]; then
    print_info "Deploying with Docker..."
    
    cd "$PROJECT_DIR"
    
    # Build image
    if docker-compose -f docker-compose.prod.yml build; then
        print_info "Docker image built successfully"
    else
        print_error "Docker build failed!"
        exit 1
    fi
    
    # Start services
    if docker-compose -f docker-compose.prod.yml up -d; then
        print_info "Docker services started"
    else
        print_error "Failed to start Docker services!"
        exit 1
    fi
    
    # Wait for health check
    print_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check health
    if curl -f http://localhost:8000/health/ >/dev/null 2>&1; then
        print_info "Service is healthy"
    else
        print_warn "Health check failed (service might still be starting)"
    fi
    
elif [ "$DEPLOY_MODE" = "systemd" ]; then
    print_info "Deploying with systemd..."
    
    # Check if systemd service exists
    if [ -f "/etc/systemd/system/wireguard-backend.service" ]; then
        # Reload systemd
        sudo systemctl daemon-reload
        
        # Restart service
        if sudo systemctl restart wireguard-backend; then
            print_info "Service restarted"
            
            # Wait a bit
            sleep 5
            
            # Check status
            if sudo systemctl is-active --quiet wireguard-backend; then
                print_info "Service is running"
            else
                print_error "Service failed to start!"
                sudo systemctl status wireguard-backend
                exit 1
            fi
        else
            print_error "Failed to restart service!"
            exit 1
        fi
    else
        print_warn "systemd service not found"
        print_info "Install service: sudo cp systemd/wireguard-backend.service /etc/systemd/system/"
        print_info "Then: sudo systemctl daemon-reload && sudo systemctl enable wireguard-backend"
    fi
else
    print_error "Unknown deployment mode: $DEPLOY_MODE"
    exit 1
fi

# Step 6: Verify deployment
print_step "Step 6: Verifying deployment..."

sleep 5

# Check health endpoint
if curl -f http://localhost:8000/health/ >/dev/null 2>&1; then
    print_info "✓ Health check passed"
else
    print_warn "Health check failed (check logs)"
fi

# Final summary
echo ""
echo "============================================"
echo "Deployment Complete"
echo "============================================"
print_info "Deployment mode: $DEPLOY_MODE"
print_info "Service should be running on: http://localhost:8000"
print_info ""
print_info "Next steps:"
print_info "  1. Check logs: sudo journalctl -u wireguard-backend -f"
print_info "  2. Test API: curl http://localhost:8000/health/"
print_info "  3. Setup Nginx reverse proxy (if not done)"
print_info "  4. Setup SSL certificate (Let's Encrypt)"
echo ""

