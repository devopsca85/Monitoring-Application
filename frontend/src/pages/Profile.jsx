import { useState } from 'react';
import { updateMe } from '../services/api';

export default function Profile({ user, onUpdate }) {
  const [form, setForm] = useState({
    full_name: user.full_name || '',
    email: user.email,
  });
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', confirm: '' });
  const [msg, setMsg] = useState({ text: '', type: '' });

  const showMsg = (text, type = 'success') => {
    setMsg({ text, type });
    setTimeout(() => setMsg({ text: '', type: '' }), 4000);
  };

  const handleProfile = async (e) => {
    e.preventDefault();
    try {
      const res = await updateMe({ full_name: form.full_name, email: form.email });
      onUpdate(res.data);
      showMsg('Profile updated');
    } catch (err) {
      showMsg(err.response?.data?.detail || 'Update failed', 'error');
    }
  };

  const handlePassword = async (e) => {
    e.preventDefault();
    if (passwords.new_password !== passwords.confirm) {
      showMsg('New passwords do not match', 'error');
      return;
    }
    if (passwords.new_password.length < 6) {
      showMsg('Password must be at least 6 characters', 'error');
      return;
    }
    try {
      await updateMe({ current_password: passwords.current_password, new_password: passwords.new_password });
      setPasswords({ current_password: '', new_password: '', confirm: '' });
      showMsg('Password changed');
    } catch (err) {
      showMsg(err.response?.data?.detail || 'Password change failed', 'error');
    }
  };

  return (
    <div>
      <div className="page-header">
        <h2>My Profile</h2>
        <span className={`badge ${user.is_admin ? 'badge-warning' : 'badge-ok'}`} style={{ fontSize: '13px', padding: '5px 14px' }}>
          {user.is_admin ? 'Admin' : 'User'}
        </span>
      </div>

      {msg.text && (
        <div className="error-message" style={{
          background: msg.type === 'error' ? undefined : '#f0fff4',
          color: msg.type === 'error' ? undefined : 'var(--color-status-ok)',
          marginBottom: '16px',
        }}>{msg.text}</div>
      )}

      <form onSubmit={handleProfile}>
        <div className="card">
          <div className="card-header"><h3>Profile Information</h3></div>
          <div className="form-row">
            <div className="form-group">
              <label>Full Name</label>
              <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </div>
          </div>
          <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>Save Profile</button>
        </div>
      </form>

      <form onSubmit={handlePassword}>
        <div className="card">
          <div className="card-header"><h3>Change Password</h3></div>
          <div className="form-group">
            <label>Current Password</label>
            <input type="password" value={passwords.current_password} onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })} required />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>New Password</label>
              <input type="password" value={passwords.new_password} onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })} required />
            </div>
            <div className="form-group">
              <label>Confirm New Password</label>
              <input type="password" value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} required />
            </div>
          </div>
          <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>Change Password</button>
        </div>
      </form>
    </div>
  );
}
