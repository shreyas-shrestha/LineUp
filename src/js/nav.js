// App tabs inside #view-app. The hash is the single source of truth:
// navigate() writes location.hash, router.js applies it (with the auth gate)
// and calls applyTab(), so back/forward and deep links (#/client/explore)
// all take the same path. The Account entry is a plain link to #/account,
// which is its own view rather than a tab.
import { $$, byId, html } from './dom.js';
import { icon } from './icons.js';
import { store } from './state.js';
import { debug } from './env.js';

const TABS = [
  { key: 'ai', slug: 'home', label: 'Home', icon: 'home' },
  { key: 'barbers', slug: 'explore', label: 'Explore', icon: 'search' },
  { key: 'account', slug: 'account', label: 'Account', icon: 'user', href: '#/account' },
];

const hooks = new Map();
let current = null;

const findTab = (key) => TABS.find((tab) => tab.key === key);
const findBySlug = (slug) => TABS.find((tab) => tab.slug === slug);

export function currentTab() { return current; }
export function defaultTab() { return TABS[0].key; }

export function onTabShow(key, fn) {
  if (!hooks.has(key)) hooks.set(key, new Set());
  hooks.get(key).add(fn);
  return () => hooks.get(key).delete(fn);
}

export function hashFor(key) {
  const tab = findTab(key);
  return `#/client/${tab ? tab.slug : key}`;
}

// "#/client/explore" -> { tab: 'barbers' } or null. Account is a view, not a tab.
export function parseAppHash(hash) {
  const match = /^#\/client\/([a-z-]+)\/?(?:\?.*)?$/.exec(hash || '');
  if (!match) return null;
  const tab = findBySlug(match[1]);
  return tab && !tab.href ? { tab: tab.key } : null;
}

export function navigate(key, { replace = false } = {}) {
  const target = hashFor(key);
  if (window.location.hash === target) { applyTab(key); return; }
  if (replace) {
    window.history.replaceState(null, '', target);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  } else {
    window.location.hash = target;
  }
}

function renderBottomNav() {
  const nav = byId('bottom-nav');
  if (!nav || nav.firstElementChild) return;
  nav.innerHTML = html`<div class="bottom-nav-list">${TABS.map((tab) => (tab.href
    ? html`<a class="tab-pill" href="${tab.href}">${icon(tab.icon)}<span>${tab.label}</span></a>`
    : html`<button type="button" class="tab-pill" data-tab="${tab.key}">${icon(tab.icon)}<span>${tab.label}</span></button>`))}</div>`;
}

export function applyTab(tab, { initial = false } = {}) {
  const tabChanged = tab !== current;
  current = tab;
  renderBottomNav();

  $$('.tab-content').forEach((section) => section.classList.toggle('hidden', section.id !== `${tab}-tab-content`));
  $$('#bottom-nav .tab-pill').forEach((button) => {
    if (button.dataset.tab === tab) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });

  const meta = findTab(tab);
  document.title = `${meta ? meta.label : 'LineUp'} · LineUp`;
  store.set('tab', tab);

  if (!initial && tabChanged) {
    window.scrollTo({ top: 0 });
    const main = byId('main-content');
    if (main && !document.activeElement?.closest('.modal-backdrop')) main.focus({ preventScroll: true });
  }
  (hooks.get(tab) || []).forEach((fn) => { try { fn({ tab, initial }); } catch (err) { debug('tab hook failed', tab, err); } });
}

export function initNav() {
  document.addEventListener('click', (event) => {
    const trigger = event.target instanceof Element ? event.target.closest('[data-tab]') : null;
    if (trigger) navigate(trigger.dataset.tab);
  });
}
