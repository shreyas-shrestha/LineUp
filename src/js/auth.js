// Identity: sign in (Firebase Google/email when the server has a Firebase web
// config, the developer sign-in otherwise), the account menu in the app
// header, the account page identity block, and sign-out. There is no
// onboarding step: every account is a client. The session itself lives in
// session.js; api.js sends the token.
import { byId, setBusy, setFieldError, clearFieldError, clearFormErrors } from './dom.js';
import { api, ApiError, setTokenRefresher } from './api.js';
import { store, clearUserState } from './state.js';
import { getSession, getUser, isSignedIn, authMode, setSession, updateToken, clearSession, onSessionChange } from './session.js';
import { onRoute, rememberNext, signInHash, continueAfterAuth } from './router.js';
import { toastAfterReload } from './ui/toast.js';
import { initials } from './format.js';
import { debug } from './env.js';

const FIREBASE_VERSION = '10.14.1';
const FIREBASE_BASE = `https://www.gstatic.com/firebasejs/${FIREBASE_VERSION}`;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const els = {};
let capabilities = null;
let firebase = null; // { app, auth, mod } once loaded
let createMode = false;

// -- capabilities -> which sign-in UI to show ---------------------------------

function firebaseConfig() {
  const auth = capabilities && capabilities.auth;
  return auth && auth.mode === 'firebase' && auth.firebase && auth.firebase.apiKey ? auth.firebase : null;
}

function devLoginEnabled() {
  const auth = capabilities && capabilities.auth;
  return Boolean(auth && (auth.mode === 'dev' || auth.devLogin));
}

function configureSignIn() {
  const config = firebaseConfig();
  const unknown = capabilities == null;
  const unavailable = Boolean(capabilities && capabilities.unavailable);
  els.firebaseBlock.classList.toggle('hidden', !(config || unknown));
  els.googleBtn.disabled = !config;
  els.submit.disabled = !config;
  els.unavailable.classList.toggle('hidden', Boolean(config) || unknown);
  const title = els.unavailable.querySelector('.notice-title');
  const text = els.unavailable.querySelector('.notice-text');
  if (unavailable) {
    title.textContent = 'Could not reach the LineUp service';
    text.textContent = 'Sign-in needs the API. Check your connection and reload.';
  } else if (devLoginEnabled()) {
    title.textContent = 'Sign-in is not configured on this server';
    text.textContent = 'Google and email sign-in need Firebase keys. In development, use the developer sign-in below.';
  } else {
    title.textContent = 'Sign-in is not configured on this server';
    text.textContent = 'Google and email sign-in need Firebase keys. Ask whoever runs this deployment to add them.';
  }
  els.devCard.classList.toggle('hidden', !devLoginEnabled());
  els.devCard.hidden = !devLoginEnabled();
}

// -- Firebase (loaded only when the server publishes a web config) -----------

async function loadFirebase() {
  if (firebase) return firebase;
  const config = firebaseConfig();
  if (!config) throw new ApiError('Google and email sign-in are not configured on this server.');
  const [appMod, authMod] = await Promise.all([
    import(`${FIREBASE_BASE}/firebase-app.js`),
    import(`${FIREBASE_BASE}/firebase-auth.js`),
  ]);
  const app = appMod.getApps().length ? appMod.getApp() : appMod.initializeApp(config);
  const auth = authMod.getAuth(app);
  firebase = { app, auth, mod: authMod };
  setTokenRefresher(async () => {
    const user = auth.currentUser;
    if (!user) return null;
    const token = await user.getIdToken(true);
    updateToken(token);
    return token;
  });
  authMod.onIdTokenChanged(auth, async (user) => {
    if (!user || !isSignedIn() || authMode() !== 'firebase') return;
    try { updateToken(await user.getIdToken()); } catch (err) { debug('token refresh failed', err); }
  });
  return firebase;
}

