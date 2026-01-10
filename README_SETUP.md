# 🚀 Setup Guide: WireGuard VPN Portal Backend

## Prerequisites

- Python 3.8+
- MySQL 5.7+ atau MariaDB 10.3+
- Redis (untuk rate limiting)
- OpenLDAP server
- WireGuard installed di server

## Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

## Step 2: Setup MySQL Database

**MySQL Server:** 117.53.45.105 (VPS terpisah - AlmaLinux)  
**Backend Server:** 117.53.44.59 (WireGuard, LDAP, Backend, Frontend)

Lihat file `database/MYSQL_SETUP_REMOTE.md` untuk instruksi lengkap setup MySQL di VPS remote.

**Quick Setup:**
```bash
# Di MySQL Server (117.53.45.105)
sudo mysql -u root -p
CREATE DATABASE wireguard_vpn CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'wgadmin'@'117.53.44.59' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON wireguard_vpn.* TO 'wgadmin'@'117.53.44.59';
FLUSH PRIVILEGES;
EXIT;

# Import schema dari Backend Server (117.53.44.59)
mysql -h 117.53.45.105 -u wgadmin -p wireguard_vpn < database/schema.sql
```

## Step 3: Setup Environment Variables

```bash
# Copy .env.example ke .env
cp .env.example .env

# Edit .env dan isi dengan konfigurasi Anda:
# - LDAP credentials
# - MySQL credentials
# - JWT secret (generate baru dengan: openssl rand -hex 32)
# - WireGuard config
```

## Step 4: Generate JWT Secret

```bash
# Generate secure JWT secret
openssl rand -hex 32

# Copy hasilnya ke .env file sebagai JWT_SECRET
```

## Step 5: Test Database Connection

```bash
# Run Python untuk test connection
python -c "from app.database.connection import test_connection; test_connection()"
```

## Step 6: Setup LDAP Schema Extension

Lihat file `plan.md` untuk instruksi lengkap tentang LDAP schema extension.

## Step 7: Run Application

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode (dengan gunicorn)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Step 8: Verify Installation

```bash
# Test API endpoint
curl http://localhost:8000/

# Expected response:
# {"message": "Backend is running"}
```

## Troubleshooting

### Database Connection Error
- Pastikan MySQL service running: `sudo systemctl status mysql`
- Check credentials di .env file
- Test connection manual: `mysql -u wgadmin -p wireguard_vpn`

### LDAP Connection Error
- Pastikan LDAP server accessible
- Check LDAP_SERVER di .env
- Test dengan: `ldapsearch -x -H ldap://your-ldap-server:389 -b "dc=example,dc=com"`

### Redis Connection Error
- Pastikan Redis running: `redis-cli ping`
- Should return: `PONG`

## Next Steps

Setelah setup selesai, lanjutkan ke Phase 2: LDAP Schema Extension sesuai plan.md
