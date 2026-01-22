#!/bin/bash
set -e

# Ensure virtual environment is in PATH
# Virtual environment sudah di-set di Dockerfile via ENV PATH="/opt/venv/bin:$PATH"
# Tapi kita pastikan lagi di sini untuk safety
export PATH="/opt/venv/bin:$PATH"

# Verify Python is using venv (optional check, tidak fatal jika gagal)
if command -v python >/dev/null 2>&1; then
    PYTHON_PREFIX=$(python -c "import sys; print(sys.prefix)" 2>/dev/null || echo "unknown")
    if [ "$PYTHON_PREFIX" != "/opt/venv" ] && [ "$PYTHON_PREFIX" != "unknown" ]; then
        echo "WARNING: Python prefix is $PYTHON_PREFIX, expected /opt/venv"
        echo "This might indicate virtual environment is not active"
    else
        echo "✓ Virtual environment is active (Python prefix: $PYTHON_PREFIX)"
    fi
fi

# Wait for Redis to be available
wait_for_redis() {
    echo "Waiting for Redis at ${REDIS_HOST:-127.0.0.1}:${REDIS_PORT:-6379}..."
    local max_attempts=30
    local attempt=0
    
    until redis-cli -h "${REDIS_HOST:-127.0.0.1}" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "ERROR: Redis connection timeout after $max_attempts attempts"
            exit 1
        fi
        echo "Redis is unavailable - sleeping (attempt $attempt/$max_attempts)"
        sleep 2
    done
    echo "✓ Redis is up!"
}

# Wait for MySQL to be available
wait_for_mysql() {
    echo "Waiting for MySQL..."
    local max_attempts=30
    local attempt=0
    
    until python -c "from app.database.connection import test_connection; exit(0 if test_connection() else 1)" 2>/dev/null; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            echo "ERROR: MySQL connection timeout after $max_attempts attempts"
            exit 1
        fi
        echo "MySQL is unavailable - sleeping (attempt $attempt/$max_attempts)"
        sleep 2
    done
    echo "MySQL is up!"
}

# Run database migrations
run_migrations() {
    echo "=========================================="
    echo "Running database migrations..."
    echo "=========================================="
    
    # Skip migrations if SKIP_MIGRATIONS is set
    if [ "${SKIP_MIGRATIONS:-false}" = "true" ]; then
        echo "⚠ Skipping migrations (SKIP_MIGRATIONS=true)"
        return 0
    fi
    
    # Run migrations with proper error handling
    if python -m database.migrations.migration_runner; then
        echo "✓ Database migrations completed successfully"
        echo "=========================================="
    else
        migration_exit_code=$?
        echo "=========================================="
        echo "ERROR: Database migrations failed (exit code: $migration_exit_code)"
        echo "=========================================="
        
        # In production, exit on migration failure
        # In development, continue with warning
        if [ "${ENVIRONMENT:-production}" = "production" ]; then
            echo "FATAL: Cannot continue in production mode with failed migrations"
            exit 1
        else
            echo "WARNING: Continuing despite migration failure (development mode)"
            echo "This may cause application errors!"
        fi
    fi
}

# Run startup checks
startup_checks() {
    echo "Running startup checks..."
    
    # Check required environment variables
    if [ -z "$MYSQL_HOST" ]; then
        echo "ERROR: MYSQL_HOST is not set"
        exit 1
    fi
    
    if [ -z "$LDAP_SERVER" ]; then
        echo "WARNING: LDAP_SERVER is not set"
    fi
    
    if [ -z "$JWT_SECRET" ]; then
        echo "WARNING: JWT_SECRET is not set - using default (not recommended for production)"
    fi
    
    # Test database connection
    if ! python -c "from app.database.connection import test_connection; exit(0 if test_connection() else 1)" 2>/dev/null; then
        echo "WARNING: Database connection test failed"
    fi
}

# Main execution
main() {
    echo "Starting WireGuard VPN Portal Backend..."
    
    # Wait for dependencies
    wait_for_redis
    wait_for_mysql
    
    # Run startup checks
    startup_checks
    
    # Run database migrations (after MySQL is ready)
    run_migrations
    
    # Execute the main command
    echo "Starting application..."
    exec "$@"
}

main "$@"
