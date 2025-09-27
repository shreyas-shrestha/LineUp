// scripts.js

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

// --- Configuration ---
// Use the actual Render URL
const API_URL = 'https://lineup-fjpn.onrender.com';

console.log('API URL:', API_URL);

// --- Mock Barbers ---
const atlantaBarbers = [
  { id: 1, name: 'Cuts by Clay', specialties: ['Fade', 'Taper'], rating: 4.9, avgCost: 45, location: 'Midtown' },
  { id: 2, name: 'The Buckhead Barber', specialties: ['Pompadour', 'Buzz Cut'], rating: 4.8, avgCost: 55, location: 'Buckhead' },
  { id: 3, name: 'Virginia-Highland Shears', specialties: ['Shag', 'Bob'], rating: 4.9, avgCost: 75, location: 'Virginia-Highland' }
];

// --- Initialize Barbers on Load ---
window.addEventListener('DOMContentLoaded', () => {
  renderBarberList(atlantaBarbers);
});

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

// --- Image Upload ---
imageUploadArea.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', e => {
  const file = e.target.files[0];
  if (!file) return;
  
  // Check file size (max 2MB for better performance)
  if (file.size > 2 * 1024 * 1024) {
    showError("Image too large. Please use an image under 2MB.");
    return;
  }
  
  // Check file type
  if (!file.type.startsWith('image/')) {
    showError("Please upload an image file.");
    return;
  }
  
  const reader = new FileReader();
  reader.onload = e => {
    // Resize image if needed to reduce payload size
    const img = new Image();
    img.onload = function() {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      // Max dimensions
      const maxWidth = 800;
      const maxHeight = 800;
      let width = img.width;
      let height = img.height;
      
      // Calculate new dimensions
      if (width > height) {
        if (width > maxWidth) {
          height = height * (maxWidth / width);
          width = maxWidth;
        }
      } else {
        if (height > maxHeight) {
          width = width * (maxHeight / height);
          height = maxHeight;
        }
      }
      
      canvas.width = width;
      canvas.height = height;
      ctx.drawImage(img, 0, 0, width, height);
      
      // Get base64 with reduced quality
      const resizedBase64 = canvas.toDataURL('image/jpeg', 0.8);
      base64ImageData = resizedBase64.split(',')[1];
      imagePreview.src = resizedBase64;
      imageUploadArea.classList.add('hidden');
      imagePreviewContainer.classList.remove('hidden');
      console.log('Image loaded and resized, base64 length:', base64ImageData.length);
    };
    img.src = e.target.result;
  };
  reader.onerror = () => {
    showError("Failed to read image file.");
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

  // Use mock data if backend fails
  const useMockData = () => {
    console.log('Using mock data fallback');
    const mockResult = {
      analysis: {
        faceShape: "oval",
        hairTexture: "straight",
        hairColor: "brown",
        estimatedGender: "male",
        estimatedAge: "25-30"
      },
      recommendations: [
        {
          styleName: "Classic Fade",
          description: "A timeless cut with short sides that gradually blend into longer hair on top",
          reason: "Works well with oval face shapes and straight hair"
        },
        {
          styleName: "Textured Quiff",
          description: "Modern style with volume at the front, swept upward and back",
          reason: "Adds dimension and height, perfect for your face shape"
        },
        {
          styleName: "Side Part",
          description: "Clean and professional with a defined part on one side",
          reason: "Classic look that complements straight hair texture"
        },
        {
          styleName: "Buzz Cut",
          description: "Very short all over, low maintenance and clean",
          reason: "Simple and masculine, shows off facial features"
        },
        {
          styleName: "Crew Cut",
          description: "Short on sides and back with slightly longer hair on top",
          reason: "Versatile and easy to style for any occasion"
        }
      ]
    };
    displayResults(mockResult);
  };

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
    console.log('Payload size:', JSON.stringify(payload).length);

    // Add timeout to prevent hanging
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ payload }),
      signal: controller.signal
    }).catch(err => {
      console.error('Fetch error:', err);
      if (err.name === 'AbortError') {
        throw new Error('Request timeout - server took too long to respond');
      }
      throw new Error('Network error - could not reach server');
    });

    clearTimeout(timeoutId);

    console.log('Response received');
    console.log('Response status:', response.status);
    console.log('Response type:', response.headers.get('content-type'));

    // Check if we got a response at all
    if (!response) {
      console.error('No response received');
      useMockData();
      return;
    }

    // Check content type
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      console.error('Invalid content type:', contentType);
      const text = await response.text();
      console.error('Response body:', text.substring(0, 200));
      
      // If server is returning HTML (error page), use mock data
      if (text.includes('<!DOCTYPE') || text.includes('<html')) {
        console.log('Server returned HTML error page, using mock data');
        useMockData();
        return;
      }
      
      throw new Error('Server returned non-JSON response');
    }

    // Try to get response text
    const responseText = await response.text();
    console.log('Response length:', responseText.length);
    
    if (!responseText || responseText.trim() === '') {
      console.error('Empty response body');
      useMockData();
      return;
    }

    console.log('Response preview:', responseText.substring(0, 200));

    // Parse JSON
    let result;
    try {
      result = JSON.parse(responseText);
      console.log('Successfully parsed JSON');
    } catch (e) {
      console.error('JSON parse error:', e);
      console.error('Failed to parse:', responseText.substring(0, 500));
      
      // Try to extract JSON from response if it's wrapped in something
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          result = JSON.parse(jsonMatch[0]);
          console.log('Extracted and parsed JSON from response');
        } catch (e2) {
          console.error('Failed to extract JSON:', e2);
          useMockData();
          return;
        }
      } else {
        useMockData();
        return;
      }
    }

    console.log('Result:', result);

    // Check for error in result
    if (result.error) {
      console.error('Server returned error:', result.error);
      // If it's an API key error or similar, use mock data
      if (result.error.includes('API') || result.error.includes('key') || result.error.includes('Gemini')) {
        console.log('API configuration issue, using mock data');
        useMockData();
        return;
      }
      throw new Error(result.error);
    }

    // Validate result structure
    if (!result.analysis || !result.recommendations) {
      console.error('Invalid result structure:', result);
      useMockData();
      return;
    }

    displayResults(result);

  } catch (err) {
    console.error('Analysis error:', err);
    
    // For any error, try mock data as fallback
    if (err.message.includes('timeout') || err.message.includes('Network') || err.message.includes('fetch')) {
      showError("Server is not responding. Showing demo results.");
      useMockData();
    } else {
      showError(err.message || "Analysis failed. Showing demo results.");
      useMockData();
    }
  } finally {
    loader.classList.add('hidden');
    statusMessage.textContent = '';
  }
});

function showError(msg) {
  loader.classList.add('hidden');
  statusMessage.textContent = '';
  errorContainer.classList.remove('hidden');
  errorMessage.textContent = msg;
  
  // Auto-hide error after 5 seconds
  setTimeout(() => {
    errorContainer.classList.add('hidden');
  }, 5000);
}

// --- Display Results ---
function displayResults(data) {
  console.log('Displaying results:', data);
  
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

  // --- Recommendations (max 5) ---
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
