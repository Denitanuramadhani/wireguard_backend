# Backup & Restore Procedures

## Backup Strategy

### 1. Database Backup (MySQL)

#### Automated Backup Script
```bash
#!/bin/bash
# backup-mysql.sh

BACKUP_DIR="/backup/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="wireguard_vpn"
DB_USER="wgadmin"
DB_HOST="117.53.45.105"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD \
    --single-transaction \
    --routines \
    --triggers \
    $DB_NAME > $BACKUP_DIR/wireguard_vpn_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/wireguard_vpn_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: wireguard_vpn_$DATE.sql.gz"
```

#### Setup Cron Job
```bash
# Add to crontab
0 2 * * * /opt/wireguard-backend/scripts/backup-mysql.sh
```

### 2. LDAP Backup

```bash
#!/bin/bash
# backup-ldap.sh

BACKUP_DIR="/backup/ldap"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup LDAP data
slapcat -n 2 > $BACKUP_DIR/ldap_$DATE.ldif

# Compress
gzip $BACKUP_DIR/ldap_$DATE.ldif

# Keep only last 30 days
find $BACKUP_DIR -name "*.ldif.gz" -mtime +30 -delete

echo "LDAP backup completed: ldap_$DATE.ldif.gz"
```

### 3. Configuration Backup

```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR="/backup/config"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup .env (encrypted atau exclude dari backup)
# Backup nginx config
sudo cp /etc/nginx/sites-available/wireguard-backend $BACKUP_DIR/nginx_$DATE.conf

# Backup systemd service
sudo cp /etc/systemd/system/wireguard-backend.service $BACKUP_DIR/service_$DATE.service

# Backup WireGuard config
sudo cp /etc/wireguard/wg0.conf $BACKUP_DIR/wg0_$DATE.conf

# Create archive
tar -czf $BACKUP_DIR/config_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*

# Keep only last 7 days
find $BACKUP_DIR -name "config_*.tar.gz" -mtime +7 -delete
```

## Restore Procedures

### 1. Restore Database

```bash
# Stop backend service
sudo systemctl stop wireguard-backend

# Restore database
gunzip < /backup/mysql/wireguard_vpn_20240101_020000.sql.gz | \
    mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn

# Start backend service
sudo systemctl start wireguard-backend

# Verify
curl http://localhost:8000/health/database
```

### 2. Restore LDAP

```bash
# Stop LDAP service
sudo systemctl stop slapd

# Restore LDAP
gunzip < /backup/ldap/ldap_20240101_020000.ldif.gz | \
    slapadd -n 2

# Fix permissions
sudo chown -R openldap:openldap /var/lib/ldap

# Start LDAP service
sudo systemctl start slapd

# Verify
ldapsearch -x -H ldap://localhost:389 -b "dc=example,dc=com"
```

### 3. Restore Configuration

```bash
# Extract backup
tar -xzf /backup/config/config_20240101_020000.tar.gz

# Restore nginx config
sudo cp nginx_20240101_020000.conf /etc/nginx/sites-available/wireguard-backend
sudo nginx -t
sudo systemctl reload nginx

# Restore systemd service
sudo cp service_20240101_020000.service /etc/systemd/system/wireguard-backend.service
sudo systemctl daemon-reload
sudo systemctl restart wireguard-backend

# Restore WireGuard config
sudo cp wg0_20240101_020000.conf /etc/wireguard/wg0.conf
sudo systemctl restart wg-quick@wg0
```

## Disaster Recovery

### Full System Restore

1. **Restore VPS**
   - Setup new VPS dengan same specifications
   - Install semua dependencies
   - Restore configurations

2. **Restore Database**
   - Setup MySQL
   - Restore database dari backup

3. **Restore LDAP**
   - Setup OpenLDAP
   - Restore LDAP data

4. **Restore Backend**
   - Clone repository
   - Restore .env file
   - Restore configurations
   - Start services

5. **Verify**
   - Check health endpoints
   - Test authentication
   - Test device operations

## Backup Retention Policy

- **Daily backups:** Keep for 7 days
- **Weekly backups:** Keep for 4 weeks
- **Monthly backups:** Keep for 12 months

## Backup Verification

```bash
# Verify database backup
gunzip -t /backup/mysql/wireguard_vpn_*.sql.gz

# Verify LDAP backup
gunzip -t /backup/ldap/ldap_*.ldif.gz

# Test restore (on test server)
# Always test restore procedures on test environment first
```
