import React, { useRef, useEffect } from 'react';
import { useMap } from 'react-leaflet';
import { MAP_STYLES, STYLE_CATEGORIES } from './mapConstants';

export const ZoomCircles = () => {
  const map = useMap();
  const zoomIntervalRef = useRef(null);

  const startZoomIn = () => { zoomIntervalRef.current = setInterval(() => map.setZoom(map.getZoom() + 1), 100); };
  const startZoomOut = () => { zoomIntervalRef.current = setInterval(() => map.setZoom(map.getZoom() - 1), 100); };
  const stopZoom = () => { clearInterval(zoomIntervalRef.current); };

  return (
    <div className="zoom-circles">
      <div className="zoom-circle zoom-in" onMouseDown={startZoomIn} onTouchStart={startZoomIn} onMouseUp={stopZoom} onTouchEnd={stopZoom} onMouseLeave={stopZoom}>+</div>
      <div className="zoom-circle zoom-out" onMouseDown={startZoomOut} onTouchStart={startZoomOut} onMouseUp={stopZoom} onTouchEnd={stopZoom} onMouseLeave={stopZoom}>-</div>
    </div>
  );
};

export const FitBounds = ({ bounds }) => {
  const map = useMap();
  const prevCountRef = useRef(0);

  useEffect(() => {
    if (bounds && bounds.length > 0 && bounds.length !== prevCountRef.current) {
      try {
        map.fitBounds(bounds, { padding: [40, 40] });
        prevCountRef.current = bounds.length;
      } catch (e) {
        /* fitting bounds failed */
      }
    }
  }, [bounds, map]);

  return null;
};

export const MapStylePanel = ({ currentStyle, onStyleChange, onClose }) => (
  <div className="map-style-panel">
    <div className="map-style-panel-header">
      <span>Map Style</span>
      <button className="map-style-close" onClick={onClose} title="Close">✕</button>
    </div>
    {STYLE_CATEGORIES.map(cat => {
      const styles = MAP_STYLES.filter(s => s.category === cat);
      if (!styles.length) return null;
      return (
        <div key={cat} className="map-style-category-group">
          <div className="map-style-category-label">{cat}</div>
          <div className="map-style-grid">
            {styles.map(style => (
              <button
                key={style.id}
                className={`map-style-option${currentStyle.id === style.id ? ' active' : ''}`}
                onClick={() => { onStyleChange(style); onClose(); }}
                title={style.name}
              >
                <div className="map-style-swatch" style={{ background: style.swatch }} />
                <span className="map-style-name">{style.name}</span>
                {currentStyle.id === style.id && <span className="map-style-check">✓</span>}
              </button>
            ))}
          </div>
        </div>
      );
    })}
  </div>
);
