# Deployment Guide: WireGuard VPN Portal Backend

## Prerequisites

- VPS dengan Ubuntu/Debian/AlmaLinux
- Python 3.11+
- MySQL 8.0+ (remote atau local)
- Redis 7+
- OpenLDAP server
- WireGuard installed dan configured
- Nginx (untuk reverse proxy)
- SSL certificate (Let's Encrypt recommended)

## Architecture

### VPS 1: Backend Services (117.53.44.59)
- WireGuard Server
- OpenLDAP Server
- Backend API
- Frontend
- Redis

### VPS 2: Database Server (117.53.45.105)
- MySQL Server

## Step 1: Server Preparation

### Update System
```bash
sudo apt update && sudo apt upgrade -y
# atau untuk AlmaLinux
sudo dnf update -y
```

### Install Dependencies
```bash
# Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# WireGuard
sudo apt install wireguard wireguard-tools -y

# Redis
sudo apt install redis-server -y

# Nginx
sudo apt install nginx -y

# MySQL Client (untuk testing)
sudo apt install mysql-client -y
```

## Step 2: Setup MySQL (Remote Server)

Lihat `database/MYSQL_SETUP_REMOTE.md` untuk detail setup MySQL di remote server.

## Step 3: Setup OpenLDAP

Lihat `ldap/README.md` untuk detail setup LDAP schema extension.

## Step 4: Clone & Setup Backend

```bash
# Clone repository
cd /opt
sudo git clone <your-repo-url> wireguard-backend
cd wireguard-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp env.example.txt .env
nano .env  # Edit dengan credentials Anda
```

## Step 5: Configure Environment Variables

Edit `.env` file:
```bash
# LDAP
LDAP_SERVER=ldap://117.53.44.59:389
LDAP_BASE_DN=dc=example,dc=com
LDAP_ADMIN_DN=cn=admin,dc=example,dc=com
LDAP_ADMIN_PASSWORD=your_ldap_password

# MySQL (Remote)
MYSQL_HOST=117.53.45.105
MYSQL_PORT=3306
MYSQL_USER=wgadmin
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=wireguard_vpn

# JWT
JWT_SECRET=your_very_long_random_secret_key_here

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# WireGuard
WG_SERVER_PUBLIC_KEY=your_server_public_key
WG_ENDPOINT=117.53.44.59:51820

# Security
ENCRYPTION_KEY=your_32_byte_encryption_key
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

## Step 6: Database Migration

```bash
# Import schema
mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn < database/schema.sql

# Run migrations
mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn < database/migrations/add_qr_expiration.sql
mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn < database/migrations/add_performance_indexes.sql
```

## Step 7: Setup Systemd Service

```bash
# Copy service file
sudo cp systemd/wireguard-backend.service /etc/systemd/system/

# Edit service file (adjust paths)
sudo nano /etc/systemd/system/wireguard-backend.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable wireguard-backend

# Start service
sudo systemctl start wireguard-backend

# Check status
sudo systemctl status wireguard-backend
```

## Step 8: Setup Nginx Reverse Proxy

```bash
# Copy nginx config
sudo cp nginx/wireguard-backend.conf /etc/nginx/sites-available/wireguard-backend

# Edit config (change domain)
sudo nano /etc/nginx/sites-available/wireguard-backend

# Enable site
sudo ln -s /etc/nginx/sites-available/wireguard-backend /etc/nginx/sites-enabled/

# Add rate limiting zone to nginx.conf
sudo nano /etc/nginx/nginx.conf
# Add: limit_req_zone $binary_remote_addr zone=login_limit:10m rate=10r/m;

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Step 9: Setup SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already configured by certbot)
```

## Step 10: Firewall Configuration

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 51820/udp  # WireGuard
sudo ufw enable

# Firewalld (AlmaLinux)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=51820/udp
sudo firewall-cmd --reload
```

## Step 11: Verify Deployment

```bash
# Check backend service
curl http://localhost:8000/health/

# Check via Nginx
curl https://your-domain.com/health/

# Check logs
sudo journalctl -u wireguard-backend -f
```

## Step 12: Monitoring Setup

### Health Check Monitoring
Setup monitoring tool (Prometheus, Nagios, dll) untuk monitor:
- `/health/full` endpoint
- Service status
- Disk space
- Memory usage

### Log Monitoring
```bash
# View logs
sudo journalctl -u wireguard-backend -n 100

# Log rotation (already configured by systemd)
```

## Troubleshooting

### Backend tidak start
```bash
# Check logs
sudo journalctl -u wireguard-backend -n 50

# Check Python environment
source /opt/wireguard-backend/venv/bin/activate
python -c "import app.main"

# Check database connection
python -c "from app.database.connection import test_connection; test_connection()"
```

### Database connection failed
- Check MySQL firewall rules
- Verify MySQL user permissions
- Check MySQL bind-address configuration
- Test connection: `mysql -h 117.53.45.105 -u wgadmin -p`

### LDAP connection failed
- Check LDAP service: `systemctl status slapd`
- Test connection: `ldapsearch -x -H ldap://117.53.44.59:389 -b "dc=example,dc=com"`

### Redis connection failed
- Check Redis service: `systemctl status redis`
- Test connection: `redis-cli ping`

## Backup Procedures

See `docs/BACKUP_RESTORE.md` for detailed backup procedures.

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong JWT_SECRET (min 32 characters)
- [ ] Use strong ENCRYPTION_KEY (32 bytes)
- [ ] Configure firewall properly
- [ ] Enable SSL/TLS
- [ ] Set proper CORS_ORIGINS
- [ ] Regular security updates
- [ ] Monitor audit logs
- [ ] Setup log rotation
- [ ] Regular backups
