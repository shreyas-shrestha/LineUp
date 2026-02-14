// scripts-updated.js - Frontend JavaScript for LineUp Two-Sided Platform

// --- Configuration ---
// Use centralized config from config.js (LINEUP_CONFIG) with fallbacks
const API_URL = (window.LINEUP_CONFIG && window.LINEUP_CONFIG.API_URL) || 
                (window.LineUpConfig && window.LineUpConfig.apiUrl) || 
                'http://localhost:5000';

// Feature flags and UI config
const CONFIG = window.LINEUP_CONFIG || {
  FEATURES: { 
    virtualTryOn: true, 
    socialFeed: false, 
    subscriptionPackages: true,
    googlePlacesSearch: true,
    contentModeration: true
  },
  UI: { 
    defaultLocation: 'Atlanta, GA', 
    maxImageSizeMB: 5,
    supportedImageTypes: ['image/jpeg', 'image/png', 'image/webp']
  },
  DEBUG: false,
  MOCK_MODE: false
};

// Log configuration status
if (window.LINEUP_CONFIG) {
  console.log('✅ LineUp Config loaded:', { apiUrl: API_URL, debug: CONFIG.DEBUG });
} else if (window.LineUpConfig) {
  console.log('✅ Using legacy LineUpConfig:', { apiUrl: API_URL });
} else {
  console.warn('⚠️ No config loaded, using defaults. API:', API_URL);
}

// --- DOM Elements ---
const fileInput = document.getElementById('file-input');
const imageUploadArea = document.getElementById('image-upload-area');
const imagePreviewContainer = document.getElementById('image-preview-container');
const imagePreview = document.getElementById('image-preview');
const analyzeButton = document.getElementById('analyze-button');
const uploadSection = document.getElementById('upload-section');
const statusSection = document.getElementById('status-section');
const loader = document.getElementById('loader');
const statusMessage = document.getElementById('status-message');
const errorContainer = document.getElementById('error-container');
const errorMessage = document.getElementById('error-message');
const tryAgainButton = document.getElementById('try-again-button');
const resultsSection = document.getElementById('results-section');
const analysisGrid = document.getElementById('analysis-grid');
const recommendationsContainer = document.getElementById('recommendations-container');
const startOverButton = document.getElementById('start-over-button');
const findBarberButton = document.getElementById('find-barber-button');
const barberListContainer = document.getElementById('barber-list-container');
const barberIntro = document.getElementById('barber-intro');
const locationSearch = document.getElementById('location-search');
const refreshBarbersBtn = document.getElementById('refresh-barbers');
const bottomNav = document.getElementById('bottom-nav');

// Client content
const clientContent = document.getElementById('client-content');

// Appointment elements
const bookAppointmentModal = document.getElementById('book-appointment-modal');
const clientAppointmentsContainer = document.getElementById('client-appointments-container');
const noAppointments = document.getElementById('no-appointments');

// --- State ---
let base64ImageData = null;
let lastRecommendedStyles = [];
let appointments = [];
let currentBarberForBooking = null;
let nearbyBarbers = []; // Store loaded barbers for booking URL access

// --- Toast Notification System ---
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  // Trigger show animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  // Auto-dismiss
  setTimeout(() => {
    toast.classList.remove('show');
    toast.classList.add('hide');
    setTimeout(() => toast.remove(), 350);
  }, duration);
}

