import { useState, useEffect } from 'react';
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { getMe } from './services/api';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Sites from './pages/Sites';
import SiteDetail from './pages/SiteDetail';
import SiteForm from './pages/SiteForm';
import Alerts from './pages/Alerts';

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
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    );
  }

  return (
    <div className="app-layout">
      <Sidebar user={user} setUser={setUser} />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/sites/new" element={<SiteForm />} />
          <Route path="/sites/:id/edit" element={<SiteForm />} />
          <Route path="/sites/:id" element={<SiteDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </div>
  );
}

function Sidebar({ user, setUser }) {
  const location = useLocation();
  const isActive = (path) =>
    location.pathname === path || location.pathname.startsWith(path + '/')
      ? 'active'
      : '';

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

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
      </nav>
      <div style={{ padding: '16px 24px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>
          {user.email}
        </div>
        <button onClick={handleLogout} className="btn btn-outline" style={{ width: '100%', color: 'rgba(255,255,255,0.7)', borderColor: 'rgba(255,255,255,0.2)' }}>
          Logout
        </button>
      </div>
    </aside>
  );
}

export default App;
