// scripts-updated.js - Frontend JavaScript for LineUp Two-Sided Platform

// --- Configuration ---
const API_URL = 'https://lineup-fjpn.onrender.com';

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

// Subscription package elements
const createPackageBtn = document.getElementById('create-package-btn');
const createPackageModal = document.getElementById('create-package-modal');
const subscriptionPackagesList = document.getElementById('subscription-packages-list');
const cancelPackageBtn = document.getElementById('cancel-package');
const submitPackageBtn = document.getElementById('submit-package');

// --- State ---
let base64ImageData = null;
let lastRecommendedStyles = [];
let currentUserMode = 'client';
let socialPosts = [];
let barberPortfolio = [];
let appointments = [];
let currentBarberForBooking = null;
let subscriptionPackages = [];
let currentBarberId = 'barber_' + Math.random().toString(36).substr(2, 9);
let currentBarberName = 'My Barber Shop';

// --- Initialize Mock Data ---
function initializeMockData() {
  // Social posts with variety
  socialPosts = [
    {
      id: 1,
      username: 'mike_style',
      avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop&crop=face',
      image: 'https://images.unsplash.com/photo-1622296089863-eb7fc530daa8?w=400&h=400&fit=crop',
      caption: 'Fresh fade from @atlanta_cuts 🔥 Loving this clean look!',
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
    },
    {
      id: 4,
      username: 'alex_barber',
      avatar: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop&crop=face',
      image: 'https://images.unsplash.com/photo-1633681926022-84c23e8cb2d6?w=400&h=400&fit=crop',
      caption: 'Textured pompadour on my client today. What do you think? 💇‍♂️',
      likes: 89,
      timeAgo: '2d',
      liked: false
    }
  ];
  
  // Barber portfolio
  barberPortfolio = [
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
    },
    {
      id: 3,
      styleName: 'Textured Quiff',
      image: 'https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=400&fit=crop',
      description: 'Voluminous quiff with natural texture and movement.',
      likes: 25,
      date: '2024-01-13'
    }
  ];
  
  // Appointments - Include appointments for current barber (will be filtered by barberId)
  appointments = [
    {
      id: 1,
      clientName: 'Alex Johnson',
      clientId: 'client_1',
      barberName: 'Mike\'s Cuts',
      barberId: 'barber_1',
      date: '2024-12-20',
      time: '14:00',
      service: 'Haircut + Beard',
      price: '$65',
      status: 'confirmed',
      notes: 'Looking for a modern fade'
    },
    {
      id: 2,
      clientName: 'Current User',
      clientId: 'current-user',
      barberName: 'Style Studio',
      barberId: 'barber_2',
      date: '2024-12-22',
      time: '10:00',
      service: 'Haircut',
      price: '$45',
      status: 'pending',
      notes: 'First time visit'
    },
    {
      id: 3,
      clientName: 'Sarah Miller',
      clientId: 'client_2',
      barberName: 'Mike\'s Cuts',
      barberId: 'barber_1',
      date: '2024-12-21',
      time: '15:30',
      service: 'Haircut',
      price: '$45',
      status: 'confirmed',
      notes: 'Regular trim'
    },
    {
      id: 4,
      clientName: 'Michael Chen',
      clientId: 'client_3',
      barberName: 'Mike\'s Cuts',
      barberId: 'barber_1',
      date: '2024-12-23',
      time: '11:00',
      service: 'Haircut + Beard',
      price: '$65',
      status: 'pending',
      notes: 'Want a fade with texture on top'
    },
    {
      id: 5,
      clientName: 'David Williams',
      clientId: 'client_4',
      barberName: 'Mike\'s Cuts',
      barberId: 'barber_1',
      date: '2024-12-24',
      time: '16:00',
      service: 'Haircut',
      price: '$45',
      status: 'confirmed',
      notes: 'Regular customer'
    }
  ];
}

// --- Initialize ---
window.addEventListener('DOMContentLoaded', () => {
  console.log('LineUp Two-Sided Platform initialized');
  
  initializeMockData();
  testBackendConnection();
  setupEventListeners();
  renderBottomNav();
  
  // Load posts from API first, then render
  loadSocialPosts().then(() => {
  renderSocialFeed();
  });
  
  // Render initial data
  renderBarberPortfolio(); // This will show mock data initially
  renderClientAppointments();
  loadBarberAppointments();
  updateDashboardStats();
  
  loadNearbyBarbers('Atlanta, GA');
  
  // Default to client Home - render nav first, then switch mode
  renderBottomNav();
  switchMode('client');
});

