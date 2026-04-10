-- ============================================================================
-- Fix: NULL values in alerts table that cause API serialization failures
-- Run this to fix existing alert rows with NULL boolean fields
-- ============================================================================

USE monitoring_db;

-- Fix NULL notified → default to 0
UPDATE alerts SET notified = 0 WHERE notified IS NULL;

-- Fix NULL resolved → default to 0
UPDATE alerts SET resolved = 0 WHERE resolved IS NULL;

-- Verify
SELECT id, site_id, alert_type, notified, resolved, created_at
FROM alerts ORDER BY created_at DESC LIMIT 20;
