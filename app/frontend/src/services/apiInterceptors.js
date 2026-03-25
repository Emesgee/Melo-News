import { api } from './api';

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1000;

/**
 * Determine if a failed request should be retried.
 * Only retry network errors and 5xx server errors (not 4xx client errors).
 */
const shouldRetry = (error) => {
  if (!error.response) return true; // Network error (no response at all)
  const status = error.response.status;
  return status >= 500 && status < 600;
};

/**
 * Setup axios interceptors for:
 * - Automatic retry with exponential backoff (network errors + 5xx)
 * - Centralized error toasts via addToast callback
 * - Auth session expiry detection (401 → redirect to login)
 *
 * Call this once from the app root after ToastContext is available.
 *
 * @param {Function} addToast - (message, type, duration?) => void
 * @param {Function} onAuthExpired - () => void (called on 401)
 */
export const setupInterceptors = (addToast, onAuthExpired) => {
  // ── Request interceptor: attach retry counter ──────────────────
  api.interceptors.request.use((config) => {
    config.__retryCount = config.__retryCount || 0;
    return config;
  });

  // ── Response interceptor: retry + error toasts ─────────────────
  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const config = error.config || {};

      // ── Retry logic ────────────────────────────────────────────
      if (shouldRetry(error) && config.__retryCount < MAX_RETRIES) {
        config.__retryCount += 1;
        const delay = RETRY_DELAY_MS * Math.pow(2, config.__retryCount - 1);
        await new Promise((resolve) => setTimeout(resolve, delay));
        return api(config);
      }

      // ── Centralized error handling (after retries exhausted) ───
      const status = error.response?.status;
      const serverMessage =
        error.response?.data?.error ||
        error.response?.data?.message ||
        error.response?.data?.detail;

      // Auth expiry
      if (status === 401) {
        // Don't toast for auth/me checks (silent auth probe)
        if (!config.url?.includes('auth/me')) {
          addToast('Session expired. Please log in again.', 'warning');
          onAuthExpired?.();
        }
        return Promise.reject(error);
      }

      // Forbidden
      if (status === 403) {
        addToast('You do not have permission to perform this action.', 'error');
        return Promise.reject(error);
      }

      // Rate limited
      if (status === 429) {
        addToast('Too many requests. Please wait a moment and try again.', 'warning');
        return Promise.reject(error);
      }

      // Server errors (after retries failed)
      if (status >= 500) {
        addToast(
          serverMessage || 'Server error. Please try again later.',
          'error',
        );
        return Promise.reject(error);
      }

      // Network error (no response at all, retries exhausted)
      if (!error.response) {
        addToast(
          'Network error. Please check your connection.',
          'error',
        );
        return Promise.reject(error);
      }

      // Other client errors (400, 404, 422, etc.) — let calling code handle these
      // but show a toast if there's a server message
      if (serverMessage && status !== 400) {
        addToast(serverMessage, 'error');
      }

      return Promise.reject(error);
    },
  );
};
