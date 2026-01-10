# Analisis Proyek: Sistem VPN WireGuard dengan Portal LDAP Authentication

## 📋 RINGKASAN FITUR YANG SUDAH DIIMPLEMENTASI

### 1. **Sistem Autentikasi**
- ✅ LDAP Authentication (`app/services/ldap_auth.py`)
- ✅ JWT Token System dengan Access Token & Refresh Token
- ✅ Rate Limiting untuk endpoint login (100 requests/60 detik)
- ✅ Middleware untuk verifikasi JWT token
- ✅ Logging aktivitas login (success/failed)

### 2. **Manajemen WireGuard**
- ✅ Generate keypair WireGuard (private & public key)
- ✅ Generate konfigurasi client (.conf file)
- ✅ Generate QR Code untuk mobile
- ✅ Alokasi IP otomatis (10.8.0.2 - 10.8.0.250)
- ✅ Menambahkan peer ke WireGuard server (`wg set`)
- ✅ Menghapus peer dari WireGuard server
- ✅ Monitoring peers aktif (`wg show wg0 dump`)

### 3. **Portal Admin**
- ✅ List semua pengguna yang terdaftar
- ✅ Tambah user baru ke LDAP + WireGuard
- ✅ Hapus user (hapus dari LDAP, WireGuard, dan file config)
- ✅ Monitoring IP usage

### 4. **Portal User**
- ✅ Generate konfigurasi VPN sendiri
- ✅ Download file konfigurasi (.conf)
- ✅ Lihat QR Code
- ✅ Lihat IP yang dialokasikan
- ✅ Cleanup konfigurasi sendiri

### 5. **Keamanan & Rate Limiting**
- ✅ Rate limiting dengan Redis
- ✅ JWT token expiration (1 jam untuk access token, 24 jam untuk refresh token)
- ✅ Authorization header verification
- ✅ User hanya bisa akses data miliknya sendiri

### 6. **Logging**
- ✅ Logging aktivitas ke file `backend.log`
- ✅ Mencatat IP address pengguna
- ✅ Mencatat waktu dan aktivitas

---

## ⚠️ KELEMAHAN & MASALAH KEAMANAN

### 🔴 **KRITIS - Keamanan**

#### 1. **Hardcoded Credentials & Secrets**
```python
# app/config.py
JWT_SECRET = "6fa6969e55e9b8d5fce4e1117fe1f95ee42e47f50dd6d5dc781a9423e70b3e7f"  # Hardcoded!
LDAP_ADMIN_PASS = "_l3Rum*Foca"  # Hardcoded di admin_add_user.py
```
**Masalah:** Secret key dan password ter-expose di source code
**Solusi:** Gunakan environment variables atau file `.env` yang di-ignore oleh git

#### 2. **CORS Terlalu Permisif**
```python
# app/main.py
allow_origins=["*"]  # ⚠️ Semua origin diizinkan!
```
**Masalah:** Siapa saja bisa mengakses API dari browser
**Solusi:** Batasi ke domain frontend yang spesifik, contoh: `allow_origins=["https://vpn.example.com"]`

#### 3. **Admin List Hardcoded**
```python
# app/middleware/auth_middleware.py
ADMIN_LIST = ["denita"]  # Hardcoded!
```
**Masalah:** Admin harus di-hardcode, tidak fleksibel
**Solusi:** Ambil dari LDAP group (misalnya `cn=admins,ou=groups,dc=example,dc=com`) atau database

#### 4. **LDAP Password di Source Code**
```python
# app/routers/admin_add_user.py
LDAP_ADMIN_PASS = "_l3Rum*Foca"  # ⚠️ Hardcoded!
```
**Masalah:** Password LDAP admin ter-expose
**Solusi:** Pindahkan ke environment variable

#### 5. **Tidak Ada Input Validation**
- Username tidak divalidasi (bisa mengandung karakter berbahaya)
- Password tidak ada policy (minimal length, complexity)
- IP address tidak divalidasi sebelum digunakan

#### 6. **Error Handling Lemah**
```python
# Banyak tempat menggunakan bare except:
except:
    pass  # ⚠️ Menyembunyikan error!
```
**Masalah:** Error disembunyikan, sulit debugging
**Solusi:** Log error dan return error message yang jelas

