import { useState, useEffect } from 'react';
import { getSystemSettings, updateSmtpSettings, updateTeamsSettings, testSmtp, testTeams, getSsoSettings, updateSsoSettings } from '../services/api';

export default function AdminSettings() {
  const [loading, setLoading] = useState(true);
  const [smtp, setSmtp] = useState({
    smtp_host: '', smtp_port: '587', smtp_user: '', smtp_password: '',
    smtp_from_email: '', smtp_use_tls: 'true',
  });
  const [smtpPasswordSet, setSmtpPasswordSet] = useState(false);
  const [teams, setTeams] = useState({ teams_webhook_url: '', teams_enabled: true });
  const [teamsSet, setTeamsSet] = useState(false);
  const [testEmail, setTestEmail] = useState('');
  const [sso, setSso] = useState({
    enabled: false, tenant_id: '', client_id: '', client_secret: '',
    redirect_uri: '', admin_group_id: '', user_group_id: '',
  });
  const [ssoSecretSet, setSsoSecretSet] = useState(false);
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
        setTeams({ teams_webhook_url: '', teams_enabled: s.teams_enabled !== false });
        setTeamsSet(s.teams_webhook_set);
      })
      .catch(() => {});

    getSsoSettings()
      .then((r) => {
        const s = r.data;
        setSso({
          enabled: s.enabled, tenant_id: s.tenant_id || '', client_id: s.client_id || '',
          client_secret: '', redirect_uri: s.redirect_uri || '',
          admin_group_id: s.admin_group_id || '', user_group_id: s.user_group_id || '',
        });
        setSsoSecretSet(s.client_secret_set);
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className={`badge ${teamsSet && teams.teams_enabled ? 'badge-ok' : 'badge-warning'}`}>
                {!teamsSet ? 'Not Configured' : teams.teams_enabled ? 'Enabled' : 'Disabled'}
              </span>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}>
                <input
                  type="checkbox"
                  checked={teams.teams_enabled}
                  onChange={(e) => setTeams({ ...teams, teams_enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--color-primary)' }}
                />
                {teams.teams_enabled ? 'ON' : 'OFF'}
              </label>
            </div>
          </div>
          {!teams.teams_enabled && (
            <div style={{ background: '#fffaf0', border: '1px solid #fbd38d', borderRadius: 'var(--radius)', padding: '10px 14px', fontSize: '13px', color: '#dd6b20', marginBottom: '16px' }}>
              Teams notifications are disabled. Toggle ON to send alerts to Teams.
            </div>
          )}
          <div className="form-group">
            <label>Webhook URL {teamsSet && <span style={{ color: 'var(--color-status-ok)', fontSize: '12px' }}>(currently set — leave blank to keep)</span>}</label>
            <input value={teams.teams_webhook_url} onChange={(e) => setTeams({ ...teams, teams_webhook_url: e.target.value })} placeholder={teamsSet ? 'Leave blank to keep current webhook' : 'https://your-org.webhook.office.com/webhookb2/...'} />
          </div>
          <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
            <button type="submit" className="btn btn-primary">Save Teams Settings</button>
            {teamsSet && (
              <button type="button" onClick={async () => {
                try { await testTeams(); showMsg('Test message sent to Teams'); }
                catch (err) { showMsg(err.response?.data?.detail || 'Teams test failed', 'error'); }
              }} className="btn btn-outline">Test Teams</button>
            )}
          </div>
        </div>
      </form>

      {/* Azure SSO */}
      <form onSubmit={async (e) => {
        e.preventDefault();
        try {
          await updateSsoSettings(sso);
          showMsg('Azure SSO settings saved');
          if (sso.client_secret) setSsoSecretSet(true);
        } catch (err) { showMsg(err.response?.data?.detail || 'Failed to save SSO settings', 'error'); }
      }}>
        <div className="card">
          <div className="card-header">
            <h3>Azure SSO (Entra ID)</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className={`badge ${sso.enabled ? 'badge-ok' : 'badge-warning'}`}>
                {sso.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}>
                <input type="checkbox" checked={sso.enabled} onChange={(e) => setSso({ ...sso, enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--color-primary)' }} />
                {sso.enabled ? 'ON' : 'OFF'}
              </label>
            </div>
          </div>

          <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
            Configure Azure App Registration to enable "Sign in with Microsoft" on the login page.
            Users will be auto-created on first SSO login. Map Entra ID groups to control admin/user roles.
          </p>

          <div className="form-row">
            <div className="form-group">
              <label>Tenant ID</label>
              <input value={sso.tenant_id} onChange={(e) => setSso({ ...sso, tenant_id: e.target.value })} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
            </div>
            <div className="form-group">
              <label>Client ID (Application ID)</label>
              <input value={sso.client_id} onChange={(e) => setSso({ ...sso, client_id: e.target.value })} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Client Secret {ssoSecretSet && <span style={{ color: 'var(--color-status-ok)', fontSize: '12px' }}>(set — leave blank to keep)</span>}</label>
              <input type="password" value={sso.client_secret} onChange={(e) => setSso({ ...sso, client_secret: e.target.value })} placeholder={ssoSecretSet ? 'Leave blank to keep current' : 'Enter client secret'} />
            </div>
            <div className="form-group">
              <label>Redirect URI</label>
              <input value={sso.redirect_uri} onChange={(e) => setSso({ ...sso, redirect_uri: e.target.value })} placeholder={`${window.location.origin}/sso/callback`} />
              <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '4px', display: 'block' }}>
                Must match the redirect URI in Azure App Registration.
              </span>
            </div>
          </div>

          <div style={{ background: 'var(--color-bg)', borderRadius: 'var(--radius)', padding: '16px', marginTop: '8px', marginBottom: '12px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 600, marginBottom: '10px' }}>Entra ID Group Mapping</h4>
            <div className="form-row">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Admin Group ID <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 'normal' }}>— users in this group get Admin role</span></label>
                <input value={sso.admin_group_id} onChange={(e) => setSso({ ...sso, admin_group_id: e.target.value })} placeholder="Entra ID Group Object ID (optional)" />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>User Group ID <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 'normal' }}>— only users in this group can access</span></label>
                <input value={sso.user_group_id} onChange={(e) => setSso({ ...sso, user_group_id: e.target.value })} placeholder="Entra ID Group Object ID (optional)" />
              </div>
            </div>
          </div>

          <button type="submit" className="btn btn-primary">Save SSO Settings</button>
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
            <li>Azure SSO client secret — <strong>Fernet AES-128 encrypted</strong></li>
            <li>User passwords — <strong>bcrypt hashed</strong> (one-way, cannot be decrypted)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
