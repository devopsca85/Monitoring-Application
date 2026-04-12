export default function Metrics() {
  const rules = [
    {
      title: 'Uptime Check',
      icon: '\u2191',
      color: '#3b82f6',
      items: [
        { label: 'Method', value: 'Headless Chromium (Playwright) loads full page' },
        { label: 'HTTP Errors', value: '404/5XX → instant CRITICAL. 4XX → CRITICAL' },
        { label: 'Timeout', value: 'CRITICAL if page does not load within 30s' },
        { label: 'Perf Metrics', value: 'TTFB, DOM load, FCP, resources, transfer size' },
        { label: 'IIS/Stack Diag', value: 'Stack-specific error detection (ASP.NET, PHP, Node, etc.)' },
        { label: 'Security Scan', value: 'Headers, SSL, cookies, secrets — on-demand DAST' },
        { label: 'Success', value: 'HTTP 200-399 with page loaded = OK' },
      ],
    },
    {
      title: 'Login Validation',
      icon: '\uD83D\uDD12',
      color: '#10b981',
      items: [
        { label: 'Method', value: 'Fill credentials, submit, wait for page load + network idle' },
        { label: 'Group Credentials', value: 'Site can inherit login details from its Site Group' },
        { label: 'Submit Tracking', value: 'Logs navigation success/failure' },
        { label: 'Field Error', value: 'Clean error if username/password selector not found' },
        { label: 'Password Check', value: 'Password input still visible after submit = CRITICAL' },
        { label: 'Error Detection', value: '25+ keywords + .error, [role=alert], red spans' },
        { label: 'Error Page Redirect', value: 'GenericError.aspx, 500.aspx, maintenance pages' },
        { label: 'DB Issue Detection', value: 'SQL timeout, deadlock, connection pool, stack traces' },
        { label: 'Backend Latency', value: '>15s = CRITICAL. 8-15s = note appended' },
        { label: 'Expected Page', value: 'URL must contain expected page (default: mainpage.aspx)' },
        { label: 'CSS Selector', value: 'All formats: #id, .class, tag#id, ul#breadcrumbs, div.class' },
        { label: 'Indicator Logic', value: 'If set and not found: fail. On expected page without it: warn + OK' },
        { label: 'SSO Backdoor', value: 'Use direct login URL for SSO sites' },
      ],
    },
    {
      title: 'Subpage Validation',
      icon: '\uD83D\uDCC4',
      color: '#8b5cf6',
      items: [
        { label: 'Prerequisite', value: 'Only runs after login confirmed successful' },
        { label: 'HTTP Status', value: '4XX/5XX = immediate CRITICAL' },
        { label: 'Login Redirect', value: 'Redirect to login/signin = CRITICAL (session expired)' },
        { label: 'Error Page', value: 'error, 404, genericerror in URL = CRITICAL' },
        { label: 'URL Path Match', value: 'Compares expected vs actual — warns on mismatch' },
        { label: 'CSS Selector', value: 'All CSS formats normalized. Missing = CRITICAL' },
        { label: 'Expected Text', value: 'Must be in page content. Missing = WARNING' },
        { label: 'Empty Page', value: 'Body <50 chars = WARNING' },
      ],
    },
  ];

  const detection = [
    {
      title: 'Response Time',
      icon: '\u23F1',
      color: '#f59e0b',
      items: [
        { label: 'Default', value: '10,000ms (10 seconds)' },
        { label: 'Options', value: '2s, 3s, 5s, 8s, 10s, 15s, 20s, 30s' },
        { label: 'Sustained', value: 'All checks in past 15 min must exceed threshold' },
        { label: 'Cooldown', value: '3 hours between slow alerts per site' },
        { label: 'Consolidated', value: 'One email/Teams for ALL slow sites' },
        { label: 'Dedup', value: 'FOR UPDATE lock — one alert per site' },
        { label: 'Recovery', value: 'Auto-resolves when response drops below threshold' },
      ],
    },
    {
      title: 'Database / SQL Server',
      icon: '\uD83D\uDDC4',
      color: '#ef4444',
      items: [
        { label: 'SQL Timeout', value: '"execution timeout expired" → CRITICAL' },
        { label: 'Connection', value: '"cannot open database", "max pool size" → CRITICAL' },
        { label: 'Deadlock', value: '"transaction was deadlocked" → CRITICAL' },
        { label: 'Severe Latency', value: '>15s response → CRITICAL with DB diagnosis' },
        { label: 'Bottleneck', value: 'TTFB vs total — backend/database vs frontend/rendering' },
        { label: 'Backend %', value: 'Red >70%, Orange >50%, Green <50%' },
      ],
    },
    {
      title: 'IIS / App Pool',
      icon: '\u2699',
      color: '#2563eb',
      items: [
        { label: '503 Down', value: 'App Pool stopped or crashed → CRITICAL' },
        { label: '502 Crash', value: 'Worker process crash/timeout → CRITICAL' },
        { label: 'Memory', value: 'OutOfMemoryException → CRITICAL' },
        { label: 'Cold Start', value: 'TTFB >10s → App Pool recycle detected' },
        { label: 'Thread Starvation', value: '2+ slow APIs >5s → saturation' },
        { label: 'Recommendations', value: '3+ patterns → AlwaysRunning, preload, recycling' },
      ],
    },
    {
      title: 'Multi-Stack Detection',
      icon: '\u26A1',
      color: '#06b6d4',
      items: [
        { label: 'ASP.NET', value: 'YSOD, compilation, runtime, ViewState errors' },
        { label: 'PHP', value: 'Fatal, parse, memory limit, execution timeout, PDO' },
        { label: 'Node.js', value: 'Missing module, heap OOM, unhandled rejection' },
        { label: 'React', value: 'Hydration mismatch, chunk load failure' },
        { label: 'Python', value: 'Tracebacks, Django/Flask/FastAPI errors' },
        { label: 'Java', value: 'NullPointer, ClassNotFound, Spring, Tomcat' },
        { label: 'WordPress', value: 'WSOD, plugin errors, database errors' },
        { label: 'Universal', value: '502/504 proxy, SSL, CORS, rate limiting, Nginx/Apache' },
      ],
    },
    {
      title: 'Security Scanning (DAST)',
      icon: '\uD83D\uDD12',
      color: '#7c3aed',
      items: [
        { label: 'Headers', value: 'HSTS, CSP, X-Frame-Options, X-Content-Type, Referrer-Policy' },
        { label: 'SSL/TLS', value: 'Certificate validity, expiry, chain verification' },
        { label: 'Cookies', value: 'Secure, HttpOnly, SameSite flags on all cookies' },
        { label: 'Info Disclosure', value: 'Server version, X-Powered-By, X-AspNet-Version' },
        { label: 'Sensitive Paths', value: '/.env, /.git, /phpinfo.php, /elmah.axd, /wp-admin' },
        { label: 'Secrets in HTML', value: 'API keys, secret keys in page source' },
        { label: 'Mixed Content', value: 'HTTP resources on HTTPS pages' },
        { label: 'Scoring', value: '0-100 score, A/B/C/D/F grade' },
      ],
    },
    {
      title: 'Compliance',
      icon: '\u2705',
      color: '#059669',
      items: [
        { label: 'SOC 2 Type II', value: '20 controls — CC1-CC9, A1 (Trust Services Criteria)' },
        { label: 'GDPR', value: '16 controls — Art.5-37 (EU Data Privacy)' },
        { label: 'Status Tracking', value: 'Not Started → In Progress → Compliant / Non-Compliant / N/A' },
        { label: 'Evidence', value: 'Per-control notes, evidence documentation' },
        { label: 'Assignment', value: 'Assign controls to team members' },
        { label: 'Progress', value: 'Percentage bar per framework' },
      ],
    },
  ];

  const alerts = [
    {
      title: 'Alert Triggers',
      icon: '\uD83D\uDD14',
      color: '#ef4444',
      items: [
        { label: 'HTTP 404/5XX', value: 'Instant CRITICAL on first occurrence' },
        { label: 'Login Failure', value: 'Instant CRITICAL (password visible, error detected)' },
        { label: 'Error Page', value: 'GenericError.aspx etc → CRITICAL' },
        { label: 'Database', value: 'SQL timeout/deadlock/connection → CRITICAL' },
        { label: 'IIS', value: '503/502/memory → CRITICAL' },
        { label: 'Slowness', value: 'WARNING after 15min sustained, 3h cooldown' },
        { label: 'False Positive', value: 'Mark alert as FP → suppression rule auto-created' },
        { label: 'Recovery', value: 'Instant OK + auto-resolve' },
        { label: 'Dedup', value: 'FOR UPDATE lock prevents duplicates' },
      ],
    },
    {
      title: 'Notifications',
      icon: '\uD83D\uDCE7',
      color: '#3b82f6',
      items: [
        { label: 'Email', value: 'SMTP — per-site notification emails' },
        { label: 'Teams', value: 'Global webhook, ON/OFF toggle' },
        { label: 'Acknowledge', value: 'Teams message with down/slow breakdown' },
        { label: 'Alarm Audio', value: 'Custom MP3/WAV/OGG or default tone' },
        { label: 'Critical Sound', value: 'Audio only for CRITICAL, not warnings' },
        { label: 'Warning Banner', value: 'Orange, auto-hides 30s' },
        { label: 'Toast', value: 'New: instant. Ongoing: every 30min. No refresh spam' },
        { label: 'Daily Report', value: '9 AM CST — summary email with SVG pie charts' },
        { label: 'Admin Alerts', value: 'Site add/remove notifications' },
      ],
    },
  ];

  const infra = [
    {
      title: 'Scheduling',
      icon: '\u23F0',
      color: '#10b981',
      items: [
        { label: 'Scheduler', value: 'Async background task in FastAPI' },
        { label: 'Tick', value: '15 seconds' },
        { label: 'Intervals', value: '1, 3, 5, 10, 15, 30, 60 min' },
        { label: 'Overlap Guard', value: 'Skips if check running for same site' },
        { label: 'Failure Retry', value: 'Resets timer on failure' },
        { label: 'K8s Scheduler', value: 'Separate loop for cluster checks (30s tick)' },
        { label: 'Daily Report', value: '9 AM CST automatic send' },
      ],
    },
    {
      title: 'Performance Metrics',
      icon: '\u26A1',
      color: '#f97316',
      items: [
        { label: 'Source', value: 'Browser Performance API' },
        { label: 'Metrics', value: 'TTFB, DOM Loaded, FCP, DNS/TCP/TLS, Total Load' },
        { label: 'Resources', value: 'Slow (>1s), failed (4XX/5XX), slow APIs (>2s)' },
        { label: 'Backend %', value: 'TTFB as % of total — bottleneck identification' },
        { label: 'Region', value: 'MONITOR_REGION env var' },
      ],
    },
    {
      title: 'Kubernetes Monitoring',
      icon: '\u2601',
      color: '#2563eb',
      items: [
        { label: 'Providers', value: 'Azure AKS, AWS EKS, GCP GKE, On-Premise' },
        { label: 'Auth', value: 'Kubeconfig (encrypted), Bearer token, API server URL' },
        { label: 'Node Checks', value: 'Ready/NotReady, CPU %, Memory %, conditions' },
        { label: 'Pod Checks', value: 'CrashLoopBackOff, Failed, Pending, restart count' },
        { label: 'Events', value: 'Warning events with count and involved object' },
        { label: 'Metrics Server', value: 'CPU/memory usage per node and pod (if available)' },
        { label: 'Alerts', value: '8 rules: node down, crash loop, high CPU/mem, pending' },
      ],
    },
    {
      title: 'Security & Auth',
      icon: '\uD83D\uDD10',
      color: '#0f172a',
      items: [
        { label: 'Credentials', value: 'Fernet AES-128 encrypted (site + group + K8s)' },
        { label: 'SMTP/Teams/SSO', value: 'Fernet encrypted in system_settings' },
        { label: 'Passwords', value: 'bcrypt hashed (one-way)' },
        { label: 'API', value: 'JWT Bearer tokens' },
        { label: 'Azure SSO', value: 'Entra ID + group-based admin/user roles' },
        { label: 'Site Groups', value: 'Shared credentials per environment group' },
        { label: 'False Positives', value: 'Mark + auto-suppress matching alerts' },
      ],
    },
  ];

  const defaults = [
    { s: 'Slow Response Threshold', v: '10,000ms (10s)', w: 'Per site, configurable' },
    { s: 'Sustained Slowness', v: '15 minutes', w: 'Before sending alert' },
    { s: 'Slow Cooldown', v: '3 hours', w: 'Between alerts per site' },
    { s: 'DB Latency Severe', v: '>15,000ms', w: 'CRITICAL DATABASE ISSUE' },
    { s: 'DB Latency Moderate', v: '8-15,000ms', w: 'Latency note appended' },
    { s: 'Backend Bottleneck', v: 'TTFB >5,000ms', w: 'Flagged in perf metrics' },
    { s: 'IIS Cold Start', v: 'TTFB >10s', w: 'App Pool recycle' },
    { s: 'IIS Recommendations', v: '3+ patterns', w: 'Not single events' },
    { s: 'Expected Post-Login', v: 'mainpage.aspx', w: 'Per site' },
    { s: 'Browser Timeout', v: '30 seconds', w: 'Page load' },
    { s: 'Monitor Region', v: 'US-Central', w: 'MONITOR_REGION env' },
    { s: 'Scheduler Tick', v: '15 seconds', w: 'Site checks' },
    { s: 'K8s Scheduler Tick', v: '30 seconds', w: 'Cluster checks' },
    { s: 'Alert Poll', v: '10 seconds', w: 'Frontend global' },
    { s: 'Dashboard Refresh', v: '15 seconds', w: 'Auto-refresh' },
    { s: 'Toast Repeat', v: '30 minutes', w: 'Ongoing alerts' },
    { s: 'Toast Dismiss', v: '5 seconds', w: 'Auto-hide' },
    { s: 'Warning Banner', v: '30 seconds', w: 'Auto-hide' },
    { s: 'Alarm Repeat', v: '4 seconds', w: 'Critical beep' },
    { s: 'Daily Report', v: '9:00 AM CST', w: 'Automatic send' },
    { s: 'Security Score', v: '0-100, A-F', w: 'Per site' },
    { s: 'Node High CPU', v: '>85%', w: 'K8s alert' },
    { s: 'Node High Memory', v: '>85%', w: 'K8s alert' },
    { s: 'Pod High Restarts', v: '>5', w: 'K8s warning' },
  ];

  const renderSection = (title, groups) => (
    <div style={{ marginBottom: '28px' }}>
      <h3 style={{ fontSize: '17px', fontWeight: 700, marginBottom: '14px', letterSpacing: '-0.01em' }}>{title}</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
        {groups.map((g) => (
          <div key={g.title} className="card" style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <div style={{ width: 32, height: 32, borderRadius: '8px', background: g.color, color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', flexShrink: 0 }}>{g.icon}</div>
              <h4 style={{ fontSize: '14px', fontWeight: 700 }}>{g.title}</h4>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>{g.items.map((item, i) => (
                <tr key={i} style={{ borderBottom: i < g.items.length - 1 ? '1px solid var(--color-border-light)' : 'none' }}>
                  <td style={{ padding: '6px 6px 6px 0', fontSize: '11px', fontWeight: 600, color: 'var(--color-text)', whiteSpace: 'nowrap', verticalAlign: 'top', width: '30%' }}>{item.label}</td>
                  <td style={{ padding: '6px 0', fontSize: '11px', color: 'var(--color-text-secondary)' }}>{item.value}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div>
      <div className="page-header"><h2>Monitoring Metrics & Rules</h2><span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>v1.0</span></div>

      <div className="card" style={{ background: 'linear-gradient(135deg, #0f172a, #1e3a5f)', color: 'white', marginBottom: '24px' }}>
        <h3 style={{ fontSize: '15px', marginBottom: '6px' }}>How This Monitoring App Works</h3>
        <p style={{ fontSize: '12px', opacity: 0.85, lineHeight: 1.7 }}>
          Real user simulation via headless Chromium. Collects performance metrics (TTFB, FCP, resources).
          Detects SQL Server issues, IIS/App Pool problems, and stack-specific errors (ASP.NET, PHP, Node, React, Python, Java, WordPress).
          DAST security scanning (headers, SSL, cookies, secrets). SOC 2 + GDPR compliance tracking.
          Kubernetes cluster monitoring (AKS, EKS, GKE). Site Groups with shared credentials.
          Alerts fire instantly on failures. Slowness alerts: 15min sustained, consolidated, 3h cooldown.
          Daily report at 9 AM CST with SVG charts.
        </p>
      </div>

      {renderSection('Check Types', rules)}
      {renderSection('Detection & Diagnostics', detection)}
      {renderSection('Alerts & Notifications', alerts)}
      {renderSection('Infrastructure & Security', infra)}

      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header"><h3>Default Values</h3></div>
        <div className="table-container">
          <table>
            <thead><tr><th>Setting</th><th>Value</th><th>Context</th></tr></thead>
            <tbody>{defaults.map((d, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 500, fontSize: '12px' }}>{d.s}</td>
                <td style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-primary)' }}>{d.v}</td>
                <td style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{d.w}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px' }}>Status Reference</h3>
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
          {[
            { b: 'ok', l: 'OK', d: 'Up, fast, all checks pass, IIS healthy, security score A/B' },
            { b: 'warning', l: 'WARNING', d: 'Slow (>15min), text missing, URL mismatch, cold start, security C/D' },
            { b: 'critical', l: 'CRITICAL', d: 'Down, login failed, HTTP error, DB issue, IIS crash, security F, K8s node down' },
          ].map((s) => (
            <div key={s.b} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`badge badge-${s.b}`} style={{ fontSize: '11px' }}>{s.l}</span>
              <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>{s.d}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
