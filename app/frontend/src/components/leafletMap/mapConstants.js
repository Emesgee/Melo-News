// Two theme-linked basemaps — the map follows the app theme (light in light
// mode, dark in dark mode). No style picker; one fewer decision for the reader.
export const MAP_STYLES = [
  {
    id: 'light',
    name: 'Light',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; CARTO &copy; OpenStreetMap contributors',
  },
  {
    id: 'dark',
    name: 'Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; CARTO &copy; OpenStreetMap contributors',
  },
];

export const defaultPosition = [31.9, 35.2];