// --- Skeleton Loading Helpers ---
function createBarberSkeleton(count = 3) {
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden mb-4">
        <div class="flex flex-col sm:flex-row">
          <div class="w-full sm:w-48 h-48 sm:h-auto skeleton"></div>
          <div class="p-5 flex-1 space-y-3">
            <div class="skeleton h-6 w-3/4"></div>
            <div class="skeleton h-4 w-1/2"></div>
            <div class="flex gap-2">
              <div class="skeleton h-6 w-20 rounded-full"></div>
              <div class="skeleton h-6 w-24 rounded-full"></div>
            </div>
            <div class="flex gap-2 mt-4">
              <div class="skeleton h-10 w-32 rounded-lg"></div>
              <div class="skeleton h-10 w-24 rounded-lg"></div>
            </div>
          </div>
        </div>
      </div>`;
  }
  return html;
}

// --- Initialize ---
window.addEventListener('DOMContentLoaded', () => {
  console.log('LineUp Customer Platform initialized');
  
  testBackendConnection();
  setupEventListeners();
  renderBottomNav();
  
  // Render initial data (appointments loaded from API when available)
  renderClientAppointments();
});

// --- Setup Event Listeners ---
function setupEventListeners() {
  // Image upload
  imageUploadArea.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', handleImageUpload);
  
  // Analysis
  analyzeButton.addEventListener('click', analyzeImage);
  tryAgainButton.addEventListener('click', resetUI);
  startOverButton.addEventListener('click', resetUI);
  findBarberButton.addEventListener('click', findMatchingBarbers);
  
  // Barber search
  refreshBarbersBtn.addEventListener('click', () => {
    const location = locationSearch.value || 'Atlanta, GA';
    loadNearbyBarbers(location, lastRecommendedStyles);
  });
  
  setupLocationSearch();
  
  // Appointment booking
  const cancelBookingBtn = document.getElementById('cancel-booking');
  const confirmBookingBtn = document.getElementById('confirm-booking');
  if (cancelBookingBtn) cancelBookingBtn.addEventListener('click', closeBookingModal);
  if (confirmBookingBtn) confirmBookingBtn.addEventListener('click', confirmBooking);
  
  // Close modals on outside click
  [bookAppointmentModal].forEach(modal => {
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.add('hidden');
        }
      });
    }
  });
  
  // Zipcode modal handlers
  const zipcodeModal = document.getElementById('zipcode-modal');
  if (document.getElementById('confirm-zipcode')) {
    document.getElementById('confirm-zipcode').addEventListener('click', confirmZipcodeSearch);
  }
  if (document.getElementById('cancel-zipcode')) {
    document.getElementById('cancel-zipcode').addEventListener('click', cancelZipcodeSearch);
  }
  // Allow Enter key to confirm
  if (document.getElementById('zipcode-input')) {
    document.getElementById('zipcode-input').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        confirmZipcodeSearch();
      }
    });
  }
  // Close modal on outside click
  if (zipcodeModal) {
    zipcodeModal.addEventListener('click', (e) => {
      if (e.target === zipcodeModal) {
        cancelZipcodeSearch();
      }
    });
  }

  // Drag-and-drop on upload area
  if (imageUploadArea) {
    imageUploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      imageUploadArea.classList.add('drag-over');
    });
    imageUploadArea.addEventListener('dragleave', () => {
      imageUploadArea.classList.remove('drag-over');
    });
    imageUploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      imageUploadArea.classList.remove('drag-over');
      const file = e.dataTransfer.files[0];
      if (file) {
        // Validate then process
        const fakeEvent = { target: { files: [file] } };
        handleImageUpload(fakeEvent);
      }
    });
  }

  // Escape key closes modals
  const zipcodeModalEl = document.getElementById('zipcode-modal');
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      [bookAppointmentModal, zipcodeModalEl].forEach(modal => {
        if (modal && !modal.classList.contains('hidden')) {
          modal.classList.add('hidden');
        }
      });
    }
  });
}

// --- Tab Switching ---
function switchTab(targetTab) {
  console.log('Switching to tab:', targetTab);
  
  // Update tab button active state
  document.querySelectorAll(`#bottom-nav .tab-button`).forEach(t => {
    t.classList.remove('tab-active', 'text-white', 'font-semibold');
    t.classList.add('text-gray-500');
  });
  
  const activeTab = document.querySelector(`#bottom-nav [data-tab="${targetTab}"]`);
  if (activeTab) {
    activeTab.classList.add('tab-active', 'text-white', 'font-semibold');
    activeTab.classList.remove('text-gray-500');
  }
  
  // Hide all tab content
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  
  // Show target content
  const targetContent = document.getElementById(targetTab + '-tab-content');
  if (targetContent) {
    targetContent.classList.remove('hidden');
  }

  // Refresh data when switching to certain tabs
  if (targetTab === 'profile') {
    renderClientProfile();
  }
}

// --- Backend Connection ---
async function testBackendConnection() {
  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();
    console.log('✅ Backend connected:', data);
  } catch (err) {
    console.log('⚠️ Backend may be sleeping. Using mock data.');
  }
}

