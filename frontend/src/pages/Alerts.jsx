import { useState, useEffect } from 'react';
import { getAlerts, resolveAlert } from '../services/api';

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [showResolved, setShowResolved] = useState(false);

  const load = () => getAlerts(showResolved).then((r) => setAlerts(r.data)).catch(() => {});

  useEffect(() => { load(); }, [showResolved]);

  const handleResolve = async (id) => {
    await resolveAlert(id);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <h2>Alerts</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn ${!showResolved ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setShowResolved(false)}
          >
            Active
          </button>
          <button
            className={`btn ${showResolved ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setShowResolved(true)}
          >
            Resolved
          </button>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th>Severity</th>
                <th>Message</th>
                <th>Created</th>
                {showResolved && <th>Resolved</th>}
                {!showResolved && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id}>
                  <td>Site #{alert.site_id}</td>
                  <td><span className={`badge badge-${alert.alert_type}`}>{alert.alert_type}</span></td>
                  <td style={{ maxWidth: '400px' }}>{alert.message}</td>
                  <td>{new Date(alert.created_at).toLocaleString()}</td>
                  {showResolved && <td>{alert.resolved_at ? new Date(alert.resolved_at).toLocaleString() : '-'}</td>}
                  {!showResolved && (
                    <td>
                      <button onClick={() => handleResolve(alert.id)} className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '12px' }}>
                        Resolve
                      </button>
                    </td>
                  )}
                </tr>
              ))}
              {alerts.length === 0 && (
                <tr><td colSpan={showResolved ? 5 : 5} style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>
                  {showResolved ? 'No resolved alerts' : 'No active alerts'}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