#### 7. **Race Condition pada IP Allocation**
```python
# app/wg/ip_manager.py
def allocate_ip(username):
    data = load_ips()  # Read
    # ... logic ...
    save_ips(data)  # Write
```
**Masalah:** Jika 2 request bersamaan, bisa dapat IP yang sama
**Solusi:** Gunakan file locking atau database dengan transaction

#### 8. **Tidak Ada HTTPS Enforcement**
**Masalah:** API bisa diakses via HTTP, credentials bisa di-intercept
**Solusi:** Gunakan HTTPS dan redirect HTTP ke HTTPS

#### 9. **SQL Injection Risk (meskipun pakai JSON)**
Meskipun menggunakan JSON file, tidak ada sanitization untuk username yang digunakan di file path:
```python
path = f"generated_configs/{username}.conf"  # ⚠️ Path traversal possible!
```
**Masalah:** Username seperti `../../etc/passwd` bisa mengakses file lain
**Solusi:** Validasi dan sanitize username sebelum digunakan

#### 10. **Command Injection Risk**
```python
subprocess.run(["sudo", "wg", "set", "wg0", "peer", public_key, ...])
```
**Masalah:** Jika `public_key` tidak divalidasi, bisa injection command
**Solusi:** Validasi format public key WireGuard sebelum digunakan

### 🟡 **MEDIUM - Masalah Kode**

#### 11. **Duplikasi JWT Handler**
Ada 2 file JWT handler:
- `app/auth/jwt_handler.py` (tidak digunakan?)
- `app/middleware/auth_middleware.py` (yang digunakan)
**Solusi:** Hapus yang tidak digunakan atau konsolidasi

#### 12. **Dummy/Mock Code Masih Ada**
```python
# app/core/ldap_client.py - Semua di-comment, ada dummy code
# app/wg/keygen.py - Ada mock_key() function
```
**Masalah:** Code dummy masih ada, bisa membingungkan
**Solusi:** Hapus atau dokumentasikan dengan jelas

#### 13. **Tidak Ada Database**
Menggunakan JSON file untuk storage:
- `allocated_ips.json`
- File config di filesystem
**Masalah:** Tidak scalable, tidak ada backup otomatis, tidak ada transaction
**Solusi:** Migrate ke database (PostgreSQL/SQLite)

#### 14. **Tidak Ada Unit Tests**
**Masalah:** Tidak ada testing, sulit memastikan kode bekerja dengan benar
**Solusi:** Tambahkan unit tests dan integration tests

#### 15. **Logging Tidak Terstruktur**
```python
logger.info(f"LOGIN attempt by username={username}")
```
**Masalah:** Format log tidak konsisten, tidak ada structured logging
**Solusi:** Gunakan structured logging (JSON format) untuk memudahkan parsing

#### 16. **Tidak Ada Request ID/Trace ID**
**Masalah:** Sulit tracking request di log
**Solusi:** Tambahkan request ID untuk setiap request

#### 17. **Cleanup Endpoint Tidak Konsisten**
```python
# app/routers/cleanup.py - User bisa cleanup sendiri
# app/routers/delete_user.py - Admin delete user
```
**Masalah:** Ada 2 cara delete, bisa membingungkan
**Solusi:** Konsolidasi atau dokumentasikan perbedaannya

#### 18. **Tidak Ada Backup Mechanism**
**Masalah:** Jika `allocated_ips.json` corrupt, data hilang
**Solusi:** Implementasi backup otomatis atau gunakan database

#### 19. **Rate Limiting Tidak Konsisten**
Beberapa endpoint tidak ada rate limiting:
- `/admin/users` - tidak ada rate limit
- `/wg/peers` - tidak ada rate limit
**Solusi:** Tambahkan rate limiting ke semua endpoint

#### 20. **Tidak Ada Pagination**
```python
# app/routers/admin.py
return {"status": "ok", "users": users}  # Return semua user sekaligus
```
**Masalah:** Jika user banyak, response besar
**Solusi:** Implementasi pagination

### 🟢 **LOW - Improvement**

#### 21. **Tidak Ada API Documentation**
**Masalah:** Tidak ada Swagger/OpenAPI docs yang lengkap
**Solusi:** FastAPI sudah generate docs otomatis di `/docs`, tapi bisa diperbaiki dengan description

#### 22. **Tidak Ada Versioning API**
**Masalah:** Tidak ada `/v1/` prefix
**Solusi:** Tambahkan versioning untuk kemudahan upgrade

