import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

const ToastContext = createContext();

let toastIdCounter = 0;

/**
 * Toast types: 'success' | 'error' | 'warning' | 'info'
 *
 * Usage:
 *   const { addToast } = useToast();
 *   addToast('Something went wrong', 'error');
 *   addToast('Saved!', 'success', 3000);
 */
export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef({});

  const removeToast = useCallback((id) => {
    clearTimeout(timersRef.current[id]);
    delete timersRef.current[id];
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = ++toastIdCounter;
    setToasts((prev) => [...prev.slice(-4), { id, message, type }]); // Keep max 5

    if (duration > 0) {
      timersRef.current[id] = setTimeout(() => removeToast(id), duration);
    }

    return id;
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
};

export const useToast = () => useContext(ToastContext);
