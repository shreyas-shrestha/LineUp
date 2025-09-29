// Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    });
}

async function initializeApp() {
    // Test backend connection
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        console.log('✅ Backend connected:', data);
    } catch (err) {
        console.log('⚠️ Backend offline, using fallback mode');
    }
    
    // Load initial data
    loadMockData();
    renderBottomNav();
    switchMode('client');
    
    // Initialize virtual try-on
    appState.virtualTryOnInstance = new VirtualTryOn();
    await appState.virtualTryOnInstance.initialize();
}

// --- Mode Switching ---
function switchMode(mode) {
    appState.currentUserMode = mode;
    
    const clientBtn = document.getElementById('client-mode');
    const barberBtn = document.getElementById('barber-mode');
    const clientContent = document.getElementById('client-content');
    const barberContent = document.getElementById('barber-content');
    
    if (mode === 'client') {
        clientBtn?.classList.add('bg-sky-500', 'text-white');
        clientBtn?.classList.remove('text-gray-400');
        barberBtn?.classList.remove('bg-sky-500', 'text-white');
        barberBtn?.classList.add('text-gray-400');
        clientContent?.classList.remove('hidden');
        barberContent?.classList.add('hidden');
    } else {
        barberBtn?.classList.add('bg-sky-500', 'text-white');
        barberBtn?.classList.remove('text-gray-400');
        clientBtn?.classList.remove('bg-sky-500', 'text-white');
        clientBtn?.classList.add('text-gray-400');
        barberContent?.classList.remove('hidden');
        clientContent?.classList.add('hidden');
    }
    
    renderBottomNav();
    switchTab(mode === 'client' ? 'ai' : 'barber-dashboard');
}

// --- Tab Navigation ---
function renderBottomNav() {
    const nav = elements.bottomNav;
    if (!nav) return;
    
    const clientTabs = [
        { key: 'ai', label: 'Home', icon: '🏠' },
        { key: 'barbers', label: 'Explore', icon: '🔍' },
        { key: 'appointments', label: 'Bookings', icon: '📅', center: true },
        { key: 'community', label: 'Community', icon: '👥' },
        { key: 'profile', label: 'Profile', icon: '👤' }
    ];
    
    const barberTabs = [
        { key: 'barber-dashboard', label: 'Home', icon: '🏠' },
        { key: 'barber-schedule', label: 'Bookings', icon: '📅' },
        { key: 'barber-portfolio', label: 'Portfolio', icon: '✂️', center: true },
        { key: 'community', label: 'Community', icon: '👥' },
        { key: 'barber-profile', label: 'Shop', icon: '🏢' }
    ];
    
    const tabs = appState.currentUserMode === 'client' ? clientTabs : barberTabs;
    const baseBtn = 'tab-button flex flex-col items-center justify-center h-16 flex-1 text-xs transition-all duration-200';
    const centerBtn = 'tab-button center-pill flex flex-col items-center justify-center h-16 w-16 text-xs transition-all duration-200 rounded-full bg-gray-800 border border-gray-700 -translate-y-2';
    
    nav.innerHTML = `
        <div class="flex items-center justify-between px-3">
            ${tabs.map(t => `
                ${t.center ? 
                    `<div class="flex-1 flex items-center justify-center">
                        <button class="${centerBtn} text-gray-200" data-tab="${t.key}">
                            <span class="text-lg leading-none">${t.icon}</span>
                            <span class="text-[10px] mt-1">${t.label}</span>
                        </button>
                    </div>` :
                    `<button class="${baseBtn} text-gray-400" data-tab="${t.key}">
                        <span class="text-lg leading-none">${t.icon}</span>
                        <span class="text-[10px] mt-1">${t.label}</span>
                    </button>`
                }
            `).join('')}
        </div>
    `;
    
    // Attach tab click handlers
    nav.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
}

function switchTab(tabKey) {
    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Show target tab
    const targetContent = document.getElementById(`${tabKey}-tab-content`);
    if (targetContent) {
        targetContent.classList.remove('hidden');
    }
    
    // Update tab button states
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('tab-active', 'text-sky-400', 'bg-gradient-to-r', 'from-sky-500', 'to-purple-500', 'text-white');
        btn.classList.add('text-gray-400');
        
        if (btn.dataset.tab === tabKey) {
            if (btn.classList.contains('center-pill')) {
                btn.classList.add('bg-gradient-to-r', 'from-sky-500', 'to-purple-500', 'text-white');
            } else {
                btn.classList.add('tab-active', 'text-sky-400');
            }
            btn.classList.remove('text-gray-400');
        }
    });
}

