// scripts-updated.js - Frontend JavaScript for LineUp Two-Sided Platform

// --- Configuration ---
const API_URL = 'https://lineup-fjpn.onrender.com'; // Keep for Gemini AI analysis
let GOOGLE_PLACES_API_KEY = null;

// Firebase Service (will be loaded from firebase-simple.js)
let firebaseService = null;

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

// Role switching
const clientModeBtn = document.getElementById('client-mode');
const barberModeBtn = document.getElementById('barber-mode');
const clientContent = document.getElementById('client-content');
const barberContent = document.getElementById('barber-content');
// Bottom nav is rendered dynamically into #bottom-nav

// Social / Community elements
const socialFeedContainer = document.getElementById('social-feed-container');
const addPostButton = document.getElementById('add-post-button');
const addPostModal = document.getElementById('add-post-modal');
const postImageArea = document.getElementById('post-image-area');
const postImageInput = document.getElementById('post-image-input');
const postImagePreview = document.getElementById('post-image-preview');
const postCaption = document.getElementById('post-caption');
const cancelPost = document.getElementById('cancel-post');
const submitPost = document.getElementById('submit-post');

// Barber elements
const portfolioGrid = document.getElementById('barber-portfolio-grid');
const uploadWorkButton = document.getElementById('upload-work-button');
const uploadWorkModal = document.getElementById('upload-work-modal');
const workImageArea = document.getElementById('work-image-area');
const workImageInput = document.getElementById('work-image-input');
const workImagePreview = document.getElementById('work-image-preview');
const workStyleName = document.getElementById('work-style-name');
const workDescription = document.getElementById('work-description');
const cancelWork = document.getElementById('cancel-work');
const submitWork = document.getElementById('submit-work');

// Appointment elements
const bookAppointmentModal = document.getElementById('book-appointment-modal');
const clientAppointmentsContainer = document.getElementById('client-appointments-container');
const barberAppointmentsContainer = document.getElementById('barber-appointments-container');
const noAppointments = document.getElementById('no-appointments');

// --- State ---
let base64ImageData = null;
let lastRecommendedStyles = [];
let currentUserMode = 'client';
let socialPosts = [];
let barberPortfolio = [];
let appointments = [];
let currentBarberForBooking = null;
let subscriptionPackages = [];
let clientSubscriptions = [];

// --- Mock Data ---
const mockSocialPosts = [
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
  },
  {
    id: 3,
    username: 'jason_cuts',
    avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop&crop=face',
    image: 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=400&h=400&fit=crop',
    caption: 'Classic taper fade. Clean and professional 💼',
    likes: 67,
    timeAgo: '1d',
    liked: false
  }
];

const mockBarberPortfolio = [
  {
    id: 1,
    styleName: 'Modern Fade',
    image: 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop',
    description: 'Clean fade with textured top. Perfect for professionals.',
    likes: 12,
    date: '2024-01-15'
  },
  {
    id: 2,
    styleName: 'Classic Pompadour',
    image: 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=400&h=400&fit=crop',
    description: 'Vintage-inspired pompadour with modern styling.',
    likes: 18,
    date: '2024-01-14'
  }
];

const mockAppointments = [
  {
    id: 1,
    clientName: 'Alex Johnson',
    barberName: 'Mike\'s Cuts',
    date: '2024-01-20',
    time: '14:00',
    service: 'Haircut + Beard',
    price: '$65',
    status: 'confirmed',
    notes: 'Looking for a modern fade'
  },
  {
    id: 2,
    clientName: 'Current User',
    barberName: 'Style Studio',
    date: '2024-01-22',
    time: '10:00',
    service: 'Haircut',
    price: '$45',
    status: 'pending',
    notes: 'First time visit'
  }
];

// --- Style Example Images ---
// Maps normalized style names to representative example photos
const STYLE_IMAGE_MAP = {
  'classic fade': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=1200&auto=format&fit=crop&q=80',
  'textured quiff': 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=1200&auto=format&fit=crop&q=80',
  'side part': 'https://images.unsplash.com/photo-1519741497674-611481863552?w=1200&auto=format&fit=crop&q=80',
  'messy crop': 'https://images.unsplash.com/photo-1519741497674-611481863552?w=1200&auto=format&fit=crop&q=80',
  'buzz cut': 'https://images.unsplash.com/photo-1514790193030-c89d266d5a9d?w=1200&auto=format&fit=crop&q=80',
  // Generic fallbacks
  'pompadour': 'https://images.unsplash.com/photo-1621605815971-fbc98d665033?w=1200&auto=format&fit=crop&q=80',
  'fade': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=1200&auto=format&fit=crop&q=80',
  'taper': 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=1200&auto=format&fit=crop&q=80'
};

function normalizeStyleName(name) {
  return (name || '').toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ').trim();
}

function getStyleImage(name) {
  const key = normalizeStyleName(name);
  return STYLE_IMAGE_MAP[key] || null;
}

// --- Initialize ---
window.addEventListener('DOMContentLoaded', async () => {
  console.log('LineUp Two-Sided Platform with Firebase initialized');
  
  // Wait for Firebase to be available
  setTimeout(async () => {
    firebaseService = window.firebaseService;
    
    if (firebaseService) {
      console.log('🔥 Firebase service connected');
      
      // Load real data from Firebase
      await loadSocialFeed();
      await loadBarberPortfolio();
      await loadAppointments();
      
      // Set up real-time listeners
      setupRealtimeListeners();
    } else {
      console.log('⚠️ Firebase not available, using mock data');
      // Fallback to mock data
      socialPosts = [...mockSocialPosts];
      barberPortfolio = [...mockBarberPortfolio];
      appointments = [...mockAppointments];
      
      renderSocialFeed();
      renderBarberPortfolio();
      renderClientAppointments();
      renderBarberAppointments();
    }
    
    loadNearbyBarbers('Atlanta, GA');
    testBackendConnection();
    setupEventListeners();
    renderBottomNav();
    updateDashboardStats();
    // Default to client Home
    switchMode('client');
  }, 1000); // Give Firebase time to load
});

