import React, { useState, useRef, useMemo, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './MapArea.css';
import MarkerClusterGroup from 'react-leaflet-markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { dedupeStories } from '../../utils/storyUtils';
import CityHistory from './CityHistory';
import NewsChat from './NewsChat';
import MeloSummary from './MeloSummary';

// Marker wrapper component - simplified approach
const MarkerPopupWrapper = ({ result, title, city, country, description, files, redDotIcon, markerId }) => {
  const infoTabRef = useRef(null);
  const chatTabRef = useRef(null);
  const infoButtonRef = useRef(null);
  const chatButtonRef = useRef(null);
  const activeTabRef = useRef('info');

  const showTab = useCallback((tab) => {
    if (!infoTabRef.current || !chatTabRef.current || !infoButtonRef.current || !chatButtonRef.current) {
      return;
    }

    activeTabRef.current = tab;

    if (tab === 'info') {
      infoTabRef.current.style.display = 'flex';
      chatTabRef.current.style.display = 'none';
      infoButtonRef.current.classList.add('active');
      chatButtonRef.current.classList.remove('active');
    } else {
      infoTabRef.current.style.display = 'none';
      chatTabRef.current.style.display = 'flex';
      chatButtonRef.current.classList.add('active');
      infoButtonRef.current.classList.remove('active');
    }
  }, []);

  useEffect(() => {
    showTab(activeTabRef.current);
  }, [showTab]);

  return (
    <Marker 
      key={markerId}
      position={[result.lat, result.lon]} 
      icon={redDotIcon}
    >
      <Popup 
        className="modern-popup"
        closeButton={true}
        autoClose={false}
        closeOnClick={false}
      >
        <div className="popup-header">
          <h3 className="popup-title">{title}</h3>
          <p className="popup-location">
            <span className="location-icon">📍</span>
            {city}, {country}
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="popup-tabs">
          <button 
            ref={infoButtonRef}
            className="tab-btn active"
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              showTab('info');
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
          >
            📰 Info
          </button>
          <button 
            ref={chatButtonRef}
            className="tab-btn"
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              showTab('chat');
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
          >
            💬 Chat
          </button>
        </div>

        {/* Info Tab */}
        <div ref={infoTabRef} className="popup-info-tab">
          {files.length > 0 && (
            <div className="popup-media-container">
              {files.map((url, i) => {
                if (/\.(mp4|webm|ogg)$/i.test(url)) {
                  return (
                    <video key={i} controls className="popup-video" style={{ marginBottom: '10px' }}>
                      <source src={url} type="video/mp4" />
                      Your browser does not support the video tag.
                    </video>
                  );
                } else if (/\.(jpg|jpeg|png|gif)$/i.test(url)) {
                  return (
                    <img key={i} src={url} alt={title} className="popup-image" />
                  );
                }
                return null;
              })}
            </div>
          )}

          <p className="popup-description">{description}</p>

          {files.length > 0 && files.some(f => !(/\.(jpg|jpeg|png|gif|mp4|webm|ogg)$/i.test(f))) && (
            <div className="popup-files">
              {files.filter(f => !(/\.(jpg|jpeg|png|gif|mp4|webm|ogg)$/i.test(f))).map((url, i) => (
                <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="popup-file-link">
                  📎 View File
                </a>
              ))}
            </div>
          )}

          {/* City History Section */}
          <CityHistory lat={result.lat} lon={result.lon} city={city} />
        </div>

        <div ref={chatTabRef} className="popup-chat-tab" style={{ display: 'none' }}>
          <NewsChat 
            newsId={markerId}
            newsData={{
              title,
              description,
              city,
              lat: result.lat,
              lon: result.lon
            }}
          />
        </div>
      </Popup>
    </Marker>
  );
};

// Map layer options
const mapLayers = [
  { name: 'OpenStreetMap', url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; OpenStreetMap contributors' },
  { name: 'OpenTopoMap', url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)' },
  { name: 'Stamen Watercolor', url: 'https://stamen-tiles-{s}.a.ssl.fastly.net/watercolor/{z}/{x}/{y}.jpg', attribution: 'Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors' },
  { name: 'Stadia Map', url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png', attribution: '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, © <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors' },
  { name: 'CartoDB Positron', url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', attribution: '&copy; <a href="https://www.carto.com/">CARTO</a>, © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors' },
];

// Default map center
const defaultPosition = [31.9, 35.2]; // Center of Israel/Palestine

// Red dot marker for Israel/Palestine points
const redDotIcon = L.divIcon({
  className: 'red-dot-marker',
  html: '<div style="background-color: #c81515; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
  popupAnchor: [0, -8],
});

// Zoom Circles Component
const ZoomCircles = () => {
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

// FitBounds Component to zoom map to all markers
const FitBounds = ({ bounds }) => {
  const map = useMap();
  const prevCountRef = useRef(0);
  
  useEffect(() => {
    if (bounds && bounds.length > 0 && bounds.length !== prevCountRef.current) {
      try {
        map.fitBounds(bounds, { padding: [40, 40] });
        prevCountRef.current = bounds.length;
      } catch (e) {
        console.error('Error fitting bounds:', e);
      }
    }
  }, [bounds, map]);
  
  return null;
};

// Main MapArea Component
const MapArea = ({ searchResults = [] }) => {
  const [selectedLayer, setSelectedLayer] = useState(mapLayers[0]);

  const dedupedResults = useMemo(
    () => dedupeStories(searchResults),
    [searchResults],
  );

  // Normalize and filter results with valid coordinates
  const validResults = useMemo(() => {
    const results = (dedupedResults || []).map(r => {
      if (!r) return null;
      
      // Normalize coordinates - try various field names
      const lat = r.lat || r.latitude || r.result_lat || r.lat_result;
      const lon = r.lon || r.longitude || r.result_lon || r.lon_result;
      
      return (lat != null && lon != null) ? { ...r, lat: parseFloat(lat), lon: parseFloat(lon) } : null;
    }).filter(Boolean);
    
    return results;
  }, [dedupedResults]);

  // Bounds for map zoom
  const bounds = useMemo(() => validResults.map(r => [r.lat, r.lon]), [validResults]);

  return (
    <div className="map-container">
      <MapContainer
        center={defaultPosition}
        zoom={10}
        minZoom={2}
        maxZoom={14}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
        attributionControl={false}
      >
        {/* Layer selection dropdown */}
        <div className="map-dropdown">
          <select
            value={selectedLayer.name}
            onChange={(e) => setSelectedLayer(mapLayers.find(layer => layer.name === e.target.value))}
          >
            {mapLayers.map(layer => <option key={layer.name} value={layer.name}>{layer.name}</option>)}
          </select>
        </div>

        <TileLayer url={selectedLayer.url} attribution={selectedLayer.attribution} />

        <ZoomCircles />
        <FitBounds bounds={bounds} />

        {/* Clustered markers */}
        <MarkerClusterGroup chunkedLoading>
          {validResults.map(result => {
            // Harmonize fields from backend/producer
            const title = result.title || (result.message ? result.message.slice(0, 80) : 'No Title Available');
            const city = result.city || result.matched_city || result.city_result || 'Unknown';
            const country = result.country || 'Unknown';
            const description = result.description || result.message || 'No description available.';
            const imageLinks = (result.image_links ? result.image_links.split('|') : (result.fileUrl ? [result.fileUrl] : []));
            const videoLinks = (result.video_links ? result.video_links.split('|') : (result.videoUrl ? Array.from(new Set(result.videoUrl.split('|'))) : []));
            const files = Array.from(new Set([...(imageLinks || []), ...(videoLinks || [])])).filter(Boolean);
            const key = result.id || `${result.lat},${result.lon},${title}`;

            return (
              <MarkerPopupWrapper
                key={key}
                markerId={key}
                result={result}
                title={title}
                city={city}
                country={country}
                description={description}
                files={files}
                redDotIcon={redDotIcon}
              />
            );
          })}
        </MarkerClusterGroup>
      </MapContainer>
  <MeloSummary searchResults={validResults} />
    </div>
  );
};

export default MapArea;
