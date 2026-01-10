# ✅ Phase 2: LDAP Schema Extension - COMPLETED

## 📋 Yang Sudah Dikerjakan

### 1. ✅ LDAP Schema File
- **File:** `ldap/wireguard.schema`
- **Content:**
  - Custom attribute `wireguardEnabled` (Boolean)
  - Custom attribute `maxWireguardDevices` (Integer)
  - Custom objectClass `wireguardUser` (AUXILIARY)

### 2. ✅ LDAP Setup Script
- **File:** `scripts/setup_ldap_schema.sh`
- **Features:**
  - Auto-detect OpenLDAP version (2.3 atau 2.4+)
  - Setup schema untuk cn=config (OpenLDAP 2.4+)
  - Setup schema untuk slapd.conf (OpenLDAP 2.3)
  - Verification setelah setup

### 3. ✅ LDAP Client Module (Updated)
- **File:** `app/core/ldap_client.py`
- **New Functions:**
  - `get_ldap_connection(admin=False)` - Get LDAP connection dengan/without admin credentials
  - `get_user_attributes(username, attributes)` - Get user attributes dari LDAP
  - `check_wireguard_enabled(username)` - Check jika user punya WireGuard access enabled
  - `get_max_devices(username)` - Get max devices allowed untuk user
  - `enable_wireguard_user(username)` - Enable WireGuard access
  - `disable_wireguard_user(username)` - Disable WireGuard access
  - `set_max_devices(username, max_devices)` - Set max devices untuk user
  - `check_user_in_group(username, group_dn)` - Check group membership
  - `is_admin(username)` - Check jika user adalah admin (dari LDAP group)

### 4. ✅ LDAP Auth Service (Updated)
- **File:** `app/services/ldap_auth.py`
- **Changes:**
  - Improved error logging
  - Note bahwa wireguardEnabled check dilakukan setelah login

### 5. ✅ Auth Router (Updated)
- **File:** `app/routers/auth.py`
- **Changes:**
  - Check `wireguardEnabled` status setelah login
  - Return `wireguard_enabled` dan `max_devices` di response
  - User tetap bisa login meskipun wireguardEnabled = FALSE (untuk keperluan lain)

### 6. ✅ Auth Middleware (Updated)
- **File:** `app/middleware/auth_middleware.py`
- **Changes:**
  - **REMOVED:** Hardcoded `ADMIN_LIST = ["denita"]`
  - **ADDED:** `verify_jwt_admin()` sekarang check dari LDAP group `cn=admins,ou=groups,dc=example,dc=com`
  - Admin ditentukan dari LDAP `memberOf` attribute, bukan hardcoded

### 7. ✅ Admin Add User (Updated)
- **File:** `app/routers/admin_add_user.py`
- **Major Changes:**
  - **REMOVED:** Logic untuk generate WireGuard config saat add user
  - **REMOVED:** Logic untuk allocate IP dan add peer
  - **ADDED:** Set `wireguardEnabled = FALSE` default saat create user
  - **ADDED:** Tambahkan `objectClass: wireguardUser` saat create user
  - **ADDED:** Set `maxWireguardDevices` default = 3
  - **ADDED:** Username validation
  - **ADDED:** Check jika user sudah exists
  - **ADDED:** Menggunakan config dari environment variables (bukan hardcoded)

## 🔧 LDAP Schema Details

### Attributes:
1. **wireguardEnabled** (Boolean)
   - `TRUE` = User bisa akses VPN
   - `FALSE` = User tidak bisa akses VPN (default)
   - Single value

2. **maxWireguardDevices** (Integer)
   - Maximum devices yang bisa dibuat user
   - Default: 3
   - Single value

### ObjectClass:
- **wireguardUser** (AUXILIARY)
  - Bisa ditambahkan ke user existing tanpa mengubah objectClass lain
  - MAY attributes: wireguardEnabled, maxWireguardDevices

## 📝 Setup Instructions

### Step 1: Install LDAP Schema

```bash
# Di LDAP Server (117.53.44.59)
cd /path/to/wireguard_backend
sudo bash scripts/setup_ldap_schema.sh
```

### Step 2: Update Existing Users