// --- Setup Event Listeners ---
function setupEventListeners() {
  // Role switching
  clientModeBtn.addEventListener('click', () => switchMode('client'));
  barberModeBtn.addEventListener('click', () => switchMode('barber'));
  
  // Tabs are attached after rendering bottom nav dynamically

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
  
  // Setup location search
  setupLocationSearch();
  
  // Social modals
  addPostButton.addEventListener('click', () => addPostModal.classList.remove('hidden'));
  postImageArea.addEventListener('click', () => postImageInput.click());
  postImageInput.addEventListener('change', handlePostImageUpload);
  cancelPost.addEventListener('click', closeAddPostModal);
  submitPost.addEventListener('click', submitSocialPost);
  
  // Barber modals
  uploadWorkButton.addEventListener('click', () => uploadWorkModal.classList.remove('hidden'));
  document.getElementById('add-portfolio-btn').addEventListener('click', () => uploadWorkModal.classList.remove('hidden'));
  document.getElementById('view-schedule-btn').addEventListener('click', () => switchTab('barber-schedule'));
  workImageArea.addEventListener('click', () => workImageInput.click());
  workImageInput.addEventListener('change', handleWorkImageUpload);
  cancelWork.addEventListener('click', closeUploadWorkModal);
  submitWork.addEventListener('click', submitPortfolioWork);
  
  // Appointment booking
  document.getElementById('cancel-booking').addEventListener('click', closeBookingModal);
  document.getElementById('confirm-booking').addEventListener('click', confirmBooking);
  
  // Logo upload
  const logoInput = document.getElementById('logo-input');
  const logoPreviewContainer = document.getElementById('logo-preview-container');
  const logoPreview = document.getElementById('logo-preview');
  const logoPlaceholder = document.getElementById('logo-placeholder');
  const uploadLogoBtn = document.getElementById('upload-logo-btn');
  
  if (uploadLogoBtn && logoPreviewContainer && logoInput) {
    uploadLogoBtn.addEventListener('click', () => logoInput.click());
    logoPreviewContainer.addEventListener('click', () => logoInput.click());
    logoInput.addEventListener('change', handleLogoUpload);
  }
  
  // Subscription packages
  const createPackageBtn = document.getElementById('create-package-btn');
  const createPackageModal = document.getElementById('create-package-modal');
  const cancelPackage = document.getElementById('cancel-package');
  const submitPackage = document.getElementById('submit-package');
  
  if (createPackageBtn) {
    createPackageBtn.addEventListener('click', () => createPackageModal.classList.remove('hidden'));
  }
  if (cancelPackage) {
    cancelPackage.addEventListener('click', closeCreatePackageModal);
  }
  if (submitPackage) {
    submitPackage.addEventListener('click', handleCreatePackage);
  }
  
  // Close modals on outside click
  [addPostModal, uploadWorkModal, bookAppointmentModal, createPackageModal].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.add('hidden');
      }
    });
  });
}

// --- Mode Switching ---
function switchMode(mode) {
  currentUserMode = mode;
  
  if (mode === 'client') {
    clientModeBtn.classList.add('bg-white', 'text-black', 'shadow-sm');
    clientModeBtn.classList.remove('text-gray-400');
    barberModeBtn.classList.remove('bg-white', 'text-black', 'shadow-sm');
    barberModeBtn.classList.add('text-gray-400');
    
    clientContent.classList.remove('hidden');
    barberContent.classList.add('hidden');

    renderBottomNav();
    switchTab('ai');
  } else {
    barberModeBtn.classList.add('bg-white', 'text-black', 'shadow-sm');
    barberModeBtn.classList.remove('text-gray-400');
    clientModeBtn.classList.remove('bg-white', 'text-black', 'shadow-sm');
    clientModeBtn.classList.add('text-gray-400');
    
    barberContent.classList.remove('hidden');
    clientContent.classList.add('hidden');

    renderBottomNav();
    switchTab('barber-dashboard');
  }
}

// --- Tab Switching ---
function switchTab(targetTab) {
  console.log('Switching to tab:', targetTab);
  
  // Update tab button active state
  document.querySelectorAll(`#bottom-nav .tab-button`).forEach(t => {
    t.classList.remove('tab-active');
    t.classList.remove('text-white');
    t.classList.add('text-gray-500');
    // Keep center pill transform
    if (!t.classList.contains('center-pill')) {
      t.classList.remove('font-semibold');
    }
  });
  
  const activeTab = document.querySelector(`#bottom-nav [data-tab="${targetTab}"]`);
  if (activeTab) {
    activeTab.classList.add('tab-active');
    if (!activeTab.classList.contains('center-pill')) {
      activeTab.classList.add('text-white', 'font-semibold');
      activeTab.classList.remove('text-gray-500');
    }
  }
  
  // Hide all tab content
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  
  // Show target content
  const targetContent = document.getElementById(targetTab + '-tab-content');
  if (targetContent) {
    targetContent.classList.remove('hidden');
  }

  // If we navigated to profile in client mode, render it
  if (targetTab === 'profile') {
    renderClientProfile();
  }
  
  // If we navigated to barber profile, load subscription packages
  if (targetTab === 'barber-profile') {
    loadSubscriptionPackages();
  }
}

// --- Backend Connection ---
async function testBackendConnection() {
  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();
    console.log('✅ Backend connected:', data);
  } catch (err) {
    console.log('⚠️ Backend may be sleeping. Will wake up on first request.');
  }
}

// --- Image Upload and Analysis ---
function handleImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
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

// Logo upload handler
function handleLogoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = (e) => {
    const logoPreview = document.getElementById('logo-preview');
    const logoPlaceholder = document.getElementById('logo-placeholder');
    
    if (logoPreview && logoPlaceholder) {
      logoPreview.src = e.target.result;
      logoPreview.classList.remove('hidden');
      logoPlaceholder.classList.add('hidden');
    }
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
              { text: "Analyze this person and provide face, hair info and 5 haircut recommendations." },
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
    showError("Using demo results while our servers wake up...");
    setTimeout(() => {
      displayResults(getMockData());
    }, 2000);
  } finally {
    loader.classList.add('hidden');
    statusMessage.textContent = '';
  }
}