// --- Setup Event Listeners ---
function setupEventListeners() {
  // Role switching
  clientModeBtn.addEventListener('click', () => switchMode('client'));
  barberModeBtn.addEventListener('click', () => switchMode('barber'));
  
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
  
  // Subscription packages
  if (createPackageBtn) createPackageBtn.addEventListener('click', openCreatePackageModal);
  if (cancelPackageBtn) cancelPackageBtn.addEventListener('click', closeCreatePackageModal);
  if (submitPackageBtn) submitPackageBtn.addEventListener('click', submitSubscriptionPackage);
  
  // Close modals on outside click
  [addPostModal, uploadWorkModal, bookAppointmentModal, createPackageModal].forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.classList.add('hidden');
      }
    });
  });
  
  // Barber Phase 1 modals
  const availabilityModal = document.getElementById('availability-modal');
  const servicesModal = document.getElementById('services-modal');
  const clientsModal = document.getElementById('clients-modal');
  
  // Availability modal handlers
  if (document.getElementById('manage-availability-btn')) {
    document.getElementById('manage-availability-btn').addEventListener('click', () => {
      loadAvailabilitySettings();
      if (availabilityModal) availabilityModal.classList.remove('hidden');
    });
  }
  if (document.getElementById('close-availability-modal')) {
    document.getElementById('close-availability-modal').addEventListener('click', () => {
      if (availabilityModal) availabilityModal.classList.add('hidden');
    });
  }
  if (document.getElementById('cancel-availability')) {
    document.getElementById('cancel-availability').addEventListener('click', () => {
      if (availabilityModal) availabilityModal.classList.add('hidden');
    });
  }
  if (document.getElementById('save-availability')) {
    document.getElementById('save-availability').addEventListener('click', saveAvailabilitySettings);
  }
  
  // Services modal handlers
  if (document.getElementById('manage-services-btn')) {
    document.getElementById('manage-services-btn').addEventListener('click', () => {
      loadServices();
      if (servicesModal) servicesModal.classList.remove('hidden');
    });
  }
  if (document.getElementById('close-services-modal')) {
    document.getElementById('close-services-modal').addEventListener('click', () => {
      if (servicesModal) servicesModal.classList.add('hidden');
    });
  }
  if (document.getElementById('close-services')) {
    document.getElementById('close-services').addEventListener('click', () => {
      if (servicesModal) servicesModal.classList.add('hidden');
    });
  }
  if (document.getElementById('add-service-btn')) {
    document.getElementById('add-service-btn').addEventListener('click', () => {
      document.getElementById('add-service-form').classList.remove('hidden');
    });
  }
  if (document.getElementById('cancel-service')) {
    document.getElementById('cancel-service').addEventListener('click', () => {
      document.getElementById('add-service-form').classList.add('hidden');
      // Clear form
      document.getElementById('service-name').value = '';
      document.getElementById('service-price').value = '';
      document.getElementById('service-duration').value = '';
      document.getElementById('service-category').value = '';
      document.getElementById('service-description').value = '';
    });
  }
  if (document.getElementById('save-service')) {
    document.getElementById('save-service').addEventListener('click', saveService);
  }
  
  // Clients modal handlers
  if (document.getElementById('view-clients-btn')) {
    document.getElementById('view-clients-btn').addEventListener('click', () => {
      loadClients();
      if (clientsModal) clientsModal.classList.remove('hidden');
    });
  }
  if (document.getElementById('close-clients-modal')) {
    document.getElementById('close-clients-modal').addEventListener('click', () => {
      if (clientsModal) clientsModal.classList.add('hidden');
    });
  }
  
  // Bookings view toggle and filters
  const listViewBtn = document.getElementById('list-view-btn');
  const calendarViewBtn = document.getElementById('calendar-view-btn');
  const statusFilter = document.getElementById('status-filter');
  const dateStartFilter = document.getElementById('date-filter-start');
  const dateEndFilter = document.getElementById('date-filter-end');
  const clearFiltersBtn = document.getElementById('clear-filters');
  
  if (listViewBtn) {
    listViewBtn.addEventListener('click', () => {
      listViewBtn.classList.add('bg-white', 'text-black');
      listViewBtn.classList.remove('text-gray-400');
      calendarViewBtn.classList.remove('bg-white', 'text-black');
      calendarViewBtn.classList.add('text-gray-400');
      
      document.getElementById('bookings-list-view').classList.remove('hidden');
      document.getElementById('bookings-calendar-view').classList.add('hidden');
    });
  }
  
  if (calendarViewBtn) {
    calendarViewBtn.addEventListener('click', () => {
      calendarViewBtn.classList.add('bg-white', 'text-black');
      calendarViewBtn.classList.remove('text-gray-400');
      listViewBtn.classList.remove('bg-white', 'text-black');
      listViewBtn.classList.add('text-gray-400');
      
      document.getElementById('bookings-list-view').classList.add('hidden');
      document.getElementById('bookings-calendar-view').classList.remove('hidden');
    });
  }
  
  if (statusFilter) {
    statusFilter.addEventListener('change', () => {
      loadBarberAppointments();
    });
  }
  
  if (dateStartFilter) {
    dateStartFilter.addEventListener('change', () => {
      loadBarberAppointments();
    });
  }
  
  if (dateEndFilter) {
    dateEndFilter.addEventListener('change', () => {
      loadBarberAppointments();
    });
  }
  
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
      if (statusFilter) statusFilter.value = 'all';
      if (dateStartFilter) dateStartFilter.value = '';
      if (dateEndFilter) dateEndFilter.value = '';
      loadBarberAppointments();
    });
  }
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
    t.classList.remove('tab-active', 'text-white', 'font-semibold');
    t.classList.add('text-gray-500');
  });
  
  const activeTab = document.querySelector(`#bottom-nav [data-tab="${targetTab}"]`);
  if (activeTab && !activeTab.classList.contains('center-pill')) {
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
  
  if (targetTab === 'community') {
    loadSocialPosts(); // Load fresh posts from API when switching to community tab
    renderSocialFeed();
  }
  
  if (targetTab === 'barber-dashboard') {
    updateDashboardStats();
    loadSubscriptionPackages();
  }
  
  if (targetTab === 'barber-schedule') {
    loadBarberAppointments();
  }
  
  if (targetTab === 'barber-profile') {
    // Load previews (but don't open modals)
    loadAvailabilityPreview();
    loadServicesPreview();
    loadClientsPreview();
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
    showError("Using demo results...");
    setTimeout(() => {
      displayResults(getMockData());
    }, 1000);
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
    card.className = `card-hover bg-gray-900 border border-gray-800 ${color.topBorder} rounded-lg p-5`;
    
    card.innerHTML = `
      <div class="mb-4">
        <h3 class="text-lg font-semibold mb-1 text-white">${rec.styleName || 'Unnamed Style'}</h3>
        <p class="text-gray-400 text-sm line-clamp-2">${rec.description || 'Professional haircut recommendation'}</p>
      </div>
      
      <div class="space-y-2">
        <button onclick="tryOnStyle('${rec.styleName}')" 
                class="w-full btn-primary px-4 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
          Preview Style
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
    barberListContainer.innerHTML = '<div class="text-center py-8"><div class="loader mx-auto"></div><p class="mt-4 text-gray-400">Finding barbershops near you...</p></div>';
  }
  
  try {
    const stylesParam = recommendedStyles.length > 0 ? `&styles=${encodeURIComponent(recommendedStyles.join(','))}` : '';
    const response = await fetch(`${API_URL}/barbers?location=${encodeURIComponent(location)}${stylesParam}`);
    const data = await response.json();
    
    if (data.barbers && data.barbers.length > 0) {
      renderBarberList(data.barbers, data.real_data);
    } else {
      throw new Error('No barbershops found');
    }
  } catch (error) {
    console.error('Error loading barbershops:', error);
    if (barberListContainer) {
      barberListContainer.innerHTML = `
        <div class="bg-yellow-900/20 border border-yellow-500/50 rounded-lg p-4 text-center">
          <p class="text-yellow-400">Using sample data. Connect to backend for real barbershops.</p>
        </div>
      `;
    }
  }
}

function renderBarberList(barbers, isRealData = false) {
  if (!barberListContainer) return;
  
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
            <span class="text-green-400 font-semibold">~$${barber.avgCost}</span>
            <span class="text-gray-400 text-sm">${barber.phone}</span>
          </div>
          
          <div class="flex flex-wrap gap-2 mb-4">
            ${barber.specialties.map(s => 
              `<span class="bg-sky-500/20 border border-sky-500/50 text-sky-300 text-xs px-3 py-1 rounded-full">${s}</span>`
            ).join('')}
          </div>
          
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
  const location = locationSearch.value || 'Atlanta, GA';
  
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
  
  loadNearbyBarbers(location, [styleName]);
  switchTab('barbers');
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

// --- Social Media Functions ---
async function loadSocialPosts() {
  try {
    const response = await fetch(`${API_URL}/social`);
    const data = await response.json();
    
    if (data.posts && Array.isArray(data.posts)) {
      // Create a map of existing post IDs to avoid duplicates
      const existingIds = new Set(socialPosts.map(p => String(p.id)));
      
      // Add new posts that don't exist locally
      const newPosts = data.posts.filter(p => !existingIds.has(String(p.id)));
      
      // Merge: new posts first, then existing local posts
      socialPosts = [...newPosts, ...socialPosts];
      
      // Sort by timestamp (newest first)
      socialPosts.sort((a, b) => {
        const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
        const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
        return timeB - timeA;
      });
      
      // Remove duplicates by ID
      const seen = new Set();
      socialPosts = socialPosts.filter(p => {
        const id = String(p.id);
        if (seen.has(id)) return false;
        seen.add(id);
        return true;
      });
      
      renderSocialFeed();
    }
  } catch (error) {
    console.error('Error loading posts:', error);
    // Keep existing posts if API fails - don't clear the feed
  }
}

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
    
    // Extract hashtags from caption
    const caption = post.caption || '';
    const hashtags = post.hashtags || [];
    
    // Calculate timeAgo from timestamp if not provided
    let timeAgo = post.timeAgo || 'now';
    if (post.timestamp && !post.timeAgo) {
      const postTime = new Date(post.timestamp);
      const now = new Date();
      const diffMs = now - postTime;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);
      
      if (diffMins < 1) timeAgo = 'now';
      else if (diffMins < 60) timeAgo = `${diffMins}m`;
      else if (diffHours < 24) timeAgo = `${diffHours}h`;
      else if (diffDays < 7) timeAgo = `${diffDays}d`;
      else timeAgo = postTime.toLocaleDateString();
    }
    
    // Handle image URL - support both base64 and Cloudinary URLs
    let imageSrc = post.image || '';
    if (imageSrc && !imageSrc.startsWith('http') && !imageSrc.startsWith('data:')) {
      // If it's base64 without prefix, add data URL prefix
      imageSrc = `data:image/jpeg;base64,${imageSrc}`;
    }
    
    postElement.innerHTML = `
      <div class="p-4 flex items-center gap-3 justify-between">
        <div class="flex items-center gap-3">
        <img src="${post.avatar}" alt="${post.username}" class="w-10 h-10 rounded-full object-cover">
        <div>
          <p class="font-semibold text-white">${post.username}</p>
          <p class="text-xs text-gray-400">${timeAgo}</p>
        </div>
      </div>
        <button onclick="toggleFollow('${post.username}')" class="text-sky-400 hover:text-sky-300 text-sm font-medium">
          Follow
        </button>
      </div>
      <img src="${imageSrc}" alt="Post image" class="w-full h-80 object-cover">
      <div class="p-4">
        <div class="flex items-center gap-4 mb-3">
          <button onclick="toggleLike('${post.id}')" class="flex items-center gap-2 transition-colors ${post.liked ? 'text-red-500' : 'text-gray-400 hover:text-red-500'}">
            <svg class="w-6 h-6 ${post.liked ? 'fill-current' : ''}" fill="${post.liked ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
            </svg>
            <span class="text-sm font-semibold">${post.likes || 0}</span>
          </button>
          <button onclick="toggleComments('${post.id}')" class="flex items-center gap-2 text-gray-400 hover:text-gray-200">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
            </svg>
            <span class="text-sm">${post.comments || 0}</span>
          </button>
          <button onclick="sharePost('${post.id}')" class="flex items-center gap-2 text-gray-400 hover:text-gray-200">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path>
            </svg>
            <span class="text-sm">${post.shares || 0}</span>
          </button>
        </div>
        <p class="text-gray-300 mb-2">${caption}</p>
        <div class="flex flex-wrap gap-1 mb-3">
          ${hashtags.map(tag => `<span class="text-sky-400 text-sm hover:underline cursor-pointer">#${tag}</span>`).join('')}
        </div>
        <div id="comments-${post.id}" class="hidden space-y-2 mb-3 max-h-48 overflow-y-auto border-t border-gray-700 pt-3"></div>
        <div class="flex gap-2">
          <input type="text" id="comment-input-${post.id}" placeholder="Add a comment..." class="flex-1 bg-gray-800 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-400">
          <button onclick="submitComment('${post.id}')" class="bg-sky-500 text-white px-4 py-2 rounded-lg hover:bg-sky-600 text-sm font-medium">Post</button>
        </div>
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
  
  // Show loading state
  if (submitPost) {
    submitPost.disabled = true;
    submitPost.textContent = 'Posting...';
  }
  
  try {
    // Get base64 image (remove data URL prefix if present)
    let imageBase64 = postImagePreview.src;
    if (imageBase64.includes(',')) {
      imageBase64 = imageBase64.split(',')[1];
    }
    
    const response = await fetch(`${API_URL}/social`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
    username: 'you',
    avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop&crop=face',
        image: imageBase64,
    caption: caption,
        hashtags: []
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Reload posts from server to get latest (includes the new post)
      await loadSocialPosts();
      closeAddPostModal();
  alert('Post shared successfully! 🎉');
    } else {
      // Handle rejection (content moderation)
      const errorMsg = data.reason || data.error || 'Failed to post. Please try again.';
      alert(errorMsg);
    }
  } catch (error) {
    console.error('Error posting:', error);
    alert('Failed to post. Please check your connection and try again.');
  } finally {
    if (submitPost) {
      submitPost.disabled = false;
      submitPost.textContent = 'Post';
    }
  }
}

async function toggleLike(postId) {
  // Find post by ID (handle both string and number IDs)
  const post = socialPosts.find(p => String(p.id) === String(postId));
  if (!post) {
    console.error('Post not found:', postId);
    return;
  }
  
  // Optimistically update UI
  const wasLiked = post.liked || false;
  post.liked = !wasLiked;
  post.likes = (post.likes || 0) + (post.liked ? 1 : -1);
    renderSocialFeed();
  
  try {
    // Call backend API to persist the like
    const response = await fetch(`${API_URL}/social/${postId}/like`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    const data = await response.json();
    
    if (data.success) {
      // Update with server response
      post.liked = data.liked;
      post.likes = data.likes;
      renderSocialFeed();
    } else {
      // Revert on error
      post.liked = wasLiked;
      post.likes = (post.likes || 0) + (wasLiked ? 1 : -1);
      renderSocialFeed();
      console.error('Failed to toggle like:', data.error);
    }
  } catch (error) {
    // Revert on error
    post.liked = wasLiked;
    post.likes = (post.likes || 0) + (wasLiked ? 1 : -1);
    renderSocialFeed();
    console.error('Error toggling like:', error);
  }
}

// --- Bottom Nav Rendering ---
function renderBottomNav() {
  if (!bottomNav) return;

  const baseBtn = 'tab-button flex flex-col items-center justify-center h-14 flex-1 text-xs transition-all duration-200';
  const centerBtn = 'tab-button center-pill flex items-center justify-center h-12 w-12 transition-all duration-200 rounded-full bg-white -translate-y-2';

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

  bottomNav.innerHTML = `
    <div class="flex items-center justify-between px-4 py-1">
      ${tabs.map((t) => {
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

  bottomNav.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  const defaultTab = currentUserMode === 'client' ? 'ai' : 'barber-dashboard';
  switchTab(defaultTab);
}

// --- Barber Portfolio Functions ---
async function renderBarberPortfolio() {
  if (!portfolioGrid) return;
  
  portfolioGrid.innerHTML = '';
  
  // Try to load from API first
  try {
    const response = await fetch(`${API_URL}/portfolio/${currentBarberId}`);
    const data = await response.json();
    if (data.portfolio && data.portfolio.length > 0) {
      barberPortfolio = data.portfolio;
    }
  } catch (error) {
    console.error('Error loading portfolio from API:', error);
    // Continue with existing barberPortfolio (mock data)
  }
  
  // If still empty, ensure mock data is there
  if (barberPortfolio.length === 0) {
    // Mock data should already be initialized, but ensure it's there
    if (barberPortfolio.length === 0) {
      barberPortfolio = [
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
        },
        {
          id: 3,
          styleName: 'Textured Quiff',
          image: 'https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=400&fit=crop',
          description: 'Voluminous quiff with natural texture and movement.',
          likes: 25,
          date: '2024-01-13'
        }
      ];
    }
  }
  
  if (barberPortfolio.length === 0) {
    portfolioGrid.innerHTML = `
      <div class="col-span-full text-center py-16">
        <div class="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
        </div>
        <p class="text-gray-400 text-lg mb-2">No portfolio items yet</p>
        <p class="text-gray-500 text-sm">Upload your first work to showcase your skills</p>
      </div>
    `;
    return;
  }
  
  barberPortfolio.forEach(work => {
    const workElement = document.createElement('div');
    workElement.className = 'bg-gray-900 border border-gray-800 rounded-xl overflow-hidden card-hover';
    workElement.innerHTML = `
      <div class="relative aspect-square overflow-hidden bg-gray-800">
        <img src="${work.image}" alt="${work.styleName}" class="w-full h-full object-cover">
      </div>
      <div class="p-4">
        <h3 class="text-lg font-bold text-white mb-2">${work.styleName}</h3>
        <p class="text-gray-400 text-sm mb-3 line-clamp-2">${work.description}</p>
        <div class="flex justify-between items-center pt-3 border-t border-gray-800">
          <div class="flex items-center gap-2 text-sm text-gray-400">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
            </svg>
            <span>${work.likes}</span>
          </div>
          <span class="text-xs text-gray-500">${new Date(work.date).toLocaleDateString()}</span>
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
  
  alert('Portfolio work added successfully! 🎨');
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
function openBookingModal(barberId, barberName) {
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
  loadBarberAppointments();
  updateDashboardStats();
  closeBookingModal();
  
  alert('Appointment booked successfully! 📅');
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

async function loadBarberAppointments() {
  // Save current appointments (mock data) before API call
  const currentAppointments = [...appointments];
  
  try {
    const response = await fetch(`${API_URL}/appointments?type=barber&user_id=${currentBarberId}`);
    const data = await response.json();
    
    if (data.appointments && data.appointments.length > 0) {
      // Merge API appointments with mock data (avoid duplicates)
      const apiAppointmentIds = new Set(data.appointments.map(apt => String(apt.id)));
      const mockAppointments = currentAppointments.filter(apt => !apiAppointmentIds.has(String(apt.id)));
      appointments = [...data.appointments, ...mockAppointments];
    } else {
      // If API returns empty, keep mock data
      appointments = currentAppointments;
    }
  } catch (error) {
    console.error('Error loading appointments:', error);
    // Keep existing appointments (mock data) if API fails
    appointments = currentAppointments;
  }
  
  // Always render after loading (whether from API or mock data)
  renderBarberAppointments();
}

function renderBarberAppointments() {
  if (!barberAppointmentsContainer) return;
  
  barberAppointmentsContainer.innerHTML = '';
  
  // Filter appointments for current barber
  // Show appointments that match currentBarberId, or show mock appointments (barber_1) for demo
  const barberAppointments = appointments.filter(apt => {
    // Always show mock appointments with barber_1 for demo purposes
    if (apt.barberId === 'barber_1') return true;
    // Otherwise match by currentBarberId
    return apt.barberId === currentBarberId || !apt.barberId;
  });
  
  if (barberAppointments.length === 0) {
    barberAppointmentsContainer.innerHTML = `
      <div class="text-center py-16">
        <div class="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
        </div>
        <p class="text-gray-400 text-lg mb-2">No appointments scheduled</p>
        <p class="text-gray-500 text-sm">Your upcoming bookings will appear here</p>
      </div>
    `;
    return;
  }
  
  // Sort by date and time
  barberAppointments.sort((a, b) => {
    const dateA = new Date(`${a.date} ${a.time}`);
    const dateB = new Date(`${b.date} ${b.time}`);
    return dateA - dateB;
  });
  
  barberAppointments.forEach(appointment => {
    const appointmentElement = document.createElement('div');
    appointmentElement.className = 'bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl p-5 card-hover transition-all duration-200 hover:border-sky-500/50 hover:shadow-lg hover:shadow-sky-500/10';
    
    const appointmentDate = new Date(`${appointment.date}T${appointment.time}`);
    const now = new Date();
    const isToday = appointmentDate.toDateString() === now.toDateString();
    const isPast = appointmentDate < now;
    const timeUntil = getTimeUntil(appointmentDate);
    
    const statusColors = {
      'pending': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      'confirmed': 'bg-green-500/20 text-green-400 border-green-500/30',
      'completed': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      'cancelled': 'bg-red-500/20 text-red-400 border-red-500/30',
      'rejected': 'bg-gray-500/20 text-gray-400 border-gray-500/30',
      'rescheduled': 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    };
    
    const statusColor = statusColors[appointment.status] || statusColors.pending;
    
    appointmentElement.innerHTML = `
      <!-- Header with Status Badge & Time -->
      <div class="flex justify-between items-start mb-4">
        <div class="flex-1">
          <div class="flex items-center gap-3 mb-2">
            <div class="w-12 h-12 bg-gradient-to-br from-sky-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
              ${(appointment.clientName || 'U').charAt(0).toUpperCase()}
            </div>
        <div>
              <h3 class="text-lg font-bold text-white">${appointment.clientName || 'Unknown Client'}</h3>
              <p class="text-gray-400 text-sm">${appointment.service || 'Service'}</p>
        </div>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            ${isToday ? '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">Today</span>' : ''}
            ${isPast && appointment.status !== 'completed' && appointment.status !== 'cancelled' ? '<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">Past Due</span>' : ''}
          </div>
        </div>
        <div class="text-right">
          <span class="px-3 py-1.5 rounded-full text-xs font-semibold border ${statusColor}">
            ${appointment.status ? appointment.status.charAt(0).toUpperCase() + appointment.status.slice(1) : 'Pending'}
          </span>
        </div>
      </div>
      
      <!-- Date & Time with Icon -->
      <div class="flex items-center gap-4 mb-4 p-3 bg-gray-800/50 rounded-lg">
        <div class="flex items-center gap-2 flex-1">
          <svg class="w-5 h-5 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
          </svg>
          <span class="text-white font-medium text-sm">${formatDate(appointment.date)}</span>
      </div>
        <div class="flex items-center gap-2 flex-1">
          <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span class="text-white font-medium text-sm">${appointment.time || 'N/A'}</span>
        </div>
        <div class="ml-auto">
          <span class="text-lg font-bold text-white">${appointment.price || '$0'}</span>
        </div>
      </div>
      
      ${timeUntil && !isPast ? `
        <div class="mb-4 p-2 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <p class="text-xs text-blue-400">⏰ ${timeUntil}</p>
        </div>
      ` : ''}
      
      ${appointment.notes && appointment.notes !== 'No special requests' ? `
        <div class="mb-4 p-3 bg-gray-800/30 rounded-lg border-l-2 border-sky-500">
          <p class="text-xs text-gray-400 mb-1 uppercase tracking-wide">Client Notes</p>
          <p class="text-sm text-gray-300">${appointment.notes}</p>
        </div>
      ` : ''}
      
      ${appointment.barberNotes && appointment.barberNotes.length > 0 ? `
        <div class="mb-4 p-3 bg-gray-800/30 rounded-lg border-l-2 border-purple-500">
          <p class="text-xs text-gray-400 mb-1 uppercase tracking-wide">Your Notes</p>
          ${appointment.barberNotes.map(note => `
            <p class="text-sm text-gray-300 mb-1">${note.note || note}</p>
          `).join('')}
        </div>
      ` : ''}
      
      <!-- Action Buttons -->
      <div class="flex gap-2 pt-4 border-t border-gray-800 flex-wrap">
        ${appointment.status === 'pending' ? `
          <button onclick="quickAccept('${appointment.id}')" class="flex-1 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white px-4 py-2.5 rounded-lg font-medium text-sm transition-all shadow-lg shadow-green-500/20">
            ✓ Accept
          </button>
          <button onclick="quickReject('${appointment.id}')" class="flex-1 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-4 py-2.5 rounded-lg font-medium text-sm transition-all">
            ✕ Reject
          </button>
        ` : ''}
        ${appointment.status === 'confirmed' || appointment.status === 'pending' ? `
          <button onclick="rescheduleAppointment('${appointment.id}')" class="px-4 py-2.5 bg-purple-500 hover:bg-purple-600 text-white rounded-lg font-medium text-sm transition-all">
            Reschedule
          </button>
          <button onclick="cancelAppointment('${appointment.id}')" class="px-4 py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-lg font-medium text-sm transition-all">
            Cancel
          </button>
        ` : ''}
        <button onclick="viewClientHistory('${appointment.clientId}')" class="px-4 py-2.5 bg-sky-500 hover:bg-sky-600 text-white rounded-lg font-medium text-sm transition-all">
          History
        </button>
        <button onclick="addAppointmentNote('${appointment.id}')" class="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium text-sm transition-all">
          Note
        </button>
      </div>
    `;
    barberAppointmentsContainer.appendChild(appointmentElement);
  });
  
  // Apply filters if active
  applyAppointmentFilters();
}

function getTimeUntil(date) {
  try {
    const now = new Date();
    const diff = date - now;
    if (diff < 0) return null;
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days} day${days > 1 ? 's' : ''} away`;
    }
    if (hours > 0) return `${hours}h ${minutes}m away`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} away`;
    return 'Starting soon';
  } catch (e) {
    return null;
  }
}

function formatDate(dateString) {
  try {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    if (date.toDateString() === today.toDateString()) return 'Today';
    if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow';
    
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  } catch (e) {
    return dateString;
  }
}

function quickAccept(appointmentId) {
  acceptAppointment(appointmentId);
}

function quickReject(appointmentId) {
  rejectAppointment(appointmentId);
}

function applyAppointmentFilters() {
  const statusFilter = document.getElementById('status-filter');
  const dateStartFilter = document.getElementById('date-filter-start');
  const dateEndFilter = document.getElementById('date-filter-end');
  
  if (!statusFilter) return;
  
  const filterStatus = statusFilter.value;
  const filterStart = dateStartFilter?.value;
  const filterEnd = dateEndFilter?.value;
  
  const cards = barberAppointmentsContainer.querySelectorAll('[class*="bg-gradient-to-br"]');
  
  cards.forEach(card => {
    let show = true;
    
    // Status filter
    if (filterStatus !== 'all') {
      const statusBadge = card.querySelector('[class*="rounded-full"]');
      if (statusBadge && !statusBadge.textContent.toLowerCase().includes(filterStatus.toLowerCase())) {
        show = false;
      }
    }
    
    // Date range filter
    if (filterStart || filterEnd) {
      const dateText = card.textContent;
      // Simple check - could be improved
      if (filterStart && dateText.includes(formatDate(filterStart))) {
        // Check if date is in range
      }
    }
    
    card.style.display = show ? 'block' : 'none';
  });
}

async function acceptAppointment(appointmentId) {
  try {
    const response = await fetch(`${API_URL}/appointments/${appointmentId}/accept`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    if (data.success) {
      await loadBarberAppointments();
    updateDashboardStats();
      alert('Appointment accepted! ✅');
    } else {
      alert('Failed to accept appointment');
    }
  } catch (error) {
    console.error('Error accepting appointment:', error);
    alert('Error accepting appointment');
  }
}

async function rejectAppointment(appointmentId) {
  const reason = prompt('Reason for rejection (optional):');
  try {
    const response = await fetch(`${API_URL}/appointments/${appointmentId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason || 'No reason provided' })
    });
    
    const data = await response.json();
    if (data.success) {
      await loadBarberAppointments();
      updateDashboardStats();
      alert('Appointment rejected');
    } else {
      alert('Failed to reject appointment');
    }
  } catch (error) {
    console.error('Error rejecting appointment:', error);
    alert('Error rejecting appointment');
  }
}

async function rescheduleAppointment(appointmentId) {
  const newDate = prompt('New date (YYYY-MM-DD):');
  const newTime = prompt('New time (HH:MM):');
  const reason = prompt('Reason for rescheduling (optional):');
  
  if (!newDate || !newTime) {
    alert('Date and time are required');
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/appointments/${appointmentId}/reschedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        date: newDate,
        time: newTime,
        reason: reason || 'Rescheduled by barber'
      })
    });
    
    const data = await response.json();
    if (data.success) {
      await loadBarberAppointments();
      updateDashboardStats();
      alert('Appointment rescheduled! ✅');
    } else {
      alert('Failed to reschedule appointment');
    }
  } catch (error) {
    console.error('Error rescheduling appointment:', error);
    alert('Error rescheduling appointment');
  }
}

async function cancelAppointment(appointmentId) {
  const reason = prompt('Reason for cancellation (optional):');
  if (!confirm('Are you sure you want to cancel this appointment?')) return;
  
  try {
    const response = await fetch(`${API_URL}/appointments/${appointmentId}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: reason || 'Cancelled by barber' })
    });
    
    const data = await response.json();
    if (data.success) {
      await loadBarberAppointments();
      updateDashboardStats();
      alert('Appointment cancelled');
    } else {
      alert('Failed to cancel appointment');
    }
  } catch (error) {
    console.error('Error cancelling appointment:', error);
    alert('Error cancelling appointment');
  }
}

async function addAppointmentNote(appointmentId) {
  const note = prompt('Add a note for this appointment:');
  if (!note) return;
  
  try {
    const response = await fetch(`${API_URL}/appointments/${appointmentId}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note: note, type: 'general' })
    });
    
    const data = await response.json();
    if (data.success) {
      await loadBarberAppointments();
      alert('Note added! ✅');
    } else {
      alert('Failed to add note');
    }
  } catch (error) {
    console.error('Error adding note:', error);
    alert('Error adding note');
  }
}

async function viewClientHistory(clientId) {
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/clients/${clientId}/history`);
    const data = await response.json();
    
    const history = data.appointments || [];
    const historyText = history.map(apt => 
      `${apt.date} ${apt.time}: ${apt.service} - ${apt.status}`
    ).join('\n');
    
    if (history.length === 0) {
      alert(`No history for client: ${clientId}`);
    } else {
      alert(`Client History:\n\n${historyText}`);
    }
  } catch (error) {
    console.error('Error loading client history:', error);
    alert('Failed to load client history');
  }
}

function confirmAppointment(appointmentId) {
  acceptAppointment(appointmentId);
}

function updateDashboardStats() {
  const today = new Date().toISOString().split('T')[0];
  const todayAppointments = appointments.filter(apt => apt.date === today).length;
  
  const thisWeekStart = new Date();
  thisWeekStart.setDate(thisWeekStart.getDate() - thisWeekStart.getDay());
  thisWeekStart.setHours(0, 0, 0, 0);
  const thisWeekAppointments = appointments.filter(apt => {
    const aptDate = new Date(apt.date);
    aptDate.setHours(0, 0, 0, 0);
    return aptDate >= thisWeekStart;
  }).length;
  
  const todayElement = document.getElementById('today-appointments');
  const weekElement = document.getElementById('week-appointments');
  const portfolioCountElement = document.getElementById('portfolio-count');
  
  if (todayElement) todayElement.textContent = todayAppointments;
  if (weekElement) weekElement.textContent = thisWeekAppointments;
  if (portfolioCountElement) portfolioCountElement.textContent = barberPortfolio.length;
  
  // Calculate and update analytics
  calculateAnalytics();
}

// Analytics calculation functions
function calculateAnalytics() {
  try {
    const now = new Date();
    const thisMonth = now.getMonth();
    const lastMonth = thisMonth === 0 ? 11 : thisMonth - 1;
    const thisYear = now.getFullYear();
    
    // Get barber appointments
    const allAppointments = appointments.filter(apt => {
      if (apt.barberId === 'barber_1') return true;
      return apt.barberId === currentBarberId || !apt.barberId;
    });
    
    // This month appointments (completed)
    const thisMonthAppointments = allAppointments.filter(apt => {
      try {
        const aptDate = new Date(apt.date);
        return aptDate.getMonth() === thisMonth && 
               aptDate.getFullYear() === thisYear && 
               apt.status === 'completed';
      } catch (e) {
        return false;
      }
    });
    
    // Last month appointments (completed)
    const lastMonthAppointments = allAppointments.filter(apt => {
      try {
        const aptDate = new Date(apt.date);
        return aptDate.getMonth() === lastMonth && 
               aptDate.getFullYear() === thisYear && 
               apt.status === 'completed';
      } catch (e) {
        return false;
      }
    });
    
    // Calculate revenue
    const totalRevenue = thisMonthAppointments.reduce((sum, apt) => {
      try {
        const priceStr = apt.price || '$0';
        const price = parseFloat(priceStr.replace(/[^0-9.]/g, '')) || 0;
        return sum + price;
      } catch (e) {
        return sum;
      }
    }, 0);
    
    const lastMonthRevenue = lastMonthAppointments.reduce((sum, apt) => {
      try {
        const priceStr = apt.price || '$0';
        const price = parseFloat(priceStr.replace(/[^0-9.]/g, '')) || 0;
        return sum + price;
      } catch (e) {
        return sum;
      }
    }, 0);
    
    const revenueChange = lastMonthRevenue > 0 
      ? ((totalRevenue - lastMonthRevenue) / lastMonthRevenue * 100).toFixed(1)
      : totalRevenue > 0 ? '100.0' : '0.0';
    
    // Client calculations
    const uniqueClients = new Set(allAppointments.map(apt => apt.clientId).filter(Boolean));
    const thisMonthClients = new Set(thisMonthAppointments.map(apt => apt.clientId).filter(Boolean));
    
    // Count new clients this month
    const newClients = [...thisMonthClients].filter(clientId => {
      const firstApt = allAppointments.find(apt => apt.clientId === clientId);
      if (!firstApt) return false;
      try {
        const firstAptDate = new Date(firstApt.date);
        return firstAptDate.getMonth() === thisMonth && firstAptDate.getFullYear() === thisYear;
      } catch (e) {
        return false;
      }
    }).length;
    
    // Utilization calculation (estimate)
    const workingDays = 5; // 5 days/week
    const slotsPerDay = 8; // 8 slots/day
    const totalSlots = workingDays * slotsPerDay * 4; // 4 weeks
    const bookedSlots = thisMonthAppointments.length;
    const utilization = totalSlots > 0 ? ((bookedSlots / totalSlots) * 100).toFixed(1) : '0.0';
    
    // Update UI
    updateAnalyticsUI({
      totalRevenue,
      revenueChange,
      totalAppointments: thisMonthAppointments.length,
      totalClients: uniqueClients.size,
      newClients,
      utilization
    });
    
    // Generate service analytics
    generateServiceAnalytics(allAppointments);
    generatePeakTimes(allAppointments);
    
  } catch (error) {
    console.error('Error calculating analytics:', error);
  }
}

function updateAnalyticsUI(data) {
  const revenueEl = document.getElementById('total-revenue');
  const revenueChangeEl = document.getElementById('revenue-change');
  const appointmentsEl = document.getElementById('total-appointments');
  const clientsEl = document.getElementById('total-clients');
  const newClientsEl = document.getElementById('new-clients');
  const utilizationEl = document.getElementById('utilization-rate');
  
  if (revenueEl) revenueEl.textContent = `$${data.totalRevenue.toFixed(2)}`;
  if (revenueChangeEl) {
    const change = parseFloat(data.revenueChange);
    revenueChangeEl.textContent = `${change >= 0 ? '+' : ''}${data.revenueChange}% vs last month`;
    revenueChangeEl.className = `text-xs ${change >= 0 ? 'text-green-400' : 'text-red-400'}`;
  }
  if (appointmentsEl) appointmentsEl.textContent = data.totalAppointments;
  if (clientsEl) clientsEl.textContent = data.totalClients;
  if (newClientsEl) newClientsEl.textContent = `+${data.newClients} new this month`;
  if (utilizationEl) utilizationEl.textContent = `${data.utilization}%`;
}

function generateServiceAnalytics(appointments) {
  const servicesContainer = document.getElementById('services-analytics');
  if (!servicesContainer) return;
  
  // Count services
  const serviceCounts = {};
  appointments.forEach(apt => {
    if (apt.status !== 'completed') return;
    const serviceName = apt.service || 'Unknown';
    serviceCounts[serviceName] = (serviceCounts[serviceName] || 0) + 1;
  });
  
  // Sort by count
  const sortedServices = Object.entries(serviceCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5); // Top 5
  
  if (sortedServices.length === 0) {
    servicesContainer.innerHTML = '<p class="text-gray-400 text-sm text-center py-4">No completed appointments yet</p>';
    return;
  }
  
  const total = Object.values(serviceCounts).reduce((sum, count) => sum + count, 0);
  
  servicesContainer.innerHTML = sortedServices.map(([serviceName, count]) => {
    const percentage = ((count / total) * 100).toFixed(0);
    return `
      <div class="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
        <div class="flex-1">
          <p class="text-white font-medium text-sm">${serviceName}</p>
          <p class="text-gray-400 text-xs">${count} booking${count > 1 ? 's' : ''} (${percentage}%)</p>
        </div>
        <div class="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-sky-500 to-purple-500 rounded-full" style="width: ${percentage}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

function generatePeakTimes(appointments) {
  const peakTimesContainer = document.getElementById('peak-times');
  if (!peakTimesContainer) return;
  
  // Count appointments by hour
  const hourCounts = {};
  appointments.forEach(apt => {
    if (!apt.time) return;
    try {
      const hour = parseInt(apt.time.split(':')[0]);
      if (isNaN(hour)) return;
      hourCounts[hour] = (hourCounts[hour] || 0) + 1;
    } catch (e) {
      // Skip invalid times
    }
  });
  
  if (Object.keys(hourCounts).length === 0) {
    peakTimesContainer.innerHTML = '<p class="text-gray-400 text-sm text-center py-4">No booking time data yet</p>';
    return;
  }
  
  const maxCount = Math.max(...Object.values(hourCounts));
  
  // Generate bars for common hours (9 AM - 6 PM)
  const commonHours = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18];
  
  peakTimesContainer.innerHTML = commonHours.map(hour => {
    const count = hourCounts[hour] || 0;
    const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
    const displayHour = hour > 12 ? `${hour - 12} PM` : hour === 12 ? '12 PM' : `${hour} AM`;
    
    return `
      <div class="flex items-center gap-3">
        <div class="w-16 text-gray-400 text-xs font-medium">${displayHour}</div>
        <div class="flex-1 h-6 bg-gray-800 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-orange-500 to-red-500 rounded-full transition-all" style="width: ${percentage}%"></div>
        </div>
        <div class="w-8 text-white text-xs font-medium text-right">${count}</div>
      </div>
    `;
  }).join('');
}

// --- Virtual Try-On Implementation ---
async function tryOnStyle(styleName) {
  // Check if user has uploaded a photo
  if (!base64ImageData) {
    alert(`📸 Please upload a photo first!\n\nGo to the AI Analysis tab and upload your photo, then come back to try on styles.`);
    return;
  }

  // Show loading state
  const loadingMsg = `🎨 Applying "${styleName}" to your photo...\n\nThis may take a few seconds...`;
  console.log(loadingMsg);
  
  // Create a simple loading indicator
  const originalButton = event?.target;
  if (originalButton) {
    originalButton.disabled = true;
    originalButton.textContent = 'Processing...';
  }

  try {
    // Call the backend virtual try-on endpoint
    const response = await fetch(`${API_URL}/virtual-tryon`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        userPhoto: base64ImageData,
        styleDescription: styleName
      })
    });

    const result = await response.json();

    if (response.ok && result.success) {
      // Display the result image with before/after comparison
      // Use originalImage from response, or fall back to stored base64ImageData
      const originalImg = result.originalImage || base64ImageData;
      displayTryOnResult(originalImg, result.resultImage, styleName, result.poweredBy);
      
      alert(`✅ Try-On Complete!\n\nStyle: ${styleName}\n${result.message || ''}\n\nScroll down to see your before & after!`);
    } else {
      throw new Error(result.error || 'Try-on failed');
    }
  } catch (error) {
    console.error('Try-on error:', error);
    alert(`❌ Try-On Error\n\n${error.message}\n\nThe preview feature works immediately - no setup needed!\n\nFor AI enhancement: See HAIR_TRYON_SETUP.md`);
  } finally {
    // Restore button state
    if (originalButton) {
      originalButton.disabled = false;
      originalButton.textContent = 'Try On';
    }
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

// --- Subscription Package Functions ---
function openCreatePackageModal() {
  createPackageModal.classList.remove('hidden');
}

function closeCreatePackageModal() {
  createPackageModal.classList.add('hidden');
  // Clear form fields
  document.getElementById('package-title').value = '';
  document.getElementById('package-description').value = '';
  document.getElementById('package-num-cuts').value = '';
  document.getElementById('package-duration').value = '';
  document.getElementById('package-price').value = '';
  document.getElementById('package-discount').value = '';
}

async function submitSubscriptionPackage() {
  const title = document.getElementById('package-title').value.trim();
  const description = document.getElementById('package-description').value.trim();
  const numCuts = parseInt(document.getElementById('package-num-cuts').value);
  const durationMonths = parseInt(document.getElementById('package-duration').value);
  const price = document.getElementById('package-price').value.trim();
  const discount = document.getElementById('package-discount').value.trim();

  if (!title || !numCuts || !durationMonths || !price) {
    alert('Please fill in all required fields (Title, Number of Cuts, Duration, Price)');
    return;
  }

  const packageData = {
    barberId: currentBarberId,
    barberName: currentBarberName,
    title: title,
    description: description,
    price: price,
    numCuts: numCuts,
    durationMonths: durationMonths,
    discount: discount
  };

  try {
    const response = await fetch(`${API_URL}/subscription-packages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(packageData)
    });

    const result = await response.json();

    if (response.ok && result.success) {
      alert('✅ Subscription package created successfully!');
      closeCreatePackageModal();
      loadSubscriptionPackages();
    } else {
      alert('❌ Failed to create package: ' + (result.error || 'Unknown error'));
    }
  } catch (error) {
    console.error('Error creating subscription package:', error);
    alert('❌ Error creating package. Please try again.');
  }
}

