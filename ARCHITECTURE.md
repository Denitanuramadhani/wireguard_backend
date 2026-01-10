# 🏗️ Architecture Overview: WireGuard VPN Portal

## Infrastructure Layout

### VPS 1: Backend Services (117.53.44.59)
**Services:**
- ✅ WireGuard Server (wg0 interface)
- ✅ OpenLDAP Server (User identity & authentication)
- ✅ Backend API (FastAPI)
- ✅ Frontend (Web Portal)
- ✅ Redis (Rate limiting)

**Responsibilities:**
- User authentication via LDAP
- User authorization (role/group management)
- WireGuard peer management
- API endpoints
- Web interface

### VPS 2: Database Server (117.53.45.105)
**Services:**
- ✅ MySQL Server (AlmaLinux)

**Responsibilities:**
- Store VPN device data
- Store WireGuard keys
- Store IP allocations
- Store VPN status
- Store traffic logs
- Store audit logs

**Data Stored:**
- Device information (device_name, public_key, vpn_ip)
- Device status (active, revoked, expired)
- Traffic statistics (transfer_rx, transfer_tx)
- Bandwidth limits
- Audit logs

**Data NOT Stored:**
- ❌ User identity (tetap di LDAP)
- ❌ User passwords (tetap di LDAP)
- ❌ User roles/groups (tetap di LDAP)
- ❌ User authentication data (tetap di LDAP)

## Data Flow

### User Authentication Flow
```
User → Frontend (117.53.44.59)
  ↓
Frontend → Backend API (117.53.44.59)
  ↓
Backend → LDAP Server (117.53.44.59)
  ↓
LDAP → Verify credentials
  ↓
Backend → Generate JWT token
  ↓
Frontend → Store token
```

### Device Creation Flow
```
User → Frontend (117.53.44.59)
  ↓
Frontend → Backend API (117.53.44.59)
  ↓
Backend → Check LDAP (117.53.44.59): wireguardEnabled?
  ↓
Backend → Check MySQL (117.53.45.105): device count < max?
  ↓
Backend → Generate WireGuard keys
  ↓
Backend → Allocate IP dari MySQL (117.53.45.105)
  ↓
Backend → Insert device ke MySQL (117.53.45.105)
  ↓
Backend → Add peer ke WireGuard (117.53.44.59)
  ↓
Backend → Generate config & QR
  ↓
Frontend → Display config/QR
```

### Traffic Monitoring Flow
```
WireGuard Server (117.53.44.59)
  ↓
Background Job → Query: wg show wg0 dump
  ↓
Parse traffic data
  ↓
Update MySQL (117.53.45.105): vpn_devices table
  ↓
Insert MySQL (117.53.45.105): vpn_traffic_logs table
  ↓
Frontend → Query MySQL (117.53.45.105) untuk analytics
```

## Database Schema (MySQL - 117.53.45.105)

### Tables:
1. **vpn_devices** - Device information
   - id, ldap_uid (reference ke LDAP), device_name, public_key, vpn_ip, status
   - Traffic stats, timestamps, bandwidth limits

2. **vpn_traffic_logs** - Traffic logs untuk analytics
   - device_id, transfer_rx, transfer_tx, recorded_at

3. **vpn_revoke_history** - Audit log untuk revoked devices
   - device_id, revoked_by, revoked_at, revoke_reason

4. **vpn_bandwidth_limits** - Bandwidth limit configuration
   - ldap_uid, device_id, bandwidth_limit

5. **vpn_audit_logs** - Security audit logs
   - action, performed_by, ip_address, details

## LDAP Schema (OpenLDAP - 117.53.44.59)

### User Attributes:
- `uid` - Username
- `userPassword` - Password (hashed)
- `cn`, `sn` - Name
- `memberOf` - Groups (untuk authorization)
- `wireguardEnabled` - Enable/disable VPN access (custom attribute)
- `maxWireguardDevices` - Max devices allowed (custom attribute)

### Groups:
- `cn=admins,ou=groups,dc=example,dc=com` - Admin users
- `cn=users,ou=groups,dc=example,dc=com` - Regular users

## Security Considerations

### Network Security:
- MySQL hanya accessible dari backend server (117.53.44.59)
- Firewall rules untuk restrict access
- SSL/TLS untuk MySQL connection (recommended)

### Data Security:
- User passwords: Hanya di LDAP (hashed)
- WireGuard private keys: Hanya di config files (tidak di MySQL)
- JWT secrets: Di environment variables
- Database credentials: Di .env file (tidak di git)

### Access Control:
- LDAP untuk user authentication
- LDAP groups untuk authorization (admin vs user)
- JWT tokens untuk session management
- Rate limiting via Redis

## Scalability

### Current Setup:
- Single MySQL server
- Single LDAP server
- Single WireGuard server

### Future Scalability Options:
- MySQL replication (master-slave)
- LDAP replication (master-slave)
- Load balancer untuk backend API
- Multiple WireGuard servers dengan routing

## Monitoring

### Metrics to Monitor:
- MySQL connection pool usage
- LDAP response time
- WireGuard peer count
- API response time
- Traffic statistics
- Error rates

### Logs:
- Application logs: `backend.log`
- MySQL logs: `/var/log/mysql/`
- LDAP logs: `/var/log/slapd/`
- WireGuard logs: `wg show` command

---

*Architecture ini dirancang untuk separation of concerns: LDAP untuk identity, MySQL untuk device data, WireGuard untuk VPN tunneling.*
