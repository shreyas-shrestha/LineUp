// Home tab: choose a photo, compress it, send it for analysis, show the
// face/hair read-out and recommended cuts, and hand off to try-on or search.
import { byId, html, show, hide, setBusy, delegate } from '../dom.js';
import { icon } from '../icons.js';
import { api, ApiError } from '../api.js';
import { getSavedAnalysis, saveAnalysis, clearAnalysis, getSavedImage, saveImage } from '../state.js';
import { bindDropzone, validateImage, compressImage } from '../ui/dropzone.js';
import { titleCase } from '../format.js';
import { openTryOn } from './tryon.js';
import { openZipcodePrompt, searchForStyles } from './barbers.js';
import { debug } from '../env.js';

const SAMPLE_RESULT = {
  mock: true,
  source: 'sample',
  analysis: { faceShape: 'oval', hairTexture: 'wavy', hairColor: 'brown', estimatedGender: 'male', estimatedAge: '25-30' },
  recommendations: [
    { styleName: 'Modern Fade', description: 'Short, blended sides with a textured top.', reason: 'Keeps an oval face balanced.' },
    { styleName: 'Textured Quiff', description: 'Volume at the front, swept up and back.', reason: 'Wavy hair holds the shape without much product.' },
    { styleName: 'Classic Side Part', description: 'Clean lines with a defined part.', reason: 'Adds structure and works for most settings.' },
    { styleName: 'Messy Crop', description: 'Short and textured with a tousled finish.', reason: 'Low maintenance; natural texture does the work.' },
    { styleName: 'Short Buzz', description: 'Close all over, clean and minimal.', reason: 'Shows off facial structure with no styling.' },
    { styleName: 'Undercut', description: 'Short sides with a longer, styled top.', reason: 'Contrast adds definition.' },
  ],
};

// Why the server sent a fixed example instead of a real read. "No Gemini key"
// is only one of the reasons, and saying it when a key IS configured sends
// you looking in the wrong place.
const MOCK_REASONS = {
  gemini_not_configured: 'This deployment has no Gemini key, so these suggestions are a fixed example rather than a read of your photo.',
  daily_quota_reached: "This deployment's Gemini budget for today is spent, so these are sample results. Real analysis resumes tomorrow.",
  gemini_error: 'The analysis service refused the request, so these are sample results. The key may be wrong, or the model may not be available to it.',
  request_failed: 'The analysis service could not be reached, so these are sample results.',
};

function mockReasonText(reason) {
  if (MOCK_REASONS[reason]) return MOCK_REASONS[reason];
  return reason
    ? `These are sample results rather than a read of your photo (${reason}).`
    : 'These are sample results rather than a read of your photo.';
}

const els = {};
let photo = null; // { dataUrl, base64 }
let result = null;

export function getPhoto() { return photo; }
export function getRecommendedStyles() {
  return (result?.recommendations || []).map((rec) => rec.styleName).filter(Boolean).slice(0, 6);
}

function normalize(data) {
  const analysis = data.analysis || {};
  return {
    mock: Boolean(data.mock),
    source: data.source || (data.mock ? 'mock' : 'gemini'),
    reason: data.reason || '',
    analysis: {
      faceShape: analysis.faceShape || analysis.face_shape || '',
      hairTexture: analysis.hairTexture || analysis.hair_texture || '',
      hairColor: analysis.hairColor || analysis.hair_color || '',
      estimatedGender: analysis.estimatedGender || analysis.gender || '',
      estimatedAge: analysis.estimatedAge || analysis.age || '',
    },
    recommendations: (data.recommendations || []).slice(0, 6).map((rec) => ({
      styleName: rec.styleName || rec.name || 'Untitled style',
      description: rec.description || '',
      reason: rec.reason || '',
    })),
  };
}

function showPreview() {
  show(els.uploadSection);
  hide(els.statusSection);
  hide(els.results);
  hide(els.errorWrap);
  if (photo) {
    els.preview.src = photo.dataUrl;
    hide(els.zone);
    show(els.previewWrap);
  } else {
    show(els.zone);
    hide(els.previewWrap);
  }
}

async function handleFile(file) {
  const problem = validateImage(file);
  if (problem) { showError(problem, { offerSample: false, keepUpload: true }); return; }
  try {
    photo = await compressImage(file, { maxSize: 1280, quality: 0.85 });
    saveImage(photo.dataUrl);
    showPreview();
    els.analyzeBtn.focus({ preventScroll: true });
  } catch (err) {
    debug('image load failed', err);
    showError('That image could not be read. Try a different file.', { offerSample: false, keepUpload: true });
  }
}

function showError(message, { offerSample = true, keepUpload = false, title, focus = true } = {}) {
  if (!keepUpload) hide(els.uploadSection);
  show(els.statusSection);
  hide(els.loader);
  els.statusMessage.textContent = '';
  els.statusTitle.textContent = title || (keepUpload ? 'Check the photo' : 'Analysis did not finish');
  els.errorMessage.textContent = message;
  els.sampleBtn.classList.toggle('hidden', !offerSample);
  show(els.errorWrap);
  if (focus) els.tryAgain.focus({ preventScroll: true });
}

function reset() {
  photo = null;
  result = null;
  clearAnalysis();
  els.fileInput.value = '';
  els.preview.removeAttribute('src');
  els.statusTitle.textContent = 'Analyzing your photo';
  showPreview();
  els.fileInput.focus({ preventScroll: true });
}

