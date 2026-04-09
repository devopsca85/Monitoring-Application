-- ============================================================================
-- Migration: Add slow_threshold_ms column to sites table
-- Alerts when page response time exceeds this threshold (default 5000ms)
-- ============================================================================

USE monitoring_db;

SET @col_exists = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'sites'
      AND COLUMN_NAME = 'slow_threshold_ms'
);

SET @sql = IF(@col_exists = 0,
    'ALTER TABLE sites ADD COLUMN slow_threshold_ms INT DEFAULT 8000 AFTER check_interval_minutes',
    'SELECT ''Column slow_threshold_ms already exists'' AS status'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