function firebaseMessage(err) {
  const code = (err && err.code) || '';
  const map = {
    'auth/invalid-credential': 'Email or password is incorrect.',
    'auth/invalid-login-credentials': 'Email or password is incorrect.',
    'auth/user-not-found': 'No account with that email. Create one below.',
    'auth/wrong-password': 'Email or password is incorrect.',
    'auth/invalid-email': 'Enter a valid email address.',
    'auth/email-already-in-use': 'There is already an account with that email. Sign in instead.',
    'auth/weak-password': 'Use at least 8 characters.',
    'auth/popup-closed-by-user': 'The Google window was closed before finishing.',
    'auth/cancelled-popup-request': 'The Google window was closed before finishing.',
    'auth/popup-blocked': 'The browser blocked the Google window. Allow pop-ups and try again.',
    'auth/network-request-failed': 'Could not reach Google. Check your connection.',
    'auth/too-many-requests': 'Too many attempts. Wait a minute and try again.',
    'auth/operation-not-allowed': 'This sign-in method is switched off for this project.',
    'auth/unauthorized-domain': "This site's domain is not on the Firebase project's authorised list, so sign-in was refused. Whoever runs this deployment adds it under Authentication, Settings, Authorized domains.",
    'auth/configuration-not-found': 'Sign-in is not finished being set up on the Firebase project for this site.',
    'auth/internal-error': 'Firebase returned an internal error. Try again in a moment.',
    'auth/timeout': 'Sign-in timed out. Check the connection and try again.',
    'auth/web-storage-unsupported': 'This browser is blocking the storage sign-in needs. Allow cookies for this site, or leave private browsing.',
  };
  if (map[code]) return map[code];
  if (err instanceof ApiError) return err.message;
  // Naming the code beats a dead end: an unmapped failure is almost always a
  // console setting, and the code is the only thing that says which one.
  return code ? `Sign-in did not finish (${code}). Try again.` : 'Sign-in did not finish. Try again.';
}

async function completeFirebaseSignIn(credential) {
  const token = await credential.user.getIdToken();
  const me = await api.me(token);
  setSession({ token, user: me.user, mode: 'firebase' });
  return me.user;
}

export async function signInWithGoogle() {
  const { auth, mod } = await loadFirebase();
  const provider = new mod.GoogleAuthProvider();
  provider.setCustomParameters({ prompt: 'select_account' });
  const credential = await mod.signInWithPopup(auth, provider);
  return completeFirebaseSignIn(credential);
}

export async function signInWithEmail(email, password) {
  const { auth, mod } = await loadFirebase();
  const credential = await mod.signInWithEmailAndPassword(auth, email, password);
  return completeFirebaseSignIn(credential);
}

export async function createAccount(email, password) {
  const { auth, mod } = await loadFirebase();
  const credential = await mod.createUserWithEmailAndPassword(auth, email, password);
  return completeFirebaseSignIn(credential);
}

export async function signInAsDeveloper(email, name) {
  const data = await api.devLogin(email, name);
  if (!data || !data.token || !data.user) throw new ApiError('The server did not return a session.');
  setSession({ token: data.token, user: data.user, mode: 'dev', expiresAt: data.expiresAt || null });
  return data.user;
}

// Ask the server who we are (refreshes credits after a reload).
export async function refreshSession() {
  if (!isSignedIn()) return null;
  try {
    const me = await api.me();
    if (me && me.user) setSession({ token: getSession().token, user: me.user });
    return me;
  } catch (err) {
    debug('session refresh failed', err);
    return null;
  }
}

export async function signOut() {
  if (authMode() === 'firebase' && firebase) {
    try { await firebase.mod.signOut(firebase.auth); } catch (err) { debug('firebase sign-out failed', err); }
  }
  clearSession();
  clearUserState();
  // A reload guarantees no per-user data lingers in module state.
  window.location.replace(`${window.location.pathname}${window.location.search}#/`);
  window.location.reload();
}

// -- sign-in view -------------------------------------------------------------

