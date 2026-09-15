// App tabs and the client/barber mode inside #view-app. The hash is the
// single source of truth: navigate() writes location.hash, router.js applies
// it (with the auth/role guards) and calls applyTab(), so back/forward and
// deep links (#/barber/bookings) all take the same path.
import { $$, byId, html } from './dom.js';
import { icon } from './icons.js';
import { store } from './state.js';
import { debug } from './env.js';

const TABS = {
  client: [
    { key: 'ai', slug: 'home', label: 'Home', icon: 'home' },
    { key: 'barbers', slug: 'explore', label: 'Explore', icon: 'search' },
    { key: 'appointments', slug: 'bookings', label: 'Bookings', icon: 'calendar', raised: true },
    { key: 'community', slug: 'community', label: 'Community', icon: 'users' },
    { key: 'profile', slug: 'profile', label: 'Profile', icon: 'user' },
  ],
  barber: [
    { key: 'barber-dashboard', slug: 'dashboard', label: 'Home', icon: 'home' },
    { key: 'barber-schedule', slug: 'bookings', label: 'Bookings', icon: 'calendar' },
    { key: 'barber-portfolio', slug: 'work', label: 'Work', icon: 'scissors', raised: true },
    { key: 'community', slug: 'community', label: 'Community', icon: 'users' },
    { key: 'barber-profile', slug: 'shop', label: 'Shop', icon: 'store' },
  ],
};

const hooks = new Map();
const lastTabByMode = {};
let current = { mode: null, tab: null };

const findTab = (mode, key) => (TABS[mode] || []).find((tab) => tab.key === key);
const findBySlug = (mode, slug) => (TABS[mode] || []).find((tab) => tab.slug === slug);

export function currentMode() { return current.mode; }
export function currentTab() { return current.tab; }
export function defaultTab(mode) { return TABS[mode] ? TABS[mode][0].key : 'ai'; }

export function onTabShow(key, fn) {
  if (!hooks.has(key)) hooks.set(key, new Set());
  hooks.get(key).add(fn);
  return () => hooks.get(key).delete(fn);
}

export function hashFor(mode, key) {
  const tab = findTab(mode, key);
  return `#/${mode}/${tab ? tab.slug : key}`;
}

// "#/barber/bookings" -> { mode: 'barber', tab: 'barber-schedule' } or null.
export function parseAppHash(hash) {
  const match = /^#\/(client|barber)\/([a-z-]+)\/?(?:\?.*)?$/.exec(hash || '');
  if (!match) return null;
  const tab = findBySlug(match[1], match[2]);
  return tab ? { mode: match[1], tab: tab.key } : null;
}

function inferMode(key, preferred) {
  if (findTab(preferred, key)) return preferred;
  if (findTab('client', key)) return 'client';
  if (findTab('barber', key)) return 'barber';
  return preferred;
}

export function navigate(key, { mode, replace = false } = {}) {
  const targetMode = inferMode(key, mode || current.mode || 'client');
  const target = hashFor(targetMode, key);
  if (window.location.hash === target) { applyTab(targetMode, key); return; }
  if (replace) {
    window.history.replaceState(null, '', target);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  } else {
    window.location.hash = target;
  }
}

// Only barbers can enter barber mode; clients never see the switch.
export function canUseMode(mode) {
  if (mode !== 'barber') return true;
  const user = store.get('user');
  return Boolean(user && user.role === 'barber');
}

export function setMode(mode) {
  if (mode === current.mode || !canUseMode(mode)) return;
  navigate(lastTabByMode[mode] || defaultTab(mode), { mode });
}

function renderBottomNav(mode) {
  const nav = byId('bottom-nav');
  if (!nav) return;
  nav.innerHTML = html`<div class="bottom-nav-list">${TABS[mode].map((tab) => (tab.raised
    ? html`<button type="button" class="tab-pill tab-pill-raised" data-tab="${tab.key}" aria-label="${tab.label}">${icon(tab.icon)}</button>`
    : html`<button type="button" class="tab-pill" data-tab="${tab.key}">${icon(tab.icon)}<span>${tab.label}</span></button>`))}</div>`;
}

export function applyTab(mode, tab, { initial = false } = {}) {
  const modeChanged = mode !== current.mode;
  const tabChanged = tab !== current.tab;
  current = { mode, tab };
  lastTabByMode[mode] = tab;

  const clientButton = byId('client-mode');
  const barberButton = byId('barber-mode');
  if (clientButton && barberButton) {
    clientButton.classList.toggle('is-active', mode === 'client');
    clientButton.setAttribute('aria-pressed', String(mode === 'client'));
    barberButton.classList.toggle('is-active', mode === 'barber');
    barberButton.setAttribute('aria-pressed', String(mode === 'barber'));
  }
  byId('client-content').classList.toggle('hidden', mode !== 'client');
  byId('barber-content').classList.toggle('hidden', mode !== 'barber');

  if (modeChanged || !byId('bottom-nav').firstElementChild) renderBottomNav(mode);

  $$('.tab-content').forEach((section) => section.classList.toggle('hidden', section.id !== `${tab}-tab-content`));
  $$('#bottom-nav .tab-pill').forEach((button) => {
    if (button.dataset.tab === tab) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });

  const meta = findTab(mode, tab);
  document.title = `${meta ? meta.label : 'LineUp'} · LineUp`;
  store.set('mode', mode);
  store.set('tab', tab);

  if (!initial && (modeChanged || tabChanged)) {
    window.scrollTo({ top: 0 });
    const main = byId('main-content');
    if (main && !document.activeElement?.closest('.modal-backdrop')) main.focus({ preventScroll: true });
  }
  (hooks.get(tab) || []).forEach((fn) => { try { fn({ mode, tab, initial }); } catch (err) { debug('tab hook failed', tab, err); } });
}

export function initNav() {
  byId('client-mode').addEventListener('click', () => setMode('client'));
  byId('barber-mode').addEventListener('click', () => setMode('barber'));
  document.addEventListener('click', (event) => {
    const trigger = event.target instanceof Element ? event.target.closest('[data-tab]') : null;
    if (trigger) navigate(trigger.dataset.tab);
  });
}
