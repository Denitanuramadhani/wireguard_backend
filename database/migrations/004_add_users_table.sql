-- ============================================
-- Migration: Add Users Table
-- Phase: Role-based Authorization
-- ============================================
--
-- This migration creates the 'users' table for storing user roles
-- User identity & authentication tetap di LDAP
-- MySQL hanya menyimpan: username, role, created_at
--
-- Note: This migration is idempotent - safe to run multiple times
-- ============================================

-- ============================================
-- Table: users
-- Stores user roles for authorization
-- User identity & password tetap di LDAP
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE COMMENT 'Username from LDAP (reference only)',
    role ENUM('user', 'admin') DEFAULT 'user' COMMENT 'User role for authorization',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When user was created',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Last role update',
    
    INDEX idx_username (username),
    INDEX idx_role (role),
    INDEX idx_username_role (username, role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User roles table (user identity tetap di LDAP)';

-- ============================================
-- Notes:
-- - User identity (username, password, attributes) tetap di LDAP
-- - MySQL hanya menyimpan role untuk authorization
-- - Authentication: LDAP
-- - Authorization: MySQL role
-- ============================================

