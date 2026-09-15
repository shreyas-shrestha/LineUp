// Single reader for the frozen window.LINEUP_CONFIG built by config.js.
// Every other module imports from here instead of touching window.
const FALLBACK = {
  API_URL: 'http://localhost:5000',
  UI: { defaultLocation: 'Atlanta, GA', maxImageSizeMB: 5, supportedImageTypes: ['image/jpeg', 'image/png', 'image/webp'] },
  DEBUG: false,
};

const source = (typeof window !== 'undefined' && window.LINEUP_CONFIG) || FALLBACK;
const DEBUG = Boolean(source.DEBUG);

export const API_URL = String(source.API_URL || FALLBACK.API_URL).replace(/\/+$/, '');
export const UI = { ...FALLBACK.UI, ...(source.UI || {}) };

// Development-only logging. Silent unless LINEUP_CONFIG.DEBUG (or ?debug=true).
export function debug(...args) {
  if (DEBUG) console.info('[LineUp]', ...args);
}
