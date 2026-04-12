import { useState } from 'react';

const ENDPOINTS = [
  {
    group: 'Authentication',
    color: '#10b981',
    endpoints: [
      { method: 'GET', path: '/auth/setup-check', auth: false, desc: 'Check if initial setup is needed' },
      { method: 'POST', path: '/auth/register', auth: false, desc: 'Register first admin user (setup only)' },
      { method: 'POST', path: '/auth/login', auth: false, desc: 'Login with email/password → JWT token' },
      { method: 'GET', path: '/auth/me', auth: true, desc: 'Get current user profile' },
      { method: 'PUT', path: '/auth/me', auth: true, desc: 'Update own profile (name, email, password)' },
    ],
  },
  {
    group: 'Azure SSO',
    color: '#3b82f6',
    endpoints: [
      { method: 'GET', path: '/sso/config', auth: false, desc: 'Get SSO auth URL for login page' },
      { method: 'POST', path: '/sso/callback', auth: false, desc: 'Exchange Azure auth code for JWT' },
    ],
  },
  {
    group: 'Sites',
    color: '#8b5cf6',
    endpoints: [
      { method: 'GET', path: '/sites/', auth: true, desc: 'List all sites with status' },
      { method: 'GET', path: '/sites/{id}', auth: true, desc: 'Get site detail with pages' },
      { method: 'POST', path: '/sites/', auth: true, desc: 'Create new site' },
      { method: 'PUT', path: '/sites/{id}', auth: true, desc: 'Update site config' },
      { method: 'DELETE', path: '/sites/{id}', auth: true, desc: 'Delete site + cascade alerts' },
      { method: 'GET', path: '/sites/{id}/credentials', auth: true, desc: 'Get site credential config (no secrets)' },
      { method: 'GET', path: '/sites/debug', auth: false, desc: 'Debug: raw site data without auth' },
    ],
  },
  {
    group: 'Site Groups',
    color: '#f59e0b',
    endpoints: [
      { method: 'GET', path: '/groups/', auth: true, desc: 'List all groups with site counts' },
      { method: 'GET', path: '/groups/{id}', auth: true, desc: 'Group detail with site list' },
      { method: 'GET', path: '/groups/{id}/credentials', auth: true, desc: 'Group credential config' },
      { method: 'POST', path: '/groups/', auth: true, admin: true, desc: 'Create group with shared credentials' },
      { method: 'PUT', path: '/groups/{id}', auth: true, admin: true, desc: 'Update group' },
      { method: 'DELETE', path: '/groups/{id}', auth: true, admin: true, desc: 'Delete group' },
    ],
  },
  {
    group: 'Monitoring',
    color: '#ef4444',
    endpoints: [
      { method: 'POST', path: '/monitoring/results', auth: false, desc: 'Submit check result (from engine)' },
      { method: 'POST', path: '/monitoring/trigger/{site_id}', auth: true, desc: 'Manually trigger a check' },
      { method: 'GET', path: '/monitoring/results/{site_id}', auth: true, desc: 'Get check results for site' },
      { method: 'GET', path: '/monitoring/sites-status', auth: true, desc: 'All sites with latest status' },
      { method: 'GET', path: '/monitoring/dashboard', auth: true, desc: 'Dashboard summary stats' },
      { method: 'GET', path: '/monitoring/slowness-analysis', auth: true, desc: 'Slowness analysis (>60min windows)' },
      { method: 'GET', path: '/monitoring/iis-diagnostics/{site_id}', auth: true, desc: 'IIS/App Pool diagnostics + recommendations' },
      { method: 'GET', path: '/monitoring/daily-report/preview', auth: true, desc: 'Preview daily report data' },
      { method: 'POST', path: '/monitoring/daily-report/send', auth: true, admin: true, desc: 'Manually send daily report' },
    ],
  },
  {
    group: 'Alerts',
    color: '#dc2626',
    endpoints: [
      { method: 'GET', path: '/monitoring/alerts-raw', auth: true, desc: 'Active alerts (bypasses Pydantic)' },
      { method: 'GET', path: '/monitoring/alert-history-raw', auth: true, desc: 'Full alert history' },
      { method: 'POST', path: '/monitoring/alerts/{id}/resolve', auth: true, desc: 'Resolve an alert' },
      { method: 'POST', path: '/monitoring/alerts/acknowledge', auth: true, desc: 'Acknowledge + send Teams notification' },
      { method: 'DELETE', path: '/monitoring/alerts/history', auth: true, admin: true, desc: 'Delete resolved alert history' },
      { method: 'GET', path: '/monitoring/alerts/debug', auth: false, desc: 'Debug: raw alert data' },
    ],
  },
  {
    group: 'False Positives',
    color: '#f97316',
    endpoints: [
      { method: 'POST', path: '/monitoring/alerts/{id}/false-positive', auth: true, admin: true, desc: 'Mark as false positive + create suppression rule' },
      { method: 'POST', path: '/monitoring/alerts/{id}/restore', auth: true, admin: true, desc: 'Restore false positive alert' },
      { method: 'GET', path: '/monitoring/false-positives', auth: true, desc: 'Get FP alerts + active rules' },
      { method: 'DELETE', path: '/monitoring/false-positive-rules/{id}', auth: true, admin: true, desc: 'Delete suppression rule' },
    ],
  },
  {
    group: 'Security Scanning',
    color: '#7c3aed',
    endpoints: [
      { method: 'POST', path: '/security/scan/{site_id}', auth: true, desc: 'Run DAST security scan' },
      { method: 'GET', path: '/security/scans/{site_id}', auth: true, desc: 'Scan history for site' },
      { method: 'GET', path: '/security/scans/{site_id}/latest', auth: true, desc: 'Latest scan with findings' },
      { method: 'GET', path: '/security/dashboard', auth: true, desc: 'Security overview across all sites' },
    ],
  },
  {
    group: 'Compliance',
    color: '#059669',
    endpoints: [
      { method: 'GET', path: '/security/compliance/frameworks', auth: true, desc: 'List frameworks with compliance %' },
      { method: 'GET', path: '/security/compliance/frameworks/{id}', auth: true, desc: 'Framework controls detail' },
      { method: 'PUT', path: '/security/compliance/controls/{id}', auth: true, desc: 'Update control status/evidence' },
      { method: 'POST', path: '/security/compliance/seed', auth: true, admin: true, desc: 'Seed SOC 2 + GDPR frameworks' },
    ],
  },
  {
    group: 'Kubernetes',
    color: '#2563eb',
    endpoints: [
      { method: 'GET', path: '/k8s/clusters', auth: true, desc: 'List clusters with latest status' },
      { method: 'POST', path: '/k8s/clusters', auth: true, admin: true, desc: 'Add K8s cluster' },
      { method: 'GET', path: '/k8s/clusters/{id}', auth: true, desc: 'Cluster detail (nodes, pods, events)' },
      { method: 'PUT', path: '/k8s/clusters/{id}', auth: true, admin: true, desc: 'Update cluster config' },
      { method: 'DELETE', path: '/k8s/clusters/{id}', auth: true, admin: true, desc: 'Delete cluster' },
      { method: 'GET', path: '/k8s/clusters/{id}/alerts', auth: true, desc: 'Cluster K8s alerts' },
      { method: 'POST', path: '/k8s/clusters/{id}/alerts/{aid}/resolve', auth: true, desc: 'Resolve K8s alert' },
      { method: 'GET', path: '/k8s/clusters/{id}/history', auth: true, desc: 'Cluster snapshot history' },
    ],
  },
  {
    group: 'Admin — Users',
    color: '#64748b',
    endpoints: [
      { method: 'GET', path: '/admin/users', auth: true, admin: true, desc: 'List all users' },
      { method: 'POST', path: '/admin/users', auth: true, admin: true, desc: 'Create user' },
      { method: 'PUT', path: '/admin/users/{id}', auth: true, admin: true, desc: 'Update user (role, status, password)' },
      { method: 'DELETE', path: '/admin/users/{id}', auth: true, admin: true, desc: 'Delete user' },
    ],
  },
  {
    group: 'Admin — Settings',
    color: '#475569',
    endpoints: [
      { method: 'GET', path: '/admin/settings', auth: true, admin: true, desc: 'Get SMTP/Teams config' },
      { method: 'PUT', path: '/admin/settings/smtp', auth: true, admin: true, desc: 'Update SMTP settings' },
      { method: 'PUT', path: '/admin/settings/teams', auth: true, admin: true, desc: 'Update Teams webhook' },
      { method: 'POST', path: '/admin/settings/smtp/test', auth: true, admin: true, desc: 'Send test email' },
      { method: 'POST', path: '/admin/settings/teams/test', auth: true, admin: true, desc: 'Send test Teams message' },
      { method: 'GET', path: '/admin/settings/sso', auth: true, admin: true, desc: 'Get Azure SSO config' },
      { method: 'PUT', path: '/admin/settings/sso', auth: true, admin: true, desc: 'Update Azure SSO settings' },
      { method: 'POST', path: '/admin/alarm-audio', auth: true, admin: true, desc: 'Upload custom alarm audio' },
      { method: 'DELETE', path: '/admin/alarm-audio', auth: true, admin: true, desc: 'Delete custom alarm audio' },
      { method: 'GET', path: '/admin/alarm-audio/info', auth: true, admin: true, desc: 'Check if custom audio exists' },
      { method: 'GET', path: '/admin/alarm-audio/file', auth: false, desc: 'Serve alarm audio file' },
    ],
  },
];

