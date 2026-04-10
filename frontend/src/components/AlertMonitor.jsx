import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAlerts, acknowledgeAlerts } from '../services/api';
import { playAlarmBeep, startAlarmLoop, stopAlarmLoop } from '../services/alarm';
import { formatCSTTime } from '../services/time';

export default function AlertMonitor() {
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [alarmAcknowledged, setAlarmAcknowledged] = useState(false);
  const [warningDismissed, setWarningDismissed] = useState(false);
  const [toasts, setToasts] = useState([]);
  const knownAlertIds = useRef(null);
  const warningTimerRef = useRef(null);
  const navigate = useNavigate();

  const addToast = useCallback((title, message, type = 'critical') => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev.slice(-4), { id, title, message, type }]);
    // Auto-hide after 5 seconds
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  }, []);

  // Separate alerts by severity
  const criticalAlerts = activeAlerts.filter((a) => a.alert_type === 'critical' || !a.alert_type);
  const warningAlerts = activeAlerts.filter((a) => a.alert_type === 'warning');

  // Poll every 10 seconds
  useEffect(() => {
    const poll = () => {
      getAlerts(false).then((r) => {
        const alerts = r.data || [];
        setActiveAlerts(alerts);

        const currentIds = new Set(alerts.map((a) => a.id));
        const previousIds = knownAlertIds.current;

        if (previousIds === null) {
          // First load
          const crits = alerts.filter((a) => a.alert_type === 'critical' || !a.alert_type);
          if (crits.length > 0) {
            playAlarmBeep();
            setAlarmAcknowledged(false);
          }
          for (const a of alerts) {
            addToast(`Alert: ${a.site_name || 'Site #' + a.site_id}`, a.message || '', a.alert_type || 'critical');
          }
        } else {
          for (const a of alerts) {
            if (!previousIds.has(a.id)) {
              addToast(`Alert: ${a.site_name || 'Site #' + a.site_id}`, a.message || '', a.alert_type || 'critical');
              if (a.alert_type === 'critical' || !a.alert_type) {
                playAlarmBeep();
                setAlarmAcknowledged(false);
              }
            }
          }
          if (alerts.length === 0 && previousIds.size > 0) {
            addToast('All Clear', 'All sites are back online', 'ok');
          }
        }
        knownAlertIds.current = currentIds;
      }).catch((e) => console.error('AlertMonitor poll failed:', e));
    };
    poll();
    const id = setInterval(poll, 10000);
    return () => clearInterval(id);
  }, [addToast]);

  // Auto-hide warning banner after 30 seconds
  useEffect(() => {
    if (warningAlerts.length > 0 && criticalAlerts.length === 0) {
      setWarningDismissed(false);
      warningTimerRef.current = setTimeout(() => setWarningDismissed(true), 30000);
    } else {
      setWarningDismissed(false);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    }
    return () => { if (warningTimerRef.current) clearTimeout(warningTimerRef.current); };
  }, [warningAlerts.length, criticalAlerts.length]);

  // Alarm sound — only for critical
  useEffect(() => {
    if (criticalAlerts.length > 0 && !alarmAcknowledged) {
      startAlarmLoop();
    } else {
      stopAlarmLoop();
    }
    return () => stopAlarmLoop();
  }, [criticalAlerts.length, alarmAcknowledged]);

  // No alerts — render nothing
  if (activeAlerts.length === 0 && toasts.length === 0) return null;

  return (
    <>
      {/* CRITICAL banner — red, "sites down" */}
      {criticalAlerts.length > 0 && (
        <div style={{
          background: 'linear-gradient(90deg, #e53e3e, #c53030)',
          color: 'white', padding: '10px 24px',
          display: 'flex', alignItems: 'center', gap: '14px',
          animation: 'alarmPulse 1.5s ease-in-out infinite',
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%', background: 'rgba(255,255,255,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', flexShrink: 0,
            animation: 'alarmShake 0.5s ease-in-out infinite',
          }}>&#128680;</div>
          <div style={{ flex: 1 }}>
            <span style={{ fontWeight: 700, fontSize: '13px' }}>
              CRITICAL: {criticalAlerts.length} site{criticalAlerts.length > 1 ? 's' : ''} down
            </span>
            <span style={{ fontSize: '12px', opacity: 0.85, marginLeft: '12px' }}>
              {criticalAlerts.map((a) => a.site_name || `Site #${a.site_id}`).join(', ')}
            </span>
          </div>
          <button onClick={() => navigate('/alerts')} style={{
            background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.4)',
            color: 'white', padding: '6px 14px', borderRadius: '20px',
            cursor: 'pointer', fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
          }}>View Alerts</button>
          <button onClick={() => {
            setAlarmAcknowledged(true);
            stopAlarmLoop();
            acknowledgeAlerts().catch(() => {});
          }} style={{
            background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)',
            color: 'white', padding: '6px 14px', borderRadius: '20px',
            cursor: 'pointer', fontSize: '12px', fontWeight: 500, whiteSpace: 'nowrap',
          }}>{alarmAcknowledged ? 'Acknowledged' : 'Silence Alarm'}</button>
        </div>
      )}

      {/* WARNING banner — orange, auto-hides after 30s */}
      {warningAlerts.length > 0 && criticalAlerts.length === 0 && !warningDismissed && (
        <div style={{
          background: 'linear-gradient(90deg, #dd6b20, #c05621)',
          color: 'white', padding: '8px 24px',
          display: 'flex', alignItems: 'center', gap: '14px',
        }}>
          <span style={{ fontSize: '16px' }}>&#9888;</span>
          <div style={{ flex: 1 }}>
            <span style={{ fontWeight: 600, fontSize: '13px' }}>
              WARNING: {warningAlerts.length} site{warningAlerts.length > 1 ? 's' : ''} slow
            </span>
            <span style={{ fontSize: '12px', opacity: 0.85, marginLeft: '12px' }}>
              {warningAlerts.map((a) => a.site_name || `Site #${a.site_id}`).join(', ')}
            </span>
          </div>
          <button onClick={() => navigate('/alerts')} style={{
            background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.4)',
            color: 'white', padding: '6px 14px', borderRadius: '20px',
            cursor: 'pointer', fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
          }}>View Details</button>
        </div>
      )}

      {/* Toast notifications */}
      <div style={{
        position: 'fixed', top: 70, right: 24, zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: '10px',
        maxWidth: '420px', pointerEvents: 'none',
      }}>
        {toasts.map((t) => (
          <div key={t.id} style={{
            pointerEvents: 'auto',
            background: t.type === 'critical' ? '#fff5f5' : t.type === 'ok' ? '#f0fff4' : '#fffaf0',
            border: `1px solid ${t.type === 'critical' ? '#feb2b2' : t.type === 'ok' ? '#9ae6b4' : '#fbd38d'}`,
            borderLeft: `4px solid ${t.type === 'critical' ? '#e53e3e' : t.type === 'ok' ? '#38a169' : '#dd6b20'}`,
            borderRadius: '8px', padding: '12px 16px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            animation: 'slideInRight 0.3s ease-out',
            display: 'flex', gap: '10px', alignItems: 'flex-start',
          }}>
            <div style={{
              width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px',
              background: t.type === 'critical' ? '#e53e3e' : t.type === 'ok' ? '#38a169' : '#dd6b20',
              color: 'white', fontWeight: 700,
            }}>
              {t.type === 'critical' ? '!' : t.type === 'ok' ? '\u2713' : '\u26A0'}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: '12px', color: 'var(--color-text)' }}>{t.title}</div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.message}</div>
            </div>
            <button onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))} style={{
              background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)',
              fontSize: '16px', lineHeight: 1, padding: 0, flexShrink: 0,
            }}>&times;</button>
          </div>
        ))}
      </div>
    </>
  );
}
