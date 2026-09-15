// Barber portfolio: grid of work photos and the upload modal.
import { byId, html, show, hide, setBusy, setFieldError, clearFormErrors, errorNotice } from '../dom.js';
import { api, ApiError } from '../api.js';
import { getIdentity, store } from '../state.js';
import { openModal, closeModal, onModalClose } from '../ui/modal.js';
import { notify } from '../ui/toast.js';
import { showSkeleton, skeletonCards, clearBusy } from '../ui/skeleton.js';
import { bindDropzone, validateImage, compressImage } from '../ui/dropzone.js';
import { onTabShow } from '../nav.js';
import { imageSrc, formatDate } from '../format.js';
import { debug } from '../env.js';

const els = {};
let items = [];
let pendingImage = null;

export function getPortfolio() { return items; }

function render() {
  clearBusy(els.grid);
  if (!items.length) {
    els.grid.innerHTML = '';
    show(els.empty);
    return;
  }
  hide(els.empty);
  els.grid.innerHTML = html`${items.map((work) => html`
    <article class="card">
      <div class="card-media card-media-square"><img src="${imageSrc(work.image)}" alt="${work.styleName || 'Portfolio photo'}" loading="lazy" width="480" height="480"></div>
      <h3 class="card-title">${work.styleName || 'Untitled'}</h3>
      ${work.description ? html`<p class="card-text">${work.description}</p>` : ''}
      ${work.date ? html`<p class="text-xs text-text-2 mt-3">${formatDate(work.date, { relative: false })}</p>` : ''}
    </article>`)}`;
}

export async function loadPortfolio({ silent = false } = {}) {
  const { barberId } = getIdentity();
  if (!silent) { hide(els.empty); showSkeleton(els.grid, skeletonCards(3)); }
  try {
    const data = await api.portfolio(barberId);
    items = Array.isArray(data.portfolio) ? data.portfolio : [];
    store.set('portfolio', items);
    render();
  } catch (err) {
    debug('portfolio failed', err);
    clearBusy(els.grid);
    hide(els.empty);
    els.grid.replaceChildren(errorNotice({ title: 'Portfolio did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadPortfolio() }));
  }
  return items;
}

function resetForm() {
  pendingImage = null;
  els.input.value = '';
  els.preview.removeAttribute('src');
  hide(els.preview);
  show(els.zone);
  els.styleName.value = '';
  els.description.value = '';
  clearFormErrors(els.form);
}

async function handleFile(file) {
  clearFormErrors(els.form);
  const problem = validateImage(file);
  if (problem) { setFieldError(els.error, problem); return; }
  try {
    pendingImage = await compressImage(file);
    els.preview.src = pendingImage.dataUrl;
    show(els.preview);
    hide(els.zone);
    els.styleName.focus({ preventScroll: true });
  } catch (err) {
    debug('portfolio image failed', err);
    setFieldError(els.error, 'That image could not be read. Try a different file.');
  }
}

async function submit(event) {
  event.preventDefault();
  clearFormErrors(els.form);
  const styleName = els.styleName.value.trim();
  if (!pendingImage) { setFieldError(els.error, 'Choose a photo of the cut.'); els.input.focus(); return; }
  if (!styleName) { setFieldError(els.error, 'Give the style a name.', els.styleName); return; }
  setBusy(els.submit, true, 'Uploading…');
  try {
    const data = await api.addPortfolio(getIdentity().barberId, { styleName, image: pendingImage.base64, description: els.description.value.trim() });
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'The photo was not saved.');
    closeModal('upload-work-modal');
    notify.success('Added to portfolio', styleName);
    await loadPortfolio({ silent: true });
  } catch (err) {
    debug('portfolio upload failed', err);
    setFieldError(els.error, err instanceof ApiError ? err.message : 'The photo could not be uploaded.');
  } finally {
    setBusy(els.submit, false);
  }
}

export function initPortfolio() {
  Object.assign(els, {
    grid: byId('barber-portfolio-grid'),
    empty: byId('portfolio-empty'),
    form: byId('work-form'),
    input: byId('work-image-input'),
    zone: byId('work-image-area'),
    preview: byId('work-image-preview'),
    styleName: byId('work-style-name'),
    description: byId('work-description'),
    error: byId('work-error'),
    submit: byId('submit-work'),
  });
  byId('upload-work-button').addEventListener('click', () => { resetForm(); openModal('upload-work-modal'); });
  bindDropzone({ input: els.input, zone: els.zone, onFile: handleFile });
  els.form.addEventListener('submit', submit);
  onModalClose('upload-work-modal', resetForm);
  onTabShow('barber-portfolio', () => loadPortfolio({ silent: items.length > 0 }));
}
