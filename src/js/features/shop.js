// Shop settings: business info (GET/PUT /barbers/<uid>/profile), hours modal,
// services modal, clients modal (Pro) and subscription packages (Pro).
import { byId, html, show, hide, delegate, setBusy, setFieldError, clearFormErrors, errorNotice } from '../dom.js';
import { icon } from '../icons.js';
import { api, ApiError } from '../api.js';
import { getIdentity, store } from '../state.js';
import { openModal, closeModal, onModalClose } from '../ui/modal.js';
import { confirmDialog } from '../ui/confirm.js';
import { notify } from '../ui/toast.js';
import { showSkeleton, skeletonRows, skeletonCards, clearBusy } from '../ui/skeleton.js';
import { onTabShow } from '../nav.js';
import { hasFeature } from '../billing.js';
import { formatTime, formatDate, money, initials, plural, capitalize } from '../format.js';
import { debug } from '../env.js';

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
const els = {};
let availability = null;
let hoursFormReady = false;
let services = [];
let clients = [];
let packages = [];
let profile = null;

// -- business info ------------------------------------------------------------

function fillShopForm() {
  const current = profile || store.get('barberProfile') || {};
  if (document.activeElement === els.shopName || document.activeElement === els.shopPhone || document.activeElement === els.shopAddress) return;
  els.shopName.value = current.name || '';
  els.shopPhone.value = current.phone || '';
  els.shopAddress.value = current.address || '';
}

async function loadShopProfile() {
  const { barberId } = getIdentity();
  if (!barberId) return;
  try {
    const data = await api.barberProfile(barberId);
    if (data && data.profile) {
      profile = data.profile;
      store.set('barberProfile', profile);
      fillShopForm();
    }
  } catch (err) {
    debug('shop profile failed', err);
  }
}

async function saveShopInfo(event) {
  event.preventDefault();
  clearFormErrors(els.shopForm);
  const name = els.shopName.value.trim();
  const phone = els.shopPhone.value.trim();
  const address = els.shopAddress.value.trim();
  if (!name) { setFieldError(els.shopError, 'Enter your shop name.', els.shopName); return; }
  if (phone && phone.replace(/\D/g, '').length < 10) { setFieldError(els.shopError, 'Enter a phone number with an area code.', els.shopPhone); return; }
  setBusy(els.shopSubmit, true, 'Saving…');
  try {
    const data = await api.saveBarberProfile(getIdentity().barberId, { name, phone, address, bio: (profile && profile.bio) || '' });
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'Shop details were not saved.');
    profile = data.profile || { ...profile, name, phone, address };
    store.set('barberProfile', profile);
    notify.success('Shop details saved', 'Clients see these on your booking page.');
  } catch (err) {
    debug('shop profile save failed', err);
    setFieldError(els.shopError, err instanceof ApiError ? err.message : 'Shop details could not be saved.');
  } finally {
    setBusy(els.shopSubmit, false);
  }
}

// -- hours --------------------------------------------------------------------

function renderAvailabilityPreview() {
  clearBusy(els.availabilityPreview);
  const hours = (availability && availability.workingHours) || {};
  els.availabilityPreview.innerHTML = html`${DAYS.map((day) => {
    const spec = hours[day] || { enabled: false };
    return html`<div class="list-row" style="min-height:40px;padding:8px 0"><span class="grow list-title">${capitalize(day)}</span><span class="list-value ${spec.enabled ? '' : 'text-text-2'}">${spec.enabled ? `${formatTime(spec.start)} – ${formatTime(spec.end)}` : 'Closed'}</span></div>`;
  })}`;
}

