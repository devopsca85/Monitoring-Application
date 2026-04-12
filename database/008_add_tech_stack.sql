-- ============================================================================
-- Migration: Add tech_stack column to sites table
-- Supports: asp_net, asp_net_core, php, nodejs, react, angular, vue,
--           python, java, ruby, wordpress, drupal, static, other
-- ============================================================================

USE monitoring_db;

SET @col = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sites' AND COLUMN_NAME='tech_stack');

SET @sql = IF(@col=0,
    "ALTER TABLE sites ADD COLUMN tech_stack ENUM('asp_net','asp_net_core','php','nodejs','react','angular','vue','python','java','ruby','wordpress','drupal','static','other') DEFAULT 'other' AFTER check_type",
    'SELECT 1');

PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- Backfill existing sites to 'other'
UPDATE sites SET tech_stack = 'other' WHERE tech_stack IS NULL;
