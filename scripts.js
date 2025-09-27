// scripts.js - Frontend JavaScript for lineupai.onrender.com

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

// --- State ---
let base64ImageData = null;
let lastRecommendedStyles = [];

// --- BACKEND URL ---
const API_URL = 'https://lineup-fjpn.onrender.com';

// --- Mock Barbers ---
const atlantaBarbers = [
  { id: 1, name: 'Cuts by Clay', specialties: ['Fade', 'Taper'], rating: 4.9, avgCost: 45, location: 'Midtown' },
  { id: 2, name: 'The Buckhead Barber', specialties: ['Pompadour', 'Buzz Cut'], rating: 4.8, avgCost: 55, location: 'Buckhead' },
  { id: 3, name: 'Virginia-Highland Shears', specialties: ['Shag', 'Bob'], rating: 4.9, avgCost: 75, location: 'Virginia-Highland' }
];

// --- Initialize on Load ---
window.addEventListener('DOMContentLoaded', () => {
  console.log('LineUp AI initialized');
  console.log('Backend URL:', API_URL);
  renderBarberList(atlantaBarbers);
  testBackendConnection();
});

// Test backend connection
async function testBackendConnection() {
  try {
    const response = await fetch(`${API_URL}/health`);
    const data = await response.json();
    console.log('✅ Backend connected:', data);
  } catch (err) {
    console.log('⚠️ Backend may be sleeping (Render free tier). Will wake up on first request.');
  }
}

// --- Tabs ---
document.querySelectorAll('.tab-button').forEach(tab => {
  tab.addEventListener('click', () => {
    const targetTab = tab.dataset.tab;
    document.querySelectorAll('.tab-button').forEach(t => t.classList.remove('tab-active'));
    tab.classList.add('tab-active');
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
    document.getElementById(targetTab + '-tab-content').classList.remove('hidden');
  });
});

// --- Image Upload with Resizing ---
imageUploadArea.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = e => {
    // Create image to resize
    const img = new Image();
    img.onload = function() {
      // Create canvas for resizing
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      // Calculate new dimensions (max 800px)
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
      
      // Resize
      canvas.width = width;
      canvas.height = height;
      ctx.drawImage(img, 0, 0, width, height);
      
      // Get resized base64
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
});

// --- Reset UI ---
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

tryAgainButton.addEventListener('click', resetUI);
startOverButton.addEventListener('click', resetUI);

// --- Analysis ---
analyzeButton.addEventListener('click', async () => {
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

    console.log('Sending request to:', `${API_URL}/analyze`);

    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ payload })
    });

    console.log('Response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Error response:', errorText);
      throw new Error(`Server error: ${response.status}`);
    }

    const result = await response.json();
    console.log('Analysis complete:', result);

    if (result.error) {
      throw new Error(result.error);
    }

    displayResults(result);

  } catch (err) {
    console.error('Analysis error:', err);
    
    // If error, show message then display mock data
    showError("Using demo results while our servers wake up...");
    setTimeout(() => {
      displayResults(getMockData());
    }, 2000);
  } finally {
    loader.classList.add('hidden');
    statusMessage.textContent = '';
  }
});

// Mock data fallback
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
  
  // Auto-hide error after 3 seconds
  setTimeout(() => {
    errorContainer.classList.add('hidden');
  }, 3000);
}

// --- Display Results ---
function displayResults(data) {
  console.log('Displaying results...');
  
  statusSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');

  // --- Analysis Grid ---
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

  // --- Recommendations ---
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

// --- Barbers ---
findBarberButton.addEventListener('click', () => {
  barberIntro.textContent = "Top barbers matching your style:";
  const filteredBarbers = atlantaBarbers.filter(b => 
    b.specialties.some(s => lastRecommendedStyles.some(style => 
      style && style.toLowerCase().includes(s.toLowerCase())
    ))
  );
  renderBarberList(filteredBarbers.length > 0 ? filteredBarbers : atlantaBarbers);
  document.querySelector('.tab-button[data-tab="barbers"]').click();
});

function renderBarberList(barbers) {
  if (!barberListContainer) return;
  
  barberListContainer.innerHTML = '';
  barbers.forEach(barber => {
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4';
    card.innerHTML = `
      <div>
        <h4 class="text-xl font-bold text-white">${barber.name}</h4>
        <p class="text-sm text-gray-400">${barber.location}</p>
        <div class="flex items-center gap-4 mt-2">
          <span class="text-yellow-400 flex items-center gap-1">${barber.rating} ★</span>
          <span class="text-green-400 font-semibold">~$${barber.avgCost}</span>
        </div>
      </div>
      <div class="flex gap-2 mt-3 sm:mt-0">
        ${barber.specialties.map(s => 
          `<span class="bg-sky-500/20 border border-sky-500/50 text-sky-300 text-xs px-3 py-1 rounded-full">${s}</span>`
        ).join('')}
      </div>
    `;
    barberListContainer.appendChild(card);
  });
}
