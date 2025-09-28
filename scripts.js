// scripts-updated.js - Frontend JavaScript for LineUp Two-Sided Platform

// --- Configuration ---
const API_URL = 'https://lineup-fjpn.onrender.com';
let GOOGLE_PLACES_API_KEY = null; // Will be fetched from backend

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

// Role switching
const clientModeBtn = document.getElementById('client-mode');
const barberModeBtn = document.getElementById('barber-mode');
const clientContent = document.getElementById('client-content');
const barberContent = document.getElementById('barber-content');
const clientNav = document.getElementById('client-nav');
const barberNav = document.getElementById('barber-nav');

// Social elements
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

// --- Initialize ---
window.addEventListener('DOMContentLoaded', async () => {
  console.log('LineUp Two-Sided Platform initialized');
  
  // Fetch API key from backend
  await fetchApiConfig();
  
  // Initialize data
  socialPosts = [...mockSocialPosts];
  barberPortfolio = [...mockBarberPortfolio];
  appointments = [...mockAppointments];
  
  // Render initial content
  renderSocialFeed();
  renderBarberPortfolio();
  renderClientAppointments();
  renderBarberAppointments();
  loadNearbyBarbers('Atlanta, GA');
  
  testBackendConnection();
  setupEventListeners();
  updateDashboardStats();
});

// Fetch API configuration from backend
async function fetchApiConfig() {
  try {
    const response = await fetch(`${API_URL}/config`);
    const data = await response.json();
    GOOGLE_PLACES_API_KEY = data.placesApiKey;
    console.log('Google Places API configured:', !!GOOGLE_PLACES_API_KEY);
  } catch (error) {
    console.log('Could not fetch API config, using mock data');
    GOOGLE_PLACES_API_KEY = null;
  }
}
});

// --- Setup Event Listeners ---
function setupEventListeners() {
  // Role switching
  clientModeBtn.addEventListener('click', () => switchMode('client'));
  barberModeBtn.addEventListener('click', () => switchMode('barber'));
  
  // Tabs
  document.querySelectorAll('.tab-button').forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.dataset.tab;
      switchTab(targetTab);
    });
  });

  // Image upload
  imageUploadArea.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', handleImageUpload);
  
  // Analysis
  analyzeButton.addEventListener('click', analyzeImage);
  tryAgainButton.addEventListener('click', resetUI);
  startOverButton.addEventListener('click', resetUI);
  findBarberButton.addEventListener('click', findMatchingBarbers);
  
  // Barber search
  locationSearch.addEventListener('input', debounce(searchBarbersByLocation, 300));
  refreshBarbersBtn.addEventListener('click', () => loadNearbyBarbers(locationSearch.value || 'Atlanta, GA'));
  
  // Social modals
  addPostButton.addEventListener('click', () => addPostModal.classList.remove('hidden'));
  postImageArea.addEventListener('click', () => postImageInput.click());
  postImageInput.addEventListener('change', handlePostImageUpload);
  cancelPost.addEventListener('click', closeAddPostModal);
  submitPost.addEventListener('click', submitSocialPost);
  
  // Barber modals
  uploadWorkButton.addEventListener('click', () => uploadWorkModal.classList.remove('hidden'));
  document.getElementById('add-portfolio-btn').addEventListener('click', () => uploadWorkModal.classList.remove('hidden'));
  workImageArea.addEventListener('click', () => workImageInput.click());
  workImageInput.addEventListener('change', handleWorkImageUpload);
  cancelWork.addEventListener('click', closeUploadWorkModal);
  submitWork.addEventListener('click', submitPortfolioWork);
  
  // Appointment booking
  document.getElementById('cancel-booking').addEventListener('click', closeBookingModal);
  document.getElementById('confirm-booking').addEventListener('click', confirmBooking);
  
  // Close modals on outside click
  [addPostModal, uploadWorkModal, bookAppointmentModal].forEach(modal => {
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
    clientModeBtn.classList.add('bg-sky-500', 'text-white');
    clientModeBtn.classList.remove('text-gray-400');
    barberModeBtn.classList.remove('bg-sky-500', 'text-white');
    barberModeBtn.classList.add('text-gray-400');
    
    clientContent.classList.remove('hidden');
    barberContent.classList.add('hidden');
    clientNav.classList.remove('hidden');
    barberNav.classList.add('hidden');
    
    // Reset to first tab
    switchTab('ai');
  } else {
    barberModeBtn.classList.add('bg-sky-500', 'text-white');
    barberModeBtn.classList.remove('text-gray-400');
    clientModeBtn.classList.remove('bg-sky-500', 'text-white');
    clientModeBtn.classList.add('text-gray-400');
    
    barberContent.classList.remove('hidden');
    clientContent.classList.add('hidden');
    barberNav.classList.remove('hidden');
    clientNav.classList.add('hidden');
    
    // Reset to first tab
    switchTab('barber-dashboard');
  }
}

