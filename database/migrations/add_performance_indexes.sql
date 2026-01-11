-- ============================================
-- Migration: Add Performance Indexes
-- Phase 8: Performance Optimization & Caching
-- ============================================

-- Index untuk frequently queried fields di vpn_devices
-- (Beberapa index mungkin sudah ada, tapi kita pastikan semua ada)

-- Index untuk ldap_uid + status (untuk get_user_devices)
CREATE INDEX IF NOT EXISTS idx_ldap_uid_status ON vpn_devices(ldap_uid, status);

-- Index untuk public_key (untuk get_device_by_public_key)
CREATE INDEX IF NOT EXISTS idx_public_key ON vpn_devices(public_key);

-- Index untuk vpn_ip (untuk IP allocation check)
CREATE INDEX IF NOT EXISTS idx_vpn_ip ON vpn_devices(vpn_ip);

-- Index untuk last_seen (untuk device expiration check)
CREATE INDEX IF NOT EXISTS idx_last_seen ON vpn_devices(last_seen);

-- Index untuk expires_at (untuk device expiration)
CREATE INDEX IF NOT EXISTS idx_expires_at ON vpn_devices(expires_at);

-- Index untuk qr_code_expires_at (untuk QR expiration check)
CREATE INDEX IF NOT EXISTS idx_qr_expires_at ON vpn_devices(qr_code_expires_at);

-- Index untuk created_at (untuk sorting)
CREATE INDEX IF NOT EXISTS idx_created_at ON vpn_devices(created_at);

-- Composite index untuk admin queries (status + created_at)
CREATE INDEX IF NOT EXISTS idx_status_created_at ON vpn_devices(status, created_at);

-- Index untuk traffic logs
CREATE INDEX IF NOT EXISTS idx_traffic_device_recorded ON vpn_traffic_logs(device_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_traffic_ldap_recorded ON vpn_traffic_logs(ldap_uid, recorded_at);

-- Index untuk revoke history
CREATE INDEX IF NOT EXISTS idx_revoke_ldap_at ON vpn_revoke_history(ldap_uid, revoked_at);

-- Index untuk audit logs
CREATE INDEX IF NOT EXISTS idx_audit_action_created ON vpn_audit_logs(action, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_ldap_created ON vpn_audit_logs(ldap_uid, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_performed_by ON vpn_audit_logs(performed_by, created_at);
