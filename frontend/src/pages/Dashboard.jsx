import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getDashboardStats, getSites, getAlerts } from '../services/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [sites, setSites] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    getDashboardStats().then((r) => setStats(r.data)).catch(() => {});
    getSites().then((r) => setSites(r.data)).catch(() => {});
    getAlerts().then((r) => setAlerts(r.data)).catch(() => {});
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
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
        <div className="card">
          <div className="card-header">
            <h3>Monitored Sites</h3>
            <Link to="/sites" className="btn btn-outline" style={{ fontSize: '13px', padding: '6px 14px' }}>View All</Link>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sites.slice(0, 5).map((site) => (
                  <tr key={site.id}>
                    <td><Link to={`/sites/${site.id}`}>{site.name}</Link></td>
                    <td>{site.check_type}</td>
                    <td><span className={`badge badge-${site.is_active ? 'ok' : 'warning'}`}>{site.is_active ? 'Active' : 'Paused'}</span></td>
                  </tr>
                ))}
                {sites.length === 0 && (
                  <tr><td colSpan="3" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>No sites configured</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Active Alerts</h3>
            <Link to="/alerts" className="btn btn-outline" style={{ fontSize: '13px', padding: '6px 14px' }}>View All</Link>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Site</th>
                  <th>Type</th>
                  <th>Message</th>
                </tr>
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
    </div>
  );
}
