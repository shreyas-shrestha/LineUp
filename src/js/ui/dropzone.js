// File pickers: click/drag/drop on a .dropzone, validation against config,
// and canvas compression to a <= 1280px JPEG before anything is uploaded.
import { UI, debug } from '../env.js';

export function validateImage(file) {
  if (!file) return 'Choose a photo first.';
  const types = UI.supportedImageTypes || [];
  if (types.length && !types.includes(file.type)) return 'Use a JPG, PNG or WebP image.';
  const maxBytes = (UI.maxImageSizeMB || 5) * 1024 * 1024;
  if (file.size > maxBytes) return `That file is ${(file.size / 1048576).toFixed(1)} MB. The limit is ${UI.maxImageSizeMB || 5} MB.`;
  return null;
}

async function loadBitmap(file) {
  if (typeof createImageBitmap === 'function') {
    try { return await createImageBitmap(file, { imageOrientation: 'from-image' }); } catch (err) { debug('createImageBitmap failed', err); }
  }
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => { URL.revokeObjectURL(url); resolve(image); };
    image.onerror = () => { URL.revokeObjectURL(url); reject(new Error('That image could not be read.')); };
    image.src = url;
  });
}

export async function compressImage(file, { maxSize = 1280, quality = 0.85 } = {}) {
  const bitmap = await loadBitmap(file);
  const sourceWidth = bitmap.naturalWidth || bitmap.width;
  const sourceHeight = bitmap.naturalHeight || bitmap.height;
  const scale = Math.min(1, maxSize / Math.max(sourceWidth, sourceHeight));
  const width = Math.max(1, Math.round(sourceWidth * scale));
  const height = Math.max(1, Math.round(sourceHeight * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  context.drawImage(bitmap, 0, 0, width, height);
  if (typeof bitmap.close === 'function') bitmap.close();
  const dataUrl = canvas.toDataURL('image/jpeg', quality);
  return { dataUrl, base64: dataUrl.split(',')[1], width, height };
}

export function bindDropzone({ input, zone, onFile }) {
  if (!input || !zone) return;
  zone.addEventListener('click', (event) => {
    if (event.target === input) return;
    input.click();
  });
  zone.addEventListener('dragover', (event) => { event.preventDefault(); zone.classList.add('is-dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('is-dragover'));
  zone.addEventListener('drop', (event) => {
    event.preventDefault();
    zone.classList.remove('is-dragover');
    const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
    if (file) onFile(file);
  });
  input.addEventListener('change', () => {
    const file = input.files && input.files[0];
    if (file) onFile(file);
  });
}
