-- ============================================
-- Migration: Add QR Code Expiration Support
-- Phase 7: QR Code Expiration & Security Enhancements
-- ============================================

-- Note: MySQL doesn't support IF NOT EXISTS in ALTER TABLE
-- This migration uses INFORMATION_SCHEMA check for idempotency
-- Safe to run multiple times

-- Check and add qr_code_base64 column
SET @dbname = DATABASE();
SET @tablename = 'vpn_devices';
SET @columnname = 'qr_code_base64';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (COLUMN_NAME = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TEXT NULL COMMENT ''QR code (base64) - temporary'';')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Check and add qr_code_expires_at column
SET @columnname = 'qr_code_expires_at';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (COLUMN_NAME = @columnname)
  ) > 0,
  'SELECT 1',
  CONCAT('ALTER TABLE ', @tablename, ' ADD COLUMN ', @columnname, ' TIMESTAMP NULL COMMENT ''QR code expiration timestamp'';')
));
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;

-- Add index for QR expiration queries (check if exists first for MySQL compatibility)
SET @dbname = DATABASE();
SET @tablename = 'vpn_devices';
SET @indexname = 'idx_qr_expires_at';
SET @preparedStatement = (SELECT IF(
  (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
    WHERE
      (TABLE_SCHEMA = @dbname)
      AND (TABLE_NAME = @tablename)
      AND (INDEX_NAME = @indexname)
  ) > 0,
  'SELECT 1',
  CONCAT('CREATE INDEX ', @indexname, ' ON ', @tablename, '(qr_code_expires_at);')
));
PREPARE createIndexIfNotExists FROM @preparedStatement;
EXECUTE createIndexIfNotExists;
DEALLOCATE PREPARE createIndexIfNotExists;

-- Update existing devices: set QR expiration to NULL (no QR stored)
UPDATE vpn_devices SET qr_code_expires_at = NULL WHERE qr_code_expires_at IS NULL;
