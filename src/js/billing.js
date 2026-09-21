// Credits: pricing cards (landing, pricing page, account, the out-of-credits
// modal), the header credits pill, Stripe Checkout / portal redirects, the
// usage ledger, and the 402 handling (insufficient_credits -> modal).
import { byId, html, setBusy, setFieldError, clearFieldError, delegate } from './dom.js';
import { icon } from './icons.js';
import { api, ApiError } from './api.js';
import { store } from './state.js';
import { getUser, isSignedIn, onSessionChange } from './session.js';
import { go, onRoute, rememberNext, signInHash } from './router.js';
import { openModal, closeModal, isModalOpen } from './ui/modal.js';
import { notify } from './ui/toast.js';
import { debug } from './env.js';

const DEFAULT_COSTS = { analysis: 1, tryon: 3, barber_search: 1 };
const ACTION_LABELS = { analysis: 'Analysis', tryon: 'Preview', barber_search: 'Barber search' };
const PACK_COPY = {
  starter: 'Enough for a few analyses and one preview.',
  plus: 'Try several cuts on your photo before you commit.',
  studio: 'For stylists and people who change their cut often.',
};

const els = {};
let pricing = null;
let billing = null;
let usageLoaded = false;

// -- helpers ------------------------------------------------------------------

const cents = (value) => `$${(Number(value || 0) / 100).toFixed(2).replace(/\.00$/, '')}`;
const perCredit = (pack) => `$${(Number(pack.price_cents) / 100 / Math.max(1, Number(pack.credits))).toFixed(2)} per credit`;

export function getCreditCost(action) {
  const costs = (billing && billing.entitlements && billing.entitlements.credit_costs)
    || (pricing && pricing.credit_costs)
    || DEFAULT_COSTS;
  return Number(costs[action] ?? DEFAULT_COSTS[action] ?? 0);
}

function devToolsEnabled() {
  if (billing && billing.dev) return Boolean(billing.dev.grant);
  const caps = store.get('capabilities');
  return Boolean(caps && caps.auth && caps.auth.mode === 'dev');
}

function actionLabel(action) { return ACTION_LABELS[action] || (action ? action.replace(/_/g, ' ') : 'Action'); }

function formatWhen(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return String(iso || '');
  const now = new Date();
  const sameDay = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  const time = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  if (sameDay(date, now)) return `Today ${time}`;
  if (sameDay(date, yesterday)) return `Yesterday ${time}`;
  const sameYear = date.getFullYear() === now.getFullYear();
  return `${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', ...(sameYear ? {} : { year: 'numeric' }) })}, ${time}`;
}

// -- pricing cards ------------------------------------------------------------

function packCard(pack) {
  const featured = Boolean(pack.highlight);
  const costs = (pricing && pricing.credit_costs) || DEFAULT_COSTS;
  return html`
    <article class="pricing-card ${featured ? 'is-featured' : ''}" data-plan="${pack.id}">
      <div class="pricing-card-head"><h3 class="pricing-name">${pack.name || pack.id}</h3>${featured ? html`<span class="pricing-badge">Most popular</span>` : ''}</div>
      <p class="pricing-price"><span class="pricing-amount">${cents(pack.price_cents)}</span><span class="pricing-period">one time</span></p>
      <p class="pricing-desc">${pack.credits} credits. ${PACK_COPY[pack.id] || 'Spend them on analyses, previews and searches.'}</p>
      <ul class="feature-list">
        <li>${icon('check')}<span>${pack.credits} credits, never expire</span></li>
        <li>${icon('check')}<span>Analysis: ${costs.analysis} credit${costs.analysis === 1 ? '' : 's'}</span></li>
        <li>${icon('check')}<span>Preview on your photo: ${costs.tryon} credits</span></li>
        <li>${icon('check')}<span>Barber search: ${costs.barber_search} credit${costs.barber_search === 1 ? '' : 's'}; repeats are free</span></li>
      </ul>
      <button type="button" class="${featured ? 'btn-primary' : 'btn-secondary'}" data-action="buy-pack" data-pack-id="${pack.id}">Buy ${pack.credits} credits</button>
      <p class="pricing-meta">${perCredit(pack)}</p>
    </article>`;
}

function packButton(pack) {
  return html`<button type="button" class="pack-btn ${pack.highlight ? 'is-featured' : ''}" data-action="buy-pack" data-pack-id="${pack.id}"><span class="pack-btn-credits">${pack.credits} credits</span><span class="pack-btn-price">${cents(pack.price_cents)}</span><span class="pack-btn-name">${pack.name || pack.id}</span></button>`;
}

