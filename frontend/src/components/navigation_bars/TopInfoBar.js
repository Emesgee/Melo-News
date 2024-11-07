// src/pages/InfoSidebar.js
import React from 'react';
import { useNavigate } from 'react-router-dom';
import './TopInfoBar.css';

const TopInfoBar = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');  // Navigate to the login page
  };

  const handleUpload = () => {
    navigate('/upload');  // Navigate to the upload page
  };

  return (
    <div className="top-infobar">
      <h1 className="welcome">Welcome</h1>

      {/* Button for Logout with SVG Icon */}
      <button className="icon-button" onClick={handleLogout}>
        <svg
          className="icon icon--account icon--grey icon--24"
          viewBox="0 24 24"
          version="1.1"
          aria-hidden="true"
        >
          <title>Logout</title>
          <path
            fill="none"
            fillRule="evenodd"
            stroke="#000"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            transform="translate(1 1)"
            className="icon-main-color"
            d="M6 20v-1.815c0-.58.21-1.135.586-1.545C6.96 16.23 7.47 16 8 16h6c.53 0 1.04.23 1.414.64.375.41.586.965.586 1.545V20m6-9c0 6.075-4.925 11-11 11S0 17.075 0 11 4.925 0 11 0s11 4.925 11 11Zm-8-2a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
          ></path>
        </svg>
      </button>

      {/* Button for Upload with SVG Icon */}
      <button className="icon-button" onClick={handleUpload}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="lucide lucide-cloud-upload"
        >
          <title>Upload</title>
          <path d="M12 13v8" />
          <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
          <path d="m8 17 4-4 4 4" />
        </svg>
      </button>
    </div>
  );
};

export default TopInfoBar;
