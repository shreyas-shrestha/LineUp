// The signed-in session: bearer token + user document, persisted in
// localStorage so a reload keeps you signed in. auth.js writes it, api.js
// reads the token, everything else reads the user through state.js.
import { store } from './state.js';
import { debug } from './env.js';

const KEY = 'lineup.session.v1';
export const HOME_HASH = '#/client/home';
const listeners = new Set();
let session = null;
let loaded = false;

function load() {
  if (loaded) return session;
  loaded = true;
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    session = parsed && parsed.token && parsed.user && parsed.user.uid ? parsed : null;
  } catch (err) {
    debug('session read failed', err);
    session = null;
  }
  store.set('user', session ? session.user : null);
  return session;
}

function persist() {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session));
    else localStorage.removeItem(KEY);
  } catch (err) {
    debug('session write failed', err);
  }
}

function emit() {
  store.set('user', session ? session.user : null);
  listeners.forEach((fn) => { try { fn(session ? session.user : null); } catch (err) { debug('session listener failed', err); } });
}

export function getSession() { return load(); }
export function getToken() { return load()?.token || null; }
export function getUser() { return load()?.user || null; }
export function isSignedIn() { return Boolean(getToken()); }
export function authMode() { return load()?.mode || null; }

export function setSession({ token, user, mode, expiresAt }) {
  load();
  session = { token, user, mode: mode || session?.mode || null, expiresAt: expiresAt || null };
  persist();
  emit();
  return session.user;
}

export function updateToken(token) {
  load();
  if (!session || !token || session.token === token) return;
  session = { ...session, token };
  persist();
}

export function clearSession() {
  load();
  session = null;
  persist();
  emit();
}

export function onSessionChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
