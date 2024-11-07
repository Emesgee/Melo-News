// src/pages/MapArea.js
import React, {useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import './MapArea.css';


const defaultPosition = [55.7, 12.57];

// Set up the default icon for Leaflet
const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

L.Marker.prototype.options.icon = defaultIcon;

// Component to handle zoom controls on mobile
const MobileZoomControl = () => {
  const map = useMap();
  const zoomInterval = useRef(null);

  const startZooming = (zoomIn = true) => {
    clearInterval(zoomInterval.current);
    zoomInterval.current = setInterval(() => {
      map.setZoom(map.getZoom() + (zoomIn ? 1 : -1));
    }, 200);
  };

  const stopZooming = () => {
    clearInterval(zoomInterval.current);
  };

  return (
    <>
      {/* Circle for zooming out on the bottom-left corner */}
      <div
        className="zoom-circle zoom-out"
        onTouchStart={() => startZooming(false)}
        onTouchEnd={stopZooming}
      >
        -
      </div>

      {/* Circle for zooming in on the bottom-right corner */}
      <div
        className="zoom-circle zoom-in"
        onTouchStart={() => startZooming(true)}
        onTouchEnd={stopZooming}
      >
        +
      </div>
    </>
  );
};

const MapArea = () => {
  return (
    <div className="map-container">
      <MapContainer center={defaultPosition} zoom={10} style={{ height: '100%', width: '100%' }} zoomControl={false}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* Mobile Zoom Controls */}
        <MobileZoomControl />

        <Marker position={defaultPosition}>
          <Popup>
            <strong>Default Marker</strong>
            <p>This is a marker at the map's center.</p>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
};

export default MapArea;
