import { useState, useEffect, Fragment } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSite, getResults, triggerCheck } from '../services/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

function parseSubpageDetails(details) {
  if (!details) return [];
  try { return JSON.parse(details); } catch { return []; }
}

export default function SiteDetail() {
  const { id } = useParams();
  const [site, setSite] = useState(null);
  const [results, setResults] = useState([]);
  const [checking, setChecking] = useState(false);
  const [checkMsg, setCheckMsg] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);

  const loadData = () => {
    getSite(id).then((r) => setSite(r.data)).catch(() => {});
    getResults(id, 100).then((r) => setResults(r.data.reverse())).catch(() => {});
  };

  useEffect(() => { loadData(); }, [id]);

  const handleRunCheck = async () => {
    setChecking(true);
    setCheckMsg('');
    try {
      await triggerCheck(id);
      setCheckMsg('Check completed! Refreshing...');
      setTimeout(() => {
        loadData();
        setCheckMsg('');
      }, 1500);
    } catch (err) {
      setCheckMsg(err.response?.data?.detail || 'Check failed — is the monitoring engine running?');
    } finally {
      setChecking(false);
    }
  };

  if (!site) return <div>Loading...</div>;

  const chartData = results.map((r) => ({
    time: new Date(r.checked_at).toLocaleTimeString(),
    response_time: r.response_time_ms,
    status: r.status,
  }));

  // Get the latest result's subpage details for the summary card
  const latestResult = results.length > 0 ? results[results.length - 1] : null;
  const latestSubpages = latestResult ? parseSubpageDetails(latestResult.details) : [];

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/sites" style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>&larr; Back to Sites</Link>
          <h2 style={{ marginTop: '4px' }}>{site.name}</h2>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button onClick={handleRunCheck} disabled={checking} className="btn btn-primary" style={{ fontSize: '14px' }}>
            {checking ? 'Running...' : 'Run Check Now'}
          </button>
          <Link to={`/sites/${id}/edit`} className="btn btn-outline" style={{ fontSize: '14px' }}>Edit</Link>
          <span className={`badge badge-${site.is_active ? 'ok' : 'warning'}`} style={{ fontSize: '14px', padding: '6px 16px' }}>
            {site.is_active ? 'Active' : 'Paused'}
          </span>
        </div>
      </div>

      {checkMsg && (
        <div className="error-message" style={{ background: checkMsg.includes('completed') ? '#f0fff4' : undefined, color: checkMsg.includes('completed') ? 'var(--color-status-ok)' : undefined, marginBottom: '16px' }}>
          {checkMsg}
        </div>
      )}

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
          <div className="stat-value" style={{ fontSize: '14px' }}>{{ email: 'Email', teams: 'MS Teams', both: 'MS Teams & Email' }[site.notification_channel] || site.notification_channel}</div>
          <div className="stat-label">Notifications</div>
        </div>
      </div>

      {/* Subpage Status — latest results */}
      {latestSubpages.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3>Subpage Status (Latest Check)</h3>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              {latestResult ? new Date(latestResult.checked_at).toLocaleString() : ''}
            </span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: '40px' }}></th>
                  <th>Page</th>
                  <th>Status</th>
                  <th>Response Time</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {latestSubpages.map((sp, i) => (
                  <tr key={i}>
                    <td style={{ textAlign: 'center' }}>
                      {sp.status === 'ok' ? (
                        <span style={{ color: 'var(--color-status-ok)', fontSize: '16px' }}>&#10003;</span>
                      ) : sp.status === 'warning' ? (
                        <span style={{ color: 'var(--color-status-warning)', fontSize: '16px' }}>&#9888;</span>
                      ) : (
                        <span style={{ color: 'var(--color-status-critical)', fontSize: '16px' }}>&#10007;</span>
                      )}
                    </td>
                    <td style={{ fontWeight: 500 }}>{sp.page_name || sp.page_url || `Page ${i + 1}`}</td>
                    <td><span className={`badge badge-${sp.status || 'ok'}`}>{sp.status || 'ok'}</span></td>
                    <td style={{ fontVariantNumeric: 'tabular-nums' }}>
                      {sp.response_time_ms != null ? `${Math.round(sp.response_time_ms)}ms` : '-'}
                    </td>
                    <td style={{ color: sp.error ? 'var(--color-status-critical)' : 'var(--color-text-secondary)', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {sp.error || 'OK'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Configured subpages */}
      {site.pages && site.pages.length > 0 && (
        <div className="card">
          <div className="card-header"><h3>Configured Subpages</h3></div>
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

      {/* Recent Results with expandable subpage details */}
      <div className="card">
        <div className="card-header"><h3>Recent Results</h3></div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: '30px' }}></th>
                <th>Time</th>
                <th>Status</th>
                <th>Response Time</th>
                <th>Status Code</th>
                <th>Subpages</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {results.slice(-20).reverse().map((r) => {
                const subpages = parseSubpageDetails(r.details);
                const hasSubpages = subpages.length > 0;
                const isExpanded = expandedRow === r.id;
                const subOk = subpages.filter((s) => s.status === 'ok').length;
                const subFail = subpages.length - subOk;

                return (
                  <Fragment key={r.id}>
                    <tr
                      style={{ cursor: hasSubpages ? 'pointer' : 'default' }}
                      onClick={() => hasSubpages && setExpandedRow(isExpanded ? null : r.id)}
                    >
                      <td style={{ textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '12px' }}>
                        {hasSubpages && (isExpanded ? '▼' : '▶')}
                      </td>
                      <td>{new Date(r.checked_at).toLocaleString()}</td>
                      <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
                      <td style={{ fontVariantNumeric: 'tabular-nums' }}>{r.response_time_ms?.toFixed(0)}ms</td>
                      <td>{r.status_code || '-'}</td>
                      <td>
                        {hasSubpages ? (
                          <span style={{ fontSize: '12px' }}>
                            <span style={{ color: 'var(--color-status-ok)', fontWeight: 600 }}>{subOk}</span>
                            <span style={{ color: 'var(--color-text-secondary)' }}> / {subpages.length} </span>
                            {subFail > 0 && <span style={{ color: 'var(--color-status-critical)', fontWeight: 600 }}>({subFail} failed)</span>}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--color-text-secondary)' }}>-</span>
                        )}
                      </td>
                      <td style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {r.error_message || '-'}
                      </td>
                    </tr>
                    {isExpanded && subpages.map((sp, i) => (
                      <tr key={`${r.id}-sp-${i}`} style={{ background: 'var(--color-bg)' }}>
                        <td></td>
                        <td colSpan="2" style={{ paddingLeft: '24px' }}>
                          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>↳ </span>
                          <span style={{ fontWeight: 500, fontSize: '13px' }}>{sp.page_name || `Subpage ${i + 1}`}</span>
                        </td>
                        <td><span className={`badge badge-${sp.status || 'ok'}`} style={{ fontSize: '11px' }}>{sp.status || 'ok'}</span></td>
                        <td style={{ fontVariantNumeric: 'tabular-nums', fontSize: '13px' }}>
                          {sp.response_time_ms != null ? `${Math.round(sp.response_time_ms)}ms` : '-'}
                        </td>
                        <td colSpan="2" style={{ fontSize: '13px', color: sp.error ? 'var(--color-status-critical)' : 'var(--color-text-secondary)' }}>
                          {sp.error || 'OK'}
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                );
              })}
              {results.length === 0 && (
                <tr><td colSpan="7" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>No results yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

