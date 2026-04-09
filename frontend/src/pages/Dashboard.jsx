import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { getDashboardStats, getAlerts, getSitesStatus } from '../services/api';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
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
  const [refreshIn, setRefreshIn] = useState(15);
  const refreshRef = useRef(null);

  const loadData = () => {
    getDashboardStats().then((r) => setStats(r.data)).catch(() => {});
    getSitesStatus().then((r) => setSitesStatus(r.data)).catch(() => {});
    getAlerts().then((r) => setAlerts(r.data)).catch(() => {});
    setRefreshIn(15);
  };

  // Initial load + auto-refresh every 15 seconds
  useEffect(() => {
    loadData();
    refreshRef.current = setInterval(loadData, 15000);
    return () => clearInterval(refreshRef.current);
  }, []);

  // Countdown ticker for the refresh indicator
  useEffect(() => {
    const id = setInterval(() => setRefreshIn((p) => Math.max(0, p - 1)), 1000);
    return () => clearInterval(id);
  }, []);

  const pieData = stats ? [
    { name: 'Up', value: stats.sites_up, color: PIE_COLORS.up },
    { name: 'Down', value: stats.sites_down, color: PIE_COLORS.down },
    { name: 'Warning', value: stats.sites_warning, color: PIE_COLORS.warning },
    ...(stats.total_sites - stats.sites_up - stats.sites_down - stats.sites_warning > 0
      ? [{ name: 'No Data', value: stats.total_sites - stats.sites_up - stats.sites_down - stats.sites_warning, color: PIE_COLORS.unmonitored }]
      : []),
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
          <div className="stat-value">{stats?.sites_warning ?? '-'}</div>
          <div className="stat-label">Warnings</div>
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
            <h3>Active Alerts</h3>
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
                    <td>Site #{alert.site_id}</td>
                    <td><span className={`badge badge-${alert.alert_type}`}>{alert.alert_type}</span></td>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{alert.message}</td>
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
                    {site.last_response_time_ms != null ? `${Math.round(site.last_response_time_ms)}ms` : '--'}
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
