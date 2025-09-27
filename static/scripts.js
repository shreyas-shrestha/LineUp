// --- DOM elements ---
const fileInput = document.getElementById('file-input'),
      imageUploadArea = document.getElementById('image-upload-area'),
      imagePreviewContainer = document.getElementById('image-preview-container'),
      imagePreview = document.getElementById('image-preview'),
      analyzeButton = document.getElementById('analyze-button'),
      uploadSection = document.getElementById('upload-section'),
      statusSection = document.getElementById('status-section'),
      loader = document.getElementById('loader'),
      statusMessage = document.getElementById('status-message'),
      errorContainer = document.getElementById('error-container'),
      errorMessage = document.getElementById('error-message'),
      tryAgainButton = document.getElementById('try-again-button'),
      resultsSection = document.getElementById('results-section'),
      analysisGrid = document.getElementById('analysis-grid'),
      recommendationsContainer = document.getElementById('recommendations-container'),
      startOverButton = document.getElementById('start-over-button'),
      findBarberButton = document.getElementById('find-barber-button'),
      barberListContainer = document.getElementById('barber-list-container'),
      socialFeedContainer = document.getElementById('social-feed-container'),
      addPostButton = document.getElementById('add-post-button'),
      addPostModal = document.getElementById('add-post-modal'),
      closeModalButton = document.getElementById('close-modal-button'),
      postUploadArea = document.getElementById('post-upload-area'),
      postFileInput = document.getElementById('post-file-input'),
      postImagePreview = document.getElementById('post-image-preview'),
      postCaptionInput = document.getElementById('post-caption-input'),
      submitPostButton = document.getElementById('submit-post-button'),
      bookingModal = document.getElementById('booking-modal'),
      closeBookingModal = document.getElementById('close-booking-modal');

const tabs = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('tab-active'));
    tab.classList.add('tab-active');
    const tabName = tab.dataset.tab;
    tabContents.forEach(c => c.classList.add('hidden'));
    document.getElementById(`${tabName}-tab-content`).classList.remove('hidden');
  });
});

function switchToTab(name) {
  document.querySelector(`.tab-button[data-tab="${name}"]`).click();
}

// --- State ---
let base64ImageData = null, postBase64ImageData = null, lastRecommendedStyles = [];

// Mock barber data
const atlantaBarbers = [
  { id: 1, name: 'Cuts by Clay', specialties: ['Fade','Taper','Modern Mullet'], rating: 4.9, avgCost: 45, location: 'Midtown' },
  { id: 2, name: 'The Buckhead Barber', specialties: ['Pompadour','Buzz Cut','Crew Cut'], rating: 4.8, avgCost: 55, location: 'Buckhead' },
  { id: 3, name: 'Virginia-Highland Shears', specialties: ['Shag','Bob','Long Layers'], rating: 4.9, avgCost: 75, location: 'Virginia-Highland' },
  { id: 4, name: 'East Atlanta Edge', specialties: ['Fade','Undercut','Curly Top'], rating: 4.7, avgCost: 40, location: 'East Atlanta' },
  { id: 5, name: 'Ponce City Fades', specialties: ['Taper','Crew Cut','Quiff'], rating: 4.8, avgCost: 50, location: 'Old Fourth Ward' }
];

// --- File handling ---
imageUploadArea.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => handleFileSelect(e, 'analysis'));
analyzeButton.addEventListener('click', startAnalysis);
tryAgainButton?.addEventListener('click', resetUI);
startOverButton?.addEventListener('click', resetUI);
findBarberButton?.addEventListener('click', showBarbersForRecommendations);

// Post modal
addPostButton.addEventListener('click', () => addPostModal.classList.remove('hidden'));
closeModalButton.addEventListener('click', resetPostModal);
postUploadArea?.addEventListener('click', () => postFileInput.click());
postFileInput?.addEventListener('change', (e) => handleFileSelect(e, 'post'));
submitPostButton?.addEventListener('click', handleSubmitPost);

function handleFileSelect(event, type) {
  const file = event.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    if (type === 'analysis') {
      base64ImageData = e.target.result.split(',')[1];
      imagePreview.src = e.target.result;
      imageUploadArea.classList.add('hidden');
      imagePreviewContainer.classList.remove('hidden');
    } else {
      postBase64ImageData = e.target.result.split(',')[1];
      postImagePreview.src = e.target.result;
      postUploadArea.classList.add('hidden');
      postImagePreview.classList.remove('hidden');
    }
  };
  reader.readAsDataURL(file);
}

function resetUI() {
  uploadSection.classList.remove('hidden');
  statusSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  errorContainer.classList.add('hidden');
  imageUploadArea.classList.remove('hidden');
  imagePreviewContainer.classList.add('hidden');
  imagePreview.src = '';
  fileInput.value = '';
  base64ImageData = null;
}

