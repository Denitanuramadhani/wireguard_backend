# Docker Setup Guide

## Quick Start

### 1. Setup Environment Variables

```bash
# Copy example file
cp env.example.txt .env

# Edit .env file
nano .env
```

**Important variables to set:**
- `MYSQL_PASSWORD` - Strong password for MySQL user
- `MYSQL_ROOT_PASSWORD` - Strong password for MySQL root
- `JWT_SECRET` - Long random secret (min 32 characters)
- `ENCRYPTION_KEY` - 32-byte encryption key (hex)
- `LDAP_SERVER` - Your LDAP server address
- `LDAP_ADMIN_PASSWORD` - LDAP admin password

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 3. Run Database Migrations

```bash
# Option 1: Auto-migration (schema.sql runs automatically on first MySQL start)
# Migrations need to be run manually:

docker-compose exec backend bash scripts/migrate.sh

# Option 2: Run from host
./scripts/migrate.sh
```

### 4. Verify Setup

```bash
# Check health
curl http://localhost:8000/health/

# Check database
docker-compose exec mysql mysql -u wgadmin -p${MYSQL_PASSWORD:-wgpassword} wireguard_vpn -e "SHOW TABLES;"
```

## Services

### Backend
- **Container:** `wireguard-backend`
- **Port:** `8000`
- **Health Check:** `http://localhost:8000/health/`

### MySQL
- **Container:** `wireguard-mysql`
- **Port:** `3306`
- **Database:** `wireguard_vpn`
- **User:** `wgadmin`
- **Auto-schema:** Runs `schema.sql` on first start

### Redis
- **Container:** `wireguard-redis`
- **Port:** `6379`
- **Purpose:** Rate limiting & caching

## Network

All services are connected to `zanfuu_network` bridge network.

## Volumes

- `mysql-data` - MySQL data persistence
- `redis-data` - Redis data persistence

## Environment Variables

### For Docker Compose

When using Docker Compose, use service names for connections:

```env
MYSQL_HOST=mysql          # Service name
REDIS_HOST=redis          # Service name
```

### For Remote Services

If using remote MySQL/Redis:

```env
MYSQL_HOST=117.53.45.105  # Remote IP
REDIS_HOST=127.0.0.1      # Local or remote IP
```

## Troubleshooting

### MySQL Connection Failed

```bash
# Check MySQL is running
docker-compose ps mysql

# Check MySQL logs
docker-compose logs mysql

# Test connection
docker-compose exec mysql mysql -u wgadmin -pwgpassword -e "SELECT 1;"
```

### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis
docker-compose exec redis redis-cli ping
```

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Check environment variables
docker-compose exec backend env | grep -E "MYSQL|REDIS|LDAP"

# Test database connection
docker-compose exec backend python -c "from app.database.connection import test_connection; test_connection()"
```

### Migration Issues

```bash
# Verify migration status
docker-compose exec backend bash scripts/migrate.sh --verify-only

# Force re-run migration (WARNING: Deletes data!)
docker-compose exec backend bash scripts/migrate.sh --force
```

## Production Considerations

1. **Change Default Passwords** - Update all passwords in `.env`
2. **Use Strong Secrets** - Generate strong JWT_SECRET and ENCRYPTION_KEY
3. **Network Security** - Don't expose MySQL/Redis ports publicly
4. **Backup Strategy** - Setup regular database backups
5. **Monitoring** - Setup health check monitoring
6. **SSL/TLS** - Use reverse proxy (Nginx) with SSL

## Backup & Restore

### Backup Database

```bash
docker-compose exec mysql mysqldump -u wgadmin -pwgpassword wireguard_vpn > backup.sql
```

### Restore Database

```bash
docker-compose exec -T mysql mysql -u wgadmin -pwgpassword wireguard_vpn < backup.sql
```

## Useful Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: Deletes data!)
docker-compose down -v

# Rebuild backend
docker-compose build backend

# View all logs
docker-compose logs -f

# Execute command in backend container
docker-compose exec backend bash

# Execute command in MySQL container
docker-compose exec mysql mysql -u wgadmin -pwgpassword wireguard_vpn
```

