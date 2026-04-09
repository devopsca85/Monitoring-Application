-- ============================================================================
-- Migration: Add expected_page column + system_settings table
-- Run this on an EXISTING database that was created before these features
-- Safe to run multiple times (uses IF NOT EXISTS / IF NOT EXISTS checks)
-- ============================================================================

USE monitoring_db;

-- 1. Add expected_page column to site_credentials
--    (for SSO backdoor login — stores which page should open after login)
SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'site_credentials'
      AND COLUMN_NAME = 'expected_page'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE site_credentials ADD COLUMN expected_page VARCHAR(255) DEFAULT ''mainpage.aspx'' AFTER success_indicator',
    'SELECT ''Column expected_page already exists'' AS status'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Create system_settings table (for SMTP, Teams webhook, etc.)
CREATE TABLE IF NOT EXISTS system_settings (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    `key`         VARCHAR(255) NOT NULL UNIQUE,
    value         TEXT NOT NULL DEFAULT '',
    is_encrypted  TINYINT(1) DEFAULT 0,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_settings_key (`key`)
) ENGINE=InnoDB;

-- 3. Backfill: set expected_page for existing credentials that don't have it
UPDATE site_credentials
SET expected_page = 'mainpage.aspx'
WHERE expected_page IS NULL OR expected_page = '';
