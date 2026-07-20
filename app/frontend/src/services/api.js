import axios from 'axios';

// Use relative /api path so all requests go through Nginx proxy
const API_URL = process.env.REACT_APP_API_URL || '/api';
const ACCESS_TOKEN_KEY = 'melo_access_token';

export const getAccessToken = () => {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  } catch (_) {
    return null;
  }
};

export const setAccessToken = (token) => {
  try {
    if (token) localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } catch (_) {
    // Ignore storage failures in private browsing/restricted environments.
  }
};

export const clearAccessToken = () => {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  } catch (_) {
    // Ignore storage failures.
  }
};

// Axios instance — cookies are sent automatically via withCredentials
export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'X-Requested-With': 'XMLHttpRequest',  // CSRF protection: server can reject non-XHR requests
  },
  withCredentials: true,
});


// User Registration
export const registerUser = async (userData) => {
  return api.post('auth/register', userData);
};

// User Login (server sets httpOnly cookie)
export const loginUser = async (credentials) => {
  return api.post('auth/login', credentials);
};

// User Logout (server clears httpOnly cookie)
export const logoutUser = async () => {
  const resp = await api.post('auth/logout');
  clearAccessToken();
  return resp;
};

// Check current auth status via cookie
export const checkAuth = async () => {
  return api.get('auth/me');
};

// Get Profile Data
export const getProfileData = async () => {
  return api.get('profile', { params: { userData: 'name' } });
};

/** @deprecated Use getProfileData instead */
export const ProfileData = getProfileData;

// Fetch Available File Types
export const fetchFileTypes = async () => {
  return api.get('file-types/');
};

// Test API URL for connectivity
export const testApiUrl = async () => {
  return api.get('test');
};

// News feed — source-agnostic map markers (kept generic fetcher over stories/map)
export const getNewsFeed = async (limit = 100) => {
  return api.get('stories/map', { params: { limit } });
};

// Events feed — the reader-facing corroboration unit (Stage E). Leads with
// CORROBORATED, keeps DISPUTED prominent; only events with verified members.
export const getEvents = async ({ status, q, limit = 100 } = {}) => {
  return api.get('events', { params: { status, q, limit } });
};

export const getEventDetail = async (eventId) => {
  return api.get(`events/${eventId}`);
};

// --- Citizen Upload Management ---

export const getMyUploads = async () => {
  return api.get('file_upload/my-uploads');
};

export const editUpload = async (id, data) => {
  return api.put(`file_upload/${id}`, data);
};

export const deleteUpload = async (id) => {
  return api.delete(`file_upload/${id}`);
};

// --- Editorial Moderation (moderator role required) ---

export const getModerationQueue = async (status = 'PENDING', limit = 50, offset = 0) => {
  return api.get('moderation/queue', { params: { status, limit, offset } });
};

export const verifyUpload = async (id, note = '') => {
  return api.post(`moderation/${id}/verify`, { note });
};

export const rejectUpload = async (id, note) => {
  return api.post(`moderation/${id}/reject`, { note });
};

// --- Steward governance (steward role required) ---
// Rung/role changes are the ADR-0016 bootstrap: an Event cannot auto-reach
// CORROBORATED without a rung-2+ member, so vouching is what lets a drill
// cohort's reports actually corroborate.

export const getIdentities = async () => {
  return api.get('moderation/users');
};

export const setUserRung = async (userId, rung) => {
  return api.post(`moderation/users/${userId}/rung`, { rung });
};

export const setUserRole = async (userId, role) => {
  return api.post(`moderation/users/${userId}/role`, { role });
};

// Financial data (P2-12) - uses free Yahoo Finance API proxy
export const getMarketData = async () => {
  try {
    const resp = await api.get('analytics/market-data');
    return resp.data;
  } catch {
    return null;
  }
};