// --- Image Upload and Analysis ---
function handleImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  // Validate file type
  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    showToast('Please upload a JPEG, PNG, or WebP image.', 'error');
    return;
  }

  // Validate file size (5MB max)
  const maxSizeMB = 5;
  if (file.size > maxSizeMB * 1024 * 1024) {
    showToast(`Image too large. Maximum size is ${maxSizeMB}MB.`, 'error');
    return;
  }
  
  const reader = new FileReader();
  reader.onload = e => {
    const img = new Image();
    img.onload = function() {
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
      base64ImageData = resizedDataUrl.split(',')[1];
      imagePreview.src = resizedDataUrl;
      imageUploadArea.classList.add('hidden');
      imagePreviewContainer.classList.remove('hidden');
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function resetUI() {
  uploadSection.classList.remove('hidden');
  statusSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  errorContainer.classList.add('hidden');
  loader.classList.add('hidden');
  imageUploadArea.classList.remove('hidden');
  imagePreviewContainer.classList.add('hidden');
  imagePreview.src = '';
  fileInput.value = '';
  base64ImageData = null;
  lastRecommendedStyles = [];
}

async function analyzeImage() {
  if (!base64ImageData) { 
    showError("Please upload a photo."); 
    return; 
  }

  console.log('Starting analysis...');
  uploadSection.classList.add('hidden');
  statusSection.classList.remove('hidden');
  loader.classList.remove('hidden');
  statusMessage.textContent = "Analyzing your photo...";
  errorContainer.classList.add('hidden');

  try {
    const payload = {
      payload: {
        contents: [
          { 
            parts: [
              { text: "Analyze this person and provide face, hair info and 6 haircut recommendations." },
              { inlineData: { mimeType: "image/jpeg", data: base64ImageData } }
            ]
          }
        ]
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
      throw new Error(`Server error: ${response.status}`);
    }

    const result = await response.json();
    displayResults(result);

  } catch (err) {
    console.error('Analysis error:', err);
    showError(err.message || 'Analysis failed. Please try again.');
  } finally {
    loader.classList.add('hidden');
    statusMessage.textContent = '';
  }
}

function showError(msg) {
  loader.classList.add('hidden');
  statusMessage.textContent = '';
  errorContainer.classList.remove('hidden');
  errorMessage.textContent = msg;
}

function displayResults(data) {
  statusSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');

  const capitalizeWords = (str) => {
    if (!str || str === 'Unknown') return str;
    return str.split(' ').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
    ).join(' ');
  };

  // Analysis Grid
  analysisGrid.innerHTML = '';
  const analysisData = [
    { label: 'Face Shape', value: capitalizeWords(data.analysis.faceShape) || 'Unknown' },
    { label: 'Hair Texture', value: capitalizeWords(data.analysis.hairTexture) || 'Unknown' },
    { label: 'Hair Color', value: capitalizeWords(data.analysis.hairColor) || 'Unknown' },
    { label: 'Gender', value: capitalizeWords(data.analysis.estimatedGender) || 'Unknown' },
    { label: 'Est. Age', value: data.analysis.estimatedAge || 'Unknown' }
  ];
  
  analysisData.forEach((item, i) => {
    const div = document.createElement('div');
    div.className = 'bg-gradient-to-br from-gray-800 to-gray-900 p-5 rounded-xl border border-gray-700 hover:border-sky-500/50 transition-all duration-300 fade-in-up';
    div.style.animationDelay = `${i * 80}ms`;
    div.innerHTML = `
      <div class="flex items-center gap-2 mb-2">
        <div class="w-2 h-2 bg-sky-400 rounded-full"></div>
        <p class="text-sm font-medium text-gray-300">${item.label}</p>
      </div>
      <p class="font-bold text-xl text-white">${item.value}</p>
    `;
    analysisGrid.appendChild(div);
  });

  // Recommendations
  recommendationsContainer.innerHTML = '';
  const recommendations = data.recommendations || [];
  lastRecommendedStyles = recommendations.slice(0, 6).map(r => r.styleName);
  
  const colors = [
    { topBorder: 'border-t-4 border-t-sky-400', text: 'text-sky-400' },
    { topBorder: 'border-t-4 border-t-purple-400', text: 'text-purple-400' },
    { topBorder: 'border-t-4 border-t-green-400', text: 'text-green-400' },
    { topBorder: 'border-t-4 border-t-orange-400', text: 'text-orange-400' },
    { topBorder: 'border-t-4 border-t-pink-400', text: 'text-pink-400' },
    { topBorder: 'border-t-4 border-t-yellow-400', text: 'text-yellow-400' }
  ];
  
  recommendations.slice(0, 6).forEach((rec, index) => {
    const color = colors[index % colors.length];
    const card = document.createElement('div');
    card.className = `card-hover bg-gray-900 border border-gray-800 ${color.topBorder} rounded-lg p-5 fade-in-up`;
    card.style.animationDelay = `${(index * 100) + 400}ms`; // stagger after analysis grid
    
    card.innerHTML = `
      <div class="mb-4">
        <h3 class="text-lg font-semibold mb-1 text-white">${rec.styleName || 'Unnamed Style'}</h3>
        <p class="text-gray-400 text-sm line-clamp-2">${rec.description || 'Professional haircut recommendation'}</p>
        ${rec.reason ? `<p class="text-gray-500 text-xs mt-2 italic">${rec.reason}</p>` : ''}
      </div>
      
      <div class="space-y-2">
        <button onclick="tryOnStyle('${rec.styleName}')" 
                class="w-full btn-primary px-4 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
          Try On
        </button>
        
        <button onclick="findBarbersForStyle('${rec.styleName}')" 
                class="w-full btn-secondary px-4 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2">
          <svg class="w-4 h-4 ${color.text}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
          Find barbers
        </button>
      </div>
    `;
    recommendationsContainer.appendChild(card);
  });
}

// --- Barber Search ---
async function loadNearbyBarbers(location = 'Atlanta, GA', recommendedStyles = []) {
  console.log('Loading barbershops for:', location);
  
  if (barberListContainer) {
    barberListContainer.innerHTML = createBarberSkeleton(3);
  }
  if (barberIntro) barberIntro.textContent = 'Searching for barbershops near you...';
  
  try {
    const stylesParam = recommendedStyles.length > 0 ? `&styles=${encodeURIComponent(recommendedStyles.join(','))}` : '';
    const response = await fetch(`${API_URL}/barbers?location=${encodeURIComponent(location)}${stylesParam}`);
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || data.message || 'Failed to load barbershops');
    }
    if (data.barbers && data.barbers.length > 0) {
      renderBarberList(data.barbers, data.real_data);
    } else {
      throw new Error('No barbershops found');
    }
  } catch (error) {
    console.error('Error loading barbershops:', error);
    if (barberListContainer) {
      barberListContainer.innerHTML = `
        <div class="bg-red-900/20 border border-red-500/50 rounded-lg p-4 text-center">
          <p class="text-red-400">Could not load barbershops. Please check your location and try again.</p>
          <button onclick="loadNearbyBarbers(document.getElementById('location-search')?.value || 'Atlanta, GA', lastRecommendedStyles)" class="mt-3 btn-secondary py-2 px-4 rounded-lg text-sm">Retry</button>
        </div>
      `;
    }
  }
}