const METHOD_COLORS = { GET: '#10b981', POST: '#3b82f6', PUT: '#f59e0b', DELETE: '#ef4444' };

export default function ApiDocs() {
  const [filter, setFilter] = useState('');
  const [expandedGroup, setExpandedGroup] = useState(null);

  const totalEndpoints = ENDPOINTS.reduce((s, g) => s + g.endpoints.length, 0);
  const filtered = filter
    ? ENDPOINTS.map(g => ({ ...g, endpoints: g.endpoints.filter(e => e.path.toLowerCase().includes(filter.toLowerCase()) || e.desc.toLowerCase().includes(filter.toLowerCase())) })).filter(g => g.endpoints.length > 0)
    : ENDPOINTS;

  return (
    <div>
      <div className="page-header">
        <h2>API Documentation</h2>
        <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{totalEndpoints} endpoints | Base: /api/v1</span>
      </div>

      <div className="card" style={{ marginBottom: '20px', padding: '16px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Search endpoints..." style={{ flex: 1, padding: '10px 14px', border: '1px solid var(--color-border)', borderRadius: 'var(--radius)', fontSize: '14px' }} />
          <div style={{ display: 'flex', gap: '6px', fontSize: '11px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} /> Auth required</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', display: 'inline-block' }} /> Admin only</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: 8, height: 8, borderRadius: '50%', background: '#94a3b8', display: 'inline-block' }} /> Public</span>
          </div>
        </div>
      </div>

      {filtered.map(group => (
        <div key={group.group} className="card" style={{ marginBottom: '12px' }}>
          <div onClick={() => setExpandedGroup(expandedGroup === group.group ? null : group.group)} style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', marginBottom: expandedGroup === group.group ? '12px' : 0 }}>
            <div style={{ width: 28, height: 28, borderRadius: '6px', background: group.color, color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 700 }}>{group.endpoints.length}</div>
            <h3 style={{ flex: 1, fontSize: '14px', fontWeight: 700 }}>{group.group}</h3>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', transform: expandedGroup === group.group ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>&#9660;</span>
          </div>

          {expandedGroup === group.group && (
            <div className="table-container">
              <table>
                <thead><tr><th style={{ width: '70px' }}>Method</th><th>Endpoint</th><th>Auth</th><th>Description</th></tr></thead>
                <tbody>
                  {group.endpoints.map((e, i) => (
                    <tr key={i}>
                      <td><span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'white', background: METHOD_COLORS[e.method] || '#94a3b8' }}>{e.method}</span></td>
                      <td><code style={{ fontSize: '12px', background: 'var(--color-bg)', padding: '2px 6px', borderRadius: '4px' }}>/api/v1{e.path}</code></td>
                      <td>
                        {e.admin ? <span className="badge badge-critical" style={{ fontSize: '9px' }}>Admin</span>
                          : e.auth ? <span className="badge badge-ok" style={{ fontSize: '9px' }}>Auth</span>
                          : <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>Public</span>}
                      </td>
                      <td style={{ fontSize: '12px' }}>{e.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
