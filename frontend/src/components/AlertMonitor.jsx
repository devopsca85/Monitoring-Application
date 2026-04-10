import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAlerts } from '../services/api';
import { playAlarmBeep, startAlarmLoop, stopAlarmLoop } from '../services/alarm';

function formatCST(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleString('en-US', {
    timeZone: 'America/Chicago',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true,
  }) + ' CST';
}

export default function AlertMonitor() {
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [alarmAcknowledged, setAlarmAcknowledged] = useState(false);
  const [toasts, setToasts] = useState([]);
  const knownAlertIds = useRef(new Set());
  const isFirstLoad = useRef(true);
  const navigate = useNavigate();

  const addToast = (title, message, type = 'critical') => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev.slice(-4), { id, title, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 8000);
  };

  // Poll for alerts every 15 seconds — runs globally regardless of current page
  useEffect(() => {
    const poll = () => {
      getAlerts(false).then((r) => {
        const alerts = r.data;
        setActiveAlerts(alerts);

        // Detect new alerts
        if (!isFirstLoad.current) {
          for (const a of alerts) {
            if (!knownAlertIds.current.has(a.id)) {
              const name = a.site_name || `Site #${a.site_id}`;
              addToast(`Alert: ${name}`, a.message || 'Monitoring alert triggered', a.alert_type || 'critical');
              playAlarmBeep();
              setAlarmAcknowledged(false);
            }
          }
        }

        // Check if all alerts resolved
        if (alerts.length === 0 && knownAlertIds.current.size > 0 && !isFirstLoad.current) {
          addToast('All Clear', 'All sites are back online', 'ok');
        }

        knownAlertIds.current = new Set(alerts.map((a) => a.id));
        isFirstLoad.current = false;
      }).catch(() => {});
    };

    poll();
    const id = setInterval(poll, 15000);
    return () => clearInterval(id);
  }, []);

  // Alarm loop control
  useEffect(() => {
    if (activeAlerts.length > 0 && !alarmAcknowledged) {
      startAlarmLoop();
    } else {
      stopAlarmLoop();
    }
    return () => stopAlarmLoop();
  }, [activeAlerts, alarmAcknowledged]);

  return (
    <>
      {/* Alarm banner — shows on ALL pages when sites are down */}
      {activeAlerts.length > 0 && (
        <div style={{
          background: 'linear-gradient(90deg, #e53e3e, #c53030)',
          color: 'white',
          padding: '10px 24px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          animation: 'alarmPulse 1.5s ease-in-out infinite',
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: '50%',
            background: 'rgba(255,255,255,0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '16px', flexShrink: 0,
            animation: 'alarmShake 0.5s ease-in-out infinite',
          }}>
            &#128680;
          </div>
          <div style={{ flex: 1 }}>
            <span style={{ fontWeight: 700, fontSize: '13px' }}>
              ALERT: {activeAlerts.length} site{activeAlerts.length > 1 ? 's' : ''} down
            </span>
            <span style={{ fontSize: '12px', opacity: 0.85, marginLeft: '12px' }}>
              {activeAlerts.map((a) => a.site_name || `Site #${a.site_id}`).join(', ')}
            </span>
          </div>
          <button
            onClick={() => navigate('/alerts')}
            style={{
              background: 'rgba(255,255,255,0.2)', border: '1px solid rgba(255,255,255,0.4)',
              color: 'white', padding: '6px 14px', borderRadius: '20px',
              cursor: 'pointer', fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
            }}
          >
            View Alerts
          </button>
          <button
            onClick={() => { setAlarmAcknowledged(true); stopAlarmLoop(); }}
            style={{
              background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)',
              color: 'white', padding: '6px 14px', borderRadius: '20px',
              cursor: 'pointer', fontSize: '12px', fontWeight: 500, whiteSpace: 'nowrap',
            }}
          >
            {alarmAcknowledged ? 'Acknowledged' : 'Silence Alarm'}
          </button>
        </div>
      )}

      {/* Toast notifications — top right, visible on ALL pages */}
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
            borderRadius: '8px',
            padding: '14px 18px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            animation: 'slideInRight 0.3s ease-out',
            display: 'flex', gap: '12px', alignItems: 'flex-start',
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px',
              background: t.type === 'critical' ? '#e53e3e' : t.type === 'ok' ? '#38a169' : '#dd6b20',
              color: 'white', fontWeight: 700,
            }}>
              {t.type === 'critical' ? '!' : t.type === 'ok' ? '\u2713' : '\u26A0'}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-text)', marginBottom: '2px' }}>
                {t.title}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {t.message}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                {formatCST(new Date().toISOString())}
              </div>
            </div>
            <button onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))} style={{
              background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)',
              fontSize: '18px', lineHeight: 1, padding: '0 2px', flexShrink: 0,
            }}>&times;</button>
          </div>
        ))}
      </div>
    </>
  );
}
