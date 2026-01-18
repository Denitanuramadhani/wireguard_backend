-- ============================================
-- Migration: Add QR Code Expiration Support
-- Phase 7: QR Code Expiration & Security Enhancements
-- ============================================

-- Add columns for QR code expiration
<<<<<<< HEAD:database/migrations/002_add_qr_expiration.sql
-- Note: MySQL < 8.0.19 doesn't support ADD COLUMN IF NOT EXISTS
-- Migration runner will handle duplicate column errors gracefully (error code 1060)

-- Add qr_code_base64 column (will be skipped if already exists)
ALTER TABLE vpn_devices 
ADD COLUMN qr_code_base64 TEXT NULL COMMENT 'QR code (base64) - temporary';

-- Add qr_code_expires_at column (will be skipped if already exists)
ALTER TABLE vpn_devices 
ADD COLUMN qr_code_expires_at TIMESTAMP NULL COMMENT 'QR code expiration timestamp';
=======
-- Note: MySQL 8.0 doesn't support IF NOT EXISTS in ALTER TABLE
-- This migration is idempotent - safe to run multiple times
>>>>>>> a26638eb4b8af0e3d06c3e2f99de8ce21e12449f:database/migrations/add_qr_expiration.sql

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
