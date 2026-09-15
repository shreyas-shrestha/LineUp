// Single reader for the frozen window.LINEUP_CONFIG built by config.js.
// Every other module imports from here instead of touching window.
const FALLBACK = {
  API_URL: 'http://localhost:5000',
  FEATURES: { virtualTryOn: true, socialFeed: true, subscriptionPackages: true, googlePlacesSearch: true, contentModeration: true },
  UI: { defaultLocation: 'Atlanta, GA', maxImageSizeMB: 5, supportedImageTypes: ['image/jpeg', 'image/png', 'image/webp'] },
  RATE_LIMITS: { analysisDelayMs: 1000, searchDebounceMs: 300 },
  DEBUG: false,
  MOCK_MODE: false,
};

const source = (typeof window !== 'undefined' && window.LINEUP_CONFIG) || FALLBACK;

export const config = source;
export const API_URL = String(source.API_URL || FALLBACK.API_URL).replace(/\/+$/, '');
export const UI = { ...FALLBACK.UI, ...(source.UI || {}) };
export const RATE_LIMITS = { ...FALLBACK.RATE_LIMITS, ...(source.RATE_LIMITS || {}) };
export const DEBUG = Boolean(source.DEBUG);

// Development-only logging. Silent unless LINEUP_CONFIG.DEBUG (or ?debug=true).
export function debug(...args) {
  if (DEBUG) console.info('[LineUp]', ...args);
}
