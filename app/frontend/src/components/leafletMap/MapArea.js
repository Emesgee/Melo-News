import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip } from 'react-leaflet';
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

const MapArea = () => {
  const navigate = useNavigate();
  const { filter } = useSearch();
  const { isDark } = useDarkMode();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

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
          <TileLayer url={tile.url} attribution={tile.attribution} />
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

    </div>
  );
};

export default MapArea;