// --- Image Upload & Analysis ---
function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = function() {
            // Compress image
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const maxSize = 800;
            let width = img.width;
            let height = img.height;
            
            if (width > height && width > maxSize) {
                height = (height * maxSize) / width;
                width = maxSize;
            } else if (height > maxSize) {
                width = (width * maxSize) / height;
                height = maxSize;
            }
            
            canvas.width = width;
            canvas.height = height;
            ctx.drawImage(img, 0, 0, width, height);
            
            const resizedDataUrl = canvas.toDataURL('image/jpeg', 0.8);
            appState.base64ImageData = resizedDataUrl.split(',')[1];
            appState.uploadedImageSrc = resizedDataUrl;
            
            elements.imagePreview.src = resizedDataUrl;
            elements.imageUploadArea.classList.add('hidden');
            elements.imagePreviewContainer.classList.remove('hidden');
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function analyzeImage() {
    if (!appState.base64ImageData) {
        showError("Please upload a photo first");
        return;
    }
    
    elements.uploadSection.classList.add('hidden');
    elements.statusSection.classList.remove('hidden');
    elements.loader.classList.remove('hidden');
    elements.statusMessage.textContent = "Analyzing your photo with AI...";
    elements.errorContainer.classList.add('hidden');
    
    try {
        const payload = {
            payload: {
                contents: [{
                    parts: [
                        { text: "Analyze this person and provide face, hair info and 5 haircut recommendations." },
                        { inlineData: { mimeType: "image/jpeg", data: appState.base64ImageData } }
                    ]
                }]
            }
        };
        
        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`Analysis failed: ${response.status}`);
        }
        
        const result = await response.json();
        displayResults(result);
        
    } catch (error) {
        console.error('Analysis error:', error);
        // Use mock data as fallback
        setTimeout(() => {
            displayResults(getMockAnalysisData());
        }, 1500);
    } finally {
        elements.loader.classList.add('hidden');
        elements.statusMessage.textContent = '';
    }
}

function displayResults(data) {
    elements.statusSection.classList.add('hidden');
    elements.resultsSection.classList.remove('hidden');
    
    // Display analysis
    displayAnalysis(data.analysis);
    
    // Display recommendations
    displayRecommendations(data.recommendations);
    
    // Store recommended styles for barber search
    appState.lastRecommendedStyles = data.recommendations.map(r => r.styleName);
}

function displayAnalysis(analysis) {
    const analysisData = [
        { label: 'Face Shape', value: capitalizeWords(analysis.faceShape) },
        { label: 'Hair Texture', value: capitalizeWords(analysis.hairTexture) },
        { label: 'Hair Color', value: capitalizeWords(analysis.hairColor) },
        { label: 'Gender', value: capitalizeWords(analysis.estimatedGender) },
        { label: 'Age Range', value: analysis.estimatedAge }
    ];
    
    elements.analysisGrid.innerHTML = analysisData.map(item => `
        <div class="bg-gradient-to-br from-gray-800 to-gray-900 p-5 rounded-xl border border-gray-700 hover:border-sky-500/50 transition-all duration-300">
            <div class="flex items-center gap-2 mb-2">
                <div class="w-2 h-2 bg-sky-400 rounded-full"></div>
                <p class="text-sm font-medium text-gray-300">${item.label}</p>
            </div>
            <p class="font-bold text-xl text-white">${item.value}</p>
        </div>
    `).join('');
}

