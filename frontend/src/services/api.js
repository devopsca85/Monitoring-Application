import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const login = (username, password) =>
  api.post('/auth/login', new URLSearchParams({ username, password }));

export const register = (data) => api.post('/auth/register', data);

export const getMe = () => api.get('/auth/me');
export const updateMe = (data) => api.put('/auth/me', data);

// Sites
export const getSites = () => api.get('/sites/');
export const getSite = (id) => api.get(`/sites/${id}`);
export const createSite = (data) => api.post('/sites/', data);
export const updateSite = (id, data) => api.put(`/sites/${id}`, data);
export const deleteSite = (id) => api.delete(`/sites/${id}`);
export const getSiteCredentials = (id) => api.get(`/sites/${id}/credentials`);

// Monitoring
export const getDashboardStats = () => api.get('/monitoring/dashboard');
export const getResults = (siteId, limit = 50) =>
  api.get(`/monitoring/results/${siteId}?limit=${limit}`);
export const getAlerts = (resolved = false) =>
  api.get(`/monitoring/alerts-raw?resolved=${resolved}`);
export const resolveAlert = (id) => api.post(`/monitoring/alerts/${id}/resolve`);
export const getAlertHistory = (limit = 100) => api.get(`/monitoring/alert-history-raw?limit=${limit}`);
export const triggerCheck = (siteId) => api.post(`/monitoring/trigger/${siteId}`);
export const acknowledgeAlerts = () => api.post('/monitoring/alerts/acknowledge');
export const deleteAlertHistory = () => api.delete('/monitoring/alerts/history');
export const getSlownessAnalysis = () => api.get('/monitoring/slowness-analysis');
export const getIisDiagnostics = (siteId) => api.get(`/monitoring/iis-diagnostics/${siteId}`);
export const getSitesStatus = () => api.get('/monitoring/sites-status');

// Admin — Users
export const getUsers = () => api.get('/admin/users');
export const createUser = (data) => api.post('/admin/users', data);
export const updateUser = (id, data) => api.put(`/admin/users/${id}`, data);
export const deleteUser = (id) => api.delete(`/admin/users/${id}`);

// Admin — Settings
export const getSystemSettings = () => api.get('/admin/settings');
export const updateSmtpSettings = (data) => api.put('/admin/settings/smtp', data);
export const updateTeamsSettings = (data) => api.put('/admin/settings/teams', data);
export const testSmtp = (data) => api.post('/admin/settings/smtp/test', data);
export const testTeams = () => api.post('/admin/settings/teams/test');

// Admin — Azure SSO
export const getSsoSettings = () => api.get('/admin/settings/sso');
export const updateSsoSettings = (data) => api.put('/admin/settings/sso', data);

// Admin — Alarm Audio
export const uploadAlarmAudio = (file) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/admin/alarm-audio', form, { headers: { 'Content-Type': 'multipart/form-data' } });
};
export const deleteAlarmAudio = () => api.delete('/admin/alarm-audio');
export const getAlarmAudioInfo = () => api.get('/admin/alarm-audio/info');

// SSO (public)
export const getSsoConfig = () => api.get('/sso/config');
export const ssoCallback = (data) => api.post('/sso/callback', data);

export default api;
