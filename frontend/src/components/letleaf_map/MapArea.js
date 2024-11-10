// src/MapArea.js

import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import './MapArea.css';

const defaultPosition = [55.7, 12.57];

// Set up default icon for Leaflet
const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const FitBounds = ({ bounds }) => {
  const map = useMap();
  if (bounds.length > 0) {
    map.fitBounds(bounds);
  }
  return null;
};

const MapArea = ({ searchResults = [] }) => {
  console.log("Search Results:", searchResults); // Check data in console

  const bounds = searchResults
    .filter((result) => result.lat && result.lon) // Ensure only valid lat/lon pairs are used
    .map((result) => [result.lat, result.lon]);

  return (
    <div className="map-container">
      <MapContainer center={defaultPosition} zoom={10} style={{ height: '100%', width: '100%' }} zoomControl={false}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        <FitBounds bounds={bounds} />

        {Array.isArray(searchResults) &&
          searchResults.map((result) => (
            result.lat && result.lon && (
              <Marker key={result.id} position={[result.lat, result.lon]} icon={defaultIcon}>
                <Popup>
                  <h3><em>Title: </em>{result.title}</h3>
                  <strong><em></em>{result.country}, <em></em>{result.city}</strong>
                  <p>Latitude: {result.lat}, Longitude: {result.lon}</p>
                </Popup>
              </Marker>
            )
          ))}
      </MapContainer>
    </div>
  );
};

export default MapArea;
