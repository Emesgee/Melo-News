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

// Marker wrapper component
// Marker wrapper component with map centering
const MarkerPopupWrapper = ({ time, result, title, city, country, description, files, markerIcon, markerId, onMarkerClick }) => {
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

  // Get video URLs
  console.log('[DEBUG] Files for marker:', files);
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
  console.log('[DEBUG] Video files:', videoFiles);
  console.log('[DEBUG] Image files:', imageFiles);
  console.log('[DEBUG] Has video:', hasVideo);

  return (
    <Marker 
      key={markerId}
      position={[result.lat, result.lon]} 
      icon={markerIcon}
      eventHandlers={{
        click: () => {
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
              onLoadStart={(e) => {
                console.log('[VIDEO] Loading video:', videoFiles[0]);
              }}
              onCanPlay={(e) => {
                console.log('[VIDEO] Video can play:', videoFiles[0]);
              }}
              onError={(e) => {
                console.error('[VIDEO] Video load error for:', videoFiles[0]);
                console.error('[VIDEO] Error details:', e.target.error);
                if (e.target.error) {
                  console.error('[VIDEO] Error code:', e.target.error.code);
                  console.error('[VIDEO] Error message:', e.target.error.message);
                }
              }}
            >
              <source src={videoFiles[0]} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
            
            {/* Overlay information on video */}
            <div className="video-overlay">
              <h3 className="video-overlay-title">{title}</h3>
              <div className="video-overlay-info">
                <span className="video-overlay-time">🕒 {time}</span>
                <span className="video-overlay-location">📍 {city}, {country}</span>
              </div>
            </div>
          </div>
        )}

        {/* Header (only if no video) */}
        {!hasVideo && (
          <div className="popup-header">
            <h3 className="popup-title">{title}</h3>
            <span className="popup-time">{time}</span>
            <p className="popup-location">
              <span className="location-icon">📍</span>
              {city}, {country}
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
                    console.error('Image load error:', url);
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

// Create custom icon with image/video thumbnail
const createThumbnailIcon = (thumbnailUrl, hasVideo = false) => {
  const iconHtml = thumbnailUrl 
    ? `<div class="thumbnail-marker ${hasVideo ? 'has-video' : ''}">
         <img src="${thumbnailUrl}" alt="thumbnail" />
         ${hasVideo ? '<span class="video-badge">▶</span>' : ''}
       </div>`
    : `<div class="red-dot-marker">
         <div style="background-color: #c81515; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>
       </div>`;
  
  return L.divIcon({
    className: 'custom-marker-icon',
    html: iconHtml,
    iconSize: thumbnailUrl ? [50, 50] : [16, 16],
    iconAnchor: thumbnailUrl ? [25, 50] : [8, 8],
    popupAnchor: thumbnailUrl ? [0, -50] : [0, -8],
  });
};

// Red dot marker for fallback (when no thumbnail available)
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
  const [isLoading, setIsLoading] = useState(false);
  const [selectedMarker, setSelectedMarker] = useState(null);

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
    <div className="map-area">
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
          imageLinks = imageLinks.filter(Boolean).map(link => String(link).trim());
          videoLinks = videoLinks.filter(Boolean).map(link => String(link).trim());
          
          const key = result.id || `${result.lat},${result.lon},${title}`;
          console.log('[DEBUG] Result ID:', key, 'Image links:', imageLinks, 'Video links:', videoLinks);
          
          const files = Array.from(new Set([...(imageLinks || []), ...(videoLinks || [])])).filter(Boolean);
          
          // Get thumbnail for marker icon (first image or video)
          const thumbnailUrl = imageLinks[0] || videoLinks[0] || null;
          const hasVideo = videoLinks.length > 0;
          console.log('[DEBUG] Marker thumbnail:', thumbnailUrl, 'Has video:', hasVideo);
          const markerIcon = createThumbnailIcon(thumbnailUrl, hasVideo);
          
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
              console.error('Error parsing date:', time, e);
            }
          }

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
              markerIcon={markerIcon}
              time={formattedTime}
              onMarkerClick={() => setSelectedMarker({
                markerId: key,
                result,
                title,
                city,
                country,
                description,
                files,
                time: formattedTime
              })}
            />
          );
        })}
        </MarkerClusterGroup>
      </MapContainer>
      <MeloSummary searchResults={validResults} />
      </div>

      {/* Left side panel for popup content */}
      {selectedMarker && (
        <div className="map-side-panel" style={{
          position: 'fixed',
          left: '20px',
          top: '50px',
          width: '350px',
          maxHeight: 'calc(100vh - 80px)',
          backgroundColor: 'white',
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.15)',
          zIndex: 1000,
          overflow: 'auto',
          padding: '0'
        }}>
          <SelectedMarkerPanel 
            marker={selectedMarker}
            onClose={() => setSelectedMarker(null)}
          />
        </div>
      )}
    </div>
  );
};