function renderBarberList(barbers, isRealData = false) {
  if (!barberListContainer) return;
  
  // Store barbers globally for booking URL access
  nearbyBarbers = barbers;
  
  const dataSourceBadge = isRealData ? 
    '<span class="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-xs">✓ Real Barbershops</span>' : '';
  
  barberListContainer.innerHTML = `
    <div class="mb-6 p-4 bg-gray-800/50 rounded-xl border border-gray-700">
      <div class="flex justify-between items-center mb-2">
        <p class="text-lg font-semibold text-white">Found ${barbers.length} barbershops</p>
        ${dataSourceBadge}
      </div>
      <p class="text-sm text-gray-400">These barbers specialize in the styles you're looking for</p>
    </div>
  `;
  
  barbers.forEach(barber => {
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden mb-4 hover:border-sky-500/50 transition-all';
    
    const ratingText = barber.user_ratings_total ? 
      `${barber.rating} ★ (${barber.user_ratings_total} reviews)` :
      `${barber.rating} ★`;
    
    card.innerHTML = `
      <div class="flex flex-col sm:flex-row">
        ${barber.photo ? 
          `<img src="${barber.photo}" alt="${barber.name}" class="w-full sm:w-48 h-48 sm:h-auto object-cover" onerror="this.src='https://placehold.co/400x300/1a1a1a/38bdf8?text=Barbershop'">` :
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
          </div>
          
          <div class="flex items-center gap-4 mb-3">
            <span class="text-yellow-400 flex items-center gap-1">${ratingText}</span>
            ${barber.priceTier ? `<span class="text-green-400 font-semibold">${barber.priceTier}</span>` : ''}
            <span class="text-gray-400 text-sm">${barber.phone}</span>
          </div>
          
          <div class="flex flex-wrap gap-2 mb-3">
            ${(barber.specialties || []).map(s => 
              `<span class="bg-sky-500/20 border border-sky-500/50 text-sky-300 text-xs px-3 py-1 rounded-full">${s}</span>`
            ).join('')}
          </div>
          
          ${barber.match_evidence && barber.match_evidence.length > 0 ? `
            <div class="bg-gray-800/50 border border-gray-700 rounded-lg p-3 mb-3">
              <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Why this barber</p>
              ${barber.match_evidence.map(e => `<p class="text-sm text-gray-300 italic">"${e}"</p>`).join('')}
            </div>
          ` : ''}
          
          <div class="flex flex-wrap gap-3">
          <button onclick="openBookingModal('${barber.id}', '${barber.name.replace(/'/g, "\\'")}')" 
                    class="bg-green-500 text-white px-6 py-2 rounded-lg hover:bg-green-600 transition-colors font-medium">
            Book Appointment
          </button>
            <button onclick="showBarberReviews('${barber.id}')" 
                    class="bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-600 transition-colors font-medium flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path>
              </svg>
              Reviews
          </button>
          ${barber.google_maps_url ? `
            <a href="${barber.google_maps_url}" target="_blank" rel="noopener noreferrer"
               class="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors font-medium flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path>
              </svg>
              Location
            </a>
          ` : ''}
          ${barber.website ? `
            <a href="${barber.website}" target="_blank" rel="noopener noreferrer"
               class="bg-sky-500 text-white px-4 py-2 rounded-lg hover:bg-sky-600 transition-colors font-medium flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path>
              </svg>
              Website
            </a>
          ` : ''}
          </div>
        </div>
      </div>
    `;
    barberListContainer.appendChild(card);
  });
}

function findMatchingBarbers() {
  const location = locationSearch.value || 'Atlanta, GA';
  
  if (barberIntro) {
    barberIntro.innerHTML = `
      <span class="text-gray-300">Finding real barbershops in</span> 
      <span class="text-sky-400 font-semibold">${location}</span>
      <span class="text-gray-300">that specialize in your recommended styles...</span>
    `;
  }
  
  loadNearbyBarbers(location, lastRecommendedStyles);
  switchTab('barbers');
}