function setCreateMode(value) {
  createMode = value;
  els.title.textContent = value ? 'Create your LineUp account' : 'Sign in to LineUp';
  els.lead.textContent = value
    ? 'Use your Google account or pick an email and password. You start with 3 free credits.'
    : 'Use your Google account or your email. New here? Create an account below.';
  els.submit.textContent = value ? 'Create account' : 'Sign in';
  els.modeText.textContent = value ? 'Already have an account?' : 'New to LineUp?';
  els.modeToggle.textContent = value ? 'Sign in' : 'Create an account';
  els.modeToggle.setAttribute('aria-pressed', value ? 'true' : 'false');
  els.password.setAttribute('autocomplete', value ? 'new-password' : 'current-password');
  clearFieldError(els.error, els.email, els.password);
}

async function submitEmailForm(event) {
  event.preventDefault();
  clearFormErrors(els.form);
  const email = els.email.value.trim();
  const password = els.password.value;
  if (!EMAIL_RE.test(email)) { setFieldError(els.error, 'Enter a valid email address.', els.email); return; }
  if (password.length < 8) { setFieldError(els.error, 'Use at least 8 characters.', els.password); return; }
  setBusy(els.submit, true, createMode ? 'Creating…' : 'Signing in…');
  try {
    if (createMode) await createAccount(email, password);
    else await signInWithEmail(email, password);
    continueAfterAuth();
  } catch (err) {
    debug('email sign-in failed', err);
    setFieldError(els.error, firebaseMessage(err));
  } finally {
    setBusy(els.submit, false);
  }
}

async function googleSignIn() {
  clearFormErrors(els.form);
  setBusy(els.googleBtn, true, 'Opening Google…');
  try {
    await signInWithGoogle();
    continueAfterAuth();
  } catch (err) {
    debug('google sign-in failed', err);
    setFieldError(els.error, firebaseMessage(err));
  } finally {
    setBusy(els.googleBtn, false);
  }
}

async function submitDevForm(event) {
  event.preventDefault();
  clearFormErrors(els.devForm);
  const email = els.devEmail.value.trim().toLowerCase();
  const name = els.devName.value.trim();
  if (!EMAIL_RE.test(email)) { setFieldError(els.devError, 'Enter a valid email address.', els.devEmail); return; }
  setBusy(els.devSubmit, true, 'Signing in…');
  try {
    await signInAsDeveloper(email, name || email.split('@')[0]);
    continueAfterAuth();
  } catch (err) {
    debug('dev sign-in failed', err);
    setFieldError(els.devError, err instanceof ApiError ? err.message : 'Sign-in did not finish. Try again.');
  } finally {
    setBusy(els.devSubmit, false);
  }
}

// -- header menu + account identity -------------------------------------------

function paintAvatar(node, user, { size = 'sm' } = {}) {
  if (!node) return;
  if (user && user.photoUrl) {
    node.innerHTML = '';
    const img = document.createElement('img');
    img.src = user.photoUrl;
    img.alt = '';
    img.width = size === 'xl' ? 64 : 32;
    img.height = size === 'xl' ? 64 : 32;
    img.referrerPolicy = 'no-referrer';
    img.addEventListener('error', () => { node.textContent = initials(user.name || user.email); }, { once: true });
    node.appendChild(img);
  } else if (user && (user.name || user.email)) {
    node.textContent = initials(user.name || user.email);
  } else {
    node.innerHTML = '<svg class="icon icon-sm" aria-hidden="true"><use href="#i-user"/></svg>';
  }
}

function paintIdentity(user) {
  const signedIn = Boolean(user);
  els.menuName.textContent = signedIn ? (user.name || user.email || 'Signed in') : 'Not signed in';
  els.menuEmail.textContent = signedIn ? (user.email || '') : '';
  paintAvatar(els.menuAvatar, user);

  els.accountName.textContent = signedIn ? (user.name || 'Member') : 'Not signed in';
  els.accountEmail.textContent = signedIn ? (user.email || '') : '';
  paintAvatar(els.accountAvatar, user, { size: 'xl' });
}

