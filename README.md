# WireGuard VPN Portal Backend

Backend API untuk WireGuard VPN Portal dengan LDAP Authentication, MySQL database, dan comprehensive monitoring.

## Features

- ✅ LDAP Authentication & Authorization
- ✅ Multi-Device Support (per user)
- ✅ QR Code Generation dengan Expiration
- ✅ Bandwidth Limit Management
- ✅ Traffic Monitoring & Analytics
- ✅ Device Expiration (Auto-revoke)
- ✅ Comprehensive Audit Logging
- ✅ Alert System
- ✅ Health Monitoring
- ✅ Performance Optimization (Caching, Connection Pooling)
- ✅ Security Hardening

## Architecture

### VPS 1: Backend Services (117.53.44.59)
- WireGuard Server
- OpenLDAP Server
- Backend API (FastAPI)
- Frontend
- Redis

### VPS 2: Database Server (117.53.45.105)
- MySQL Server

## Quick Start

### Development

```bash
# Clone repository
git clone <repo-url>
cd wireguard-backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp env.example.txt .env
# Edit .env dengan credentials Anda

# Run application
uvicorn app.main:app --reload
```

### Docker

```bash
# Build image
docker build -t wireguard-backend .

# Run dengan docker-compose
docker-compose up -d
```

### Production

See `docs/DEPLOYMENT_GUIDE.md` untuk detailed deployment instructions.

## Documentation

- [API Documentation](docs/API_DOCUMENTATION.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Admin Guide](docs/ADMIN_GUIDE.md)
- [User Guide](docs/USER_GUIDE.md)
- [Backup & Restore](docs/BACKUP_RESTORE.md)
- [Architecture Overview](ARCHITECTURE.md)

## Project Structure

```
wireguard-backend/
├── app/
│   ├── core/           # Core utilities (LDAP, cache, encryption)
│   ├── database/       # Database connection & queries
│   ├── middleware/     # Middleware (auth, security, graceful degradation)
│   ├── routers/        # API endpoints
│   ├── services/       # Business logic
│   └── wg/            # WireGuard utilities
├── database/
│   ├── migrations/     # Database migrations
│   └── schema.sql     # Database schema
├── docs/              # Documentation
├── ldap/              # LDAP schema extensions
├── nginx/             # Nginx configuration
├── scripts/           # Setup scripts
├── systemd/           # Systemd service files
└── tests/             # Test files
```

## Environment Variables

See `env.example.txt` untuk complete list of environment variables.

Key variables:
- `LDAP_SERVER` - LDAP server address
- `MYSQL_HOST` - MySQL server address (remote)
- `JWT_SECRET` - JWT secret key
- `ENCRYPTION_KEY` - Encryption key untuk private keys
- `CORS_ORIGINS` - Allowed CORS origins

## API Endpoints

### Public
- `GET /health/` - Health check
- `POST /auth/login` - Login

### User Endpoints
- `GET /devices/` - List my devices
- `POST /devices/add` - Add device
- `GET /devices/{id}` - Get device details
- `DELETE /devices/{id}` - Revoke device
- `GET /devices/{id}/qr` - Get QR code

### Admin Endpoints
- `GET /admin/users` - List all users
- `POST /admin/users/{username}/enable` - Enable VPN access
- `POST /admin/users/{username}/disable` - Disable VPN access
- `GET /admin/devices` - List all devices
- `GET /admin/monitoring/alerts` - Get alerts
- `GET /admin/monitoring/audit-logs` - Get audit logs

See `docs/API_DOCUMENTATION.md` untuk complete API reference.

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html
```

## Development Phases

- ✅ Phase 1: Foundation & Database Setup
- ✅ Phase 2: LDAP Schema Extension
- ✅ Phase 3: Device Management Core
- ✅ Phase 4: Admin Features
- ✅ Phase 5: Traffic Monitoring & Analytics
- ✅ Phase 6: Testing & Optimization
- ✅ Phase 7: QR Code Expiration & Security Enhancements
- ✅ Phase 8: Performance Optimization & Caching
- ✅ Phase 9: Monitoring, Health Checks & Alerting
- ✅ Phase 10: Production Deployment & Documentation

## Security

- JWT authentication
- Rate limiting
- Input validation
- SQL injection prevention
- XSS protection
- Security headers
- Audit logging
- Private key encryption

## License

[Your License Here]

## Support

Untuk support dan pertanyaan:
- Check documentation di `docs/` directory
- Review troubleshooting guides
- Contact administrator
