// Client profile: display name shown to barbers (device preference over the
// account name), booking history, notification switches.
import { byId, html, setFieldError, clearFormErrors, errorNotice } from '../dom.js';
import { icon } from '../icons.js';
import { api, ApiError } from '../api.js';
import { getIdentity, updateIdentity, store } from '../state.js';
import { notify } from '../ui/toast.js';
import { showSkeleton, skeletonRows, clearBusy } from '../ui/skeleton.js';
import { onTabShow } from '../nav.js';
import { formatDate, formatTime, initials, appointmentDate } from '../format.js';
import { debug } from '../env.js';

const els = {};

function paintAvatar(name) {
  if (name) {
    els.avatar.textContent = initials(name);
  } else {
    els.avatar.innerHTML = html`${icon('user')}`;
  }
}

function fill() {
  const identity = getIdentity();
  els.name.value = identity.displayName || '';
  els.name.placeholder = identity.accountName || 'Your name';
  els.notifyBookings.checked = identity.notifyBookings !== false;
  els.notifyReminders.checked = identity.notifyReminders !== false;
  paintAvatar(identity.displayName || identity.accountName);
}

function save(event) {
  event.preventDefault();
  clearFormErrors(els.form);
  const name = els.name.value.trim();
  if (name.length < 2) { setFieldError(els.error, 'Enter at least two characters.', els.name); return; }
  updateIdentity({ displayName: name });
  paintAvatar(name);
  notify.success('Profile saved', `Barbers see you as ${name}.`);
}

async function loadHistory() {
  showSkeleton(els.history, skeletonRows(3));
  try {
    const data = await api.appointments('client');
    const items = (Array.isArray(data.appointments) ? data.appointments : [])
      .slice()
      .sort((a, b) => (appointmentDate(b)?.getTime() ?? 0) - (appointmentDate(a)?.getTime() ?? 0));
    clearBusy(els.history);
    if (!items.length) {
      els.history.innerHTML = html`<p class="text-sm text-text-2">No bookings yet. <button type="button" class="btn-ghost btn-sm -ml-3" data-tab="barbers">Find a barber</button></p>`;
      return;
    }
    els.history.innerHTML = html`${items.map((apt) => html`
      <div class="list-row">
        <div class="grow"><p class="list-title">${apt.barberName || 'Barber'}</p><p class="list-text">${apt.service || 'Appointment'} · ${apt.status || 'pending'}</p></div>
        <div class="list-value"><p>${formatDate(apt.date, { relative: false })}</p><p class="list-text">${formatTime(apt.time)}${apt.price ? ` · ${apt.price}` : ''}</p></div>
      </div>`)}`;
  } catch (err) {
    debug('history failed', err);
    clearBusy(els.history);
    els.history.replaceChildren(errorNotice({ title: 'History did not load', text: err instanceof ApiError ? err.message : '', onRetry: loadHistory }));
  }
}

export function initProfile() {
  Object.assign(els, {
    form: byId('client-profile-form'),
    avatar: byId('client-avatar'),
    name: byId('client-display-name'),
    error: byId('client-profile-error'),
    history: byId('client-profile-history'),
    refresh: byId('refresh-history'),
    notifyBookings: byId('notify-bookings'),
    notifyReminders: byId('notify-reminders'),
  });
  els.form.addEventListener('submit', save);
  els.refresh.addEventListener('click', loadHistory);
  els.notifyBookings.addEventListener('change', () => updateIdentity({ notifyBookings: els.notifyBookings.checked }));
  els.notifyReminders.addEventListener('change', () => updateIdentity({ notifyReminders: els.notifyReminders.checked }));
  store.subscribe('identity', () => { if (document.activeElement !== els.name) fill(); });
  store.subscribe('user', () => { if (document.activeElement !== els.name) fill(); });
  onTabShow('profile', () => { fill(); loadHistory(); });
  fill();
}
