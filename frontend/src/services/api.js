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
  api.get(`/monitoring/alerts?resolved=${resolved}`);
export const resolveAlert = (id) => api.post(`/monitoring/alerts/${id}/resolve`);
export const triggerCheck = (siteId) => api.post(`/monitoring/trigger/${siteId}`);

export default api;