function getMockData() {
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
        styleName: "Classic Fade",
        description: "Short on the sides with a gradual fade, longer on top for versatility",
        reason: "Perfect for oval face shapes and professional settings"
      },
      {
        styleName: "Textured Quiff",
        description: "Modern style with volume at the front, swept upward and back",
        reason: "Takes advantage of wavy hair texture for natural volume"
      },
      {
        styleName: "Side Part",
        description: "Timeless look with a defined part, suitable for any occasion",
        reason: "Enhances facial symmetry and adds sophistication"
      },
      {
        styleName: "Messy Crop", 
        description: "Short, textured cut with a deliberately tousled finish",
        reason: "Low maintenance while maintaining style"
      },
      {
        styleName: "Buzz Cut",
        description: "Very short all over, clean and minimal",
        reason: "Highlights facial features with zero styling needed"
      },
      {
        styleName: "Undercut",
        description: "Dramatic contrast with shaved sides and longer top",
        reason: "Bold, edgy style that adds character and dimension"
      }
    ]
  };
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
  
  analysisData.forEach(item => {
    const div = document.createElement('div');
    div.className = 'bg-gradient-to-br from-gray-800 to-gray-900 p-5 rounded-xl border border-gray-700 hover:border-sky-500/50 transition-all duration-300';
    div.innerHTML = `
      <div class="flex items-center gap-2 mb-2">
        <div class="w-2 h-2 bg-sky-400 rounded-full"></div>
        <p class="text-sm font-medium text-gray-300">${item.label}</p>
      </div>
      <p class="font-bold text-xl text-white">${item.value}</p>
    `;
    analysisGrid.appendChild(div);
  });

  // Recommendations with colorful borders and drop shadows
  recommendationsContainer.innerHTML = '';
  const recommendations = data.recommendations || [];
  lastRecommendedStyles = recommendations.slice(0, 6).map(r => r.styleName);
  
  // Vibrant color scheme with borders and shadows
  const colors = [
    { border: 'border-sky-400', shadow: 'shadow-lg shadow-sky-500/50', text: 'text-sky-400' },
    { border: 'border-purple-400', shadow: 'shadow-lg shadow-purple-500/50', text: 'text-purple-400' },
    { border: 'border-green-400', shadow: 'shadow-lg shadow-green-500/50', text: 'text-green-400' },
    { border: 'border-orange-400', shadow: 'shadow-lg shadow-orange-500/50', text: 'text-orange-400' },
    { border: 'border-pink-400', shadow: 'shadow-lg shadow-pink-500/50', text: 'text-pink-400' },
    { border: 'border-yellow-400', shadow: 'shadow-lg shadow-yellow-500/50', text: 'text-yellow-400' }
  ];
  
  recommendations.slice(0, 6).forEach((rec, index) => {
    const color = colors[index % colors.length];
    const card = document.createElement('div');
    card.className = `card-hover bg-gray-900 border-2 ${color.border} ${color.shadow} rounded-lg p-5`;
    
    card.innerHTML = `
      <div class="mb-4">
        <h3 class="text-lg font-semibold mb-1 text-white">${rec.styleName || 'Unnamed Style'}</h3>
        <p class="text-gray-400 text-sm line-clamp-2">${rec.description || 'Professional haircut recommendation'}</p>
      </div>
      
      <div class="space-y-2">
        <button onclick="tryOnStyle('${rec.styleName}')" 
                class="w-full btn-primary px-4 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
          </svg>
          Try it on
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

// --- Barber Functions with Real Google Places ---
async function loadNearbyBarbers(location = 'Atlanta, GA', recommendedStyles = []) {
  console.log('Loading REAL barbershops for:', location);
  console.log('Recommended styles:', recommendedStyles);
  
  // Show loading state
  if (barberListContainer) {
    barberListContainer.innerHTML = '<div class="text-center py-8"><div class="loader mx-auto"></div><p class="mt-4 text-gray-400">Finding real barbershops near you...</p></div>';
  }
  
  try {
    // Include recommended styles in the request
    const stylesParam = recommendedStyles.length > 0 ? `&styles=${encodeURIComponent(recommendedStyles.join(','))}` : '';
    const response = await fetch(`${API_URL}/barbers?location=${encodeURIComponent(location)}${stylesParam}`);
    const data = await response.json();
    
    console.log('Barber API response:', data);
    
    if (data.barbers && data.barbers.length > 0) {
      renderRealBarberList(data.barbers, data.real_data);
    } else {
      throw new Error('No barbershops found');
    }
  } catch (error) {
    console.error('Error loading barbershops:', error);
    if (barberListContainer) {
      barberListContainer.innerHTML = `
        <div class="bg-red-900/20 border border-red-500/50 rounded-lg p-4 text-center">
          <p class="text-red-400">Unable to load barbershops. Please check your location and try again.</p>
        </div>
      `;
    }
  }
}

function renderRealBarberList(barbers, isRealData = false) {
  if (!barberListContainer) return;
  
  // Add header showing if this is real or mock data
  const dataSourceBadge = isRealData ? 
    '<span class="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-xs">✓ Real Barbershops</span>' :
    '<span class="bg-yellow-500/20 text-yellow-400 px-3 py-1 rounded-full text-xs">Sample Data</span>';
  
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
    
    // Format hours if available
    let hoursHtml = '';
    if (barber.hours && barber.hours.length > 0) {
      const today = new Date().getDay();
      const todayHours = barber.hours[today === 0 ? 6 : today - 1]; // Adjust for Sunday
      hoursHtml = `<p class="text-xs text-gray-500 mt-1">${todayHours || 'Hours not available'}</p>`;
    }
    
    // Format open now status
    let openStatus = '';
    if (barber.open_now !== null && barber.open_now !== undefined) {
      openStatus = barber.open_now ? 
        '<span class="bg-green-500/20 text-green-400 px-2 py-1 rounded text-xs">Open Now</span>' :
        '<span class="bg-red-500/20 text-red-400 px-2 py-1 rounded text-xs">Closed</span>';
    }
    
    // Show real rating count if available
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
              ${hoursHtml}
            </div>
            ${openStatus}
          </div>
          
          <div class="flex items-center gap-4 mb-3">
            <span class="text-yellow-400 flex items-center gap-1">${ratingText}</span>
            <span class="text-green-400 font-semibold">~${barber.avgCost}</span>
            ${barber.phone !== 'Call for info' ? 
              `<a href="tel:${barber.phone}" class="text-sky-400 hover:text-sky-300 text-sm">${barber.phone}</a>` : 
              '<span class="text-gray-500 text-sm">No phone listed</span>'
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
              `<a href="${barber.website}" target="_blank" class="bg-gray-700 text-white px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors">
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
    `;
    barberListContainer.appendChild(card);
  });
  
  // Add search tips
  const tipsDiv = document.createElement('div');
  tipsDiv.className = 'mt-6 p-4 bg-gray-800/50 rounded-lg border border-gray-700';
  tipsDiv.innerHTML = `
    <p class="text-sm text-gray-400 mb-2">💡 Search Tips:</p>
    <ul class="text-xs text-gray-500 space-y-1">
      <li>• Enter your ZIP code for more precise results (e.g., "30308")</li>
      <li>• Use neighborhood names (e.g., "Buckhead, Atlanta")</li>
      <li>• Include city and state (e.g., "Atlanta, GA")</li>
    </ul>
  `;
  barberListContainer.appendChild(tipsDiv);
}

function findMatchingBarbers() {
  const location = locationSearch.value || 'Atlanta, GA';
  
  // Update the intro text
  if (barberIntro) {
    barberIntro.innerHTML = `
      <span class="text-gray-300">Finding real barbershops in</span> 
      <span class="text-sky-400 font-semibold">${location}</span>
      <span class="text-gray-300">that specialize in your recommended styles...</span>
    `;
  }
  
  // Pass recommended styles to the barber search
  loadNearbyBarbers(location, lastRecommendedStyles);
  switchTab('barbers');
}

// Add location search with debouncing
let searchTimeout;
function setupLocationSearch() {
  if (locationSearch) {
    locationSearch.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      const value = e.target.value.trim();
      
      if (value.length > 2) {
        searchTimeout = setTimeout(() => {
          loadNearbyBarbers(value, lastRecommendedStyles);
        }, 500); // Wait 500ms after user stops typing
      }
    });
    
    // Handle enter key
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

// --- Social Media Functions ---
function renderSocialFeed() {
  if (!socialFeedContainer) return;
  
  socialFeedContainer.innerHTML = '';
  
  if (socialPosts.length === 0) {
    socialFeedContainer.innerHTML = '<p class="text-center text-gray-500 py-10">No posts yet. Be the first!</p>';
    return;
  }
  
  socialPosts.forEach(post => {
    const postElement = document.createElement('div');
    postElement.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden';
    postElement.innerHTML = `
      <div class="p-4 flex items-center gap-3">
        <img src="${post.avatar}" alt="${post.username}" class="w-10 h-10 rounded-full object-cover">
        <div>
          <p class="font-semibold text-white">${post.username}</p>
          <p class="text-xs text-gray-400">${post.timeAgo}</p>
        </div>
      </div>
      <img src="${post.image}" alt="Post image" class="w-full h-80 object-cover">
      <div class="p-4">
        <div class="flex items-center gap-4 mb-2">
          <button onclick="toggleLike(${post.id})" class="flex items-center gap-2 transition-colors ${post.liked ? 'text-red-500' : 'text-gray-400 hover:text-red-500'}">
            <svg class="w-6 h-6 ${post.liked ? 'fill-current' : ''}" fill="${post.liked ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
            </svg>
            <span class="text-sm font-semibold">${post.likes}</span>
          </button>
        </div>
        <p class="text-gray-300">${post.caption}</p>
      </div>
    `;
    socialFeedContainer.appendChild(postElement);
  });
}

function handlePostImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = e => {
    postImagePreview.src = e.target.result;
    postImagePreview.classList.remove('hidden');
    postImageArea.classList.add('hidden');
  };
  reader.readAsDataURL(file);
}

function closeAddPostModal() {
  addPostModal.classList.add('hidden');
  postImageInput.value = '';
  postImagePreview.classList.add('hidden');
  postImageArea.classList.remove('hidden');
  postCaption.value = '';
}

async function submitSocialPost() {
  const caption = postCaption.value.trim();
  if (!postImagePreview.src || !caption) {
    alert('Please add both an image and caption');
    return;
  }
  
  const postData = {
    username: 'you',
    avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face',
    image: postImagePreview.src,
    caption: caption
  };
  
  if (firebaseService) {
    // Save to Firebase
    const result = await firebaseService.createSocialPost(postData);
    if (result.success) {
      console.log('✨ Post saved to Firebase');
      // Real-time listener will update the UI
    } else {
      alert('Failed to save post. Please try again.');
      return;
    }
  } else {
    // Fallback to local storage
    const newPost = {
      id: Date.now(),
      ...postData,
      likes: 0,
      timeAgo: 'now',
      liked: false
    };
    socialPosts.unshift(newPost);
    renderSocialFeed();
  }
  
  closeAddPostModal();
}

async function toggleLike(postId) {
  if (firebaseService) {
    // Update in Firebase
    const result = await firebaseService.toggleLike(postId);
    if (result.success) {
      console.log('❤️ Like updated in Firebase');
      // Real-time listener will update the UI
    }
  } else {
    // Fallback to local update
    const post = socialPosts.find(p => p.id === postId);
    if (post) {
      post.liked = !post.liked;
      post.likes += post.liked ? 1 : -1;
      renderSocialFeed();
    }
  }
  
  // Add heart animation
  if (event && event.target) {
    event.target.closest('button').classList.add('heart-animation');
    setTimeout(() => {
      event.target.closest('button').classList.remove('heart-animation');
    }, 600);
  }
}

// --- Bottom Nav Rendering ---
function renderBottomNav() {
  if (!bottomNav) return;

  const baseBtn = 'tab-button flex flex-col items-center justify-center h-14 flex-1 text-xs transition-all duration-200';
  const centerBtn = 'tab-button center-pill flex items-center justify-center h-12 w-12 transition-all duration-200 rounded-full bg-white -translate-y-2';

  // Clean SVG icons
  const icons = {
    home: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>',
    explore: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>',
    calendar: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>',
    community: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>',
    profile: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>',
    scissors: '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z"></path></svg>',
    shop: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>'
  };

  const clientTabs = [
    { key: 'ai', label: 'Home', icon: icons.home },
    { key: 'barbers', label: 'Explore', icon: icons.explore },
    { key: 'appointments', label: 'Book', icon: icons.calendar, center: true },
    { key: 'community', label: 'Community', icon: icons.community },
    { key: 'profile', label: 'Profile', icon: icons.profile }
  ];

  const barberTabs = [
    { key: 'barber-dashboard', label: 'Home', icon: icons.home },
    { key: 'barber-schedule', label: 'Bookings', icon: icons.calendar },
    { key: 'barber-portfolio', label: 'Work', icon: icons.scissors, center: true },
    { key: 'community', label: 'Community', icon: icons.community },
    { key: 'barber-profile', label: 'Shop', icon: icons.shop }
  ];

  const tabs = currentUserMode === 'client' ? clientTabs : barberTabs;

  // Layout: space for center pill - dark theme with white accents
  bottomNav.innerHTML = `
    <div class="flex items-center justify-between px-4 py-1">
      ${tabs.map((t, idx) => {
        if (t.center) {
          return `
            <div class="flex-1 flex items-center justify-center">
              <button class="${centerBtn} text-black" data-tab="${t.key}">
                ${t.icon}
              </button>
            </div>
          `;
        }
        return `
          <button class="${baseBtn} text-gray-500 hover:text-white" data-tab="${t.key}">
            ${t.icon}
            <span class="mt-1 text-[11px]">${t.label}</span>
          </button>
        `;
      }).join('')}
    </div>
  `;

  // Attach events
  bottomNav.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Set initial active state
  const defaultTab = currentUserMode === 'client' ? 'ai' : 'barber-dashboard';
  switchTab(defaultTab);
}

// --- Barber Portfolio Functions ---
function renderBarberPortfolio() {
  if (!portfolioGrid) return;
  
  portfolioGrid.innerHTML = '';
  
  if (barberPortfolio.length === 0) {
    portfolioGrid.innerHTML = '<div class="col-span-full text-center text-gray-500 py-10">No portfolio items yet. Upload your first work!</div>';
    return;
  }
  
  barberPortfolio.forEach(work => {
    const workElement = document.createElement('div');
    workElement.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden';
    workElement.innerHTML = `
      <img src="${work.image}" alt="${work.styleName}" class="w-full h-64 object-cover">
      <div class="p-4">
        <h3 class="text-lg font-bold text-white mb-2">${work.styleName}</h3>
        <p class="text-gray-300 text-sm mb-3">${work.description}</p>
        <div class="flex justify-between items-center text-xs text-gray-400">
          <span>${work.likes} likes</span>
          <span>${new Date(work.date).toLocaleDateString()}</span>
        </div>
      </div>
    `;
    portfolioGrid.appendChild(workElement);
  });
}

function handleWorkImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = e => {
    workImagePreview.src = e.target.result;
    workImagePreview.classList.remove('hidden');
    workImageArea.classList.add('hidden');
  };
  reader.readAsDataURL(file);
}

function closeUploadWorkModal() {
  uploadWorkModal.classList.add('hidden');
  workImageInput.value = '';
  workImagePreview.classList.add('hidden');
  workImageArea.classList.remove('hidden');
  workStyleName.value = '';
  workDescription.value = '';
}

async function submitPortfolioWork() {
  const styleName = workStyleName.value.trim();
  const description = workDescription.value.trim();
  
  if (!workImagePreview.src || !styleName || !description) {
    alert('Please fill in all fields');
    return;
  }
  
  const portfolioData = {
    barberId: 'current-barber',
    styleName: styleName,
    image: workImagePreview.src,
    description: description
  };
  
  if (firebaseService) {
    // Save to Firebase
    const result = await firebaseService.addPortfolioItem(portfolioData);
    if (result.success) {
      console.log('🎨 Portfolio work saved to Firebase');
      await loadBarberPortfolio(); // Reload portfolio
    } else {
      alert('Failed to save portfolio work. Please try again.');
      return;
    }
  } else {
    // Fallback to local storage
    const newWork = {
      id: Date.now(),
      ...portfolioData,
      likes: 0,
      date: new Date().toISOString().split('T')[0]
    };
    barberPortfolio.unshift(newWork);
    renderBarberPortfolio();
  }
  
  updateDashboardStats();
  closeUploadWorkModal();
}

// --- Client Profile Rendering ---
function renderClientProfile() {
  const historyEl = document.getElementById('client-profile-history');
  if (historyEl) {
    const history = appointments.filter(apt => apt.clientName === 'Current User');
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
function openBookingModal(barberId, barberName) {
  currentBarberForBooking = { id: barberId, name: barberName };
  
  document.getElementById('booking-barber-info').innerHTML = `
    <p class="text-lg font-semibold text-white">Booking with ${barberName}</p>
    <p class="text-sm text-gray-400">Select your preferred date and time</p>
  `;
  
  // Set minimum date to today
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

async function confirmBooking() {
  const date = document.getElementById('appointment-date').value;
  const time = document.getElementById('appointment-time').value;
  const service = document.getElementById('appointment-service').value;
  const notes = document.getElementById('appointment-notes').value;
  
  if (!date || !time || !service) {
    alert('Please fill in all required fields');
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
  
  const appointmentData = {
    clientName: 'Current User',
    clientId: 'current-user',
    barberName: currentBarberForBooking.name,
    barberId: currentBarberForBooking.id,
    date: date,
    time: time,
    service: serviceMap[service],
    price: priceMap[service],
    notes: notes || 'No special requests'
  };
  
  if (firebaseService) {
    // Save to Firebase
    const result = await firebaseService.createAppointment(appointmentData);
    if (result.success) {
      console.log('📅 Appointment saved to Firebase');
      await loadAppointments(); // Reload appointments
    } else {
      alert('Failed to book appointment. Please try again.');
      return;
    }
  } else {
    // Fallback to local storage
    const newAppointment = {
      id: Date.now(),
      ...appointmentData,
      status: 'pending'
    };
    appointments.push(newAppointment);
    renderClientAppointments();
    renderBarberAppointments();
  }
  
  updateDashboardStats();
  closeBookingModal();
  alert('Appointment booked successfully!');
}

function renderClientAppointments() {
  const clientAppointments = appointments.filter(apt => apt.clientName === 'Current User');
  
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

function renderBarberAppointments() {
  if (!barberAppointmentsContainer) return;
  
  barberAppointmentsContainer.innerHTML = '';
  
  if (appointments.length === 0) {
    barberAppointmentsContainer.innerHTML = '<p class="text-center text-gray-500 py-10">No appointments scheduled.</p>';
    return;
  }
  
  appointments.forEach(appointment => {
    const appointmentElement = document.createElement('div');
    appointmentElement.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl p-5';
    appointmentElement.innerHTML = `
      <div class="flex justify-between items-start mb-3">
        <div>
          <h3 class="text-lg font-bold text-white">${appointment.clientName}</h3>
          <p class="text-gray-400">${appointment.service}</p>
        </div>
        <div class="flex gap-2">
          <span class="px-3 py-1 rounded-full text-xs font-semibold ${
            appointment.status === 'confirmed' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'
          }">
            ${appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1)}
          </span>
          ${appointment.status === 'pending' ? 
            `<button onclick="confirmAppointment(${appointment.id})" class="bg-green-500 text-white px-3 py-1 rounded-full text-xs hover:bg-green-600 transition-colors">Confirm</button>` : ''
          }
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 text-sm">
        <p class="text-gray-300"><span class="text-gray-400">Date:</span> ${new Date(appointment.date).toLocaleDateString()}</p>
        <p class="text-gray-300"><span class="text-gray-400">Time:</span> ${appointment.time}</p>
        <p class="text-gray-300"><span class="text-gray-400">Price:</span> ${appointment.price}</p>
        <p class="text-gray-300"><span class="text-gray-400">Contact:</span> Available in app</p>
      </div>
      ${appointment.notes !== 'No special requests' ? `<p class="text-gray-400 text-sm mt-3">Notes: ${appointment.notes}</p>` : ''}
    `;
    barberAppointmentsContainer.appendChild(appointmentElement);
  });
}

function confirmAppointment(appointmentId) {
  const appointment = appointments.find(apt => apt.id === appointmentId);
  if (appointment) {
    appointment.status = 'confirmed';
    renderBarberAppointments();
    renderClientAppointments();
    updateDashboardStats();
  }
}

function updateDashboardStats() {
  const today = new Date().toISOString().split('T')[0];
  const todayAppointments = appointments.filter(apt => apt.date === today).length;
  
  const thisWeekStart = new Date();
  thisWeekStart.setDate(thisWeekStart.getDate() - thisWeekStart.getDay());
  const thisWeekAppointments = appointments.filter(apt => {
    const aptDate = new Date(apt.date);
    return aptDate >= thisWeekStart;
  }).length;
  
  const todayElement = document.getElementById('today-appointments');
  const weekElement = document.getElementById('week-appointments');
  const portfolioCountElement = document.getElementById('portfolio-count');
  
  if (todayElement) todayElement.textContent = todayAppointments;
  if (weekElement) weekElement.textContent = thisWeekAppointments;
  if (portfolioCountElement) portfolioCountElement.textContent = barberPortfolio.length;
}

// --- New function for individual style barber search ---
function findBarbersForStyle(styleName) {
  const location = locationSearch.value || 'Atlanta, GA';
  
  console.log(`Finding barbers for specific style: ${styleName} in ${location}`);
  
  // Update the intro text to show we're searching for this specific style
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
  
  // Search for barbers with this specific style
  loadNearbyBarbers(location, [styleName]);
  switchTab('barbers');
}

// --- Virtual Try-On Integration ---
let virtualTryOnInstance = null;

// Function to open virtual try-on for specific style
async function tryOnStyle(styleName) {
  console.log(`Opening virtual try-on for: ${styleName}`);
  
  // Check if user has uploaded a photo
  const imagePreview = document.getElementById('image-preview');
  if (!imagePreview || !imagePreview.src || imagePreview.src === '') {
    alert('Please upload a photo first to use virtual try-on');
    return;
  }
  
  // Show modal
  const modal = document.getElementById('virtual-tryon-modal');
  if (modal) {
    modal.classList.remove('hidden');
    document.getElementById('current-tryon-style').innerHTML = `
      <span class="text-sky-400 font-semibold">Trying on: ${styleName}</span>
    `;
    
    // Copy the uploaded image to the try-on viewer
    const tryOnPhoto = document.getElementById('virtual-tryon-photo');
    const tryOnVideo = document.getElementById('virtual-tryon-video');
    
    if (tryOnPhoto && imagePreview.src) {
      tryOnPhoto.src = imagePreview.src;
      tryOnPhoto.style.display = 'block';
      
      // Hide video element
      if (tryOnVideo) {
        tryOnVideo.style.display = 'none';
      }
    }
  }
  
  // Initialize virtual try-on if needed
  if (!virtualTryOnInstance) {
    virtualTryOnInstance = new LineUpVirtualTryOn();
  }
  
  // Load the specific style
  await virtualTryOnInstance.initialize();
  await virtualTryOnInstance.selectHairstyle(styleName);
}

// Virtual Try-On Integration Class - HairCLIP via Replicate
class LineUpVirtualTryOn {
  constructor() {
    this.isInitialized = false;
    this.currentStyle = null;
    this.resultImage = null;
  }

  async initialize() {
    if (this.isInitialized) return;

    try {
      const loading = document.getElementById('tryon-loading');
      if (loading) loading.classList.remove('hidden');
      
      // Simple initialization - no external dependencies needed
      await new Promise(resolve => setTimeout(resolve, 100));
      
      this.isInitialized = true;
      this.setupEventListeners();
      
      console.log('✅ HairCLIP Virtual Try-On ready!');
    } catch (error) {
      console.error('❌ Virtual Try-On failed:', error);
      alert('Virtual Try-On initialization failed: ' + error.message);
    } finally {
      const loading = document.getElementById('tryon-loading');
      if (loading) loading.classList.add('hidden');
    }
  }

  setupEventListeners() {
    const startBtn = document.getElementById('start-tryon');
    const stopBtn = document.getElementById('stop-tryon');
    const screenshotBtn = document.getElementById('take-screenshot');
    const closeBtn = document.getElementById('close-tryon-modal');

    if (startBtn) startBtn.addEventListener('click', () => this.startTryOn());
    if (stopBtn) stopBtn.addEventListener('click', () => this.stopTryOn());
    if (screenshotBtn) screenshotBtn.addEventListener('click', () => this.takeScreenshot());
    if (closeBtn) closeBtn.addEventListener('click', () => this.closeTryOnModal());
  }

  async startTryOn() {
    const photoElement = document.getElementById('virtual-tryon-photo');
    const imagePreview = document.getElementById('image-preview');
    
    console.log('🎬 Starting virtual try-on...');
    console.log('Photo element:', photoElement);
    console.log('Image preview:', imagePreview);
    console.log('Current style:', this.currentStyle);
    
    if (!photoElement) {
      alert('Virtual try-on photo element not found');
      return;
    }
    
    if (!imagePreview || !imagePreview.src) {
      alert('Please upload a photo first to use virtual try-on');
      return;
    }
    
    if (!this.currentStyle) {
      alert('No hairstyle selected');
      return;
    }
    
    try {
      const loading = document.getElementById('tryon-loading');
      if (loading) {
        loading.classList.remove('hidden');
        loading.querySelector('p').textContent = 'Applying hairstyle with AI... This may take 30-60 seconds.';
      }
      
      console.log('Converting image to base64...');
      const base64Data = await this.imageToBase64(imagePreview.src);
      console.log('Base64 data length:', base64Data.length);
      console.log('Sending to backend API...');
      
      // Call backend with HairCLIP
      const response = await fetch(`${API_URL}/virtual-tryon`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userPhoto: base64Data,
          styleDescription: this.currentStyle
        })
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        throw new Error('Failed to process hairstyle change: ' + errorText);
      }
      
      const result = await response.json();
      console.log('✅ Try-on processed:', result);
      
      if (result.success && result.resultImage) {
        // Display the result image
        this.resultImage = `data:image/jpeg;base64,${result.resultImage}`;
        
        console.log('📸 Updating photo element with result...');
        console.log('Result image data length:', result.resultImage.length);
        
        // Make sure the photo element is visible and set the source
        photoElement.style.display = 'block';
        photoElement.style.zIndex = '10';
        photoElement.src = this.resultImage;
        
        // Force a reflow to ensure the update is applied
        photoElement.offsetHeight;
        
        console.log('✅ Image updated! Photo element src:', photoElement.src.substring(0, 50) + '...');
      } else {
        throw new Error(result.message || 'No result image returned');
      }
      
      document.getElementById('start-tryon').classList.add('hidden');
      document.getElementById('stop-tryon').classList.remove('hidden');
      document.getElementById('take-screenshot').classList.remove('hidden');
    } catch (error) {
      console.error('❌ Detailed error:', error);
      alert('Failed to apply hairstyle: ' + error.message);
    } finally {
      const loading = document.getElementById('tryon-loading');
      if (loading) loading.classList.add('hidden');
    }
  }

  stopTryOn() {
    document.getElementById('start-tryon').classList.remove('hidden');
    document.getElementById('stop-tryon').classList.add('hidden');
    document.getElementById('take-screenshot').classList.add('hidden');
    this.resultImage = null;
  }

  async selectHairstyle(styleName) {
    this.currentStyle = styleName;
    this.resultImage = null; // Reset result when changing style
    console.log('Selected style:', styleName);
  }
  
  async imageToBase64(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      
      // Don't set crossOrigin for data URLs or same-origin images
      if (src.startsWith('http://') || src.startsWith('https://')) {
        img.crossOrigin = 'anonymous';
      }
      
      img.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          canvas.width = img.width;
          canvas.height = img.height;
          ctx.drawImage(img, 0, 0);
          const dataUrl = canvas.toDataURL('image/jpeg');
          // Extract base64 part after comma
          const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl;
          resolve(base64);
        } catch (error) {
          reject(new Error('Failed to convert image to base64: ' + error.message));
        }
      };
      
      img.onerror = (error) => {
        reject(new Error('Failed to load image: ' + error));
      };
      
      img.src = src;
    });
  }

  async takeScreenshot() {
    if (!this.resultImage) {
      alert('No result to capture. Please apply a hairstyle first.');
      return;
    }
    
    const screenshot = this.resultImage;
    
    if (firebaseService) {
      try {
        const postData = {
          username: 'you',
          avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face',
          image: screenshot,
          caption: `Trying on ${this.currentStyle} with LineUp AI! 🔥✨`
        };
        
        await firebaseService.createSocialPost(postData);
        alert('Screenshot saved and shared to social feed! 🎉');
      } catch (error) {
        console.error('Failed to save screenshot:', error);
        alert('Failed to save screenshot. Please try again.');
      }
    } else {
      const newPost = {
        id: Date.now(),
        username: 'you',
        avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face',
        image: screenshot,
        caption: `Trying on ${this.currentStyle} with LineUp AI! 🔥`,
        likes: 0,
        timeAgo: 'now',
        liked: false
      };
      
      socialPosts.unshift(newPost);
      renderSocialFeed();
      alert('Screenshot saved to social feed!');
    }
  }

  closeTryOnModal() {
    this.stopTryOn();
    const modal = document.getElementById('virtual-tryon-modal');
    if (modal) modal.classList.add('hidden');
  }
}

// --- Firebase Data Loading Functions ---
async function loadSocialFeed() {
  if (!firebaseService) return;
  
  try {
    const result = await firebaseService.getSocialPosts();
    if (result.success) {
      socialPosts = result.posts;
      renderSocialFeed();
      console.log('📱 Social feed loaded from Firebase');
    }
  } catch (error) {
    console.error('❌ Failed to load social feed:', error);
  }
}

async function loadBarberPortfolio() {
  if (!firebaseService) return;
  
  try {
    const result = await firebaseService.getPortfolio();
    if (result.success) {
      barberPortfolio = result.portfolio;
      renderBarberPortfolio();
      console.log('💼 Portfolio loaded from Firebase');
    }
  } catch (error) {
    console.error('❌ Failed to load portfolio:', error);
  }
}

async function loadAppointments() {
  if (!firebaseService) return;
  
  try {
    const result = await firebaseService.getAppointments();
    if (result.success) {
      appointments = result.appointments;
      renderClientAppointments();
      renderBarberAppointments();
      console.log('📅 Appointments loaded from Firebase');
    }
  } catch (error) {
    console.error('❌ Failed to load appointments:', error);
  }
}

// Set up real-time listeners
function setupRealtimeListeners() {
  if (!firebaseService) return;
  
  // Real-time social feed updates
  firebaseService.subscribeSocialPosts((posts) => {
    socialPosts = posts;
    renderSocialFeed();
    console.log('🔄 Social feed updated in real-time');
  });
  
  console.log('🔊 Real-time listeners set up');
}

// --- Subscription Package Functions ---
function closeCreatePackageModal() {
  const modal = document.getElementById('create-package-modal');
  if (modal) modal.classList.add('hidden');
  
  // Reset form
  document.getElementById('package-title').value = '';
  document.getElementById('package-description').value = '';
  document.getElementById('package-num-cuts').value = '';
  document.getElementById('package-duration').value = '';
  document.getElementById('package-price').value = '';
  document.getElementById('package-discount').value = '';
}

async function handleCreatePackage() {
  const title = document.getElementById('package-title').value.trim();
  const description = document.getElementById('package-description').value.trim();
  const numCuts = parseInt(document.getElementById('package-num-cuts').value);
  const duration = parseInt(document.getElementById('package-duration').value);
  const price = document.getElementById('package-price').value.trim();
  const discount = document.getElementById('package-discount').value.trim();
  
  if (!title || !description || !numCuts || !duration || !price) {
    alert('Please fill in all required fields');
    return;
  }
  
  const packageData = {
    barberId: 'current-barber',
    barberName: 'Your Barber Shop',
    title: title,
    description: description,
    numCuts: numCuts,
    durationMonths: duration,
    price: price,
    discount: discount
  };
  
  try {
    const response = await fetch(`${API_URL}/subscription-packages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(packageData)
    });
    
    if (!response.ok) throw new Error('Failed to create package');
    
    const result = await response.json();
    subscriptionPackages.push(result.package);
    renderSubscriptionPackages();
    closeCreatePackageModal();
    alert('Package created successfully!');
  } catch (error) {
    console.error('Error creating package:', error);
    alert('Failed to create package. Please try again.');
  }
}

