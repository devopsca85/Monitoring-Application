-- ============================================================================
-- Kubernetes Monitoring Module — Database Schema
-- ============================================================================

USE monitoring_db;

CREATE TABLE IF NOT EXISTS k8s_clusters (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    name                    VARCHAR(255) NOT NULL,
    cloud_provider          VARCHAR(50) DEFAULT 'azure',
    environment             VARCHAR(50) DEFAULT 'production',
    region                  VARCHAR(100),
    api_server_url          VARCHAR(500),
    auth_type               VARCHAR(50) DEFAULT 'kubeconfig',
    encrypted_kubeconfig    TEXT,
    encrypted_token         TEXT,
    namespace_filter        VARCHAR(500),
    is_active               TINYINT(1) DEFAULT 1,
    check_interval_minutes  INT DEFAULT 3,
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS k8s_snapshots (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    cluster_id          INT NOT NULL,
    checked_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    cluster_status      VARCHAR(50),
    k8s_version         VARCHAR(50),
    total_nodes         INT DEFAULT 0,
    ready_nodes         INT DEFAULT 0,
    total_pods          INT DEFAULT 0,
    running_pods        INT DEFAULT 0,
    failed_pods         INT DEFAULT 0,
    pending_pods        INT DEFAULT 0,
    cpu_capacity_cores  FLOAT,
    cpu_used_cores      FLOAT,
    memory_capacity_gb  FLOAT,
    memory_used_gb      FLOAT,
    nodes_data          JSON,
    pods_data           JSON,
    events_data         JSON,
    error_message       TEXT,
    INDEX idx_k8s_snap_cluster (cluster_id),
    INDEX idx_k8s_snap_time (checked_at),
    FOREIGN KEY (cluster_id) REFERENCES k8s_clusters(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS k8s_alerts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    cluster_id      INT NOT NULL,
    alert_type      VARCHAR(50),
    severity        VARCHAR(20),
    resource_name   VARCHAR(255),
    namespace       VARCHAR(255),
    message         TEXT,
    resolved        TINYINT(1) DEFAULT 0,
    resolved_at     DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_k8s_alert_cluster (cluster_id),
    FOREIGN KEY (cluster_id) REFERENCES k8s_clusters(id) ON DELETE CASCADE
) ENGINE=InnoDB;
