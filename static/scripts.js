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

// --- Mock Barbers ---
const atlantaBarbers = [
  { id: 1, name: 'Cuts by Clay', specialties: ['Fade', 'Taper'], rating: 4.9, avgCost: 45, location: 'Midtown' },
  { id: 2, name: 'The Buckhead Barber', specialties: ['Pompadour', 'Buzz Cut'], rating: 4.8, avgCost: 55, location: 'Buckhead' },
  { id: 3, name: 'Virginia-Highland Shears', specialties: ['Shag', 'Bob'], rating: 4.9, avgCost: 75, location: 'Virginia-Highland' }
];

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
  const reader = new FileReader();
  reader.onload = e => {
    base64ImageData = e.target.result.split(',')[1];
    imagePreview.src = e.target.result;
    imageUploadArea.classList.add('hidden');
    imagePreviewContainer.classList.remove('hidden');
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
}
tryAgainButton.addEventListener('click', resetUI);
startOverButton.addEventListener('click', resetUI);

// --- Analysis ---
analyzeButton.addEventListener('click', async () => {
  if (!base64ImageData) { showError("Please upload a photo."); return; }

  uploadSection.classList.add('hidden');
  statusSection.classList.remove('hidden');
  loader.classList.remove('hidden');
  statusMessage.textContent = "Analyzing your photo...";
  errorContainer.classList.add('hidden');

  try {
    const payload = {
      contents: [
        { parts: [
            { text: "Analyze this person and provide face, hair info and 5 haircut recommendations." },
            { inlineData: { mimeType: "image/jpeg", data: base64ImageData } }
          ]
        }
      ]
    };

    const response = await fetch('https://lineup-fjpn.onrender.com/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ payload })
    });

    const result = await response.json();

    if (result.error) throw new Error(result.error);

    displayResults(result);

  } catch (err) {
    showError(err.message || "Analysis failed.");
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
}

// --- Display Results ---
function displayResults(data) {
  statusSection.classList.add('hidden');
  resultsSection.classList.remove('hidden');

  // --- Analysis Grid ---
  analysisGrid.innerHTML = '';
  const analysisData = [
    { label: 'Face Shape', value: data.analysis.faceShape },
    { label: 'Hair Texture', value: data.analysis.hairTexture },
    { label: 'Hair Color', value: data.analysis.hairColor },
    { label: 'Gender', value: data.analysis.estimatedGender },
    { label: 'Est. Age', value: data.analysis.estimatedAge }
  ];
  analysisData.forEach(item => {
    const div = document.createElement('div');
    div.className = 'bg-gray-800 p-4 rounded-lg';
    div.innerHTML = `<p class="text-sm text-gray-400">${item.label}</p><p class="font-bold text-lg text-white">${item.value}</p>`;
    analysisGrid.appendChild(div);
  });

  // --- Recommendations (max 5) ---
  recommendationsContainer.innerHTML = '';
  lastRecommendedStyles = data.recommendations.slice(0,5).map(r => r.styleName);
  data.recommendations.slice(0,5).forEach(rec => {
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden flex flex-col';
    const placeholderImageUrl = `https://placehold.co/600x400/000000/FFFFFF?text=${encodeURIComponent(rec.styleName)}`;
    card.innerHTML = `<img src="${placeholderImageUrl}" alt="${rec.styleName}" class="w-full h-48 object-cover">
    <div class="p-5 flex flex-col flex-grow">
      <h3 class="text-xl font-bold text-white mb-2">${rec.styleName}</h3>
      <p class="text-gray-300 text-sm mb-4 flex-grow">${rec.description}</p>
      <p class="text-xs text-gray-400"><strong class="text-sky-400">Why it works:</strong> ${rec.reason}</p>
    </div>`;
    recommendationsContainer.appendChild(card);
  });
}

// --- Barbers ---
findBarberButton.addEventListener('click', () => {
  barberIntro.textContent = "Top barbers matching your style:";
  renderBarberList(atlantaBarbers.filter(b => b.specialties.some(s => lastRecommendedStyles.includes(s))) || atlantaBarbers);
  document.querySelector('.tab-button[data-tab="barbers"]').click();
});

function renderBarberList(barbers) {
  barberListContainer.innerHTML = '';
  barbers.forEach(barber => {
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4';
    card.innerHTML = `
      <div>
        <h4 class="text-xl font-bold">${barber.name}</h4>
        <p class="text-sm text-gray-400">${barber.location}</p>
        <div class="flex items-center gap-4 mt-2">
          <span class="text-yellow-400 flex items-center gap-1">${barber.rating} ★</span>
          <span class="text-green-400 font-semibold">~$${barber.avgCost}</span>
        </div>
      </div>
      <div class="flex gap-2 mt-3 sm:mt-0">
        ${barber.specialties.map(s => `<span class="bg-sky-500/50 text-white text-xs px-3 py-1 rounded-full">${s}</span>`).join('')}
      </div>
    `;
    barberListContainer.appendChild(card);
  });
}