function renderPricing() {
  if (!pricing) {
    // No API yet: the landing page has static cards; mirror them on the pricing page.
    if (!els.pricingPageGrid.children.length) els.pricingPageGrid.innerHTML = els.pricingGrid.innerHTML;
    return;
  }
  const packs = Array.isArray(pricing.credit_packs) ? pricing.credit_packs : [];
  const cards = html`${packs.map(packCard)}`;
  els.pricingGrid.innerHTML = cards;
  els.pricingPageGrid.innerHTML = cards;
  const buttons = html`${packs.map(packButton)}`;
  els.accountPacks.innerHTML = buttons;
  els.modalPacks.innerHTML = buttons;
}

export async function loadPricing() {
  try {
    const data = await api.pricing();
    if (data && Array.isArray(data.credit_packs)) {
      pricing = data;
      store.set('pricing', data);
    }
  } catch (err) {
    debug('pricing unavailable, using static cards', err);
  }
  renderPricing();
  paintCostHints();
  return pricing;
}

// Cost labels in the app ("Analyze photo · 1 credit").
function paintCostHints() {
  const button = byId('analyze-button');
  if (button && !button.hasAttribute('aria-busy')) {
    const cost = getCreditCost('analysis');
    button.innerHTML = html`Analyze photo <span class="btn-cost">${cost} credit${cost === 1 ? '' : 's'}</span>`;
  }
  const tryon = byId('start-tryon');
  if (tryon && !tryon.hasAttribute('aria-busy') && !tryon.dataset.idleHtml) {
    const cost = getCreditCost('tryon');
    tryon.innerHTML = html`Start preview <span class="btn-cost">${cost} credits</span>`;
  }
}

// -- balance and billing state ------------------------------------------------

function paintCredits(credits) {
  const value = Math.max(0, Number(credits) || 0);
  els.headerCreditsValue.textContent = String(value);
  els.headerCredits.classList.toggle('is-low', value > 0 && value <= 3);
  els.headerCredits.classList.toggle('is-empty', value === 0);
  els.headerCredits.setAttribute('aria-label', `${value} credit${value === 1 ? '' : 's'}. Open account`);
  els.balance.textContent = String(value);
  els.modalBalance.textContent = String(value);
  if (billing) billing = { ...billing, credits: value };
  const user = getUser();
  if (user && user.credits !== value) store.set('user', { ...user, credits: value });
}

function paintBillingState() {
  const signedIn = isSignedIn();
  els.headerCredits.classList.toggle('hidden', !signedIn);

  const dev = devToolsEnabled();
  els.devGrant.classList.toggle('hidden', !dev);
  els.modalDevGrant.classList.toggle('hidden', !dev);

  const stripeReady = Boolean(billing && billing.stripe && billing.stripe.configured);
  els.manageBilling.classList.toggle('hidden', !stripeReady || !(billing && billing.stripe.customer));
  els.creditsNote.textContent = stripeReady
    ? 'Credits never expire. Failed analyses are refunded automatically.'
    : 'Payments are not set up on this server yet. Credits never expire once added.';
  els.modalNote.textContent = stripeReady
    ? "You'll be sent to Stripe Checkout and back here when it's done."
    : 'Payments are not set up on this server yet.';
}

export async function refreshBilling({ silent = true } = {}) {
  if (!isSignedIn()) { billing = null; paintBillingState(); return null; }
  try {
    const data = await api.billingMe();
    billing = data;
    store.set('billing', data);
    paintCredits(data.credits);
    paintBillingState();
    paintCostHints();
    clearFieldError(els.billingError);
    return data;
  } catch (err) {
    debug('billing refresh failed', err);
    if (!silent) setFieldError(els.billingError, err instanceof ApiError ? err.message : 'Could not load your balance.');
    return null;
  }
}

// -- usage ledger -------------------------------------------------------------

