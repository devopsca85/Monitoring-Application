import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getAlerts, resolveAlert } from '../services/api';

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
  const [alerts, setAlerts] = useState([]);
  const [filter, setFilter] = useState('active'); // active, resolved, all
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    if (filter === 'all') {
      // Fetch both and merge
      Promise.all([
        getAlerts(false).then((r) => r.data),
        getAlerts(true).then((r) => r.data),
      ]).then(([active, resolved]) => {
        const merged = [...active, ...resolved].sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at)
        );
        setAlerts(merged);
      }).catch(() => {}).finally(() => setLoading(false));
    } else {
      getAlerts(filter === 'resolved')
        .then((r) => setAlerts(r.data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  };

  useEffect(() => { load(); }, [filter]);

  // Auto-refresh every 15 seconds
  useEffect(() => {
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [filter]);

  const handleResolve = async (id) => {
    await resolveAlert(id);
    load();
  };

  const activeCount = alerts.filter((a) => !a.resolved).length;
  const resolvedCount = alerts.filter((a) => a.resolved).length;

  return (
    <div>
      <div className="page-header">
        <h2>Alert Log</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          {[
            { key: 'active', label: 'Active' },
            { key: 'resolved', label: 'Resolved' },
            { key: 'all', label: 'All' },
          ].map((f) => (
            <button
              key={f.key}
              className={`btn ${filter === f.key ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary stats */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: '20px' }}>
        <div className="stat-card critical">
          <div className="stat-value">{filter === 'resolved' ? 0 : activeCount}</div>
          <div className="stat-label">Active Alerts</div>
        </div>
        <div className="stat-card ok">
          <div className="stat-value">{filter === 'active' ? 0 : resolvedCount}</div>
          <div className="stat-label">Resolved</div>
        </div>
        <div className="stat-card info">
          <div className="stat-value">{alerts.length}</div>
          <div className="stat-label">Total Shown</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            Alert Timeline
          </h3>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>All times in CST</span>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th>Severity</th>
                <th>Message</th>
                <th>Alert Triggered (CST)</th>
                <th>Resolved At (CST)</th>
                <th>Duration</th>
                <th>Status</th>
                {filter !== 'resolved' && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id} style={{
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
                    <span className={`badge badge-${alert.alert_type}`}>
                      {alert.alert_type}
                    </span>
                  </td>
                  <td style={{ maxWidth: '300px', fontSize: '13px' }}>
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
                  {filter !== 'resolved' && (
                    <td>
                      {!alert.resolved && (
                        <button
                          onClick={() => handleResolve(alert.id)}
                          className="btn btn-primary"
                          style={{ padding: '4px 12px', fontSize: '12px' }}
                        >
                          Resolve
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
              {alerts.length === 0 && !loading && (
                <tr>
                  <td colSpan={filter !== 'resolved' ? 8 : 7} style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>
                    {filter === 'active' ? 'No active alerts' : filter === 'resolved' ? 'No resolved alerts' : 'No alerts recorded'}
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
