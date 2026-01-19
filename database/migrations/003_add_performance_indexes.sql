-- ============================================
-- Migration: Add Performance Indexes
-- Phase 8: Performance Optimization & Caching
-- ============================================
--
-- Note: MySQL doesn't support IF NOT EXISTS in CREATE INDEX (before 8.0.19)
-- This migration uses INFORMATION_SCHEMA check for idempotency
-- Safe to run multiple times
--
-- Note: Some indexes may already exist from migration 001, but we ensure all are present
-- ============================================

SET @dbname = DATABASE();

-- ============================================
-- Indexes for vpn_devices table
-- ============================================
-- Note: Some indexes (idx_ldap_uid_status, idx_public_key, idx_vpn_ip, 
-- idx_last_seen, idx_expires_at) already exist in migration 001
-- idx_qr_expires_at already exists in migration 002

SET @tablename = 'vpn_devices';

-- Index untuk created_at (untuk sorting)
SET @indexname = 'idx_created_at';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(created_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- Composite index untuk admin queries (status + created_at)
SET @indexname = 'idx_status_created_at';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(status, created_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- ============================================
-- Indexes for vpn_traffic_logs table
-- ============================================

SET @tablename = 'vpn_traffic_logs';

-- Index untuk traffic logs (device_id + recorded_at)
-- Note: idx_device_recorded already exists in migration 001 with same columns
-- This index name is kept for consistency with code that might reference it
SET @indexname = 'idx_traffic_device_recorded';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(device_id, recorded_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- Index untuk traffic logs (ldap_uid + recorded_at)
SET @indexname = 'idx_traffic_ldap_recorded';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(ldap_uid, recorded_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- ============================================
-- Indexes for vpn_revoke_history table
-- ============================================

SET @tablename = 'vpn_revoke_history';

-- Index untuk revoke history (ldap_uid + revoked_at)
SET @indexname = 'idx_revoke_ldap_at';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(ldap_uid, revoked_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- ============================================
-- Indexes for vpn_audit_logs table
-- ============================================

SET @tablename = 'vpn_audit_logs';

-- Index untuk audit logs (action + created_at)
SET @indexname = 'idx_audit_action_created';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(action, created_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- Index untuk audit logs (ldap_uid + created_at)
SET @indexname = 'idx_audit_ldap_created';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(ldap_uid, created_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- Index untuk audit logs (performed_by + created_at)
SET @indexname = 'idx_audit_performed_by';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(performed_by, created_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;
