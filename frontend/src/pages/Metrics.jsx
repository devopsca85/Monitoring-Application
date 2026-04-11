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
        { label: 'Perf Metrics', value: 'TTFB, DOM load, FCP, resource counts, transfer size, slow resources' },
        { label: 'IIS Diagnostics', value: 'Scans for 503/502/401/403 errors, app pool issues, config errors' },
        { label: 'Success', value: 'HTTP 200-399 with page loaded = OK' },
      ],
    },
    {
      title: 'Login Validation',
      icon: '\uD83D\uDD12',
      color: '#13612e',
      items: [
        { label: 'Method', value: 'Fills username/password, clicks submit, waits for page load + network idle' },
        { label: 'Submit Tracking', value: 'Logs navigation success/failure — detects form submit issues' },
        { label: 'Field Error', value: 'If username/password field not found — clean error with selector name' },
        { label: 'Password Check', value: 'If password input still visible after submit = CRITICAL' },
        { label: 'Error Detection', value: 'Scans .error, .alert-danger, [role=alert], red spans, 25+ keywords' },
        { label: 'Error Page Redirect', value: 'Detects GenericError.aspx, Error.aspx, 500.aspx, maintenance pages' },
        { label: 'DB Issue Detection', value: 'SQL timeout, deadlock, connection pool, ASP.NET stack traces' },
        { label: 'Backend Latency', value: '>15s = DATABASE ISSUE (CRITICAL). 8-15s = latency note appended' },
        { label: 'Expected Page', value: 'Verifies URL contains expected page (default: mainpage.aspx)' },
        { label: 'CSS Selector', value: 'All formats: #id, .class, tag#id, ul#breadcrumbs, div.class, input[attr]' },
        { label: 'Indicator Logic', value: 'If set and not found: fail (not silent pass). On expected page: warn + OK' },
        { label: 'SSO Backdoor', value: 'Use direct login URL for SSO sites' },
        { label: 'Response Time', value: 'Submit-to-network-idle only. JS buffer and retries excluded' },
        { label: 'IIS Diagnostics', value: 'Full IIS/App Pool analysis after login (cold starts, crashes, thread starvation)' },
      ],
    },
    {
      title: 'Subpage Validation',
      icon: '\uD83D\uDCC4',
      color: '#6b46c1',
      items: [
        { label: 'Prerequisite', value: 'Only executes after login is confirmed successful' },
        { label: 'Method', value: 'Navigates each configured subpage in sort order' },
        { label: 'HTTP Status', value: '4XX/5XX = immediate CRITICAL' },
        { label: 'Login Redirect', value: 'Detects redirect to login/signin/auth = CRITICAL (session expired)' },
        { label: 'Error Page', value: 'Detects error, 404, not-found, genericerror in URL = CRITICAL' },
        { label: 'URL Path Match', value: 'Compares expected vs actual path — warns on mismatch (SPA catch)' },
        { label: 'CSS Selector', value: 'All CSS formats normalized. Missing = CRITICAL' },
        { label: 'Expected Text', value: 'Must be in page content. Missing = WARNING' },
        { label: 'Empty Page', value: 'Body <50 chars with no CSS/text checks = WARNING' },
        { label: 'Overall Status', value: 'Worst subpage status becomes the result' },
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
        { label: 'Sustained Check', value: 'All checks in the past 15 minutes must exceed threshold' },
        { label: 'Min Data Points', value: 'At least 2 results before alerting' },
        { label: 'Cooldown', value: '3 hours between slow alerts per site' },
        { label: 'Consolidated', value: 'One email/Teams for ALL slow sites together' },
        { label: 'Dedup', value: 'One alert per site — updates existing, no duplicates (FOR UPDATE lock)' },
        { label: 'Measurement', value: 'Submit-to-network-idle (excludes JS buffer, indicator retries)' },
        { label: 'Recovery', value: 'Auto-resolves when response drops below threshold' },
        { label: 'Dashboard', value: 'Slowness analysis chart for periods >60 min' },
      ],
    },
    {
      title: 'Database / SQL Server Detection',
      icon: '\uD83D\uDDC4',
      color: '#c53030',
      items: [
        { label: 'SQL Timeout', value: '"execution timeout expired", "wait operation timed out" → CRITICAL' },
        { label: 'Connection', value: '"cannot open database", "network-related error", "max pool size" → CRITICAL' },
        { label: 'Deadlock', value: '"transaction was deadlocked" → CRITICAL' },
        { label: 'DB Auth', value: '"login failed for user" → CRITICAL' },
        { label: 'ASP.NET', value: '"server error in", "runtime error", "stack trace" → CRITICAL' },
        { label: 'Severe Latency', value: '>15s response → CRITICAL with DB diagnosis' },
        { label: 'Moderate Latency', value: '8-15s → Latency note appended to alert message' },
        { label: 'Bottleneck', value: 'TTFB vs total — identifies backend/database vs frontend/rendering' },
        { label: 'Backend %', value: 'Percentage of load on server. Red >70%, Orange >50%, Green <50%' },
      ],
    },
    {
      title: 'IIS / App Pool Diagnostics',
      icon: '\u2699',
      color: '#2b6cb0',
      items: [
        { label: 'Real-Time Detection', value: 'Runs on every check — scans page for 15 IIS error categories' },
        { label: '503 App Pool Down', value: 'Detects stopped/crashed app pool → CRITICAL' },
        { label: '502 Worker Crash', value: 'Detects worker process crash/timeout → CRITICAL' },
        { label: 'Request Queue Full', value: 'Detects 503.2 queue overflow → CRITICAL' },
        { label: 'Memory Exhaustion', value: 'Detects OutOfMemoryException → CRITICAL' },
        { label: 'Cold Start', value: 'TTFB >10s with fast subsequent load → App Pool recycle detected' },
        { label: 'Thread Starvation', value: '2+ slow API calls averaging >5s → Thread pool saturation' },
        { label: 'Config/Compile Error', value: 'Detects web.config, parser, compilation errors' },
        { label: 'Auth Issues', value: '401/403 patterns → IIS authentication/permission misconfiguration' },
        { label: 'Resource Failures', value: '3+ failed resources → Static file serving misconfigured' },
      ],
    },
    {
      title: 'IIS Trend Recommendations',
      icon: '\uD83D\uDCA1',
      color: '#38a169',
      items: [
        { label: 'Analysis Period', value: '24h for current issues, 7 days for trend detection' },
        { label: 'Cold Starts (3+)', value: 'Recommend: AlwaysRunning start mode, preloadEnabled, Warm-Up module, idle timeout 0' },
        { label: 'Failures >10%', value: 'Recommend: Check Event Viewer, Rapid-Fail Protection, memory limits, recycling schedule' },
        { label: 'Slow >20%', value: 'Recommend: Profile queries, output caching, compression, maxConcurrentRequestsPerCPU, Web Garden' },
        { label: 'Error Pages (3+)', value: 'Recommend: Check Application Event Log, customErrors, deployment correlation' },
        { label: 'Worsening Trend', value: 'Recommend: Investigate deployments, resource usage, IIS logs, scaling' },
        { label: 'Trigger Threshold', value: 'Recommendations only after consistent patterns — no single-event noise' },
      ],
    },
    {
      title: 'Alert Triggers',
      icon: '\uD83D\uDD14',
      color: '#e53e3e',
      items: [
        { label: 'HTTP 404 / 5XX', value: 'Instant CRITICAL on first occurrence' },
        { label: 'Login Failure', value: 'Instant CRITICAL (password visible, error detected, wrong page)' },
        { label: 'Error Page Redirect', value: 'GenericError.aspx etc → CRITICAL with page content extraction' },
        { label: 'Database Issue', value: 'Instant CRITICAL with category (timeout/connection/deadlock/latency)' },
        { label: 'IIS App Pool', value: '503/502/memory → CRITICAL with specific IIS diagnosis' },
        { label: 'Subpage Failure', value: 'CRITICAL if element missing or redirected to login/error' },
        { label: 'Slowness', value: 'WARNING after 15min sustained, consolidated, 3h cooldown' },
        { label: 'Recovery', value: 'Instant OK notification + auto-resolve' },
        { label: 'Dedup', value: 'FOR UPDATE lock prevents race condition duplicates' },
        { label: 'Orphan Cleanup', value: 'Alerts for deleted sites auto-resolve and hidden' },
      ],
    },
    {
      title: 'Notification Channels',
      icon: '\uD83D\uDCE7',
      color: '#007aff',
      items: [
        { label: 'Email (SMTP)', value: 'Per-site notification emails, configurable in Admin > Settings' },
        { label: 'MS Teams', value: 'Global webhook, ON/OFF toggle in settings' },
        { label: 'Teams Acknowledge', value: '"Alert Acknowledged by [name]" with down/slow breakdown' },
        { label: 'Dashboard Alarm', value: 'Audio + red/orange banner + toasts on all pages' },
        { label: 'Custom Audio', value: 'Upload MP3/WAV/OGG in Admin > Settings' },
        { label: 'Critical Only Sound', value: 'Audio only for CRITICAL. Warnings = visual only' },
        { label: 'Warning Banner', value: 'Orange, auto-hides after 30 seconds' },
        { label: 'Toast Behavior', value: 'New: instant. Ongoing: repeats every 30 min. No refresh spam' },
        { label: 'Toast Dismiss', value: '5 seconds auto-dismiss' },
        { label: 'Admin Alerts', value: 'All admins emailed on site add/remove' },
        { label: 'Recovery', value: 'Green email/Teams when site recovers' },
      ],
    },
  ];

  const timing = [
    {
      title: 'Check Scheduling',
      icon: '\u23F0',
      color: '#38a169',
      items: [
        { label: 'Scheduler', value: 'Async background task in FastAPI backend' },
        { label: 'Tick', value: 'Every 15 seconds checks which sites are due' },
        { label: 'Intervals', value: '1, 3, 5, 10, 15, 30, 60 minutes' },
        { label: 'Overlap Guard', value: 'Skips if check already running for same site' },
        { label: 'Failure Retry', value: 'Resets timer on engine failure — retries next cycle' },
        { label: 'Manual', value: '"Run Check Now" on site detail page' },
        { label: 'Dashboard', value: 'Auto-refresh every 15s with countdown' },
        { label: 'Alert Poll', value: 'Global AlertMonitor polls every 10s on all pages' },
      ],
    },
    {
      title: 'Performance Metrics',
      icon: '\u26A1',
      color: '#fc5c1d',
      items: [
        { label: 'Source', value: 'Browser Performance API (Navigation, Resource, Paint Timing)' },
        { label: 'TTFB', value: 'Time to First Byte — server + network latency' },
        { label: 'DOM Loaded', value: 'DOMContentLoaded — HTML parsed + sync scripts' },
        { label: 'DOM Complete', value: 'All resources loaded' },
        { label: 'Total Load', value: 'Load event end — page fully ready' },
        { label: 'FP / FCP', value: 'First Paint, First Contentful Paint' },
        { label: 'DNS / TCP / TLS', value: 'Network breakdown for connectivity diagnosis' },
        { label: 'Slow Resources', value: '>1 second — name, type, duration, size' },
        { label: 'Slow APIs', value: '>2 seconds — endpoint URL, duration, size' },
        { label: 'Failed Resources', value: '4XX/5XX status resources listed' },
        { label: 'Backend %', value: 'TTFB as % of total — backend vs frontend bottleneck' },
        { label: 'Region', value: 'MONITOR_REGION env var (default: US-Central)' },
        { label: 'Browser', value: 'Chromium headless via Playwright' },
      ],
    },
    {
      title: 'Security & Auth',
      icon: '\uD83D\uDD10',
      color: '#001e3f',
      items: [
        { label: 'Site Credentials', value: 'Fernet AES-128 encrypted (username + password)' },
        { label: 'SMTP Password', value: 'Fernet AES-128 encrypted in system_settings' },
        { label: 'Teams Webhook', value: 'Fernet AES-128 encrypted in system_settings' },
        { label: 'Azure SSO Secret', value: 'Fernet AES-128 encrypted in system_settings' },
        { label: 'User Passwords', value: 'bcrypt hashed (one-way)' },
        { label: 'API Auth', value: 'JWT Bearer tokens with configurable expiry' },
        { label: 'Azure SSO', value: 'Entra ID with group-based admin/user role mapping' },
        { label: 'Registration', value: 'Locked after first user — admin-only creation' },
        { label: 'Profile', value: 'Self-service name, email, password change' },
        { label: 'Alert Dedup', value: 'DB-level FOR UPDATE lock prevents race condition duplicates' },
      ],
    },
  ];

  const defaults = [
    { setting: 'Slow Response Threshold', value: '10,000ms (10s)', where: 'Per site, configurable' },
    { setting: 'Sustained Slowness', value: '15 minutes', where: 'Before sending slow alert' },
    { setting: 'Slow Alert Cooldown', value: '3 hours', where: 'Between repeated alerts per site' },
    { setting: 'Slow Alert Dedup', value: '1 per site', where: 'FOR UPDATE lock, updates existing' },
    { setting: 'Slowness Chart Threshold', value: '>60 minutes', where: 'Dashboard analysis section' },
    { setting: 'DB Latency Severe', value: '>15,000ms', where: 'CRITICAL DATABASE ISSUE' },
    { setting: 'DB Latency Moderate', value: '8,000-15,000ms', where: 'Latency note appended' },
    { setting: 'Backend Bottleneck', value: 'TTFB >5,000ms', where: 'Flagged in perf metrics' },
    { setting: 'Frontend Bottleneck', value: 'Render >5,000ms', where: 'Flagged in perf metrics' },
    { setting: 'IIS Cold Start', value: 'TTFB >10s', where: 'App Pool recycle detection' },
    { setting: 'IIS Thread Starvation', value: '2+ APIs >5s avg', where: 'Thread pool saturation' },
    { setting: 'IIS Recommendations', value: '3+ consistent patterns', where: 'Not on single events' },
    { setting: 'IIS Trend Analysis', value: '24h current + 7d trend', where: 'Pattern detection window' },
    { setting: 'Expected Post-Login Page', value: 'mainpage.aspx', where: 'Per site, configurable' },
    { setting: 'Browser Timeout', value: '30 seconds', where: 'Page load timeout' },
    { setting: 'Monitor Region', value: 'US-Central', where: 'MONITOR_REGION env var' },
    { setting: 'Scheduler Tick', value: '15 seconds', where: 'Checks which sites are due' },
    { setting: 'Alert Poll', value: '10 seconds', where: 'Frontend global polling' },
    { setting: 'Dashboard Refresh', value: '15 seconds', where: 'Auto-refresh with countdown' },
    { setting: 'Toast Repeat', value: '30 minutes', where: 'Ongoing alert reminder' },
    { setting: 'Toast Dismiss', value: '5 seconds', where: 'Auto-hide popup' },
    { setting: 'Warning Banner Hide', value: '30 seconds', where: 'Orange banner auto-dismiss' },
    { setting: 'Alarm Sound Repeat', value: '4 seconds', where: 'Critical alert beep interval' },
    { setting: 'Check Interval Default', value: '5 minutes', where: 'New site default' },
    { setting: 'Indicator Retry Wait', value: '1 second', where: 'Single retry (was 2x2s, reduced)' },
    { setting: 'Subpage Buffer', value: '1.5 seconds', where: 'JS rendering after navigate' },
    { setting: 'Slow Resource', value: '>1 second', where: 'Flagged in perf metrics' },
    { setting: 'Slow API Call', value: '>2 seconds', where: 'Flagged in perf metrics' },
    { setting: 'Failed Resource Count', value: '3+', where: 'IIS static file serving issue' },
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
        <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>v1.0</span>
      </div>

      <div className="card" style={{ background: 'linear-gradient(135deg, #001e3f, #003366)', color: 'white', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>How This Monitoring App Works</h3>
        <p style={{ fontSize: '13px', opacity: 0.85, lineHeight: 1.7 }}>
          The monitoring engine uses a <strong>headless Chromium browser (Playwright)</strong> to perform real user simulations.
          For each site it loads pages, fills login forms, navigates subpages, and collects
          <strong> detailed performance metrics</strong> (TTFB, DOM load, FCP, resource timing) via the browser Performance API.
          It detects <strong>SQL Server issues</strong> (timeouts, deadlocks, connection failures),
          <strong> IIS/App Pool problems</strong> (503 crashes, cold starts, thread starvation, memory exhaustion),
          and identifies whether slowness is caused by <strong>backend/database</strong> or <strong>frontend/rendering</strong>.
          Trend analysis over 24h/7d generates <strong>actionable IIS recommendations</strong> only after consistent patterns.
        </p>
      </div>

      {renderSection('Check Types', rules)}
      {renderSection('Detection, Alerts & Diagnostics', thresholds)}
      {renderSection('Scheduling, Metrics & Security', timing)}

      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header"><h3>Default Values & Thresholds</h3></div>
        <div className="table-container">
          <table>
            <thead><tr><th>Setting</th><th>Default Value</th><th>Context</th></tr></thead>
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

      <div className="card">
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>Alert Status Reference</h3>
        <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
          {[
            { badge: 'ok', label: 'OK', desc: 'Site up, fast, all checks pass, IIS healthy' },
            { badge: 'warning', label: 'WARNING', desc: 'Slow (>15min sustained), text missing, URL mismatch, IIS cold start, thread starvation' },
            { badge: 'critical', label: 'CRITICAL', desc: 'Down, login failed, HTTP error, DB issue, IIS crash/503/502, error page redirect, severe latency' },
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
