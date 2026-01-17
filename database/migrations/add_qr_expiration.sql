-- ============================================
-- Migration: Add QR Code Expiration Support
-- Phase 7: QR Code Expiration & Security Enhancements
-- ============================================

-- Add columns for QR code expiration
-- Note: MySQL 8.0 doesn't support IF NOT EXISTS in ALTER TABLE
-- This migration is idempotent - safe to run multiple times

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

-- Add index for QR expiration queries (IF NOT EXISTS is supported for CREATE INDEX in MySQL 8.0)
CREATE INDEX IF NOT EXISTS idx_qr_expires_at ON vpn_devices(qr_code_expires_at);

-- Update existing devices: set QR expiration to NULL (no QR stored)
UPDATE vpn_devices SET qr_code_expires_at = NULL WHERE qr_code_expires_at IS NULL;
