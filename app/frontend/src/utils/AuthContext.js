import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { checkAuth, logoutUser } from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children, initialLoggedIn }) => {
  const [isLoggedIn, setIsLoggedIn] = useState(
    typeof initialLoggedIn === 'boolean' ? initialLoggedIn : false
  );
  const [isModerator, setIsModerator] = useState(false);
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  const refreshAuth = useCallback(async () => {
    try {
      const resp = await checkAuth();
      setIsLoggedIn(true);
      setIsModerator(Boolean(resp?.data?.is_moderator));
      setUser(resp?.data || null);
    } catch (_) {
      setIsLoggedIn(false);
      setIsModerator(false);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refreshAuth().finally(() => setAuthLoading(false));
  }, [refreshAuth]);

  const login = useCallback(() => {
    setIsLoggedIn(true);
    // Re-fetch /me so we pick up is_moderator without waiting for a reload
    refreshAuth();
  }, [refreshAuth]);

  const logout = useCallback(async () => {
    try { await logoutUser(); } catch (_) { /* ignore */ }
    setIsLoggedIn(false);
    setIsModerator(false);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ isLoggedIn, isModerator, user, authLoading, login, logout, refreshAuth }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
