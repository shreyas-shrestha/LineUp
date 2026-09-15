// Tiny store plus localStorage persistence for per-user preferences and the
// last analysis. Identity comes from the signed-in user (session.js keeps
// store['user'] current): clientId and barberId are both the account uid.
import { debug } from './env.js';

const KEYS = {
  prefs: 'lineup.prefs.v1',
  analysis: 'lineup.analysis.v1',
  image: 'lineup.analysis-image.v1',
};

function read(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value == null ? fallback : JSON.parse(value);
  } catch (err) {
    debug('storage read failed', key, err);
    return fallback;
  }
}

function write(key, value) {
  try {
    if (value == null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (err) {
    debug('storage write failed', key, err);
    return false;
  }
}

function createStore(initial) {
  const data = { ...initial };
  const subscribers = new Map();
  return {
    get(key) { return data[key]; },
    set(key, value) {
      if (Object.is(data[key], value)) return;
      data[key] = value;
      (subscribers.get(key) || []).forEach((fn) => { try { fn(value); } catch (err) { debug('subscriber failed', key, err); } });
    },
    subscribe(key, fn) {
      if (!subscribers.has(key)) subscribers.set(key, new Set());
      subscribers.get(key).add(fn);
      return () => subscribers.get(key).delete(fn);
    },
  };
}

export const store = createStore({
  mode: 'client',
  tab: 'ai',
  user: null,
  billing: null,
  pricing: null,
  capabilities: null,
  clientAppointments: [],
  barberAppointments: [],
  portfolio: [],
});

// Device-local preferences, kept per account so two people sharing a browser
// do not see each other's search location or notification switches.
const PREF_DEFAULTS = {
  displayName: '',
  lastLocation: '',
  notifyBookings: true,
  notifyReminders: true,
  following: [],
};

function prefsKey(uid) { return `${KEYS.prefs}.${uid || 'anonymous'}`; }

function readPrefs(uid) {
  const prefs = { ...PREF_DEFAULTS, ...read(prefsKey(uid), {}) };
  if (!Array.isArray(prefs.following)) prefs.following = [];
  return prefs;
}

export function getIdentity() {
  const user = store.get('user');
  const uid = user ? user.uid : null;
  const prefs = readPrefs(uid);
  return {
    ...prefs,
    uid,
    clientId: uid,
    barberId: uid,
    role: user ? user.role : null,
    email: user ? user.email : '',
    photoUrl: user ? user.photoUrl : null,
    displayName: prefs.displayName || (user && user.name) || '',
    accountName: (user && user.name) || '',
  };
}

export function updateIdentity(patch) {
  const user = store.get('user');
  const uid = user ? user.uid : null;
  const next = { ...readPrefs(uid) };
  for (const key of Object.keys(PREF_DEFAULTS)) {
    if (key in patch) next[key] = patch[key];
  }
  write(prefsKey(uid), next);
  store.set('identity', getIdentity());
  return getIdentity();
}

export function getSavedAnalysis() { return read(KEYS.analysis, null); }
export function saveAnalysis(result) { return write(KEYS.analysis, result); }
export function getSavedImage() { return read(KEYS.image, null); }
export function saveImage(dataUrl) { return write(KEYS.image, dataUrl); }
export function clearAnalysis() { write(KEYS.analysis, null); write(KEYS.image, null); }

// Sign-out: drop everything that belongs to the person, keep nothing readable.
export function clearUserState() {
  clearAnalysis();
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(KEYS.prefs))
      .forEach((key) => localStorage.removeItem(key));
  } catch (err) {
    debug('prefs clear failed', err);
  }
}
