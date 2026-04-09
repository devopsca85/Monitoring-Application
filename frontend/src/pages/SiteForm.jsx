import { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { createSite, getSite, getSiteCredentials, updateSite } from '../services/api';

export default function SiteForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(isEdit);
  const [form, setForm] = useState({
    name: '',
    url: '',
    check_type: 'uptime',
    check_interval_minutes: 5,
    slow_threshold_ms: 8000,
    notification_channel: 'email',
    notification_emails: '',
    is_active: true,
  });
  const [credentials, setCredentials] = useState({
    login_url: '',
    username_selector: '#username',
    password_selector: '#password',
    submit_selector: "button[type='submit']",
    success_indicator: '',
    expected_page: 'mainpage.aspx',
    username: '',
    password: '',
  });
  const [pages, setPages] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isEdit) return;

    Promise.all([getSite(id), getSiteCredentials(id)])
      .then(([siteRes, credRes]) => {
        const site = siteRes.data;
        setForm({
          name: site.name,
          url: site.url,
          check_type: site.check_type,
          check_interval_minutes: site.check_interval_minutes,
          slow_threshold_ms: site.slow_threshold_ms || 5000,
          notification_channel: site.notification_channel,
          notification_emails: site.notification_emails || '',
          is_active: site.is_active,
        });
        if (site.pages && site.pages.length > 0) {
          setPages(site.pages.map((p) => ({
            page_url: p.page_url,
            page_name: p.page_name || '',
            expected_element: p.expected_element || '',
            expected_text: p.expected_text || '',
            sort_order: p.sort_order,
          })));
        }
        if (credRes.data) {
          setCredentials({
            login_url: credRes.data.login_url || '',
            username_selector: credRes.data.username_selector || '#username',
            password_selector: credRes.data.password_selector || '#password',
            submit_selector: credRes.data.submit_selector || "button[type='submit']",
            success_indicator: credRes.data.success_indicator || '',
            expected_page: credRes.data.expected_page || 'mainpage.aspx',
            username: '',
            password: '',
          });
        }
      })
      .catch(() => setError('Failed to load site'))
      .finally(() => setLoading(false));
  }, [id, isEdit]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const payload = { ...form };
      if (form.check_type === 'login' || form.check_type === 'multi_page') {
        payload.credentials = credentials;
      }
      if (form.check_type === 'login' || form.check_type === 'multi_page') {
        payload.pages = pages;
      }

      if (isEdit) {
        await updateSite(id, payload);
      } else {
        await createSite(payload);
      }
      navigate('/sites');
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to ${isEdit ? 'update' : 'create'} site`);
    }
  };

  const addPage = () => {
    setPages([...pages, { page_url: '', page_name: '', expected_element: '', expected_text: '', sort_order: pages.length }]);
  };

  const updatePage = (idx, field, value) => {
    const updated = [...pages];
    updated[idx] = { ...updated[idx], [field]: value };
    setPages(updated);
  };

  const removePage = (idx) => {
    setPages(pages.filter((_, i) => i !== idx));
  };

  if (loading) return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>Loading...</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/sites" style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>&larr; Back to Sites</Link>
          <h2 style={{ marginTop: '4px' }}>{isEdit ? 'Edit Site' : 'Add New Site'}</h2>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="card">
          <div className="card-header"><h3>Basic Information</h3></div>
          <div className="form-row">
            <div className="form-group">
              <label>Site Name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My Website" required />
            </div>
            <div className="form-group">
              <label>URL</label>
              <input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://example.com" required />
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Check Type</label>
              <select value={form.check_type} onChange={(e) => setForm({ ...form, check_type: e.target.value })}>
                <option value="uptime">Uptime Check</option>
                <option value="login">Login Validation</option>
                <option value="multi_page">Multi-Page Validation</option>
              </select>
            </div>
            <div className="form-group">
              <label>Check Interval</label>
              <select value={String(form.check_interval_minutes)} onChange={(e) => setForm({ ...form, check_interval_minutes: parseInt(e.target.value) })}>
                <option value="1">Every 1 minute</option>
                <option value="3">Every 3 minutes</option>
                <option value="5">Every 5 minutes</option>
                <option value="10">Every 10 minutes</option>
                <option value="15">Every 15 minutes</option>
                <option value="30">Every 30 minutes</option>
                <option value="60">Every 60 minutes</option>
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Slow Response Threshold</label>
              <select value={String(form.slow_threshold_ms)} onChange={(e) => setForm({ ...form, slow_threshold_ms: parseInt(e.target.value) })}>
                <option value="2000">2 seconds</option>
                <option value="3000">3 seconds</option>
                <option value="5000">5 seconds</option>
                <option value="8000">8 seconds (default)</option>
                <option value="10000">10 seconds</option>
                <option value="15000">15 seconds</option>
                <option value="20000">20 seconds</option>
                <option value="30000">30 seconds</option>
              </select>
              <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px', display: 'block' }}>
                Alert if page load takes longer than this.
              </span>
            </div>
            <div className="form-group">
              <label>Notification Channel</label>
              <select value={form.notification_channel} onChange={(e) => setForm({ ...form, notification_channel: e.target.value })}>
                <option value="email">Email</option>
                <option value="teams">Teams</option>
                <option value="both">MS Teams & Email</option>
              </select>
            </div>
            <div className="form-group">
              <label>Notification Emails (comma-separated)</label>
              <input value={form.notification_emails} onChange={(e) => setForm({ ...form, notification_emails: e.target.value })} placeholder="admin@company.com, ops@company.com" />
            </div>
          </div>
          {isEdit && (
            <div className="form-group">
              <label>Status</label>
              <select value={form.is_active ? 'true' : 'false'} onChange={(e) => setForm({ ...form, is_active: e.target.value === 'true' })}>
                <option value="true">Active</option>
                <option value="false">Paused</option>
              </select>
            </div>
          )}
        </div>

        {(form.check_type === 'login' || form.check_type === 'multi_page') && (
          <div className="card">
            <div className="card-header"><h3>Login Credentials</h3></div>
            {isEdit && (
              <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginBottom: '16px' }}>
                Leave username and password blank to keep the existing values.
              </p>
            )}
            <div className="form-group">
              <label>Login URL</label>
              <input value={credentials.login_url} onChange={(e) => setCredentials({ ...credentials, login_url: e.target.value })} placeholder="https://example.com/login" />
              <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px', display: 'block' }}>
                For SSO sites, use the backdoor/direct login URL. After login, the system verifies <strong>mainpage.aspx</strong> loads.
              </span>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Success Indicator (CSS Selector) <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 'normal' }}>— optional</span></label>
                <input value={credentials.success_indicator} onChange={(e) => setCredentials({ ...credentials, success_indicator: e.target.value })} placeholder="e.g. TabContainer1_tbTraining or #dashboard" />
                <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px', display: 'block' }}>
                  If left empty, the system checks that <strong>mainpage.aspx</strong> opens after login.
                </span>
              </div>
              <div className="form-group">
                <label>Expected Post-Login Page <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)', fontWeight: 'normal' }}>— optional</span></label>
                <input value={credentials.expected_page || ''} onChange={(e) => setCredentials({ ...credentials, expected_page: e.target.value })} placeholder="mainpage.aspx (default)" />
                <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px', display: 'block' }}>
                  Page that should appear in the URL after successful login.
                </span>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Username{isEdit ? ' (leave blank to keep current)' : ''}</label>
                <input value={credentials.username} onChange={(e) => setCredentials({ ...credentials, username: e.target.value })} placeholder={isEdit ? 'Leave blank to keep current' : ''} required={!isEdit} />
              </div>
              <div className="form-group">
                <label>Password{isEdit ? ' (leave blank to keep current)' : ''}</label>
                <input type="password" value={credentials.password} onChange={(e) => setCredentials({ ...credentials, password: e.target.value })} placeholder={isEdit ? 'Leave blank to keep current' : ''} required={!isEdit} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Username Selector</label>
                <input value={credentials.username_selector} onChange={(e) => setCredentials({ ...credentials, username_selector: e.target.value })} />
              </div>
              <div className="form-group">
                <label>Password Selector</label>
                <input value={credentials.password_selector} onChange={(e) => setCredentials({ ...credentials, password_selector: e.target.value })} />
              </div>
            </div>
            <div className="form-group">
              <label>Submit Button Selector</label>
              <input value={credentials.submit_selector} onChange={(e) => setCredentials({ ...credentials, submit_selector: e.target.value })} />
            </div>
          </div>
        )}

        {(form.check_type === 'login' || form.check_type === 'multi_page') && (
          <div className="card">
            <div className="card-header">
              <h3>Subpages to Validate After Login</h3>
              <button type="button" onClick={addPage} className="btn btn-outline">+ Add Page</button>
            </div>
            {pages.map((page, idx) => (
              <div key={idx} style={{ padding: '16px', background: 'var(--color-bg)', borderRadius: 'var(--radius)', marginBottom: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <strong>Page {idx + 1}</strong>
                  <button type="button" onClick={() => removePage(idx)} className="btn btn-danger" style={{ padding: '4px 10px', fontSize: '12px' }}>Remove</button>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Page Name</label>
                    <input value={page.page_name} onChange={(e) => updatePage(idx, 'page_name', e.target.value)} placeholder="Dashboard" />
                  </div>
                  <div className="form-group">
                    <label>Page URL</label>
                    <input value={page.page_url} onChange={(e) => updatePage(idx, 'page_url', e.target.value)} placeholder="https://example.com/dashboard" required />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Expected Element (CSS Selector)</label>
                    <input value={page.expected_element} onChange={(e) => updatePage(idx, 'expected_element', e.target.value)} placeholder=".content, #main" />
                  </div>
                  <div className="form-group">
                    <label>Expected Text</label>
                    <input value={page.expected_text} onChange={(e) => updatePage(idx, 'expected_text', e.target.value)} placeholder="Welcome" />
                  </div>
                </div>
              </div>
            ))}
            {pages.length === 0 && <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: '20px' }}>No subpages added. Click "+ Add Page" to validate pages after login.</p>}
          </div>
        )}

        <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
          {isEdit ? 'Save Changes' : 'Create Site'}
        </button>
      </form>
    </div>
  );
}