// --- Tab Switching ---
function switchTab(targetTab) {
  // Update tab buttons
  document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('tab-active'));
  document.querySelector(`[data-tab="${targetTab}"]`).classList.add('tab-active');
  
  // Update content
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  document.getElementById(targetTab + '-content').classList.remove('hidden');
}

// --- Backend Connection ---
async function testBackendConnection() {
  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();
    console.log('✅ Backend connected:', data);
  } catch (err) {
    console.log('⚠️ Backend may be sleeping (Render free tier). Will wake up on first request.');
  }
}

// --- Image Upload and Analysis (existing code) ---
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
      console.log('Image loaded and resized. Size:', Math.round(base64ImageData.length / 1024), 'KB');
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
      contents: [
        { 
          parts: [
            { text: "Analyze this person and provide face, hair info and 5 haircut recommendations." },
            { inlineData: { mimeType: "image/jpeg", data: base64ImageData } }
          ]
        }
      ]
    };

    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ payload })
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const result = await response.json();
    if (result.error) {
      throw new Error(result.error);
    }

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
      }
    ]
  };
}

function showError(msg) {
  loader.classList.add('hidden');
  statusMessage.textContent = '';
  errorContainer.classList.remove('hidden');
  errorMessage.textContent = msg;
  
  setTimeout(() => {
    errorContainer.classList.add('hidden');
  }, 3000);
}

function displayResults(data) {
  statusSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');

  // Analysis Grid
  analysisGrid.innerHTML = '';
  const analysisData = [
    { label: 'Face Shape', value: data.analysis.faceShape || 'Unknown' },
    { label: 'Hair Texture', value: data.analysis.hairTexture || 'Unknown' },
    { label: 'Hair Color', value: data.analysis.hairColor || 'Unknown' },
    { label: 'Gender', value: data.analysis.estimatedGender || 'Unknown' },
    { label: 'Est. Age', value: data.analysis.estimatedAge || 'Unknown' }
  ];
  
  analysisData.forEach(item => {
    const div = document.createElement('div');
    div.className = 'bg-gray-800 p-4 rounded-lg';
    div.innerHTML = `
      <p class="text-sm text-gray-400">${item.label}</p>
      <p class="font-bold text-lg text-white">${item.value}</p>
    `;
    analysisGrid.appendChild(div);
  });

  // Recommendations
  recommendationsContainer.innerHTML = '';
  const recommendations = data.recommendations || [];
  lastRecommendedStyles = recommendations.slice(0, 5).map(r => r.styleName);
  
  recommendations.slice(0, 5).forEach(rec => {
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden flex flex-col';
    const placeholderImageUrl = `https://placehold.co/600x400/1a1a1a/38bdf8?text=${encodeURIComponent(rec.styleName || 'Style')}`;
    card.innerHTML = `
      <img src="${placeholderImageUrl}" alt="${rec.styleName}" class="w-full h-48 object-cover">
      <div class="p-5 flex flex-col flex-grow">
        <h3 class="text-xl font-bold text-white mb-2">${rec.styleName || 'Unnamed Style'}</h3>
        <p class="text-gray-300 text-sm mb-4 flex-grow">${rec.description || 'No description available'}</p>
        <p class="text-xs text-gray-400">
          <strong class="text-sky-400">Why it works:</strong> ${rec.reason || 'Great match for your features'}
        </p>
      </div>
    `;
    recommendationsContainer.appendChild(card);
  });
}