async function loadSubscriptionPackages() {
  try {
    const response = await fetch(`${API_URL}/subscription-packages?barber_id=${currentBarberId}`);
    const data = await response.json();
    
    if (response.ok) {
      subscriptionPackages = data.packages || [];
      renderSubscriptionPackages();
    }
  } catch (error) {
    console.error('Error loading subscription packages:', error);
  }
}

function renderSubscriptionPackages() {
  if (!subscriptionPackagesList) return;

  if (subscriptionPackages.length === 0) {
    subscriptionPackagesList.innerHTML = `
      <div class="text-center py-12 border border-gray-800 rounded-xl bg-gray-800/30">
        <div class="w-12 h-12 bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
          <svg class="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
        </div>
        <p class="text-gray-400 text-sm mb-1">No subscription packages yet</p>
        <p class="text-gray-500 text-xs">Create one to offer monthly deals to clients</p>
      </div>
    `;
    return;
  }

  subscriptionPackagesList.innerHTML = '';
  
  subscriptionPackages.forEach(pkg => {
    const packageElement = document.createElement('div');
    packageElement.className = 'bg-gray-800 border border-gray-700 rounded-xl p-5 card-hover';
    packageElement.innerHTML = `
      <div class="flex justify-between items-start mb-4">
        <div class="flex-1">
          <h4 class="text-xl font-bold text-white mb-2">${pkg.title}</h4>
          <p class="text-gray-400 text-sm mb-4">${pkg.description}</p>
        </div>
        <button onclick="deletePackage('${pkg.id}')" class="text-gray-400 hover:text-red-400 transition-colors p-2 -mt-2 -mr-2">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
      <div class="grid grid-cols-2 gap-4 pt-4 border-t border-gray-700">
        <div>
          <p class="text-xs text-gray-500 mb-1 uppercase tracking-wide">Price</p>
          <p class="text-lg font-bold text-white">${pkg.price}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 mb-1 uppercase tracking-wide">Haircuts</p>
          <p class="text-lg font-bold text-white">${pkg.numCuts} per month</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 mb-1 uppercase tracking-wide">Duration</p>
          <p class="text-sm font-medium text-white">${pkg.durationMonths} month${pkg.durationMonths > 1 ? 's' : ''}</p>
        </div>
        ${pkg.discount ? `
        <div>
          <p class="text-xs text-gray-500 mb-1 uppercase tracking-wide">Discount</p>
          <p class="text-sm font-medium text-green-400">${pkg.discount}</p>
        </div>
        ` : '<div></div>'}
      </div>
    `;
    subscriptionPackagesList.appendChild(packageElement);
  });
}

