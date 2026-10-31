/**
 * SHIELD Platform — API Client
 * Centralized Axios client with automatic token refresh and device fingerprinting.
 */
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ─── Device Fingerprint ──────────────────────────────────
export function computeDeviceFingerprint(): string {
  if (typeof window === 'undefined') return 'server';
  const raw = [
    navigator.userAgent,
    navigator.platform,
    screen.width + 'x' + screen.height,
    Intl.DateTimeFormat().resolvedOptions().timeZone,
  ].join('|');
  // Simple hash (use crypto-js in production for better entropy)
  let hash = 0;
  for (let i = 0; i < raw.length; i++) {
    hash = ((hash << 5) - hash) + raw.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(16).padStart(16, '0');
}

// ─── Axios Instance ──────────────────────────────────────
const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // Send cookies
});

// ─── Request Interceptor ─────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('shield_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Attach device fingerprint to every request
  config.headers['X-Device-Fingerprint'] = computeDeviceFingerprint();
  return config;
});

// ─── Response Interceptor (Auto Token Refresh) ───────────
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('shield_refresh_token');
        if (!refreshToken) throw new Error('No refresh token');
        
        const { data } = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
          device_fingerprint: computeDeviceFingerprint(),
        });
        
        localStorage.setItem('shield_access_token', data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch {
        // Refresh failed — redirect to login
        localStorage.clear();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth API ────────────────────────────────────────────
export const authAPI = {
  login: (badgeNumber: string, password: string, totpToken: string) =>
    api.post('/auth/login', {
      badge_number: badgeNumber,
      password,
      totp_token: totpToken,
      device_fingerprint: computeDeviceFingerprint(),
    }),
  
  me: () => api.get('/auth/me'),
  
  logout: () => api.post('/auth/logout'),
  
  setupMFA: () => api.post('/auth/setup-mfa'),
};

// ─── Cases API ───────────────────────────────────────────
export const casesAPI = {
  list: (params?: { status?: string; page?: number; per_page?: number }) =>
    api.get('/cases', { params }),
  
  get: (caseId: string) => api.get(`/cases/${caseId}`),
  
  create: (data: Record<string, unknown>) => api.post('/cases', data),
  
  update: (caseId: string, data: Record<string, unknown>) =>
    api.patch(`/cases/${caseId}`, data),
  
  requestTransfer: (caseId: string, toOfficerId: string, reason: string) =>
    api.post(`/cases/${caseId}/transfer`, { to_officer_id: toOfficerId, reason }),
  
  uploadEvidence: (caseId: string, formData: FormData) =>
    api.post(`/cases/${caseId}/evidence`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

// ─── AI API ──────────────────────────────────────────────
export const ariaAPI = {
  analyzeCase: (caseId: string) =>
    api.post('/ai/analyze-case', { case_id: caseId }),
  
  analyzeDocument: (text: string, type: string) =>
    api.post('/ai/analyze-document', { document_text: text, document_type: type }),
  
  chat: (message: string, caseId?: string) =>
    api.post('/ai/chat', { message, case_id: caseId }),
  
  suggestSteps: (caseId: string) =>
    api.post('/ai/suggest-investigation-steps', { case_id: caseId }),
};

// ─── Duty API ────────────────────────────────────────────
export const dutyAPI = {
  start: (lat: number, lng: number) =>
    api.post('/duty/start', {
      device_fingerprint: computeDeviceFingerprint(),
      initial_latitude: lat,
      initial_longitude: lng,
    }),
  
  end: () => api.post('/duty/end'),
  
  updateLocation: (lat: number, lng: number, extras?: Record<string, unknown>) =>
    api.post('/duty/location', { latitude: lat, longitude: lng, ...extras }),
  
  panic: (lat: number, lng: number, message?: string) =>
    api.post('/duty/panic', { latitude: lat, longitude: lng, message }),
  
  liveOfficers: () => api.get('/duty/live-officers'),
};

// ─── Admin API ───────────────────────────────────────────
export const adminAPI = {
  dashboard: () => api.get('/admin/dashboard'),
  
  createOfficer: (data: Record<string, unknown>) => api.post('/admin/officers', data),
  
  suspendOfficer: (officerId: string, reason: string) =>
    api.post(`/admin/officers/${officerId}/suspend`, { reason }),
  
  threatReports: () => api.get('/admin/threat-reports'),
  
  auditLogs: (officerId?: string, limit?: number) =>
    api.get('/admin/audit-logs', { params: { officer_id: officerId, limit } }),
};

// ─── CCTV API ────────────────────────────────────────────
export const cctvAPI = {
  cameras: (zone?: string) => api.get('/cctv/cameras', { params: { zone } }),
  
  streamToken: (cameraId: string) => api.get(`/cctv/cameras/${cameraId}/stream`),
  
  recordings: (cameraId: string, date?: string) =>
    api.get(`/cctv/cameras/${cameraId}/recordings`, { params: { date } }),
  
  alerts: () => api.get('/cctv/alerts'),
};

export default api;
