// Builds the frozen window.LINEUP_CONFIG that src/js/env.js reads. Loaded as a
// plain script before the modules, so env.js sees it at module-eval time.
// Precedence: ?api= / ?debug= beat window.__LINEUP_CONFIG__, which beats the
// host-derived default below.

(function() {
  'use strict';

  const defaults = {
    API_URL: 'https://lineup-fjpn.onrender.com',
    UI: {
      defaultLocation: 'Atlanta, GA',
      maxImageSizeMB: 5,
      supportedImageTypes: ['image/jpeg', 'image/png', 'image/webp'],
    },
    DEBUG: false,
  };

  function detectApiUrl() {
    const hostname = window.location.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:5000';
    }
    if (hostname.includes('onrender.com')) {
      return 'https://lineup-fjpn.onrender.com';
    }
    return defaults.API_URL;
  }

  function deepMerge(target, source) {
    const result = { ...target };
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = deepMerge(target[key] || {}, source[key]);
      } else {
        result[key] = source[key];
      }
    }
    return result;
  }

  function buildConfig() {
    let config = { ...defaults, API_URL: detectApiUrl() };

    if (window.__LINEUP_CONFIG__) {
      config = deepMerge(config, window.__LINEUP_CONFIG__);
    }

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('api')) {
      config.API_URL = urlParams.get('api');
    }
    if (urlParams.get('debug') === 'true') {
      config.DEBUG = true;
    }

    Object.freeze(config);
    Object.freeze(config.UI);
    return config;
  }

  const CONFIG = buildConfig();
  window.LINEUP_CONFIG = CONFIG;

  if (CONFIG.DEBUG) {
    console.log('LineUp config:', CONFIG);
  }

})();