async function loadSubscriptionPackages() {
  try {
    const response = await fetch(`${API_URL}/subscription-packages?barber_id=current-barber`);
    const data = await response.json();
    if (data.packages) {
      subscriptionPackages = data.packages;
      renderSubscriptionPackages();
    }
  } catch (error) {
    console.error('Error loading packages:', error);
  }
}

function renderSubscriptionPackages() {
  const container = document.getElementById('subscription-packages-list');
  if (!container) return;
  
  if (subscriptionPackages.length === 0) {
    container.innerHTML = '<p class="text-gray-500 text-sm">No packages created yet.</p>';
    return;
  }
  
  container.innerHTML = subscriptionPackages.map(pkg => `
    <div class="bg-gray-800/60 border border-gray-700 rounded-xl p-4">
      <div class="flex justify-between items-start mb-2">
        <div>
          <h4 class="font-bold text-white">${pkg.title}</h4>
          <p class="text-sm text-gray-400">${pkg.description}</p>
        </div>
        <span class="text-green-400 font-bold">${pkg.price}</span>
      </div>
      <div class="grid grid-cols-3 gap-2 text-xs text-gray-400 mt-3">
        <span>${pkg.numCuts} cuts</span>
        <span>${pkg.durationMonths} months</span>
        ${pkg.discount ? `<span class="text-green-400">${pkg.discount}</span>` : ''}
      </div>
    </div>
  `).join('');
}

// --- Make functions globally available ---
window.toggleLike = toggleLike;
window.openBookingModal = openBookingModal;
window.confirmAppointment = confirmAppointment;
window.findBarbersForStyle = findBarbersForStyle;
window.tryOnStyle = tryOnStyle;
window.loadSocialFeed = loadSocialFeed;
window.loadBarberPortfolio = loadBarberPortfolio;
window.loadAppointments = loadAppointments;
window.loadSubscriptionPackages = loadSubscriptionPackages;
