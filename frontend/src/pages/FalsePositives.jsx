import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getFalsePositives, restoreFalsePositive, deleteFpRule } from '../services/api';
import { formatCST } from '../services/time';

export default function FalsePositives() {
  const [data, setData] = useState({ alerts: [], rules: [] });
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');

  const load = () => {
    getFalsePositives()
      .then((r) => setData(r.data))
      .catch((e) => console.error('False positives fetch failed:', e))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleRestore = async (id) => {
    if (!confirm('Restore this alert? It will become active again and notifications will resume for this pattern.')) return;
    try {
      await restoreFalsePositive(id);
      setMsg('Alert restored');
      load();
      setTimeout(() => setMsg(''), 3000);
    } catch (e) {
      setMsg('Restore failed');
    }
  };

  const handleDeleteRule = async (id) => {
    if (!confirm('Delete this suppression rule? Future alerts matching this pattern will send notifications again.')) return;
    try {
      await deleteFpRule(id);
      setMsg('Suppression rule deleted');
      load();
      setTimeout(() => setMsg(''), 3000);
    } catch (e) {
      setMsg('Delete failed');
    }
  };

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>False Positives</h2>
        <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
          {data.rules.length} active suppression rule(s)
        </span>
      </div>

      {msg && (
        <div className="error-message" style={{ background: '#f0fff4', color: 'var(--color-status-ok)', marginBottom: '16px' }}>{msg}</div>
      )}

      {/* Active Suppression Rules */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header">
          <h3>Active Suppression Rules</h3>
          <span className="badge badge-warning">{data.rules.length} rule(s)</span>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '12px' }}>
          Alerts matching these patterns will be auto-suppressed — no email or Teams notifications sent.
        </p>
        {data.rules.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Site</th><th>Suppressed Pattern</th><th>Created By</th><th>Created</th><th>Action</th></tr>
              </thead>
              <tbody>
                {data.rules.map((r) => (
                  <tr key={r.id}>
                    <td><Link to={`/sites/${r.site_id}`} style={{ fontWeight: 500 }}>{r.site_name}</Link></td>
                    <td title={r.error_pattern} style={{ fontSize: '12px', maxWidth: '350px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>
                      <code style={{ background: 'var(--color-bg)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px' }}>{r.error_pattern}</code>
                    </td>
                    <td style={{ fontSize: '12px' }}>{r.created_by}</td>
                    <td style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>{formatCST(r.created_at)}</td>
                    <td>
                      <button onClick={() => handleDeleteRule(r.id)} className="btn btn-danger" style={{ padding: '3px 10px', fontSize: '11px' }}>
                        Remove Rule
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
            No active suppression rules. Mark alerts as false positive to create rules.
          </p>
        )}
      </div>

      {/* False Positive Alerts */}
      <div className="card">
        <div className="card-header">
          <h3>False Positive Alerts</h3>
          <span className="badge badge-ok">{data.alerts.length} alert(s)</span>
        </div>
        {data.alerts.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr><th>Site</th><th>Type</th><th>Error Message</th><th>Marked By</th><th>Marked At (CST)</th><th>Original Alert (CST)</th><th>Action</th></tr>
              </thead>
              <tbody>
                {data.alerts.map((a) => (
                  <tr key={a.id}>
                    <td><Link to={`/sites/${a.site_id}`} style={{ fontWeight: 500 }}>{a.site_name}</Link></td>
                    <td><span className={`badge badge-${a.alert_type || 'critical'}`} style={{ fontSize: '10px' }}>{a.alert_type || 'critical'}</span></td>
                    <td title={a.message} style={{ fontSize: '11px', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'default' }}>{a.message}</td>
                    <td style={{ fontSize: '12px' }}>{a.false_positive_by}</td>
                    <td style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>{formatCST(a.false_positive_at)}</td>
                    <td style={{ fontSize: '11px', whiteSpace: 'nowrap' }}>{formatCST(a.created_at)}</td>
                    <td>
                      <button onClick={() => handleRestore(a.id)} className="btn btn-primary" style={{ padding: '3px 10px', fontSize: '11px' }}>
                        Restore
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ textAlign: 'center', padding: '20px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
            No alerts marked as false positive.
          </p>
        )}
      </div>
    </div>
  );
}
