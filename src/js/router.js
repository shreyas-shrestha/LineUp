// Hash router for the whole site. Exactly one `.view` is visible at a time;
// #app-header only for the app and account views. Public: landing, pricing,
// legal, sign-in. Gated: the app (#/client/*, #/barber/*), onboarding and the
// account page need a session; a user without a role is sent to onboarding;
// a client asking for #/barber/* lands on their own home.
import { $$, byId } from './dom.js';
import { store } from './state.js';
import { getUser, isSignedIn, homeHashFor } from './session.js';
import { parseAppHash, applyTab, defaultTab } from './nav.js';
import { debug } from './env.js';

const NEXT_KEY = 'lineup.next';
const TITLES = {
  landing: 'LineUp – Find a cut that fits your face',
  pricing: 'Pricing · LineUp',
  signin: 'Sign in · LineUp',
  onboarding: 'Choose how you use LineUp · LineUp',
  account: 'Account · LineUp',
  legal: { terms: 'Terms of service · LineUp', privacy: 'Privacy policy · LineUp' },
};

const routeListeners = new Set();
let currentRoute = null;
let pendingScroll = null;

export function currentView() { return currentRoute ? currentRoute.name : null; }
export function onRoute(fn) { routeListeners.add(fn); return () => routeListeners.delete(fn); }

// "#/signin?next=%23%2Fclient%2Fhome" -> { name, path, query }
export function parseRoute(hash) {
  const raw = String(hash || '');
  const queryIndex = raw.indexOf('?');
  const path = (queryIndex >= 0 ? raw.slice(0, queryIndex) : raw).replace(/\/+$/, '') || '#';
  const query = new URLSearchParams(queryIndex >= 0 ? raw.slice(queryIndex + 1) : '');
  if (path === '#' || path === '#/') return { name: 'landing', query };
  if (path === '#/pricing') return { name: 'pricing', query };
  if (path === '#/signin') return { name: 'signin', query };
  if (path === '#/onboarding') return { name: 'onboarding', query };
  if (path === '#/account') return { name: 'account', query };
  const legal = /^#\/legal\/(terms|privacy)$/.exec(path);
  if (legal) return { name: 'legal', page: legal[1], query };
  const app = parseAppHash(path);
  if (app) return { name: 'app', mode: app.mode, tab: app.tab, query };
  return null;
}

export function go(hash, { replace = false } = {}) {
  if (window.location.hash === hash) { applyRoute(); return; }
  if (replace) {
    window.history.replaceState(null, '', hash);
    applyRoute();
  } else {
    window.location.hash = hash;
  }
}

