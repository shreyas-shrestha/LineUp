// Virtual try-on modal: shows the analysed photo (or a camera capture), calls
// /virtual-tryon and renders a before/after comparison with a download.
import { byId, show, hide, setBusy, setFieldError, clearFieldError } from '../dom.js';
import { api, ApiError } from '../api.js';
import { openModal, onModalClose } from '../ui/modal.js';
import { imageSrc, slugify } from '../format.js';
import { getPhoto } from './analysis.js';
import { debug } from '../env.js';

const els = {};
let stream = null;
let source = null; // { dataUrl, base64 }
let styleName = '';
let result = null;

function setButtons({ camera = false } = {}) {
  els.stop.classList.toggle('hidden', !camera);
  els.capture.classList.toggle('hidden', !camera);
  els.useCamera.classList.toggle('hidden', camera);
  els.start.classList.toggle('hidden', camera);
  els.save.classList.toggle('hidden', camera || !result);
}

function render() {
  els.subtitle.textContent = styleName;
  hide(els.video);
  hide(els.compare);
  hide(els.loading);
  clearFieldError(els.error);
  els.note.hidden = true;
  if (source) {
    els.photo.src = source.dataUrl;
    show(els.photo);
    hide(els.empty);
  } else {
    els.photo.removeAttribute('src');
    hide(els.photo);
    show(els.empty);
  }
  els.start.disabled = !source;
  setButtons({ camera: false });
}

export function openTryOn(name) {
  styleName = name || '';
  source = getPhoto();
  result = null;
  render();
  openModal('virtual-tryon-modal');
}

async function startCamera() {
  clearFieldError(els.error);
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setFieldError(els.error, 'This browser does not support camera access. Upload a photo instead.');
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 } }, audio: false });
  } catch (err) {
    debug('camera blocked', err);
    setFieldError(els.error, 'Camera access was blocked. Allow it in the browser, or upload a photo instead.');
    return;
  }
  els.video.srcObject = stream;
  show(els.video);
  hide(els.photo);
  hide(els.compare);
  hide(els.empty);
  setButtons({ camera: true });
  els.capture.focus({ preventScroll: true });
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    stream = null;
  }
  if (els.video) els.video.srcObject = null;
  render();
}

function capturePhoto() {
  if (!stream || !els.video.videoWidth) return;
  const maxSize = 1280;
  const scale = Math.min(1, maxSize / Math.max(els.video.videoWidth, els.video.videoHeight));
  const canvas = els.canvas;
  canvas.width = Math.round(els.video.videoWidth * scale);
  canvas.height = Math.round(els.video.videoHeight * scale);
  canvas.getContext('2d').drawImage(els.video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
  source = { dataUrl, base64: dataUrl.split(',')[1] };
  result = null;
  stopCamera();
  els.start.focus({ preventScroll: true });
}

async function runPreview() {
  clearFieldError(els.error);
  if (!source) { setFieldError(els.error, 'Upload a photo first, or use your camera.'); return; }
  show(els.loading);
  hide(els.compare);
  setBusy(els.start, true, 'Rendering…');
  try {
    const data = await api.tryOn(source.base64, styleName || 'a fresh haircut');
    if (!data || data.success === false || !data.resultImage) throw new ApiError((data && data.error) || 'The preview could not be created.');
    result = data;
    els.before.src = imageSrc(data.originalImage || source.base64);
    els.after.src = imageSrc(data.resultImage);
    els.photo.src = els.after.src;
    show(els.photo);
    show(els.compare);
    els.note.textContent = data.mock
      ? 'Preview only: your photo labelled with the style. Connect a Replicate token for a generated result.'
      : (data.note || '');
    els.note.hidden = !els.note.textContent;
    show(els.save);
  } catch (err) {
    debug('try-on failed', err);
    setFieldError(els.error, err instanceof ApiError ? err.message : 'The preview could not be created.');
  } finally {
    hide(els.loading);
    setBusy(els.start, false);
  }
}

function saveResult() {
  if (!result) return;
  const link = document.createElement('a');
  link.href = imageSrc(result.resultImage);
  link.download = `lineup-${slugify(styleName)}.jpg`;
  // download is ignored for cross-origin URLs (Replicate); open those in a new tab instead of navigating away.
  if (!/^(data:|blob:)/.test(link.href) && new URL(link.href, location.href).origin !== location.origin) { link.target = '_blank'; link.rel = 'noopener'; }
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function initTryOn() {
  Object.assign(els, {
    subtitle: byId('current-tryon-style'),
    video: byId('virtual-tryon-video'),
    photo: byId('virtual-tryon-photo'),
    canvas: byId('virtual-tryon-canvas'),
    empty: byId('tryon-empty'),
    loading: byId('tryon-loading'),
    compare: byId('tryon-compare'),
    before: byId('tryon-before'),
    after: byId('tryon-after'),
    note: byId('tryon-note'),
    error: byId('tryon-error'),
    stop: byId('stop-tryon'),
    capture: byId('capture-photo'),
    useCamera: byId('use-camera'),
    save: byId('take-screenshot'),
    start: byId('start-tryon'),
  });
  els.start.addEventListener('click', runPreview);
  els.useCamera.addEventListener('click', startCamera);
  els.stop.addEventListener('click', stopCamera);
  els.capture.addEventListener('click', capturePhoto);
  els.save.addEventListener('click', saveResult);
  onModalClose('virtual-tryon-modal', () => { if (stream) stopCamera(); });
}