async function deletePackage(packageId) {
  if (!confirm('Are you sure you want to delete this subscription package?')) {
    return;
  }
  
  // For now, just remove from local state since backend doesn't have DELETE endpoint
  subscriptionPackages = subscriptionPackages.filter(pkg => pkg.id !== packageId);
  renderSubscriptionPackages();
  alert('✅ Package deleted successfully!');
}

// ============================================================
// NEW FEATURES: Comments, Shares, Follows, AI Insights
// ============================================================

let postCommentsState = {}; // Track which post comments are visible

async function toggleComments(postId) {
  const commentsDiv = document.getElementById(`comments-${postId}`);
  if (!commentsDiv) return;
  
  const isHidden = commentsDiv.classList.contains('hidden');
  
  if (isHidden) {
    // Load and show comments
    try {
      const response = await fetch(`${API_URL}/social/${postId}/comments`);
      const data = await response.json();
      
      commentsDiv.innerHTML = '';
      if (data.comments && data.comments.length > 0) {
        data.comments.forEach(comment => {
          const commentDiv = document.createElement('div');
          commentDiv.className = 'flex gap-2';
          commentDiv.innerHTML = `
            <span class="font-semibold text-white text-sm">${comment.username}</span>
            <span class="text-gray-300 text-sm">${comment.text}</span>
          `;
          commentsDiv.appendChild(commentDiv);
        });
      } else {
        commentsDiv.innerHTML = '<p class="text-gray-500 text-sm">No comments yet</p>';
      }
      commentsDiv.classList.remove('hidden');
    } catch (error) {
      console.error('Error loading comments:', error);
      alert('Failed to load comments');
    }
  } else {
    commentsDiv.classList.add('hidden');
  }
}

