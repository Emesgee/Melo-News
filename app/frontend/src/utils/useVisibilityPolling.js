import { useEffect, useRef, useCallback } from 'react';

/**
 * Poll a callback at a given interval, but only when the tab is visible.
 * Automatically pauses when the user switches tabs and resumes on return.
 *
 * @param {Function} callback - Async or sync function to call on each tick
 * @param {number} intervalMs - Polling interval in milliseconds
 * @param {boolean} enabled - Whether polling is active (set false to fully disable)
 */
const useVisibilityPolling = (callback, intervalMs, enabled = true) => {
  const intervalRef = useRef(null);
  const callbackRef = useRef(callback);

  // Keep callback ref fresh without re-creating the effect
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const start = useCallback(() => {
    if (intervalRef.current) return;
    intervalRef.current = setInterval(() => callbackRef.current(), intervalMs);
  }, [intervalMs]);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!enabled) { stop(); return; }

    // Initial call
    callbackRef.current();

    // Start polling if tab is visible
    if (!document.hidden) start();

    const handleVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        callbackRef.current(); // Fetch fresh data immediately on tab return
        start();
      }
    };

    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      stop();
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [enabled, start, stop]);
};

export default useVisibilityPolling;
