# LDAP Users Seeder Guide

## Overview

Script untuk create/seed LDAP users dari file CSV. Berguna untuk:
- Initial setup users
- Bulk create users
- Testing dengan sample users

## Prerequisites

1. **LDAP Schema sudah terinstall**
   ```bash
   sudo bash scripts/setup_ldap_schema.sh
   ```

2. **LDAP tools terinstall**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ldap-utils openldap-utils
   
   # CentOS/RHEL
   sudo yum install openldap-clients
   ```

3. **LDAP Admin credentials**
   - Set di `.env` file atau environment variables

## Quick Start

### 1. Create Sample CSV File

```bash
cd wireguard_backend/scripts
./seed_ldap_users.sh --sample
```

Ini akan membuat file `users_sample.csv` dengan contoh users.

### 2. Edit CSV File

Edit `users_sample.csv` sesuai kebutuhan:

```csv
username,password,max_devices,wireguard_enabled
user1,password123,3,FALSE
user2,password123,5,TRUE
admin,admin123,10,TRUE
```

**Format CSV:**
- `username` - Username (required, alphanumeric + underscore)
- `password` - Password (required)
- `max_devices` - Maximum devices allowed (optional, default: 3)
- `wireguard_enabled` - Enable VPN access (optional, default: FALSE)

### 3. Seed Users

```bash
# Seed dari CSV file
./seed_ldap_users.sh users_sample.csv

# Atau dengan custom password
LDAP_ADMIN_PASSWORD=your_password ./seed_ldap_users.sh users.csv
```

## CSV File Format

### Basic Format

```csv
username,password
user1,password123
user2,password123
```

### Full Format

```csv
username,password,max_devices,wireguard_enabled
user1,password123,3,FALSE
user2,password123,5,TRUE
admin,admin123,10,TRUE
```

### With Header (Optional)

Script akan otomatis skip header jika baris pertama adalah "username" atau "Username".

## Examples

### Create Sample and Seed

```bash
# 1. Create sample CSV
./seed_ldap_users.sh --sample

# 2. Edit users_sample.csv

# 3. Seed users
./seed_ldap_users.sh users_sample.csv
```

### Custom CSV File

```bash
# Create your own CSV
cat > my_users.csv <<EOF
username,password,max_devices,wireguard_enabled
john,secret123,3,FALSE
jane,secret456,5,TRUE
EOF

# Seed users
./seed_ldap_users.sh my_users.csv
```

### With Environment Variables

```bash
LDAP_SERVER="ldap://localhost:389" \
LDAP_BASE_DN="dc=wireguard,dc=local" \
LDAP_ADMIN_DN="cn=admin,dc=wireguard,dc=local" \
LDAP_ADMIN_PASSWORD="123" \
./seed_ldap_users.sh users.csv
```

## Features

### Idempotent

- Script bisa dijalankan berulang kali
- User yang sudah exists akan di-skip
- Tidak akan duplicate users

### Auto UID Number

- Script otomatis generate `uidNumber` yang unik
- Mulai dari `UID_NUMBER_START` (default: 2000)
- Auto-increment untuk setiap user baru

### User Attributes

Setiap user akan dibuat dengan:
- `objectClass`: inetOrgPerson, organizationalPerson, person, posixAccount, top, wireguardUser
- `cn`: username
- `sn`: username
- `uid`: username
- `uidNumber`: auto-generated
- `gidNumber`: same as uidNumber
- `homeDirectory`: /home/username
- `loginShell`: /bin/bash
- `userPassword`: SSHA hashed password
- `wireguardEnabled`: from CSV or default FALSE
- `maxWireguardDevices`: from CSV or default 3

## Environment Variables

```bash
export LDAP_SERVER="ldap://117.53.44.59:389"
export LDAP_BASE_DN="dc=wireguard,dc=local"
export LDAP_ADMIN_DN="cn=admin,dc=wireguard,dc=local"
export LDAP_ADMIN_PASSWORD="your_password"
export UID_NUMBER_START="2000"  # Starting UID number
export WIREGUARD_ENABLED_DEFAULT="FALSE"  # Default wireguardEnabled
export MAX_DEVICES_DEFAULT="3"  # Default max devices
```

## Troubleshooting

### User Already Exists

```
[WARN] User user1 already exists, skipping...
```

Ini normal - script idempotent, user yang sudah ada akan di-skip.

### Password Hash Error

```
[ERROR] slappasswd not found. Please install openldap-utils
```

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install openldap-utils

# CentOS/RHEL
sudo yum install openldap-utils
```

### Connection Failed

```
[ERROR] LDAP connection failed!
```

**Check:**
1. LDAP server is running
2. Admin credentials are correct
3. Network connectivity to LDAP server

**Test connection:**
```bash
ldapsearch -x -H "ldap://117.53.44.59:389" \
  -D "cn=admin,dc=wireguard,dc=local" \
  -w "123" \
  -b "dc=wireguard,dc=local" \
  -s base "(objectClass=*)"
```

### Invalid Username Format

```
[ERROR] ✗ Invalid username format: user-name (line 2)
```

**Solution:** Username harus alphanumeric + underscore saja (no dashes, spaces, etc.)

## Integration dengan Setup

Seeder bisa digunakan dalam deployment process:

```bash
# 1. Setup LDAP schema
sudo bash scripts/setup_ldap_schema.sh

# 2. Migrate existing users (jika ada)
LDAP_ADMIN_PASSWORD=secret bash scripts/migrate_ldap_users.sh

# 3. Seed initial users
LDAP_ADMIN_PASSWORD=secret bash scripts/seed_ldap_users.sh initial_users.csv

# 4. Start application
# ...
```

## Notes

- Password akan di-hash dengan SSHA sebelum disimpan
- Default `wireguardEnabled = FALSE` untuk security
- Default `maxWireguardDevices = 3`
- UID number auto-increment dari max existing UID
- Script aman untuk dijalankan di production (idempotent)