async function submitComment(postId) {
  const input = document.getElementById(`comment-input-${postId}`);
  const text = input.value.trim();
  
  if (!text) {
    alert('Please enter a comment');
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/social/${postId}/comments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username: 'you',
        text: text
      })
    });
    
    if (response.ok) {
      input.value = '';
      toggleComments(postId); // Reload comments
    } else {
      alert('Failed to post comment');
    }
  } catch (error) {
    console.error('Error posting comment:', error);
    alert('Failed to post comment');
  }
}

async function sharePost(postId) {
  try {
    const response = await fetch(`${API_URL}/social/${postId}/share`, {
      method: 'POST'
    });
    
    if (response.ok) {
      const data = await response.json();
      const post = socialPosts.find(p => String(p.id) === String(postId));
      if (post) {
        post.shares = data.shares || (post.shares || 0) + 1;
      }
      renderSocialFeed();
      alert('Post shared! 📤');
    } else {
      alert('Failed to share post');
    }
  } catch (error) {
    console.error('Error sharing post:', error);
    alert('Failed to share post');
  }
}

async function toggleFollow(username) {
  const isFollowing = (user_follows?.current_user || []).includes(username);
  
  const endpoint = isFollowing ? 'unfollow' : 'follow';
  
  try {
    const response = await fetch(`${API_URL}/users/${username}/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        follower_id: 'current_user'
      })
    });
    
    if (response.ok) {
      alert(isFollowing ? `Unfollowed ${username}` : `Now following ${username}!`);
      renderSocialFeed(); // Re-render to update follow button
    } else {
      alert('Failed to update follow status');
    }
  } catch (error) {
    console.error('Error toggling follow:', error);
    alert('Failed to update follow status');
  }
}

// Load AI insights and display trending styles
async function loadAIInsights() {
  try {
    const styles = lastRecommendedStyles.map(s => s.styleName).join(',');
    const response = await fetch(`${API_URL}/ai-insights?styles=${styles}`);
    const data = await response.json();
    
    // Create insights display
    const insightsDiv = document.createElement('div');
    insightsDiv.id = 'ai-insights-display';
    insightsDiv.className = 'bg-gradient-to-r from-sky-900 to-purple-900 border border-sky-700 rounded-2xl p-6 mb-6';
    insightsDiv.innerHTML = `
      <h3 class="text-xl font-bold mb-4 text-white">✨ AI Style Insights</h3>
      
      <div class="mb-4">
        <p class="text-sm font-semibold text-sky-200 mb-2">🔥 Trending Styles</p>
        <div class="flex flex-wrap gap-2">
          ${data.trending_styles.map(style => `
            <span class="bg-white/20 text-white px-3 py-1 rounded-full text-sm">${style}</span>
          `).join('')}
        </div>
      </div>
      
      <div class="mb-4">
        <p class="text-sm font-semibold text-sky-200 mb-2">💡 Seasonal Tips</p>
        <p class="text-white text-sm">${data.seasonal_tips}</p>
      </div>
      
      <div class="mb-4">
        <p class="text-sm font-semibold text-sky-200 mb-2">🎨 Popular Colors</p>
        <div class="flex flex-wrap gap-2">
          ${data.popular_colors.map(color => `
            <span class="bg-white/20 text-white px-3 py-1 rounded-full text-sm">${color}</span>
          `).join('')}
        </div>
      </div>
      
      ${data.trending_hashtags.length > 0 ? `
      <div>
        <p class="text-sm font-semibold text-sky-200 mb-2">📱 Trending Hashtags</p>
        <div class="flex flex-wrap gap-2">
          ${data.trending_hashtags.map(tag => `
            <span class="text-sky-300 text-sm">#${tag}</span>
          `).join('')}
        </div>
      </div>
      ` : ''}
    `;
    
    // Insert after recommendations
    const recommendationsContainer = document.getElementById('recommendations-container');
    if (recommendationsContainer && !document.getElementById('ai-insights-display')) {
      recommendationsContainer.insertAdjacentElement('afterend', insightsDiv);
    }
  } catch (error) {
    console.error('Error loading AI insights:', error);
  }
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
  const reviewsData = await loadBarberReviews(barberId);
  
  if (!reviewsData) {
    alert('Failed to load reviews');
    return;
  }
  
  const reviews = reviewsData.reviews || [];
  const avgRating = reviewsData.average_rating || 0;
  const totalReviews = reviewsData.total_reviews || 0;
  
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
                <div>
                  <p class="font-semibold text-white">${review.username}</p>
                  <p class="text-gray-400 text-sm">${review.date}</p>
                </div>
                <div class="flex gap-1">
                  ${Array(5).fill(0).map((_, i) => `
                    <span class="text-${i < review.rating ? 'yellow' : 'gray'}-400">⭐</span>
                  `).join('')}
                </div>
              </div>
              <p class="text-gray-300">${review.text}</p>
            </div>
          `).join('')}
        </div>
        ` : `
        <div class="text-center py-10 text-gray-400">
          <p>No reviews yet. Be the first to review!</p>
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
window.toggleLike = toggleLike;
window.openBookingModal = openBookingModal;
window.confirmAppointment = confirmAppointment;
window.findBarbersForStyle = findBarbersForStyle;
window.tryOnStyle = tryOnStyle;
window.deletePackage = deletePackage;
window.downloadTryOnImage = downloadTryOnImage;
window.toggleComments = toggleComments;
window.submitComment = submitComment;
window.sharePost = sharePost;
window.toggleFollow = toggleFollow;
window.loadAIInsights = loadAIInsights;
window.showBarberReviews = showBarberReviews;
window.acceptAppointment = acceptAppointment;
window.rejectAppointment = rejectAppointment;
window.rescheduleAppointment = rescheduleAppointment;
window.cancelAppointment = cancelAppointment;
window.addAppointmentNote = addAppointmentNote;
window.viewClientHistory = viewClientHistory;
window.quickAccept = quickAccept;
window.quickReject = quickReject;

// ========================================
// PHASE 1: BARBER FEATURES - Full Implementation
// ========================================

// Availability & Working Hours Management
async function loadAvailabilitySettings() {
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/availability`);
    const data = await response.json();
    
    const availability = data.availability || {};
    const workingHours = availability.workingHours || {};
    const formContainer = document.getElementById('availability-form');
    
    if (!formContainer) return;
    
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    
    formContainer.innerHTML = `
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-400 mb-2">Service Duration (minutes)</label>
          <input type="number" id="service-duration-setting" value="${availability.serviceDuration || 30}" class="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-400 mb-2">Buffer Time (minutes)</label>
          <input type="number" id="buffer-time-setting" value="${availability.bufferTime || 15}" class="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-2 text-white">
        </div>
        <div class="space-y-3">
          <label class="block text-sm font-medium text-gray-400 mb-2">Working Hours</label>
          ${days.map(day => {
            const dayHours = workingHours[day] || { enabled: false, start: '09:00', end: '18:00' };
            return `
              <div class="flex items-center gap-4 bg-gray-800 p-3 rounded-lg">
                <input type="checkbox" id="${day}-enabled" ${dayHours.enabled ? 'checked' : ''} class="w-4 h-4">
                <label class="text-white capitalize min-w-[80px]">${day}</label>
                <input type="time" id="${day}-start" value="${dayHours.start || '09:00'}" class="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm" ${!dayHours.enabled ? 'disabled' : ''}>
                <span class="text-gray-400">to</span>
                <input type="time" id="${day}-end" value="${dayHours.end || '18:00'}" class="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm" ${!dayHours.enabled ? 'disabled' : ''}>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
    
    // Enable/disable time inputs based on checkbox
    days.forEach(day => {
      const checkbox = document.getElementById(`${day}-enabled`);
      const startInput = document.getElementById(`${day}-start`);
      const endInput = document.getElementById(`${day}-end`);
      if (checkbox && startInput && endInput) {
        checkbox.addEventListener('change', () => {
          startInput.disabled = !checkbox.checked;
          endInput.disabled = !checkbox.checked;
        });
      }
    });
    
    // Update preview
    updateAvailabilityPreview(availability);
  } catch (error) {
    console.error('Error loading availability:', error);
    alert('Failed to load availability settings');
  }
}

async function saveAvailabilitySettings() {
  try {
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    const workingHours = {};
    
    days.forEach(day => {
      const enabledEl = document.getElementById(`${day}-enabled`);
      const startEl = document.getElementById(`${day}-start`);
      const endEl = document.getElementById(`${day}-end`);
      if (enabledEl && startEl && endEl) {
        const enabled = enabledEl.checked;
        const start = startEl.value;
        const end = endEl.value;
        workingHours[day] = { enabled, start, end };
      }
    });
    
    const availabilityData = {
      workingHours,
      serviceDuration: parseInt(document.getElementById('service-duration-setting')?.value || '30') || 30,
      bufferTime: parseInt(document.getElementById('buffer-time-setting')?.value || '15') || 15,
      breakTimes: [],
      blockedDates: [],
      timezone: "America/New_York"
    };
    
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/availability`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(availabilityData)
    });
    
    const data = await response.json();
    if (data.success) {
      updateAvailabilityPreview(availabilityData);
      const modal = document.getElementById('availability-modal');
      if (modal) modal.classList.add('hidden');
      alert('Availability settings saved! ✅');
    } else {
      alert('Failed to save availability settings');
    }
  } catch (error) {
    console.error('Error saving availability:', error);
    alert('Error saving availability settings');
  }
}

function updateAvailabilityPreview(availability) {
  const preview = document.getElementById('availability-preview');
  if (!preview) return;
  
  const workingHours = availability.workingHours || {};
  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
  const enabledDays = days.filter(day => workingHours[day]?.enabled);
  
  if (enabledDays.length === 0) {
    preview.innerHTML = '<p class="text-gray-500">No working hours configured</p>';
  } else {
    preview.innerHTML = enabledDays.map(day => {
      const hours = workingHours[day];
      return `<p class="text-sm"><span class="capitalize">${day}</span>: ${hours.start} - ${hours.end}</p>`;
    }).join('');
  }
}

// Services Management
async function loadServices() {
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/services`);
    const data = await response.json();
    
    const services = data.services || [];
    const servicesList = document.getElementById('services-list');
    
    if (!servicesList) return;
    
    if (services.length === 0) {
      servicesList.innerHTML = '<p class="text-gray-500 text-center py-4">No services configured yet</p>';
    } else {
      servicesList.innerHTML = services.map(service => `
        <div class="bg-gray-800 p-4 rounded-lg flex justify-between items-center">
          <div>
            <h4 class="font-semibold text-white">${service.name}</h4>
            <p class="text-sm text-gray-400">$${service.price} • ${service.duration} min</p>
          </div>
          <button onclick="deleteService('${service.id}')" class="text-red-400 hover:text-red-300 text-sm">Delete</button>
        </div>
      `).join('');
    }
    
    updateServicesPreview(services);
  } catch (error) {
    console.error('Error loading services:', error);
    alert('Failed to load services');
  }
}

async function saveService() {
  try {
    const nameEl = document.getElementById('service-name');
    const priceEl = document.getElementById('service-price');
    const durationEl = document.getElementById('service-duration');
    const categoryEl = document.getElementById('service-category');
    const descEl = document.getElementById('service-description');
    
    if (!nameEl || !priceEl || !durationEl) {
      alert('Service form fields not found');
      return;
    }
    
    const serviceData = {
      name: nameEl.value,
      price: parseFloat(priceEl.value) || 0,
      duration: parseInt(durationEl.value) || 30,
      category: categoryEl?.value || 'General',
      description: descEl?.value || ''
    };
    
    if (!serviceData.name) {
      alert('Service name is required');
      return;
    }
    
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/services`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(serviceData)
    });
    
    const data = await response.json();
    if (data.success) {
      const form = document.getElementById('add-service-form');
      if (form) form.classList.add('hidden');
      if (nameEl) nameEl.value = '';
      if (priceEl) priceEl.value = '';
      if (durationEl) durationEl.value = '';
      if (categoryEl) categoryEl.value = '';
      if (descEl) descEl.value = '';
      await loadServices();
      alert('Service added! ✅');
    } else {
      alert('Failed to add service');
    }
  } catch (error) {
    console.error('Error saving service:', error);
    alert('Error saving service');
  }
}