// Side panel component to display selected marker content
const SelectedMarkerPanel = ({ marker, onClose }) => {
  const [activeTab, setActiveTab] = useState('info');
  const videoRef = React.useRef(null);

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
    // Extract the date from marker.time
    const dateStr = marker.time ? new Date(marker.time).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '';
    
    // Get the search term from title or description
    const searchTerm = marker.title || marker.description || '';
    
    // Create Google search URL with the topic and date (without quotes for cleaner search)
    const searchQuery = `${searchTerm} ${dateStr}`;
    const googleSearchURL = `https://www.google.com/search?q=${encodeURIComponent(searchQuery)}`;
    
    // Open in new tab
    window.open(googleSearchURL, '_blank');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '0.5rem',
        flexShrink: 0
      }}>
        <h3 style={{ margin: '0', fontSize: '1.125rem', fontWeight: 600, flex: 1, marginRight: '0.5rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {marker.title}
        </h3>
        <button
          onClick={handleSearchOnline}
          style={{
            background: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            padding: '6px 12px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 500,
            whiteSpace: 'nowrap',
            transition: 'background 0.2s'
          }}
          onMouseOver={(e) => e.target.style.background = '#2563eb'}
          onMouseOut={(e) => e.target.style.background = '#3b82f6'}
          title="Search online for this topic on the same date"
        >
          🔍 Search
        </button>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '1.5rem',
            cursor: 'pointer',
            color: '#666',
            padding: '0',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          ✕
        </button>
      </div>

      {/* Media preview with description overlay */}
      {(hasVideo || imageFiles.length > 0) && (
        <div style={{
          padding: '0.5rem 1rem',
          flexShrink: 0,
          position: 'relative'
        }}>
          {hasVideo && (
            <div style={{ position: 'relative' }}>
              <video
                ref={videoRef}
                onClick={handleVideoClick}
                preload="metadata"
                playsInline
                muted={false}
                crossOrigin="anonymous"
                style={{
                  width: '100%',
                  maxHeight: '200px',
                  borderRadius: '8px',
                  objectFit: 'cover',
                  cursor: 'pointer'
                }}
              >
                <source src={videoFiles[0]} type="video/mp4" />
              </video>
              {marker.description && (
                <div style={{
                  position: 'absolute',
                  bottom: '0',
                  left: '0',
                  right: '0',
                  background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)',
                  color: 'white',
                  padding: '1rem',
                  borderBottomLeftRadius: '8px',
                  borderBottomRightRadius: '8px',
                  fontSize: '0.75rem',
                  lineHeight: '1.4',
                  maxHeight: '80px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {marker.description}
                </div>
              )}
            </div>
          )}
          {!hasVideo && imageFiles.length > 0 && (
            <div style={{ position: 'relative' }}>
              <img
                src={imageFiles[0]}
                alt="preview"
                style={{
                  width: '100%',
                  maxHeight: '200px',
                  borderRadius: '8px',
                  objectFit: 'cover'
                }}
              />
              {marker.description && (
                <div style={{
                  position: 'absolute',
                  bottom: '0',
                  left: '0',
                  right: '0',
                  background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)',
                  color: 'white',
                  padding: '1rem',
                  borderBottomLeftRadius: '8px',
                  borderBottomRightRadius: '8px',
                  fontSize: '0.75rem',
                  lineHeight: '1.4',
                  maxHeight: '80px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {marker.description}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Location info */}
      <div style={{
        padding: '1rem',
        borderBottom: '1px solid #e5e7eb',
        flexShrink: 0
      }}>
        <p style={{ margin: '0.5rem 0', fontSize: '0.875rem', color: '#666' }}>
          <strong>City:</strong> {marker.city}
        </p>
        {marker.country && (
          <p style={{ margin: '0.5rem 0', fontSize: '0.875rem', color: '#666' }}>
            <strong>Country:</strong> {marker.country}
          </p>
        )}
        <p style={{ margin: '0.5rem 0', fontSize: '0.875rem', color: '#999' }}>
          {marker.time}
        </p>
      </div>

      {/* Tab buttons */}
      {/* Removed temporarily */}

      {/* Content */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '1rem'
      }}>
        <div>
          {!hasVideo && (
            <p style={{ margin: '0 0 1rem 0', lineHeight: '1.6', fontSize: '0.875rem', color: '#333' }}>
              {marker.description}
            </p>
          )}
          {marker.files.length > 0 && (
            <div>
              <h4 style={{ margin: '1rem 0 0.5rem 0', fontSize: '0.875rem', fontWeight: 600 }}>
                Attachments ({marker.files.length})
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
                {marker.files.map((file, idx) => (
                  <a
                    key={idx}
                    href={file}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: '0.75rem',
                      color: '#c81515',
                      textDecoration: 'none',
                      padding: '0.5rem',
                      background: '#f0f0f0',
                      borderRadius: '4px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                    title={file}
                  >
                    File {idx + 1}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MapArea;