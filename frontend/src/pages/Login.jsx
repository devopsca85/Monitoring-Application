import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { login, register, getMe, getSsoConfig, ssoCallback } from '../services/api';
import api from '../services/api';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSetup, setIsSetup] = useState(false);
  const [checking, setChecking] = useState(true);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [ssoAuthUrl, setSsoAuthUrl] = useState('');
  const [ssoLoading, setSsoLoading] = useState(false);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    // Check setup + SSO config in parallel
    Promise.all([
      api.get('/auth/setup-check').then((r) => setIsSetup(r.data.needs_setup)).catch(() => setIsSetup(false)),
      getSsoConfig().then((r) => {
        if (r.data.enabled) {
          setSsoEnabled(true);
          setSsoAuthUrl(r.data.auth_url);
        }
      }).catch(() => {}),
    ]).finally(() => setChecking(false));
  }, []);

  // Handle SSO callback (code in URL params)
  useEffect(() => {
    const code = searchParams.get('code');
    if (code && !ssoLoading) {
      setSsoLoading(true);
      setError('');
      ssoCallback({ code })
        .then(async (res) => {
          localStorage.setItem('token', res.data.access_token);
          const me = await getMe();
          onLogin(me.data);
          navigate('/');
        })
        .catch((err) => {
          setError(err.response?.data?.detail || 'Azure SSO login failed');
          // Clear code from URL
          window.history.replaceState({}, '', '/login');
        })
        .finally(() => setSsoLoading(false));
    }
  }, [searchParams]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await login(email, password);
      localStorage.setItem('token', res.data.access_token);
      const me = await getMe();
      onLogin(me.data);
      navigate('/');
    } catch {
      setError('Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  const handleSetup = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register({ email, password, full_name: fullName });
      const res = await login(email, password);
      localStorage.setItem('token', res.data.access_token);
      const me = await getMe();
      onLogin(me.data);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Setup failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSsoLogin = () => {
    // auth_url already contains redirect_uri from admin settings — use as-is
    window.location.href = ssoAuthUrl;
  };

  if (checking) return null;

  if (ssoLoading) {
    return (
      <div className="login-container">
        <div className="login-card" style={{ textAlign: 'center' }}>
          <div style={{ marginBottom: '16px' }}>
            <img src="https://www.fldata.com/wp-content/uploads/2020/09/fldata_logo.png" alt="FLData" style={{ maxWidth: '200px', height: 'auto' }} />
          </div>
          <p style={{ marginBottom: '16px' }}>Signing in with Microsoft...</p>
          <div style={{ width: '40px', height: '40px', border: '3px solid var(--color-border)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', margin: '0 auto' }} />
        </div>
      </div>
    );
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <div style={{ textAlign: 'center', marginBottom: '8px' }}>
          <img src="https://www.fldata.com/wp-content/uploads/2020/09/fldata_logo.png" alt="FLData" style={{ maxWidth: '200px', height: 'auto' }} />
        </div>

        {isSetup ? (
          <>
            <p>Create your admin account to get started</p>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleSetup}>
              <div className="form-group">
                <label>Full Name</label>
                <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Admin User" />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@company.com" required />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Choose a strong password" required />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                {loading ? 'Creating account...' : 'Create Admin Account'}
              </button>
            </form>
          </>
        ) : (
          <>
            <p>Sign in to your monitoring dashboard</p>
            {error && <div className="error-message">{error}</div>}

            {/* Azure SSO Button */}
            {ssoEnabled && (
              <>
                <button onClick={handleSsoLogin} style={{
                  width: '100%', padding: '12px', border: '1px solid var(--color-border)',
                  borderRadius: '30px', background: 'var(--color-bg-white)', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
                  fontSize: '14px', fontWeight: 500, color: 'var(--color-text)',
                  transition: 'all 0.2s', marginBottom: '16px',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-bg)'; e.currentTarget.style.borderColor = 'var(--color-primary)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--color-bg-white)'; e.currentTarget.style.borderColor = 'var(--color-border)'; }}
                >
                  <svg width="20" height="20" viewBox="0 0 21 21">
                    <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
                    <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
                    <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
                    <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
                  </svg>
                  Sign in with Microsoft
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                  <div style={{ flex: 1, height: '1px', background: 'var(--color-border)' }} />
                  <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>or</span>
                  <div style={{ flex: 1, height: '1px', background: 'var(--color-border)' }} />
                </div>
              </>
            )}

            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" required />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" required />
              </div>
              <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
