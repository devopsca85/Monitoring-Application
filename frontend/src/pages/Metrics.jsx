export default function Metrics() {
  const rules = [
    {
      title: 'Uptime Check',
      icon: '\u2191',
      color: '#007aff',
      items: [
        { label: 'Method', value: 'Headless browser (Playwright) loads the full page' },
        { label: 'Measures', value: 'Page load time (domcontentloaded)' },
        { label: 'HTTP 404', value: 'Instant CRITICAL alert' },
        { label: 'HTTP 5XX', value: 'Instant CRITICAL alert (500, 501, 502, 503, 504)' },
        { label: 'HTTP 4XX (other)', value: 'Instant CRITICAL alert' },
        { label: 'Timeout', value: 'CRITICAL alert if page does not load within 30 seconds' },
        { label: 'Success', value: 'HTTP 200-399 with page loaded = OK' },
      ],
    },
    {
      title: 'Login Validation',
      icon: '\uD83D\uDD12',
      color: '#13612e',
      items: [
        { label: 'Method', value: 'Headless browser fills username/password, clicks submit, waits for redirect' },
        { label: 'Login Failed Detection', value: 'Password field still visible after submit = CRITICAL' },
        { label: 'Error Message Detection', value: 'Scans for "invalid", "incorrect", "failed", "denied" text on page' },
        { label: 'Error Element Detection', value: 'Checks .error, .alert-danger, [role=alert], red span elements' },
        { label: 'Expected Page Check', value: 'Verifies URL contains the expected page (default: mainpage.aspx)' },
        { label: 'CSS Selector Check', value: 'If success indicator is set, verifies element exists in DOM' },
        { label: 'Fallback', value: 'If CSS selector not found but expected page is in URL = OK' },
        { label: 'SSO Backdoor', value: 'Use the direct login URL for sites with SSO (bypasses SSO flow)' },
      ],
    },
    {
      title: 'Multi-Page Validation',
      icon: '\uD83D\uDCC4',
      color: '#6b46c1',
      items: [
        { label: 'Method', value: 'Login first, then navigate each configured subpage in order' },
        { label: 'Element Check', value: 'Expected CSS element must exist on each page' },
        { label: 'Text Check', value: 'Expected text must be present in page content' },
        { label: 'Per-Page Status', value: 'Each subpage gets its own OK/WARNING/CRITICAL status' },
        { label: 'Overall Status', value: 'Worst subpage status becomes the overall result' },
      ],
    },
  ];

  const thresholds = [
    {
      title: 'Response Time (Slowness)',
      icon: '\u23F1',
      color: '#dd6b20',
      items: [
        { label: 'Threshold', value: 'Configurable per site (default: 10000ms / 10 seconds)' },
        { label: 'Options', value: '2s, 3s, 5s, 8s (default), 10s, 15s, 20s, 30s' },
        { label: 'Alert Level', value: 'WARNING — site is up but slow' },
        { label: 'Measurement', value: 'Time from form submit to page load + network idle (excludes JS rendering buffer)' },
        { label: 'Recovery', value: 'Auto-resolves when response drops below threshold' },
      ],
    },
    {
      title: 'Alert Triggers',
      icon: '\uD83D\uDD14',
      color: '#e53e3e',
      items: [
        { label: 'HTTP 404 / 5XX', value: 'Instant alert on first occurrence (no waiting)' },
        { label: 'Login Failure', value: 'Instant alert when wrong credentials or login form still showing' },
        { label: 'Slowness', value: 'WARNING alert when response exceeds threshold' },
        { label: 'Subpage Failure', value: 'CRITICAL if expected element missing, WARNING if expected text missing' },
        { label: 'Recovery', value: 'Instant OK alert + auto-resolve when site comes back' },
        { label: 'Duplicate Prevention', value: 'One active alert per site — new failures update existing alert' },
      ],
    },
    {
      title: 'Notification Channels',
      icon: '\uD83D\uDCE7',
      color: '#007aff',
      items: [
        { label: 'Email (SMTP)', value: 'Configurable in Admin > Settings — sent to site notification emails' },
        { label: 'MS Teams', value: 'Global webhook — always fires if configured, regardless of site channel' },
        { label: 'Dashboard Alarm', value: 'Sound alarm + red banner + toast popup when admin is on dashboard' },
        { label: 'Admin Notifications', value: 'All admins notified when sites are added or removed' },
        { label: 'Recovery Email', value: 'Green-themed email when site comes back online' },
      ],
    },
  ];

  const timing = [
    {
      title: 'Check Scheduling',
      icon: '\u23F0',
      color: '#38a169',
      items: [
        { label: 'Scheduler', value: 'Built-in background scheduler (runs inside the backend)' },
        { label: 'Tick Interval', value: 'Every 15 seconds the scheduler checks which sites are due' },
        { label: 'Check Intervals', value: '1 min, 3 min, 5 min, 10 min, 15 min, 30 min, 60 min' },
        { label: 'Manual Trigger', value: '"Run Check Now" button on site detail page' },
        { label: 'Dashboard Refresh', value: 'Auto-refresh every 15 seconds with live countdown' },
      ],
    },
    {
      title: 'Response Time Measurement',
      icon: '\u26A1',
      color: '#fc5c1d',
      items: [
        { label: 'Uptime Check', value: 'Time from navigation start to domcontentloaded' },
        { label: 'Login Check', value: 'Time from submit click to page load + network idle' },
        { label: 'Excludes', value: 'JS rendering buffer (2s) and indicator retry waits are NOT counted' },
        { label: 'Subpage Time', value: 'Each subpage measured independently from navigation to load' },
        { label: 'Browser', value: 'Chromium headless via Playwright (same engine as Chrome)' },
      ],
    },
    {
      title: 'Security',
      icon: '\uD83D\uDD10',
      color: '#001e3f',
      items: [
        { label: 'Site Credentials', value: 'Fernet AES-128 encrypted at rest (username + password)' },
        { label: 'SMTP Password', value: 'Fernet AES-128 encrypted in system_settings table' },
        { label: 'Teams Webhook', value: 'Fernet AES-128 encrypted in system_settings table' },
        { label: 'User Passwords', value: 'bcrypt hashed (one-way, cannot be decrypted)' },
        { label: 'API Auth', value: 'JWT Bearer tokens with configurable expiry' },
        { label: 'Registration', value: 'Locked after first user — only admins can create accounts' },
      ],
    },
  ];

  const renderSection = (title, groups) => (
    <div style={{ marginBottom: '32px' }}>
      <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px', color: 'var(--color-text)' }}>{title}</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
        {groups.map((group) => (
          <div key={group.title} className="card" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: 36, height: 36, borderRadius: '8px', background: group.color,
                color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '18px', flexShrink: 0,
              }}>
                {group.icon}
              </div>
              <h4 style={{ fontSize: '15px', fontWeight: 600 }}>{group.title}</h4>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {group.items.map((item, i) => (
                  <tr key={i} style={{ borderBottom: i < group.items.length - 1 ? '1px solid var(--color-border)' : 'none' }}>
                    <td style={{ padding: '8px 8px 8px 0', fontSize: '12px', fontWeight: 600, color: 'var(--color-text)', whiteSpace: 'nowrap', verticalAlign: 'top', width: '35%' }}>
                      {item.label}
                    </td>
                    <td style={{ padding: '8px 0', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                      {item.value}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h2>Monitoring Metrics & Rules</h2>
      </div>

      <div className="card" style={{ background: 'linear-gradient(135deg, #001e3f, #003366)', color: 'white', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>How This Monitoring App Works</h3>
        <p style={{ fontSize: '13px', opacity: 0.85, lineHeight: 1.7 }}>
          The monitoring engine uses a <strong>headless Chromium browser (Playwright)</strong> to perform real user simulations.
          For each configured site, it loads the page, fills login forms, clicks buttons, and navigates subpages — exactly like a real user would.
          Response times measure <strong>actual page load speed</strong>, not just HTTP pings.
          Alerts fire instantly on failures and auto-resolve on recovery.
        </p>
      </div>

      {renderSection('Check Types', rules)}
      {renderSection('Thresholds & Alerts', thresholds)}
      {renderSection('Scheduling & Security', timing)}

      <div className="card" style={{ marginTop: '8px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>Alert Status Reference</h3>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          {[
            { badge: 'ok', label: 'OK', desc: 'Site is up, fast, and all checks pass' },
            { badge: 'warning', label: 'WARNING', desc: 'Site is up but slow (exceeds threshold) or minor issue' },
            { badge: 'critical', label: 'CRITICAL', desc: 'Site is down, login failed, HTTP error, or page missing' },
          ].map((s) => (
            <div key={s.badge} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className={`badge badge-${s.badge}`} style={{ fontSize: '12px' }}>{s.label}</span>
              <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{s.desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
