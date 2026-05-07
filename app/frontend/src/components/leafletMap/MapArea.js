import React, { useState, useRef, useMemo, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './MapArea.css';
import MarkerClusterGroup from 'react-leaflet-markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';
import { api } from '../../services/api';
import { parseMediaLinks, normalizeMediaUrl, filterVideoFiles, filterImageFiles, formatNewsTime } from '../../utils/mediaUtils';
import { useSearch } from '../../utils/SearchContext';
import { MAP_STYLES, defaultPosition, createThumbnailIcon } from './mapConstants';
import { ZoomCircles, FitBounds, MapStylePanel } from './MapControls';
import CityHistory from './CityHistory';
import NewsChat from './NewsChat';
import MeloSummary from './MeloSummary';
import GlobeView from './GlobeView';

// Marker wrapper component
// Marker wrapper component with map centering
const MarkerPopupWrapper = ({ time, result, title, city, country, description, files, markerIcon, markerId, onMarkerClick, customData }) => {
  const infoTabRef = useRef(null);
  const chatTabRef = useRef(null);
  const infoButtonRef = useRef(null);
  const chatButtonRef = useRef(null);
  const activeTabRef = useRef('info');
  const map = useMap();

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

  const videoFiles = files.filter(url => {
    if (!url) return false;
    const urlStr = String(url).toLowerCase();
    return /\.(mp4|webm|ogg|mov|avi)$/i.test(urlStr) || 
           urlStr.includes('blob.core.windows.net') ||
           urlStr.includes('video');
  });
  const imageFiles = files.filter(url => {
    if (!url) return false;
    const urlStr = String(url).toLowerCase();
    return /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(urlStr) && !videoFiles.includes(url);
  });
  const hasVideo = videoFiles.length > 0;

  return (
    <Marker 
      key={markerId}
      position={[result.lat, result.lon]} 
      icon={markerIcon}
      customData={customData} // Pass to Leaflet options
      eventHandlers={{
        click: (e) => {
          // Prevent cluster click from firing if individual marker is clicked
          L.DomEvent.stopPropagation(e);
          
          // Show in side panel and center map on marker
          onMarkerClick?.();
          map.setView([result.lat, result.lon], map.getZoom(), {
            animate: true,
            duration: 0.5
          });
        }
      }}
    >
      <Popup 
        className="modern-popup video-popup"
        closeButton={true}
        autoClose={false}
        closeOnClick={false}
        maxWidth={hasVideo ? 500 : 350}
      >
        {/* Video with overlay */}
        {hasVideo && (
          <div className="popup-video-container" style={{ position: 'relative' }}>
            <video 
              controls 
              className="popup-video-main"
              preload="metadata"
              playsInline
              muted={false}
              crossOrigin="anonymous"
              style={{ 
                width: '100%', 
                maxHeight: '350px', 
                objectFit: 'cover', 
                borderRadius: '12px 12px 0 0',
                display: 'block'
              }}
            >
              <source src={videoFiles[0]} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            
            {/* Overlay information on video */}
            <div className="video-overlay">
              <h3 className="video-overlay-title" title={title}>{formatTitle(title)}</h3>
              <div className="video-overlay-info">
                <span className="video-overlay-time">📅 {time}</span>
                <span className="video-overlay-location">📍 {formatLocation(city, country)}
                  {extractMentionedLocations(description, city).length > 0 && (
                    <span className="popup-route-label"> → {extractMentionedLocations(description, city).map(formatTitle).join(', ')}</span>
                  )}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Header (only if no video) */}
        {!hasVideo && (
          <div className="popup-header">
            <h3 className="popup-title" title={title}>{formatTitle(title)}</h3>
            <span className="popup-time">📅 {time}</span>
            <p className="popup-location">
              <span className="location-icon">📍</span>
              {formatLocation(city, country)}
              {extractMentionedLocations(description, city).length > 0 && (
                <span className="popup-route-label"> → {extractMentionedLocations(description, city).map(formatTitle).join(', ')}</span>
              )}
            </p>
          </div>
        )}

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
          <p className="popup-description">{description}</p>

          {/* Show additional images if any */}
          {imageFiles.length > 0 && (
            <div className="popup-media-container">
              {imageFiles.map((url, i) => (
                <img 
                  key={i} 
                  src={url} 
                  alt={title} 
                  className="popup-image"
                  onError={(e) => {
                    e.target.style.display = 'none';
                  }}
                />
              ))}
            </div>
          )}

          {/* Show additional videos */}
          {videoFiles.length > 1 && (
            <div className="popup-additional-videos">
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>More videos:</h4>
              {videoFiles.slice(1).map((url, i) => (
                <a 
                  key={i}
                  href={url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ 
                    display: 'block',
                    marginBottom: '0.5rem',
                    padding: '6px 10px',
                    fontSize: '11px',
                    color: '#2563eb',
                    textDecoration: 'none',
                    backgroundColor: '#eff6ff',
                    borderRadius: '4px'
                  }}
                >
                  🎥 Video {i + 2}
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

// Constants, controls, and icons imported from extracted modules

// ── Main MapArea Component ──────────────────────────────────
const MapArea = () => {
  const { searchResults, setSearchResults } = useSearch();
  const [currentStyle, setCurrentStyle] = useState(MAP_STYLES[0]);
  const [is3D, setIs3D] = useState(false);
  const [showGlobe, setShowGlobe] = useState(false);
  const [showStylePicker, setShowStylePicker] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMarker, setSelectedMarker] = useState(null);
  const [clusterList, setClusterList] = useState(null); // New state for cluster lists

  // Close style picker on outside click
  const stylePanelRef = useRef(null);
  useEffect(() => {
    const handleOutside = (e) => {
      if (stylePanelRef.current && !stylePanelRef.current.contains(e.target)) {
        setShowStylePicker(false);
      }
    };
    if (showStylePicker) document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, [showStylePicker]);

  // Load all stories when map mounts if no search results exist
  useEffect(() => {
    if (!searchResults || searchResults.length === 0) {
      const loadAllStories = async () => {
        try {
          setIsLoading(true);
          const response = await api.post('search', {
            user_id: 1,
            term: '*', // Wildcard to get all results
            filters: {},
            template_ids: [1],
          });
          
          const results = Array.isArray(response.data.results) 
            ? response.data.results 
            : (response.data.results ? [response.data.results] : []);
          
          setSearchResults(results);
        } catch (error) {
          console.error('Error loading map stories:', error);
        } finally {
          setIsLoading(false);
        }
      };

      loadAllStories();
    }
  }, []); // Run only once on mount

  // Normalize and filter results with valid coordinates
  // (deduplication already done in SearchContext)
  const validResults = useMemo(() => {
    const positionCount = {};

    return (searchResults || []).map(r => {
      if (!r) return null;

      // Support both nested Story shape and legacy flat Telegram shape
      const loc  = r.location   || {};
      const med  = r.media      || {};
      const met  = r.metrics    || {};
      const ts   = r.timestamps || {};
      const prov = r.provenance || {};

      const lat = r.lat  ?? loc.lat  ?? r.latitude  ?? r.result_lat ?? r.lat_result;
      const lon = r.lon  ?? loc.lon  ?? r.longitude ?? r.result_lon ?? r.lon_result;
      if (lat == null || lon == null) return null;

      // Apply a tiny spiral offset so markers at the exact same position
      // remain individually visible instead of stacking on top of each other.
      const posKey = `${parseFloat(lat).toFixed(5)},${parseFloat(lon).toFixed(5)}`;
      const idx = positionCount[posKey] ?? 0;
      positionCount[posKey] = idx + 1;
      const jitterRadius = idx * 0.00015; // ~17 m per step
      const jitterAngle  = idx * 2.39996; // golden-angle spiral
      const jLat = idx === 0 ? 0 : jitterRadius * Math.cos(jitterAngle);
      const jLon = idx === 0 ? 0 : jitterRadius * Math.sin(jitterAngle);

      return {
        ...r,
        lat:              parseFloat(lat) + jLat,
        lon:              parseFloat(lon) + jLon,
        city:             r.city             || loc.city            || r.matched_city   || r.city_result || 'Unknown',
        country:          r.country          || loc.country         || '',
        description:      r.description      || r.body              || r.message        || '',
        image_links:      r.image_links      || med.images          || [],
        video_links:      r.video_links      || med.videos          || [],
        fileUrl:          r.fileUrl          || r.file_path         || med.primary_url  || null,
        severity:         r.severity         || met.severity        || 'MEDIUM',
        confidence_score: r.confidence_score ?? met.confidence_score ?? null,
        time:             r.time             || ts.published_at     || r.published_at   || '',
        source:           r.source           || prov.source_name    || r.source_type    || '',
        source_count:     r.source_count     ?? met.source_count    ?? 1,
        escalation:       r.escalation       || met.escalation      || null,
      };
    }).filter(Boolean);
  }, [searchResults]);

  // Bounds for map zoom
  const bounds = useMemo(() => validResults.map(r => [r.lat, r.lon]), [validResults]);

  return (
    <div className="map-area">

      {/* Loading indicator */}
      {isLoading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1000,
          background: 'rgba(0, 0, 0, 0.7)',
          padding: '2rem',
          borderRadius: '12px',
          color: 'white',
          textAlign: 'center',
          minWidth: '200px'
        }}>
          <div style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>Loading map stories...</div>
          <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>Please wait</div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && validResults.length === 0 && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 1000,
          background: 'rgba(0, 0, 0, 0.7)',
          padding: '2rem',
          borderRadius: '12px',
          color: 'white',
          textAlign: 'center',
          minWidth: '200px'
        }}>
          <div style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>No stories found</div>
          <div style={{ fontSize: '0.9rem', opacity: 0.8 }}>Start by uploading your first story or try searching</div>
        </div>
      )}

      {/* Globe view (replaces map when active) */}
      {showGlobe && (
        <GlobeView
          points={validResults.map(r => ({
            ...r,
            lat: r.lat,
            lng: r.lon,
            title:       r.title || (r.message ? r.message.slice(0, 80) : 'Incident'),
            city:        r.city || r.matched_city || 'Unknown',
            country:     r.country || 'Unknown',
            description: r.description || r.message || '',
            severity:    r.severity || 'MEDIUM',
          }))}
          onPointClick={(point) => {
            const key = point.id || `${point.lat},${point.lng}`;
            let imageLinks = [];
            if (Array.isArray(point.image_links)) imageLinks = point.image_links;
            else if (point.image_links) { try { imageLinks = JSON.parse(point.image_links); } catch { imageLinks = point.image_links.split('|'); } }
            let videoLinks = [];
            if (Array.isArray(point.video_links)) videoLinks = point.video_links;
            else if (point.video_links) { try { videoLinks = JSON.parse(point.video_links); } catch { videoLinks = point.video_links.split('|'); } }
            // Normalize URLs
            imageLinks = imageLinks.map(link => normalizeMediaUrl(link)).filter(Boolean);
            videoLinks = videoLinks.map(link => normalizeMediaUrl(link)).filter(Boolean);
            const files = Array.from(new Set([...imageLinks, ...videoLinks])).filter(Boolean);
            let formattedTime = 'Recent';
            const raw = point.time || point.published_at || point.date || '';
            if (raw) { try { const d = new Date(raw); if (!isNaN(d)) formattedTime = d.toLocaleString('en-US', { year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }); } catch {} }
            setSelectedMarker({ markerId: key, result: point, title: point.title, city: point.city, country: point.country, description: point.description, files, time: formattedTime });
          }}
        />
      )}

      {/* 2D / 3D tilt viewport wrapper (hidden when globe is active) */}
      <div className={`map-viewport-wrapper${is3D ? ' tilt-3d' : ''}${showGlobe ? ' map-hidden' : ''}`}>
        <div className="map-container" style={{ width: '100%', height: '100vh' }}>
          <MapContainer
            center={defaultPosition}
            zoom={10}
            minZoom={2}
            maxZoom={14}
            style={{ height: '100%', width: '100%' }}
            zoomControl={false}
            attributionControl={false}
          >
          <TileLayer url={currentStyle.url} attribution={currentStyle.attribution} />

        <ZoomCircles />
        <FitBounds bounds={bounds} />

        {/* Clustered markers */}
        <MarkerClusterGroup 
          chunkedLoading
          spiderfyOnMaxZoom={false}
          showCoverageOnHover={false}
          zoomToBoundsOnClick={false}
          onClick={(e) => {
            // Check if it's a cluster click
            const layer = e.layer;
            
            // Check if we clicked on a cluster (has getAllChildMarkers)
            if (layer && typeof layer.getAllChildMarkers === 'function') {
              const markers = layer.getAllChildMarkers();
              
              // Extract data from markers. In React-Leaflet v3/v4, props passed to <Marker> 
              // are often available in 'options' of the leaflet instance.
              const clusterData = markers.map(m => {
                return m.options.customData || m.options.icon?.options?.customData;
              }).filter(Boolean);

              if (clusterData.length > 0) {
                 // Stop propagation to prevent map click
                 L.DomEvent.stopPropagation(e);
                 setClusterList(clusterData);
                 setSelectedMarker(clusterData); // Show list
              }
            }
          }}
        >
        {validResults.map(result => {
          // Harmonize fields from backend/producer
          const title = result.title || (result.message ? result.message.slice(0, 80) : 'No Title Available');
          const city = result.city || result.matched_city || result.city_result || 'Unknown';
          const country = result.country || 'Unknown';
          const description = result.description || result.message || 'No description available.';
          
          // Handle image_links - can be array, JSON string, or pipe-separated string
          let imageLinks = [];
          if (Array.isArray(result.image_links)) {
            imageLinks = result.image_links;
          } else if (result.image_links) {
            try {
              // Try parsing as JSON first
              imageLinks = JSON.parse(result.image_links);
            } catch {
              // Fall back to pipe-separated string
              imageLinks = result.image_links.split('|');
            }
          } else if (result.fileUrl) {
            imageLinks = [result.fileUrl];
          }
          
          // Handle video_links - can be array, JSON string, or pipe-separated string
          let videoLinks = [];
          if (Array.isArray(result.video_links)) {
            videoLinks = result.video_links;
          } else if (result.video_links) {
            try {
              // Try parsing as JSON first
              videoLinks = JSON.parse(result.video_links);
            } catch {
              // Fall back to pipe-separated string
              videoLinks = result.video_links.split('|');
            }
          } else if (result.videoUrl) {
            if (typeof result.videoUrl === 'string') {
              try {
                videoLinks = JSON.parse(result.videoUrl);
              } catch {
                videoLinks = result.videoUrl.split('|');
              }
            } else if (Array.isArray(result.videoUrl)) {
              videoLinks = result.videoUrl;
            }
          }
          
          // Clean and deduplicate
          imageLinks = imageLinks
            .filter(Boolean)
            .map(link => String(link).trim())
            .map(link => normalizeMediaUrl(link)) // Normalize URLs
            .filter(link => {
              // Skip obviously invalid URLs (too short or malformed)
              if (!link || link.length < 5) return false;
              // Skip if it contains 'undefined', 'null', 'NaN'
              if (/undefined|null|NaN/i.test(link)) return false;
              return true;
            });
          
          videoLinks = videoLinks
            .filter(Boolean)
            .map(link => String(link).trim())
            .map(link => normalizeMediaUrl(link)) // Normalize URLs
            .filter(link => {
              if (!link || link.length < 5) return false;
              if (/undefined|null|NaN/i.test(link)) return false;
              return true;
            });
          
          const key = result.id || `${result.lat},${result.lon},${title}`;
          
          const files = Array.from(new Set([...(imageLinks || []), ...(videoLinks || [])])).filter(Boolean);
          
          // Get thumbnail for marker icon (first image or video)
          const thumbnailUrl = imageLinks[0] || videoLinks[0] || null;
          const hasVideo = videoLinks.length > 0;
          const severity = result.severity || 'MEDIUM';
          const markerIcon = createThumbnailIcon(thumbnailUrl, hasVideo, severity);
          
          // Extract time - handle various formats
          let time = result.time || result.published_at || result.date || result.created_at || result.timestamp || '';
          
          // Handle timestamp format
          let formattedTime = 'Recent';
          if (time) {
            try {
              const dateObj = new Date(time);
              if (!isNaN(dateObj.getTime())) {
                formattedTime = dateObj.toLocaleString('en-US', {
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                });
              }
            } catch (e) {
              /* invalid date */
            }
          }

          // Marker data object for cluster extraction
          const markerData = {
              markerId: key,
              result,
              title,
              city,
              country,
              description,
              files,
              time: formattedTime
          };

          return (
            <MarkerPopupWrapper
              key={key}
              {...markerData}
              markerIcon={markerIcon}
              customData={markerData} // Pass as prop
              onMarkerClick={() => {
                setClusterList(null);
                setSelectedMarker(markerData);
              }}
            />
          );
        })}
          </MarkerClusterGroup>
          </MapContainer>
          <MeloSummary />
        </div>
      </div>{/* end map-viewport-wrapper */}

      {/* Map overlay controls (outside 3D wrapper so they stay flat) */}
      <div className="map-overlay-controls" ref={stylePanelRef}>
        {/* Globe / Map toggle */}
        <button
          className={`map-globe-toggle${showGlobe ? ' active' : ''}`}
          onClick={() => { setShowGlobe(v => !v); setIs3D(false); setShowStylePicker(false); }}
          title={showGlobe ? 'Switch to flat map' : 'Switch to 3D globe'}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
        </button>

        {/* 2D/3D tilt (only when in map mode) */}
        {!showGlobe && (
        <button
          className={`map-view-toggle${is3D ? ' active' : ''}`}
          onClick={() => setIs3D(v => !v)}
          title={is3D ? 'Switch to 2D' : 'Switch to 3D tilt'}
        >
          {is3D ? '2D' : '3D'}
        </button>
        )}

        <button
          className={`map-style-toggle${showStylePicker ? ' active' : ''}`}
          onClick={() => setShowStylePicker(v => !v)}
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

      {is3D && <div className="map-3d-indicator">3D TILT</div>}

      {/* Left side panel for popup content */}
      {selectedMarker && (
        <div className="map-side-panel" style={{
          position: 'fixed',
          left: '20px',
          top: '50px',
          width: '350px',
          maxHeight: 'calc(100vh - 80px)',
          backgroundColor: 'var(--panel-bg, white)',
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.15)',
          zIndex: 1000,
          overflow: 'auto',
          padding: '0'
        }}>
          <SelectedMarkerPanel 
            marker={selectedMarker}
            onClose={() => {
              setSelectedMarker(null);
              setClusterList(null);
            }}
            onSelectFromCluster={(item) => {
               // Keep the list in history (clusterList state), show item
               setSelectedMarker(item);
            }}
            onBack={() => {
              // Go back to the list if we have one
              if (clusterList) {
                setSelectedMarker(clusterList);
              }
            }}
          />
        </div>
      )}
    </div>
  );
};

// Helper functions for data formatting
const formatTitle = (title) => {
  if (!title) return 'Untitled';
  // detailed cleanup: replace underscores/hyphens with spaces
  const cleanTitle = title.replace(/[_-]/g, ' ');
  // Title Case
  return cleanTitle.replace(/\w\S*/g, (txt) => {
    return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
  });
};

const formatLocation = (city, country) => {
  const c = city || '';
  const co = country || '';
  
  // If only one exists
  if (!c && !co) return 'Unknown Location';
  if (!c) return formatTitle(co);
  if (!co) return formatTitle(c);

  // If both exist, check duplication (case-insensitive)
  if (c.toLowerCase().trim() === co.toLowerCase().trim()) {
    return formatTitle(c);
  }
  return `${formatTitle(c)}, ${formatTitle(co)}`;
};

/**
 * Extract mentioned location names from description text.
 * Looks for patterns like "between X and Y", "from X to Y",
 * and well-known Palestinian/Israeli city names.
 */
const KNOWN_LOCATIONS = [
  'Ramallah', 'Nablus', 'Hebron', 'Jenin', 'Tulkarm', 'Bethlehem',
  'Jericho', 'Qalqilya', 'Salfit', 'Tubas', 'Gaza', 'Khan Yunis',
  'Rafah', 'Deir al-Balah', 'Jabalia', 'Beit Lahia', 'Jerusalem',
  'Haifa', 'Acre', 'Nazareth', 'Safed', 'Tiberias', 'Beersheba',
  'Ashkelon', 'Ashdod', 'Tel Aviv', 'Lod', 'Ramleh', 'Jaffa',
  'Sderot', 'Netanya', 'Huwara', 'Beita', 'Azzun', 'Silwan',
  'Sheikh Jarrah', 'Beit Hanoun', 'Al-Bireh', 'Bir Zeit',
  'Rawabi', 'Dura', 'Yatta', 'Anata', 'Abu Dis', 'Beit Jala',
  'Beit Sahour', 'Al-Khalil', 'Sebastia', 'Aqraba', 'Burin',
  'Kafr Qaddum', 'Ni\'lin', 'Bil\'in', 'Turmus Ayya'
];

const extractMentionedLocations = (text, primaryCity) => {
  if (!text) return [];
  const found = [];
  const primaryLower = (primaryCity || '').toLowerCase().trim();

  for (const loc of KNOWN_LOCATIONS) {
    // Case-insensitive whole-word match
    const re = new RegExp(`\\b${loc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
    if (re.test(text) && loc.toLowerCase() !== primaryLower) {
      found.push(loc);
    }
  }
  return [...new Set(found)];
};

const getFileName = (url) => {
  try {
    // Decode URL to handle encoded characters
    const decodedUrl = decodeURIComponent(url);
    // Extract filename from path
    const parts = decodedUrl.split('/');
    let fileName = parts[parts.length - 1];
    
    // Remove query parameters if present
    fileName = fileName.split('?')[0];
    
    // Truncate if too long (e.g. > 30 chars)
    if (fileName.length > 30) {
      const ext = fileName.split('.').pop();
      const name = fileName.substring(0, 25);
      return `${name}...${ext}`;
    }
    return fileName;
  } catch (e) {
    return 'File';
  }
};

// Multi-location chip display component (state-of-the-art benchmark style)
const LocationChips = ({ marker }) => {
  const primaryLocation = formatLocation(marker.city, marker.country);
  const mentioned = extractMentionedLocations(marker.description, marker.city);

  return (
    <div className="side-panel__location">
      <div className="side-panel__locations-row">
        <span className="location-chip location-chip--primary" title="Primary location">
          <span className="location-chip__icon">📍</span>
          <span className="location-chip__text">{primaryLocation}</span>
        </span>
        {mentioned.map((loc, i) => (
          <React.Fragment key={loc}>
            <span className="location-chip__connector">
              <svg width="16" height="10" viewBox="0 0 16 10" fill="none">
                <path d="M0 5h12M10 1l4 4-4 4" stroke="#666" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </span>
            <span className="location-chip location-chip--mentioned" title="Mentioned location">
              <span className="location-chip__icon">📌</span>
              <span className="location-chip__text">{formatTitle(loc)}</span>
            </span>
          </React.Fragment>
        ))}
      </div>
      <p className="side-panel__time">🇵🇸 {marker.time}</p>
    </div>
  );
};

// Side panel component to display selected marker content OR a list of cluster items
const SelectedMarkerPanel = ({ marker, onClose, onSelectFromCluster, onBack }) => {
  const [activeTab, setActiveTab] = useState('info');
  const videoRef = React.useRef(null);
  
  // 1. CLUSTER LIST VIEW
  if (Array.isArray(marker)) {
    return (
      <div className="side-panel">
        <div className="side-panel__header">
          <h3 className="side-panel__title">{marker.length} Incidents</h3>
          <button className="side-panel__close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="side-panel__content cluster-list">
          {marker.map((item, idx) => {
            // Extract thumbnail
            let thumb = null;
            if (item.files && item.files.length > 0) thumb = item.files[0];
            const isVideo = thumb && (thumb.endsWith('.mp4') || thumb.includes('video'));
            
            // Format meta info
            const loc = formatLocation(item.city, item.country);
            const date = item.time ? item.time.split(',')[0] : '';
            const metaString = [loc, date].filter(Boolean).join(' • ');

            // Smart Title Logic
            let displayTitle = formatTitle(item.title);
            const genericTitles = ['Settler Violence', 'Incident', 'Untitled', 'Unknown'];
            if (genericTitles.some(t => displayTitle.toLowerCase().includes(t.toLowerCase())) && item.description) {
               // Use description if title is generic
               const cleanDesc = item.description.replace(/<[^>]*>?/gm, ''); // strip html if any
               if (cleanDesc.length > 5) {
                 displayTitle = cleanDesc.slice(0, 60) + (cleanDesc.length > 60 ? '...' : '');
               }
            }

            return (
              <div key={idx} className="cluster-list-item" onClick={() => onSelectFromCluster(item)}>
                <div className="cluster-item-thumb">
                  {thumb ? (
                    isVideo ? (
                      <video src={thumb} muted className="cluster-thumb-img" />
                    ) : (
                      <img 
                        src={thumb} 
                        alt="" 
                        className="cluster-thumb-img"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.parentNode.classList.add('broken');
                        }} 
                      />
                    )
                  ) : (
                    <div className="cluster-thumb-placeholder"></div>
                  )}
                  {isVideo && <div className="cluster-video-badge">▶</div>}
                </div>
                <div className="cluster-item-info">
                  <h4 className="cluster-item-title" title={item.title || item.description}>{displayTitle}</h4>
                  <div className="cluster-item-meta">
                    {metaString}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // 2. SINGLE MARKER DETAIL VIEW
  if (!marker) return null;

  const videoFiles = marker.files.filter(url => {
    if (!url) return false;
    const urlStr = String(url).toLowerCase();
    return /\.(mp4|webm|ogg|mov|avi)$/i.test(urlStr) || 
           urlStr.includes('blob.core.windows.net') ||
           urlStr.includes('video');
  });

  const imageFiles = marker.files.filter(url => {
    if (!url) return false;
    const urlStr = String(url).toLowerCase();
    return /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(urlStr) && !videoFiles.includes(url);
  });

  const hasVideo = videoFiles.length > 0;

  const handleVideoClick = () => {
    if (videoRef.current) {
      if (videoRef.current.paused) {
        videoRef.current.play();
      } else {
        videoRef.current.pause();
      }
    }
  };

  const handleSearchOnline = () => {
    const dateStr = marker.time
      ? new Date(marker.time).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
      : '';
    // Limit search query length to prevent URL abuse
    const rawTerm = (marker.title || marker.description || '').slice(0, 200);
    const searchQuery = `${rawTerm} ${dateStr}`.trim();
    if (!searchQuery) return;
    // Hardcode the Google origin to prevent open-redirect attacks
    const url = new URL('https://www.google.com/search');
    url.searchParams.set('q', searchQuery);
    window.open(url.toString(), '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="side-panel">
      <div className="side-panel__header">
        {onBack && (
          <button className="side-panel__back-btn" onClick={onBack} title="Back to list">
            ← Back
          </button>
        )}
        <h3 className="side-panel__title" title={marker.title}>{formatTitle(marker.title)}</h3>
        <button className="side-panel__search-btn" onClick={handleSearchOnline} title="Search online for this topic on the same date">
          🌐 Web Search
        </button>
        <button className="side-panel__close-btn" onClick={onClose}>✕</button>
      </div>

      {(hasVideo || imageFiles.length > 0) && (
        <div className="side-panel__media">
          {hasVideo && (
            <div className="side-panel__media-wrap">
              <video ref={videoRef} onClick={handleVideoClick} preload="metadata" playsInline muted={false} crossOrigin="anonymous" className="side-panel__video">
                <source src={videoFiles[0]} type="video/mp4" />
              </video>
              {marker.description && <div className="side-panel__desc-overlay">{marker.description}</div>}
            </div>
          )}
          {!hasVideo && imageFiles.length > 0 && (
            <div className="side-panel__media-wrap">
              <img src={imageFiles[0]} alt="preview" className="side-panel__image" />
              {marker.description && <div className="side-panel__desc-overlay">{marker.description}</div>}
            </div>
          )}
        </div>
      )}

      <LocationChips marker={marker} />

      <div className="side-panel__content">
        {!hasVideo && <p className="side-panel__description">{marker.description}</p>}
        {marker.files.length > 0 && (
          <div>
            <h4 className="side-panel__attachments-title">Attachments ({marker.files.length})</h4>
            <div className="side-panel__attachments-grid">
              {marker.files.map((file, idx) => (
                <a key={idx} href={file} target="_blank" rel="noopener noreferrer" className="side-panel__file-link" title={file}>
                  📄 {getFileName(file)}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MapArea;