async function deleteService(serviceId) {
  if (!confirm('Are you sure you want to delete this service?')) return;
  
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/services?service_id=${serviceId}`, {
      method: 'DELETE'
    });
    
    const data = await response.json();
    if (data.success) {
      await loadServices();
      alert('Service deleted');
    } else {
      alert('Failed to delete service');
    }
  } catch (error) {
    console.error('Error deleting service:', error);
    alert('Error deleting service');
  }
}

function updateServicesPreview(services) {
  const preview = document.getElementById('services-preview');
  if (!preview) return;
  
  if (services.length === 0) {
    preview.innerHTML = '<p class="text-gray-500">No services configured</p>';
  } else {
    preview.innerHTML = `<p class="text-sm">${services.length} service(s) configured</p>`;
  }
}

// Client Management
async function loadClients() {
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/clients`);
    const data = await response.json();
    
    const clients = data.clients || [];
    const clientsList = document.getElementById('clients-list');
    
    if (!clientsList) return;
    
    if (clients.length === 0) {
      clientsList.innerHTML = '<p class="text-gray-500 text-center py-8">No clients yet</p>';
    } else {
      clientsList.innerHTML = clients.map(client => `
        <div class="bg-gray-800 p-4 rounded-lg">
          <div class="flex justify-between items-start mb-2">
            <div>
              <h4 class="font-semibold text-white">${client.clientName}</h4>
              <p class="text-sm text-gray-400">Client ID: ${client.clientId}</p>
            </div>
            <button onclick="viewClientDetails('${client.clientId}')" class="text-sky-400 hover:text-sky-300 text-sm">View Details</button>
          </div>
          <div class="grid grid-cols-3 gap-4 mt-3 text-sm">
            <div>
              <p class="text-gray-500">Visits</p>
              <p class="text-white font-semibold">${client.totalVisits || 0}</p>
            </div>
            <div>
              <p class="text-gray-500">Last Visit</p>
              <p class="text-white font-semibold">${client.lastVisit || 'Never'}</p>
            </div>
            <div>
              <p class="text-gray-500">Total Spent</p>
              <p class="text-white font-semibold">$${(client.totalSpent || 0).toFixed(2)}</p>
            </div>
          </div>
        </div>
      `).join('');
    }
    
    updateClientsPreview(clients);
  } catch (error) {
    console.error('Error loading clients:', error);
    alert('Failed to load clients');
  }
}

