import React, { useState, useEffect, useMemo, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './MapArea.css';
import MarkerClusterGroup from 'react-leaflet-markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { getEvents } from '../../services/api';
import { MAP_STYLES, defaultPosition } from './mapConstants';
import { ZoomCircles, FitBounds, MapStylePanel } from './MapControls';

// The map is a feed of Events: one status-colored pin per incident. Clicking a
// pin opens the shareable /events/:id page (the same place a List card goes).
// No raw-report markers, no media popups — the unit is the Event.

const STATUS_COLOR = {
  CORROBORATED: '#15803d',
  DISPUTED: '#b91c1c',
  DEVELOPING: '#a16207',
  CLOSED: '#6b7280',
};

const eventIcon = (status) => {
  const color = STATUS_COLOR[status] || STATUS_COLOR.DEVELOPING;
  return L.divIcon({
    className: 'event-pin',
    html: `<span class="event-pin-dot" style="background:${color}"></span>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
};

const MapArea = () => {
  const navigate = useNavigate();
  const [currentStyle, setCurrentStyle] = useState(MAP_STYLES[0]);
  const [showStylePicker, setShowStylePicker] = useState(false);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const stylePanelRef = useRef(null);

  // Close the style picker on outside click
  useEffect(() => {
    const handleOutside = (e) => {
      if (stylePanelRef.current && !stylePanelRef.current.contains(e.target)) {
        setShowStylePicker(false);
      }
    };
    if (showStylePicker) document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [showStylePicker]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await getEvents({ limit: 200 });
        if (alive) setEvents(res.data?.events || []);
      } catch (e) {
        if (alive) setEvents([]);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const pins = useMemo(
    () => (events || []).filter((ev) => ev.location && ev.location.lat != null && ev.location.lon != null),
    [events],
  );
  const bounds = useMemo(() => pins.map((ev) => [ev.location.lat, ev.location.lon]), [pins]);

  return (
    <div className="map-area">
      {!loading && pins.length === 0 && (
        <div className="map-empty-state">
          <div className="map-empty-title">No events on the map yet</div>
          <div className="map-empty-sub">
            This is a young, closed pilot. Corroborated reports appear here as independent reporters file them.
          </div>
        </div>
      )}

      <div className="map-container" style={{ width: '100%', height: '100vh' }}>
        <MapContainer
          center={defaultPosition}
          zoom={6}
          minZoom={2}
          maxZoom={14}
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
          attributionControl={false}
        >
          <TileLayer url={currentStyle.url} attribution={currentStyle.attribution} />
          <ZoomCircles />
          {bounds.length > 0 && <FitBounds bounds={bounds} />}

          <MarkerClusterGroup chunkedLoading showCoverageOnHover={false} spiderfyOnMaxZoom>
            {pins.map((ev) => (
              <Marker
                key={ev.id}
                position={[ev.location.lat, ev.location.lon]}
                icon={eventIcon(ev.status)}
                eventHandlers={{ click: () => navigate(`/events/${ev.id}`) }}
              >
                <Tooltip direction="top" offset={[0, -10]}>
                  <strong>{ev.title || 'Incident'}</strong>
                  <br />
                  {ev.status}
                  {ev.corroboration?.counted > 0 ? ` · ✓ ${ev.corroboration.counted}` : ''}
                </Tooltip>
              </Marker>
            ))}
          </MarkerClusterGroup>
        </MapContainer>
      </div>

      {/* Map overlay controls */}
      <div className="map-overlay-controls" ref={stylePanelRef}>
        <button
          className={`map-style-toggle${showStylePicker ? ' active' : ''}`}
          onClick={() => setShowStylePicker((v) => !v)}
          title="Change map style"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
            <line x1="8" y1="2" x2="8" y2="18" />
            <line x1="16" y1="6" x2="16" y2="22" />
          </svg>
        </button>
        <span className="map-current-style-badge">{currentStyle.name}</span>
        {showStylePicker && (
          <MapStylePanel
            currentStyle={currentStyle}
            onStyleChange={setCurrentStyle}
            onClose={() => setShowStylePicker(false)}
          />
        )}
      </div>
    </div>
  );
};

export default MapArea;
