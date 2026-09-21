// One request() for every call: base URL from config, JSON in/out, bearer
// token from the session, timeout via AbortController, de-duplicated in-flight
// GETs, and a single connectivity signal so the "service unreachable" notice
// shows once instead of per request. Auth/billing outcomes are broadcast as
// DOM events so the modules that own the UI for them can react:
//   lineup:unauthorized       401 with a token -> session cleared (auth.js redirects)
//   lineup:payment-required   402 {error: insufficient_credits, ...}
//   lineup:credits            any response carrying a `billing` block (metered routes)
import { API_URL, debug } from './env.js';
import { getToken, clearSession } from './session.js';

export class ApiError extends Error {
  constructor(message, { status = 0, data = null, kind = 'http' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.kind = kind; // 'http' | 'network' | 'timeout' | 'aborted'
  }
  get isNetwork() { return this.kind === 'network'; }
  get code() { return (this.data && (this.data.code || this.data.error)) || ''; }
}

const inflight = new Map();
const connectivityListeners = new Set();
let apiDown = false;
let tokenRefresher = null; // auth.js registers a function returning a fresh token (Firebase)

export function setTokenRefresher(fn) { tokenRefresher = typeof fn === 'function' ? fn : null; }

export function onConnectivity(fn) {
  connectivityListeners.add(fn);
  return () => connectivityListeners.delete(fn);
}
function setApiDown(value) {
  if (apiDown === value) return;
  apiDown = value;
  connectivityListeners.forEach((fn) => { try { fn(value); } catch (err) { debug('connectivity listener failed', err); } });
}

function emit(name, detail) {
  if (typeof document === 'undefined') return;
  document.dispatchEvent(new CustomEvent(name, { detail }));
}

function buildUrl(path, query) {
  const url = new URL(API_URL + (path.startsWith('/') ? path : `/${path}`));
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value == null || value === '') continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export function request(path, { method = 'GET', body, query, timeout = 15000, signal, dedupe = true, auth = true, token } = {}) {
  const url = buildUrl(path, query);
  const bearer = token || (auth ? getToken() : null);
  const key = method === 'GET' && dedupe ? `${bearer ? 'u' : 'a'} ${url}` : null;
  if (key && inflight.has(key)) return inflight.get(key);
  const promise = performWithRefresh(url, { method, body, timeout, signal, bearer });
  if (key) {
    inflight.set(key, promise);
    promise.then(() => inflight.delete(key), () => inflight.delete(key));
  }
  return promise;
}

function friendlyMessage(status, data) {
  const code = data && (data.code || data.error);
  if (status === 402 && code === 'insufficient_credits') {
    const needed = Number(data.needed) || 1;
    return `This needs ${needed} credit${needed === 1 ? '' : 's'} and you have ${Number(data.credits) || 0}.`;
  }
  if (status === 401) return 'Your session has ended. Sign in again to continue.';
  if (status === 503 && code === 'stripe_not_configured') return 'Payments are not set up on this server yet.';
  if (status === 429) {
    const retry = Number(data && data.retry_after) || 0;
    if (code === 'daily_cap_reached') return `You have reached today's limit for this action. Try again in ${Math.max(1, Math.ceil(retry / 3600))} hours.`;
    return retry ? `Too many requests. Try again in ${retry} seconds.` : 'Too many requests. Wait a moment and try again.';
  }
  return (data && (data.message || data.error)) || `Request failed (${status}).`;
}

// An expired Firebase token gets one silent refresh + retry; anything else
// that is still 401 ends the session.
async function performWithRefresh(url, options) {
  try {
    return await perform(url, options);
  } catch (err) {
    const expired = err instanceof ApiError && err.status === 401 && options.bearer && tokenRefresher
      && ['token_expired', 'invalid_token'].includes(err.code) && !options.retried;
    if (!expired) throw err;
    let fresh = null;
    try { fresh = await tokenRefresher(); } catch (refreshErr) { debug('token refresh failed', refreshErr); }
    if (!fresh || fresh === options.bearer) {
      clearSession();
      emit('lineup:unauthorized', { url });
      throw err;
    }
    return perform(url, { ...options, bearer: fresh, retried: true });
  }
}

async function perform(url, { method, body, timeout, signal, bearer, retried = false }) {
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
  if (signal) signal.addEventListener('abort', () => controller.abort(), { once: true });

  const init = { method, headers: { Accept: 'application/json' }, signal: controller.signal, mode: 'cors' };
  if (bearer) init.headers.Authorization = `Bearer ${bearer}`;
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, init);
  } catch (err) {
    clearTimeout(timer);
    if (timedOut) throw new ApiError('The request took too long. Try again.', { kind: 'timeout' });
    if (controller.signal.aborted) throw new ApiError('Request cancelled.', { kind: 'aborted' });
    debug('network error', method, url, err);
    setApiDown(true);
    throw new ApiError('Could not reach the LineUp service.', { kind: 'network' });
  }
  clearTimeout(timer);

  let data = null;
  const text = await response.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = null; }
  }
  setApiDown(false);

  if (!response.ok) {
    const status = response.status;
    if (status === 429 && data && !data.retry_after) {
      const header = Number(response.headers.get('Retry-After')) || 0;
      if (header) data = { ...data, retry_after: header };
    }
    const message = friendlyMessage(status, data);
    debug('http error', status, method, url, data);
    const code = data && (data.code || data.error);
    const refreshable = !retried && tokenRefresher && ['token_expired', 'invalid_token'].includes(code);
    if (status === 401 && bearer && bearer === getToken() && !refreshable) {
      clearSession();
      emit('lineup:unauthorized', { url });
    } else if (status === 402 && data) {
      emit('lineup:payment-required', { ...data, code: data.code || data.error });
    }
    throw new ApiError(message, { status, data });
  }
  if (data && data.billing && typeof data.billing.credits === 'number') emit('lineup:credits', data.billing);
  return data ?? {};
}

const enc = encodeURIComponent;
const post = (path, body = {}, options = {}) => request(path, { method: 'POST', body, ...options });

// Typed helpers, one per endpoint the UI uses. Paths match the backend contract.
export const api = {
  health: () => request('/health', { timeout: 8000, dedupe: false, auth: false }),
  capabilities: () => request('/config', { timeout: 8000, auth: false }),

  // auth
  me: (token) => request('/auth/me', { dedupe: false, token }),
  devLogin: (email, name) => post('/auth/dev-login', { email, name }, { auth: false }),

  // billing
  pricing: () => request('/billing/pricing', { auth: false }),
  billingMe: () => request('/billing/me', { dedupe: false }),
  usage: (limit = 50) => request('/billing/usage', { query: { limit }, dedupe: false }),
  checkout: (body) => post('/billing/checkout', body),
  portal: () => post('/billing/portal'),
  devGrant: (credits = 10) => post('/billing/dev-grant', { credits }),

  // paid actions
  analyze: (base64) => post('/analyze', { image: base64 }, { timeout: 60000 }),
  tryOn: (base64, styleDescription) => post('/virtual-tryon', { userPhoto: base64, styleDescription }, { timeout: 120000 }),

  // barbers
  barbers: (location, styles = []) => request('/barbers', { query: { location, styles: styles.join(',') }, timeout: 25000 }),
  reviews: (barberId) => request(`/barbers/${enc(barberId)}/reviews`),
};