function findBarbersForStyle(styleName) {
  // Store the style name for the confirm button
  window.currentSearchStyle = styleName;
  
  // Get modal elements
  const zipcodeModal = document.getElementById('zipcode-modal');
  const zipcodeInput = document.getElementById('zipcode-input');
  const zipcodeModalSubtitle = document.getElementById('zipcode-modal-subtitle');
  
  // Update modal subtitle with style name
  if (zipcodeModalSubtitle) {
    zipcodeModalSubtitle.textContent = `Enter your ZIP code or city to find barbers specializing in ${styleName}.`;
  }
  
  // Clear input and show modal
  if (zipcodeInput) {
    zipcodeInput.value = '';
    zipcodeInput.focus();
  }
  if (zipcodeModal) {
    zipcodeModal.classList.remove('hidden');
  }
}

// Add function to handle zipcode confirmation
function confirmZipcodeSearch() {
  const zipcodeModal = document.getElementById('zipcode-modal');
  const zipcodeInput = document.getElementById('zipcode-input');
  const styleName = window.currentSearchStyle;
  const barberIntro = document.getElementById('barber-intro');
  
  if (!zipcodeInput || !styleName) return;
  
  const location = zipcodeInput.value.trim();
  
  const zipcodeError = document.getElementById('zipcode-error');
  if (!location) {
    // Show inline validation error
    if (zipcodeError) zipcodeError.classList.remove('hidden');
    if (zipcodeInput) zipcodeInput.classList.add('border-red-500');
    return;
  }
  // Clear error if present
  if (zipcodeError) zipcodeError.classList.add('hidden');
  if (zipcodeInput) zipcodeInput.classList.remove('border-red-500');
  
  // Hide modal
  if (zipcodeModal) {
    zipcodeModal.classList.add('hidden');
  }
  
  // Update UI message
  if (barberIntro) {
    barberIntro.innerHTML = `
      <div class="text-center mb-4">
        <span class="inline-block bg-sky-500/20 border border-sky-500/50 text-sky-300 text-sm px-4 py-2 rounded-full mb-2">
          Searching for: ${styleName}
        </span>
        <br>
        <span class="text-gray-300">Finding real barbershops in</span> 
        <span class="text-sky-400 font-semibold">${location}</span>
        <span class="text-gray-300">that specialize in this style...</span>
      </div>
    `;
  }
  
  // Switch to barbers tab first
  switchTab('barbers');
  
  // Then load barbers with the entered location
  loadNearbyBarbers(location, [styleName]);
  
  // Clear stored style
  window.currentSearchStyle = null;
}

// Add function to cancel zipcode search
function cancelZipcodeSearch() {
  const zipcodeModal = document.getElementById('zipcode-modal');
  if (zipcodeModal) {
    zipcodeModal.classList.add('hidden');
  }
  window.currentSearchStyle = null;
}

let searchTimeout;
function setupLocationSearch() {
  if (locationSearch) {
    locationSearch.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      const value = e.target.value.trim();
      
      if (value.length > 2) {
        searchTimeout = setTimeout(() => {
          loadNearbyBarbers(value, lastRecommendedStyles);
        }, 500);
      }
    });
    
    locationSearch.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        clearTimeout(searchTimeout);
        const value = e.target.value.trim();
        if (value) {
          loadNearbyBarbers(value, lastRecommendedStyles);
        }
      }
    });
  }
}

// --- Bottom Nav Rendering ---
function renderBottomNav() {
  if (!bottomNav) return;

  const baseBtn = 'tab-button flex flex-col items-center justify-center h-14 flex-1 text-xs transition-all duration-200';

  const icons = {
    home: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>',
    explore: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>',
    calendar: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>',
    community: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>',
    profile: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>',
    scissors: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z"></path></svg>',
    shop: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>'
  };

  const tabs = [
    { key: 'ai', label: 'Home', icon: icons.home },
    { key: 'barbers', label: 'Explore', icon: icons.explore },
    { key: 'appointments', label: 'Book', icon: icons.calendar },
    { key: 'profile', label: 'Profile', icon: icons.profile }
  ];

  bottomNav.innerHTML = `
    <div class="flex items-center justify-between px-4 py-1">
      ${tabs.map((t) => `
        <button class="${baseBtn} text-gray-500 hover:text-white" data-tab="${t.key}">
          ${t.icon}
          <span class="mt-1 text-[11px]">${t.label}</span>
        </button>
      `).join('')}
    </div>
  `;

  bottomNav.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  switchTab('ai');
}

