-- ============================================================================
-- Fix: Resolve alerts for deleted sites ("Site #None" in the UI)
-- ============================================================================

USE monitoring_db;

-- Show orphaned alerts (site no longer exists)
SELECT a.id, a.site_id, a.alert_type, a.message, a.resolved, a.created_at
FROM alerts a
LEFT JOIN sites s ON a.site_id = s.id
WHERE s.id IS NULL;

-- Auto-resolve orphaned alerts
UPDATE alerts a
LEFT JOIN sites s ON a.site_id = s.id
SET a.resolved = 1, a.resolved_at = NOW(),
    a.message = CONCAT(IFNULL(a.message, ''), ' [Auto-resolved: site deleted]')
WHERE s.id IS NULL AND a.resolved = 0;

-- Delete orphaned alerts entirely (optional — uncomment if you want to remove them)
-- DELETE a FROM alerts a LEFT JOIN sites s ON a.site_id = s.id WHERE s.id IS NULL;

-- Verify no orphans remain
SELECT COUNT(*) AS orphaned_alerts
FROM alerts a LEFT JOIN sites s ON a.site_id = s.id
WHERE s.id IS NULL AND a.resolved = 0;
