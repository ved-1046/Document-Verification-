import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8080';

const api = axios.create({
    baseURL: `${API_BASE}/api/v1`,
});

// Attach JWT automatically if stored and handle FormData multipart boundaries
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    // If request payload is FormData, do not let an explicit Content-Type header interfere.
    // The browser must automatically set 'multipart/form-data; boundary=...'
    if (config.data instanceof FormData) {
        if (config.headers) {
            delete config.headers['Content-Type'];
            delete config.headers['content-type'];
            if (typeof (config.headers as any).delete === 'function') {
                (config.headers as any).delete('Content-Type');
                (config.headers as any).delete('content-type');
            }
        }
    }
    return config;
});

// Redirect to login on 401
api.interceptors.response.use(
    (res) => res,
    (err) => {
        const path = err.config?.url ?? '';
        const isAuthAttempt =
            path.includes('/auth/login') || path.includes('/auth/register');
        if (err.response?.status === 401 && !isAuthAttempt) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
        return Promise.reject(err);
    },
);

export default api;