async function analyze() {
  if (!photo) { showError('Choose a photo first.', { offerSample: false, keepUpload: true }); return; }
  hide(els.uploadSection);
  hide(els.results);
  hide(els.errorWrap);
  show(els.statusSection);
  show(els.loader);
  els.statusTitle.textContent = 'Analyzing your photo';
  els.statusMessage.textContent = 'Reading face shape and hair texture. This takes about ten seconds.';
  setBusy(els.analyzeBtn, true, 'Analyzing…');
  try {
    const data = await api.analyze(photo.base64);
    if (!data || !data.analysis) throw new ApiError('The service returned an unexpected response.');
    result = normalize(data);
    saveAnalysis(result);
    renderResults();
  } catch (err) {
    debug('analysis failed', err);
    const message = err instanceof ApiError ? err.message : 'Something went wrong while analyzing the photo.';
    // Out of credits: billing.js opens the credits modal; keep the photo so
    // the user can run it again after topping up.
    if (err instanceof ApiError && err.status === 402) {
      showPreview();
      showError(message, { offerSample: false, keepUpload: true, title: 'Out of credits', focus: false });
    } else {
      showError(message, { offerSample: true });
    }
  } finally {
    setBusy(els.analyzeBtn, false);
    hide(els.loader);
    els.statusMessage.textContent = '';
  }
}

function useSample() {
  result = normalize(SAMPLE_RESULT);
  result.reason = 'request_failed';
  saveAnalysis(result);
  renderResults();
}

function renderResults() {
  hide(els.statusSection);
  hide(els.uploadSection);
  show(els.results);

  const a = result.analysis;
  const rows = [
    ['Face shape', titleCase(a.faceShape) || 'Not detected'],
    ['Hair texture', titleCase(a.hairTexture) || 'Not detected'],
    ['Hair color', titleCase(a.hairColor) || 'Not detected'],
    ['Gender', titleCase(a.estimatedGender) || 'Not detected'],
    ['Age range', a.estimatedAge || 'Not detected'],
  ];
  els.grid.innerHTML = html`${rows.map(([label, value]) => html`<div class="kv"><p class="kv-label">${label}</p><p class="kv-value">${value}</p></div>`)}`;

  els.notice.innerHTML = result.mock
    ? html`<div class="notice" role="status">${icon('info', { className: 'notice-icon' })}<div class="notice-body"><div><p class="notice-title">Sample results</p><p class="notice-text">${mockReasonText(result.reason)}</p></div></div></div>`
    : '';

  els.recs.innerHTML = html`${result.recommendations.map((rec) => html`
    <article class="card">
      <div class="card-header"><div><h3 class="card-title">${rec.styleName}</h3><p class="card-text">${rec.description}</p></div></div>
      ${rec.reason ? html`<p class="text-sm text-text-2"><span class="text-text-1 font-medium">Why it fits:</span> ${rec.reason}</p>` : ''}
      <div class="card-footer">
        <button type="button" class="btn-primary btn-sm" data-action="tryon" data-style="${rec.styleName}">${icon('image', { size: 'sm' })}Preview</button>
        <button type="button" class="btn-ghost btn-sm" data-action="find-barbers" data-style="${rec.styleName}">${icon('map-pin', { size: 'sm' })}Find barbers</button>
      </div>
    </article>`)}`;
  if (!result.recommendations.length) {
    els.recs.innerHTML = '<p class="text-sm text-text-2">No recommendations came back for this photo. Try a clearer, front-facing shot.</p>';
  }
}

function restore() {
  const savedImage = getSavedImage();
  if (typeof savedImage === 'string' && savedImage.startsWith('data:image/')) {
    photo = { dataUrl: savedImage, base64: savedImage.split(',')[1] };
  }
  const saved = getSavedAnalysis();
  // A saved sample is the same fixed example every time, so restoring one is
  // worth nothing and costs a lot: the page looks like it just analysed the
  // photo and produced a sample, which reads as "my key is not working" long
  // after the key is working. Drop it and offer Analyze again; the photo stays.
  if (saved && saved.mock) {
    saveAnalysis(null);
    showPreview();
    return;
  }
  if (saved && saved.analysis && photo) {
    result = normalize(saved);
    result.reason = saved.reason || '';
    renderResults();
    return;
  }
  showPreview();
}

export function initAnalysis() {
  Object.assign(els, {
    fileInput: byId('file-input'),
    zone: byId('image-upload-area'),
    previewWrap: byId('image-preview-container'),
    preview: byId('image-preview'),
    analyzeBtn: byId('analyze-button'),
    uploadSection: byId('upload-section'),
    statusSection: byId('status-section'),
    statusTitle: byId('status-title'),
    statusMessage: byId('status-message'),
    loader: byId('loader'),
    errorWrap: byId('error-container'),
    errorMessage: byId('error-message'),
    tryAgain: byId('try-again-button'),
    sampleBtn: byId('use-sample-button'),
    results: byId('results-section'),
    grid: byId('analysis-grid'),
    recs: byId('recommendations-container'),
    findBtn: byId('find-barber-button'),
    startOver: byId('start-over-button'),
  });
  const notice = document.createElement('div');
  notice.id = 'analysis-notice';
  els.results.prepend(notice);
  els.notice = notice;

  bindDropzone({ input: els.fileInput, zone: els.zone, onFile: handleFile });
  els.analyzeBtn.addEventListener('click', analyze);
  els.tryAgain.addEventListener('click', () => { els.statusTitle.textContent = 'Analyzing your photo'; showPreview(); });
  els.sampleBtn.addEventListener('click', useSample);
  els.startOver.addEventListener('click', reset);
  els.findBtn.addEventListener('click', () => searchForStyles(getRecommendedStyles()));
  delegate(els.recs, 'click', '[data-action]', (event, button) => {
    const style = button.dataset.style || '';
    if (button.dataset.action === 'tryon') openTryOn(style);
    else if (button.dataset.action === 'find-barbers') openZipcodePrompt(style);
  });
  restore();
}