async function loadAvailability({ silent = false } = {}) {
  if (!silent) showSkeleton(els.availabilityPreview, skeletonRows(4));
  try {
    const data = await api.availability(getIdentity().barberId);
    availability = data.availability || null;
    renderAvailabilityPreview();
  } catch (err) {
    debug('availability failed', err);
    clearBusy(els.availabilityPreview);
    els.availabilityPreview.replaceChildren(errorNotice({ title: 'Hours did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadAvailability() }));
  }
}

function renderHoursForm() {
  hoursFormReady = true;
  els.hoursSubmit.disabled = false;
  const hours = (availability && availability.workingHours) || {};
  els.hoursForm.innerHTML = html`
    <div class="form-row">
      <div class="field">
        <label for="service-duration-setting" class="field-label">Appointment length (minutes)</label>
        <input type="number" id="service-duration-setting" class="input" inputmode="numeric" min="5" step="5" value="${availability?.serviceDuration || 30}">
      </div>
      <div class="field">
        <label for="buffer-time-setting" class="field-label">Gap between appointments (minutes)</label>
        <input type="number" id="buffer-time-setting" class="input" inputmode="numeric" min="0" step="5" value="${availability?.bufferTime ?? 15}">
      </div>
    </div>
    <div class="modal-section">
      <p class="eyebrow mb-2">Working hours</p>
      ${DAYS.map((day) => {
        const spec = hours[day] || { enabled: false, start: '09:00', end: '18:00' };
        return html`<div class="hours-row ${spec.enabled ? '' : 'is-off'}" data-day="${day}">
          <label class="row grow" for="${day}-enabled">
            <span class="switch"><input type="checkbox" id="${day}-enabled" ${spec.enabled ? 'checked' : ''}><span class="switch-track"></span></span>
            <span class="hours-day">${capitalize(day)}</span>
          </label>
          <div class="hours-times">
            <label class="sr-only" for="${day}-start">${capitalize(day)} opens</label>
            <input type="time" id="${day}-start" class="input" value="${spec.start || '09:00'}" ${spec.enabled ? '' : 'disabled'}>
            <span>to</span>
            <label class="sr-only" for="${day}-end">${capitalize(day)} closes</label>
            <input type="time" id="${day}-end" class="input" value="${spec.end || '18:00'}" ${spec.enabled ? '' : 'disabled'}>
          </div>
        </div>`;
      })}
    </div>`;
}

function openHours() {
  clearFormErrors(els.hoursFormEl);
  if (availability) {
    renderHoursForm();
  } else {
    // Saving a form that never rendered would read every day as "closed" and
    // silently make the shop unbookable, so Save stays off until it is there.
    hoursFormReady = false;
    els.hoursSubmit.disabled = true;
    showSkeleton(els.hoursForm, skeletonRows(5));
  }
  openModal('availability-modal');
  if (!availability) {
    loadAvailability({ silent: true }).then(() => {
      clearBusy(els.hoursForm);
      if (availability) renderHoursForm();
      else {
        els.hoursForm.replaceChildren(errorNotice({ title: 'Hours did not load', text: 'Check your connection and try again.', onRetry: () => { closeModal('availability-modal'); openHours(); } }));
        setFieldError(els.hoursError, 'Your current hours could not be loaded, so they cannot be saved yet.');
      }
    });
  }
}

async function saveHours(event) {
  event.preventDefault();
  clearFormErrors(els.hoursFormEl);
  if (!hoursFormReady) {
    setFieldError(els.hoursError, 'Your current hours have not loaded yet. Close this and try again.');
    return;
  }
  const workingHours = {};
  for (const day of DAYS) {
    const enabled = byId(`${day}-enabled`)?.checked || false;
    const start = byId(`${day}-start`)?.value || '09:00';
    const end = byId(`${day}-end`)?.value || '18:00';
    if (enabled && start >= end) { setFieldError(els.hoursError, `${capitalize(day)}: opening time must be before closing time.`, byId(`${day}-start`)); return; }
    workingHours[day] = { enabled, start, end };
  }
  const body = {
    workingHours,
    serviceDuration: Math.max(5, parseInt(byId('service-duration-setting')?.value, 10) || 30),
    bufferTime: Math.max(0, parseInt(byId('buffer-time-setting')?.value, 10) || 0),
    breakTimes: availability?.breakTimes || [],
    blockedDates: availability?.blockedDates || [],
    timezone: availability?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/New_York',
  };
  setBusy(els.hoursSubmit, true, 'Saving…');
  try {
    const data = await api.saveAvailability(getIdentity().barberId, body);
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'Hours were not saved.');
    availability = data.availability || { ...availability, ...body };
    renderAvailabilityPreview();
    closeModal('availability-modal');
    notify.success('Hours saved');
  } catch (err) {
    debug('hours save failed', err);
    setFieldError(els.hoursError, err instanceof ApiError ? err.message : 'Hours could not be saved.');
  } finally {
    setBusy(els.hoursSubmit, false);
  }
}

// -- services -----------------------------------------------------------------

function renderServicesPreview() {
  clearBusy(els.servicesPreview);
  if (!services.length) {
    els.servicesPreview.innerHTML = '<p class="text-sm text-text-2 py-1">No services yet. Add what you offer so clients can pick one when booking.</p>';
    return;
  }
  const shown = services.slice(0, 4);
  els.servicesPreview.innerHTML = html`${shown.map((s) => html`<div class="list-row" style="min-height:40px;padding:8px 0"><div class="grow"><p class="list-title">${s.name}</p><p class="list-text">${s.duration ? `${s.duration} min` : ''}${s.category ? ` · ${s.category}` : ''}</p></div><span class="list-value">${money(s.price)}</span></div>`)}${services.length > shown.length ? html`<p class="list-text pt-2">and ${services.length - shown.length} more</p>` : ''}`;
}

function renderServicesList() {
  clearBusy(els.servicesList);
  if (!services.length) {
    els.servicesList.innerHTML = '<p class="text-sm text-text-2 py-2">No services yet.</p>';
    return;
  }
  els.servicesList.innerHTML = html`${services.map((s) => html`
    <div class="list-row" data-service-id="${s.id}">
      <div class="grow"><p class="list-title">${s.name}</p><p class="list-text">${money(s.price)}${s.duration ? ` · ${s.duration} min` : ''}${s.category ? ` · ${s.category}` : ''}</p>${s.description ? html`<p class="list-text">${s.description}</p>` : ''}</div>
      <button type="button" class="btn-ghost btn-icon btn-sm" data-action="delete-service" aria-label="Delete ${s.name}">${icon('trash')}</button>
    </div>`)}`;
}

async function loadServices({ silent = false } = {}) {
  if (!silent) showSkeleton(els.servicesPreview, skeletonRows(3));
  try {
    const data = await api.services(getIdentity().barberId);
    services = Array.isArray(data.services) ? data.services : [];
    renderServicesPreview();
    renderServicesList();
  } catch (err) {
    debug('services failed', err);
    clearBusy(els.servicesPreview);
    els.servicesPreview.replaceChildren(errorNotice({ title: 'Services did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadServices() }));
  }
}

function resetServiceForm() {
  els.serviceName.value = '';
  els.servicePrice.value = '';
  els.serviceDuration.value = '';
  els.serviceCategory.value = '';
  els.serviceDescription.value = '';
  clearFormErrors(els.serviceForm);
  hide(els.serviceForm);
  show(els.addServiceBtn);
}

async function saveService(event) {
  event.preventDefault();
  clearFormErrors(els.serviceForm);
  const name = els.serviceName.value.trim();
  const price = parseFloat(els.servicePrice.value);
  const duration = parseInt(els.serviceDuration.value, 10);
  if (!name) { setFieldError(els.serviceError, 'Give the service a name.', els.serviceName); return; }
  if (Number.isNaN(price) || price < 0) { setFieldError(els.serviceError, 'Enter a price of 0 or more.', els.servicePrice); return; }
  if (Number.isNaN(duration) || duration < 5) { setFieldError(els.serviceError, 'Enter a duration of at least 5 minutes.', els.serviceDuration); return; }
  setBusy(els.serviceSubmit, true, 'Saving…');
  try {
    const data = await api.addService(getIdentity().barberId, { name, price, duration, category: els.serviceCategory.value.trim() || 'General', description: els.serviceDescription.value.trim() });
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'The service was not saved.');
    resetServiceForm();
    notify.success('Service added', name);
    await loadServices({ silent: true });
    els.addServiceBtn.focus({ preventScroll: true });
  } catch (err) {
    debug('service save failed', err);
    setFieldError(els.serviceError, err instanceof ApiError ? err.message : 'The service could not be saved.');
  } finally {
    setBusy(els.serviceSubmit, false);
  }
}

async function deleteService(button) {
  const row = button.closest('[data-service-id]');
  const service = services.find((s) => String(s.id) === row?.dataset.serviceId);
  if (!service) return;
  const ok = await confirmDialog({ title: `Delete ${service.name}?`, body: 'Clients will no longer be able to book it. Existing bookings are not affected.', confirmLabel: 'Delete service' });
  if (!ok) return;
  setBusy(button, true);
  try {
    const data = await api.deleteService(getIdentity().barberId, service.id);
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'The service was not deleted.');
    notify.success('Service deleted', service.name);
    await loadServices({ silent: true });
  } catch (err) {
    debug('service delete failed', err);
    setBusy(button, false);
    notify.error('Could not delete the service', err instanceof ApiError ? err.message : '');
  }
}

// -- clients ------------------------------------------------------------------

function renderClientsPreview() {
  clearBusy(els.clientsPreview);
  if (!clients.length) {
    els.clientsPreview.innerHTML = '<p class="text-sm text-text-2 py-1">No clients yet. They appear here after their first booking.</p>';
    return;
  }
  els.clientsPreview.innerHTML = html`${clients.slice(0, 3).map((c) => html`<div class="list-row" style="min-height:40px;padding:8px 0"><div class="avatar avatar-sm" aria-hidden="true">${initials(c.clientName)}</div><div class="grow"><p class="list-title">${c.clientName}</p><p class="list-text">${plural(c.totalVisits || 0, 'visit')}</p></div></div>`)}${clients.length > 3 ? html`<p class="list-text pt-2">and ${clients.length - 3} more</p>` : ''}`;
}

function renderClientsList() {
  clearBusy(els.clientsList);
  if (!clients.length) {
    els.clientsList.innerHTML = html`<div class="empty-state">${icon('users', { size: 'lg', className: 'empty-state-icon' })}<p class="empty-state-title">No clients yet</p><p class="empty-state-text">Everyone who books you shows up here with their visit history.</p></div>`;
    return;
  }
  els.clientsList.innerHTML = html`${clients.map((c) => html`
    <div class="list-row items-start" data-client-id="${c.clientId}">
      <div class="avatar" aria-hidden="true">${initials(c.clientName)}</div>
      <div class="grow">
        <div class="row"><p class="list-title grow">${c.clientName}</p><span class="list-value">${money(c.totalSpent || 0)}</span></div>
        <p class="list-text">${plural(c.totalVisits || 0, 'visit')}${c.lastVisit ? ` · last ${formatDate(c.lastVisit, { relative: false })}` : ''}</p>
        <div class="hidden" data-history></div>
        <button type="button" class="btn-ghost btn-sm mt-2 -ml-3" data-action="client-history" aria-expanded="false">History</button>
      </div>
    </div>`)}`;
}

async function loadClients({ silent = false } = {}) {
  // The client list is a Pro feature; the panel shows a locked overlay instead of a 402.
  if (!hasFeature('clients')) {
    clients = [];
    clearBusy(els.clientsPreview);
    els.clientsPreview.innerHTML = '<p class="text-sm text-text-2 py-1">Your client list, visit history and private notes come with Pro.</p>';
    renderClientsList();
    return;
  }
  if (!silent) showSkeleton(els.clientsPreview, skeletonRows(2));
  try {
    const data = await api.clients(getIdentity().barberId);
    clients = Array.isArray(data.clients) ? data.clients : [];
    renderClientsPreview();
    renderClientsList();
  } catch (err) {
    debug('clients failed', err);
    clearBusy(els.clientsPreview);
    els.clientsPreview.replaceChildren(errorNotice({ title: 'Clients did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadClients() }));
  }
}

async function toggleClientHistory(button) {
  const row = button.closest('[data-client-id]');
  const panel = row.querySelector('[data-history]');
  if (button.getAttribute('aria-expanded') === 'true') { hide(panel); button.setAttribute('aria-expanded', 'false'); return; }
  button.setAttribute('aria-expanded', 'true');
  show(panel);
  showSkeleton(panel, skeletonRows(2));
  try {
    const data = await api.clientHistory(getIdentity().barberId, row.dataset.clientId);
    const items = Array.isArray(data.appointments) ? data.appointments : [];
    clearBusy(panel);
    panel.innerHTML = html`<div class="list mt-2">${items.length
      ? items.map((a) => html`<div class="list-row" style="min-height:40px;padding:8px 0"><div class="grow"><p class="text-sm">${a.service || 'Appointment'}</p><p class="list-text">${formatDate(a.date, { relative: false })} · ${formatTime(a.time)}</p></div><span class="list-value">${a.status || ''}</span></div>`)
      : html`<p class="list-text">No visits recorded.</p>`}</div>`;
  } catch (err) {
    debug('client history failed', err);
    clearBusy(panel);
    panel.replaceChildren(errorNotice({ title: 'History did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => { button.setAttribute('aria-expanded', 'false'); toggleClientHistory(button); } }));
  }
}

// -- packages -----------------------------------------------------------------

function renderPackages() {
  clearBusy(els.packagesList);
  if (!packages.length) {
    els.packagesList.innerHTML = html`<div class="empty-state">${icon('scissors', { size: 'lg', className: 'empty-state-icon' })}<p class="empty-state-title">No packages yet</p><p class="empty-state-text">Offer a bundle like "4 cuts for $120, valid 2 months" and regulars can prepay.</p><button type="button" class="btn-secondary btn-sm" data-open-modal="create-package-modal">New package</button></div>`;
    return;
  }
  els.packagesList.innerHTML = html`${packages.map((p) => html`
    <article class="card">
      <div class="card-header">
        <div class="min-w-0"><h3 class="card-title">${p.title}</h3>${p.description ? html`<p class="card-text">${p.description}</p>` : ''}</div>
        ${p.discount ? html`<span class="chip-success">${p.discount}</span>` : ''}
      </div>
      <div class="kv-grid">
        <div class="kv"><p class="kv-label">Price</p><p class="kv-value">${money(p.price)}</p></div>
        <div class="kv"><p class="kv-label">Cuts</p><p class="kv-value">${p.numCuts || 0}</p></div>
        <div class="kv"><p class="kv-label">Valid for</p><p class="kv-value">${plural(p.durationMonths || 0, 'month')}</p></div>
      </div>
    </article>`)}`;
}

async function loadPackages({ silent = false } = {}) {
  if (!silent) showSkeleton(els.packagesList, skeletonCards(1));
  try {
    const data = await api.packages(getIdentity().barberId);
    packages = Array.isArray(data.packages) ? data.packages : [];
    renderPackages();
  } catch (err) {
    debug('packages failed', err);
    clearBusy(els.packagesList);
    els.packagesList.replaceChildren(errorNotice({ title: 'Packages did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadPackages() }));
  }
}

function resetPackageForm() {
  ['packageTitle', 'packageDescription', 'packageCuts', 'packageDuration', 'packagePrice', 'packageDiscount'].forEach((key) => { els[key].value = ''; });
  clearFormErrors(els.packageForm);
}

async function submitPackage(event) {
  event.preventDefault();
  clearFormErrors(els.packageForm);
  const title = els.packageTitle.value.trim();
  const numCuts = parseInt(els.packageCuts.value, 10);
  const durationMonths = parseInt(els.packageDuration.value, 10);
  const price = els.packagePrice.value.trim();
  if (!title) { setFieldError(els.packageError, 'Give the package a name.', els.packageTitle); return; }
  if (Number.isNaN(numCuts) || numCuts < 1) { setFieldError(els.packageError, 'Enter how many cuts are included.', els.packageCuts); return; }
  if (Number.isNaN(durationMonths) || durationMonths < 1) { setFieldError(els.packageError, 'Enter how many months it is valid for.', els.packageDuration); return; }
  if (!price || !/\d/.test(price)) { setFieldError(els.packageError, 'Enter a price.', els.packagePrice); return; }
  const identity = getIdentity();
  setBusy(els.packageSubmit, true, 'Creating…');
  try {
    const data = await api.createPackage({
      barberId: identity.barberId,
      barberName: (profile && profile.name) || identity.accountName || 'My shop',
      title,
      description: els.packageDescription.value.trim(),
      price: money(price),
      numCuts,
      durationMonths,
      discount: els.packageDiscount.value.trim(),
    });
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'The package was not saved.');
    closeModal('create-package-modal');
    notify.success('Package created', title);
    await loadPackages({ silent: true });
  } catch (err) {
    debug('package failed', err);
    setFieldError(els.packageError, err instanceof ApiError ? err.message : 'The package could not be created.');
  } finally {
    setBusy(els.packageSubmit, false);
  }
}

// -- wiring -------------------------------------------------------------------

export function initShop() {
  Object.assign(els, {
    shopForm: byId('shop-info-form'),
    shopName: byId('shop-name'),
    shopPhone: byId('shop-phone'),
    shopAddress: byId('shop-address'),
    shopError: byId('shop-info-error'),
    shopSubmit: byId('save-shop-info'),
    availabilityPreview: byId('availability-preview'),
    hoursFormEl: byId('hours-form'),
    hoursForm: byId('availability-form'),
    hoursError: byId('availability-error'),
    hoursSubmit: byId('save-availability'),
    servicesPreview: byId('services-preview'),
    servicesList: byId('services-list'),
    addServiceBtn: byId('add-service-btn'),
    serviceForm: byId('add-service-form'),
    serviceName: byId('service-name'),
    servicePrice: byId('service-price'),
    serviceDuration: byId('service-duration'),
    serviceCategory: byId('service-category'),
    serviceDescription: byId('service-description'),
    serviceError: byId('service-error'),
    serviceSubmit: byId('save-service'),
    clientsPreview: byId('clients-preview'),
    clientsList: byId('clients-list'),
    packagesList: byId('subscription-packages-list'),
    packageForm: byId('package-form'),
    packageTitle: byId('package-title'),
    packageDescription: byId('package-description'),
    packageCuts: byId('package-num-cuts'),
    packageDuration: byId('package-duration'),
    packagePrice: byId('package-price'),
    packageDiscount: byId('package-discount'),
    packageError: byId('package-error'),
    packageSubmit: byId('submit-package'),
  });

  els.shopForm.addEventListener('submit', saveShopInfo);

  byId('manage-availability-btn').addEventListener('click', openHours);
  els.hoursFormEl.addEventListener('submit', saveHours);
  els.hoursForm.addEventListener('change', (event) => {
    if (!(event.target instanceof HTMLInputElement) || event.target.type !== 'checkbox') return;
    const row = event.target.closest('.hours-row');
    if (!row) return;
    row.classList.toggle('is-off', !event.target.checked);
    row.querySelectorAll('input[type="time"]').forEach((input) => { input.disabled = !event.target.checked; });
  });

  byId('manage-services-btn').addEventListener('click', () => { resetServiceForm(); renderServicesList(); openModal('services-modal'); loadServices({ silent: true }); });
  els.addServiceBtn.addEventListener('click', () => { show(els.serviceForm); hide(els.addServiceBtn); els.serviceName.focus({ preventScroll: true }); });
  byId('cancel-service').addEventListener('click', () => { resetServiceForm(); els.addServiceBtn.focus({ preventScroll: true }); });
  els.serviceForm.addEventListener('submit', saveService);
  delegate(els.servicesList, 'click', '[data-action="delete-service"]', (event, button) => deleteService(button));
  onModalClose('services-modal', resetServiceForm);

  byId('view-clients-btn').addEventListener('click', () => { renderClientsList(); openModal('clients-modal'); loadClients({ silent: true }); });
  delegate(els.clientsList, 'click', '[data-action="client-history"]', (event, button) => toggleClientHistory(button));

  byId('create-package-btn').addEventListener('click', () => { resetPackageForm(); openModal('create-package-modal'); });
  els.packageForm.addEventListener('submit', submitPackage);
  onModalClose('create-package-modal', resetPackageForm);

  store.subscribe('barberProfile', (value) => { if (value && !profile) { profile = value; fillShopForm(); } });
  store.subscribe('billing', () => { if (store.get('tab') === 'barber-profile') loadClients({ silent: true }); });

  onTabShow('barber-profile', () => {
    fillShopForm();
    loadShopProfile();
    loadAvailability({ silent: Boolean(availability) });
    loadServices({ silent: services.length > 0 });
    loadClients({ silent: clients.length > 0 });
    loadPackages({ silent: packages.length > 0 });
  });
}
