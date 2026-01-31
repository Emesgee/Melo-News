// src/index.js
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

// Debug: Check if environment variables are loaded
console.log('[DEBUG] REACT_APP_API_URL:', process.env.REACT_APP_API_URL);
console.log('[DEBUG] All env vars:', process.env);

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
