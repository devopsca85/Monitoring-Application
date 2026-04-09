import { useState, useEffect } from 'react';
import { getSystemSettings, updateSmtpSettings, updateTeamsSettings, testSmtp } from '../services/api';

export default function AdminSettings() {
  const [loading, setLoading] = useState(true);
  const [smtp, setSmtp] = useState({
    smtp_host: '', smtp_port: '587', smtp_user: '', smtp_password: '',
    smtp_from_email: '', smtp_use_tls: 'true',
  });
  const [smtpPasswordSet, setSmtpPasswordSet] = useState(false);
  const [teams, setTeams] = useState({ teams_webhook_url: '' });
  const [teamsSet, setTeamsSet] = useState(false);
  const [testEmail, setTestEmail] = useState('');
  const [msg, setMsg] = useState({ text: '', type: '' });

  const showMsg = (text, type = 'success') => {
    setMsg({ text, type });
    setTimeout(() => setMsg({ text: '', type: '' }), 5000);
  };

  useEffect(() => {
    getSystemSettings()
      .then((r) => {
        const s = r.data;
        setSmtp({
          smtp_host: s.smtp_host || '',
          smtp_port: s.smtp_port || '587',
          smtp_user: s.smtp_user || '',
          smtp_password: '',
          smtp_from_email: s.smtp_from_email || '',
          smtp_use_tls: s.smtp_use_tls || 'true',
        });
        setSmtpPasswordSet(s.smtp_password_set);
        setTeams({ teams_webhook_url: '' });
        setTeamsSet(s.teams_webhook_set);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSaveSmtp = async (e) => {
    e.preventDefault();
    try {
      await updateSmtpSettings(smtp);
      showMsg('SMTP settings saved successfully');
      if (smtp.smtp_password) setSmtpPasswordSet(true);
    } catch (err) {
      showMsg(err.response?.data?.detail || 'Failed to save SMTP settings', 'error');
    }
  };

  const handleSaveTeams = async (e) => {
    e.preventDefault();
    try {
      await updateTeamsSettings(teams);
      showMsg('Teams webhook saved successfully');
      if (teams.teams_webhook_url) setTeamsSet(true);
    } catch (err) {
      showMsg(err.response?.data?.detail || 'Failed to save Teams settings', 'error');
    }
  };

  const handleTestSmtp = async () => {
    if (!testEmail) { showMsg('Enter a test email address', 'error'); return; }
    try {
      await testSmtp({ to_email: testEmail });
      showMsg(`Test email sent to ${testEmail}`);
    } catch (err) {
      showMsg(err.response?.data?.detail || 'SMTP test failed', 'error');
    }
  };

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <h2>System Settings</h2>
      </div>

      {msg.text && (
        <div className="error-message" style={{
          background: msg.type === 'error' ? undefined : '#f0fff4',
          color: msg.type === 'error' ? undefined : 'var(--color-status-ok)',
          marginBottom: '16px'
        }}>
          {msg.text}
        </div>
      )}

      {/* SMTP Settings */}
      <form onSubmit={handleSaveSmtp}>
        <div className="card">
          <div className="card-header">
            <h3>Email (SMTP) Settings</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`badge ${smtpPasswordSet && smtp.smtp_host ? 'badge-ok' : 'badge-warning'}`}>
                {smtpPasswordSet && smtp.smtp_host ? 'Configured' : 'Not Configured'}
              </span>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>SMTP Host</label>
              <input value={smtp.smtp_host} onChange={(e) => setSmtp({ ...smtp, smtp_host: e.target.value })} placeholder="smtp.gmail.com" />
            </div>
            <div className="form-group">
              <label>SMTP Port</label>
              <input value={smtp.smtp_port} onChange={(e) => setSmtp({ ...smtp, smtp_port: e.target.value })} placeholder="587" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>SMTP Username</label>
              <input value={smtp.smtp_user} onChange={(e) => setSmtp({ ...smtp, smtp_user: e.target.value })} placeholder="alerts@company.com" />
            </div>
            <div className="form-group">
              <label>SMTP Password {smtpPasswordSet && <span style={{ color: 'var(--color-status-ok)', fontSize: '12px' }}>(currently set — leave blank to keep)</span>}</label>
              <input type="password" value={smtp.smtp_password} onChange={(e) => setSmtp({ ...smtp, smtp_password: e.target.value })} placeholder={smtpPasswordSet ? 'Leave blank to keep current' : 'Enter SMTP password'} />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>From Email</label>
              <input value={smtp.smtp_from_email} onChange={(e) => setSmtp({ ...smtp, smtp_from_email: e.target.value })} placeholder="monitoring@company.com" />
            </div>
            <div className="form-group">
              <label>Use TLS</label>
              <select value={smtp.smtp_use_tls} onChange={(e) => setSmtp({ ...smtp, smtp_use_tls: e.target.value })}>
                <option value="true">Yes (recommended)</option>
                <option value="false">No</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
            <button type="submit" className="btn btn-primary">Save SMTP Settings</button>
          </div>
        </div>
      </form>

      {/* Test Email */}
      <div className="card">
        <div className="card-header"><h3>Test Email</h3></div>
        <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
          Send a test email to verify your SMTP configuration is working.
        </p>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <label>Recipient Email</label>
            <input value={testEmail} onChange={(e) => setTestEmail(e.target.value)} placeholder="your@email.com" type="email" />
          </div>
          <button type="button" onClick={handleTestSmtp} className="btn btn-outline" style={{ height: '42px' }}>Send Test</button>
        </div>
      </div>

      {/* Teams Webhook */}
      <form onSubmit={handleSaveTeams}>
        <div className="card">
          <div className="card-header">
            <h3>Microsoft Teams Webhook</h3>
            <span className={`badge ${teamsSet ? 'badge-ok' : 'badge-warning'}`}>
              {teamsSet ? 'Configured' : 'Not Configured'}
            </span>
          </div>
          <div className="form-group">
            <label>Webhook URL {teamsSet && <span style={{ color: 'var(--color-status-ok)', fontSize: '12px' }}>(currently set — leave blank to keep)</span>}</label>
            <input value={teams.teams_webhook_url} onChange={(e) => setTeams({ ...teams, teams_webhook_url: e.target.value })} placeholder={teamsSet ? 'Leave blank to keep current webhook' : 'https://your-org.webhook.office.com/webhookb2/...'} />
          </div>
          <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>Save Teams Settings</button>
        </div>
      </form>

      {/* Security Info */}
      <div className="card">
        <div className="card-header"><h3>Security</h3></div>
        <div style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          <p style={{ marginBottom: '8px' }}>All sensitive data is encrypted at rest:</p>
          <ul style={{ paddingLeft: '20px', lineHeight: '2' }}>
            <li>Site login credentials (username & password) — <strong>Fernet AES-128 encrypted</strong></li>
            <li>SMTP password — <strong>Fernet AES-128 encrypted</strong></li>
            <li>Teams webhook URL — <strong>Fernet AES-128 encrypted</strong></li>
            <li>User passwords — <strong>bcrypt hashed</strong> (one-way, cannot be decrypted)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
