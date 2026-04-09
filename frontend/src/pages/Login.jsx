import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register, getMe } from '../services/api';
import api from '../services/api';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSetup, setIsSetup] = useState(false);
  const [checking, setChecking] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/auth/setup-check')
      .then((r) => setIsSetup(r.data.needs_setup))
      .catch(() => setIsSetup(false))
      .finally(() => setChecking(false));
  }, []);

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

  if (checking) return null;

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
