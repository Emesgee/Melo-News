import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { checkAuth, logoutUser } from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children, initialLoggedIn }) => {
  const [isLoggedIn, setIsLoggedIn] = useState(
    typeof initialLoggedIn === 'boolean' ? initialLoggedIn : false
  );
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    checkAuth()
      .then(() => setIsLoggedIn(true))
      .catch(() => setIsLoggedIn(false))
      .finally(() => setAuthLoading(false));
  }, []);

  const login = useCallback(() => setIsLoggedIn(true), []);

  const logout = useCallback(async () => {
    try { await logoutUser(); } catch (_) { /* ignore */ }
    setIsLoggedIn(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isLoggedIn, authLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
