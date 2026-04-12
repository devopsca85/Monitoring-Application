import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSecurityDashboard, runSecurityScan, getLatestScan, downloadSecurityReport, sendSecurityReport } from '../services/api';
import { formatCST } from '../services/time';

const GRADE_COLORS = { A: '#10b981', B: '#3b82f6', C: '#f59e0b', D: '#f97316', F: '#ef4444' };
const SEV_COLORS = { critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#3b82f6', info: '#94a3b8' };

export default function SecurityDashboard() {
  const [data, setData] = useState(null);
  const [scanning, setScanning] = useState(null);
  const [selectedSite, setSelectedSite] = useState(null);
  const [scanDetail, setScanDetail] = useState(null);

  const load = () => getSecurityDashboard().then(r => setData(r.data)).catch(e => console.error(e));
  useEffect(() => { load(); }, []);

  const handleScan = async (siteId) => {
    setScanning(siteId);
    try { await runSecurityScan(siteId); load(); } catch (e) { console.error(e); }
    finally { setScanning(null); }
  };

  const viewDetails = async (siteId, siteName) => {
    setSelectedSite(siteName);
    try { const r = await getLatestScan(siteId); setScanDetail(r.data); } catch { setScanDetail(null); }
  };

  if (!data) return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>Security Dashboard</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={async () => {
            try {
              const res = await downloadSecurityReport();
              const url = window.URL.createObjectURL(new Blob([res.data]));
              const a = document.createElement('a'); a.href = url;
              a.download = `security-report-${new Date().toISOString().split('T')[0]}.pdf`;
              a.click(); window.URL.revokeObjectURL(url);
            } catch (e) { console.error('PDF download failed:', e); }
          }} className="btn btn-outline" style={{ fontSize: '12px' }}>Download PDF</button>
          <button onClick={async () => {
            try { await sendSecurityReport(); alert('Security report sent to all admins'); } catch (e) { console.error(e); }
          }} className="btn btn-outline" style={{ fontSize: '12px' }}>Email Report</button>
        </div>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
        <div className="stat-card info"><div className="stat-value">{data.total_sites}</div><div className="stat-label">Total Sites</div></div>
        <div className="stat-card ok"><div className="stat-value">{data.scanned_sites}</div><div className="stat-label">Scanned</div></div>
        <div className="stat-card info"><div className="stat-value">{data.avg_score}/100</div><div className="stat-label">Avg Score</div></div>
        <div className="stat-card critical"><div className="stat-value">{data.total_critical}</div><div className="stat-label">Critical</div></div>
        <div className="stat-card warning"><div className="stat-value">{data.total_high}</div><div className="stat-label">High</div></div>
      </div>

      {/* Sites Table */}
      <div className="card">
        <div className="card-header"><h3>Site Security Scores</h3></div>
        <div className="table-container">
          <table>
            <thead><tr><th>Site</th><th>Grade</th><th>Score</th><th>Critical</th><th>High</th><th>Medium</th><th>Low</th><th>Last Scan</th><th>Actions</th></tr></thead>
            <tbody>
              {data.sites.map(s => (
                <tr key={s.site_id}>
                  <td><Link to={`/sites/${s.site_id}`} style={{ fontWeight: 500 }}>{s.site_name}</Link><div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{s.site_url}</div></td>
                  <td>{s.grade ? <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32, borderRadius: '50%', background: GRADE_COLORS[s.grade[0]] || '#94a3b8', color: 'white', fontWeight: 700, fontSize: '14px' }}>{s.grade}</span> : '—'}</td>
                  <td style={{ fontWeight: 600, fontSize: '16px', color: s.score >= 80 ? 'var(--color-status-ok)' : s.score >= 60 ? 'var(--color-status-warning)' : s.score != null ? 'var(--color-status-critical)' : undefined }}>{s.score ?? '—'}</td>
                  <td style={{ color: s.critical > 0 ? 'var(--color-status-critical)' : undefined, fontWeight: s.critical > 0 ? 700 : undefined }}>{s.critical}</td>
                  <td style={{ color: s.high > 0 ? '#f97316' : undefined }}>{s.high}</td>
                  <td>{s.medium}</td>
                  <td>{s.low}</td>
                  <td style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>{s.scanned_at ? formatCST(s.scanned_at) : 'Never'}</td>
                  <td style={{ display: 'flex', gap: '4px' }}>
                    <button onClick={() => handleScan(s.site_id)} disabled={scanning === s.site_id} className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '11px' }}>{scanning === s.site_id ? 'Scanning...' : 'Scan'}</button>
                    {s.has_scan && <button onClick={() => viewDetails(s.site_id, s.site_name)} className="btn btn-outline" style={{ padding: '4px 10px', fontSize: '11px' }}>Details</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Scan Detail Panel */}
      {scanDetail && scanDetail.has_scan && (
        <div className="card">
          <div className="card-header">
            <h3>Scan Results: {selectedSite}</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 36, height: 36, borderRadius: '50%', background: GRADE_COLORS[scanDetail.grade?.[0]] || '#94a3b8', color: 'white', fontWeight: 700, fontSize: '16px' }}>{scanDetail.grade}</span>
              <span style={{ fontSize: '20px', fontWeight: 700 }}>{scanDetail.score}/100</span>
              <button onClick={() => { setScanDetail(null); setSelectedSite(null); }} className="btn btn-outline" style={{ padding: '4px 10px', fontSize: '11px' }}>Close</button>
            </div>
          </div>

          {/* Severity Summary */}
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            {[['critical', scanDetail.critical_count], ['high', scanDetail.high_count], ['medium', scanDetail.medium_count], ['low', scanDetail.low_count], ['info', scanDetail.info_count]].map(([sev, count]) => (
              <div key={sev} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', borderRadius: '8px', background: count > 0 ? `${SEV_COLORS[sev]}15` : 'var(--color-bg)', border: `1px solid ${count > 0 ? SEV_COLORS[sev] + '40' : 'var(--color-border-light)'}` }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: SEV_COLORS[sev] }} />
                <span style={{ fontSize: '12px', fontWeight: 600, textTransform: 'capitalize' }}>{sev}</span>
                <span style={{ fontSize: '14px', fontWeight: 700, color: count > 0 ? SEV_COLORS[sev] : 'var(--color-text-secondary)' }}>{count}</span>
              </div>
            ))}
          </div>

          {/* SSL Info */}
          {scanDetail.ssl_data && scanDetail.ssl_data.days_until_expiry != null && (
            <div style={{ background: scanDetail.ssl_data.days_until_expiry < 30 ? '#fef2f2' : '#ecfdf5', border: `1px solid ${scanDetail.ssl_data.days_until_expiry < 30 ? '#fecaca' : '#a7f3d0'}`, borderRadius: 'var(--radius)', padding: '10px 14px', marginBottom: '16px', fontSize: '12px' }}>
              <strong>SSL Certificate:</strong> Expires in {scanDetail.ssl_data.days_until_expiry} days
              {scanDetail.ssl_data.issuer && ` | Issuer: ${scanDetail.ssl_data.issuer.organizationName || scanDetail.ssl_data.issuer.commonName || 'Unknown'}`}
            </div>
          )}

          {/* Findings Table */}
          <div className="table-container">
            <table>
              <thead><tr><th>Severity</th><th>Category</th><th>Finding</th><th>Recommendation</th></tr></thead>
              <tbody>
                {(scanDetail.findings || []).map((f, i) => (
                  <tr key={i} style={{ background: f.severity === 'critical' ? '#fef2f220' : f.severity === 'high' ? '#fff7ed20' : undefined }}>
                    <td><span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700, background: `${SEV_COLORS[f.severity]}20`, color: SEV_COLORS[f.severity], textTransform: 'uppercase' }}>{f.severity}</span></td>
                    <td style={{ fontSize: '12px', fontWeight: 500 }}>{f.category}</td>
                    <td><div style={{ fontWeight: 500, fontSize: '12px' }}>{f.title}</div><div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{f.description}</div></td>
                    <td style={{ fontSize: '11px', color: 'var(--color-status-ok)' }}>{f.recommendation}</td>
                  </tr>
                ))}
                {(!scanDetail.findings || scanDetail.findings.length === 0) && <tr><td colSpan="4" style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-secondary)' }}>No findings — site is secure</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