export function rememberNext(hash) {
  try {
    if (hash && /^#\/(client|barber|account|onboarding)/.test(hash)) sessionStorage.setItem(NEXT_KEY, hash);
    else sessionStorage.removeItem(NEXT_KEY);
  } catch (err) { debug('next write failed', err); }
}

export function takeNext() {
  try {
    const next = sessionStorage.getItem(NEXT_KEY);
    sessionStorage.removeItem(NEXT_KEY);
    return next && parseRoute(next) ? next : null;
  } catch (err) { debug('next read failed', err); return null; }
}

export function signInHash(next) {
  return next ? `#/signin?next=${encodeURIComponent(next)}` : '#/signin';
}

// Where a signed-in user should go after sign-in/onboarding.
// preferHome (after onboarding): a brand-new account starts on its own home
// rather than whatever app tab the deep link pointed at; non-app targets
// such as #/account are still honoured.
export function continueAfterAuth({ replace = true, preferHome = false } = {}) {
  const user = getUser();
  if (!user) { go('#/signin', { replace }); return; }
  if (!user.role) { go('#/onboarding', { replace }); return; }
  const next = takeNext();
  const route = next ? parseRoute(next) : null;
  const useNext = route && allowed(route, user) && !(preferHome && route.name === 'app');
  go(useNext ? next : homeHashFor(user), { replace });
}

function allowed(route, user) {
  if (!route) return false;
  if (route.name === 'app') return route.mode !== 'barber' || (user && user.role === 'barber');
  return true;
}

function setAuthVisibility() {
  const signedIn = isSignedIn();
  const home = homeHashFor(getUser());
  $$('[data-auth]').forEach((node) => {
    const wants = node.dataset.auth === 'signed-in';
    node.classList.toggle('hidden', wants !== signedIn);
    if (wants && node instanceof HTMLAnchorElement && /^#\/(client|barber)\//.test(node.getAttribute('href') || '')) node.setAttribute('href', home);
  });
}

function showView(name) {
  $$('.view').forEach((view) => {
    const visible = view.id === `view-${name}`;
    view.hidden = !visible;
    view.classList.toggle('hidden', !visible);
  });
  const header = byId('app-header');
  const withHeader = name === 'app' || name === 'account';
  header.hidden = !withHeader;
  header.classList.toggle('hidden', !withHeader);
  document.body.classList.toggle('has-app-header', withHeader);
  document.body.dataset.view = name;
}

function fillLegal(page) {
  const template = byId(`legal-${page}-template`);
  const body = byId('legal-body');
  if (template && body) body.replaceChildren(template.content.cloneNode(true));
  byId('legal-title').textContent = page === 'privacy' ? 'Privacy policy' : 'Terms of service';
  $$('[data-legal]').forEach((link) => {
    if (link.dataset.legal === page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
}

function scrollAfterRoute(viewChanged) {
  if (pendingScroll) {
    const target = byId(pendingScroll);
    pendingScroll = null;
    if (target) {
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
      return;
    }
  }
  if (viewChanged) window.scrollTo({ top: 0 });
}

// Resolve guards for the requested route. Returns the hash to redirect to, or null.
function redirectFor(route) {
  const user = getUser();
  const signedIn = isSignedIn();
  const hash = window.location.hash || '#/';
  if (!route) return signedIn && user && user.role ? homeHashFor(user) : '#/';
  switch (route.name) {
    case 'app':
    case 'account':
      if (!signedIn) { rememberNext(hash); return signInHash(hash); }
      if (!user.role) { rememberNext(hash); return '#/onboarding'; }
      if (route.name === 'app' && !allowed(route, user)) return homeHashFor(user);
      return null;
    case 'onboarding':
      if (!signedIn) { rememberNext(hash); return signInHash(hash); }
      if (user.role) return takeNext() || homeHashFor(user);
      return null;
    case 'signin': {
      const next = route.query.get('next');
      if (next) rememberNext(next);
      if (signedIn) return user.role ? (takeNext() || homeHashFor(user)) : '#/onboarding';
      return null;
    }
    default:
      return null;
  }
}

export function applyRoute({ initial = false } = {}) {
  const hash = window.location.hash || '#/';
  const route = parseRoute(hash);
  const redirect = redirectFor(route);
  if (redirect && redirect !== hash) {
    window.history.replaceState(null, '', redirect);
    applyRoute({ initial });
    return;
  }
  const resolved = route || { name: 'landing', query: new URLSearchParams() };
  const viewChanged = !currentRoute || currentRoute.name !== resolved.name || (resolved.name === 'legal' && currentRoute.page !== resolved.page);
  currentRoute = resolved;
  setAuthVisibility();
  showView(resolved.name);

  if (resolved.name === 'app') {
    applyTab(resolved.mode, resolved.tab, { initial: initial || viewChanged });
  } else if (resolved.name === 'legal') {
    fillLegal(resolved.page);
    document.title = TITLES.legal[resolved.page];
  } else {
    document.title = TITLES[resolved.name] || 'LineUp';
  }
  store.set('view', resolved.name);
  if (!initial) scrollAfterRoute(viewChanged);
  else scrollAfterRoute(false);
  routeListeners.forEach((fn) => { try { fn(resolved, { initial, viewChanged }); } catch (err) { debug('route listener failed', err); } });
}

// Landing nav links: scroll to a section when already on the landing page,
// otherwise route there first and scroll once it is visible.
function handleScrollLinks(event) {
  const link = event.target instanceof Element ? event.target.closest('[data-scroll-to]') : null;
  if (!link) return;
  event.preventDefault();
  pendingScroll = link.dataset.scrollTo;
  if (currentRoute && currentRoute.name === 'landing') {
    scrollAfterRoute(false);
  } else {
    go('#/');
  }
}

// Re-run the guards when the session changes (sign-out on a gated page, or
// onboarding completing) without touching the hash.
export function refreshRoute() { applyRoute(); }

export function initRouter() {
  document.addEventListener('click', handleScrollLinks);
  window.addEventListener('hashchange', () => applyRoute());
  applyRoute({ initial: true });
}

