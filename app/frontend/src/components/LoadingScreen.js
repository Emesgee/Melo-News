import React from 'react';
import './LoadingScreen.css';

/**
 * Shown while AuthContext verifies the session.
 * No fake delays — it renders until the parent stops mounting it.
 */
const LoadingScreen = () => (
  <div className="loading-screen">
    <h1 className="loading-screen__title">MELO-NEWS</h1>
    <p className="loading-screen__subtitle">Community Intelligence Platform</p>

    <div className="loading-screen__progress">
      <div className="loading-screen__progress-header">
        <span className="loading-screen__progress-label">LOADING</span>
      </div>
      <div className="loading-screen__bar-bg">
        <div className="loading-screen__bar-fill loading-screen__bar-fill--indeterminate" />
      </div>
    </div>

    <div className="loading-screen__steps">
      <div className="loading-screen__step loading-screen__step--active">
        <span>›</span>
        <span>Verifying session…</span>
      </div>
    </div>
  </div>
);

export default LoadingScreen;
