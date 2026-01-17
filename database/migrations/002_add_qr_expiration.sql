-- ============================================
-- Migration: Add QR Code Expiration Support
-- Phase 7: QR Code Expiration & Security Enhancements
-- ============================================

-- Add columns for QR code expiration
-- Note: MySQL < 8.0.19 doesn't support ADD COLUMN IF NOT EXISTS
-- Migration runner will handle duplicate column errors gracefully (error code 1060)

-- Add qr_code_base64 column (will be skipped if already exists)
ALTER TABLE vpn_devices 
ADD COLUMN qr_code_base64 TEXT NULL COMMENT 'QR code (base64) - temporary';

-- Add qr_code_expires_at column (will be skipped if already exists)
ALTER TABLE vpn_devices 
ADD COLUMN qr_code_expires_at TIMESTAMP NULL COMMENT 'QR code expiration timestamp';

-- Add index for QR expiration queries
CREATE INDEX IF NOT EXISTS idx_qr_expires_at ON vpn_devices(qr_code_expires_at);

-- Update existing devices: set QR expiration to NULL (no QR stored)
UPDATE vpn_devices SET qr_code_expires_at = NULL WHERE qr_code_expires_at IS NULL;
