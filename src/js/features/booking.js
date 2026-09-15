// Booking modal: barber summary, name, date (not in the past), time slots
// from /available-slots, services from /services, then POST /appointments.
import { byId, html, setBusy, setFieldError, clearFormErrors } from '../dom.js';
import { api, ApiError } from '../api.js';
import { getIdentity, updateIdentity } from '../state.js';
import { openModal, closeModal } from '../ui/modal.js';
import { notify } from '../ui/toast.js';
import { navigate } from '../nav.js';
import { formatDate, formatTime, todayIso, money, parsePrice } from '../format.js';
import { notifyAppointmentsChanged } from './appointments.js';
import { debug } from '../env.js';

const DEFAULT_TIMES = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];
const DEFAULT_SERVICES = [
  { id: 'haircut', name: 'Haircut', price: 45 },
  { id: 'haircut-beard', name: 'Haircut and beard', price: 65 },
  { id: 'beard-only', name: 'Beard trim', price: 25 },
];

const DEFAULT_SERVICE_HINT = 'Typical rates. The shop confirms the price when it accepts your request.';
const LISTED_SERVICE_HINT = "Prices are the shop's listed rates and may change on the day.";

const els = {};
let barber = null;
let services = DEFAULT_SERVICES;
let slotSeq = 0;
let submitting = false;

function setTimeOptions(times, { keep } = {}) {
  els.time.innerHTML = html`<option value="">Choose a time</option>${times.map((time) => html`<option value="${time}">${formatTime(time)}</option>`)}`;
  if (keep && times.includes(keep)) els.time.value = keep;
}

function setServiceOptions(list) {
  els.service.innerHTML = html`<option value="">Choose a service</option>${list.map((service) => html`<option value="${service.id}">${service.name}${service.price != null && service.price !== '' ? ` – ${money(service.price)}` : ''}</option>`)}`;
}

async function loadServices(target) {
  try {
    const data = await api.services(target.id);
    if (barber !== target) return;
    const list = Array.isArray(data.services) ? data.services.filter((s) => s && s.name) : [];
    if (list.length) {
      services = list.map((s) => ({ id: String(s.id), name: s.name, price: s.price, duration: s.duration }));
      setServiceOptions(services);
      // Services the barber never edited are placeholders, not this shop's price list.
      els.serviceHint.textContent = list.every((s) => s.default) ? DEFAULT_SERVICE_HINT : LISTED_SERVICE_HINT;
    }
  } catch (err) {
    debug('services fallback', err);
  }
}

async function loadSlots(date) {
  const seq = ++slotSeq;
  const previous = els.time.value;
  els.timeHint.hidden = false;
  els.timeHint.textContent = 'Checking open times…';
  try {
    const data = await api.availableSlots(barber.id, date);
    if (seq !== slotSeq) return;
    const slots = Array.isArray(data.slots) ? data.slots : [];
    if (slots.length) {
      setTimeOptions(slots, { keep: previous });
      els.timeHint.textContent = `${slots.length} open ${slots.length === 1 ? 'time' : 'times'} on ${formatDate(date)}.`;
    } else {
      setTimeOptions([]);
      els.timeHint.textContent = `No open times on ${formatDate(date)}. Pick another day.`;
    }
  } catch (err) {
    if (seq !== slotSeq) return;
    debug('slots fallback', err);
    setTimeOptions(DEFAULT_TIMES, { keep: previous });
    els.timeHint.hidden = true;
  }
}

export function openBooking(target) {
  barber = target;
  services = DEFAULT_SERVICES;
  els.info.innerHTML = html`<p class="list-title">${target.name}</p><p class="list-text">${[target.address, target.phone].filter(Boolean).join(' · ') || 'Booking request'}</p>`;
  els.name.value = getIdentity().displayName || '';
  els.date.min = todayIso();
  els.date.value = '';
  els.notes.value = '';
  setTimeOptions(DEFAULT_TIMES);
  setServiceOptions(services);
  els.serviceHint.textContent = DEFAULT_SERVICE_HINT;
  els.timeHint.hidden = true;
  clearFormErrors(els.form);
  openModal('book-appointment-modal');
  loadServices(target);
}

async function submit(event) {
  event.preventDefault();
  if (!barber || submitting) return;
  clearFormErrors(els.form);
  const name = els.name.value.trim();
  const date = els.date.value;
  const time = els.time.value;
  const serviceId = els.service.value;
  const notes = els.notes.value.trim();

  if (!name) { setFieldError(els.error, 'Enter your name so the barber knows who is booking.', els.name); return; }
  if (!date) { setFieldError(els.error, 'Pick a date.', els.date); return; }
  if (date < todayIso()) { setFieldError(els.error, 'Pick today or a later date.', els.date); return; }
  if (!time) { setFieldError(els.error, 'Pick a time.', els.time); return; }
  if (!serviceId) { setFieldError(els.error, 'Pick a service.', els.service); return; }
  const service = services.find((s) => String(s.id) === serviceId);
  if (!service) { setFieldError(els.error, 'Pick a service.', els.service); return; }

  const identity = getIdentity();
  if (name !== identity.displayName) updateIdentity({ displayName: name });

  submitting = true;
  setBusy(els.submit, true, 'Sending…');
  try {
    const data = await api.createAppointment({
      clientName: name,
      barberId: String(barber.id),
      barberName: barber.name,
      date,
      time,
      service: service.name,
      price: money(parsePrice(service.price)),
      notes,
    });
    if (!data || data.success === false) throw new ApiError((data && data.error) || 'The booking was not saved.');
    closeModal('book-appointment-modal');
    notify.success('Booking requested', `${barber.name}, ${formatDate(date)} at ${formatTime(time)}. They will confirm shortly.`, {
      action: { label: 'View bookings', onClick: () => navigate('appointments') },
    });
    notifyAppointmentsChanged(data.appointment || null);
  } catch (err) {
    debug('booking failed', err);
    setFieldError(els.error, err instanceof ApiError ? err.message : 'The booking could not be sent. Try again.');
  } finally {
    submitting = false;
    setBusy(els.submit, false);
  }
}

export function initBooking() {
  Object.assign(els, {
    form: byId('booking-form'),
    info: byId('booking-barber-info'),
    name: byId('booking-client-name'),
    date: byId('appointment-date'),
    time: byId('appointment-time'),
    timeHint: byId('appointment-time-hint'),
    service: byId('appointment-service'),
    serviceHint: byId('appointment-service-hint'),
    notes: byId('appointment-notes'),
    error: byId('booking-error'),
    submit: byId('confirm-booking'),
  });
  els.form.addEventListener('submit', submit);
  els.date.addEventListener('change', () => {
    if (!barber || !els.date.value) return;
    if (els.date.value < todayIso()) { setFieldError(els.error, 'Pick today or a later date.', els.date); return; }
    clearFormErrors(els.form);
    loadSlots(els.date.value);
  });
}
