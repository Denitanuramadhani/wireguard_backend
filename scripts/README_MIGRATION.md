# Database Migration Guide

## Quick Start

### Using Docker Compose

```bash
# Start all services (MySQL will auto-run schema.sql on first start)
docker-compose up -d

# Run migrations manually (if needed)
docker-compose exec backend bash scripts/migrate.sh
```

### Manual Migration

```bash
# Make script executable
chmod +x scripts/migrate.sh

# Run full migration
./scripts/migrate.sh

# Or with custom MySQL host
MYSQL_HOST=localhost MYSQL_USER=root MYSQL_PASSWORD=password ./scripts/migrate.sh
```

## Migration Script Options

```bash
# Full migration (schema + migrations)
./scripts/migrate.sh

# Only run schema.sql
./scripts/migrate.sh --schema-only

# Only run migrations (skip schema)
./scripts/migrate.sh --migrations-only

# Verify migration status
./scripts/migrate.sh --verify-only

# Force recreate database (WARNING: Deletes all data!)
./scripts/migrate.sh --force
```

## Environment Variables

The migration script uses these environment variables (with defaults):

- `MYSQL_HOST` (default: `mysql` - Docker service name)
- `MYSQL_PORT` (default: `3306`)
- `MYSQL_USER` (default: `wgadmin`)
- `MYSQL_PASSWORD` (default: `wgpassword`)
- `MYSQL_DATABASE` (default: `wireguard_vpn`)

## Migration Order

1. **schema.sql** - Creates all tables and initial structure
2. **add_qr_expiration.sql** - Adds QR code expiration columns
3. **add_performance_indexes.sql** - Adds performance indexes

## Troubleshooting

### Connection Failed

```bash
# Check MySQL is running
docker-compose ps mysql

# Check MySQL logs
docker-compose logs mysql

# Test connection manually
docker-compose exec mysql mysql -u wgadmin -pwgpassword -e "SELECT 1;"
```

### Migration Failed

```bash
# Check which migration failed
docker-compose exec backend bash scripts/migrate.sh --verify-only

# Run specific migration manually
docker-compose exec mysql mysql -u wgadmin -pwgpassword wireguard_vpn < database/migrations/add_qr_expiration.sql
```

### Reset Database

```bash
# WARNING: This deletes all data!
docker-compose exec backend bash scripts/migrate.sh --force
```

## Docker Compose Auto-Migration

When using Docker Compose, MySQL container automatically runs:
- `schema.sql` on first start (via `/docker-entrypoint-initdb.d/`)
- Migrations should be run manually after container is up

## Production Deployment

For production, it's recommended to:
1. Run migrations manually before starting the application
2. Backup database before running migrations
3. Test migrations on staging environment first

```bash
# Production migration example
MYSQL_HOST=your-mysql-host \
MYSQL_USER=wgadmin \
MYSQL_PASSWORD=your-secure-password \
MYSQL_DATABASE=wireguard_vpn \
./scripts/migrate.sh
```

