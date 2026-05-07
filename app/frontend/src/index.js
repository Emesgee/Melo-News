// src/index.js
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

if ('serviceWorker' in navigator) {
  if (process.env.NODE_ENV === 'production') {
    // Register service worker only in production to avoid stale dev builds.
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .catch(() => { /* SW registration failed */ });
    });
  } else {
    // Clear old registrations in non-production so normal refresh always picks latest changes.
    navigator.serviceWorker.getRegistrations()
      .then((registrations) => Promise.all(registrations.map((registration) => registration.unregister())))
      .catch(() => { /* Ignore SW cleanup failures */ });
  }
}
