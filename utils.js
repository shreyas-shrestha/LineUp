// utils.js - Frontend Utility Functions (Optimized)

/**
 * Debounce function - prevents excessive function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
export function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function - limits function execution rate
 * @param {Function} func - Function to throttle
 * @param {number} limit - Minimum time between calls
 * @returns {Function} - Throttled function
 */
export function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Efficient DOM manipulation using DocumentFragment
 * @param {Array} items - Array of items to render
 * @param {Function} createElementFn - Function to create DOM element from item
 * @param {HTMLElement} container - Container to append elements to
 */
export function renderWithFragment(items, createElementFn, container) {
    const fragment = document.createDocumentFragment();
    
    items.forEach(item => {
        const element = createElementFn(item);
        fragment.appendChild(element);
    });
    
    // Clear container and append all at once
    container.innerHTML = '';
    container.appendChild(fragment);
}

/**
 * Lazy load images using Intersection Observer
 * @param {string} selector - CSS selector for images to lazy load
 */
export function lazyLoadImages(selector = 'img[data-src]') {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
                
                // Add loaded class for fade-in effect
                img.classList.add('loaded');
            }
        });
    }, {
        rootMargin: '50px' // Load slightly before entering viewport
    });
    
    document.querySelectorAll(selector).forEach(img => {
        imageObserver.observe(img);
    });
}

/**
 * Cache API responses in localStorage
 * @param {string} key - Cache key
 * @param {any} data - Data to cache
 * @param {number} ttl - Time to live in milliseconds
 */
export function cacheSet(key, data, ttl = 3600000) { // Default 1 hour
    const item = {
        data: data,
        expiry: Date.now() + ttl
    };
    try {
        localStorage.setItem(key, JSON.stringify(item));
    } catch (e) {
        console.warn('localStorage full, clearing old cache');
        // Clear old cache items
        cacheClear();
        try {
            localStorage.setItem(key, JSON.stringify(item));
        } catch (e2) {
            console.error('Failed to cache data:', e2);
        }
    }
}

/**
 * Get cached data from localStorage
 * @param {string} key - Cache key
 * @returns {any|null} - Cached data or null if expired/not found
 */
export function cacheGet(key) {
    try {
        const itemStr = localStorage.getItem(key);
        if (!itemStr) return null;
        
        const item = JSON.parse(itemStr);
        
        // Check if expired
        if (Date.now() > item.expiry) {
            localStorage.removeItem(key);
            return null;
        }
        
        return item.data;
    } catch (e) {
        console.error('Cache get error:', e);
        return null;
    }
}

/**
 * Clear expired cache items
 */
export function cacheClear() {
    try {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith('cache_')) {
                const item = JSON.parse(localStorage.getItem(key));
                if (Date.now() > item.expiry) {
                    localStorage.removeItem(key);
                }
            }
        });
    } catch (e) {
        console.error('Cache clear error:', e);
    }
}

/**
 * Sanitize HTML to prevent XSS
 * @param {string} str - String to sanitize
 * @returns {string} - Sanitized string
 */
export function sanitizeHTML(str) {
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}

/**
 * Create element from HTML string efficiently
 * @param {string} html - HTML string
 * @returns {HTMLElement} - Created element
 */
export function createElementFromHTML(html) {
    const template = document.createElement('template');
    template.innerHTML = html.trim();
    return template.content.firstChild;
}

/**
 * Retry failed API calls with exponential backoff
 * @param {Function} fn - Async function to retry
 * @param {number} retries - Number of retry attempts
 * @param {number} delay - Initial delay in ms
 * @returns {Promise} - Result of function call
 */
export async function retryWithBackoff(fn, retries = 3, delay = 1000) {
    try {
        return await fn();
    } catch (error) {
        if (retries === 0) throw error;
        
        console.warn(`Retry attempt ${4 - retries} failed, retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return retryWithBackoff(fn, retries - 1, delay * 2);
    }
}

/**
 * Format relative time (e.g., "2h ago", "3d ago")
 * @param {Date|string} date - Date to format
 * @returns {string} - Formatted relative time
 */
export function formatRelativeTime(date) {
    const now = new Date();
    const then = new Date(date);
    const diffMs = now - then;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    return then.toLocaleDateString();
}

/**
 * Batch multiple state updates to prevent excessive re-renders
 */
export class BatchUpdater {
    constructor(updateFn, delay = 16) { // 16ms = ~60fps
        this.updateFn = updateFn;
        this.delay = delay;
        this.pending = [];
        this.timeout = null;
    }
    
    add(update) {
        this.pending.push(update);
        
        if (!this.timeout) {
            this.timeout = setTimeout(() => {
                this.updateFn(this.pending);
                this.pending = [];
                this.timeout = null;
            }, this.delay);
        }
    }
    
    flush() {
        if (this.timeout) {
            clearTimeout(this.timeout);
            this.updateFn(this.pending);
            this.pending = [];
            this.timeout = null;
        }
    }
}

/**
 * Check if user is online
 * @returns {boolean} - Online status
 */
export function isOnline() {
    return navigator.onLine;
}

/**
 * Register online/offline listeners
 * @param {Function} onOnline - Callback when online
 * @param {Function} onOffline - Callback when offline
 */
export function registerConnectivityListeners(onOnline, onOffline) {
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    
    // Return cleanup function
    return () => {
        window.removeEventListener('online', onOnline);
        window.removeEventListener('offline', onOffline);
    };
}

/**
 * Compress image before upload
 * @param {File} file - Image file
 * @param {number} maxWidth - Maximum width
 * @param {number} maxHeight - Maximum height
 * @param {number} quality - JPEG quality (0-1)
 * @returns {Promise<string>} - Base64 compressed image
 */
export function compressImage(file, maxWidth = 1024, maxHeight = 1024, quality = 0.8) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const img = new Image();
            
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                let width = img.width;
                let height = img.height;
                
                // Calculate new dimensions
                if (width > height && width > maxWidth) {
                    height = (height * maxWidth) / width;
                    width = maxWidth;
                } else if (height > maxHeight) {
                    width = (width * maxHeight) / height;
                    height = maxHeight;
                }
                
                canvas.width = width;
                canvas.height = height;
                
                // Draw and compress
                ctx.drawImage(img, 0, 0, width, height);
                const compressedDataUrl = canvas.toDataURL('image/jpeg', quality);
                
                // Extract base64
                const base64 = compressedDataUrl.split(',')[1];
                resolve(base64);
            };
            
            img.onerror = reject;
            img.src = e.target.result;
        };
        
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

