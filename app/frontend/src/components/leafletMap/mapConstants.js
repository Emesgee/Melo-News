import L from 'leaflet';
import { SEVERITY_COLORS } from '../../constants/severity';

// ── Journalistic map style configurations ────────────────────────────
export const MAP_STYLES = [
  { id: 'standard',     name: 'Standard',     swatch: '#a8c5a0', category: 'Default',       url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',                                           attribution: '&copy; OpenStreetMap contributors' },
  { id: 'dark',         name: 'Dark',         swatch: '#1a1a2e', category: 'Dark',          url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',                                attribution: '&copy; CARTO &copy; OpenStreetMap contributors' },
  { id: 'dark-pure',    name: 'Dark Pure',    swatch: '#0d0d0d', category: 'Dark',          url: 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png',                           attribution: '&copy; CARTO' },
  { id: 'night',        name: 'Night',        swatch: '#1e2130', category: 'Dark',          url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png',                    attribution: '&copy; Stadia Maps &copy; OpenMapTiles &copy; OpenStreetMap contributors' },
  { id: 'minimal',      name: 'Minimal',      swatch: '#f0f0f0', category: 'Light',         url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',                               attribution: '&copy; CARTO &copy; OpenStreetMap contributors' },
  { id: 'clean',        name: 'Clean',        swatch: '#e8edf2', category: 'Light',         url: 'https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png',                          attribution: '&copy; CARTO' },
  { id: 'alidade',      name: 'Alidade',      swatch: '#c8d8e4', category: 'Light',         url: 'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png',                         attribution: '&copy; Stadia Maps &copy; OpenMapTiles &copy; OpenStreetMap contributors' },
  { id: 'satellite',    name: 'Satellite',    swatch: '#2d4a22', category: 'Satellite',     url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attribution: '&copy; Esri' },
  { id: 'terrain',      name: 'Terrain',      swatch: '#8fbc8f', category: 'Terrain',       url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',                                             attribution: '&copy; OpenTopoMap contributors' },
  { id: 'humanitarian', name: 'Humanitarian', swatch: '#c2410c', category: 'Journalistic',  url: 'https://tile-{s}.openstreetmap.fr/hot/{z}/{x}/{y}.png',                                        attribution: '&copy; OpenStreetMap contributors, HOT' },
];

export const STYLE_CATEGORIES = ['Default', 'Dark', 'Light', 'Satellite', 'Terrain', 'Journalistic'];

export const defaultPosition = [31.9, 35.2];

export const createThumbnailIcon = (thumbnailUrl, hasVideo = false, severity = 'MEDIUM') => {
  const dotColor = SEVERITY_COLORS[severity] || SEVERITY_COLORS.MEDIUM;
  const iconHtml = thumbnailUrl
    ? `<div class="thumbnail-marker ${hasVideo ? 'has-video' : ''}" style="border-color: ${dotColor}">
         <img src="${thumbnailUrl}" alt="thumbnail" />
         ${hasVideo ? '<span class="video-badge">▶</span>' : ''}
       </div>`
    : `<div class="red-dot-marker">
         <div style="background-color: ${dotColor}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>
       </div>`;

  return L.divIcon({
    className: 'custom-marker-icon',
    html: iconHtml,
    iconSize: thumbnailUrl ? [50, 50] : [16, 16],
    iconAnchor: thumbnailUrl ? [25, 50] : [8, 8],
    popupAnchor: thumbnailUrl ? [0, -50] : [0, -8],
  });
};
