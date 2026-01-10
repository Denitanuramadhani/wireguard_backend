# 🗄️ Setup MySQL di VPS Remote (AlmaLinux)

## Server Information

- **MySQL Server IP:** 117.53.45.105
- **OS:** AlmaLinux
- **Purpose:** Menyimpan data VPN devices (device, key, IP, status)
- **Note:** User identity & role tetap di LDAP (117.53.44.59)

## Step 1: Install MySQL di VPS Remote

```bash
# Login ke VPS MySQL (117.53.45.105)
ssh user@117.53.45.105

# Update system
sudo dnf update -y

# Install MySQL Server
sudo dnf install mysql-server -y

# Start MySQL service
sudo systemctl start mysqld
sudo systemctl enable mysqld

# Check status
sudo systemctl status mysqld
```

## Step 2: Secure MySQL Installation

```bash
# Run MySQL secure installation
sudo mysql_secure_installation

# Follow prompts:
# - Set root password
# - Remove anonymous users: Yes
# - Disallow root login remotely: Yes (optional, tergantung kebutuhan)
# - Remove test database: Yes
# - Reload privilege tables: Yes
```

## Step 3: Create Database dan User

```bash
# Login sebagai root
sudo mysql -u root -p

# Create database
CREATE DATABASE wireguard_vpn CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Create user untuk remote access dari 117.53.44.59
CREATE USER 'wgadmin'@'117.53.44.59' IDENTIFIED BY 'your_strong_password_here';

# Grant privileges
GRANT ALL PRIVILEGES ON wireguard_vpn.* TO 'wgadmin'@'117.53.44.59';

# Atau jika ingin allow dari semua IP (kurang secure, hanya untuk testing)
# CREATE USER 'wgadmin'@'%' IDENTIFIED BY 'your_strong_password_here';
# GRANT ALL PRIVILEGES ON wireguard_vpn.* TO 'wgadmin'@'%';

# Flush privileges
FLUSH PRIVILEGES;

# Verify
SHOW DATABASES;
SELECT user, host FROM mysql.user WHERE user = 'wgadmin';

EXIT;
```

## Step 4: Configure MySQL untuk Remote Access

```bash
# Edit MySQL config
sudo vi /etc/my.cnf.d/mysql-server.cnf

# Atau jika file tidak ada:
sudo vi /etc/my.cnf

# Tambahkan/modify:
[mysqld]
bind-address = 0.0.0.0  # Allow connections from any IP
# atau
bind-address = 117.53.44.59  # Hanya allow dari backend server

# Restart MySQL
sudo systemctl restart mysqld
```

## Step 5: Configure Firewall (Firewalld)

```bash
# Check firewall status
sudo firewall-cmd --state

# Allow MySQL port (3306) dari backend server
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="117.53.44.59" port port="3306" protocol="tcp" accept'

# Atau allow dari semua IP (kurang secure)
# sudo firewall-cmd --permanent --add-service=mysql

# Reload firewall
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-all
```

## Step 6: Import Database Schema

```bash
# Di VPS Backend (117.53.44.59), copy schema file ke MySQL server
scp database/schema.sql user@117.53.45.105:/tmp/

# Atau langsung import dari backend server
mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn < database/schema.sql

# Verify tables
mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn -e "SHOW TABLES;"
```

## Step 7: Test Connection dari Backend Server

```bash
# Di VPS Backend (117.53.44.59)
# Test connection
mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn -e "SELECT 1;"

# Atau dari Python
python -c "from app.database.connection import test_connection; test_connection()"
```

## Step 8: Security Best Practices

### 1. SSL/TLS Connection (Recommended)

```bash
# Di MySQL server, generate SSL certificates
sudo mysql_ssl_rsa_setup --uid=mysql

# Update user untuk require SSL
mysql -u root -p
ALTER USER 'wgadmin'@'117.53.44.59' REQUIRE SSL;
FLUSH PRIVILEGES;
```

### 2. Limit Connection Rate

```bash
# Di MySQL server
mysql -u root -p

# Set max connections per user
ALTER USER 'wgadmin'@'117.53.44.59' WITH MAX_CONNECTIONS_PER_HOUR 100;
FLUSH PRIVILEGES;
```

### 3. Enable Query Logging (Optional, untuk debugging)

```bash
# Edit MySQL config
sudo vi /etc/my.cnf.d/mysql-server.cnf

[mysqld]
general_log = 1
general_log_file = /var/log/mysql/general.log

# Restart MySQL
sudo systemctl restart mysqld
```

## Step 9: Backup Strategy

```bash
# Create backup script
sudo vi /root/backup_wireguard_db.sh

#!/bin/bash
BACKUP_DIR="/backup/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="wireguard_vpn"
DB_USER="wgadmin"
DB_PASS="your_password"

mkdir -p $BACKUP_DIR
mysqldump -h localhost -u $DB_USER -p$DB_PASS $DB_NAME > $BACKUP_DIR/wireguard_vpn_$DATE.sql

# Compress
gzip $BACKUP_DIR/wireguard_vpn_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# Make executable
chmod +x /root/backup_wireguard_db.sh

# Add to crontab (daily backup at 2 AM)
crontab -e
0 2 * * * /root/backup_wireguard_db.sh
```

## Troubleshooting

### Connection Refused
```bash
# Check MySQL is listening
sudo netstat -tlnp | grep 3306

# Check firewall
sudo firewall-cmd --list-all

# Check MySQL bind address
sudo grep bind-address /etc/my.cnf
```

### Access Denied
```bash
# Check user privileges
mysql -u root -p
SELECT user, host FROM mysql.user WHERE user = 'wgadmin';
SHOW GRANTS FOR 'wgadmin'@'117.53.44.59';
```

### Timeout Issues
```bash
# Increase timeout di MySQL config
sudo vi /etc/my.cnf.d/mysql-server.cnf

[mysqld]
wait_timeout = 600
interactive_timeout = 600
max_connections = 200

# Restart MySQL
sudo systemctl restart mysqld
```

## Verification Checklist

- [ ] MySQL service running
- [ ] Database `wireguard_vpn` created
- [ ] User `wgadmin` created dengan IP restriction
- [ ] Firewall configured untuk allow port 3306
- [ ] Schema imported successfully
- [ ] Connection test dari backend server berhasil
- [ ] Backup script configured
- [ ] SSL/TLS configured (optional tapi recommended)

## Notes

- **Security:** Selalu gunakan strong password untuk database user
- **Network:** Pastikan network antara 117.53.44.59 dan 117.53.45.105 bisa communicate
- **Monitoring:** Setup monitoring untuk MySQL server (disk space, CPU, memory)
- **Backup:** Regular backup sangat penting untuk production

---

*Setup ini untuk MySQL server di VPS terpisah. Pastikan network security sudah dikonfigurasi dengan benar.*
