-- ============================================================================
-- Migration: Add false positive support to alerts + suppression rules table
-- ============================================================================

USE monitoring_db;

-- Add false_positive columns to alerts table
SET @col = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='alerts' AND COLUMN_NAME='false_positive');
SET @sql = IF(@col=0, 'ALTER TABLE alerts ADD COLUMN false_positive TINYINT(1) DEFAULT 0 AFTER resolved_at, ADD COLUMN false_positive_by VARCHAR(255) NULL AFTER false_positive, ADD COLUMN false_positive_at DATETIME NULL AFTER false_positive_by', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

-- Create false_positive_rules table
CREATE TABLE IF NOT EXISTS false_positive_rules (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    site_id       INT NOT NULL,
    error_pattern VARCHAR(500) NOT NULL,
    created_by    VARCHAR(255) NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active     TINYINT(1) DEFAULT 1,
    INDEX idx_fpr_site (site_id),
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Backfill: ensure no NULL false_positive values
UPDATE alerts SET false_positive = 0 WHERE false_positive IS NULL;
