# 🐳 Docker Production Deployment Guide

Panduan lengkap untuk deployment WireGuard VPN Portal Backend menggunakan Docker di production.

## 📋 Prerequisites

1. **Docker** (version 20.10+)
2. **Docker Compose** (version 2.0+)
3. **Nginx** (untuk reverse proxy dan SSL termination)
4. **MySQL Database** (remote atau local)
5. **Redis** (untuk rate limiting, bisa via docker-compose)

## 🚀 Quick Start

### 1. Setup Environment Variables

```bash
# Copy production environment template
cp .env.production.example .env.production

# Edit .env.production dengan credentials Anda
nano .env.production
```

**⚠️ IMPORTANT:** Jangan commit `.env.production` ke git! File ini berisi secrets.

### 2. Generate Secrets

```bash
# Generate JWT Secret
python -c "import secrets; print(secrets.token_hex(32))"

# Generate Encryption Key
python -c "import secrets; print(secrets.token_hex(32))"

# Generate Redis Password
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy hasilnya ke file `.env.production`.

### 3. Prepare Directories

```bash
# Create directories untuk logs dan data
sudo mkdir -p /var/log/wireguard-backend
sudo mkdir -p /var/lib/wireguard/redis-data
sudo mkdir -p /etc/wireguard

# Set permissions
sudo chown -R $USER:$USER /var/log/wireguard-backend
sudo chown -R $USER:$USER /var/lib/wireguard/redis-data
```

### 4. Build Docker Image

```bash
# Build image untuk production
docker build -t wireguard-backend:latest .

# Atau build dengan docker-compose
docker-compose -f docker-compose.prod.yml build
```

### 5. Start Services

```bash
# Start semua services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

## 🔧 Configuration

### Environment Variables

File `.env.production` berisi semua konfigurasi yang diperlukan:

- **LDAP**: LDAP server connection
- **MySQL**: Database connection (remote VPS)
- **WireGuard**: WireGuard server configuration
- **JWT**: Authentication secrets
- **Redis**: Rate limiting configuration
- **Security**: CORS origins, device limits, etc.

### Resource Limits

Production compose file sudah dikonfigurasi dengan resource limits:

- **Backend**: Max 2 CPU, 2GB RAM
- **Redis**: Max 1 CPU, 512MB RAM

Anda bisa adjust sesuai kebutuhan di `docker-compose.prod.yml`.

### Networking

- Backend service bind ke `127.0.0.1:8000` (localhost only)
- Gunakan Nginx sebagai reverse proxy untuk public access
- Internal network menggunakan bridge mode dengan subnet `172.20.0.0/16`

## 🔒 Security Best Practices

### 1. Non-Root User

Container berjalan dengan non-root user (UID 1000) untuk security.

### 2. Read-Only Filesystem

WireGuard config mounted sebagai read-only (`/etc/wireguard:/etc/wireguard:ro`).

### 3. Network Isolation

Services hanya expose ke localhost, bukan ke public interface.

### 4. Secrets Management

- Gunakan `.env.production` untuk secrets (tidak commit ke git)
- Atau gunakan Docker secrets untuk Docker Swarm
- Atau gunakan external secret management (Vault, AWS Secrets Manager)

### 5. Logging

Logs di-rotate otomatis:
- Max size: 10MB per file
- Max files: 3 (total ~30MB logs)

## 📊 Monitoring & Health Checks

### Health Checks

Health checks sudah dikonfigurasi:

```bash
# Check health status
docker-compose -f docker-compose.prod.yml ps

# Manual health check
curl http://localhost:8000/health/
```

### Logging

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs

# Follow logs
docker-compose -f docker-compose.prod.yml logs -f backend

# View last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Resource Monitoring

```bash
# Check resource usage
docker stats wireguard-backend-prod wireguard-redis-prod
```

## 🔄 Updates & Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose -f docker-compose.prod.yml build

# Restart services dengan zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps backend
```

### Backup

```bash
# Backup Redis data
docker exec wireguard-redis-prod redis-cli SAVE
docker cp wireguard-redis-prod:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb

# Backup logs (jika perlu)
tar -czf backup/logs-$(date +%Y%m%d).tar.gz /var/log/wireguard-backend/
```

### Database Migration

Database migrations harus dijalankan secara manual:

```bash
# Connect ke backend container
docker exec -it wireguard-backend-prod bash

# Run migrations (jika ada script)
python -m database.migrations.run_migrations
```

## 🌐 Nginx Reverse Proxy Setup

### 1. Install Nginx

```bash
sudo apt-get update
sudo apt-get install nginx certbot python3-certbot-nginx
```

### 2. Setup SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com
```

### 3. Configure Nginx

Copy config dari `nginx/wireguard-backend.conf` ke `/etc/nginx/sites-available/`:

```bash
sudo cp nginx/wireguard-backend.conf /etc/nginx/sites-available/wireguard-backend
sudo ln -s /etc/nginx/sites-available/wireguard-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Update CORS_ORIGINS

Pastikan `CORS_ORIGINS` di `.env.production` sesuai dengan domain Anda:

```
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

## 🛠️ Troubleshooting

### Container tidak start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check container status
docker inspect wireguard-backend-prod
```

### Database connection failed

```bash
# Test connection dari container
docker exec -it wireguard-backend-prod python -c "from app.database.connection import test_connection; test_connection()"

# Check network connectivity
docker exec -it wireguard-backend-prod ping $MYSQL_HOST
```

### Redis connection failed

```bash
# Test Redis connection
docker exec -it wireguard-redis-prod redis-cli ping

# Check Redis logs
docker-compose -f docker-compose.prod.yml logs redis
```

### Permission issues

```bash
# Check file permissions
docker exec -it wireguard-backend-prod ls -la /app/logs

# Fix permissions (jika perlu)
sudo chown -R 1000:1000 /var/log/wireguard-backend
```

## 📝 Production Checklist

- [ ] `.env.production` dikonfigurasi dengan benar
- [ ] Semua secrets di-generate (JWT_SECRET, ENCRYPTION_KEY, REDIS_PASSWORD)
- [ ] Resource limits sesuai kebutuhan
- [ ] Health checks working
- [ ] Logging configured dan monitored
- [ ] Nginx reverse proxy setup dengan SSL
- [ ] CORS_ORIGINS configured untuk domain production
- [ ] Database connection tested
- [ ] Redis connection tested
- [ ] Firewall rules configured (allow port 443, 80)
- [ ] Backup strategy in place
- [ ] Monitoring & alerting setup
- [ ] Documentation updated

## 🔗 Related Files

- `Dockerfile` - Docker image definition
- `docker-compose.prod.yml` - Production compose configuration
- `docker-entrypoint.sh` - Container startup script
- `.env.production.example` - Environment variables template
- `nginx/wireguard-backend.conf` - Nginx reverse proxy config

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)

---

**Note:** Untuk environment development, gunakan `docker-compose.yml` (file default). Untuk production, selalu gunakan `docker-compose.prod.yml`.
