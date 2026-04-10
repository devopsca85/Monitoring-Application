import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { getDashboardStats, getAlerts, getSitesStatus, getAlertHistory, getSlownessAnalysis, deleteAlertHistory } from '../services/api';
import { formatCST, formatCSTShort, formatCSTHour } from '../services/time';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';

const PIE_COLORS = {
  up: '#38a169',
  down: '#e53e3e',
  warning: '#dd6b20',
  unmonitored: '#a0aec0',
};

const RADIAN = Math.PI / 180;

function renderPieLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent === 0) return null;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={13} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

function renderLegend(props) {
  const { payload } = props;
  return (
    <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', marginTop: '8px' }}>
      {payload.map((entry) => (
        <div key={entry.value} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: entry.color, display: 'inline-block' }} />
          {entry.value}: <strong>{entry.payload.value}</strong>
        </div>
      ))}
    </div>
  );
}

function formatCountdown(seconds) {
  if (seconds <= 0) return 'Now';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function NextCheckTimer({ lastCheckedAt, intervalMinutes, isActive }) {
  const [remaining, setRemaining] = useState(null);

  useEffect(() => {
    if (!isActive || !lastCheckedAt) {
      setRemaining(null);
      return;
    }
    const calc = () => {
      const last = new Date(lastCheckedAt).getTime();
      const next = last + intervalMinutes * 60 * 1000;
      const diff = Math.max(0, Math.round((next - Date.now()) / 1000));
      setRemaining(diff);
    };
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, [lastCheckedAt, intervalMinutes, isActive]);

  if (!isActive) return <span style={{ color: 'var(--color-text-secondary)', fontSize: '12px' }}>--</span>;
  if (remaining === null) return <span style={{ color: 'var(--color-text-secondary)', fontSize: '12px' }}>Pending</span>;

  const isOverdue = remaining === 0;
  return (
    <span style={{
      fontSize: '12px',
      fontWeight: 600,
      fontVariantNumeric: 'tabular-nums',
      color: isOverdue ? 'var(--color-status-warning)' : 'var(--color-primary)',
    }}>
      {isOverdue ? 'Running...' : formatCountdown(remaining)}
    </span>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [sitesStatus, setSitesStatus] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [alertHistory, setAlertHistory] = useState([]);
  const [slowAnalysis, setSlowAnalysis] = useState([]);
  const [refreshIn, setRefreshIn] = useState(15);
  const nextRefreshAt = useRef(Date.now() + 15000);

  const loadData = () => {
    Promise.all([
      getDashboardStats().then((r) => setStats(r.data)).catch((e) => console.error('Dashboard stats error:', e)),
      getSitesStatus().then((r) => setSitesStatus(r.data)).catch((e) => console.error('Sites status error:', e)),
      getAlerts().then((r) => { setAlerts(r.data || []); }).catch((e) => { console.error('Alerts error:', e); setAlerts([]); }),
      getAlertHistory(30).then((r) => setAlertHistory(r.data || [])).catch((e) => { console.error('Alert history error:', e); setAlertHistory([]); }),
      getSlownessAnalysis().then((r) => setSlowAnalysis(r.data || [])).catch(() => setSlowAnalysis([])),
    ]);
    nextRefreshAt.current = Date.now() + 15000;
    setRefreshIn(15);
  };

  // Single 1-second tick that handles both countdown and data refresh
  useEffect(() => {
    loadData();
    const id = setInterval(() => {
      const remaining = Math.max(0, Math.round((nextRefreshAt.current - Date.now()) / 1000));
      setRefreshIn(remaining);
      if (remaining <= 0) {
        loadData();
      }
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // Compute live warning count from sitesStatus (includes slow sites)
  const liveWarnings = sitesStatus.length > 0
    ? sitesStatus.filter((s) => s.last_status === 'warning' || s.is_slow).length
    : (stats?.sites_warning || 0);
  const liveDown = stats?.sites_down || 0;
  const liveUp = stats ? Math.max(0, stats.sites_up - (liveWarnings - (stats.sites_warning || 0))) : 0;

  const pieData = stats ? [
    { name: 'Up', value: Math.max(0, (stats.total_sites || 0) - liveDown - liveWarnings), color: PIE_COLORS.up },
    { name: 'Down', value: liveDown, color: PIE_COLORS.down },
    { name: 'Warning/Slow', value: liveWarnings, color: PIE_COLORS.warning },
  ].filter((d) => d.value > 0) : [];

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
            Auto-refresh in {refreshIn}s
          </span>
          <button onClick={loadData} className="btn btn-outline" style={{ padding: '5px 14px', fontSize: '12px' }}>
            Refresh Now
          </button>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card info">
          <div className="stat-value">{stats?.total_sites ?? '-'}</div>
          <div className="stat-label">Total Sites</div>
        </div>
        <div className="stat-card ok">
          <div className="stat-value">{stats?.sites_up ?? '-'}</div>
          <div className="stat-label">Sites Up</div>
        </div>
        <div className="stat-card critical">
          <div className="stat-value">{stats?.sites_down ?? '-'}</div>
          <div className="stat-label">Sites Down</div>
        </div>
        <div className="stat-card warning">
          <div className="stat-value">
            {sitesStatus.length > 0
              ? sitesStatus.filter((s) => s.last_status === 'warning' || s.is_slow).length
              : (stats?.sites_warning ?? '-')}
          </div>
          <div className="stat-label">Warnings / Slow</div>
        </div>
        <div className="stat-card info">
          <div className="stat-value">{stats?.avg_response_time ?? '-'}<span style={{ fontSize: '16px' }}>ms</span></div>
          <div className="stat-label">Avg Response Time</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Pie Chart */}
        <div className="card">
          <div className="card-header"><h3>Site Status Overview</h3></div>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData} cx="50%" cy="50%"
                  innerRadius={60} outerRadius={110}
                  paddingAngle={3} dataKey="value"
                  labelLine={false} label={renderPieLabel}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} stroke="none" />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => {
                  const total = pieData.reduce((s, d) => s + d.value, 0);
                  const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                  return [`${value} sites (${pct}%)`, name];
                }} />
                <Legend content={renderLegend} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: '40px' }}>
              {stats ? 'No sites configured' : 'Loading...'}
            </p>
          )}
        </div>

        {/* Active Alerts */}
        <div className="card">
          <div className="card-header">
            <h3>Active Alerts ({alerts.length})</h3>
            <Link to="/alerts" className="btn btn-outline" style={{ fontSize: '13px', padding: '6px 14px' }}>View All</Link>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Site</th><th>Type</th><th>Message</th></tr>
              </thead>
              <tbody>
                {alerts.slice(0, 5).map((alert) => (
                  <tr key={alert.id}>
                    <td>{alert.site_name || `Site #${alert.site_id}`}</td>
                    <td><span className={`badge badge-${alert.alert_type}`}>{alert.alert_type}</span></td>
                    <td title={alert.message || ''} style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>{alert.message}</td>
                  </tr>
                ))}
                {alerts.length === 0 && (
                  <tr><td colSpan="3" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>No active alerts</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Alert History — with site names and CST times */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <h3>Alert History</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Times shown in CST</span>
            {alertHistory.length > 0 && (
              <button onClick={async () => {
                if (!confirm('Delete all resolved alert history? Active alerts will not be affected.')) return;
                try {
                  await deleteAlertHistory();
                  loadData();
                } catch (e) { console.error('Delete history failed:', e); }
              }} className="btn btn-danger" style={{ padding: '4px 12px', fontSize: '12px' }}>
                Clear History
              </button>
            )}
          </div>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th>Severity</th>
                <th>Message</th>
                <th>Alert Sent (CST)</th>
                <th>Resolved (CST)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {alertHistory.map((a) => (
                <tr key={a.id}>
                  <td>
                    <Link to={`/sites/${a.site_id}`} style={{ fontWeight: 500 }}>{a.site_name}</Link>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{a.site_url}</div>
                  </td>
                  <td><span className={`badge badge-${a.alert_type}`}>{a.alert_type}</span></td>
                  <td title={a.message || ''} style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '13px', cursor: 'default' }}>{a.message || '-'}</td>
                  <td style={{ fontSize: '12px', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {formatCST(a.created_at)}
                  </td>
                  <td style={{ fontSize: '12px', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {a.resolved ? formatCST(a.resolved_at) : '-'}
                  </td>
                  <td>
                    {a.resolved ? (
                      <span className="badge badge-ok">Resolved</span>
                    ) : (
                      <span className="badge badge-critical">Active</span>
                    )}
                  </td>
                </tr>
              ))}
              {alertHistory.length === 0 && (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>No alerts sent yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Slowness Analysis — sites slow >60min in last 24h */}
      {slowAnalysis.length > 0 && (
        <div className="card" style={{ marginTop: '20px' }}>
          <div className="card-header">
            <h3>Slowness Analysis (Last 24h)</h3>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>Sites with slowness &gt;60 minutes | CST timezone</span>
          </div>

          {slowAnalysis.map((site) => (
            <div key={site.site_id} style={{ marginBottom: '24px', borderBottom: '1px solid var(--color-border)', paddingBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <Link to={`/sites/${site.site_id}`} style={{ fontWeight: 600, fontSize: '15px' }}>{site.site_name}</Link>
                <span className="badge badge-warning">
                  {site.total_slow_minutes} min slow (threshold: {site.threshold_ms}ms)
                </span>
              </div>

              {/* Hourly response time bar chart */}
              {site.hourly_data && site.hourly_data.length > 0 && (
                <div style={{ marginBottom: '12px' }}>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={site.hourly_data.map((d) => ({
                      ...d,
                      hour_cst: formatCSTHour(d.hour + ':00Z'),
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                      <XAxis dataKey="hour_cst" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" height={50} />
                      <YAxis tick={{ fontSize: 10 }} unit="ms" />
                      <Tooltip
                        formatter={(v, name) => [`${v}ms`, name === 'avg_ms' ? 'Avg Response' : 'Max Response']}
                        labelFormatter={(l) => `Time: ${l}`}
                      />
                      <Bar dataKey="avg_ms" fill="#dd6b20" radius={[3,3,0,0]} name="Avg Response" />
                      <Bar dataKey="max_ms" fill="#e53e3e" radius={[3,3,0,0]} name="Max Response" opacity={0.4} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Slow windows table */}
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Slow Period Start (CST)</th>
                      <th>Slow Period End (CST)</th>
                      <th>Duration</th>
                      <th>Checks</th>
                      <th>Avg Response</th>
                      <th>Max Response</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {site.slow_windows.map((w, i) => (
                      <tr key={i} style={{ background: w.ongoing ? 'rgba(229,62,62,0.04)' : undefined }}>
                        <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>
                          {formatCSTShort(w.start)}
                        </td>
                        <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>
                          {formatCSTShort(w.end)}
                        </td>
                        <td style={{ fontWeight: 600, color: 'var(--color-status-warning)' }}>{w.duration_minutes} min</td>
                        <td>{w.check_count}</td>
                        <td style={{ fontVariantNumeric: 'tabular-nums' }}>{w.avg_response_ms}ms</td>
                        <td style={{ fontVariantNumeric: 'tabular-nums', color: 'var(--color-status-critical)' }}>{w.max_response_ms}ms</td>
                        <td>{w.ongoing ? <span className="badge badge-critical" style={{ animation: 'pulse 2s infinite' }}>Ongoing</span> : <span className="badge badge-warning">Ended</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Monitored Sites with live countdown */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <h3>Monitored Sites</h3>
          <Link to="/sites" className="btn btn-outline" style={{ fontSize: '13px', padding: '6px 14px' }}>View All</Link>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>URL</th>
                <th>Type</th>
                <th>Status</th>
                <th>Last Check</th>
                <th>Response</th>
                <th>Next Check</th>
              </tr>
            </thead>
            <tbody>
              {sitesStatus.map((site) => (
                <tr key={site.id}>
                  <td><Link to={`/sites/${site.id}`} style={{ fontWeight: 500 }}>{site.name}</Link></td>
                  <td style={{ color: 'var(--color-text-secondary)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{site.url}</td>
                  <td><span className="badge badge-ok" style={{ fontSize: '11px' }}>{site.check_type}</span></td>
                  <td>
                    {site.is_active ? (
                      <span className="badge badge-ok" style={{ gap: '4px' }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#38a169', display: 'inline-block' }} />
                        Enabled
                      </span>
                    ) : (
                      <span className="badge badge-critical" style={{ gap: '4px' }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#e53e3e', display: 'inline-block' }} />
                        Disabled
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: '12px' }}>
                    {site.last_status ? (
                      <span className={`badge badge-${site.last_status}`} style={{ fontSize: '11px' }}>{site.last_status}</span>
                    ) : (
                      <span style={{ color: 'var(--color-text-secondary)' }}>--</span>
                    )}
                  </td>
                  <td style={{ fontSize: '12px', fontVariantNumeric: 'tabular-nums' }}>
                    {site.last_response_time_ms != null ? (
                      <span style={{
                        color: site.is_slow ? 'var(--color-status-warning)' : undefined,
                        fontWeight: site.is_slow ? 700 : 400,
                      }}>
                        {Math.round(site.last_response_time_ms)}ms
                        {site.is_slow && ' ⚠ SLOW'}
                      </span>
                    ) : '--'}
                  </td>
                  <td>
                    <NextCheckTimer
                      lastCheckedAt={site.last_checked_at}
                      intervalMinutes={site.check_interval_minutes}
                      isActive={site.is_active}
                    />
                  </td>
                </tr>
              ))}
              {sitesStatus.length === 0 && (
                <tr><td colSpan="7" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>No sites configured</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