function usageRow(event) {
  const kind = event.kind || 'charge';
  const delta = Number(event.delta ?? (kind === 'charge' ? -event.credits : event.credits)) || 0;
  let label = actionLabel(event.action);
  let status = html`<span class="chip-success">OK</span>`;
  let amount = html`<td class="num is-refund">0</td>`;
  if (kind === 'charge') {
    if (event.ok === false) status = html`<span class="chip-danger">Failed</span>`;
    else if (event.free || delta === 0) status = html`<span class="chip-neutral">Free</span>`;
    if (delta < 0) amount = html`<td class="num is-debit">−${Math.abs(delta)}</td>`;
  } else if (kind === 'refund') {
    label = `Refund: ${actionLabel(event.action)}`;
    status = html`<span class="chip-neutral">Refunded</span>`;
    amount = html`<td class="num is-refund">+${Math.abs(delta)} refund</td>`;
  } else if (kind === 'grant') {
    label = { signup_bonus: 'Welcome credits', purchase: 'Credits purchased', dev_grant: 'Test credits' }[event.reason] || 'Credits added';
    status = html`<span class="chip-success">Added</span>`;
    amount = html`<td class="num is-credit">+${Math.abs(delta)}</td>`;
  } else if (kind === 'plan') {
    label = 'Plan changed';
    status = html`<span class="chip-neutral">Plan</span>`;
  }
  return html`<tr><td class="time">${formatWhen(event.ts)}</td><td>${label}</td><td>${status}</td>${amount}<td class="num">${Number(event.balance_after) || 0}</td></tr>`;
}

export async function loadUsage() {
  if (!isSignedIn()) return;
  els.usageTable.setAttribute('aria-busy', 'true');
  try {
    const data = await api.usage(50);
    const events = Array.isArray(data.events) ? data.events : [];
    els.usageBody.innerHTML = html`${events.map(usageRow)}`;
    els.usageWrap.classList.toggle('hidden', !events.length);
    els.usageEmpty.classList.toggle('hidden', events.length > 0);
    if (typeof data.credits === 'number') paintCredits(data.credits);
    usageLoaded = true;
  } catch (err) {
    debug('usage failed', err);
    els.usageBody.innerHTML = '';
    els.usageWrap.classList.add('hidden');
    els.usageEmpty.classList.remove('hidden');
    els.usageEmpty.querySelector('.empty-state-title').textContent = 'Usage did not load';
    els.usageEmpty.querySelector('.empty-state-text').textContent = err instanceof ApiError ? err.message : 'Try refreshing.';
  } finally {
    els.usageTable.removeAttribute('aria-busy');
  }
}

// -- checkout, portal, dev tools ----------------------------------------------

function errorTargetFor(button) {
  if (button.closest('#credits-modal')) return els.modalError;
  if (button.closest('#view-account')) return els.billingError;
  return null;
}

function requireSignIn() {
  if (isSignedIn()) return true;
  rememberNext('#/account');
  go(signInHash('#/account'));
  return false;
}

async function buyPack(button) {
  if (!requireSignIn()) return;
  const packId = button.dataset.packId;
  const target = errorTargetFor(button);
  clearFieldError(target);
  setBusy(button, true, 'Opening checkout…');
  try {
    const data = await api.checkout({ packId });
    if (!data || !data.url) throw new ApiError('Checkout did not return a payment page.');
    window.location.assign(data.url);
  } catch (err) {
    debug('checkout failed', err);
    setBusy(button, false);
    const message = err instanceof ApiError ? err.message : 'Could not start checkout.';
    if (target) setFieldError(target, message);
    else notify.error('Could not start checkout', message);
  }
}

async function managePortal() {
  clearFieldError(els.billingError);
  setBusy(els.manageBilling, true, 'Opening…');
  try {
    const data = await api.portal();
    if (!data || !data.url) throw new ApiError('The billing portal did not open.');
    window.location.assign(data.url);
  } catch (err) {
    debug('portal failed', err);
    setBusy(els.manageBilling, false);
    setFieldError(els.billingError, err instanceof ApiError ? err.message : 'Could not open billing.');
  }
}

async function devGrant(button) {
  const target = errorTargetFor(button);
  clearFieldError(target);
  setBusy(button, true, 'Adding…');
  try {
    const data = await api.devGrant(10);
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'Credits were not added.');
    paintCredits(data.credits);
    notify.success('10 test credits added', `Balance: ${data.credits}.`);
    if (isModalOpen('credits-modal')) closeModal('credits-modal');
    refreshBilling();
    if (usageLoaded || store.get('view') === 'account') loadUsage();
  } catch (err) {
    debug('dev grant failed', err);
    const message = err instanceof ApiError ? err.message : 'Credits were not added.';
    if (target) setFieldError(target, message); else notify.error('Could not add credits', message);
  } finally {
    setBusy(button, false);
  }
}

// -- 402 handling -------------------------------------------------------------

