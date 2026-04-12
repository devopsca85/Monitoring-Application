-- ============================================================================
-- Site Groups — shared credentials + environment grouping
-- ============================================================================

USE monitoring_db;

CREATE TABLE IF NOT EXISTS site_groups (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(255) NOT NULL UNIQUE,
    description         TEXT,
    environment         VARCHAR(50),
    login_url           VARCHAR(500),
    username_selector   VARCHAR(255) DEFAULT '#username',
    password_selector   VARCHAR(255) DEFAULT '#password',
    submit_selector     VARCHAR(255) DEFAULT "input[type='submit']",
    success_indicator   VARCHAR(255),
    expected_page       VARCHAR(255) DEFAULT 'mainpage.aspx',
    encrypted_username  TEXT,
    encrypted_password  TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Add group_id to sites table
SET @col = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='sites' AND COLUMN_NAME='group_id');
SET @sql = IF(@col=0,
    'ALTER TABLE sites ADD COLUMN group_id INT NULL AFTER id, ADD INDEX idx_sites_group (group_id), ADD CONSTRAINT fk_sites_group FOREIGN KEY (group_id) REFERENCES site_groups(id) ON DELETE SET NULL',
    'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;
