import { useState, useEffect, Fragment } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSite, getResults, triggerCheck, getIisDiagnostics } from '../services/api';
import { formatCST, formatCSTTime } from '../services/time';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

function parseDetails(details) {
  if (!details) return { subpages: [], perf: null };
  try {
    const parsed = JSON.parse(details);
    if (Array.isArray(parsed)) return { subpages: parsed, perf: null };
    return { subpages: parsed.subpages || [], perf: parsed.perf || null };
  } catch { return { subpages: [], perf: null }; }
}

export default function SiteDetail() {
  const { id } = useParams();
  const [site, setSite] = useState(null);
  const [results, setResults] = useState([]);
  const [checking, setChecking] = useState(false);
  const [checkMsg, setCheckMsg] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);
  const [iisDiag, setIisDiag] = useState(null);

  const loadData = () => {
    getSite(id).then((r) => setSite(r.data)).catch(() => {});
    getResults(id, 100).then((r) => setResults(r.data.reverse())).catch(() => {});
    getIisDiagnostics(id).then((r) => setIisDiag(r.data)).catch(() => {});
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
    time: formatCSTTime(r.checked_at),
    response_time: r.response_time_ms,
    status: r.status,
  }));

  // Get the latest result's subpage details for the summary card
  const latestResult = results.length > 0 ? results[results.length - 1] : null;
  const latestParsed = latestResult ? parseDetails(latestResult.details) : { subpages: [], perf: null };
  const latestSubpages = latestParsed.subpages;
  const latestPerf = latestParsed.perf;

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
              {latestResult ? formatCST(latestResult.checked_at) : ''}
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
                    <td title={sp.error || 'OK'} style={{ color: sp.error ? 'var(--color-status-critical)' : 'var(--color-text-secondary)', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>
                      {sp.error || 'OK'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Performance Metrics */}
      {latestPerf && (
        <div className="card">
          <div className="card-header">
            <h3>Performance Metrics (Latest Check)</h3>
            {latestPerf.region && <span className="badge badge-ok" style={{ fontSize: '11px' }}>{latestPerf.region}</span>}
          </div>

          {/* Bottleneck Analysis */}
          {latestPerf.bottleneck && (
            <div style={{
              background: latestPerf.bottleneck === 'backend/database' ? '#fff5f5' : '#fffaf0',
              border: `1px solid ${latestPerf.bottleneck === 'backend/database' ? '#feb2b2' : '#fbd38d'}`,
              borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: '16px',
              display: 'flex', alignItems: 'center', gap: '12px',
            }}>
              <span style={{ fontSize: '20px' }}>{latestPerf.bottleneck === 'backend/database' ? '\uD83D\uDDC4' : '\u26A1'}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: '13px', color: latestPerf.bottleneck === 'backend/database' ? 'var(--color-status-critical)' : 'var(--color-status-warning)' }}>
                  Bottleneck: {latestPerf.bottleneck === 'backend/database' ? 'Backend / Database' : 'Frontend / Rendering'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{latestPerf.bottleneck_detail}</div>
              </div>
            </div>
          )}

          {/* DB Latency Note */}
          {latestPerf.db_latency_note && (
            <div style={{
              background: '#fff5f5', border: '1px solid #feb2b2',
              borderRadius: 'var(--radius)', padding: '12px 16px', marginBottom: '16px',
              display: 'flex', alignItems: 'center', gap: '12px',
            }}>
              <span style={{ fontSize: '20px' }}>\uD83D\uDDC4</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-status-critical)' }}>
                  Database Latency Detected {latestPerf.db_category && `(${latestPerf.db_category})`}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{latestPerf.db_latency_note}</div>
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', marginBottom: '16px' }}>
            {[
              { label: 'TTFB', value: latestPerf.ttfb_ms, unit: 'ms', color: latestPerf.ttfb_ms > 2000 ? 'var(--color-status-critical)' : latestPerf.ttfb_ms > 800 ? 'var(--color-status-warning)' : 'var(--color-status-ok)' },
              { label: 'DOM Loaded', value: latestPerf.dom_content_loaded_ms, unit: 'ms' },
              { label: 'DOM Complete', value: latestPerf.dom_complete_ms, unit: 'ms' },
              { label: 'Total Load', value: latestPerf.total_load_ms, unit: 'ms', color: latestPerf.total_load_ms > 10000 ? 'var(--color-status-critical)' : latestPerf.total_load_ms > 5000 ? 'var(--color-status-warning)' : 'var(--color-status-ok)' },
              { label: 'First Paint', value: latestPerf.first_paint_ms, unit: 'ms' },
              { label: 'FCP', value: latestPerf.first_contentful_paint_ms, unit: 'ms' },
              { label: 'DNS', value: latestPerf.dns_ms, unit: 'ms' },
              { label: 'TCP/TLS', value: (latestPerf.tcp_ms || 0) + (latestPerf.tls_ms || 0), unit: 'ms' },
              { label: 'Download', value: latestPerf.download_ms, unit: 'ms' },
              { label: 'Resources', value: latestPerf.resource_count, unit: '' },
              { label: 'Scripts', value: latestPerf.script_count, unit: '' },
              { label: 'Transfer', value: latestPerf.total_transfer_kb, unit: 'KB' },
              { label: 'Backend %', value: latestPerf.backend_time_pct, unit: '%', color: latestPerf.backend_time_pct > 70 ? 'var(--color-status-critical)' : latestPerf.backend_time_pct > 50 ? 'var(--color-status-warning)' : 'var(--color-status-ok)' },
            ].map((m, i) => (
              <div key={i} style={{ background: 'var(--color-bg)', borderRadius: 'var(--radius)', padding: '10px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: m.color || 'var(--color-text)' }}>
                  {m.value != null ? m.value : '-'}<span style={{ fontSize: '11px', fontWeight: 400 }}>{m.unit}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{m.label}</div>
              </div>
            ))}
          </div>

          {latestPerf.slow_resources && latestPerf.slow_resources.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>Slow Resources (&gt;1s)</h4>
              <div className="table-container"><table>
                <thead><tr><th>Resource</th><th>Type</th><th>Duration</th><th>Size</th></tr></thead>
                <tbody>{latestPerf.slow_resources.map((r, i) => (
                  <tr key={i}>
                    <td title={r.name} style={{ fontSize: '12px', maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.name}</td>
                    <td><span className="badge badge-warning" style={{ fontSize: '10px' }}>{r.type}</span></td>
                    <td style={{ fontWeight: 600, color: 'var(--color-status-warning)' }}>{r.duration}ms</td>
                    <td style={{ fontSize: '12px' }}>{r.size ? `${Math.round(r.size / 1024)}KB` : '-'}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            </div>
          )}

          {latestPerf.slow_api_calls && latestPerf.slow_api_calls.length > 0 && (
            <div style={{ marginBottom: '12px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>Slow API Calls (&gt;2s)</h4>
              <div className="table-container"><table>
                <thead><tr><th>API Endpoint</th><th>Duration</th><th>Size</th></tr></thead>
                <tbody>{latestPerf.slow_api_calls.map((r, i) => (
                  <tr key={i}>
                    <td title={r.url} style={{ fontSize: '12px' }}>{r.url}</td>
                    <td style={{ fontWeight: 600, color: 'var(--color-status-critical)' }}>{r.duration}ms</td>
                    <td style={{ fontSize: '12px' }}>{r.size ? `${Math.round(r.size / 1024)}KB` : '-'}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            </div>
          )}

          {latestPerf.failed_resources && latestPerf.failed_resources.length > 0 && (
            <div>
              <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: 'var(--color-status-critical)' }}>Failed Resources</h4>
              <div className="table-container"><table>
                <thead><tr><th>Resource</th><th>Type</th><th>Status</th></tr></thead>
                <tbody>{latestPerf.failed_resources.map((r, i) => (
                  <tr key={i}>
                    <td title={r.name} style={{ fontSize: '12px' }}>{r.name}</td>
                    <td>{r.type}</td>
                    <td><span className="badge badge-critical" style={{ fontSize: '10px' }}>{r.status || 'Failed'}</span></td>
                  </tr>
                ))}</tbody>
              </table></div>
            </div>
          )}
        </div>
      )}

      {/* IIS / App Pool Diagnostics */}
      {iisDiag && iisDiag.has_issues && (
        <div className="card">
          <div className="card-header">
            <h3>IIS / App Pool Diagnostics</h3>
            <span className="badge badge-warning">{iisDiag.recommendations?.length || 0} recommendation(s)</span>
          </div>

          {/* Summary stats */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px', marginBottom: '16px' }}>
            {[
              { label: 'Checks (24h)', value: iisDiag.summary?.checks_24h },
              { label: 'Failures', value: iisDiag.summary?.failures_24h, color: iisDiag.summary?.failures_24h > 0 ? 'var(--color-status-critical)' : undefined },
              { label: 'Slow', value: iisDiag.summary?.slow_24h, color: iisDiag.summary?.slow_24h > 0 ? 'var(--color-status-warning)' : undefined },
              { label: 'Failure Rate', value: `${iisDiag.summary?.failure_rate || 0}%`, color: iisDiag.summary?.failure_rate > 10 ? 'var(--color-status-critical)' : undefined },
              { label: 'Cold Starts', value: iisDiag.summary?.cold_starts },
              { label: 'Error Pages', value: iisDiag.summary?.error_pages, color: iisDiag.summary?.error_pages > 0 ? 'var(--color-status-critical)' : undefined },
            ].map((m, i) => (
              <div key={i} style={{ background: 'var(--color-bg)', borderRadius: 'var(--radius)', padding: '10px', textAlign: 'center' }}>
                <div style={{ fontSize: '18px', fontWeight: 700, color: m.color || 'var(--color-text)' }}>{m.value ?? '-'}</div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>{m.label}</div>
              </div>
            ))}
          </div>

          {/* Recommendations */}
          {iisDiag.recommendations?.map((rec, i) => (
            <div key={i} style={{
              background: rec.priority === 'high' ? '#fff5f5' : '#fffaf0',
              border: `1px solid ${rec.priority === 'high' ? '#feb2b2' : '#fbd38d'}`,
              borderLeft: `4px solid ${rec.priority === 'high' ? '#e53e3e' : '#dd6b20'}`,
              borderRadius: 'var(--radius)', padding: '14px 16px', marginBottom: '12px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <span className={`badge badge-${rec.priority === 'high' ? 'critical' : 'warning'}`} style={{ fontSize: '10px' }}>{rec.priority}</span>
                <strong style={{ fontSize: '13px' }}>{rec.category}</strong>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '8px' }}>{rec.issue}</div>
              <div style={{ fontSize: '12px' }}>
                <strong>Recommended actions:</strong>
                <ul style={{ margin: '6px 0 0 16px', padding: 0, lineHeight: 1.8 }}>
                  {rec.actions?.map((a, j) => <li key={j}>{a}</li>)}
                </ul>
              </div>
            </div>
          ))}

          {/* Recent IIS issues detected */}
          {iisDiag.iis_issues_detected?.length > 0 && (
            <div style={{ marginTop: '12px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>Recent IIS Issues Detected</h4>
              <div className="table-container">
                <table>
                  <thead><tr><th>Time (CST)</th><th>Category</th><th>Severity</th><th>Diagnosis</th></tr></thead>
                  <tbody>
                    {iisDiag.iis_issues_detected.slice(0, 10).map((issue, i) => (
                      <tr key={i}>
                        <td style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>{formatCST(issue.time)}</td>
                        <td><span className="badge badge-warning" style={{ fontSize: '10px' }}>{issue.category}</span></td>
                        <td><span className={`badge badge-${issue.severity === 'critical' ? 'critical' : 'warning'}`} style={{ fontSize: '10px' }}>{issue.severity}</span></td>
                        <td title={issue.diagnosis} style={{ fontSize: '11px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>{issue.diagnosis}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* No IIS issues — show clean status */}
      {iisDiag && !iisDiag.has_issues && iisDiag.summary && (
        <div className="card" style={{ textAlign: 'center', padding: '20px' }}>
          <span style={{ fontSize: '20px', color: 'var(--color-status-ok)' }}>&#10003;</span>
          <div style={{ fontWeight: 500, fontSize: '14px', marginTop: '4px' }}>IIS Health: No Issues Detected</div>
          <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
            {iisDiag.summary.checks_24h} checks in 24h | {iisDiag.summary.failure_rate}% failure rate | Avg {iisDiag.summary.avg_response_ms}ms
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
                const subpages = parseDetails(r.details).subpages;
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
                      <td>{formatCST(r.checked_at)}</td>
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
                      <td title={r.error_message || ''} style={{ maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>
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