function displayRecommendations(recommendations) {
    elements.recommendationsContainer.innerHTML = recommendations.map((rec, index) => `
        <div class="bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden flex flex-col hover:border-sky-500/50 transition-all duration-300 transform hover:scale-105">
            <img src="${getStyleImage(rec.styleName)}" alt="${rec.styleName}" 
                 class="w-full h-48 object-cover" 
                 onerror="this.src='https://placehold.co/400x300/1a1a1a/38bdf8?text=${encodeURIComponent(rec.styleName)}'">
            <div class="p-5 flex flex-col flex-grow">
                <h3 class="text-xl font-bold text-white mb-2">${rec.styleName}</h3>
                <p class="text-gray-300 text-sm mb-4 flex-grow">${rec.description}</p>
                <p class="text-xs text-gray-400 mb-4">
                    <strong class="text-sky-400">Why it works:</strong> ${rec.reason}
                </p>
                <div class="grid grid-cols-1 gap-2">
                    <button onclick="tryOnStyle('${rec.styleName}')" 
                            class="w-full bg-purple-500 hover:bg-purple-600 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-105 flex items-center justify-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                        </svg>
                        Try It On (AR)
                    </button>
                    <button onclick="findBarbersForStyle('${rec.styleName}')" 
                            class="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-3 px-4 rounded-lg transition-all duration-300 transform hover:scale-105 flex items-center justify-center gap-2">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        </svg>
                        Find Barbers for This Style
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// --- Barber Search & Filtering ---
async function loadNearbyBarbers(location = 'Atlanta, GA') {
    console.log('Loading barbershops for:', location);
    
    if (elements.barberListContainer) {
        elements.barberListContainer.innerHTML = `
            <div class="text-center py-8">
                <div class="loader mx-auto"></div>
                <p class="mt-4 text-gray-400">Finding real barbershops near you...</p>
            </div>
        `;
    }
    
    try {
        const stylesParam = appState.lastRecommendedStyles.length > 0 ? 
            `&styles=${encodeURIComponent(appState.lastRecommendedStyles.join(','))}` : '';
        
        const response = await fetch(`${API_URL}/barbers?location=${encodeURIComponent(location)}${stylesParam}`);
        const data = await response.json();
        
        if (data.barbers && data.barbers.length > 0) {
            appState.filteredBarbers = data.barbers;
            renderBarberList(data.barbers, data.real_data);
        } else {
            throw new Error('No barbershops found');
        }
    } catch (error) {
        console.error('Error loading barbershops:', error);
        // Use mock data as fallback
        appState.filteredBarbers = getMockBarbers(location);
        renderBarberList(appState.filteredBarbers, false);
    }
}

function renderBarberList(barbers, isRealData = false) {
    if (!elements.barberListContainer) return;
    
    const filteredBarbers = applyFiltersToBarbers(barbers);
    
    const dataSourceBadge = isRealData ? 
        '<span class="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-xs">✓ Real Barbershops</span>' :
        '<span class="bg-yellow-500/20 text-yellow-400 px-3 py-1 rounded-full text-xs">Sample Data</span>';
    
    elements.barberListContainer.innerHTML = `
        <div class="mb-6 p-4 bg-gray-800/50 rounded-xl border border-gray-700">
            <div class="flex justify-between items-center mb-2">
                <p class="text-lg font-semibold text-white">Found ${filteredBarbers.length} barbershops</p>
                ${dataSourceBadge}
            </div>
            <p class="text-sm text-gray-400">
                ${appState.lastRecommendedStyles.length > 0 ? 
                    `Showing barbers specializing in: ${appState.lastRecommendedStyles.join(', ')}` :
                    'Showing all available barbershops'}
            </p>
        </div>
        ${filteredBarbers.map(barber => createBarberCard(barber)).join('')}
    `;
}

function createBarberCard(barber) {
    const openStatus = barber.open_now !== null && barber.open_now !== undefined ?
        (barber.open_now ? 
            '<span class="bg-green-500/20 text-green-400 px-2 py-1 rounded text-xs">Open Now</span>' :
            '<span class="bg-red-500/20 text-red-400 px-2 py-1 rounded text-xs">Closed</span>') : '';
    
    const ratingText = barber.user_ratings_total ? 
        `${barber.rating} ★ (${barber.user_ratings_total} reviews)` :
        `${barber.rating} ★`;
    
    const priceSymbol = '// scripts-fixed.js - Enhanced Frontend JavaScript for LineUp Platform

// --- Configuration ---
const API_URL = 'https://lineup-fjpn.onrender.com';

// --- State Management ---
let appState = {
    currentUserMode: 'client',
    base64ImageData: null,
    uploadedImageSrc: null,
    lastRecommendedStyles: [],
    currentBarberForBooking: null,
    virtualTryOnInstance: null,
    filters: {
        style: '',
        price: '',
        rating: '',
        availability: ''
    },
    socialPosts: [],
    barberPortfolio: [],
    appointments: [],
    filteredBarbers: []
};

// --- DOM Elements Cache ---
const elements = {};

// --- Initialize Application ---
window.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 LineUp Platform Initializing...');
    cacheElements();
    setupEventListeners();
    initializeApp();
});

function cacheElements() {
    // Upload elements
    elements.fileInput = document.getElementById('file-input');
    elements.imageUploadArea = document.getElementById('image-upload-area');
    elements.imagePreviewContainer = document.getElementById('image-preview-container');
    elements.imagePreview = document.getElementById('image-preview');
    elements.analyzeButton = document.getElementById('analyze-button');
    
    // Status elements
    elements.uploadSection = document.getElementById('upload-section');
    elements.statusSection = document.getElementById('status-section');
    elements.loader = document.getElementById('loader');
    elements.statusMessage = document.getElementById('status-message');
    elements.errorContainer = document.getElementById('error-container');
    elements.errorMessage = document.getElementById('error-message');
    
    // Results elements
    elements.resultsSection = document.getElementById('results-section');
    elements.analysisGrid = document.getElementById('analysis-grid');
    elements.recommendationsContainer = document.getElementById('recommendations-container');
    
    // Barber search elements
    elements.barberListContainer = document.getElementById('barber-list-container');
    elements.locationSearch = document.getElementById('location-search');
    elements.styleFilter = document.getElementById('style-filter');
    elements.priceFilter = document.getElementById('price-filter');
    elements.ratingFilter = document.getElementById('rating-filter');
    elements.availabilityFilter = document.getElementById('availability-filter');
    
    // Modal elements
    elements.virtualTryonModal = document.getElementById('virtual-tryon-modal');
    elements.bookAppointmentModal = document.getElementById('book-appointment-modal');
    
    // Navigation elements
    elements.bottomNav = document.getElementById('bottom-nav');
}

function setupEventListeners() {
    // Role switching
    document.getElementById('client-mode')?.addEventListener('click', () => switchMode('client'));
    document.getElementById('barber-mode')?.addEventListener('click', () => switchMode('barber'));
    
    // Image upload
    elements.imageUploadArea?.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput?.addEventListener('change', handleImageUpload);
    elements.analyzeButton?.addEventListener('click', analyzeImage);
    
    // Reset buttons
    document.getElementById('try-again-button')?.addEventListener('click', resetUI);
    document.getElementById('start-over-button')?.addEventListener('click', resetUI);
    
    // Barber search and filters
    document.getElementById('refresh-barbers')?.addEventListener('click', () => {
        const location = elements.locationSearch.value || 'Atlanta, GA';
        loadNearbyBarbers(location);
    });
    
    document.getElementById('find-barber-button')?.addEventListener('click', findMatchingBarbers);
    
    // Filter changes
    [elements.styleFilter, elements.priceFilter, elements.ratingFilter, elements.availabilityFilter].forEach(filter => {
        filter?.addEventListener('change', applyFilters);
    });
    
    // Location search with debouncing
    let searchTimeout;
    elements.locationSearch?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const value = e.target.value.trim();
        if (value.length > 2) {
            searchTimeout = setTimeout(() => loadNearbyBarbers(value), 500);
        }
    });
    
    // Virtual Try-On controls
    document.getElementById('close-tryon-modal')?.addEventListener('click', closeTryOnModal);
    document.getElementById('start-tryon')?.addEventListener('click', startARTryOn);
    document.getElementById('stop-tryon')?.addEventListener('click', stopARTryOn);
    document.getElementById('take-screenshot')?.addEventListener('click', takeARScreenshot);
    document.getElementById('switch-camera')?.addEventListener('click', switchARCamera);
    document.getElementById('reset-ar')?.addEventListener('click', resetARPosition);
    
    // Appointment modal
    document.getElementById('cancel-booking')?.addEventListener('click', closeBookingModal);
    document.getElementById('confirm-booking')?.addEventListener('click', confirmBooking);
    
    // Social feed
    document.getElementById('add-post-button')?.addEventListener('click', () => {
        document.getElementById('add-post-modal')?.classList.remove('hidden');
    });
    
    // Portfolio
    document.getElementById('upload-work-button')?.addEventListener('click', () => {
        document.getElementById('upload-work-modal')?.classList.remove('hidden');
    });
    
    // Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    });.repeat(barber.price_level || 2);
    
    return `
        <div class="bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden mb-4 hover:border-sky-500/50 transition-all">
            <div class="flex flex-col sm:flex-row">
                ${barber.photo ? 
                    `<img src="${barber.photo}" alt="${barber.name}" 
                          class="w-full sm:w-48 h-48 sm:h-auto object-cover" 
                          onerror="this.src='https://placehold.co/400x300/1a1a1a/38bdf8?text=Barbershop'">` :
                    `<div class="w-full sm:w-48 h-48 sm:h-auto bg-gray-800 flex items-center justify-center">
                        <svg class="w-16 h-16 text-gray-600" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                    </div>`
                }
                <div class="p-5 flex-1">
                    <div class="flex justify-between items-start mb-2">
                        <div class="flex-1">
                            <h4 class="text-xl font-bold text-white mb-1">${barber.name}</h4>
                            <p class="text-sm text-gray-400">${barber.address}</p>
                        </div>
                        ${openStatus}
                    </div>
                    
                    <div class="flex items-center gap-4 mb-3">
                        <span class="text-yellow-400 flex items-center gap-1">${ratingText}</span>
                        <span class="text-green-400 font-semibold">${priceSymbol} ~${barber.avgCost}</span>
                        ${barber.phone !== 'Call for info' ? 
                            `<a href="tel:${barber.phone}" class="text-sky-400 hover:text-sky-300 text-sm">${barber.phone}</a>` :
                            ''
                        }
                    </div>
                    
                    <div class="flex flex-wrap gap-2 mb-4">
                        ${barber.specialties.map(s => 
                            `<span class="bg-sky-500/20 border border-sky-500/50 text-sky-300 text-xs px-3 py-1 rounded-full">${s}</span>`
                        ).join('')}
                    </div>
                    
                    <div class="flex gap-2">
                        <button onclick="openBookingModal('${barber.id}', '${barber.name.replace(/'/g, "\\'")}')" 
                                class="bg-green-500 text-white px-6 py-2 rounded-lg hover:bg-green-600 transition-colors">
                            Book Appointment
                        </button>
                        ${barber.website ? 
                            `<a href="${barber.website}" target="_blank" 
                                class="bg-gray-700 text-white px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors">
                                Website
                            </a>` : ''
                        }
                        ${barber.location ? 
                            `<a href="https://www.google.com/maps/dir/?api=1&destination=${barber.location.lat},${barber.location.lng}" 
                               target="_blank" 
                               class="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 transition-colors">
                                Directions
                            </a>` : ''
                        }
                    </div>
                </div>
            </div>
        </div>
    `;
}

function applyFilters() {
    // Update filter state
    appState.filters = {
        style: elements.styleFilter?.value || '',
        price: elements.priceFilter?.value || '',
        rating: elements.ratingFilter?.value || '',
        availability: elements.availabilityFilter?.value || ''
    };
    
    // Re-render barber list with filters
    if (appState.filteredBarbers.length > 0) {
        renderBarberList(appState.filteredBarbers, true);
    }
}

function applyFiltersToBarbers(barbers) {
    return barbers.filter(barber => {
        // Style filter
        if (appState.filters.style) {
            const hasStyle = barber.specialties.some(s => 
                s.toLowerCase().includes(appState.filters.style.toLowerCase())
            );
            if (!hasStyle) return false;
        }
        
        // Price filter
        if (appState.filters.price) {
            const priceLevel = appState.filters.price.length;
            if (barber.price_level && barber.price_level !== priceLevel) return false;
        }
        
        // Rating filter
        if (appState.filters.rating) {
            const minRating = parseFloat(appState.filters.rating);
            if (barber.rating < minRating) return false;
        }
        
        // Availability filter
        if (appState.filters.availability === 'open-now' && barber.open_now === false) {
            return false;
        }
        
        return true;
    });
}

function findMatchingBarbers() {
    const location = elements.locationSearch?.value || 'Atlanta, GA';
    loadNearbyBarbers(location);
    switchTab('barbers');
}

function findBarbersForStyle(styleName) {
    console.log(`Finding barbers for style: ${styleName}`);
    appState.lastRecommendedStyles = [styleName];
    
    const location = elements.locationSearch?.value || 'Atlanta, GA';
    loadNearbyBarbers(location);
    switchTab('barbers');
}

// --- Virtual Try-On Functions ---
async function tryOnStyle(styleName) {
    console.log(`Opening AR try-on for: ${styleName}`);
    
    elements.virtualTryonModal?.classList.remove('hidden');
    
    const styleInfo = document.getElementById('current-tryon-style');
    if (styleInfo) {
        styleInfo.innerHTML = `
            <span class="text-sky-400 font-semibold">Trying on: ${styleName}</span>
            <p class="text-xs text-gray-400 mt-1">Use controls below to adjust position and size</p>
        `;
    }
    
    // Load hairstyle
    if (appState.virtualTryOnInstance) {
        await appState.virtualTryOnInstance.loadHairstyle(styleName);
    }
}

async function startARTryOn() {
    const videoEl = document.getElementById('virtual-tryon-video');
    const canvasEl = document.getElementById('virtual-tryon-canvas');
    const photoEl = document.getElementById('virtual-tryon-photo');
    const loading = document.getElementById('tryon-loading');
    
    try {
        loading?.classList.remove('hidden');
        
        let success = false;
        if (appState.uploadedImageSrc) {
            // Use uploaded photo
            videoEl.style.display = 'none';
            photoEl.style.display = 'block';
            success = await appState.virtualTryOnInstance.startOnImage(photoEl, canvasEl, appState.uploadedImageSrc);
        } else {
            // Use camera
            photoEl.style.display = 'none';
            videoEl.style.display = 'block';
            success = await appState.virtualTryOnInstance.startTryOn(videoEl, canvasEl);
        }
        
        if (success) {
            document.getElementById('start-tryon')?.classList.add('hidden');
            document.getElementById('stop-tryon')?.classList.remove('hidden');
            document.getElementById('take-screenshot')?.classList.remove('hidden');
            document.getElementById('switch-camera')?.classList.remove('hidden');
        }
    } catch (error) {
        console.error('AR Try-On error:', error);
        alert('Camera access is required for AR Try-On. Please check your permissions.');
    } finally {
        loading?.classList.add('hidden');
    }
}

function stopARTryOn() {
    appState.virtualTryOnInstance?.stopTryOn();
    
    document.getElementById('start-tryon')?.classList.remove('hidden');
    document.getElementById('stop-tryon')?.classList.add('hidden');
    document.getElementById('take-screenshot')?.classList.add('hidden');
    document.getElementById('switch-camera')?.classList.add('hidden');
}

function takeARScreenshot() {
    const screenshot = appState.virtualTryOnInstance?.takeScreenshot();
    if (screenshot) {
        // Create download link
        const link = document.createElement('a');
        link.download = `lineup-tryon-${Date.now()}.png`;
        link.href = screenshot;
        link.click();
        
        alert('Screenshot saved! Check your downloads folder.');
    }
}

async function switchARCamera() {
    await appState.virtualTryOnInstance?.switchCamera();
}

function resetARPosition() {
    if (appState.virtualTryOnInstance) {
        appState.virtualTryOnInstance.resetPosition();
        appState.virtualTryOnInstance.updateOverlayTransform();
    }
}

function closeTryOnModal() {
    stopARTryOn();
    elements.virtualTryonModal?.classList.add('hidden');
}

function changeHairColor(color) {
    appState.virtualTryOnInstance?.changeColor(color);
}

// --- Appointment Booking ---
function openBookingModal(barberId, barberName) {
    appState.currentBarberForBooking = { id: barberId, name: barberName };
    
    const bookingInfo = document.getElementById('booking-barber-info');
    if (bookingInfo) {
        bookingInfo.innerHTML = `
            <p class="text-lg font-semibold text-white">Booking with ${barberName}</p>
            <p class="text-sm text-gray-400">Select your preferred date and time</p>
        `;
    }
    
    // Set minimum date to today
    const dateInput = document.getElementById('appointment-date');
    if (dateInput) {
        dateInput.min = new Date().toISOString().split('T')[0];
    }
    
    elements.bookAppointmentModal?.classList.remove('hidden');
}

function closeBookingModal() {
    elements.bookAppointmentModal?.classList.add('hidden');
    
    // Clear form
    document.getElementById('appointment-date').value = '';
    document.getElementById('appointment-time').value = '';
    document.getElementById('appointment-service').value = '';
    document.getElementById('appointment-notes').value = '';
}

async function confirmBooking() {
    const date = document.getElementById('appointment-date')?.value;
    const time = document.getElementById('appointment-time')?.value;
    const service = document.getElementById('appointment-service')?.value;
    const notes = document.getElementById('appointment-notes')?.value;
    
    if (!date || !time || !service) {
        alert('Please fill in all required fields');
        return;
    }
    
    const serviceMap = {
        'haircut': { name: 'Haircut', price: '$45' },
        'haircut-beard': { name: 'Haircut + Beard', price: '$65' },
        'beard-only': { name: 'Beard Trim', price: '$25' }
    };
    
    const appointment = {
        id: Date.now(),
        clientName: 'Current User',
        barberName: appState.currentBarberForBooking.name,
        barberId: appState.currentBarberForBooking.id,
        date: date,
        time: time,
        service: serviceMap[service].name,
        price: serviceMap[service].price,
        notes: notes || 'No special requests',
        status: 'pending'
    };
    
    // Add to appointments
    appState.appointments.push(appointment);
    
    // Show success
    alert(`Appointment booked with ${appState.currentBarberForBooking.name} on ${date} at ${time}!`);
    
    closeBookingModal();
    renderAppointments();
}

// --- UI Helper Functions ---
function resetUI() {
    elements.uploadSection?.classList.remove('hidden');
    elements.statusSection?.classList.add('hidden');
    elements.resultsSection?.classList.add('hidden');
    elements.errorContainer?.classList.add('hidden');
    elements.loader?.classList.add('hidden');
    elements.imageUploadArea?.classList.remove('hidden');
    elements.imagePreviewContainer?.classList.add('hidden');
    
    if (elements.imagePreview) elements.imagePreview.src = '';
    if (elements.fileInput) elements.fileInput.value = '';
    
    appState.base64ImageData = null;
    appState.uploadedImageSrc = null;
    appState.lastRecommendedStyles = [];
}

function showError(message) {
    elements.loader?.classList.add('hidden');
    elements.statusMessage.textContent = '';
    elements.errorContainer?.classList.remove('hidden');
    if (elements.errorMessage) {
        elements.errorMessage.textContent = message;
    }
}

function capitalizeWords(str) {
    if (!str) return '';
    return str.split(/[-_\s]/).map(word => 
        word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    ).join(' ');
}

function getStyleImage(styleName) {
    const styleImages = {
        'modern fade': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=300&fit=crop',
        'classic fade': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=300&fit=crop',
        'fade': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=300&fit=crop',
        'textured quiff': 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=400&h=300&fit=crop',
        'quiff': 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=400&h=300&fit=crop',
        'pompadour': 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=400&h=300&fit=crop',
        'side part': 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=300&fit=crop',
        'messy crop': 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=300&fit=crop',
        'crop': 'https://images.unsplash.com/photo-1519741497674-611481863552?w=400&h=300&fit=crop',
        'buzz cut': 'https://images.unsplash.com/photo-1514790193030-c89d266d5a9d?w=400&h=300&fit=crop',
        'buzz': 'https://images.unsplash.com/photo-1514790193030-c89d266d5a9d?w=400&h=300&fit=crop'
    };
    
    const normalizedName = styleName.toLowerCase().trim();
    
    // Try exact match first
    if (styleImages[normalizedName]) {
        return styleImages[normalizedName];
    }
    
    // Try partial match
    for (const [key, value] of Object.entries(styleImages)) {
        if (normalizedName.includes(key) || key.includes(normalizedName)) {
            return value;
        }
    }
    
    // Default fallback
    return 'https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop';
}

// --- Mock Data Functions ---
function loadMockData() {
    // Load social posts
    appState.socialPosts = [
        {
            id: 1,
            username: 'mike_style',
            avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face',
            image: 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop',
            caption: 'Fresh fade from @atlanta_cuts 🔥',
            likes: 23,
            timeAgo: '2h',
            liked: false
        },
        {
            id: 2,
            username: 'sarah_hair',
            avatar: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=100&h=100&fit=crop&crop=face',
            image: 'https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=400&fit=crop',
            caption: 'New bob cut! Love how it frames my face ✨',
            likes: 45,
            timeAgo: '4h',
            liked: true
        }
    ];
    
    // Load appointments
    appState.appointments = [
        {
            id: 1,
            clientName: 'Current User',
            barberName: 'Elite Cuts Atlanta',
            date: '2024-01-25',
            time: '14:00',
            service: 'Haircut + Beard',
            price: '$65',
            status: 'confirmed'
        }
    ];
    
    renderSocialFeed();
    renderAppointments();
}

function getMockAnalysisData() {
    return {
        analysis: {
            faceShape: "oval",
            hairTexture: "wavy",
            hairColor: "brown",
            estimatedGender: "male",
            estimatedAge: "25-30"
        },
        recommendations: [
            {
                styleName: "Modern Fade",
                description: "A contemporary take on the classic fade with textured top for versatile styling",
                reason: "Complements oval face shapes perfectly and works well with wavy hair texture"
            },
            {
                styleName: "Textured Quiff",
                description: "Voluminous style swept upward and back for a bold, confident look",
                reason: "Takes advantage of your wavy hair texture for natural volume and movement"
            },
            {
                styleName: "Classic Side Part",
                description: "Timeless and professional with clean lines and sophisticated appearance",
                reason: "Enhances facial symmetry and adds a touch of classic sophistication"
            },
            {
                styleName: "Messy Crop",
                description: "Effortlessly cool with natural texture and tousled finish",
                reason: "Low maintenance option that embraces your natural hair texture"
            },
            {
                styleName: "Buzz Cut",
                description: "Clean, minimal, and masculine with very short length all over",
                reason: "Highlights your facial structure and requires minimal styling"
            }
        ]
    };
}

function getMockBarbers(location) {
    const cityName = location.split(',')[0].trim();
    
    return [
        {
            id: 'mock_1',
            name: `Elite Cuts ${cityName}`,
            address: `Downtown ${cityName}`,
            rating: 4.9,
            user_ratings_total: 157,
            price_level: 2,
            avgCost: 45,
            phone: '(555) 123-4567',
            website: 'https://example.com',
            photo: 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop',
            specialties: ['Fade Specialist', 'Modern Cuts', 'Beard Trim'],
            open_now: true,
            location: { lat: 33.7490, lng: -84.3880 }
        },
        {
            id: 'mock_2',
            name: `The ${cityName} Barber`,
            address: `Midtown ${cityName}`,
            rating: 4.8,
            user_ratings_total: 89,
            price_level: 3,
            avgCost: 55,
            phone: '(555) 123-4568',
            website: '',
            photo: 'https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop',
            specialties: ['Classic Cuts', 'Pompadour', 'Hot Shave'],
            open_now: false,
            location: { lat: 33.7510, lng: -84.3870 }
        },
        {
            id: 'mock_3',
            name: `${cityName} Style Studio`,
            address: `Uptown ${cityName}`,
            rating: 4.9,
            user_ratings_total: 203,
            price_level: 4,
            avgCost: 75,
            phone: '(555) 123-4569',
            website: 'https://example.com',
            photo: 'https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop',
            specialties: ['Modern Styles', 'Color', 'Styling'],
            open_now: true,
            location: { lat: 33.7520, lng: -84.3860 }
        }
    ];
}

// --- Social Feed Functions ---
function renderSocialFeed() {
    const container = document.getElementById('social-feed-container');
    if (!container) return;
    
    container.innerHTML = appState.socialPosts.map(post => `
        <div class="bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden">
            <div class="p-4 flex items-center gap-3">
                <img src="${post.avatar}" alt="${post.username}" class="w-10 h-10 rounded-full object-cover">
                <div>
                    <p class="font-semibold text-white">${post.username}</p>
                    <p class="text-xs text-gray-400">${post.timeAgo}</p>
                </div>
            </div>
            <img src="${post.image}" alt="Post" class="w-full h-80 object-cover">
            <div class="p-4">
                <div class="flex items-center gap-4 mb-2">
                    <button onclick="toggleLike(${post.id})" 
                            class="flex items-center gap-2 transition-colors ${post.liked ? 'text-red-500' : 'text-gray-400 hover:text-red-500'}">
                        <svg class="w-6 h-6 ${post.liked ? 'fill-current' : ''}" 
                             fill="${post.liked ? 'currentColor' : 'none'}" 
                             stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                  d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z">
                            </path>
                        </svg>
                        <span class="text-sm font-semibold">${post.likes}</span>
                    </button>
                </div>
                <p class="text-gray-300">${post.caption}</p>
            </div>
        </div>
    `).join('');
}

function toggleLike(postId) {
    const post = appState.socialPosts.find(p => p.id === postId);
    if (post) {
        post.liked = !post.liked;
        post.likes += post.liked ? 1 : -1;
        renderSocialFeed();
    }
}

// --- Appointments Functions ---
function renderAppointments() {
    const container = document.getElementById('client-appointments-container');
    const noAppointments = document.getElementById('no-appointments');
    
    if (!container) return;
    
    if (appState.appointments.length === 0) {
        container.innerHTML = '';
        if (noAppointments) noAppointments.classList.remove('hidden');
    } else {
        if (noAppointments) noAppointments.classList.add('hidden');
        
        container.innerHTML = appState.appointments.map(apt => `
            <div class="bg-gray-900/50 border border-gray-700 rounded-2xl p-5">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="text-lg font-bold text-white">${apt.barberName}</h3>
                        <p class="text-gray-400">${apt.service}</p>
                    </div>
                    <span class="px-3 py-1 rounded-full text-xs font-semibold ${
                        apt.status === 'confirmed' ? 
                        'bg-green-500/20 text-green-300' : 
                        'bg-yellow-500/20 text-yellow-300'
                    }">
                        ${capitalizeWords(apt.status)}
                    </span>
                </div>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <p class="text-gray-300">
                        <span class="text-gray-400">Date:</span> 
                        ${new Date(apt.date).toLocaleDateString()}
                    </p>
                    <p class="text-gray-300">
                        <span class="text-gray-400">Time:</span> ${apt.time}
                    </p>
                    <p class="text-gray-300">
                        <span class="text-gray-400">Price:</span> ${apt.price}
                    </p>
                    <p class="text-gray-300">
                        <span class="text-gray-400">Status:</span> ${apt.status}
                    </p>
                </div>
                ${apt.notes && apt.notes !== 'No special requests' ? 
                    `<p class="text-gray-400 text-sm mt-3">Notes: ${apt.notes}</p>` : ''
                }
            </div>
        `).join('');
    }
}

// --- Global Functions for onclick handlers ---
window.tryOnStyle = tryOnStyle;
window.findBarbersForStyle = findBarbersForStyle;
window.openBookingModal = openBookingModal;
window.toggleLike = toggleLike;
window.changeHairColor = changeHairColor;

console.log('✅ LineUp Platform Ready!');// scripts-fixed.js - Enhanced Frontend JavaScript for LineUp Platform

// --- Configuration ---
const API_URL = 'https://lineup-fjpn.onrender.com';

// --- State Management ---
let appState = {
    currentUserMode: 'client',
    base64ImageData: null,
    uploadedImageSrc: null,
    lastRecommendedStyles: [],
    currentBarberForBooking: null,
    virtualTryOnInstance: null,
    filters: {
        style: '',
        price: '',
        rating: '',
        availability: ''
    },
    socialPosts: [],
    barberPortfolio: [],
    appointments: [],
    filteredBarbers: []
};

// --- DOM Elements Cache ---
const elements = {};

// --- Initialize Application ---
window.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 LineUp Platform Initializing...');
    cacheElements();
    setupEventListeners();
    initializeApp();
});

function cacheElements() {
    // Upload elements
    elements.fileInput = document.getElementById('file-input');
    elements.imageUploadArea = document.getElementById('image-upload-area');
    elements.imagePreviewContainer = document.getElementById('image-preview-container');
    elements.imagePreview = document.getElementById('image-preview');
    elements.analyzeButton = document.getElementById('analyze-button');
    
    // Status elements
    elements.uploadSection = document.getElementById('upload-section');
    elements.statusSection = document.getElementById('status-section');
    elements.loader = document.getElementById('loader');
    elements.statusMessage = document.getElementById('status-message');
    elements.errorContainer = document.getElementById('error-container');
    elements.errorMessage = document.getElementById('error-message');
    
    // Results elements
    elements.resultsSection = document.getElementById('results-section');
    elements.analysisGrid = document.getElementById('analysis-grid');
    elements.recommendationsContainer = document.getElementById('recommendations-container');
    
    // Barber search elements
    elements.barberListContainer = document.getElementById('barber-list-container');
    elements.locationSearch = document.getElementById('location-search');
    elements.styleFilter = document.getElementById('style-filter');
    elements.priceFilter = document.getElementById('price-filter');
    elements.ratingFilter = document.getElementById('rating-filter');
    elements.availabilityFilter = document.getElementById('availability-filter');
    
    // Modal elements
    elements.virtualTryonModal = document.getElementById('virtual-tryon-modal');
    elements.bookAppointmentModal = document.getElementById('book-appointment-modal');
    
    // Navigation elements
    elements.bottomNav = document.getElementById('bottom-nav');
}

function setupEventListeners() {
    // Role switching
    document.getElementById('client-mode')?.addEventListener('click', () => switchMode('client'));
    document.getElementById('barber-mode')?.addEventListener('click', () => switchMode('barber'));
    
    // Image upload
    elements.imageUploadArea?.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput?.addEventListener('change', handleImageUpload);
    elements.analyzeButton?.addEventListener('click', analyzeImage);
    
    // Reset buttons
    document.getElementById('try-again-button')?.addEventListener('click', resetUI);
    document.getElementById('start-over-button')?.addEventListener('click', resetUI);
    
    // Barber search and filters
    document.getElementById('refresh-barbers')?.addEventListener('click', () => {
        const location = elements.locationSearch.value || 'Atlanta, GA';
        loadNearbyBarbers(location);
    });
    
    document.getElementById('find-barber-button')?.addEventListener('click', findMatchingBarbers);
    
    // Filter changes
    [elements.styleFilter, elements.priceFilter, elements.ratingFilter, elements.availabilityFilter].forEach(filter => {
        filter?.addEventListener('change', applyFilters);
    });
    
    // Location search with debouncing
    let searchTimeout;
    elements.locationSearch?.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const value = e.target.value.trim();
        if (value.length > 2) {
            searchTimeout = setTimeout(() => loadNearbyBarbers(value), 500);
        }
    });
    
    // Virtual Try-On controls
    document.getElementById('close-tryon-modal')?.addEventListener('click', closeTryOnModal);
    document.getElementById('start-tryon')?.addEventListener('click', startARTryOn);
    document.getElementById('stop-tryon')?.addEventListener('click', stopARTryOn);
    document.getElementById('take-screenshot')?.addEventListener('click', takeARScreenshot);
    document.getElementById('switch-camera')?.addEventListener('click', switchARCamera);
    document.getElementById('reset-ar')?.addEventListener('click', resetARPosition);
    
    // Appointment modal
    document.getElementById('cancel-booking')?.addEventListener('click', closeBookingModal);
    document.getElementById('confirm-booking')?.addEventListener('click', confirmBooking);
    
    // Social feed
    document.getElementById('add-post-button')?.addEventListener('click', () => {
        document.getElementById('add-post-modal')?.classList.remove('hidden');
    });
    
    // Portfolio
    document.getElementById('upload-work-button')?.addEventListener('click', () => {
        document.getElementById('upload-work-modal')?.classList.remove('hidden');
    });
    
    // Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    });
