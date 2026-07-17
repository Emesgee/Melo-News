import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip, useMap } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './MapArea.css';
import MarkerClusterGroup from 'react-leaflet-markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { getEvents } from '../../services/api';
import { useSearch } from '../../utils/SearchContext';
import { useDarkMode } from '../../utils/DarkModeContext';
import { MAP_STYLES, defaultPosition } from './mapConstants';
import { ZoomCircles, FitBounds } from './MapControls';

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

// Flies/zooms the map to `target` ({lat, lon, t}) whenever it changes. `t` is a
// nonce so re-selecting the same incident still re-triggers the fly.
function FlyTo({ target }) {
  const map = useMap();
  useEffect(() => {
    if (target && target.lat != null && target.lon != null) {
      map.flyTo([target.lat, target.lon], 13, { duration: 0.8 });
    }
  }, [target, map]);
  return null;
}

const _RANK = { CORROBORATED: 0, DISPUTED: 1, DEVELOPING: 2, CLOSED: 3 };

// Overlay styles (inline, self-contained — no CSS file changes).
const panelStyle = {
  position: 'absolute', top: 12, left: 12, zIndex: 1000, width: 264,
  maxHeight: '58vh', overflowY: 'auto', background: 'var(--bg-primary, #fff)',
  border: '1px solid var(--border-color, #ddd)', borderRadius: 8,
  boxShadow: '0 2px 10px rgba(0,0,0,0.18)', fontSize: 13,
};
const panelHeader = {
  position: 'sticky', top: 0, padding: '8px 12px', fontWeight: 600,
  background: 'var(--bg-secondary, #f5f5f5)', borderBottom: '1px solid var(--border-color, #ddd)',
  color: 'var(--text-primary, #222)',
};
const itemStyle = {
  display: 'flex', alignItems: 'center', gap: 8, width: '100%',
  padding: '7px 12px', border: 'none', borderBottom: '1px solid var(--border-color, #eee)',
  background: 'transparent', cursor: 'pointer', color: 'var(--text-primary, #222)',
};
const dotStyle = { width: 9, height: 9, borderRadius: '50%', flex: '0 0 auto' };

const MapArea = () => {
  const navigate = useNavigate();
  const { filter } = useSearch();
  const { isDark } = useDarkMode();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [focus, setFocus] = useState(null);

  // Basemap follows the app theme — light in light mode, dark in dark. No picker.
  const tile = MAP_STYLES[isDark ? 1 : 0];

  useEffect(() => {
    let alive = true;
    setLoading(true);
    (async () => {
      try {
        const res = await getEvents({ q: filter.q, status: filter.status, limit: 200 });
        if (alive) setEvents(res.data?.events || []);
      } catch (e) {
        if (alive) setEvents([]);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, [filter.q, filter.status]);

  const pins = useMemo(
    () => (events || []).filter((ev) => ev.location && ev.location.lat != null && ev.location.lon != null),
    [events],
  );
  const bounds = useMemo(() => pins.map((ev) => [ev.location.lat, ev.location.lon]), [pins]);
  const listed = useMemo(
    () => [...pins].sort((a, b) =>
      (_RANK[a.status] ?? 9) - (_RANK[b.status] ?? 9) ||
      (a.title || '').localeCompare(b.title || '')),
    [pins],
  );

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

      {pins.length > 0 && (
        <div style={panelStyle} aria-label="Incident list — click to locate">
          <div style={panelHeader}>Incidents · {pins.length}</div>
          {listed.map((ev) => (
            <button
              key={ev.id}
              type="button"
              style={itemStyle}
              title="Zoom to this incident"
              onClick={() => setFocus({ lat: ev.location.lat, lon: ev.location.lon, t: Date.now() })}
            >
              <span style={{ ...dotStyle, background: STATUS_COLOR[ev.status] || STATUS_COLOR.DEVELOPING }} />
              <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {ev.title || 'Incident'}
              </span>
              <span style={{ color: 'var(--text-secondary, #777)', marginLeft: 6, flex: '0 0 auto' }}>
                {ev.location.city}
              </span>
            </button>
          ))}
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
          <TileLayer url={tile.url} attribution={tile.attribution} />
          <ZoomCircles />
          <FlyTo target={focus} />
          {bounds.length > 0 && !focus && <FitBounds bounds={bounds} />}

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

    </div>
  );
};

export default MapArea;