```bash
# Update user existing dengan wireguardUser objectClass
ldapmodify -x -D "cn=admin,dc=example,dc=com" -w <password> <<EOF
dn: uid=denita,ou=people,dc=example,dc=com
changetype: modify
add: objectClass
objectClass: wireguardUser
-
add: wireguardEnabled
wireguardEnabled: FALSE
-
add: maxWireguardDevices
maxWireguardDevices: 3
EOF
```

Atau gunakan file `ldap/update_existing_users.ldif` dan edit sesuai kebutuhan.

### Step 3: Verify Schema

```bash
# Test schema
ldapsearch -x -H ldapi:/// -b "cn=schema,cn=config" "(cn=wireguard)"

# Test user attributes
ldapsearch -x -D "cn=admin,dc=example,dc=com" -w <password> \
  -b "dc=example,dc=com" "(uid=denita)" wireguardEnabled maxWireguardDevices
```

## 🔄 Flow Changes

### Before Phase 2:
```
Admin Add User → LDAP + Generate Config + Add Peer
```

### After Phase 2:
```
Admin Add User → LDAP (wireguardEnabled=FALSE)
User Login → Check wireguardEnabled (info only)
User Add Device → Check wireguardEnabled (block if FALSE)
```

## ✅ Verification Checklist

- [ ] LDAP schema installed
- [ ] Schema verified dengan ldapsearch
- [ ] Existing users updated dengan wireguardUser objectClass
- [ ] Test `check_wireguard_enabled()` function
- [ ] Test `is_admin()` function dengan LDAP group
- [ ] Test admin add user (harus set wireguardEnabled=FALSE)
- [ ] Test login (harus return wireguard_enabled status)
- [ ] Test admin endpoints (harus check LDAP group, bukan hardcoded)

## 🎯 Key Improvements

1. **Separation of Concerns:**
   - User identity tetap di LDAP
   - Device data tetap di MySQL
   - Admin check dari LDAP group, bukan hardcoded

2. **Security:**
   - Admin list tidak lagi hardcoded
   - Admin ditentukan dari LDAP group membership
   - Credentials menggunakan environment variables

3. **Flexibility:**
   - User bisa dibuat tanpa langsung dapat VPN access
   - Admin bisa enable/disable VPN access per user
   - Max devices bisa di-set per user

## 📊 Testing

### Test LDAP Functions:

```python
# Test check_wireguard_enabled
from app.core.ldap_client import check_wireguard_enabled
print(check_wireguard_enabled("denita"))  # Should return True/False

# Test is_admin
from app.core.ldap_client import is_admin
print(is_admin("denita"))  # Should return True jika member of admins group

# Test enable/disable
from app.core.ldap_client import enable_wireguard_user, disable_wireguard_user
enable_wireguard_user("testuser")
disable_wireguard_user("testuser")
```

### Test API Endpoints:

```bash
# Test login (harus return wireguard_enabled)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"denita","password":"password"}'

# Test admin add user (harus set wireguardEnabled=FALSE)
curl -X POST http://localhost:8000/admin/add-user \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","password":"password123"}'
```

## ⚠️ Important Notes

1. **LDAP Schema OID:**
   - OID yang digunakan: `1.3.6.1.4.1.99999`
   - Ini adalah Private Enterprise Number untuk testing
   - Untuk production, gunakan OID yang terdaftar atau OID lokal Anda

2. **Existing Users:**
   - User yang sudah ada perlu di-update dengan `wireguardUser` objectClass
   - Gunakan script atau manual update dengan ldapmodify

3. **Admin Group:**
   - Pastikan group `cn=admins,ou=groups,dc=example,dc=com` sudah ada di LDAP
   - Atau update `is_admin()` function untuk menggunakan group DN yang sesuai

4. **Default Values:**
   - `wireguardEnabled` = FALSE (user harus di-enable oleh admin)
   - `maxWireguardDevices` = 3 (default)

## 🚀 Next Steps (Phase 3)

Phase 3 akan fokus pada:
- Device Management (add, list, revoke device)
- IP allocation dari MySQL
- WireGuard peer management
- Device CRUD endpoints

---

*Phase 2 selesai! LDAP schema extension sudah terintegrasi dengan backend.*
