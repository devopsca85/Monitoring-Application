import { useState, useEffect } from 'react';
import { getUsers, createUser, updateUser, deleteUser } from '../services/api';

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [form, setForm] = useState({ email: '', password: '', full_name: '', is_admin: false, is_active: true });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const load = () => getUsers().then((r) => setUsers(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const resetForm = () => {
    setForm({ email: '', password: '', full_name: '', is_admin: false, is_active: true });
    setEditingUser(null);
    setError('');
  };

  const openCreate = () => { resetForm(); setShowModal(true); };

  const openEdit = (user) => {
    setEditingUser(user);
    setForm({ email: user.email, password: '', full_name: user.full_name || '', is_admin: user.is_admin, is_active: user.is_active });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (editingUser) {
        const payload = { ...form };
        if (!payload.password) delete payload.password;
        await updateUser(editingUser.id, payload);
        setSuccess('User updated successfully');
      } else {
        if (!form.password) { setError('Password is required'); return; }
        await createUser(form);
        setSuccess('User created successfully');
      }
      setShowModal(false);
      resetForm();
      load();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (user) => {
    if (!confirm(`Delete user "${user.email}"? This cannot be undone.`)) return;
    try {
      await deleteUser(user.id);
      setSuccess('User deleted');
      load();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Delete failed');
      setTimeout(() => setError(''), 3000);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>User Management</h2>
        <button onClick={openCreate} className="btn btn-primary">+ Add User</button>
      </div>

      {success && <div className="error-message" style={{ background: '#f0fff4', color: 'var(--color-status-ok)', marginBottom: '16px' }}>{success}</div>}
      {error && !showModal && <div className="error-message" style={{ marginBottom: '16px' }}>{error}</div>}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td style={{ fontWeight: 500 }}>{u.full_name || '-'}</td>
                  <td>{u.email}</td>
                  <td>
                    <span className={`badge ${u.is_admin ? 'badge-warning' : 'badge-ok'}`}>
                      {u.is_admin ? 'Admin' : 'User'}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${u.is_active ? 'badge-ok' : 'badge-critical'}`}>
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td>{u.created_at ? new Date(u.created_at).toLocaleDateString('en-US', { timeZone: 'America/Chicago' }) : '-'}</td>
                  <td style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={() => openEdit(u)} className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '12px' }}>Edit</button>
                    <button onClick={() => handleDelete(u)} className="btn btn-danger" style={{ padding: '4px 12px', fontSize: '12px' }}>Delete</button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan="7" style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>No users found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', borderRadius: 'var(--radius-lg)', padding: '32px', width: '100%', maxWidth: '500px', boxShadow: 'var(--shadow-lg)' }}>
            <h3 style={{ marginBottom: '20px' }}>{editingUser ? 'Edit User' : 'Create User'}</h3>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Full Name</label>
                <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="John Doe" />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="user@company.com" required />
              </div>
              <div className="form-group">
                <label>Password{editingUser ? ' (leave blank to keep current)' : ''}</label>
                <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={editingUser ? 'Leave blank to keep current' : 'Enter password'} required={!editingUser} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Role</label>
                  <select value={form.is_admin ? 'admin' : 'user'} onChange={(e) => setForm({ ...form, is_admin: e.target.value === 'admin' })}>
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Status</label>
                  <select value={form.is_active ? 'active' : 'disabled'} onChange={(e) => setForm({ ...form, is_active: e.target.value === 'active' })}>
                    <option value="active">Active</option>
                    <option value="disabled">Disabled</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                <button type="submit" className="btn btn-primary">{editingUser ? 'Save Changes' : 'Create User'}</button>
                <button type="button" onClick={() => { setShowModal(false); resetForm(); }} className="btn btn-outline">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