async function startAnalysis() {
  if (!base64ImageData) { showError("Please upload an image first."); return; }
  uploadSection.classList.add('hidden');
  resultsSection.classList.add('hidden');
  statusSection.classList.remove('hidden');
  loader.classList.remove('hidden');
  errorContainer.classList.add('hidden');
  statusMessage.textContent = "Checking your photo...";

  try {
    // Build payload expected by backend
    const payload = {
      payload: [
        { parts: [ { inlineData: { mimeType: "image/jpeg", data: base64ImageData } } ] }
      ]
    };

    const resp = await fetch('/analyze', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.error || "Server returned an error");
    }

    displayResults(data);
  } catch (err) {
    console.error(err);
    showError(err.message || "Analysis failed");
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
  analysisGrid.innerHTML = '';

  const analysisData = [
    { label: 'Face Shape', value: data.analysis.faceShape || data.analysis.face_shape || 'Unknown' },
    { label: 'Hair Texture', value: data.analysis.hairTexture || data.analysis.hair_texture || 'Unknown' },
    { label: 'Hair Color', value: data.analysis.hairColor || data.analysis.hair_color || 'Unknown' },
    { label: 'Est. Age', value: data.analysis.estimatedAge || data.analysis.estimated_age || 'Unknown' }
  ];

  analysisData.forEach(item => {
    const div = document.createElement('div');
    div.className = 'bg-gray-800 p-4 rounded-lg';
    div.innerHTML = `<p class="text-sm text-gray-400">${item.label}</p><p class="font-bold text-lg text-white">${item.value}</p>`;
    analysisGrid.appendChild(div);
  });

  recommendationsContainer.innerHTML = '';
  lastRecommendedStyles = (data.recommendations || []).map(r => r.styleName || r.name || r.style);

  (data.recommendations || []).forEach(rec => {
    const name = rec.styleName || rec.name || rec.style || "Style";
    const description = rec.description || rec.reason || rec.reasoning || "";
    const reason = rec.reason || rec.reasoning || "";
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden flex flex-col';
    const placeholderImageUrl = `https://placehold.co/600x400/000000/FFFFFF?text=${encodeURIComponent(name)}`;
    card.innerHTML = `<img src="${placeholderImageUrl}" alt="${name}" class="w-full h-48 object-cover"><div class="p-5 flex flex-col flex-grow"><h3 class="text-xl font-bold text-white mb-2">${name}</h3><p class="text-gray-300 text-sm mb-4 flex-grow">${description}</p><p class="text-xs text-gray-400"><strong class="text-sky-400">Why it works:</strong> ${reason}</p></div>`;
    recommendationsContainer.appendChild(card);
  });
}

// Barber functions
function showBarbersForRecommendations() {
  const preferred = atlantaBarbers.filter(b => b.specialties.some(s => lastRecommendedStyles.includes(s)));
  renderBarberList(preferred.length ? preferred : atlantaBarbers);
  switchToTab('barbers');
}

function renderBarberList(barbers) {
  barberListContainer.innerHTML = '';
  barbers.forEach(barber => {
    const card = document.createElement('div');
    card.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4';
    card.innerHTML = `<div><h4 class="text-xl font-bold">${barber.name}</h4><p class="text-sm text-gray-400">${barber.location}</p><div class="flex items-center gap-4 mt-2"><span class="text-yellow-400 flex items-center gap-1">★ ${barber.rating}</span><span class="text-green-400 font-semibold">~$${barber.avgCost}</span></div></div><button class="book-button w-full sm:w-auto bg-sky-500 text-white font-semibold py-2 px-6 rounded-lg hover:bg-sky-600 transition-colors" data-barber-name="${barber.name}">Book Now</button>`;
    barberListContainer.appendChild(card);
  });
  document.querySelectorAll('.book-button').forEach(btn => btn.addEventListener('click', (e) => {
    const name = e.currentTarget.dataset.barberName;
    document.getElementById('booking-title').textContent = `Booking with ${name}`;
    bookingModal.classList.remove('hidden');
  }));
}

// Social functions
postUploadArea?.addEventListener('click', () => postFileInput.click());
postFileInput?.addEventListener('change', e => handleFileSelect(e, 'post'));

async function handleSubmitPost() {
  if (!postBase64ImageData || !postCaptionInput.value.trim()) return alert("Please add a photo and a caption.");
  submitPostButton.disabled = true;
  try {
    await fetch('/social', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: postBase64ImageData, caption: postCaptionInput.value })
    });
    resetPostModal();
    loadSocialPosts();
  } catch (e) {
    alert("Failed to post");
  } finally {
    submitPostButton.disabled = false;
  }
}

function resetPostModal() {
  addPostModal.classList.add('hidden');
  postImagePreview.classList.add('hidden');
  postUploadArea.classList.remove('hidden');
  postFileInput.value = '';
  postCaptionInput.value = '';
  postBase64ImageData = null;
}

async function loadSocialPosts() {
  try {
    const res = await fetch('/social');
    const posts = await res.json();
    socialFeedContainer.innerHTML = '';
    if (!posts || posts.length === 0) {
      socialFeedContainer.innerHTML = "<p class='text-center py-10 text-gray-500'>No posts yet.</p>";
      return;
    }
    posts.forEach(post => {
      const pc = document.createElement('div');
      pc.className = 'bg-gray-900/50 border border-gray-700 rounded-2xl overflow-hidden';
      pc.innerHTML = `<img src="data:image/jpeg;base64,${post.image}" class="w-full h-auto max-h-[70vh] object-cover"><div class="p-4"><p class="text-white mb-3">${post.caption}</p><div class="flex items-center gap-2"><button class="like-btn" data-id="${post.id}">❤️ ${post.likes}</button></div></div>`;
      socialFeedContainer.appendChild(pc);
    });
    document.querySelectorAll('.like-btn').forEach(btn => btn.addEventListener('click', async () => {
      await fetch(`/social/like/${btn.dataset.id}`, { method: 'POST' });
      loadSocialPosts();
    }));
  } catch (e) {
    console.error(e);
  }
}

// init
renderBarberList(atlantaBarbers);
loadSocialPosts();
