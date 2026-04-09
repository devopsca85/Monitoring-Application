-- ============================================================================
-- Fix: Resolve stale unresolved alerts that may be blocking new alert creation
-- Run this once if alerts are showing zero despite sites being down
-- ============================================================================

USE monitoring_db;

-- Show current unresolved alerts
SELECT a.id, a.site_id, s.name AS site_name, a.alert_type, a.message,
       a.created_at, a.notified, a.notified_at
FROM alerts a
LEFT JOIN sites s ON a.site_id = s.id
WHERE a.resolved = 0
ORDER BY a.created_at DESC;

-- Resolve all stale alerts (older than 1 hour and still unresolved)
UPDATE alerts
SET resolved = 1,
    resolved_at = NOW()
WHERE resolved = 0
  AND created_at < DATE_SUB(NOW(), INTERVAL 1 HOUR);

-- Verify
SELECT COUNT(*) AS remaining_unresolved FROM alerts WHERE resolved = 0;
