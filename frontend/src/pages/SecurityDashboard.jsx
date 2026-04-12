import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSecurityDashboard, runSecurityScan } from '../services/api';
import { formatCST } from '../services/time';

const GRADE_COLORS = { A: '#10b981', B: '#3b82f6', C: '#f59e0b', D: '#f97316', F: '#ef4444' };

export default function SecurityDashboard() {
  const [data, setData] = useState(null);
  const [scanning, setScanning] = useState(null);

  const load = () => getSecurityDashboard().then(r => setData(r.data)).catch(e => console.error(e));
  useEffect(() => { load(); }, []);

  const handleScan = async (siteId) => {
    setScanning(siteId);
    try { await runSecurityScan(siteId); load(); } catch (e) { console.error(e); }
    finally { setScanning(null); }
  };

  if (!data) return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>Security Dashboard</h2>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        <div className="stat-card info"><div className="stat-value">{data.total_sites}</div><div className="stat-label">Total Sites</div></div>
        <div className="stat-card ok"><div className="stat-value">{data.scanned_sites}</div><div className="stat-label">Scanned</div></div>
        <div className="stat-card info"><div className="stat-value">{data.avg_score}/100</div><div className="stat-label">Avg Score</div></div>
        <div className="stat-card critical"><div className="stat-value">{data.total_critical}</div><div className="stat-label">Critical Findings</div></div>
        <div className="stat-card warning"><div className="stat-value">{data.total_high}</div><div className="stat-label">High Findings</div></div>
      </div>

      <div className="card">
        <div className="card-header"><h3>Site Security Scores</h3></div>
        <div className="table-container">
          <table>
            <thead>
              <tr><th>Site</th><th>Grade</th><th>Score</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Last Scan</th><th>Action</th></tr>
            </thead>
            <tbody>
              {data.sites.map(s => (
                <tr key={s.site_id}>
                  <td><Link to={`/sites/${s.site_id}`} style={{ fontWeight: 500 }}>{s.site_name}</Link><div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{s.site_url}</div></td>
                  <td>{s.grade ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32, borderRadius: '50%', background: GRADE_COLORS[s.grade[0]] || '#94a3b8', color: 'white', fontWeight: 700, fontSize: '14px' }}>{s.grade}</span>
                  ) : <span style={{ color: 'var(--color-text-muted)' }}>—</span>}</td>
                  <td style={{ fontWeight: 600, fontSize: '16px', color: s.score >= 80 ? 'var(--color-status-ok)' : s.score >= 60 ? 'var(--color-status-warning)' : s.score != null ? 'var(--color-status-critical)' : undefined }}>{s.score != null ? s.score : '—'}</td>
                  <td style={{ color: s.critical > 0 ? 'var(--color-status-critical)' : undefined, fontWeight: s.critical > 0 ? 700 : undefined }}>{s.critical}</td>
                  <td style={{ color: s.high > 0 ? 'var(--color-status-warning)' : undefined }}>{s.high}</td>
                  <td>{s.medium}</td>
                  <td>{s.low}</td>
                  <td style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>{s.scanned_at ? formatCST(s.scanned_at) : 'Never'}</td>
                  <td>
                    <button onClick={() => handleScan(s.site_id)} disabled={scanning === s.site_id} className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '11px' }}>
                      {scanning === s.site_id ? 'Scanning...' : 'Scan Now'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
