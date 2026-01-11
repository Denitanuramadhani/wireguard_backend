# Admin Guide: WireGuard VPN Portal

## Overview

Sebagai admin, Anda memiliki akses penuh untuk mengelola sistem VPN, termasuk:
- User management
- Device management
- Monitoring & alerts
- Bandwidth management
- System configuration

## Getting Started

### 1. Login sebagai Admin

1. Buka portal web
2. Login dengan credentials admin Anda
3. Pastikan Anda adalah member dari group `cn=admins,ou=groups,dc=example,dc=com` di LDAP

### 2. Dashboard Overview

Setelah login, Anda akan melihat:
- Total users
- Total devices (active/revoked)
- Recent alerts
- System statistics

## User Management

### Enable VPN Access untuk User

1. Navigate ke **Admin → Users**
2. Cari user yang ingin di-enable
3. Klik **Enable VPN Access**
4. User sekarang bisa add devices

### Disable VPN Access untuk User

1. Navigate ke **Admin → Users**
2. Cari user yang ingin di-disable
3. Klik **Disable VPN Access**
4. Semua active devices user akan otomatis di-revoke

### Set Maximum Devices

1. Navigate ke **Admin → Users**
2. Pilih user
3. Klik **Set Max Devices**
4. Input jumlah maksimal devices (1-10)
5. Save

## Device Management

### View All Devices

1. Navigate ke **Admin → Devices**
2. Filter by status (active/revoked)
3. View device details:
   - Device name
   - User
   - VPN IP
   - Status
   - Traffic statistics
   - Last seen

### Revoke Device

1. Navigate ke **Admin → Devices**
2. Pilih device yang ingin di-revoke
3. Klik **Revoke**
4. Device akan dihapus dari WireGuard dan status di-update ke "revoked"

### View User Devices

1. Navigate ke **Admin → Users**
2. Pilih user
3. Klik **View Devices**
4. Lihat semua devices untuk user tersebut

## Monitoring & Alerts

### View Alerts

1. Navigate ke **Admin → Monitoring → Alerts**
2. Filter by severity (low/medium/high/critical)
3. View alert details:
   - Alert type
   - Severity
   - Message
   - Timestamp
   - Details

### View Audit Logs

1. Navigate ke **Admin → Monitoring → Audit Logs**
2. Filter by:
   - Action type
   - User
   - Performed by
3. View complete audit trail

### System Statistics

1. Navigate ke **Admin → Monitoring → Statistics**
2. View:
   - Device statistics
   - User statistics
   - Alert statistics

## Bandwidth Management

### Set Bandwidth Limit per Device

1. Navigate ke **Admin → Bandwidth**
2. Pilih device
3. Set bandwidth limit (bytes per month)
4. Set to NULL untuk unlimited

### Set Bandwidth Limit per User

1. Navigate ke **Admin → Bandwidth**
2. Pilih user
3. Set bandwidth limit untuk semua devices user tersebut

### Reset Bandwidth Usage

1. Navigate ke **Admin → Bandwidth**
2. Pilih device atau user
3. Klik **Reset Usage**
4. Bandwidth usage akan di-reset ke 0

## Health Monitoring

### Check System Health

1. Navigate ke **Admin → Health** atau
2. Access `/health/full` endpoint
3. View status semua services:
   - Database
   - LDAP
   - Redis
   - WireGuard

### Consistency Check

1. Navigate ke **Admin → Health → Consistency**
2. Check inconsistencies antara WireGuard dan MySQL
3. Review dan fix jika ada inconsistencies

## Best Practices

### Security
- Review audit logs regularly
- Monitor alerts untuk suspicious activities
- Revoke unused devices
- Set appropriate bandwidth limits

### Performance
- Monitor system statistics
- Check health endpoints regularly
- Review traffic patterns
- Optimize bandwidth limits

### Maintenance
- Regular backups
- Monitor disk space
- Review logs untuk errors
- Update system regularly

## Troubleshooting

### User tidak bisa login
- Check LDAP connection: `/health/ldap`
- Verify user exists di LDAP
- Check user credentials

### Device tidak bisa connect
- Check WireGuard service: `/health/wireguard`
- Verify device status (active/revoked)
- Check WireGuard configuration
- Review device traffic logs

### High bandwidth usage
- Check bandwidth limits
- Review traffic analytics
- Consider revoking suspicious devices
- Set bandwidth limits jika diperlukan

### System errors
- Check health endpoints
- Review application logs
- Check database connection
- Review alert logs

## API Access

Admin bisa menggunakan API endpoints untuk automation:
- See `docs/API_DOCUMENTATION.md` untuk complete API reference
- Use admin JWT token untuk authentication
- Rate limits apply untuk semua endpoints
