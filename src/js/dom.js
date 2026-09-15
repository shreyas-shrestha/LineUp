// DOM helpers: selection, safe HTML templating, delegation, field errors.

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
export const byId = (id) => document.getElementById(id);

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ESCAPES[ch]);
}

// Raw marks a string as already-safe markup. Everything else interpolated
// into the html`` tag is escaped, so templates cannot leak user/API data.
export class Raw {
  constructor(value) { this.value = String(value); }
  toString() { return this.value; }
}
export const raw = (value) => new Raw(value);

function renderValue(value) {
  if (value == null || value === false) return '';
  if (value instanceof Raw) return value.value;
  if (Array.isArray(value)) return value.map(renderValue).join('');
  return escapeHtml(value);
}

export function html(strings, ...values) {
  let out = '';
  for (let i = 0; i < strings.length; i += 1) {
    out += strings[i];
    if (i < values.length) out += renderValue(values[i]);
  }
  return new Raw(out);
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'html') node.innerHTML = String(value);
    else if (key.startsWith('on') && typeof value === 'function') node.addEventListener(key.slice(2).toLowerCase(), value);
    else node.setAttribute(key, value === true ? '' : value);
  }
  for (const child of [].concat(children)) {
    if (child == null) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

// One listener per container; handlers are looked up by the closest match.
export function delegate(root, type, selector, handler) {
  if (!root) return;
  root.addEventListener(type, (event) => {
    const target = event.target instanceof Element ? event.target.closest(selector) : null;
    if (target && root.contains(target)) handler(event, target);
  });
}

export const show = (node) => { if (node) node.classList.remove('hidden'); };
export const hide = (node) => { if (node) node.classList.add('hidden'); };
export const toggle = (node, visible) => { if (node) node.classList.toggle('hidden', !visible); };

// Button loading state: disabled + aria-busy + inline spinner + label.
export function setBusy(button, busy, label) {
  if (!button) return;
  if (busy) {
    if (button.dataset.idleHtml == null) button.dataset.idleHtml = button.innerHTML;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    button.innerHTML = `<span class="spinner spinner-sm" aria-hidden="true"></span>${label ? escapeHtml(label) : button.dataset.idleHtml}`;
  } else {
    button.disabled = false;
    button.removeAttribute('aria-busy');
    if (button.dataset.idleHtml != null) {
      button.innerHTML = button.dataset.idleHtml;
      delete button.dataset.idleHtml;
    }
  }
}

export function setFieldError(errorEl, message, control) {
  if (!errorEl) return;
  errorEl.innerHTML = `<svg class="icon icon-sm" aria-hidden="true"><use href="#i-alert"/></svg><span>${escapeHtml(message)}</span>`;
  errorEl.hidden = false;
  if (control) {
    control.setAttribute('aria-invalid', 'true');
    if (errorEl.id) {
      const described = (control.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean);
      if (!described.includes(errorEl.id)) control.setAttribute('aria-describedby', [...described, errorEl.id].join(' '));
    }
    if (typeof control.focus === 'function') control.focus({ preventScroll: false });
  }
}

export function clearFieldError(errorEl, ...controls) {
  if (errorEl) {
    errorEl.hidden = true;
    errorEl.textContent = '';
  }
  controls.forEach((control) => control && control.removeAttribute('aria-invalid'));
}

export function clearFormErrors(form) {
  if (!form) return;
  $$('.field-error', form).forEach((node) => { node.hidden = true; node.textContent = ''; });
  $$('[aria-invalid]', form).forEach((node) => node.removeAttribute('aria-invalid'));
}

// Inline error block with an optional retry action (for lists and grids).
export function errorNotice({ title = 'Something went wrong', text = '', retryLabel = 'Retry', onRetry } = {}) {
  const node = el('div', { class: 'notice notice-danger', role: 'alert' });
  node.innerHTML = `<svg class="icon notice-icon" aria-hidden="true"><use href="#i-alert"/></svg>
    <div class="notice-body"><div><p class="notice-title">${escapeHtml(title)}</p>${text ? `<p class="notice-text">${escapeHtml(text)}</p>` : ''}</div>
    ${onRetry ? `<div><button type="button" class="btn-secondary btn-sm">${escapeHtml(retryLabel)}</button></div>` : ''}</div>`;
  if (onRetry) node.querySelector('button').addEventListener('click', onRetry);
  return node;
}

export function debounce(fn, wait) {
  let timer = null;
  const debounced = (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
  debounced.cancel = () => clearTimeout(timer);
  return debounced;
}
