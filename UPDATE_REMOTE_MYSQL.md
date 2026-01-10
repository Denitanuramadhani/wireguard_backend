# ✅ Update: Remote MySQL Configuration

## 📋 Perubahan yang Dilakukan

### 1. ✅ Update Configuration untuk Remote MySQL
- **File:** `app/config.py`
- **Changes:**
  - Default `MYSQL_HOST` diubah dari `localhost` ke `117.53.45.105`
  - Tambah `MYSQL_CONNECT_TIMEOUT` untuk remote connection
  - Tambah comment menjelaskan bahwa MySQL hanya untuk device data, bukan user identity

### 2. ✅ Update Database Connection
- **File:** `app/database/connection.py`
- **Changes:**
  - Tambah timeout configuration untuk remote connection
  - Tambah `read_timeout` dan `write_timeout` (30 detik)
  - Improve error logging dengan IP address

### 3. ✅ Update Environment Template
- **File:** `env.example.txt`
- **Changes:**
  - Default `MYSQL_HOST` = `117.53.45.105`
  - Tambah `MYSQL_CONNECT_TIMEOUT=10`

### 4. ✅ Documentation
- **Files Created:**
  - `database/MYSQL_SETUP_REMOTE.md` - Setup guide lengkap untuk MySQL di VPS remote
  - `ARCHITECTURE.md` - Architecture overview dengan penjelasan separation of concerns
- **Files Updated:**
  - `README_SETUP.md` - Update dengan referensi ke remote MySQL setup

## 🏗️ Architecture Summary

### VPS 1: Backend Services (117.53.44.59)
**Services:**
- WireGuard Server
- OpenLDAP Server (User identity & authentication)
- Backend API (FastAPI)
- Frontend
- Redis

**Data Stored:**
- ✅ User identity (LDAP)
- ✅ User passwords (LDAP)
- ✅ User roles/groups (LDAP)
- ✅ Authentication data (LDAP)

### VPS 2: Database Server (117.53.45.105)
**Services:**
- MySQL Server (AlmaLinux)

**Data Stored:**
- ✅ Device information
- ✅ WireGuard keys (public key)
- ✅ IP allocations
- ✅ VPN status
- ✅ Traffic logs
- ✅ Audit logs

**Data NOT Stored:**
- ❌ User identity (tetap di LDAP)
- ❌ User passwords (tetap di LDAP)
- ❌ User roles/groups (tetap di LDAP)

## 📝 Database Schema Notes

Schema MySQL **hanya** menyimpan:
1. **Device** - device_name, public_key, vpn_ip
2. **Key** - public_key (private key tidak disimpan di MySQL)
3. **IP** - vpn_ip allocation
4. **Status VPN** - status (active, revoked, expired)

**Reference ke LDAP:**
- `ldap_uid` di tabel `vpn_devices` hanya sebagai **reference** ke username di LDAP
- Tidak menyimpan user identity di MySQL
- Semua user identity tetap di LDAP

## 🔧 Next Steps

### 1. Setup MySQL di VPS Remote (117.53.45.105)
Ikuti instruksi di `database/MYSQL_SETUP_REMOTE.md`:
- Install MySQL Server
- Create database dan user
- Configure firewall
- Import schema

### 2. Update .env File
```bash
# Di Backend Server (117.53.44.59)
cp env.example.txt .env

# Edit .env:
MYSQL_HOST=117.53.45.105
MYSQL_USER=wgadmin
MYSQL_PASSWORD=your_strong_password_here
```

### 3. Test Connection
```bash
# Dari Backend Server (117.53.44.59)
python -c "from app.database.connection import test_connection; test_connection()"
```

### 4. Verify Network Connectivity
```bash
# Test dari Backend Server ke MySQL Server
telnet 117.53.45.105 3306
# atau
nc -zv 117.53.45.105 3306
```

## ⚠️ Important Notes

1. **Security:**
   - Pastikan firewall di MySQL server hanya allow connection dari 117.53.44.59
   - Gunakan strong password untuk database user
   - Consider SSL/TLS untuk MySQL connection

2. **Network:**
   - Pastikan network antara kedua VPS bisa communicate
   - Port 3306 harus accessible dari backend server
   - Check firewall rules di kedua VPS

3. **Performance:**
   - Remote MySQL connection akan lebih lambat daripada localhost
   - Connection timeout sudah di-set untuk handle network latency
   - Consider connection pooling untuk optimize performance

## ✅ Verification Checklist

- [ ] MySQL installed di VPS 117.53.45.105
- [ ] Database `wireguard_vpn` created
- [ ] User `wgadmin` created dengan IP restriction (117.53.44.59)
- [ ] Firewall configured
- [ ] Schema imported
- [ ] .env file updated dengan MySQL credentials
- [ ] Connection test berhasil dari backend server
- [ ] Network connectivity verified

---

*Semua perubahan sudah selesai. Siap untuk setup MySQL di VPS remote!*
