-- ============================================
-- WireGuard VPN Portal Database Schema
-- MySQL Database Schema
-- ============================================

-- Create database (run this manually if needed)
-- CREATE DATABASE wireguard_vpn CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE wireguard_vpn;

-- ============================================
-- Table: vpn_devices
-- Stores VPN device information
-- ============================================
CREATE TABLE IF NOT EXISTS vpn_devices (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ldap_uid VARCHAR(100) NOT NULL COMMENT 'Username from LDAP',
    device_name VARCHAR(100) NOT NULL COMMENT 'User-defined device name',
    public_key VARCHAR(255) NOT NULL UNIQUE COMMENT 'WireGuard public key',
    vpn_ip VARCHAR(15) NOT NULL UNIQUE COMMENT 'VPN IP address (10.8.0.x)',
    status ENUM('active', 'revoked', 'expired', 'inconsistent') DEFAULT 'active',
    
    -- Bandwidth Limit (in bytes per month)
    bandwidth_limit BIGINT DEFAULT NULL COMMENT 'NULL = unlimited',
    bandwidth_used BIGINT DEFAULT 0 COMMENT 'Reset setiap bulan',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NULL COMMENT 'Last handshake time',
    expires_at TIMESTAMP NULL COMMENT 'Device expiration (optional)',
    
    -- Traffic Stats
    transfer_rx BIGINT DEFAULT 0 COMMENT 'Bytes received',
    transfer_tx BIGINT DEFAULT 0 COMMENT 'Bytes sent',
    transfer_total BIGINT DEFAULT 0 COMMENT 'Total (rx + tx)',
    
    -- Revoke Info
    revoked_at TIMESTAMP NULL,
    revoked_by VARCHAR(100) NULL COMMENT 'Username who revoked',
    revoke_reason TEXT NULL,
    
    -- Device Info (for security)
    first_seen_ip VARCHAR(45) NULL COMMENT 'IPv4 or IPv6',
    user_agent TEXT NULL,
    
    -- Optional: Encrypted private key (for backup)
    private_key_encrypted TEXT NULL,
    
    INDEX idx_ldap_uid (ldap_uid),
    INDEX idx_ldap_uid_status (ldap_uid, status),
    INDEX idx_status (status),
    INDEX idx_public_key (public_key),
    INDEX idx_vpn_ip (vpn_ip),
    INDEX idx_last_seen (last_seen),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='VPN devices table';

-- ============================================
-- Table: vpn_traffic_logs
-- Stores traffic logs for analytics and graphs
-- ============================================
CREATE TABLE IF NOT EXISTS vpn_traffic_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    ldap_uid VARCHAR(100) NOT NULL,
    public_key VARCHAR(255) NOT NULL,
    
    -- Traffic Data
    transfer_rx BIGINT DEFAULT 0,
    transfer_tx BIGINT DEFAULT 0,
    transfer_total BIGINT DEFAULT 0,
    
    -- Metadata
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (device_id) REFERENCES vpn_devices(id) ON DELETE CASCADE,
    INDEX idx_device_id (device_id),
    INDEX idx_ldap_uid (ldap_uid),
    INDEX idx_recorded_at (recorded_at),
    INDEX idx_device_recorded (device_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Traffic logs for analytics';

-- ============================================
-- Table: vpn_revoke_history
-- Audit log for revoked devices
-- ============================================
CREATE TABLE IF NOT EXISTS vpn_revoke_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    device_id INT NOT NULL,
    ldap_uid VARCHAR(100) NOT NULL,
    public_key VARCHAR(255) NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    revoked_by VARCHAR(100) NOT NULL COMMENT 'Admin or user who revoked',
    revoke_reason TEXT NULL,
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ldap_uid (ldap_uid),
    INDEX idx_revoked_at (revoked_at),
    INDEX idx_revoked_by (revoked_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Revoke history audit log';

-- ============================================
-- Table: vpn_bandwidth_limits
-- Admin-configurable bandwidth limits
-- ============================================
CREATE TABLE IF NOT EXISTS vpn_bandwidth_limits (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ldap_uid VARCHAR(100) NULL COMMENT 'NULL = global default',
    device_id INT NULL COMMENT 'NULL = per-user limit',
    bandwidth_limit BIGINT NOT NULL COMMENT 'Bytes per month',
    reset_day INT DEFAULT 1 COMMENT 'Day of month untuk reset (1-28)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (device_id) REFERENCES vpn_devices(id) ON DELETE CASCADE,
    INDEX idx_ldap_uid (ldap_uid),
    INDEX idx_device_id (device_id),
    UNIQUE KEY unique_user_limit (ldap_uid),
    UNIQUE KEY unique_device_limit (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Bandwidth limits configuration';

-- ============================================
-- Table: vpn_audit_logs
-- Security audit log for all actions
-- ============================================
CREATE TABLE IF NOT EXISTS vpn_audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    action VARCHAR(50) NOT NULL COMMENT 'device_created, device_revoked, user_enabled, etc.',
    ldap_uid VARCHAR(100) NULL,
    device_id INT NULL,
    performed_by VARCHAR(100) NOT NULL COMMENT 'Username who performed action',
    ip_address VARCHAR(45) NULL COMMENT 'IPv4 or IPv6',
    details JSON NULL COMMENT 'Additional details in JSON format',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_action (action),
    INDEX idx_ldap_uid (ldap_uid),
    INDEX idx_performed_by (performed_by),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Security audit logs';

-- ============================================
-- Insert default global bandwidth limit (optional)
-- ============================================
-- INSERT INTO vpn_bandwidth_limits (ldap_uid, device_id, bandwidth_limit, reset_day)
-- VALUES (NULL, NULL, 107374182400, 1); -- 100 GB default limit