// --- Client Profile Rendering ---
function renderClientProfile() {
  const historyEl = document.getElementById('client-profile-history');
  if (historyEl) {
    const history = appointments.filter(apt => apt.clientId === 'current-user');
    if (history.length === 0) {
      historyEl.innerHTML = '<p class="text-gray-500">No past bookings yet.</p>';
    } else {
      historyEl.innerHTML = history.map(apt => `
        <div class="bg-gray-800/60 border border-gray-700 rounded-xl p-3 flex items-center justify-between">
          <div>
            <p class="font-semibold text-white">${apt.barberName}</p>
            <p class="text-sm text-gray-400">${apt.service}</p>
          </div>
          <div class="text-right text-sm text-gray-300">
            <p>${new Date(apt.date).toLocaleDateString()} • ${apt.time}</p>
            <p class="text-gray-400">${apt.price}</p>
          </div>
        </div>
      `).join('');
    }
  }

  const refreshBtn = document.getElementById('refresh-history');
  if (refreshBtn) {
    refreshBtn.onclick = () => renderClientProfile();
  }
}

// --- Appointment Functions ---
async function openBookingModal(barberId, barberName) {
  // Find the barber in the current list to get booking URL
  const barber = nearbyBarbers.find(b => b.id === barberId);
  
  console.log('Opening booking for barber:', barberId, barber);
  console.log('Booking URL:', barber?.bookingUrl);
  
  // Check if barber has an external booking URL
  if (barber && (barber.bookingUrl || barber.booking_url)) {
    const bookingUrl = barber.bookingUrl || barber.booking_url;
    console.log('Redirecting to booking URL:', bookingUrl);
    // Redirect to external booking site
    window.open(bookingUrl, '_blank', 'noopener,noreferrer');
    return;
  }
  
  // Fallback to modal if no booking URL
  console.log('No booking URL found, opening modal');
  currentBarberForBooking = { id: barberId, name: barberName };
  
  document.getElementById('booking-barber-info').innerHTML = `
    <p class="text-lg font-semibold text-white">Booking with ${barberName}</p>
    <p class="text-sm text-gray-400">Select your preferred date and time</p>
  `;
  
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('appointment-date').min = today;
  
  bookAppointmentModal.classList.remove('hidden');
}

function closeBookingModal() {
  bookAppointmentModal.classList.add('hidden');
  document.getElementById('appointment-date').value = '';
  document.getElementById('appointment-time').value = '';
  document.getElementById('appointment-service').value = '';
  document.getElementById('appointment-notes').value = '';
}

function confirmBooking() {
  const date = document.getElementById('appointment-date').value;
  const time = document.getElementById('appointment-time').value;
  const service = document.getElementById('appointment-service').value;
  const notes = document.getElementById('appointment-notes').value;
  
  if (!date || !time || !service) {
    showToast('Please fill in all required fields.', 'error');
    return;
  }
  
  const serviceMap = {
    'haircut': 'Haircut ($45)',
    'haircut-beard': 'Haircut + Beard ($65)',
    'beard-only': 'Beard Trim ($25)'
  };
  
  const priceMap = {
    'haircut': '$45',
    'haircut-beard': '$65', 
    'beard-only': '$25'
  };
  
  const newAppointment = {
    id: Date.now(),
    clientName: 'Current User',
    clientId: 'current-user',
    barberName: currentBarberForBooking.name,
    barberId: currentBarberForBooking.id,
    date: date,
    time: time,
    service: serviceMap[service],
    price: priceMap[service],
    notes: notes || 'No special requests',
    status: 'pending'
  };
  
  appointments.push(newAppointment);
  renderClientAppointments();
  closeBookingModal();
  
  showToast('Appointment booked successfully!', 'success');
  switchTab('appointments');
}

function renderClientAppointments() {
  const clientAppointments = appointments.filter(apt => apt.clientId === 'current-user');
  
  if (!clientAppointmentsContainer) return;
  
  if (clientAppointments.length === 0) {
    noAppointments.classList.remove('hidden');
    clientAppointmentsContainer.innerHTML = '';
    return;
  }
  
  noAppointments.classList.add('hidden');
  clientAppointmentsContainer.innerHTML = '';
  
  clientAppointments.forEach(appointment => {
    const appointmentElement = document.createElement('div');
    appointmentElement.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl p-5';
    appointmentElement.innerHTML = `
      <div class="flex justify-between items-start mb-3">
        <div>
          <h3 class="text-lg font-bold text-white">${appointment.barberName}</h3>
          <p class="text-gray-400">${appointment.service}</p>
        </div>
        <span class="px-3 py-1 rounded-full text-xs font-semibold ${
          appointment.status === 'confirmed' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'
        }">
          ${appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
        </span>
      </div>
      <div class="grid grid-cols-2 gap-4 text-sm">
        <p class="text-gray-300"><span class="text-gray-400">Date:</span> ${new Date(appointment.date).toLocaleDateString()}</p>
        <p class="text-gray-300"><span class="text-gray-400">Time:</span> ${appointment.time}</p>
        <p class="text-gray-300"><span class="text-gray-400">Price:</span> ${appointment.price}</p>
        <p class="text-gray-300"><span class="text-gray-400">Status:</span> ${appointment.status}</p>
      </div>
      ${appointment.notes !== 'No special requests' ? `<p class="text-gray-400 text-sm mt-3">Notes: ${appointment.notes}</p>` : ''}
    `;
    clientAppointmentsContainer.appendChild(appointmentElement);
  });
}

