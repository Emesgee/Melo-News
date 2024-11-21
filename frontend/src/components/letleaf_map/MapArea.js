import React, { useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import './MapArea.css';

const mapLayers = [
  {
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
  },
  {
    name: 'OpenTopoMap',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution:
      'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)',
  },
  {
    name: 'Stamen Watercolor',
    url: 'https://stamen-tiles-{s}.a.ssl.fastly.net/watercolor/{z}/{x}/{y}.jpg',
    attribution:
      'Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors',
  },
  {
    name: 'Stadia Map',
    url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png',
    attribution:
      '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, © <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
  },
  {
    name: 'CartoDB Positron',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution:
      '&copy; <a href="https://www.carto.com/">CARTO</a>, © <a href="http://openstreetmap.org">OpenStreetMap</a> contributors',
  },
];

const defaultPosition = [55.7, 12.57];

// Define the default icon for Leaflet
const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Set the default icon globally
L.Marker.prototype.options.icon = defaultIcon;

// Zoom Circles Component
const ZoomCircles = () => {
  const map = useMap();
  const zoomIntervalRef = useRef(null);

  const startZoomIn = () => {
    zoomIntervalRef.current = setInterval(() => {
      map.setZoom(map.getZoom() + 1);
    }, 100);
  };

  const startZoomOut = () => {
    zoomIntervalRef.current = setInterval(() => {
      map.setZoom(map.getZoom() - 1);
    }, 100);
  };

  const stopZoom = () => {
    clearInterval(zoomIntervalRef.current);
  };

  return (
    <div className="zoom-circles">
      <div
        className="zoom-circle zoom-in"
        onMouseDown={startZoomIn}
        onTouchStart={startZoomIn}
        onMouseUp={stopZoom}
        onTouchEnd={stopZoom}
        onMouseLeave={stopZoom}
      >
        +
      </div>
      <div
        className="zoom-circle zoom-out"
        onMouseDown={startZoomOut}
        onTouchStart={startZoomOut}
        onMouseUp={stopZoom}
        onTouchEnd={stopZoom}
        onMouseLeave={stopZoom}
      >
        -
      </div>
    </div>
  );
};

// FitBounds Component
const FitBounds = ({ bounds }) => {
  const map = useMap();
  if (bounds.length > 0) {
    map.fitBounds(bounds);
  }
  return null;
};

// Main MapArea Component
const MapArea = ({ searchResults = [] }) => {
  const [selectedLayer, setSelectedLayer] = useState(mapLayers[0]); // Default to the first layer

  const bounds = searchResults
    .filter((result) => result.lat && result.lon)
    .map((result) => [result.lat, result.lon]);
    
  return (
    <div className="map-container">
      <MapContainer
        center={defaultPosition}
        zoom={10}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false} // Disable default zoom controls
      >
        {/* Dropdown for selecting layers */}
        <div className="map-dropdown">
          <select
            value={selectedLayer.name}
            onChange={(e) => {
              const layer = mapLayers.find((layer) => layer.name === e.target.value);
              setSelectedLayer(layer);
            }}
          >
            {mapLayers.map((layer) => (
              <option key={layer.name} value={layer.name}>
                {layer.name}
              </option>
            ))}
          </select>
        </div>

        <TileLayer url={selectedLayer.url} attribution={selectedLayer.attribution} />

        {/* Zoom Circles */}
        <ZoomCircles />

        {/* Fit bounds to markers */}
        <FitBounds bounds={bounds} />

        {/* Markers */}
        {searchResults.map(
          (result) =>
            result.lat &&
            result.lon && (
              <Marker key={result.id} position={[result.lat, result.lon]} icon={defaultIcon}>
                <Popup>
                  <h3>{result.title}</h3>
                  <p>
                    <strong>City:</strong> {result.city}, <strong>Country:</strong>{' '}
                    {result.country}
                  </p>
                  <p>
                    <strong>Latitude:</strong> {result.lat}, <strong>Longitude:</strong>{' '}
                    {result.lon}
                  </p>
                </Popup>
              </Marker>
            )
        )}
      </MapContainer>
    </div>
  );
};

export default MapArea;
