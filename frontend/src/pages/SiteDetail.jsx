import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSite, getResults } from '../services/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

export default function SiteDetail() {
  const { id } = useParams();
  const [site, setSite] = useState(null);
  const [results, setResults] = useState([]);

  useEffect(() => {
    getSite(id).then((r) => setSite(r.data)).catch(() => {});
    getResults(id, 100).then((r) => setResults(r.data.reverse())).catch(() => {});
  }, [id]);

  if (!site) return <div>Loading...</div>;

  const chartData = results.map((r) => ({
    time: new Date(r.checked_at).toLocaleTimeString(),
    response_time: r.response_time_ms,
    status: r.status,
  }));

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/sites" style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>&larr; Back to Sites</Link>
          <h2 style={{ marginTop: '4px' }}>{site.name}</h2>
        </div>
        <span className={`badge badge-${site.is_active ? 'ok' : 'warning'}`} style={{ fontSize: '14px', padding: '6px 16px' }}>
          {site.is_active ? 'Active' : 'Paused'}
        </span>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <div className="stat-card info">
          <div className="stat-value" style={{ fontSize: '14px', wordBreak: 'break-all' }}>{site.url}</div>
          <div className="stat-label">URL</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: '20px' }}>{site.check_type}</div>
          <div className="stat-label">Check Type</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{site.check_interval_minutes}<span style={{ fontSize: '14px' }}>min</span></div>
          <div className="stat-label">Interval</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ fontSize: '14px' }}>{site.notification_channel}</div>
          <div className="stat-label">Notifications</div>
        </div>
      </div>

      {site.pages && site.pages.length > 0 && (
        <div className="card">
          <div className="card-header"><h3>Monitored Pages</h3></div>
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Page</th><th>URL</th><th>Expected Element</th><th>Expected Text</th></tr>
              </thead>
              <tbody>
                {site.pages.map((p) => (
                  <tr key={p.id}>
                    <td>{p.page_name || '-'}</td>
                    <td style={{ color: 'var(--color-text-secondary)' }}>{p.page_url}</td>
                    <td><code>{p.expected_element || '-'}</code></td>
                    <td>{p.expected_text || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header"><h3>Response Time</h3></div>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="time" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} unit="ms" />
              <Tooltip />
              <Line type="monotone" dataKey="response_time" stroke="var(--color-primary)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: '40px' }}>No monitoring data yet</p>
        )}
      </div>

      <div className="card">
        <div className="card-header"><h3>Recent Results</h3></div>
        <div className="table-container">
          <table>
            <thead>
              <tr><th>Time</th><th>Status</th><th>Response Time</th><th>Status Code</th><th>Error</th></tr>
            </thead>
            <tbody>
              {results.slice(-20).reverse().map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.checked_at).toLocaleString()}</td>
                  <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
                  <td>{r.response_time_ms?.toFixed(0)}ms</td>
                  <td>{r.status_code || '-'}</td>
                  <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.error_message || '-'}</td>
                </tr>
              ))}
              {results.length === 0 && (
                <tr><td colSpan="5" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>No results yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
