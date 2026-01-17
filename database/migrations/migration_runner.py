"""
Migration Runner untuk WireGuard VPN Backend
Menjalankan migration SQL files secara berurutan dengan tracking di database
"""

import os
import sys
from pathlib import Path
from app.database.connection import get_db_connection
from app.logger import logger

# Get migrations directory
MIGRATIONS_DIR = Path(__file__).parent


def init_migrations_table():
    """Create migrations tracking table if not exists"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    migration_file VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_migration_file (migration_file)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 
                COMMENT='Tracks applied database migrations'
            """)
            conn.commit()
            logger.debug("Migrations tracking table initialized")
    except Exception as e:
        logger.error(f"Error initializing migrations table: {e}")
        raise


def get_applied_migrations():
    """Get list of applied migrations from database"""
    init_migrations_table()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT migration_file FROM schema_migrations ORDER BY applied_at")
            return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        logger.error(f"Error getting applied migrations: {e}")
        raise


def mark_migration_applied(migration_file):
    """Mark migration as applied in database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO schema_migrations (migration_file) VALUES (%s)",
                (migration_file,)
            )
            conn.commit()
            logger.debug(f"Marked {migration_file} as applied")
    except Exception as e:
        logger.error(f"Error marking migration as applied: {e}")
        raise


def get_pending_migrations():
    """Get list of pending migrations (sorted by filename)"""
    applied = get_applied_migrations()
    
    # Get all SQL files except schema.sql and __init__.py
    migrations = sorted([
        f for f in os.listdir(MIGRATIONS_DIR) 
        if f.endswith('.sql') and f != 'schema.sql' and not f.startswith('__')
    ])
    
    return [m for m in migrations if m not in applied]


def run_migration(migration_file):
    """Run a single migration file"""
    migration_path = MIGRATIONS_DIR / migration_file
    
    if not migration_path.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")
    
    logger.info(f"Running migration: {migration_file}")
    
    # Read migration file
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    if not sql_content.strip():
        logger.warning(f"Migration file {migration_file} is empty, skipping")
        return
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Split by semicolon and execute each statement
            # Handle multi-line statements properly
            statements = []
            current_statement = []
            
            for line in sql_content.split('\n'):
                # Skip comments and empty lines
                stripped = line.strip()
                if not stripped or stripped.startswith('--'):
                    continue
                
                current_statement.append(line)
                
                # If line ends with semicolon, it's end of statement
                if stripped.endswith(';'):
                    statement = '\n'.join(current_statement).strip()
                    if statement:
                        statements.append(statement)
                    current_statement = []
            
            # Execute all statements
            for statement in statements:
                if not statement.strip():
                    continue
                    
                try:
                    cursor.execute(statement)
                except Exception as e:
                    # Check if error is because object already exists (for IF NOT EXISTS)
                    # MySQL error codes: 
                    # 1050 (table exists), 1060 (duplicate column), 1061 (duplicate key), 
                    # 1062 (duplicate entry), 1051 (unknown table - for DROP IF EXISTS)
                    error_msg = str(e).lower()
                    error_code = None
                    
                    # Try to get MySQL error code
                    if hasattr(e, 'args') and len(e.args) > 0:
                        if isinstance(e.args[0], int):
                            error_code = e.args[0]
                        elif isinstance(e.args[0], tuple) and len(e.args[0]) > 0:
                            error_code = e.args[0][0]
                    
                    # MySQL error codes for "already exists" scenarios
                    skip_error_codes = [1050, 1060, 1061, 1062, 1051]
                    
                    # Skip if object already exists (idempotent)
                    skip_conditions = [
                        'already exists' in error_msg,
                        'duplicate' in error_msg,
                        'table .* already exists' in error_msg,
                        'duplicate column' in error_msg,
                        'duplicate key' in error_msg,
                        'duplicate entry' in error_msg,
                        error_code in skip_error_codes,
                    ]
                    
                    # Special handling for ADD COLUMN (MySQL < 8.0.19 doesn't support IF NOT EXISTS)
                    if 'add column' in statement.lower() and 'duplicate column' in error_msg:
                        logger.debug(f"Column already exists (skipping): {statement[:80]}...")
                        continue
                    
                    if any(skip_conditions):
                        logger.debug(f"Object already exists (skipping): {statement[:80]}...")
                        # Continue execution - this is expected for idempotent migrations
                        continue
                    else:
                        logger.error(f"Error executing statement: {statement[:100]}...")
                        logger.error(f"Error details: {e}")
                        logger.error(f"Error code: {error_code}")
                        raise
            
            conn.commit()
            mark_migration_applied(migration_file)
            logger.info(f"✓ Migration {migration_file} applied successfully")
            
    except Exception as e:
        logger.error(f"Error running migration {migration_file}: {e}")
        raise


def run_all_migrations(dry_run=False):
    """
    Run all pending migrations
    
    Args:
        dry_run: If True, only show what would be run without executing
    """
    pending = get_pending_migrations()
    
    if not pending:
        logger.info("No pending migrations")
        return []
    
    logger.info(f"Found {len(pending)} pending migration(s)")
    
    if dry_run:
        logger.info("DRY RUN - Would execute the following migrations:")
        for migration in pending:
            logger.info(f"  - {migration}")
        return pending
    
    applied = []
    failed = []
    
    for migration in pending:
        try:
            run_migration(migration)
            applied.append(migration)
        except Exception as e:
            logger.error(f"Migration {migration} failed: {e}")
            failed.append((migration, str(e)))
            # Stop on first failure
            break
    
    if failed:
        logger.error(f"{len(failed)} migration(s) failed")
        for migration, error in failed:
            logger.error(f"  - {migration}: {error}")
        return None
    
    if applied:
        logger.info(f"✓ Successfully applied {len(applied)} migration(s)")
    
    return applied


def list_migrations():
    """List all migrations and their status"""
    applied = get_applied_migrations()
    all_migrations = sorted([
        f for f in os.listdir(MIGRATIONS_DIR) 
        if f.endswith('.sql') and f != 'schema.sql' and not f.startswith('__')
    ])
    
    print("\nMigration Status:")
    print("=" * 60)
    for migration in all_migrations:
        status = "✓ APPLIED" if migration in applied else "⏳ PENDING"
        print(f"{status:12} | {migration}")
    print("=" * 60)
    print(f"\nTotal: {len(all_migrations)} migrations")
    print(f"Applied: {len(applied)}")
    print(f"Pending: {len(all_migrations) - len(applied)}")


def main():
    """Main entry point for migration runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Migration Runner')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be run without executing'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all migrations and their status'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_migrations()
        return
    
    try:
        result = run_all_migrations(dry_run=args.dry_run)
        if result is None:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Migration runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