#### 23. **Tidak Ada Health Check Endpoint**
**Masalah:** Tidak ada endpoint untuk monitoring health
**Solusi:** Tambahkan `/health` endpoint

#### 24. **Dependencies Tidak Lengkap**
```python
# requirements.txt hanya ada:
fastapi
uvicorn
ldap3
qrcode
python-multipart
```
**Masalah:** Tidak ada `jose`, `redis`, `fastapi-limiter` di requirements.txt
**Solusi:** Update requirements.txt dengan semua dependencies

#### 25. **Tidak Ada Dockerfile/Docker Compose**
**Masalah:** Sulit deployment dan development
**Solusi:** Tambahkan Dockerfile dan docker-compose.yml

---

## 📊 STATISTIK KODE

- **Total Files:** ~25 Python files
- **Routers:** 11 endpoints
- **Services:** 2 (LDAP auth, JWT)
- **Middleware:** 1 (Auth middleware)
- **Core Modules:** 1 (LDAP client)
- **WireGuard Modules:** 4 (generator, ip_manager, keygen, utils)

---

## ✅ REKOMENDASI PRIORITAS PERBAIKAN

### **PRIORITAS TINGGI (Security)**
1. ✅ Pindahkan semua secrets ke environment variables
2. ✅ Batasi CORS ke domain spesifik
3. ✅ Validasi input (username, password, IP)
4. ✅ Perbaiki error handling (jangan bare except)
5. ✅ Fix path traversal vulnerability
6. ✅ Validasi public key sebelum digunakan di subprocess

### **PRIORITAS SEDANG (Stability)**
7. ✅ Migrate ke database (PostgreSQL/SQLite)
8. ✅ Fix race condition di IP allocation
9. ✅ Implementasi file locking atau transaction
10. ✅ Tambahkan unit tests
11. ✅ Admin list dari LDAP group, bukan hardcoded

### **PRIORITAS RENDAH (Improvement)**
12. ✅ Tambahkan pagination
13. ✅ Structured logging
14. ✅ Request ID tracking
15. ✅ Health check endpoint
16. ✅ Update requirements.txt
17. ✅ Tambahkan Dockerfile

---

## 🎯 KESIMPULAN

**Yang Sudah Bagus:**
- ✅ Arsitektur sudah cukup baik dengan separation of concerns
- ✅ Fitur utama sudah lengkap (auth, generate config, admin portal)
- ✅ Rate limiting sudah ada
- ✅ Logging sudah ada

**Yang Perlu Diperbaiki:**
- 🔴 **KEAMANAN:** Banyak hardcoded credentials, CORS terlalu permisif
- 🟡 **STABILITAS:** Tidak ada database, race condition, error handling lemah
- 🟢 **QUALITY:** Tidak ada tests, logging tidak terstruktur

**Overall Score: 6.5/10**
- Fitur: 8/10 ✅
- Keamanan: 4/10 ⚠️
- Stabilitas: 6/10 ⚠️
- Code Quality: 7/10 ✅

---

*Dokumen ini dibuat untuk membantu improvement proyek. Prioritaskan perbaikan security issues terlebih dahulu sebelum production deployment.*

# 📋 IMPLEMENTATION PLAN: Multi-Device VPN dengan LDAP + MySQL

## 🎯 KONFIGURASI YANG DIPILIH

### 1. **WireGuard Enabled Status**
**Lokasi:** LDAP Custom Attribute  
**Metode:** OPSI A - Custom Schema Extension  
**Attribute Name:** `wireguardEnabled`  
**Type:** Boolean (TRUE/FALSE)  
**Default:** FALSE

### 2. **QR Code Expiration**
**Durasi:** 30 menit  
**Mekanisme:** Timestamp-based expiration  
**Regeneration:** User bisa regenerate setelah expire

### 3. **Fitur Tambahan**
- ✅ Bandwidth Limit per device (admin-configurable)
- ✅ Traffic Logs untuk Analytics
- ✅ Device-level monitoring

---

## 🔐 SOLUSI UNTUK THREATS

### **THREAT 1: Multi-Device = Lebih Banyak Attack Surface**

**Masalah:**  
- User bisa punya 3 device → 3x kemungkinan device hilang/dicuri
- Jika 1 device compromised, semua device user bisa terkena

**Solusi:**

