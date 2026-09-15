// Modal shell: open/close by backdrop id, focus moves to the heading on open
// and back to the opener on close, Tab is trapped inside the panel, Esc and
// backdrop clicks close, body scroll is locked while any modal is open.
// Modals stack (a confirm dialog can open above the services modal).
import { $$, byId } from '../dom.js';
import { debug } from '../env.js';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
const stack = [];
const closeHooks = new Map();
let pointerDownTarget = null;

function resolveFocus(panel, focus) {
  if (focus instanceof HTMLElement) return focus;
  if (typeof focus === 'string') {
    const match = panel.querySelector(focus);
    if (match) return match;
  }
  const title = panel.querySelector('.modal-title');
  if (title) {
    if (!title.hasAttribute('tabindex')) title.setAttribute('tabindex', '-1');
    return title;
  }
  return panel;
}

export function openModal(id, { focus } = {}) {
  const backdrop = byId(id);
  if (!backdrop) { debug('openModal: missing', id); return null; }
  if (stack.some((entry) => entry.id === id)) return backdrop;
  const panel = backdrop.querySelector('.modal') || backdrop;
  const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  stack.push({ id, backdrop, panel, opener });
  // Later modals sit above earlier ones (a confirm above the services modal).
  backdrop.style.zIndex = String(100 + stack.length);
  backdrop.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  const target = resolveFocus(panel, focus);
  if (target && typeof target.focus === 'function') target.focus({ preventScroll: true });
  return backdrop;
}

export function closeModal(id) {
  const index = id ? stack.findIndex((entry) => entry.id === id) : stack.length - 1;
  if (index < 0) return;
  const [entry] = stack.splice(index, 1);
  entry.backdrop.classList.add('hidden');
  entry.backdrop.style.zIndex = '';
  if (!stack.length) document.body.style.overflow = '';
  (closeHooks.get(entry.id) || []).forEach((fn) => { try { fn(); } catch (err) { debug('close hook failed', entry.id, err); } });
  const { opener } = entry;
  if (opener && opener.isConnected && !opener.closest('.modal-backdrop.hidden')) {
    opener.focus({ preventScroll: true });
  } else if (stack.length) {
    stack[stack.length - 1].panel.focus({ preventScroll: true });
  }
}

export function isModalOpen(id) { return stack.some((entry) => entry.id === id); }

export function onModalClose(id, fn) {
  if (!closeHooks.has(id)) closeHooks.set(id, new Set());
  closeHooks.get(id).add(fn);
  return () => closeHooks.get(id).delete(fn);
}

function trapTab(event, panel) {
  const items = $$(FOCUSABLE, panel).filter((node) => node.offsetParent !== null);
  if (!items.length) { event.preventDefault(); panel.focus(); return; }
  const first = items[0];
  const last = items[items.length - 1];
  const active = document.activeElement;
  const inside = panel.contains(active);
  if (event.shiftKey && (active === first || !inside)) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && (active === last || !inside)) { event.preventDefault(); first.focus(); }
}

export function initModals() {
  document.addEventListener('pointerdown', (event) => { pointerDownTarget = event.target; });
  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    const opener = target.closest('[data-open-modal]');
    if (opener) { openModal(opener.dataset.openModal); return; }
    const closer = target.closest('[data-modal-close]');
    if (closer) {
      const backdrop = closer.closest('.modal-backdrop');
      if (backdrop) closeModal(backdrop.id);
      return;
    }
    if (target.classList.contains('modal-backdrop') && pointerDownTarget === target) closeModal(target.id);
  });
  document.addEventListener('keydown', (event) => {
    const top = stack[stack.length - 1];
    if (!top) return;
    if (event.key === 'Escape') { event.preventDefault(); closeModal(top.id); return; }
    if (event.key === 'Tab') trapTab(event, top.panel);
  });
}
