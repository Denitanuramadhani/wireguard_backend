# LDAP Schema Extension Setup Guide

## Overview

LDAP schema extension menambahkan custom attributes dan objectClass untuk WireGuard VPN Portal:
- `wireguardEnabled` - Enable/disable VPN access
- `maxWireguardDevices` - Maximum devices allowed
- `wireguardUser` - ObjectClass untuk user dengan VPN access

## Files

- `wireguard.schema` - LDAP schema definition
- `update_existing_users.ldif` - Template untuk update existing users
- `README.md` - File ini

## Quick Setup

### 1. Install Schema

```bash
# Di LDAP Server (117.53.44.59)
cd /path/to/wireguard_backend
sudo bash scripts/setup_ldap_schema.sh
```

### 2. Update Existing Users

```bash
# Edit ldap/update_existing_users.ldif sesuai kebutuhan
# Kemudian run:
ldapmodify -x -D "cn=admin,dc=example,dc=com" -w <password> -f ldap/update_existing_users.ldif
```

### 3. Verify

```bash
# Check schema
ldapsearch -x -H ldapi:/// -b "cn=schema,cn=config" "(cn=wireguard)"

# Check user attributes
ldapsearch -x -D "cn=admin,dc=example,dc=com" -w <password> \
  -b "dc=example,dc=com" "(uid=denita)" wireguardEnabled maxWireguardDevices
```

## Manual Setup (Alternative)

### For OpenLDAP 2.4+ (cn=config)

```bash
# 1. Copy schema file
sudo cp ldap/wireguard.schema /etc/ldap/schema/

# 2. Create LDIF
cat > /tmp/wireguard_schema.ldif <<EOF
dn: cn=wireguard,cn=schema,cn=config
objectClass: olcSchemaConfig
cn: wireguard
olcAttributeTypes: {0}( 1.3.6.1.4.1.99999.1.1.1 NAME 'wireguardEnabled' DESC 'Enable/disable WireGuard VPN access' EQUALITY booleanMatch SYNTAX 1.3.6.1.4.1.1466.115.121.1.7 SINGLE-VALUE )
olcAttributeTypes: {1}( 1.3.6.1.4.1.99999.1.1.2 NAME 'maxWireguardDevices' DESC 'Maximum WireGuard devices allowed' EQUALITY integerMatch SYNTAX 1.3.6.1.4.1.1466.115.121.1.27 SINGLE-VALUE )
olcObjectClasses: {0}( 1.3.6.1.4.1.99999.1.1.1 NAME 'wireguardUser' DESC 'WireGuard user extension' SUP top AUXILIARY MAY ( wireguardEnabled \$ maxWireguardDevices ) )
EOF

# 3. Add schema
sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /tmp/wireguard_schema.ldif

# 4. Cleanup
rm /tmp/wireguard_schema.ldif
```

### For OpenLDAP 2.3 (slapd.conf)

```bash
# 1. Copy schema file
sudo cp ldap/wireguard.schema /etc/ldap/schema/

# 2. Add to slapd.conf
echo "include /etc/ldap/schema/wireguard.schema" | sudo tee -a /etc/ldap/slapd.conf

# 3. Restart LDAP
sudo systemctl restart slapd
```

## Update Existing Users

### Single User

```bash
ldapmodify -x -D "cn=admin,dc=example,dc=com" -w <password> <<EOF
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
ldapsearch -x -D "cn=admin,dc=example,dc=com" -w <password> \
  -b "ou=people,dc=example,dc=com" "(objectClass=inetOrgPerson)" dn > /tmp/users.txt

# Create LDIF untuk semua users
while read dn; do
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
done < /tmp/users.txt > /tmp/update_all_users.ldif

# Apply changes
ldapmodify -x -D "cn=admin,dc=example,dc=com" -w <password> -f /tmp/update_all_users.ldif
```

## Troubleshooting

### Schema Not Found
```bash
# Check if schema file exists
ls -la /etc/ldap/schema/wireguard.schema

# Check if schema loaded
ldapsearch -x -H ldapi:/// -b "cn=schema,cn=config" "(cn=wireguard)"
```

### Attribute Not Found
```bash
# Check user objectClass
ldapsearch -x -D "cn=admin,dc=example,dc=com" -w <password> \
  -b "dc=example,dc=com" "(uid=username)" objectClass

# Should include "wireguardUser"
```

### Permission Denied
```bash
# Make sure using admin DN
# Check LDAP admin password di .env file
# Verify admin DN: cn=admin,dc=example,dc=com
```

## Testing

### Test Functions

```python
from app.core.ldap_client import (
    check_wireguard_enabled,
    get_max_devices,
    enable_wireguard_user,
    disable_wireguard_user,
    is_admin
)

# Test check wireguardEnabled
print(check_wireguard_enabled("denita"))

# Test get max devices
print(get_max_devices("denita"))

# Test enable/disable
enable_wireguard_user("testuser")
disable_wireguard_user("testuser")

# Test admin check
print(is_admin("denita"))
```

## Notes

- OID `1.3.6.1.4.1.99999` adalah Private Enterprise Number untuk testing
- Untuk production, gunakan OID yang terdaftar atau OID lokal
- Schema adalah AUXILIARY, bisa ditambahkan ke user existing tanpa mengubah objectClass lain
- Default: `wireguardEnabled = FALSE`, `maxWireguardDevices = 3`

---

*Setup guide untuk LDAP schema extension*
