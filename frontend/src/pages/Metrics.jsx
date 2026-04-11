export default function Metrics() {
  const rules = [
    {
      title: 'Uptime Check',
      icon: '\u2191',
      color: '#007aff',
      items: [
        { label: 'Method', value: 'Headless Chromium browser (Playwright) loads the full page' },
        { label: 'Measures', value: 'Page load time (domcontentloaded) + Performance API metrics' },
        { label: 'HTTP 404', value: 'Instant CRITICAL alert' },
        { label: 'HTTP 5XX', value: 'Instant CRITICAL alert (500, 501, 502, 503, 504)' },
        { label: 'HTTP 4XX (other)', value: 'Instant CRITICAL alert' },
        { label: 'Timeout', value: 'CRITICAL alert if page does not load within 30 seconds' },
        { label: 'Perf Metrics', value: 'Captures TTFB, DOM load, FCP, resource counts, transfer size' },
        { label: 'Success', value: 'HTTP 200-399 with page loaded = OK' },
      ],
    },
    {
      title: 'Login Validation',
      icon: '\uD83D\uDD12',
      color: '#13612e',
      items: [
        { label: 'Method', value: 'Fills username/password, clicks submit, waits for page load + network idle' },
        { label: 'Field Error Handling', value: 'If username/password field not found — clean error with selector name' },
        { label: 'Password Field Check', value: 'If password input still visible after submit = CRITICAL' },
        { label: 'Error Detection', value: 'Scans for .error, .alert-danger, [role=alert], red spans, error keywords' },
        { label: 'Error Keywords', value: '"invalid", "incorrect", "failed", "denied", "wrong password", "try again", "account locked"' },
        { label: 'DB Issue Detection', value: 'Scans page for SQL Server errors, timeouts, deadlocks, connection failures' },
        { label: 'Backend Latency', value: 'If login takes >15s, flags as DATABASE ISSUE (LATENCY). 8-15s adds latency note' },
        { label: 'Expected Page', value: 'Verifies URL contains expected page after login (default: mainpage.aspx)' },
        { label: 'CSS Selector', value: 'Supports all formats: #id, .class, tag#id, ul#breadcrumbs, div.class, input[attr]' },
        { label: 'Post-Login Fallback', value: 'If CSS selector not found but URL has expected page = OK' },
        { label: 'SSO Backdoor', value: 'Use direct login URL for SSO sites (bypasses SSO flow)' },
        { label: 'Response Time', value: 'Measures submit-to-page-load only (excludes JS rendering buffer)' },
      ],
    },
    {
      title: 'Subpage Validation',
      icon: '\uD83D\uDCC4',
      color: '#6b46c1',
      items: [
        { label: 'Prerequisite', value: 'Subpages only execute after login is confirmed successful' },
        { label: 'Method', value: 'After login, navigates each configured subpage in sort order' },
        { label: 'HTTP Status', value: 'Fails immediately on 4XX/5XX responses' },
        { label: 'Login Redirect', value: 'Detects if page redirected to login/signin/auth = CRITICAL (session expired)' },
        { label: 'Error Page', value: 'Detects if URL contains "error", "404", "not-found" = CRITICAL' },
        { label: 'URL Path Match', value: 'Compares expected vs actual path — warns on mismatch (catches SPA wrong routes)' },
        { label: 'CSS Selector', value: 'Supports all CSS formats (tag#id, div.class etc). Auto-normalizes. Missing = CRITICAL' },
        { label: 'Expected Text', value: 'Text must be in page content. Missing = WARNING' },
        { label: 'Empty Page Check', value: 'If no CSS/text set and body has <50 chars = WARNING (likely error page)' },
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
        { label: 'Default Threshold', value: '10,000ms (10 seconds)' },
        { label: 'Options', value: '2s, 3s, 5s, 8s, 10s (default), 15s, 20s, 30s' },
        { label: 'Alert Level', value: 'WARNING — site is up but slow' },
        { label: 'Sustained Check', value: 'Alert only if ALL checks in the past 15 minutes exceed threshold' },
        { label: 'Minimum Data', value: 'Requires at least 2 data points before alerting' },
        { label: 'Cooldown', value: '3 hours between slow alerts per site (no repeated emails/Teams)' },
        { label: 'Consolidated Alert', value: 'One email/Teams for ALL slow sites together (not per-site)' },
        { label: 'Deduplication', value: 'One alert per site — subsequent slow checks update existing alert, no new record' },
        { label: 'Measurement', value: 'Submit-to-page-load + network idle (excludes JS buffer waits)' },
        { label: 'Recovery', value: 'Auto-resolves when response drops below threshold' },
        { label: 'Dashboard Analysis', value: 'Shows slow periods >60 min with hourly bar charts in CST' },
      ],
    },
    {
      title: 'Database / SQL Server Detection',
      icon: '\uD83D\uDDC4',
      color: '#c53030',
      items: [
        { label: 'SQL Timeout', value: '"execution timeout expired", "wait operation timed out" → CRITICAL (timeout)' },
        { label: 'Connection Failure', value: '"cannot open database", "network-related error", "max pool size" → CRITICAL (connection)' },
        { label: 'Deadlock', value: '"transaction was deadlocked" → CRITICAL (deadlock)' },
        { label: 'DB Auth Failure', value: '"login failed for user" → CRITICAL (db_auth)' },
        { label: 'ASP.NET Errors', value: '"server error in", "runtime error", "stack trace" → CRITICAL (sql_error)' },
        { label: 'Severe Latency', value: 'Login response >15s → CRITICAL "Severe backend latency — likely SQL Server delays"' },
        { label: 'Moderate Latency', value: 'Login response 8-15s → Note appended: "POSSIBLE DB LATENCY"' },
        { label: 'Bottleneck Analysis', value: 'TTFB vs total load — identifies backend/database vs frontend/rendering bottleneck' },
        { label: 'Backend % Metric', value: 'Shows % of load time spent on server. Red >70%, Orange >50%, Green <50%' },
      ],
    },
    {
      title: 'Alert Triggers',
      icon: '\uD83D\uDD14',
      color: '#e53e3e',
      items: [
        { label: 'HTTP 404 / 5XX', value: 'Instant CRITICAL alert on first occurrence' },
        { label: 'Login Failure', value: 'Instant CRITICAL when password field visible or error detected' },
        { label: 'Database Issue', value: 'Instant CRITICAL with category (timeout/connection/deadlock/latency)' },
        { label: 'Subpage Failure', value: 'CRITICAL if element missing or redirected to login/error page' },
        { label: 'Slowness', value: 'WARNING after 15 min sustained, consolidated, 3-hour cooldown' },
        { label: 'Recovery', value: 'Instant OK notification + auto-resolve when site comes back' },
        { label: 'Duplicate Prevention', value: 'One active alert per site — new failures update existing alert' },
        { label: 'Orphan Cleanup', value: 'Alerts for deleted sites auto-resolve and are hidden from UI' },
      ],
    },
    {
      title: 'Notification Channels',
      icon: '\uD83D\uDCE7',
      color: '#007aff',
      items: [
        { label: 'Email (SMTP)', value: 'Configurable in Admin > Settings — sent to per-site notification emails' },
        { label: 'MS Teams', value: 'Global webhook — fires if configured and enabled. ON/OFF toggle in settings' },
        { label: 'Teams Acknowledge', value: 'When alarm is silenced, Teams gets "Alert Acknowledged by [name]" with down/slow breakdown' },
        { label: 'Dashboard Alarm', value: 'Audio alarm + red/orange banner + toast popups on all pages' },
        { label: 'Alarm Audio', value: 'Upload custom MP3/WAV/OGG in Admin > Settings, or uses default generated tone' },
        { label: 'Critical Only Sound', value: 'Audio alarm plays only for CRITICAL (down) — not for warnings (slow)' },
        { label: 'Warning Banner', value: 'Orange banner for slow sites — auto-hides after 30 seconds' },
        { label: 'Toast Behavior', value: 'New alerts: instant toast. Ongoing: repeats every 30 minutes. No spam on page refresh' },
        { label: 'Toast Auto-Dismiss', value: '5 seconds' },
        { label: 'Admin Notifications', value: 'All admins emailed when sites are added or removed' },
        { label: 'Recovery Email', value: 'Green-themed email/Teams when site comes back online' },
      ],
    },
  ];

  const timing = [
    {
      title: 'Check Scheduling',
      icon: '\u23F0',
      color: '#38a169',
      items: [
        { label: 'Scheduler', value: 'Built-in async background task inside the FastAPI backend' },
        { label: 'Tick Interval', value: 'Every 15 seconds checks which sites are due' },
        { label: 'Check Intervals', value: '1 min, 3 min, 5 min, 10 min, 15 min, 30 min, 60 min' },
        { label: 'Manual Trigger', value: '"Run Check Now" button on site detail page' },
        { label: 'Dashboard Refresh', value: 'Auto-refresh every 15 seconds with live countdown timer' },
        { label: 'Next Check Timer', value: 'Live per-site countdown on the dashboard' },
        { label: 'Alert Polling', value: 'AlertMonitor polls every 10 seconds (global, all pages)' },
      ],
    },
    {
      title: 'Performance Metrics',
      icon: '\u26A1',
      color: '#fc5c1d',
      items: [
        { label: 'Source', value: 'Browser Performance API (Navigation Timing, Resource Timing, Paint Timing)' },
        { label: 'TTFB', value: 'Time to First Byte — server processing + network latency' },
        { label: 'DOM Loaded', value: 'DOMContentLoaded event time — HTML parsed + sync scripts done' },
        { label: 'DOM Complete', value: 'All resources (images, CSS, JS) finished loading' },
        { label: 'Total Load', value: 'Load event end — complete page ready' },
        { label: 'First Paint / FCP', value: 'First pixel rendered / First meaningful content visible' },
        { label: 'DNS / TCP / TLS', value: 'Network connection breakdown — diagnose connectivity issues' },
        { label: 'Slow Resources', value: 'Resources taking >1 second (scripts, CSS, images) with name, type, duration' },
        { label: 'Slow API Calls', value: 'XHR/Fetch requests taking >2 seconds with endpoint URL and duration' },
        { label: 'Failed Resources', value: 'Resources with 4XX/5XX status codes' },
        { label: 'Backend % Metric', value: 'TTFB as percentage of total load — indicates server vs client bottleneck' },
        { label: 'Bottleneck Analysis', value: 'Auto-detects if delay is backend/database (TTFB >5s) or frontend/rendering' },
        { label: 'Region', value: 'Geographic region where check runs (configurable via MONITOR_REGION env var)' },
        { label: 'Browser', value: 'Chromium headless via Playwright (same engine as Chrome)' },
      ],
    },
    {
      title: 'Security & Auth',
      icon: '\uD83D\uDD10',
      color: '#001e3f',
      items: [
        { label: 'Site Credentials', value: 'Fernet AES-128 encrypted at rest (username + password)' },
        { label: 'SMTP Password', value: 'Fernet AES-128 encrypted in system_settings table' },
        { label: 'Teams Webhook', value: 'Fernet AES-128 encrypted in system_settings table' },
        { label: 'Azure SSO Secret', value: 'Fernet AES-128 encrypted in system_settings table' },
        { label: 'User Passwords', value: 'bcrypt hashed (one-way, cannot be decrypted)' },
        { label: 'API Auth', value: 'JWT Bearer tokens with configurable expiry' },
        { label: 'Azure SSO', value: 'Optional Entra ID integration with group-based admin/user role mapping' },
        { label: 'Registration', value: 'Locked after first user — only admins can create accounts' },
        { label: 'Profile', value: 'Users can change name, email, password. Cannot change own admin status' },
      ],
    },
  ];

  const defaults = [
    { setting: 'Slow Response Threshold', value: '10,000ms (10 seconds)', where: 'Per site, configurable' },
    { setting: 'Sustained Slowness Period', value: '15 minutes', where: 'Before sending slow alert' },
    { setting: 'Slow Alert Cooldown', value: '3 hours', where: 'Between repeated slow alerts per site' },
    { setting: 'Slow Alert Dedup', value: '1 per site', where: 'Updates existing alert, no duplicates' },
    { setting: 'Slowness Dashboard Chart', value: '>60 minutes', where: 'Show in slowness analysis section' },
    { setting: 'DB Latency Severe', value: '>15,000ms', where: 'Flags as DATABASE ISSUE (CRITICAL)' },
    { setting: 'DB Latency Moderate', value: '8,000-15,000ms', where: 'Appends latency note to alert' },
    { setting: 'Backend Bottleneck', value: 'TTFB >5,000ms', where: 'Flags as backend/database bottleneck' },
    { setting: 'Frontend Bottleneck', value: 'Render time >5,000ms', where: 'Flags as frontend/rendering bottleneck' },
    { setting: 'Expected Post-Login Page', value: 'mainpage.aspx', where: 'Per site, configurable' },
    { setting: 'Browser Timeout', value: '30 seconds', where: 'Page load timeout' },
    { setting: 'Monitor Region', value: 'US-Central', where: 'MONITOR_REGION env var on engine' },
    { setting: 'Scheduler Tick', value: '15 seconds', where: 'How often scheduler checks for due sites' },
    { setting: 'Alert Poll Interval', value: '10 seconds', where: 'Frontend checks for new alerts' },
    { setting: 'Dashboard Refresh', value: '15 seconds', where: 'Auto-refresh all dashboard data' },
    { setting: 'Toast Repeat Interval', value: '30 minutes', where: 'Repeat toast for ongoing alerts' },
    { setting: 'Toast Auto-Dismiss', value: '5 seconds', where: 'Popup notifications' },
    { setting: 'Warning Banner Auto-Hide', value: '30 seconds', where: 'Orange slow/warning banner' },
    { setting: 'Alarm Repeat', value: '4 seconds', where: 'Sound beep interval during critical alerts' },
    { setting: 'Check Interval Default', value: '5 minutes', where: 'New site default' },
    { setting: 'Slow Resource Threshold', value: '>1 second', where: 'Flagged in perf metrics' },
    { setting: 'Slow API Call Threshold', value: '>2 seconds', where: 'Flagged in perf metrics' },
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
          The monitoring engine uses a <strong>headless Chromium browser (Playwright)</strong> to perform real user simulations
          from <strong>{'{MONITOR_REGION}'}</strong>. For each site, it loads pages, fills login forms, navigates subpages, and collects
          <strong> detailed performance metrics</strong> (TTFB, DOM load, FCP, resource timing) via the browser Performance API.
          It detects <strong>SQL Server issues</strong> (timeouts, deadlocks, connection failures) and identifies whether slowness
          is caused by <strong>backend/database</strong> or <strong>frontend/rendering</strong>.
          Alerts fire instantly on failures. Slowness alerts require <strong>15 min sustained</strong>, are sent as a
          <strong> single consolidated email/Teams</strong> with a <strong>3-hour cooldown</strong>.
        </p>
      </div>

      {renderSection('Check Types', rules)}
      {renderSection('Thresholds, Detection & Alerts', thresholds)}
      {renderSection('Scheduling, Metrics & Security', timing)}

      {/* Default Values Table */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header"><h3>Default Values & Thresholds</h3></div>
        <div className="table-container">
          <table>
            <thead>
              <tr><th>Setting</th><th>Default Value</th><th>Context</th></tr>
            </thead>
            <tbody>
              {defaults.map((d, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 500, fontSize: '13px' }}>{d.setting}</td>
                  <td style={{ fontVariantNumeric: 'tabular-nums', fontSize: '13px', fontWeight: 600, color: 'var(--color-primary)' }}>{d.value}</td>
                  <td style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{d.where}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alert Status Reference */}
      <div className="card">
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>Alert Status Reference</h3>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          {[
            { badge: 'ok', label: 'OK', desc: 'Site is up, fast, all checks pass' },
            { badge: 'warning', label: 'WARNING', desc: 'Site slow (sustained >15min), text missing, URL mismatch, or moderate DB latency' },
            { badge: 'critical', label: 'CRITICAL', desc: 'Site down, login failed, HTTP 4XX/5XX, DB timeout/deadlock/connection, or severe latency (>15s)' },
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