// NOTE: Barber-specific functions removed for customer-only branch

// --- Virtual Try-On Implementation ---
async function tryOnStyle(styleName) {
  // Check if user has uploaded a photo
  if (!base64ImageData) {
    showToast('Upload a photo first, then try on styles.', 'info');
    switchTab('ai');
    return;
  }

  // Find the recommendation card that triggered this and add processing overlay
  const originalButton = event?.target;
  let cardEl = originalButton?.closest('.card-hover');
  let processingOverlay = null;
  
  if (originalButton) {
    originalButton.disabled = true;
    originalButton.innerHTML = '<div class="loader" style="width:16px;height:16px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px"></div> Processing...';
  }

  // Show processing overlay on the card
  if (cardEl) {
    processingOverlay = document.createElement('div');
    processingOverlay.className = 'tryon-processing';
    processingOverlay.innerHTML = `
      <div class="progress-ring mb-3"></div>
      <p class="text-white text-sm font-medium">Applying "${styleName}"...</p>
      <p class="text-gray-400 text-xs mt-1">This may take 10-30 seconds</p>
    `;
    cardEl.style.position = 'relative';
    cardEl.appendChild(processingOverlay);
  }

  try {
    const response = await fetch(`${API_URL}/virtual-tryon`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userPhoto: base64ImageData,
        styleDescription: styleName
      })
    });

    const result = await response.json();

    if (response.ok && result.success) {
      const originalImg = result.originalImage || base64ImageData;
      displayTryOnResult(originalImg, result.resultImage, styleName, result.poweredBy);
      showToast(`Try-on complete: ${styleName}`, 'success');

      // Scroll to the result
      setTimeout(() => {
        const resultEl = document.getElementById('tryon-results-container');
        if (resultEl) resultEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 200);
    } else {
      throw new Error(result.error || 'Try-on failed');
    }
  } catch (error) {
    console.error('Try-on error:', error);
    showToast(`Try-on failed: ${error.message}`, 'error', 5000);
  } finally {
    if (originalButton) {
      originalButton.disabled = false;
      originalButton.textContent = 'Try On';
    }
    if (processingOverlay) processingOverlay.remove();
  }
}

