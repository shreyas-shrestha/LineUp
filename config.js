/**
 * LineUp Frontend Configuration
 * 
 * This file centralizes all configuration for the frontend.
 * For local development, modify the values here.
 * For production, these can be overridden by window.__LINEUP_CONFIG__
 */

(function() {
  'use strict';

  // Default configuration
  const defaults = {
    // API Configuration
    API_URL: 'https://lineup-fjpn.onrender.com',
    
    // Feature Flags
    FEATURES: {
      virtualTryOn: true,
      socialFeed: true,
      subscriptionPackages: true,
      googlePlacesSearch: true,
      contentModeration: true,
    },
    
    // UI Configuration
    UI: {
      defaultLocation: 'Atlanta, GA',
      maxImageSizeMB: 5,
      supportedImageTypes: ['image/jpeg', 'image/png', 'image/webp'],
    },
    
    // Rate Limiting (client-side throttling)
    RATE_LIMITS: {
      analysisDelayMs: 1000,
      searchDebounceMs: 300,
    },
    
    // Development flags
    DEBUG: false,
    MOCK_MODE: false,
  };

  /**
   * Detect environment and set appropriate API URL
   */
  function detectApiUrl() {
    const hostname = window.location.hostname;
    
    // Local development
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:5000';
    }
    
    // Render.com deployment
    if (hostname.includes('onrender.com')) {
      // Use the same domain but with API subdomain pattern
      // or the dedicated API URL
      return 'https://lineup-fjpn.onrender.com';
    }
    
    // Custom domain - default to production API
    return defaults.API_URL;
  }

  /**
   * Deep merge configuration objects
   */
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

  /**
   * Build final configuration
   */
  function buildConfig() {
    let config = { ...defaults };
    
    // Auto-detect API URL based on environment
    config.API_URL = detectApiUrl();
    
    // Override with window config if provided (for server-side injection)
    if (window.__LINEUP_CONFIG__) {
      config = deepMerge(config, window.__LINEUP_CONFIG__);
    }
    
    // Override with URL parameters for development/testing
    const urlParams = new URLSearchParams(window.location.search);
    
    if (urlParams.get('api')) {
      config.API_URL = urlParams.get('api');
    }
    
    if (urlParams.get('debug') === 'true') {
      config.DEBUG = true;
    }
    
    if (urlParams.get('mock') === 'true') {
      config.MOCK_MODE = true;
    }
    
    // Freeze config to prevent accidental modification
    Object.freeze(config);
    Object.freeze(config.FEATURES);
    Object.freeze(config.UI);
    Object.freeze(config.RATE_LIMITS);
    
    return config;
  }

  // Build and expose config
  const CONFIG = buildConfig();
  
  // Expose globally
  window.LINEUP_CONFIG = CONFIG;
  
  // Log config in debug mode
  if (CONFIG.DEBUG) {
    console.log('🔧 LineUp Config:', CONFIG);
  }
  
  // Expose helper methods
  window.LINEUP_CONFIG.isFeatureEnabled = function(featureName) {
    return CONFIG.FEATURES[featureName] === true;
  };
  
  window.LINEUP_CONFIG.getApiUrl = function(endpoint) {
    const base = CONFIG.API_URL.replace(/\/$/, '');
    const path = endpoint.startsWith('/') ? endpoint : '/' + endpoint;
    return base + path;
  };

})();