function toggleMenu(open) {
  const isOpen = open ?? els.menuPanel.classList.contains('hidden');
  els.menuPanel.classList.toggle('hidden', !isOpen);
  els.menuButton.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  if (isOpen) {
    const first = els.menuPanel.querySelector('.menu-item');
    if (first) first.focus({ preventScroll: true });
  }
}

function closeMenu({ restoreFocus = false } = {}) {
  if (els.menuPanel.classList.contains('hidden')) return;
  toggleMenu(false);
  if (restoreFocus) els.menuButton.focus({ preventScroll: true });
}

// -- wiring -------------------------------------------------------------------

export function initAuth() {
  Object.assign(els, {
    firebaseBlock: byId('signin-firebase'),
    unavailable: byId('signin-unavailable'),
    devCard: byId('dev-signin'),
    googleBtn: byId('signin-google'),
    form: byId('signin-form'),
    email: byId('signin-email'),
    password: byId('signin-password'),
    error: byId('signin-error'),
    submit: byId('signin-submit'),
    title: byId('signin-title'),
    lead: byId('signin-lead'),
    modeText: byId('signin-mode-text'),
    modeToggle: byId('signin-mode-toggle'),
    devForm: byId('dev-signin-form'),
    devEmail: byId('dev-email'),
    devName: byId('dev-name'),
    devError: byId('dev-signin-error'),
    devSubmit: byId('dev-signin-submit'),
    menuButton: byId('account-menu'),
    menuPanel: byId('account-menu-panel'),
    menuAvatar: byId('account-menu-avatar'),
    menuName: byId('menu-name'),
    menuEmail: byId('menu-email'),
    accountAvatar: byId('account-avatar'),
    accountName: byId('account-name'),
    accountEmail: byId('account-email'),
  });

  getSession();
  configureSignIn();
  paintIdentity(getUser());
  onSessionChange(paintIdentity);
  store.subscribe('capabilities', (value) => {
    capabilities = value;
    configureSignIn();
    // A restored Firebase session needs the SDK for token refresh.
    if (isSignedIn() && authMode() === 'firebase' && firebaseConfig()) loadFirebase().catch((err) => debug('firebase load failed', err));
  });

  els.form.addEventListener('submit', submitEmailForm);
  els.googleBtn.addEventListener('click', googleSignIn);
  els.modeToggle.addEventListener('click', () => setCreateMode(!createMode));
  els.devForm.addEventListener('submit', submitDevForm);

  els.menuButton.addEventListener('click', () => toggleMenu());
  document.addEventListener('click', (event) => {
    if (!(event.target instanceof Element)) return;
    if (event.target.closest('#account-menu-panel .menu-item')) { closeMenu(); return; }
    if (!event.target.closest('.menu-wrap')) closeMenu();
  });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeMenu({ restoreFocus: true }); });
  byId('menu-sign-out').addEventListener('click', () => signOut());
  byId('sign-out').addEventListener('click', () => signOut());

  document.addEventListener('lineup:unauthorized', () => {
    const hash = window.location.hash || '#/';
    const gated = /^#\/(client|account)/.test(hash);
    if (gated) rememberNext(hash);
    toastAfterReload({ type: 'info', title: 'Signed out', text: 'Your session ended. Sign in to continue.' });
    clearUserState();
    window.location.replace(`${window.location.pathname}${window.location.search}${gated ? signInHash(hash) : '#/'}`);
    window.location.reload();
  });

  onRoute((route, { viewChanged }) => {
    if (route.name === 'signin' && viewChanged) {
      setCreateMode(false);
      clearFormErrors(els.devForm);
      const focusTarget = firebaseConfig() ? els.email : (devLoginEnabled() ? els.devEmail : null);
      if (focusTarget) focusTarget.focus({ preventScroll: true });
    }
    if (route.name !== 'app' && route.name !== 'account') closeMenu();
  });

  // Keep the stored user fresh (name, credits) after a reload.
  if (isSignedIn()) refreshSession();
}
