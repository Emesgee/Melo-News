import React, { useRef, useEffect } from 'react';
import { useMap } from 'react-leaflet';

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