1. **Device-Level Rate Limiting**
   # Rate limit per device, bukan per user
   - Max connection attempts per device: 10/minute
   - Auto-revoke jika suspicious activity terdeteksi
   
Device Fingerprinting
   # Simpan device info untuk tracking   - User-Agent   - IP address pertama kali connect   - Last seen location (jika memungkinkan)
Admin Alert System
   # Alert admin jika:   - Device baru ditambahkan   - Device revoked   - Multiple failed connection attempts
Device Expiration (Optional)
   # Auto-revoke device yang tidak digunakan > 90 hari   - Admin bisa set expiration policy   - User dapat warning sebelum expire

THREAT 2: Data Consistency antara WireGuard dan MySQL
Masalah:
WireGuard peer bisa dihapus manual (di server)
MySQL tidak tahu → data tidak konsisten
Bisa menyebabkan IP conflict
Solusi:
Periodic Sync Job
   # Background job setiap 5 menit:   - Query: wg show wg0 dump   - Compare dengan MySQL vpn_devices   - Detect missing peers → update MySQL status = 'inconsistent'   - Alert admin jika ada inconsistency
Transaction-Based Operations
   # Semua operasi device harus atomic:   - Start transaction   - Update MySQL   - Execute WireGuard command   - Commit transaction   - Rollback jika WireGuard command gagal
Health Check Endpoint
   # GET /admin/health/consistency   - Compare WireGuard peers dengan MySQL   - Return list inconsistencies   - Admin bisa trigger manual sync
Audit Log untuk Semua Changes
   # Log semua perubahan:   - Device created   - Device revoked   - WireGuard peer added/removed   - IP allocated/released
THREAT 3: Performance Issues
Masalah:
Query MySQL untuk setiap request → bisa slow
Background job untuk traffic sync → bisa impact performance
Tidak ada caching
Solusi:
Database Indexing
   -- Pastikan semua query fields ter-index:   CREATE INDEX idx_ldap_uid_status ON vpn_devices(ldap_uid, status);   CREATE INDEX idx_public_key ON vpn_devices(public_key);   CREATE INDEX idx_vpn_ip ON vpn_devices(vpn_ip);   CREATE INDEX idx_last_seen ON vpn_devices(last_seen);
Query Optimization
   # Gunakan:   - SELECT hanya fields yang diperlukan (bukan SELECT *)   - LIMIT untuk pagination   - Connection pooling untuk MySQL   - Prepared statements untuk prevent SQL injection
Caching Strategy
   # Cache dengan Redis:   - User device list: cache 5 menit   - LDAP wireguardEnabled status: cache 10 menit   - Admin user list: cache 2 menit
Background Job Optimization
   # Traffic sync job:   - Batch update (update multiple rows dalam 1 query)   - Run di off-peak hours jika memungkinkan   - Limit query size (misal: update 100 devices per batch)
Connection Pooling
   # MySQL connection pool:   - Min connections: 5   - Max connections: 20   - Idle timeout: 300 seconds
THREAT 4: LDAP Dependency
Masalah:
Jika LDAP down → user tidak bisa login
Tidak ada fallback mechanism
Semua auth bergantung pada LDAP
Solusi:
LDAP Connection Pooling & Retry
   # Implementasi:   - Connection pool untuk LDAP   - Retry mechanism dengan exponential backoff   - Timeout: 5 seconds per request   - Max retries: 3
Caching LDAP Results
   # Cache dengan TTL:   - User authentication status: cache 5 menit   - wireguardEnabled status: cache 10 menit   - Admin group membership: cache 15 menit
Health Check & Monitoring
   # GET /admin/health/ldap   - Test LDAP connection   - Return status: healthy/degraded/down   - Alert jika LDAP down
Graceful Degradation
   # Jika LDAP down:   - Return 503 Service Unavailable   - Show maintenance message   - Log error untuk admin
LDAP Replication (Recommended)
   # Setup LDAP master-slave replication:   - Primary LDAP server   - Secondary LDAP server (backup)   - Auto-failover jika primary down


File `plan.md` ini mencakup:
1. Konfirmasi wireguardEnabled di LDAP (custom attribute)
2. QR expiration 30 menit
3. Bandwidth limit feature
4. Solusi untuk semua threats
5. Step-by-step implementation plan (10 phases)
6. Database schema lengkap
7. LDAP schema extension
8. File structure yang diusulkan
9. Migration checklist
10. Timeline dan success metrics
