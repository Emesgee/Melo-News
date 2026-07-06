// Shared severity configuration (map markers, forms). Colors match the Android
// app's severity tints — HIGH red, MEDIUM orange, LOW green (theme.css tokens).
// Kept as hex (not var()) because map markers set fill via JS attributes.
export const SEVERITY_COLORS = {
  HIGH: '#d32f2f',
  MEDIUM: '#f57c00',
  LOW: '#388e3c',
};

export const SEVERITY_CONFIG = {
  HIGH: { emoji: '🔥', color: '#d32f2f', label: 'HIGH' },
  MEDIUM: { emoji: '⚡', color: '#f57c00', label: 'MEDIUM' },
  LOW: { emoji: '📋', color: '#388e3c', label: 'LOW' },
};
