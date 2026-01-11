# API Documentation: WireGuard VPN Portal Backend

## Base URL
```
http://your-domain.com/api
# atau
http://117.53.44.59:8000
```

## Authentication

Semua endpoints (kecuali `/health` dan `/auth/login`) memerlukan JWT token di header:
```
Authorization: Bearer <access_token>
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "user123",
  "password": "password123"
}
```

**Response:**
```json
{
  "status": "ok",
  "username": "user123",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "wireguard_enabled": true,
  "max_devices": 3
}
```

### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

## User Endpoints

### List My Devices
```http
GET /devices/
Authorization: Bearer <token>
```

### Add Device
```http
POST /devices/add
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_name": "My Laptop"
}
```

### Get Device Details
```http
GET /devices/{device_id}
Authorization: Bearer <token>
```

### Revoke Device
```http
DELETE /devices/{device_id}
Authorization: Bearer <token>
```

### Get QR Code
```http
GET /devices/{device_id}/qr
Authorization: Bearer <token>
```

### Regenerate QR Code
```http
POST /devices/{device_id}/qr/regenerate
Authorization: Bearer <token>
```

### Check Device Limit
```http
GET /devices/check/limit
Authorization: Bearer <token>
```

## Admin Endpoints

### List All Users
```http
GET /admin/users
Authorization: Bearer <admin_token>
```

### Enable User VPN Access
```http
POST /admin/users/{username}/enable
Authorization: Bearer <admin_token>
```

### Disable User VPN Access
```http
POST /admin/users/{username}/disable
Authorization: Bearer <admin_token>
```

### Set User Max Devices
```http
POST /admin/users/{username}/max-devices
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "max_devices": 5
}
```

### List All Devices
```http
GET /admin/devices?status=active&limit=100&offset=0
Authorization: Bearer <admin_token>
```

### Revoke Device (Admin)
```http
DELETE /admin/devices/{device_id}
Authorization: Bearer <admin_token>
```

### Get Alerts
```http
GET /admin/monitoring/alerts?limit=50&severity=high
Authorization: Bearer <admin_token>
```

### Get Audit Logs
```http
GET /admin/monitoring/audit-logs?action=device_created&limit=100
Authorization: Bearer <admin_token>
```

### Get System Statistics
```http
GET /admin/monitoring/stats
Authorization: Bearer <admin_token>
```

### Set Bandwidth Limit
```http
POST /admin/bandwidth/device/{device_id}/limit
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "limit_bytes": 107374182400  # 100 GB
}
```

## Health Check Endpoints

### Basic Health
```http
GET /health/
```

### Database Health
```http
GET /health/database
```

### LDAP Health
```http
GET /health/ldap
```

### Redis Health
```http
GET /health/redis
```

### WireGuard Health
```http
GET /health/wireguard
```

### Consistency Check
```http
GET /health/consistency
```

### Full Health Check
```http
GET /health/full
```

## Analytics Endpoints

### Get Traffic Analytics
```http
GET /analytics/traffic?device_id=1&hours=24
Authorization: Bearer <token>
```

### Get Device Analytics
```http
GET /analytics/device/{device_id}
Authorization: Bearer <token>
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid token"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 503 Service Unavailable
```json
{
  "status": "service_unavailable",
  "message": "LDAP service is temporarily unavailable",
  "error": "LDAP_CONNECTION_ERROR",
  "retry_after": 60
}
```

## Rate Limiting

- Login: 100 requests per 60 seconds
- Add Device: 5 requests per 60 seconds
- Regenerate QR: 3 requests per 60 seconds
- Other endpoints: Varies

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1633024800
```
