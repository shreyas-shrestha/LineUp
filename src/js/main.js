// Entry point. Order matters: modals and features register their hooks,
// auth restores the session, billing wires the credits UI, then the router
// applies the hash (with the auth gate) and the backend capability ping
// tells the sign-in page which methods exist.
import { byId, show, hide } from './dom.js';
import { api, onConnectivity } from './api.js';
import { store } from './state.js';
import { initModals } from './ui/modal.js';
import { flushPendingToast } from './ui/toast.js';
import { initNav } from './nav.js';
import { initRouter } from './router.js';
import { initAuth } from './auth.js';
import { initBilling } from './billing.js';
import { initAnalysis } from './features/analysis.js';
import { initTryOn } from './features/tryon.js';
import { initBarbers } from './features/barbers.js';
import { initBooking } from './features/booking.js';
import { initAppointments } from './features/appointments.js';
import { initCommunity } from './features/community.js';
import { initDashboard } from './features/barber-dashboard.js';
import { initPortfolio } from './features/portfolio.js';
import { initShop } from './features/shop.js';
import { initProfile } from './features/profile.js';
import { initLanding } from './features/landing.js';
import { debug } from './env.js';

function initConnectivityNotice() {
  const notice = byId('api-notice');
  const retry = byId('api-notice-retry');
  const status = byId('footer-status');
  if (!notice) return;
  onConnectivity((down) => {
    if (down) show(notice); else hide(notice);
    if (status) status.textContent = down ? 'Service unreachable' : 'All systems normal';
  });
  retry.addEventListener('click', async () => {
    retry.disabled = true;
    try { await api.health(); } catch (err) { debug('still down', err); }
    retry.disabled = false;
  });
}

async function checkBackend() {
  try {
    const capabilities = await api.capabilities();
    store.set('capabilities', capabilities);
    debug('backend capabilities', capabilities);
  } catch (err) {
    debug('backend unavailable', err);
    store.set('capabilities', { unavailable: true, auth: { mode: 'unknown' } });
  }
}

function boot() {
  document.documentElement.classList.add('js');
  initModals();
  initConnectivityNotice();
  initAnalysis();
  initTryOn();
  initBarbers();
  initBooking();
  initAppointments();
  initCommunity();
  initDashboard();
  initPortfolio();
  initShop();
  initProfile();
  initNav();
  initAuth();
  initBilling();
  initRouter();
  initLanding();
  flushPendingToast();
  checkBackend();
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
}