function displayTryOnResult(originalImageBase64, resultImageBase64, styleName, poweredBy) {
  // Find or create results container
  let resultsContainer = document.getElementById('tryon-results-container');
  
  if (!resultsContainer) {
    // Create container if it doesn't exist
    resultsContainer = document.createElement('div');
    resultsContainer.id = 'tryon-results-container';
    resultsContainer.className = 'mt-8 bg-gray-900 border border-gray-800 rounded-lg p-6';
    
    // Add it after recommendations
    const recommendationsContainer = document.getElementById('recommendations-container');
    if (recommendationsContainer) {
      recommendationsContainer.insertAdjacentElement('afterend', resultsContainer);
    }
  }

  // Display before/after comparison
  resultsContainer.innerHTML = `
    <h3 class="text-2xl font-bold mb-4 text-white">✨ Your Try-On Result</h3>
    <div class="bg-gray-800 rounded-lg p-4">
      <p class="text-gray-300 mb-4 text-center">Style: <span class="text-sky-400 font-semibold">${styleName}</span></p>
      
      <!-- Before/After Comparison -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <!-- Before Image -->
        <div class="text-center">
          <p class="text-gray-400 text-sm font-semibold mb-2">Before</p>
          <div class="w-full aspect-square rounded-lg shadow-lg border-2 border-gray-600 overflow-hidden bg-gray-700 flex items-center justify-center">
            <img src="data:image/jpeg;base64,${originalImageBase64}" 
                 alt="Before" 
                 class="w-full h-full object-contain rounded-lg">
          </div>
        </div>
        
        <!-- After Image -->
        <div class="text-center">
          <p class="text-gray-400 text-sm font-semibold mb-2">After</p>
          <div class="w-full aspect-square rounded-lg shadow-lg border-2 border-sky-500 overflow-hidden bg-gray-700 flex items-center justify-center">
            <img src="data:image/jpeg;base64,${resultImageBase64}" 
                 alt="After" 
                 class="w-full h-full object-contain rounded-lg">
          </div>
        </div>
      </div>
      
      <p class="text-gray-400 text-sm text-center mb-4">${poweredBy || 'Preview Mode'}</p>
      
      <div class="flex gap-3 mt-4">
        <button onclick="document.getElementById('tryon-results-container').remove()" 
                class="flex-1 bg-gray-700 text-white py-2 px-4 rounded-lg hover:bg-gray-600 transition-colors">
          Close
        </button>
        <button onclick="downloadTryOnImage('${resultImageBase64}', '${styleName}')" 
                class="flex-1 bg-sky-500 text-white py-2 px-4 rounded-lg hover:bg-sky-600 transition-colors">
          Download After Image
        </button>
      </div>
    </div>
  `;

  // Scroll to results
  resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function downloadTryOnImage(base64Data, styleName) {
  const link = document.createElement('a');
  link.href = `data:image/jpeg;base64,${base64Data}`;
  link.download = `lineup-tryon-${styleName.replace(/\s+/g, '-').toLowerCase()}.jpg`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}


// Load barber reviews
async function loadBarberReviews(barberId) {
  try {
    const response = await fetch(`${API_URL}/barbers/${barberId}/reviews`);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error loading reviews:', error);
    return null;
  }
}

// Show barber reviews in a modal
async function showBarberReviews(barberId) {
  console.log('Loading reviews for barber:', barberId);
  
  // Show loading state
  const loadingModal = document.createElement('div');
  loadingModal.className = 'fixed inset-0 bg-black/70 flex items-center justify-center z-50';
  loadingModal.innerHTML = `
    <div class="bg-gray-900 border border-gray-700 rounded-2xl p-6">
      <div class="flex items-center gap-3">
        <div class="loader"></div>
        <p class="text-white">Loading reviews...</p>
      </div>
    </div>
  `;
  document.body.appendChild(loadingModal);
  
  const reviewsData = await loadBarberReviews(barberId);
  loadingModal.remove();
  
  console.log('Reviews data received:', reviewsData);
  
  if (!reviewsData) {
    showToast('Failed to load reviews.', 'error');
    return;
  }
  
  const reviews = reviewsData.reviews || [];
  const avgRating = reviewsData.average_rating || 0;
  const totalReviews = reviewsData.total_reviews || 0;
  
  console.log(`Found ${reviews.length} reviews, avg rating: ${avgRating}, total: ${totalReviews}`);
  
  const modalHtml = `
    <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 modal">
      <div class="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-2xl font-bold text-white">Reviews & Ratings</h2>
          <button onclick="this.closest('.modal').remove()" class="text-gray-400 hover:text-white">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>
        
        <div class="bg-gray-800/50 rounded-xl p-4 mb-4">
          <div class="flex items-center gap-3">
            <div class="text-4xl font-bold text-yellow-400">${avgRating.toFixed(1)}</div>
            <div>
              <div class="flex items-center gap-1 mb-1">
                ${Array(5).fill(0).map((_, i) => `
                  <span class="text-${i < Math.round(avgRating) ? 'yellow' : 'gray'}-400">⭐</span>
                `).join('')}
              </div>
              <p class="text-gray-400 text-sm">Based on ${totalReviews} reviews</p>
            </div>
          </div>
        </div>
        
        ${reviews.length > 0 ? `
        <div class="space-y-4">
          ${reviews.map(review => `
            <div class="bg-gray-800/30 rounded-xl p-4 border border-gray-700">
              <div class="flex items-start justify-between mb-2">
                <div class="flex items-center gap-3 flex-1">
                  ${review.profile_photo ? `
                    <img src="${review.profile_photo}" alt="${review.username}" class="w-10 h-10 rounded-full">
                  ` : `
                    <div class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center text-white font-semibold">
                      ${(review.username || 'A').charAt(0).toUpperCase()}
                    </div>
                  `}
                  <div class="flex-1">
                    <p class="font-semibold text-white">${review.username || 'Anonymous'}</p>
                    <p class="text-gray-400 text-sm">${review.relative_time || review.date || 'Recent'}</p>
                  </div>
                </div>
                <div class="flex gap-1">
                  ${Array(5).fill(0).map((_, i) => `
                    <span class="text-${i < (review.rating || 5) ? 'yellow' : 'gray'}-400">⭐</span>
                  `).join('')}
                </div>
              </div>
              <p class="text-gray-300 mt-2">${review.text || 'No review text available'}</p>
            </div>
          `).join('')}
        </div>
        ` : `
        <div class="text-center py-10 text-gray-400">
          <p>No reviews available yet.</p>
          ${reviewsData.source === 'google' ? '<p class="text-sm mt-2">Google Reviews will appear here when available.</p>' : ''}
        </div>
        `}
        
        <div class="mt-6 pt-4 border-t border-gray-700">
          <button onclick="this.closest('.modal').remove()" class="w-full bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-medium">
            Close
          </button>
        </div>
      </div>
    </div>
  `;
  
  document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Call loadAIInsights after analysis is done
const originalAnalyzeComplete = () => {}; // We'll override this

// --- Make functions globally available ---
window.switchTab = switchTab;
window.openBookingModal = openBookingModal;
window.findBarbersForStyle = findBarbersForStyle;
window.confirmZipcodeSearch = confirmZipcodeSearch;
window.cancelZipcodeSearch = cancelZipcodeSearch;
window.tryOnStyle = tryOnStyle;
window.downloadTryOnImage = downloadTryOnImage;
window.showBarberReviews = showBarberReviews;