export function openCreditsModal({ needed, credits, action } = {}) {
  const cost = Number(needed) || getCreditCost(action || 'analysis') || 1;
  const label = actionLabel(action || 'analysis');
  els.modalTitle.textContent = 'Out of credits';
  els.modalLead.textContent = 'This action needs more credits than you have. Buy a pack to continue; credits never expire.';
  els.modalNeeded.textContent = `${label} costs ${cost} credit${cost === 1 ? '' : 's'}.`;
  if (typeof credits === 'number') paintCredits(credits);
  clearFieldError(els.modalError);
  openModal('credits-modal');
}

function onPaymentRequired(event) {
  const detail = event.detail || {};
  if (detail.code === 'insufficient_credits') openCreditsModal(detail);
}

// -- account page + routing ---------------------------------------------------

function handleCheckoutReturn(query) {
  const outcome = query.get('checkout');
  if (!outcome) { els.checkoutNotice.classList.add('hidden'); return; }
  window.history.replaceState(null, '', '#/account');
  if (outcome === 'success') {
    els.checkoutNoticeTitle.textContent = 'Payment received';
    els.checkoutNoticeText.textContent = 'Your balance has been updated. If it has not changed yet, Stripe is still confirming; refresh in a moment.';
    els.checkoutNotice.classList.remove('hidden');
    notify.success('Payment received', 'Thanks. Your account has been updated.');
  } else {
    els.checkoutNotice.classList.add('hidden');
    notify.info('Checkout cancelled', 'Nothing was charged.');
  }
}

export function initBilling() {
  Object.assign(els, {
    headerCredits: byId('header-credits'),
    headerCreditsValue: byId('header-credits-value'),
    pricingGrid: byId('pricing-grid'),
    pricingPageGrid: byId('pricing-page-grid'),
    accountPacks: byId('credit-packs'),
    modalPacks: byId('credits-modal-packs'),
    checkoutNotice: byId('checkout-notice'),
    checkoutNoticeTitle: byId('checkout-notice-title'),
    checkoutNoticeText: byId('checkout-notice-text'),
    manageBilling: byId('manage-billing'),
    refreshBilling: byId('refresh-billing'),
    balance: byId('credits-balance'),
    creditsNote: byId('credits-note'),
    billingError: byId('billing-error'),
    devGrant: byId('dev-grant'),
    refreshUsage: byId('refresh-usage'),
    usageTable: byId('usage-table'),
    usageWrap: byId('usage-table-wrap'),
    usageBody: byId('usage-table-body'),
    usageEmpty: byId('usage-empty'),
    modalTitle: byId('credits-modal-title'),
    modalLead: byId('credits-modal-lead'),
    modalBalance: byId('credits-modal-balance'),
    modalNeeded: byId('credits-modal-needed'),
    modalNote: byId('credits-modal-note'),
    modalError: byId('credits-modal-error'),
    modalDevGrant: byId('credits-modal-dev-grant'),
  });

  renderPricing();
  paintBillingState();
  paintCostHints();
  const user = getUser();
  if (user && typeof user.credits === 'number') paintCredits(user.credits);

  delegate(document, 'click', '[data-action="buy-pack"]', (event, button) => buyPack(button));
  els.manageBilling.addEventListener('click', managePortal);
  els.refreshBilling.addEventListener('click', () => { refreshBilling({ silent: false }); loadUsage(); });
  els.refreshUsage.addEventListener('click', loadUsage);
  els.devGrant.addEventListener('click', () => devGrant(els.devGrant));
  els.modalDevGrant.addEventListener('click', () => devGrant(els.modalDevGrant));

  document.addEventListener('lineup:credits', (event) => { if (event.detail && typeof event.detail.credits === 'number') paintCredits(event.detail.credits); });
  document.addEventListener('lineup:payment-required', onPaymentRequired);

  store.subscribe('capabilities', () => paintBillingState());
  onSessionChange((nextUser) => {
    if (!nextUser) { billing = null; usageLoaded = false; }
    else if (typeof nextUser.credits === 'number' && !billing) paintCredits(nextUser.credits);
    paintBillingState();
  });

  onRoute((route, { viewChanged }) => {
    if (route.name === 'account') {
      handleCheckoutReturn(route.query);
      refreshBilling({ silent: false });
      loadUsage();
    } else if ((route.name === 'landing' || route.name === 'pricing') && !pricing && viewChanged) {
      loadPricing();
    } else if (route.name === 'app' && viewChanged) {
      refreshBilling();
    }
  });

  loadPricing();
}
