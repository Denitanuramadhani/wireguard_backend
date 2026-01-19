# LDAP Users Migration Guide

## Overview

Script untuk migrate existing LDAP users dengan `wireguardUser` objectClass dan attributes yang diperlukan.

## Prerequisites

1. **LDAP Schema sudah terinstall**
   ```bash
   sudo bash scripts/setup_ldap_schema.sh
   ```

2. **LDAP tools terinstall**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ldap-utils
   
   # CentOS/RHEL
   sudo yum install openldap-clients
   ```

3. **LDAP Admin credentials**
   - Set environment variables atau edit script

## Quick Start

### 1. Dry Run (Preview)

```bash
# Preview apa yang akan di-migrate
LDAP_ADMIN_PASSWORD=your_password bash scripts/migrate_ldap_users.sh --dry-run
```

### 2. Run Migration

```bash
# Migrate semua users
LDAP_ADMIN_PASSWORD=your_password bash scripts/migrate_ldap_users.sh
```

### 3. Verify

```bash
# Check status migration
LDAP_ADMIN_PASSWORD=your_password bash scripts/migrate_ldap_users.sh --verify-only
```

## Environment Variables

```bash
export LDAP_SERVER="ldap://117.53.44.59:389"
export LDAP_BASE_DN="dc=example,dc=com"
export LDAP_ADMIN_DN="cn=admin,dc=example,dc=com"
export LDAP_ADMIN_PASSWORD="your_password"
export WIREGUARD_ENABLED_DEFAULT="FALSE"  # Default: FALSE
export MAX_DEVICES_DEFAULT="3"            # Default: 3
```

## What Does Migration Do?

Untuk setiap user yang belum punya `wireguardUser` objectClass, script akan:

1. **Add objectClass**: `wireguardUser`
2. **Add attribute**: `wireguardEnabled = FALSE` (jika belum ada)
3. **Add attribute**: `maxWireguardDevices = 3` (jika belum ada)

## Migration is Idempotent

- Script bisa dijalankan berulang kali
- Hanya migrate users yang belum punya `wireguardUser` objectClass
- Tidak akan duplicate attributes yang sudah ada

## Examples

### Basic Usage

```bash
cd wireguard_backend
LDAP_ADMIN_PASSWORD=secret123 bash scripts/migrate_ldap_users.sh
```

### With Custom Settings

```bash
LDAP_SERVER="ldap://localhost:389" \
LDAP_BASE_DN="dc=company,dc=com" \
LDAP_ADMIN_DN="cn=admin,dc=company,dc=com" \
LDAP_ADMIN_PASSWORD="password" \
WIREGUARD_ENABLED_DEFAULT="TRUE" \
MAX_DEVICES_DEFAULT="5" \
bash scripts/migrate_ldap_users.sh
```

### Check Status Only

```bash
LDAP_ADMIN_PASSWORD=secret123 bash scripts/migrate_ldap_users.sh --verify-only
```

## Troubleshooting

### Connection Failed

```bash
# Test LDAP connection manually
ldapsearch -x -H "ldap://117.53.44.59:389" \
  -D "cn=admin,dc=example,dc=com" \
  -w "your_password" \
  -b "dc=example,dc=com" \
  -s base "(objectClass=*)"
```

### Schema Not Found

```bash
# Install schema first
sudo bash scripts/setup_ldap_schema.sh

# Verify schema
ldapsearch -x -H ldapi:/// -b "cn=schema,cn=config" "(cn=wireguard)"
```

### Permission Denied

- Pastikan menggunakan admin DN yang benar
- Pastikan password admin benar
- Check LDAP ACLs jika perlu

### Users Not Found

```bash
# Check if users exist
ldapsearch -x -H "ldap://117.53.44.59:389" \
  -D "cn=admin,dc=example,dc=com" \
  -w "your_password" \
  -b "ou=people,dc=example,dc=com" \
  "(objectClass=inetOrgPerson)" dn
```

## Manual Migration (Alternative)

Jika script tidak bisa digunakan, bisa migrate manual:

### Single User

```bash
ldapmodify -x -H "ldap://117.53.44.59:389" \
  -D "cn=admin,dc=example,dc=com" \
  -w "your_password" <<EOF
dn: uid=username,ou=people,dc=example,dc=com
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

### Batch Update (All Users)

```bash
# Get all users
ldapsearch -x -H "ldap://117.53.44.59:389" \
  -D "cn=admin,dc=example,dc=com" \
  -w "your_password" \
  -b "ou=people,dc=example,dc=com" \
  "(&(objectClass=inetOrgPerson)(!(objectClass=wireguardUser)))" \
  dn > /tmp/users.txt

# Create LDIF
while read dn; do
  [ -z "$dn" ] && continue
  echo "dn: $dn"
  echo "changetype: modify"
  echo "add: objectClass"
  echo "objectClass: wireguardUser"
  echo "-"
  echo "add: wireguardEnabled"
  echo "wireguardEnabled: FALSE"
  echo "-"
  echo "add: maxWireguardDevices"
  echo "maxWireguardDevices: 3"
  echo ""
done < /tmp/users.txt > /tmp/migrate_users.ldif

# Apply
ldapmodify -x -H "ldap://117.53.44.59:389" \
  -D "cn=admin,dc=example,dc=com" \
  -w "your_password" \
  -f /tmp/migrate_users.ldif
```

## Integration dengan Setup

Migration script bisa diintegrasikan dalam deployment process:

```bash
# 1. Install schema
sudo bash scripts/setup_ldap_schema.sh

# 2. Migrate existing users
LDAP_ADMIN_PASSWORD=$LDAP_ADMIN_PASSWORD bash scripts/migrate_ldap_users.sh

# 3. Start application
# ...
```

## Notes

- Migration hanya menambahkan attributes, tidak menghapus data existing
- Default `wireguardEnabled = FALSE` untuk security (user harus enable manual)
- Default `maxWireguardDevices = 3` sesuai best practice
- Script aman untuk dijalankan di production (idempotent)

