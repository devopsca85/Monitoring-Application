import { useState, useEffect, useRef } from 'react';
import { Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom';
import { getMe } from './services/api';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Sites from './pages/Sites';
import SiteDetail from './pages/SiteDetail';
import SiteForm from './pages/SiteForm';
import Alerts from './pages/Alerts';
import AdminUsers from './pages/AdminUsers';
import AdminSettings from './pages/AdminSettings';
import Profile from './pages/Profile';
import Metrics from './pages/Metrics';
import FalsePositives from './pages/FalsePositives';
import K8sClusters from './pages/K8sClusters';
import SiteGroupsPage from './pages/SiteGroups';
import SecurityDashboard from './pages/SecurityDashboard';
import ApiDocs from './pages/ApiDocs';
import Compliance from './pages/Compliance';
import AlertMonitor from './components/AlertMonitor';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      getMe()
        .then((res) => setUser(res.data))
        .catch(() => localStorage.removeItem('token'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  if (loading) return null;

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLogin={setUser} />} />
        <Route path="*" element={<NavigateToLogin />} />
      </Routes>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar user={user} />
      <div className="main-wrapper" style={{ flex: 1, marginLeft: 260, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <AlertMonitor />
        <TopBar user={user} setUser={setUser} />
        <main className="main-content" style={{ marginLeft: 0 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/sites" element={<Sites />} />
            <Route path="/sites/new" element={<SiteForm />} />
            <Route path="/sites/:id/edit" element={<SiteForm />} />
            <Route path="/sites/:id" element={<SiteDetail />} />
            <Route path="/alerts" element={<Alerts isAdmin={user.is_admin} />} />
            <Route path="/metrics" element={<Metrics />} />
            <Route path="/false-positives" element={<FalsePositives />} />
            <Route path="/security" element={<SecurityDashboard />} />
            <Route path="/compliance" element={<Compliance />} />
            <Route path="/api-docs" element={<ApiDocs />} />
            <Route path="/k8s" element={<K8sClusters />} />
            <Route path="/k8s/new" element={<div>K8s Add Cluster — TODO</div>} />
            <Route path="/k8s/:id" element={<div>K8s Cluster Detail — TODO</div>} />
            <Route path="/profile" element={<Profile user={user} onUpdate={setUser} />} />
            {user.is_admin && (
              <>
                <Route path="/admin/groups" element={<SiteGroupsPage />} />
              <Route path="/admin/users" element={<AdminUsers />} />
                <Route path="/admin/settings" element={<AdminSettings />} />
              </>
            )}
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

// Preserves query params (like ?code=xxx) when redirecting to /login
function NavigateToLogin() {
  const location = useLocation();
  return <Navigate to={`/login${location.search}`} replace />;
}

function TopBar({ user, setUser }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const initials = (user.full_name || user.email)
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0].toUpperCase())
    .join('');

  return (
    <div className="top-bar" style={{
      height: 56, background: 'var(--color-bg-white)', borderBottom: '1px solid var(--color-border)',
      display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '0 32px',
      position: 'sticky', top: 0, zIndex: 50,
    }}>
      <div ref={ref} style={{ position: 'relative' }}>
        <button
          onClick={() => setOpen(!open)}
          style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px',
            borderRadius: 'var(--radius)', transition: 'background 0.15s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-bg)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
        >
          <div style={{
            width: 34, height: 34, borderRadius: '50%', background: 'var(--color-primary)',
            color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '13px', fontWeight: 700,
          }}>
            {initials}
          </div>
          <div style={{ textAlign: 'left' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, lineHeight: 1.2 }}>{user.full_name || user.email}</div>
            <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', lineHeight: 1.2 }}>
              {user.is_admin ? 'Admin' : 'User'}
            </div>
          </div>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2"><path d="M6 9l6 6 6-6"/></svg>
        </button>

        {open && (
          <div style={{
            position: 'absolute', right: 0, top: '100%', marginTop: 4,
            background: 'var(--color-bg-white)', border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)', boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            minWidth: 200, overflow: 'hidden', zIndex: 100,
          }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '13px', fontWeight: 600 }}>{user.full_name || 'User'}</div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>{user.email}</div>
            </div>
            <button
              onClick={() => { setOpen(false); navigate('/profile'); }}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
                padding: '10px 16px', background: 'none', border: 'none', cursor: 'pointer',
                fontSize: '13px', textAlign: 'left', color: 'var(--color-text)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-bg)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              My Profile
            </button>
            <button
              onClick={handleLogout}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
                padding: '10px 16px', background: 'none', border: 'none', cursor: 'pointer',
                fontSize: '13px', textAlign: 'left', color: 'var(--color-red)',
                borderTop: '1px solid var(--color-border)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-bg)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>
              Logout
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Sidebar({ user }) {
  const location = useLocation();
  const isActive = (path) =>
    location.pathname === path || location.pathname.startsWith(path + '/')
      ? 'active'
      : '';

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img src="https://www.fldata.com/wp-content/uploads/2020/09/fldata_logo.png" alt="FLData" style={{ maxWidth: '160px', height: 'auto', filter: 'brightness(0) invert(1)' }} />
      </div>
      <nav className="sidebar-nav">
        <Link to="/" className={isActive('/')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          Dashboard
        </Link>
        <Link to="/sites" className={isActive('/sites')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          Sites
        </Link>
        <Link to="/alerts" className={isActive('/alerts')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/></svg>
          Alerts
        </Link>
        <Link to="/metrics" className={isActive('/metrics')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 21H3V3"/><path d="M18 9l-5 5-2-2-4 4"/></svg>
          Metrics & Rules
        </Link>
        <Link to="/api-docs" className={isActive('/api-docs')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/></svg>
          API Docs
        </Link>
        <Link to="/security" className={isActive('/security')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          Security
        </Link>
        <Link to="/compliance" className={isActive('/compliance')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          Compliance
        </Link>
        <Link to="/k8s" className={isActive('/k8s')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
          Kubernetes
        </Link>
        <Link to="/false-positives" className={isActive('/false-positives')}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 9v2m0 4h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/></svg>
          False Positives
        </Link>
        {user.is_admin && (
          <>
            <div style={{ padding: '12px 24px 6px', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', color: 'rgba(255,255,255,0.3)', letterSpacing: '1px' }}>Admin</div>
            <Link to="/admin/groups" className={isActive('/admin/groups')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              Site Groups
            </Link>
            <Link to="/admin/users" className={isActive('/admin/users')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              Users
            </Link>
            <Link to="/admin/settings" className={isActive('/admin/settings')}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
              Settings
            </Link>
          </>
        )}
      </nav>
      <div style={{ padding: '12px 24px', borderTop: '1px solid rgba(255,255,255,0.1)', fontSize: '11px', color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
        v1.0
      </div>
    </aside>
  );
}

export default App;
