// src/pages/Intro.js
import React, { useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Intro.css';
import SoundwaveVisualizer from '../components/SoundwaveVisualizer';
import ArrowPulse from '../components/ArrowPulse';
import { getNetworkProfile, NETWORK_TIERS } from '../utils/connectivityPolicy';

const INTRO_METRICS_KEY = 'melo_intro_metrics';

const TIER_META = {
  [NETWORK_TIERS.OFFLINE]: {
    label: 'Offline',
    detail: 'No active connection. Stories will queue.',
    tone: 'offline',
  },
  [NETWORK_TIERS.CRITICAL]: {
    label: 'Critical',
    detail: 'Very weak connection. Minimal upload mode.',
    tone: 'critical',
  },
  [NETWORK_TIERS.CONSTRAINED]: {
    label: 'Constrained',
    detail: 'Reduced mode. Heavy processing is limited.',
    tone: 'constrained',
  },
  [NETWORK_TIERS.NORMAL]: {
    label: 'Normal',
    detail: 'Full mode available.',
    tone: 'normal',
  },
};

const summarizeIntroMetrics = (metrics) => {
  if (!Array.isArray(metrics) || metrics.length === 0) return null;

  const valid = metrics.filter((item) => Number.isFinite(item?.elapsedMs));
  if (valid.length === 0) return null;

  const times = valid.map((item) => item.elapsedMs).sort((a, b) => a - b);
  const midpoint = Math.floor(times.length / 2);
  const medianMs = times.length % 2 === 0
    ? Math.round((times[midpoint - 1] + times[midpoint]) / 2)
    : times[midpoint];

  const actionCounts = valid.reduce((acc, item) => {
    const key = item.action || 'unknown';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const topAction = Object.entries(actionCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0] || 'unknown';

  return {
    count: valid.length,
    medianMs,
    minMs: times[0],
    maxMs: times[times.length - 1],
    topAction,
    actionCounts,
    sampleTarget: 30,
    confidenceLabel: valid.length >= 30 ? 'higher confidence' : 'low confidence',
  };
};

const Intro = () => {
  const navigate = useNavigate();
  const primaryActionRef = useRef(null);
  const cameraInputRef = useRef(null);
  const voiceInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const introStartTimeRef = useRef(typeof performance !== 'undefined' ? performance.now() : Date.now());
  const firstActionTrackedRef = useRef(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [lowBandwidth, setLowBandwidth] = useState(false);
  const [autoStripGps, setAutoStripGps] = useState(false);
  const [networkProfile, setNetworkProfile] = useState(() => getNetworkProfile());
  const [devMetrics, setDevMetrics] = useState(null);
  const showDevMetrics = process.env.NODE_ENV !== 'production';

  useEffect(() => {
    const updateNetworkProfile = () => setNetworkProfile(getNetworkProfile());

    updateNetworkProfile();

    const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    window.addEventListener('online', updateNetworkProfile);
    window.addEventListener('offline', updateNetworkProfile);

    if (connection?.addEventListener) {
      connection.addEventListener('change', updateNetworkProfile);
    }

    return () => {
      window.removeEventListener('online', updateNetworkProfile);
      window.removeEventListener('offline', updateNetworkProfile);
      if (connection?.removeEventListener) {
        connection.removeEventListener('change', updateNetworkProfile);
      }
    };
  }, []);

  useEffect(() => {
    if (!showDevMetrics) return;

    const refreshMetrics = () => {
      try {
        const raw = sessionStorage.getItem(INTRO_METRICS_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        setDevMetrics(summarizeIntroMetrics(parsed));
      } catch (_) {
        setDevMetrics(null);
      }
    };

    refreshMetrics();
    window.addEventListener('melo:intro-first-action', refreshMetrics);

    return () => {
      window.removeEventListener('melo:intro-first-action', refreshMetrics);
    };
  }, [showDevMetrics]);

  useEffect(() => {
    const focusTimer = window.setTimeout(() => {
      primaryActionRef.current?.focus({ preventScroll: true });
    }, 0);

    return () => window.clearTimeout(focusTimer);
  }, []);

  const tierMeta = TIER_META[networkProfile.tier] || TIER_META[NETWORK_TIERS.NORMAL];
  const lowMotionMode = networkProfile.tier !== NETWORK_TIERS.NORMAL;

  const trackFirstAction = (actionName) => {
    if (firstActionTrackedRef.current) return;
    firstActionTrackedRef.current = true;

    const now = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const elapsedMs = Math.max(0, Math.round(now - introStartTimeRef.current));
    const eventPayload = {
      event: 'intro_first_action',
      action: actionName,
      elapsedMs,
      tier: networkProfile.tier,
      downlink: networkProfile.downlink,
      timestamp: new Date().toISOString(),
    };

    try {
      window.dispatchEvent(new CustomEvent('melo:intro-first-action', { detail: eventPayload }));
    } catch (_) {
      // Ignore custom event dispatch failures.
    }

    const telemetryUrl = process.env.REACT_APP_INTRO_TELEMETRY_URL;
    if (telemetryUrl) {
      try {
        const body = JSON.stringify(eventPayload);
        if (navigator.sendBeacon) {
          navigator.sendBeacon(telemetryUrl, new Blob([body], { type: 'application/json' }));
          return;
        }

        fetch(telemetryUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body,
          keepalive: true,
        }).catch(() => {
          // Ignore telemetry network failures.
        });
        return;
      } catch (_) {
        // Fall back to local telemetry store.
      }
    }

    try {
      const existing = JSON.parse(sessionStorage.getItem(INTRO_METRICS_KEY) || '[]');
      existing.push(eventPayload);
      sessionStorage.setItem(INTRO_METRICS_KEY, JSON.stringify(existing.slice(-20)));
    } catch (_) {
      // Ignore storage failures.
    }
  };

  const uploadPreferences = {
    lowBandwidth,
    autoStripGps,
  };

  const handleQuickPick = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    navigate('/my-uploads', {
      state: {
        openCreate: true,
        quickFile: file,
        uploadPreferences,
      },
    });
  };

  const handleSkip = () => {
    trackFirstAction('open_full_form_tap');
    navigate('/my-uploads', {
      state: {
        openCreate: true,
        uploadPreferences,
      },
    });
  };

  return (
    <section className={`intro-launcher${lowMotionMode ? ' intro-low-motion' : ''}`}>
      <div className="intro-noise"></div>
      <div className="intro-panel">
        <p className="intro-eyebrow">Fast Desk</p>
        <h1>Capture and publish now</h1>
        <p className="intro-copy">
          Tap camera to start. Use voice or file only when needed.
        </p>

        <div className={`intro-tier-chip ${tierMeta.tone}`}>
          <span className={`intro-tier-pulse ${tierMeta.tone}`} aria-hidden="true" />
          <strong>{tierMeta.label} mode</strong>
          {networkProfile.downlink !== null ? <small>{networkProfile.downlink.toFixed(1)} Mbps</small> : null}
        </div>

        <div className="intro-tier-detail">
          {tierMeta.detail}
        </div>

        <div className="intro-actions">
          <button
            ref={primaryActionRef}
            type="button"
            className="intro-action primary intro-camera-action"
            onClick={() => {
              trackFirstAction('open_camera_tap');
              cameraInputRef.current?.click();
            }}
          >
            <span className="intro-camera-visual" aria-hidden="true">
              <span className="intro-camera-ring intro-camera-ring-outer"></span>
              <span className="intro-camera-ring intro-camera-ring-mid"></span>
              <span className="intro-camera-ring intro-camera-ring-inner"></span>
              <span className="intro-camera-aperture intro-camera-aperture-a"></span>
              <span className="intro-camera-aperture intro-camera-aperture-b"></span>
              <span className="intro-camera-aperture intro-camera-aperture-c"></span>
              <span className="intro-camera-core">
                <span className="intro-camera-glass"></span>
              </span>
            </span>
            <span className="intro-camera-copy">
              <span className="intro-action-title">Open Camera</span>
              <span className="intro-action-sub">Fastest start</span>
            </span>
          </button>

          <div className="intro-secondary-actions" role="group" aria-label="Other quick options">
            <button
              type="button"
              className="intro-action intro-voice-action"
              onClick={() => {
                trackFirstAction('record_voice_tap');
                voiceInputRef.current?.click();
              }}
            >
              <span className="intro-voice-visual" aria-hidden="true">
                <SoundwaveVisualizer
                  width={280}
                  height={100}
                  barCount={56}
                  color="rgba(100, 225, 255, 0.7)"
                  secondaryColor="rgba(255, 255, 255, 0.3)"
                  animationSpeed={0.06}
                />
              </span>
              <span className="intro-voice-copy">
                <span className="intro-action-title">Record Voice</span>
                <span className="intro-action-sub">Voice only</span>
              </span>
            </button>

            <button
              type="button"
              className="intro-action intro-file-action"
              onClick={() => {
                trackFirstAction('choose_file_tap');
                fileInputRef.current?.click();
              }}
            >
              <span className="intro-file-visual" aria-hidden="true">
                <ArrowPulse color="rgba(167, 139, 250, 0.8)" size={36} />
              </span>
              <span className="intro-file-copy">
                <span className="intro-action-title">Choose File</span>
                <span className="intro-action-sub">From phone storage</span>
              </span>
            </button>
          </div>
        </div>

        <button
          type="button"
          className="intro-advanced-toggle"
          onClick={() => setShowAdvanced((prev) => !prev)}
          aria-expanded={showAdvanced}
        >
          {showAdvanced ? 'Hide settings' : 'More settings'}
        </button>

        {showAdvanced && (
          <div className="intro-advanced-panel">
            <label className="intro-advanced-item">
              <input
                type="checkbox"
                checked={lowBandwidth}
                onChange={(e) => setLowBandwidth(e.target.checked)}
              />
              <span>
                <strong>Low bandwidth mode</strong>
                <small>Disable instant AI analysis for faster, safer upload on weak networks.</small>
              </span>
            </label>

            <label className="intro-advanced-item">
              <input
                type="checkbox"
                checked={autoStripGps}
                onChange={(e) => setAutoStripGps(e.target.checked)}
              />
              <span>
                <strong>Auto-remove GPS metadata</strong>
                <small>When photo EXIF has GPS, strip it automatically before upload.</small>
              </span>
            </label>
          </div>
        )}

        <button className="intro-skip-btn" onClick={handleSkip}>
          Open full form
        </button>

        {showDevMetrics && devMetrics ? (
          <section className="intro-dev-metrics" aria-live="polite">
            <strong>Intro metrics (dev only)</strong>
            <div className="intro-dev-metrics-row">
              <span>{devMetrics.count} samples</span>
              <span>Median {devMetrics.medianMs} ms</span>
              <span>Top {devMetrics.topAction}</span>
            </div>
            <div className="intro-dev-metrics-row">
              <span>Min {devMetrics.minMs} ms</span>
              <span>Max {devMetrics.maxMs} ms</span>
              <span>
                Target {devMetrics.sampleTarget}+ ({devMetrics.confidenceLabel})
              </span>
            </div>
            <div className="intro-dev-metrics-actions">
              {Object.entries(devMetrics.actionCounts).map(([action, count]) => (
                <span key={action}>{action}: {count}</span>
              ))}
            </div>
          </section>
        ) : null}

        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*,video/*"
          capture="environment"
          onChange={handleQuickPick}
          className="intro-hidden-input"
        />
        <input
          ref={voiceInputRef}
          type="file"
          accept="audio/*"
          capture
          onChange={handleQuickPick}
          className="intro-hidden-input"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*,audio/*"
          onChange={handleQuickPick}
          className="intro-hidden-input"
        />
      </div>

      <button
        type="button"
        className="intro-map-link"
        onClick={() => navigate('/map')}
        title="View map and browse all stories"
      >
        Explore map
      </button>
    </section>
  );
};

export default Intro;
