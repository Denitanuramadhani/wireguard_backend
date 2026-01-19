# Production Deployment Checklist

## Pre-Deployment

### ✅ Environment Setup
- [ ] `.env` file created and configured
- [ ] All required environment variables set
- [ ] `JWT_SECRET` generated (min 32 chars)
- [ ] `ENCRYPTION_KEY` generated (32 bytes)
- [ ] `CORS_ORIGINS` configured (no wildcard `*`)
- [ ] `DEBUG=False` for production
- [ ] `ENVIRONMENT=production`

### ✅ Database
- [ ] MySQL server accessible
- [ ] Database user created with proper permissions
- [ ] Database `wireguard_vpn` created
- [ ] Database connection tested
- [ ] Backup strategy in place

### ✅ LDAP
- [ ] LDAP server accessible
- [ ] LDAP admin credentials configured
- [ ] WireGuard schema installed (`scripts/setup_ldap_schema.sh`)
- [ ] LDAP connection tested
- [ ] Existing users migrated (if any)

### ✅ Security
- [ ] All default passwords changed
- [ ] Strong passwords for all services
- [ ] Firewall configured (ports 80, 443, 51820)
- [ ] SSL/TLS certificate ready (Let's Encrypt)
- [ ] CORS origins restricted
- [ ] Rate limiting configured

## Deployment Steps

### 1. Pre-Deployment Check
```bash
cd wireguard_backend
bash scripts/pre_deploy_check.sh
```

**Expected:** All checks pass or only warnings (no failures)

### 2. Database Migration
```bash
# Option A: Using migration runner (recommended)
cd wireguard_backend
source venv/bin/activate
python -m database.migrations.migration_runner

# Option B: Manual migration
mysql -h $MYSQL_HOST -u $MYSQL_USER -p $MYSQL_DATABASE < database/schema.sql
python -m database.migrations.migration_runner
```

**Verify:**
```bash
python -m database.migrations.migration_runner --list
# Should show all migrations as [APPLIED]
```

### 3. LDAP Setup
```bash
# Install schema (on LDAP server)
sudo bash scripts/setup_ldap_schema.sh

# Migrate existing users (if any)
LDAP_ADMIN_PASSWORD=your_password bash scripts/migrate_ldap_users.sh

# Seed initial users (optional)
LDAP_ADMIN_PASSWORD=your_password bash scripts/seed_ldap_users.sh users.csv
```

### 4. Deploy Application

#### Option A: Systemd
```bash
# Copy service file
sudo cp systemd/wireguard-backend.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/wireguard-backend.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable wireguard-backend
sudo systemctl start wireguard-backend

# Check status
sudo systemctl status wireguard-backend
```

#### Option B: Docker
```bash
# Build and start
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

#### Option C: Automated Script
```bash
bash scripts/deploy_production.sh --mode systemd
# or
bash scripts/deploy_production.sh --mode docker
```

### 5. Nginx Reverse Proxy
```bash
# Install Nginx
sudo apt-get install nginx certbot python3-certbot-nginx

# Copy config
sudo cp nginx/wireguard-backend.conf /etc/nginx/sites-available/wireguard-backend
sudo ln -s /etc/nginx/sites-available/wireguard-backend /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload
sudo systemctl reload nginx

# Setup SSL
sudo certbot --nginx -d your-domain.com
```

### 6. Verify Deployment
```bash
# Health check
curl http://localhost:8000/health/
curl https://your-domain.com/health/

# Check logs
sudo journalctl -u wireguard-backend -f
# or
docker-compose -f docker-compose.prod.yml logs -f
```

## Post-Deployment

### ✅ Monitoring
- [ ] Health checks working
- [ ] Logs accessible and rotating
- [ ] Monitoring alerts configured
- [ ] Disk space monitoring
- [ ] Memory usage monitoring

### ✅ Testing
- [ ] API endpoints accessible
- [ ] Authentication working
- [ ] Device creation working
- [ ] QR code generation working
- [ ] Admin endpoints working

### ✅ Documentation
- [ ] Deployment documented
- [ ] Credentials stored securely
- [ ] Backup procedures documented
- [ ] Rollback procedures documented

## Quick Commands

### Check Deployment Status
```bash
# Pre-deployment check
bash scripts/pre_deploy_check.sh

# Migration status
python -m database.migrations.migration_runner --list

# LDAP users status
bash scripts/migrate_ldap_users.sh --verify-only

# Service status (systemd)
sudo systemctl status wireguard-backend

# Service status (Docker)
docker-compose -f docker-compose.prod.yml ps
```

### Common Issues

#### Database Connection Failed
```bash
# Test connection
mysql -h $MYSQL_HOST -u $MYSQL_USER -p

# Check firewall
telnet $MYSQL_HOST 3306
```

#### LDAP Connection Failed
```bash
# Test connection
ldapsearch -x -H $LDAP_SERVER -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD \
  -b $LDAP_BASE_DN -s base "(objectClass=*)"
```

#### Service Won't Start
```bash
# Check logs
sudo journalctl -u wireguard-backend -n 50

# Check Python environment
source venv/bin/activate
python -c "import app.main"

# Check dependencies
pip list | grep -E "fastapi|pymysql|ldap3"
```

## Rollback Procedure

### If Deployment Fails

1. **Stop service**
   ```bash
   sudo systemctl stop wireguard-backend
   # or
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Restore database** (if needed)
   ```bash
   mysql -h $MYSQL_HOST -u $MYSQL_USER -p $MYSQL_DATABASE < backups/db_backup_YYYYMMDD_HHMMSS.sql
   ```

3. **Revert code**
   ```bash
   git checkout <previous-commit>
   ```

4. **Restart service**
   ```bash
   sudo systemctl start wireguard-backend
   # or
   docker-compose -f docker-compose.prod.yml up -d
   ```

## Security Checklist

- [ ] All secrets in `.env` (not committed to git)
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] Strong passwords for all services
- [ ] Firewall configured
- [ ] SSL/TLS enabled
- [ ] CORS restricted to specific domains
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Regular security updates scheduled

## Maintenance

### Regular Tasks
- [ ] Weekly database backups
- [ ] Monthly security updates
- [ ] Quarterly password rotation
- [ ] Monitor disk space
- [ ] Review audit logs
- [ ] Check error logs

### Updates
```bash
# Pull latest code
git pull

# Run migrations (if any)
python -m database.migrations.migration_runner

# Restart service
sudo systemctl restart wireguard-backend
# or
docker-compose -f docker-compose.prod.yml up -d --no-deps backend
```

---

**Last Updated:** $(date +%Y-%m-%d)
**Version:** 1.0

