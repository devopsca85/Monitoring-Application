import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSites, deleteSite } from '../services/api';

export default function Sites() {
  const [sites, setSites] = useState([]);

  const load = () => getSites().then((r) => setSites(r.data)).catch(() => {});

  useEffect(() => { load(); }, []);

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    await deleteSite(id);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <h2>Sites</h2>
        <Link to="/sites/new" className="btn btn-primary">+ Add Site</Link>
      </div>
      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>URL</th>
                <th>Check Type</th>
                <th>Interval</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sites.map((site) => (
                <tr key={site.id}>
                  <td><Link to={`/sites/${site.id}`} style={{ fontWeight: 500 }}>{site.name}</Link></td>
                  <td style={{ color: 'var(--color-text-secondary)', maxWidth: '250px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{site.url}</td>
                  <td><span className="badge badge-ok">{site.check_type}</span></td>
                  <td>{site.check_interval_minutes}m</td>
                  <td><span className={`badge badge-${site.is_active ? 'ok' : 'warning'}`}>{site.is_active ? 'Active' : 'Paused'}</span></td>
                  <td style={{ display: 'flex', gap: '8px' }}>
                    <Link to={`/sites/${site.id}/edit`} className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '12px' }}>Edit</Link>
                    <button onClick={() => handleDelete(site.id, site.name)} className="btn btn-danger" style={{ padding: '4px 12px', fontSize: '12px' }}>Delete</button>
                  </td>
                </tr>
              ))}
              {sites.length === 0 && (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>No sites yet. Click "+ Add Site" to get started.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