// --- Google Places Integration ---
async function loadNearbyBarbers(location = 'Atlanta, GA') {
  console.log('Loading barbers for:', location);
  
  if (!GOOGLE_PLACES_API_KEY) {
    console.log('Google Places API key not configured, using mock data');
    renderBarberList(getMockBarbers());
    return;
  }

  try {
    // Use CORS-friendly approach through backend or direct API calls
    // For production, you might want to proxy through your backend for better security
    
    // First geocode the location
    const geocodeUrl = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodeURIComponent(location)}&key=${GOOGLE_PLACES_API_KEY}`;
    
    // Note: For production, consider making these calls through your backend to avoid CORS issues
    // For now, this will work if your API key has proper domain restrictions
    
    const geocodeResponse = await fetch(geocodeUrl);
    const geocodeData = await geocodeResponse.json();
    
    if (geocodeData.status !== 'OK' || !geocodeData.results[0]) {
      throw new Error('Location not found');
    }

    const { lat, lng } = geocodeData.results[0].geometry.location;
    
    // Search for barbershops using Places API
    const placesUrl = `https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=${lat},${lng}&radius=10000&type=hair_care&keyword=barber&key=${GOOGLE_PLACES_API_KEY}`;
    const placesResponse = await fetch(placesUrl);
    const placesData = await placesResponse.json();
    
    if (placesData.status === 'OK') {
      const barbers = placesData.results.slice(0, 10).map(place => ({
        id: place.place_id,
        name: place.name,
        rating: place.rating || 4.0,
        priceLevel: place.price_level || 2,
        address: place.vicinity,
        photo: place.photos?.[0] ? 
          `https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${place.photos[0].photo_reference}&key=${GOOGLE_PLACES_API_KEY}` : 
          null,
        specialties: ['Fade', 'Taper', 'Beard Trim'], // Default specialties
        avgCost: (place.price_level || 2) * 25 + 25, // Estimate cost based on price level
        phone: place.formatted_phone_number || 'Call for info',
        hours: place.opening_hours?.weekday_text?.[0] || 'Hours vary'
      }));
      
      renderBarberList(barbers);
    } else {
      throw new Error('Places API error: ' + placesData.status);
    }
  } catch (error) {
    console.error('Error loading barbers:', error);
    
    // Show user-friendly message
    showNotification('Using sample barbers - location services temporarily unavailable');
    
    // Fall back to mock data
    renderBarberList(getMockBarbers());
  }
}

// Alternative: Load barbers through backend (more secure)
async function loadNearbyBarbersViaBackend(location = 'Atlanta, GA') {
  try {
    const response = await fetch(`${API_URL}/barbers?location=${encodeURIComponent(location)}`);
    const data = await response.json();
    
    if (data.barbers) {
      renderBarberList(data.barbers);
    } else {
      throw new Error('No barbers data received');
    }
  } catch (error) {
    console.error('Error loading barbers via backend:', error);
    renderBarberList(getMockBarbers());
  }
}

function getMockBarbers() {
  return [
    { 
      id: 1, 
      name: 'Elite Cuts Atlanta', 
      specialties: ['Fade', 'Taper'], 
      rating: 4.9, 
      avgCost: 45, 
      address: 'Midtown Atlanta',
      photo: 'https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop'
    },
    { 
      id: 2, 
      name: 'The Buckhead Barber', 
      specialties: ['Pompadour', 'Buzz Cut'], 
      rating: 4.8, 
      avgCost: 55, 
      address: 'Buckhead',
      photo: 'https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop'
    },
    { 
      id: 3, 
      name: 'Virginia-Highland Shears', 
      specialties: ['Modern Fade', 'Beard Trim'], 
      rating: 4.9, 
      avgCost: 65, 
      address: 'Virginia-Highland',
      photo: 'https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop'
    }
  ];
}

function searchBarbersByLocation() {
  const location = locationSearch.value.trim();
  if (location.length > 2) {
    // Use backend API for more reliable results
    loadNearbyBarbersViaBackend(location);
  }
}

function findMatchingBarbers() {
  barberIntro.textContent = "Barbers specializing in your recommended styles:";
  const location = locationSearch.value || 'Atlanta, GA';
  loadNearbyBarbersViaBackend(location);
  switchTab('barbers');
}

// Show notification to user
function showNotification(message, type = 'info') {
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-lg text-white transition-all duration-300 ${
    type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500'
  }`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  // Auto-remove after 3 seconds
  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

function renderBarberList(barbers) {
  if (!barberListContainer) return;
  
  barberListContainer.innerHTML = '';
  barbers.forEach(barber => {
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden';
    card.innerHTML = `
      <div class="flex flex-col sm:flex-row">
        <img src="${barber.photo || 'https://placehold.co/200x150/1a1a1a/38bdf8?text=Barber'}" 
             alt="${barber.name}" class="w-full sm:w-48 h-48 sm:h-auto object-cover">
        <div class="p-5 flex-1 flex flex-col justify-between">
          <div>
            <h4 class="text-xl font-bold text-white mb-1">${barber.name}</h4>
            <p class="text-sm text-gray-400 mb-2">${barber.address}</p>
            <div class="flex items-center gap-4 mb-3">
              <span class="text-yellow-400 flex items-center gap-1">${barber.rating} ★</span>
              <span class="text-green-400 font-semibold">~${barber.avgCost}</span>
            </div>
            <div class="flex gap-2 mb-4">
              ${barber.specialties.map(s => 
                `<span class="bg-sky-500/20 border border-sky-500/50 text-sky-300 text-xs px-3 py-1 rounded-full">${s}</span>`
              ).join('')}
            </div>
          </div>
          <button onclick="openBookingModal(${barber.id}, '${barber.name}')" 
                  class="bg-green-500 text-white px-6 py-2 rounded-lg hover:bg-green-600 transition-colors self-start">
            Book Appointment
          </button>
        </div>
      </div>
    `;
    barberListContainer.appendChild(card);
  });
}

// --- Social Media Functions ---
function renderSocialFeed() {
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

function submitSocialPost() {
  const caption = postCaption.value.trim();
  if (!postImagePreview.src || !caption) {
    alert('Please add both an image and caption');
    return;
  }
  
  const newPost = {
    id: Date.now(),
    username: 'you',
    avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face',
    image: postImagePreview.src,
    caption: caption,
    likes: 0,
    timeAgo: 'now',
    liked: false
  };
  
  socialPosts.unshift(newPost);
  renderSocialFeed();
  closeAddPostModal();
}

function toggleLike(postId) {
  const post = socialPosts.find(p => p.id === postId);
  if (post) {
    post.liked = !post.liked;
    post.likes += post.liked ? 1 : -1;
    renderSocialFeed();
  }
}

// --- Barber Portfolio Functions ---
function renderBarberPortfolio() {
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

function submitPortfolioWork() {
  const styleName = workStyleName.value.trim();
  const description = workDescription.value.trim();
  
  if (!workImagePreview.src || !styleName || !description) {
    alert('Please fill in all fields');
    return;
  }
  
  const newWork = {
    id: Date.now(),
    styleName: styleName,
    image: workImagePreview.src,
    description: description,
    likes: 0,
    date: new Date().toISOString().split('T')[0]
  };
  
  barberPortfolio.unshift(newWork);
  renderBarberPortfolio();
  updateDashboardStats();
  closeUploadWorkModal();
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

function confirmBooking() {
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
  
  const newAppointment = {
    id: Date.now(),
    clientName: 'Current User',
    barberName: currentBarberForBooking.name,
    date: date,
    time: time,
    service: serviceMap[service],
    price: priceMap[service],
    status: 'pending',
    notes: notes || 'No special requests'
  };
  
  appointments.push(newAppointment);
  renderClientAppointments();
  renderBarberAppointments();
  updateDashboardStats();
  closeBookingModal();
  
  alert('Appointment booked successfully!');
}

function renderClientAppointments() {
  const clientAppointments = appointments.filter(apt => apt.clientName === 'Current User');
  
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
  
  document.getElementById('today-appointments').textContent = todayAppointments;
  document.getElementById('week-appointments').textContent = thisWeekAppointments;
  document.getElementById('portfolio-count').textContent = barberPortfolio.length;
}

// --- Utility Functions ---
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// --- Make functions globally available ---
window.toggleLike = toggleLike;
window.openBookingModal = openBookingModal;
window.confirmAppointment = confirmAppointment;mentElement.innerHTML = `
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
  barberAppointmentsContainer.innerHTML = '';
  
  if (appointments.length === 0) {
    barberAppointmentsContainer.innerHTML = '<p class="text-center text-gray-500 py-10">No appointments scheduled.</p>';
    return;
  }
  
  appointments.forEach(appointment => {
    const appointmentElement = document.createElement('div');
    appointmentElement.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl p-5';
    appoint
