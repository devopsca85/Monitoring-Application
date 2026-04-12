-- ============================================================================
-- Security & Compliance Module
-- ============================================================================

USE monitoring_db;

-- Security Scans
CREATE TABLE IF NOT EXISTS security_scans (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    site_id         INT NOT NULL,
    scanned_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    score           INT DEFAULT 0,
    grade           VARCHAR(5),
    total_findings  INT DEFAULT 0,
    critical_count  INT DEFAULT 0,
    high_count      INT DEFAULT 0,
    medium_count    INT DEFAULT 0,
    low_count       INT DEFAULT 0,
    info_count      INT DEFAULT 0,
    findings        JSON,
    headers_data    JSON,
    ssl_data        JSON,
    error_message   TEXT,
    INDEX idx_secscan_site (site_id),
    INDEX idx_secscan_time (scanned_at),
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Compliance Frameworks
CREATE TABLE IF NOT EXISTS compliance_frameworks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   TINYINT(1) DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Compliance Controls
CREATE TABLE IF NOT EXISTS compliance_controls (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    framework_id    INT NOT NULL,
    control_id      VARCHAR(50),
    category        VARCHAR(255),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    check_type      VARCHAR(50) DEFAULT 'manual',
    status          VARCHAR(50) DEFAULT 'not_started',
    evidence        TEXT,
    assigned_to     VARCHAR(255),
    due_date        DATETIME,
    last_reviewed   DATETIME,
    reviewed_by     VARCHAR(255),
    FOREIGN KEY (framework_id) REFERENCES compliance_frameworks(id) ON DELETE CASCADE
) ENGINE=InnoDB;
