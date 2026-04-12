import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAlerts, getAlertHistory, resolveAlert, getSitesStatus, markFalsePositive } from '../services/api';
import { formatCST } from '../services/time';

function formatDuration(startStr, endStr) {
  if (!startStr) return '-';
  const start = new Date(startStr).getTime();
  const end = endStr ? new Date(endStr).getTime() : Date.now();
  const sec = Math.round((end - start) / 1000);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`;
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60);
  if (h < 24) return `${h}h ${m}m`;
  return `${Math.floor(h / 24)}d ${h % 24}h`;
}

export default function Alerts({ isAdmin = false }) {
  const [activeAlerts, setActiveAlerts] = useState([]);
  const [history, setHistory] = useState([]);
  const [sites, setSites] = useState([]);
  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setError('');
    Promise.all([
      getAlerts(false).then((r) => { setActiveAlerts(r.data || []); return r.data; })
        .catch((e) => { console.error('Active alerts failed:', e); setError('Failed to load alerts — check browser console'); return []; }),
      getAlertHistory(100).then((r) => { setHistory(r.data || []); return r.data; })
        .catch((e) => { console.error('Alert history failed:', e); return []; }),
      getSitesStatus().then((r) => { setSites(r.data || []); return r.data; })
        .catch((e) => { console.error('Sites status failed:', e); return []; }),
    ]).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { const id = setInterval(load, 15000); return () => clearInterval(id); }, []);

  const handleResolve = async (id) => { await resolveAlert(id); load(); };
  const handleFalsePositive = async (id) => {
    if (!confirm('Mark as false positive? Future alerts with this same pattern will be suppressed.')) return;
    await markFalsePositive(id); load();
  };

  const resolvedAlerts = history.filter((a) => a.resolved);
  const criticalSites = sites.filter((s) => s.last_status === 'critical');
  const warningSites = sites.filter((s) => s.last_status === 'warning' || s.is_slow);
  const healthySites = sites.filter((s) => s.is_active && s.last_status === 'ok' && !s.is_slow);

  if (loading) return <div style={{ padding: '60px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>Loading alerts...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>Alerts & Monitoring</h2>
        <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Auto-refreshes every 15s | CST timezone</span>
      </div>

      {error && <div className="error-message" style={{ marginBottom: '16px' }}>{error}</div>}

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
          <div className="stat-value">{warningSites.length}</div>
          <div className="stat-label">Warnings / Slow</div>
        </div>
        <div className="stat-card ok">
          <div className="stat-value">{healthySites.length}</div>
          <div className="stat-label">Healthy</div>
        </div>
        <div className="stat-card info">
          <div className="stat-value">{history.length}</div>
          <div className="stat-label">Total Events</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {[
          { key: 'overview', label: 'Overview' },
          { key: 'active', label: `Active (${activeAlerts.length})` },
          { key: 'history', label: `History (${history.length})` },
          { key: 'sites', label: `All Sites (${sites.length})` },
        ].map((t) => (
          <button key={t.key} className={`btn ${tab === t.key ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* OVERVIEW TAB */}
      {tab === 'overview' && (
        <>
          {/* Current Issues */}
          {(criticalSites.length > 0 || warningSites.length > 0) ? (
            <div className="card" style={{ marginBottom: '20px' }}>
              <div className="card-header"><h3>Current Issues</h3></div>
              <div className="table-container">
                <table>
                  <thead><tr><th>Site</th><th>Status</th><th>Response</th><th>Last Check (CST)</th><th>Issue</th></tr></thead>
                  <tbody>
                    {[...criticalSites, ...warningSites].map((s) => (
                      <tr key={s.id} style={{ background: s.last_status === 'critical' ? 'rgba(229,62,62,0.04)' : 'rgba(221,107,32,0.04)' }}>
                        <td><Link to={`/sites/${s.id}`} style={{ fontWeight: 500 }}>{s.name}</Link></td>
                        <td><span className={`badge badge-${s.last_status || 'warning'}`}>{s.last_status || 'slow'}</span></td>
                        <td style={{ fontVariantNumeric: 'tabular-nums' }}>{s.last_response_time_ms ? `${Math.round(s.last_response_time_ms)}ms` : '-'}</td>
                        <td style={{ fontSize: '12px' }}>{formatCST(s.last_checked_at)}</td>
                        <td title={s.last_error || (s.is_slow ? `Slow (>${s.slow_threshold_ms}ms)` : 'Down')} style={{ fontSize: '12px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>
                          {s.last_error || (s.is_slow ? `Slow (>${s.slow_threshold_ms}ms)` : 'Down')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="card" style={{ marginBottom: '20px', textAlign: 'center', padding: '40px' }}>
              <div style={{ fontSize: '32px', marginBottom: '8px', color: 'var(--color-status-ok)' }}>&#10003;</div>
              <div style={{ fontWeight: 600, fontSize: '16px', marginBottom: '4px' }}>All Systems Operational</div>
              <div style={{ color: 'var(--color-text-secondary)' }}>All {sites.length} monitored sites are running normally.</div>
            </div>
          )}

          {/* Recent Alert Activity */}
          <div className="card">
            <div className="card-header"><h3>Recent Alert Activity</h3></div>
            {history.length > 0 ? (
              <div className="table-container">
                <table>
                  <thead><tr><th>Site</th><th>Severity</th><th>Message</th><th>When (CST)</th><th>Duration</th><th>Status</th><th>Action</th></tr></thead>
                  <tbody>
                    {history.filter((a) => !a.false_positive).slice(0, 15).map((a) => (
                      <tr key={a.id} style={{ background: !a.resolved ? 'rgba(229,62,62,0.04)' : undefined }}>
                        <td><Link to={`/sites/${a.site_id}`} style={{ fontWeight: 500 }}>{a.site_name || `Site #${a.site_id}`}</Link></td>
                        <td><span className={`badge badge-${a.alert_type || 'critical'}`}>{a.alert_type || 'critical'}</span></td>
                        <td title={a.message || ''} style={{ maxWidth: '250px', fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>{a.message || '-'}</td>
                        <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>{formatCST(a.created_at)}</td>
                        <td style={{ fontSize: '12px' }}>{formatDuration(a.created_at, a.resolved_at)}</td>
                        <td>{a.resolved ? <span className="badge badge-ok">Resolved</span> : <span className="badge badge-critical" style={{ animation: 'pulse 2s infinite' }}>Active</span>}</td>
                        <td style={{ display: 'flex', gap: '4px' }}>
                          {!a.resolved && <button onClick={() => handleResolve(a.id)} className="btn btn-primary" style={{ padding: '3px 8px', fontSize: '10px' }}>Resolve</button>}
                          {isAdmin && <button onClick={() => handleFalsePositive(a.id)} className="btn btn-outline" style={{ padding: '3px 8px', fontSize: '10px' }}>False +</button>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-secondary)' }}>No alert activity recorded yet. Alerts will appear here when sites go down or experience issues.</p>
            )}
          </div>
        </>
      )}

      {/* ACTIVE TAB */}
      {tab === 'active' && (
        <div className="card">
          <div className="card-header"><h3>Active Alerts</h3></div>
          <div className="table-container">
            <table>
              <thead><tr><th>Site</th><th>Severity</th><th>Message</th><th>Since (CST)</th><th>Duration</th><th>Action</th></tr></thead>
              <tbody>
                {activeAlerts.map((a) => (
                  <tr key={a.id} style={{ background: 'rgba(229,62,62,0.04)' }}>
                    <td>
                      <Link to={`/sites/${a.site_id}`} style={{ fontWeight: 500 }}>{a.site_name || `Site #${a.site_id}`}</Link>
                      {a.site_url && <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{a.site_url}</div>}
                    </td>
                    <td><span className={`badge badge-${a.alert_type || 'critical'}`}>{a.alert_type || 'critical'}</span></td>
                    <td style={{ maxWidth: '300px', fontSize: '13px' }}>{a.message || '-'}</td>
                    <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>{formatCST(a.created_at)}</td>
                    <td style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-status-critical)' }}>{formatDuration(a.created_at, null)}</td>
                    <td style={{ display: 'flex', gap: '6px' }}>
                      <button onClick={() => handleResolve(a.id)} className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '11px' }}>Resolve</button>
                      {isAdmin && !a.false_positive && <button onClick={() => handleFalsePositive(a.id)} className="btn btn-outline" style={{ padding: '4px 10px', fontSize: '11px' }}>False +</button>}
                    </td>
                  </tr>
                ))}
                {activeAlerts.length === 0 && (
                  <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>
                    <span style={{ color: 'var(--color-status-ok)', fontSize: '20px' }}>&#10003;</span><br/>No active alerts
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* HISTORY TAB */}
      {tab === 'history' && (
        <div className="card">
          <div className="card-header"><h3>Full Alert History</h3></div>
          <div className="table-container">
            <table>
              <thead><tr><th>Site</th><th>Severity</th><th>Message</th><th>Triggered (CST)</th><th>Resolved (CST)</th><th>Duration</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {history.filter((a) => !a.false_positive).map((a) => (
                  <tr key={a.id}>
                    <td><Link to={`/sites/${a.site_id}`} style={{ fontWeight: 500 }}>{a.site_name || `Site #${a.site_id}`}</Link></td>
                    <td><span className={`badge badge-${a.alert_type || 'critical'}`}>{a.alert_type || 'critical'}</span></td>
                    <td title={a.message || ''} style={{ maxWidth: '250px', fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>{a.message || '-'}</td>
                    <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>{formatCST(a.created_at)}</td>
                    <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>{a.resolved ? formatCST(a.resolved_at) : <span style={{ color: 'var(--color-status-critical)', fontWeight: 600 }}>ONGOING</span>}</td>
                    <td style={{ fontSize: '12px' }}>{formatDuration(a.created_at, a.resolved_at)}</td>
                    <td>{a.resolved ? <span className="badge badge-ok">Resolved</span> : <span className="badge badge-critical">Active</span>}</td>
                    <td>{isAdmin && !a.false_positive && <button onClick={() => handleFalsePositive(a.id)} className="btn btn-outline" style={{ padding: '3px 8px', fontSize: '10px' }}>False +</button>}</td>
                  </tr>
                ))}
                {history.length === 0 && (
                  <tr><td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>No alert history yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SITES TAB */}
      {tab === 'sites' && (
        <div className="card">
          <div className="card-header"><h3>All Monitored Sites</h3></div>
          <div className="table-container">
            <table>
              <thead><tr><th>Site</th><th>URL</th><th>Status</th><th>Response</th><th>Last Check (CST)</th><th>Enabled</th></tr></thead>
              <tbody>
                {sites.map((s) => (
                  <tr key={s.id}>
                    <td><Link to={`/sites/${s.id}`} style={{ fontWeight: 500 }}>{s.name}</Link></td>
                    <td style={{ fontSize: '12px', color: 'var(--color-text-secondary)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.url}</td>
                    <td>
                      {s.last_status ? <span className={`badge badge-${s.last_status}`}>{s.last_status}</span> : <span style={{ color: 'var(--color-text-secondary)' }}>--</span>}
                      {s.is_slow && <span className="badge badge-warning" style={{ marginLeft: '4px', fontSize: '10px' }}>SLOW</span>}
                    </td>
                    <td style={{ fontVariantNumeric: 'tabular-nums', fontSize: '12px' }}>{s.last_response_time_ms ? `${Math.round(s.last_response_time_ms)}ms` : '-'}</td>
                    <td style={{ fontSize: '12px' }}>{formatCST(s.last_checked_at)}</td>
                    <td>{s.is_active ? <span className="badge badge-ok">Enabled</span> : <span className="badge badge-critical">Disabled</span>}</td>
                  </tr>
                ))}
                {sites.length === 0 && (
                  <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>No sites configured</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
