import React, { useEffect, useRef, useCallback, useState } from 'react';
import Globe from 'react-globe.gl';
import './GlobeView.css';

// Severity → color mapping
const SEVERITY_COLORS = {
  HIGH:   { bg: '#ef4444', glow: 'rgba(239,68,68,0.55)' },
  MEDIUM: { bg: '#f97316', glow: 'rgba(249,115,22,0.55)' },
  LOW:    { bg: '#6b7280', glow: 'rgba(107,114,128,0.45)' },
};

const GlobeView = ({ points = [], onPointClick }) => {
  const globeEl  = useRef();
  const wrapRef  = useRef();
  const [dims, setDims] = useState({ w: window.innerWidth, h: window.innerHeight });

  /* ── responsive sizing ── */
  useEffect(() => {
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      setDims({ w: width, h: height });
    });
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  /* ── globe init ── */
  useEffect(() => {
    if (!globeEl.current) return;
    const controls = globeEl.current.controls();
    controls.autoRotate      = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableZoom      = true;
    controls.minDistance     = 150;
    controls.maxDistance     = 800;
    // Focus on Palestine / Middle East
    globeEl.current.pointOfView({ lat: 31.9, lng: 35.2, altitude: 2.2 }, 1200);
  }, []);

  /* ── stop auto-rotate on user interaction ── */
  useEffect(() => {
    if (!globeEl.current) return;
    const controls = globeEl.current.controls();
    const stop = () => { controls.autoRotate = false; };
    const el = globeEl.current.renderer().domElement;
    el.addEventListener('pointerdown', stop);
    return () => el.removeEventListener('pointerdown', stop);
  }, []);

  /* ── create HTML marker element ── */
  const createMarkerEl = useCallback((d) => {
    const { bg, glow } = SEVERITY_COLORS[d.severity] || SEVERITY_COLORS.MEDIUM;

    const wrap = document.createElement('div');
    wrap.className = 'globe-marker-wrap';
    wrap.title = d.title || 'Incident';

    // Outer pulse ring
    const ring = document.createElement('div');
    ring.className = 'globe-marker-ring';
    ring.style.setProperty('--ring-color', glow);

    // Inner dot
    const dot = document.createElement('div');
    dot.className = 'globe-marker-dot';
    dot.style.setProperty('--dot-color', bg);
    dot.style.setProperty('--dot-glow', glow);

    wrap.appendChild(ring);
    wrap.appendChild(dot);

    wrap.addEventListener('mouseenter', () => dot.classList.add('hovered'));
    wrap.addEventListener('mouseleave', () => dot.classList.remove('hovered'));

    wrap.addEventListener('click', (e) => {
      e.stopPropagation();
      if (onPointClick) onPointClick(d);
    });

    return wrap;
  }, [onPointClick]);

  return (
    <div className="globe-view-container" ref={wrapRef}>
      <Globe
        ref={globeEl}
        width={dims.w}
        height={dims.h}
        /* ── earth textures ── */
        globeImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-dark.jpg"
        bumpImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-topology.png"
        backgroundImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/night-sky.png"
        /* ── atmosphere ── */
        showAtmosphere
        atmosphereColor="rgba(180, 20, 20, 0.35)"
        atmosphereAltitude={0.13}
        /* ── graticule grid ── */
        showGraticules
        /* ── incident markers ── */
        htmlElementsData={points}
        htmlElement={createMarkerEl}
        htmlAltitude={0.015}
        htmlTransitionDuration={300}
      />

      {/* ── Legend ── */}
      <div className="globe-legend">
        <div className="globe-legend-item">
          <span className="globe-legend-dot high" />
          <span>High</span>
        </div>
        <div className="globe-legend-item">
          <span className="globe-legend-dot medium" />
          <span>Medium</span>
        </div>
        <div className="globe-legend-item">
          <span className="globe-legend-dot low" />
          <span>Low</span>
        </div>
        <span className="globe-legend-sep">|</span>
        <span className="globe-legend-count">{points.length} incident{points.length !== 1 ? 's' : ''}</span>
      </div>

      {/* ── Hint ── */}
      <div className="globe-hint">Drag to rotate · Scroll to zoom · Click marker for details</div>
    </div>
  );
};

export default GlobeView;
