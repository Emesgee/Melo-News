import React from 'react';
import { Link } from 'react-router-dom';

// The web is the reader + moderation surface (ADR-0001/0007). Reporting happens
// in the Android app, where reports are signed on-device (tamper-evident),
// work offline, and have EXIF stripped — none of which a browser can do. So the
// old /upload form is gone; visitors who want to report land here instead.

const wrap = {
  maxWidth: 520,
  margin: '0 auto',
  padding: '48px 16px',
  textAlign: 'center',
};
const card = {
  background: 'var(--bg-primary)',
  border: '1px solid var(--border-color)',
  borderRadius: 'var(--radius-lg)',
  padding: '28px 24px',
  boxShadow: 'var(--shadow-sm)',
};
const lead = { color: 'var(--text-primary)', fontSize: '0.95rem', lineHeight: 1.6, margin: '0 0 12px' };
const muted = { color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.6, margin: '0 0 20px' };

const GetTheApp = () => (
  <div style={wrap}>
    <div style={card}>
      <div style={{ fontSize: '2rem', marginBottom: 8 }}>📱</div>
      <h1 className="mn-screen-title" style={{ marginBottom: 12 }}>Reporting happens in the app</h1>
      <p style={lead}>
        Melo News reports are filed from the Android app. It signs each report on your
        device so readers can verify it wasn’t tampered with, works offline, and strips
        location metadata from photos before they’re sent — none of which a browser can do.
      </p>
      <p style={muted}>Ask the Melo News team for access to the app.</p>
      <Link to="/" className="mn-btn mn-btn--outlined">← Back to the map</Link>
    </div>
  </div>
);

export default GetTheApp;
