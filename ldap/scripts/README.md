# LDAP Scripts

Directory untuk menyimpan LDAP operation scripts (LDIF files).

## Files

- `add_suffix_acl.ldif` - Add suffix ACL configuration
- `change_pw.ldif` - Change password template
- `fix_acl.ldif` - Fix ACL configuration
- `reset_admin.ldif` - Reset admin password
- `reset_denita.ldif` - Reset user password example

## Usage

These LDIF files can be used with `ldapmodify` or `ldapadd` commands:

```bash
# Example: Reset admin password
ldapmodify -x -H ldap://localhost:389 \
  -D "cn=admin,dc=wireguard,dc=local" \
  -w "admin_password" \
  -f reset_admin.ldif
```

## Note

These are utility scripts for LDAP administration.
Modify values as needed before use.

