// src/components/navigation_bars/TopInfoBar.js
import React from 'react';
import { useNavigate } from 'react-router-dom';
import './TopInfoBar.css';

const TopInfoBar = ({
  isBusy = false,
  onUpload,
  onLogin,
}) => {
  const navigate = useNavigate();

  const handleUpload = () => {
    if (isBusy) return;
    if (typeof onUpload === 'function') {
      onUpload();
      return;
    }
    navigate('/upload');
  };

  const handleLogin = () => {
    if (isBusy) return;
    if (typeof onLogin === 'function') {
      onLogin();
      return;
    }
    navigate('/login');
  };

  return (
    <div className={`top-infobar top-infobar--compact${isBusy ? ' is-busy' : ''}`} data-busy={isBusy}>
      <div className="top-actions">
        <button
          type="button"
          className="icon-button has-label"
          onClick={handleUpload}
          aria-label="Upload file"
          title="Upload file"
          disabled={isBusy}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="lucide lucide-cloud-upload"
            aria-hidden="true"
          >
            <path d="M12 13v8" />
            <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
            <path d="m8 17 4-4 4 4" />
          </svg>
          <span className="btn-label">Upload File</span>
        </button>

        <button
          type="button"
          className="icon-button login has-label"
          onClick={handleLogin}
          aria-label="Login"
          title="Login"
          disabled={isBusy}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
            <polyline points="10 17 15 12 10 7" />
            <line x1="15" y1="12" x2="3" y2="12" />
          </svg>
          <span className="btn-label">Login</span>
        </button>
      </div>
    </div>
  );
};

export default TopInfoBar;
