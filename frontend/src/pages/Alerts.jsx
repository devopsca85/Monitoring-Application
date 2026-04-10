import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAlerts, getAlertHistory, resolveAlert, getSitesStatus } from '../services/api';

function formatCST(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('en-US', {
    timeZone: 'America/Chicago',
    year: 'numeric', month: 'short', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: true,
  }) + ' CST';
}

function formatDuration(startStr, endStr) {
  if (!startStr) return '-';
  const start = new Date(startStr).getTime();
  const end = endStr ? new Date(endStr).getTime() : Date.now();
  const diffSec = Math.round((end - start) / 1000);
  if (diffSec < 60) return `${diffSec}s`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ${diffSec % 60}s`;
  const h = Math.floor(diffSec / 3600);
  const m = Math.floor((diffSec % 3600) / 60);
  if (h < 24) return `${h}h ${m}m`;
  const d = Math.floor(h / 24);
  return `${d}d ${h % 24}h`;
}

export default function Alerts() {
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [history, setHistory] = useState([]);
  const [sites, setSites] = useState([]);
  const [tab, setTab] = useState('active');
  const [loading, setLoading] = useState(true);

  const load = () => {
    Promise.all([
      getAlerts(false).then((r) => setActiveAlerts(r.data || [])).catch((e) => { console.error('Active alerts:', e); setActiveAlerts([]); }),
      getAlertHistory(100).then((r) => setHistory(r.data || [])).catch((e) => { console.error('Alert history:', e); setHistory([]); }),
      getSitesStatus().then((r) => setSites(r.data || [])).catch((e) => { console.error('Sites status:', e); setSites([]); }),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const handleResolve = async (id) => {
    await resolveAlert(id);
    load();
  };

  const resolvedAlerts = history.filter((a) => a.resolved);
  const criticalSites = sites.filter((s) => s.last_status === 'critical');
  const warningSites = sites.filter((s) => s.last_status === 'warning');
  const slowSites = sites.filter((s) => s.is_slow);

  const tabData = tab === 'active' ? activeAlerts : tab === 'resolved' ? resolvedAlerts : history;

  return (
    <div>
      <div className="page-header">
        <h2>Alerts & Monitoring Status</h2>
        <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Auto-refreshes every 15s | Times in CST</span>
      </div>

      {/* Summary Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', marginBottom: '20px' }}>
        <div className={`stat-card ${activeAlerts.length > 0 ? 'critical' : 'ok'}`}>
          <div className="stat-value">{activeAlerts.length}</div>
          <div className="stat-label">Active Alerts</div>
        </div>
        <div className="stat-card critical">
          <div className="stat-value">{criticalSites.length}</div>
          <div className="stat-label">Sites Down</div>
        </div>
        <div className="stat-card warning">
          <div className="stat-value">{warningSites.length + slowSites.length}</div>
          <div className="stat-label">Warnings / Slow</div>
        </div>
        <div className="stat-card ok">
          <div className="stat-value">{resolvedAlerts.length}</div>
          <div className="stat-label">Resolved (recent)</div>
        </div>
        <div className="stat-card info">
          <div className="stat-value">{history.length}</div>
          <div className="stat-label">Total Events</div>
        </div>
      </div>

      {/* Current Site Health — always visible */}
      {(criticalSites.length > 0 || slowSites.length > 0) && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <div className="card-header"><h3>Current Issues</h3></div>
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Site</th><th>Status</th><th>Response</th><th>Last Check</th><th>Issue</th></tr>
              </thead>
              <tbody>
                {[...criticalSites, ...slowSites].map((s) => (
                  <tr key={s.id} style={{ background: s.last_status === 'critical' ? 'rgba(229,62,62,0.03)' : 'rgba(221,107,32,0.03)' }}>
                    <td><Link to={`/sites/${s.id}`} style={{ fontWeight: 500 }}>{s.name}</Link></td>
                    <td><span className={`badge badge-${s.last_status || 'warning'}`}>{s.last_status || 'slow'}</span></td>
                    <td style={{ fontVariantNumeric: 'tabular-nums' }}>{s.last_response_time_ms ? `${Math.round(s.last_response_time_ms)}ms` : '-'}</td>
                    <td style={{ fontSize: '12px' }}>{formatCST(s.last_checked_at)}</td>
                    <td style={{ fontSize: '12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {s.last_error || (s.is_slow ? `Slow (>${s.slow_threshold_ms}ms)` : 'Down')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab Buttons */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {[
          { key: 'active', label: `Active (${activeAlerts.length})` },
          { key: 'resolved', label: `Resolved (${resolvedAlerts.length})` },
          { key: 'all', label: `All History (${history.length})` },
        ].map((t) => (
          <button key={t.key} className={`btn ${tab === t.key ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Alert Table */}
      <div className="card">
        <div className="card-header">
          <h3>Alert Log</h3>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th>Severity</th>
                <th>Message</th>
                <th>Triggered (CST)</th>
                <th>Resolved (CST)</th>
                <th>Duration</th>
                <th>Status</th>
                {tab !== 'resolved' && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {tabData.map((alert) => (
                <tr key={`${alert.id}-${alert.resolved}`} style={{
                  background: !alert.resolved ? 'rgba(229, 62, 62, 0.03)' : undefined,
                }}>
                  <td>
                    <Link to={`/sites/${alert.site_id}`} style={{ fontWeight: 500 }}>
                      {alert.site_name || `Site #${alert.site_id}`}
                    </Link>
                    {alert.site_url && (
                      <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {alert.site_url}
                      </div>
                    )}
                  </td>
                  <td>
                    <span className={`badge badge-${alert.alert_type || 'critical'}`}>
                      {alert.alert_type || 'critical'}
                    </span>
                  </td>
                  <td style={{ maxWidth: '280px', fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {alert.message || '-'}
                  </td>
                  <td style={{ fontSize: '12px', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {formatCST(alert.created_at)}
                  </td>
                  <td style={{ fontSize: '12px', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {alert.resolved ? formatCST(alert.resolved_at) : (
                      <span style={{ color: 'var(--color-status-critical)', fontWeight: 600, fontSize: '11px' }}>ONGOING</span>
                    )}
                  </td>
                  <td style={{ fontSize: '12px', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    <span style={{
                      color: !alert.resolved ? 'var(--color-status-critical)' : 'var(--color-text-secondary)',
                      fontWeight: !alert.resolved ? 600 : 400,
                    }}>
                      {formatDuration(alert.created_at, alert.resolved_at)}
                    </span>
                  </td>
                  <td>
                    {alert.resolved ? (
                      <span className="badge badge-ok">Resolved</span>
                    ) : (
                      <span className="badge badge-critical" style={{ animation: 'pulse 2s infinite' }}>Active</span>
                    )}
                  </td>
                  {tab !== 'resolved' && (
                    <td>
                      {!alert.resolved && (
                        <button onClick={() => handleResolve(alert.id)} className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '12px' }}>
                          Resolve
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {tabData.length === 0 && !loading && (
                <tr>
                  <td colSpan={tab !== 'resolved' ? 8 : 7} style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>
                    {tab === 'active' ? (
                      <div>
                        <div style={{ fontSize: '24px', marginBottom: '8px', color: 'var(--color-status-ok)' }}>&#10003;</div>
                        <div style={{ fontWeight: 500, marginBottom: '4px' }}>All Clear</div>
                        <div>No active alerts — all monitored sites are running normally.</div>
                      </div>
                    ) : tab === 'resolved' ? 'No resolved alerts in recent history' : 'No alerts recorded yet'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
