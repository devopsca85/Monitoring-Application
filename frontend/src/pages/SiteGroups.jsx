import { useState, useEffect } from 'react';
import { getGroups, createGroup, updateGroup, deleteGroup } from '../services/api';

export default function SiteGroups() {
  const [groups, setGroups] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: '', description: '', environment: '',
    login_url: '', username_selector: '#username', password_selector: '#password',
    submit_selector: "input[type='submit']", success_indicator: '', expected_page: 'mainpage.aspx',
    username: '', password: '',
  });
  const [msg, setMsg] = useState('');

  const load = () => getGroups().then(r => setGroups(r.data || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setForm({ name: '', description: '', environment: '', login_url: '', username_selector: '#username',
      password_selector: '#password', submit_selector: "input[type='submit']", success_indicator: '',
      expected_page: 'mainpage.aspx', username: '', password: '' });
    setEditing(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await updateGroup(editing.id, form);
        setMsg('Group updated');
      } else {
        await createGroup(form);
        setMsg('Group created');
      }
      setShowModal(false); resetForm(); load();
      setTimeout(() => setMsg(''), 3000);
    } catch (err) { setMsg(err.response?.data?.detail || 'Failed'); }
  };

  const handleEdit = (g) => {
    setEditing(g);
    setForm({
      name: g.name, description: g.description || '', environment: g.environment || '',
      login_url: g.login_url || '', username_selector: g.username_selector || '#username',
      password_selector: g.password_selector || '#password',
      submit_selector: g.submit_selector || "input[type='submit']",
      success_indicator: g.success_indicator || '', expected_page: g.expected_page || 'mainpage.aspx',
      username: '', password: '',
    });
    setShowModal(true);
  };

  return (
    <div>
      <div className="page-header">
        <h2>Site Groups</h2>
        <button onClick={() => { resetForm(); setShowModal(true); }} className="btn btn-primary">+ New Group</button>
      </div>

      {msg && <div className="error-message" style={{ background: '#f0fff4', color: 'var(--color-status-ok)', marginBottom: '16px' }}>{msg}</div>}

      <div className="card">
        <div className="table-container">
          <table>
            <thead><tr><th>Group</th><th>Environment</th><th>Login URL</th><th>Credentials</th><th>Sites</th><th>Actions</th></tr></thead>
            <tbody>
              {groups.map(g => (
                <tr key={g.id}>
                  <td><strong>{g.name}</strong>{g.description && <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{g.description}</div>}</td>
                  <td>{g.environment ? <span className="badge badge-ok" style={{ fontSize: '10px' }}>{g.environment}</span> : '-'}</td>
                  <td style={{ fontSize: '12px', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.login_url || '-'}</td>
                  <td>{g.has_credentials ? <span className="badge badge-ok">Set</span> : <span className="badge badge-warning">None</span>}</td>
                  <td style={{ fontWeight: 600 }}>{g.site_count}</td>
                  <td style={{ display: 'flex', gap: '4px' }}>
                    <button onClick={() => handleEdit(g)} className="btn btn-primary" style={{ padding: '3px 10px', fontSize: '11px' }}>Edit</button>
                    <button onClick={() => { if(confirm(`Delete group "${g.name}"?`)) deleteGroup(g.id).then(load); }} className="btn btn-danger" style={{ padding: '3px 10px', fontSize: '11px' }}>Delete</button>
                  </td>
                </tr>
              ))}
              {groups.length === 0 && <tr><td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>No groups yet. Create groups to share login credentials across sites.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: 'var(--radius-lg)', padding: '28px', width: '100%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'var(--shadow-xl)' }}>
            <h3 style={{ marginBottom: '16px' }}>{editing ? 'Edit Group' : 'Create Group'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group"><label>Group Name</label><input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Production Sites" required /></div>
                <div className="form-group"><label>Environment</label>
                  <select value={form.environment} onChange={e => setForm({...form, environment: e.target.value})}>
                    <option value="">None</option><option value="production">Production</option><option value="staging">Staging</option><option value="qa">QA</option><option value="development">Development</option>
                  </select>
                </div>
              </div>
              <div className="form-group"><label>Description</label><input value={form.description} onChange={e => setForm({...form, description: e.target.value})} placeholder="Optional description" /></div>

              <h4 style={{ fontSize: '14px', fontWeight: 600, margin: '16px 0 10px', padding: '10px 0', borderTop: '1px solid var(--color-border)' }}>Shared Login Credentials</h4>
              <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '12px' }}>Sites in this group will inherit these credentials unless they have their own.</p>

              <div className="form-group"><label>Login URL</label><input value={form.login_url} onChange={e => setForm({...form, login_url: e.target.value})} placeholder="https://example.com/login" /></div>
              <div className="form-row">
                <div className="form-group"><label>Username</label><input value={form.username} onChange={e => setForm({...form, username: e.target.value})} placeholder={editing ? 'Leave blank to keep' : ''} /></div>
                <div className="form-group"><label>Password</label><input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} placeholder={editing ? 'Leave blank to keep' : ''} /></div>
              </div>
              <div className="form-row">
                <div className="form-group"><label>Username Selector</label><input value={form.username_selector} onChange={e => setForm({...form, username_selector: e.target.value})} /></div>
                <div className="form-group"><label>Password Selector</label><input value={form.password_selector} onChange={e => setForm({...form, password_selector: e.target.value})} /></div>
              </div>
              <div className="form-row">
                <div className="form-group"><label>Submit Selector</label><input value={form.submit_selector} onChange={e => setForm({...form, submit_selector: e.target.value})} /></div>
                <div className="form-group"><label>Expected Page</label><input value={form.expected_page} onChange={e => setForm({...form, expected_page: e.target.value})} /></div>
              </div>
              <div className="form-group"><label>Success Indicator (CSS)</label><input value={form.success_indicator} onChange={e => setForm({...form, success_indicator: e.target.value})} placeholder="Optional CSS selector" /></div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button type="submit" className="btn btn-primary">{editing ? 'Save' : 'Create Group'}</button>
                <button type="button" onClick={() => { setShowModal(false); resetForm(); }} className="btn btn-outline">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
