// Toasts render into #toast-region (aria-live="polite"). Max three stacked;
// success/info auto-dismiss after 4 s, errors after 6 s.
import { byId, escapeHtml } from '../dom.js';
import { debug } from '../env.js';

// A toast queued just before a full page reload (the 401 sign-out path), so the
// explanation survives into the new document instead of dying with the old one.
const PENDING_KEY = 'lineup.toast.pending';

const MAX_VISIBLE = 3;
const ICONS = { success: 'check-circle', error: 'alert', info: 'info' };

export function toast({ type = 'info', title, text = '', action, duration } = {}) {
  const region = byId('toast-region');
  if (!region) return null;
  while (region.children.length >= MAX_VISIBLE) dismiss(region.firstElementChild, true);

  const node = document.createElement('div');
  node.className = `toast toast-${ICONS[type] ? type : 'info'}`;
  node.setAttribute('role', type === 'error' ? 'alert' : 'status');
  node.innerHTML = `
    <svg class="icon toast-icon" aria-hidden="true"><use href="#i-${ICONS[type] || 'info'}"/></svg>
    <div class="toast-body">
      <p class="toast-title">${escapeHtml(title)}</p>
      ${text ? `<p class="toast-text">${escapeHtml(text)}</p>` : ''}
    </div>
    ${action ? `<button type="button" class="btn-ghost btn-sm toast-action">${escapeHtml(action.label)}</button>` : ''}
    <button type="button" class="btn-ghost btn-icon btn-sm toast-close" aria-label="Dismiss">
      <svg class="icon icon-sm" aria-hidden="true"><use href="#i-x"/></svg>
    </button>`;

  node.querySelector('.toast-close').addEventListener('click', () => dismiss(node));
  if (action) {
    node.querySelector('.toast-action').addEventListener('click', () => {
      dismiss(node);
      if (typeof action.onClick === 'function') action.onClick();
    });
  }
  region.appendChild(node);

  const ms = duration ?? (type === 'error' ? 6000 : 4000);
  node._timer = setTimeout(() => dismiss(node), ms);
  node.addEventListener('mouseenter', () => clearTimeout(node._timer));
  node.addEventListener('mouseleave', () => { node._timer = setTimeout(() => dismiss(node), 2000); });
  return node;
}

export function dismiss(node, immediate = false) {
  if (!node || node._leaving) return;
  node._leaving = true;
  clearTimeout(node._timer);
  if (immediate) { node.remove(); return; }
  node.classList.add('is-leaving');
  setTimeout(() => node.remove(), 140);
}

export const notify = {
  success: (title, text, options = {}) => toast({ type: 'success', title, text, ...options }),
  error: (title, text, options = {}) => toast({ type: 'error', title, text, ...options }),
  info: (title, text, options = {}) => toast({ type: 'info', title, text, ...options }),
};

export function toastAfterReload(options) {
  try { sessionStorage.setItem(PENDING_KEY, JSON.stringify(options)); }
  catch (err) { debug('pending toast write failed', err); }
}

export function flushPendingToast() {
  let raw = null;
  try {
    raw = sessionStorage.getItem(PENDING_KEY);
    sessionStorage.removeItem(PENDING_KEY);
  } catch (err) { debug('pending toast read failed', err); return; }
  if (!raw) return;
  try { toast(JSON.parse(raw)); }
  catch (err) { debug('pending toast parse failed', err); }
}