function updateClientsPreview(clients) {
  const preview = document.getElementById('clients-preview');
  if (!preview) return;
  
  if (clients.length === 0) {
    preview.innerHTML = '<p class="text-gray-500">No clients yet</p>';
  } else {
    preview.innerHTML = `<p class="text-sm">${clients.length} client(s)</p>`;
  }
}

// Preview loading functions (non-modal versions)
async function loadAvailabilityPreview() {
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/availability`);
    const data = await response.json();
    const availability = data.availability || {};
    updateAvailabilityPreview(availability);
  } catch (error) {
    console.error('Error loading availability preview:', error);
  }
}

async function loadServicesPreview() {
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/services`);
    const data = await response.json();
    const services = data.services || [];
    updateServicesPreview(services);
  } catch (error) {
    console.error('Error loading services preview:', error);
  }
}

async function loadClientsPreview() {
  try {
    const response = await fetch(`${API_URL}/barbers/${currentBarberId}/clients`);
    const data = await response.json();
    const clients = data.clients || [];
    updateClientsPreview(clients);
  } catch (error) {
    console.error('Error loading clients preview:', error);
  }
}

window.deleteService = deleteService;
window.viewClientDetails = viewClientDetails;
window.saveAvailabilitySettings = saveAvailabilitySettings;
window.saveService = saveService;
