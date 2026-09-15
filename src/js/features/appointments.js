// Bookings for both roles. Client: list, reschedule, cancel. Barber: filters,
// accept, decline, reschedule, cancel, notes, client history.
import { byId, html, show, hide, delegate, setBusy, setFieldError, clearFormErrors, errorNotice } from '../dom.js';
import { icon } from '../icons.js';
import { api, ApiError } from '../api.js';
import { getIdentity, store } from '../state.js';
import { openModal, closeModal } from '../ui/modal.js';
import { confirmDialog } from '../ui/confirm.js';
import { notify } from '../ui/toast.js';
import { showSkeleton, skeletonCards, skeletonRows, clearBusy } from '../ui/skeleton.js';
import { onTabShow } from '../nav.js';
import { formatDate, formatTime, todayIso, appointmentDate, initials, relativeTime } from '../format.js';
import { debug } from '../env.js';

const STATUS = {
  pending: { chip: 'chip-warning', label: 'Pending' },
  confirmed: { chip: 'chip-success', label: 'Confirmed' },
  rescheduled: { chip: 'chip-warning', label: 'Rescheduled' },
  completed: { chip: 'chip-neutral', label: 'Completed' },
  cancelled: { chip: 'chip-danger', label: 'Cancelled' },
  rejected: { chip: 'chip-danger', label: 'Declined' },
};
const OPEN = new Set(['pending', 'confirmed', 'rescheduled']);

const els = {};
const listeners = new Set();
let clientList = [];
let barberList = [];
let rescheduleTarget = null;
let noteTarget = null;

export function onAppointmentsChanged(fn) { listeners.add(fn); return () => listeners.delete(fn); }
export function notifyAppointmentsChanged(appointment) {
  if (appointment && appointment.id != null) {
    const { uid, role } = getIdentity();
    if (uid && appointment.clientId === uid) clientList = upsert(clientList, appointment);
    if (uid && role === 'barber' && appointment.barberId === uid) barberList = upsert(barberList, appointment);
    store.set('clientAppointments', clientList);
    store.set('barberAppointments', barberList);
    renderClient();
    renderBarber();
  }
  listeners.forEach((fn) => { try { fn(); } catch (err) { debug('appointments listener failed', err); } });
}
export function getBarberAppointments() { return barberList; }

function upsert(list, appointment) {
  const index = list.findIndex((item) => String(item.id) === String(appointment.id));
  if (index < 0) return [...list, appointment];
  const next = list.slice();
  next[index] = { ...next[index], ...appointment };
  return next;
}

function statusChip(status) {
  const meta = STATUS[status] || { chip: 'chip-neutral', label: status || 'Unknown' };
  return html`<span class="${meta.chip}">${meta.label}</span>`;
}

function sortUpcomingFirst(list) {
  const now = Date.now();
  return list.slice().sort((a, b) => {
    const da = appointmentDate(a)?.getTime() ?? 0;
    const db = appointmentDate(b)?.getTime() ?? 0;
    const pastA = da < now;
    const pastB = db < now;
    if (pastA !== pastB) return pastA ? 1 : -1;
    return pastA ? db - da : da - db;
  });
}

function whenRow(appointment) {
  return html`<div class="meta mt-3">
    <span class="meta-item">${icon('calendar')}${formatDate(appointment.date)}</span>
    <span class="meta-item">${icon('clock')}${formatTime(appointment.time)}</span>
    ${appointment.price ? html`<span class="meta-item meta-strong">${appointment.price}</span>` : ''}
  </div>`;
}

function clientCard(appointment) {
  const status = appointment.status || 'pending';
  return html`
    <article class="card" data-appointment-id="${appointment.id}">
      <div class="card-header">
        <div class="min-w-0"><h3 class="card-title">${appointment.barberName || 'Barber'}</h3><p class="card-text">${appointment.service || 'Appointment'}</p></div>
        ${statusChip(status)}
      </div>
      ${whenRow(appointment)}
      ${appointment.notes ? html`<p class="text-sm text-text-2 mt-3"><span class="text-text-1 font-medium">Notes:</span> ${appointment.notes}</p>` : ''}
      ${status === 'rejected' && appointment.rejectionReason ? html`<p class="text-sm text-text-2 mt-3">${appointment.rejectionReason}</p>` : ''}
      ${OPEN.has(status) ? html`<div class="card-footer">
        <button type="button" class="btn-secondary btn-sm" data-action="reschedule">Reschedule</button>
        <button type="button" class="btn-ghost btn-sm" data-action="cancel">Cancel booking</button>
      </div>` : ''}
    </article>`;
}

function barberCard(appointment) {
  const status = appointment.status || 'pending';
  const notes = Array.isArray(appointment.barberNotes) ? appointment.barberNotes : [];
  return html`
    <article class="card" data-appointment-id="${appointment.id}">
      <div class="card-header">
        <div class="row min-w-0">
          <div class="avatar" aria-hidden="true">${initials(appointment.clientName)}</div>
          <div class="min-w-0"><h3 class="card-title">${appointment.clientName || 'Client'}</h3><p class="card-text">${appointment.service || 'Appointment'}</p></div>
        </div>
        ${statusChip(status)}
      </div>
      ${whenRow(appointment)}
      ${appointment.notes ? html`<p class="text-sm text-text-2 mt-3"><span class="text-text-1 font-medium">From the client:</span> ${appointment.notes}</p>` : ''}
      ${notes.length ? html`<div class="list mt-3">${notes.map((note) => html`<div class="list-row"><div class="grow"><p class="text-sm">${note.note}</p><p class="list-text">${relativeTime(note.createdAt) || 'Note'}</p></div></div>`)}</div>` : ''}
      <div class="card-footer">
        ${status === 'pending' ? html`<button type="button" class="btn-primary btn-sm" data-action="accept">Accept</button><button type="button" class="btn-secondary btn-sm" data-action="reject">Decline</button>` : ''}
        ${OPEN.has(status) ? html`<button type="button" class="btn-secondary btn-sm" data-action="reschedule">Reschedule</button>` : ''}
        ${OPEN.has(status) && status !== 'pending' ? html`<button type="button" class="btn-ghost btn-sm" data-action="cancel">Cancel</button>` : ''}
        <button type="button" class="btn-ghost btn-sm" data-action="note">${icon('pencil', { size: 'sm' })}Note</button>
        ${appointment.clientId ? html`<button type="button" class="btn-ghost btn-sm" data-action="history" aria-expanded="false">History</button>` : ''}
      </div>
      <div class="hidden" data-history></div>
    </article>`;
}

function renderClient() {
  if (!els.clientList) return;
  clearBusy(els.clientList);
  if (!clientList.length) {
    els.clientList.innerHTML = '';
    show(els.clientEmpty);
    return;
  }
  hide(els.clientEmpty);
  els.clientList.innerHTML = html`${sortUpcomingFirst(clientList).map(clientCard)}`;
}

function renderBarber() {
  if (!els.barberList) return;
  clearBusy(els.barberList);
  const filter = els.filter.value || 'all';
  const visible = sortUpcomingFirst(barberList.filter((item) => filter === 'all' || (item.status || 'pending') === filter));
  if (!visible.length) {
    els.barberList.innerHTML = '';
    els.barberEmptyText.textContent = barberList.length
      ? 'Nothing matches this filter. Try clearing it.'
      : 'New requests appear here as clients book you.';
    show(els.barberEmpty);
    return;
  }
  hide(els.barberEmpty);
  els.barberList.innerHTML = html`${visible.map(barberCard)}`;
}

export async function loadClientAppointments({ silent = false } = {}) {
  if (!silent) { hide(els.clientEmpty); showSkeleton(els.clientList, skeletonCards(2)); }
  try {
    const data = await api.appointments('client');
    clientList = Array.isArray(data.appointments) ? data.appointments : [];
    store.set('clientAppointments', clientList);
    renderClient();
  } catch (err) {
    debug('client appointments failed', err);
    clearBusy(els.clientList);
    hide(els.clientEmpty);
    els.clientList.replaceChildren(errorNotice({ title: 'Bookings did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadClientAppointments() }));
  }
  return clientList;
}

export async function loadBarberAppointments({ silent = false } = {}) {
  if (!silent) { hide(els.barberEmpty); showSkeleton(els.barberList, skeletonCards(2)); }
  try {
    const data = await api.appointments('barber');
    barberList = Array.isArray(data.appointments) ? data.appointments : [];
    store.set('barberAppointments', barberList);
    renderBarber();
  } catch (err) {
    debug('barber appointments failed', err);
    clearBusy(els.barberList);
    hide(els.barberEmpty);
    els.barberList.replaceChildren(errorNotice({ title: 'Bookings did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => loadBarberAppointments() }));
  }
  return barberList;
}

function findAppointment(list, node) {
  const card = node.closest('[data-appointment-id]');
  if (!card) return null;
  return list.find((item) => String(item.id) === String(card.dataset.appointmentId)) || null;
}

function summary(appointment, role) {
  const who = role === 'client' ? appointment.barberName : appointment.clientName;
  return `${who || 'Booking'}, ${formatDate(appointment.date)} at ${formatTime(appointment.time)}`;
}

async function runAction(button, work, { success, failure }) {
  setBusy(button, true);
  try {
    const data = await work();
    if (!data || data.success === false || !data.appointment) throw new ApiError((data && data.error) || failure);
    notifyAppointmentsChanged(data.appointment);
    if (success) notify.success(success.title, success.text);
    return true;
  } catch (err) {
    debug('appointment action failed', err);
    setBusy(button, false);
    notify.error(failure, err instanceof ApiError ? err.message : '');
    return false;
  }
}

async function handleClientAction(event, button) {
  const appointment = findAppointment(clientList, button);
  if (!appointment) return;
  const action = button.dataset.action;
  if (action === 'reschedule') { openReschedule(appointment, 'client'); return; }
  if (action === 'cancel') {
    const ok = await confirmDialog({ title: 'Cancel this booking?', body: `${summary(appointment, 'client')}. The slot goes back to the barber.`, confirmLabel: 'Cancel booking', cancelLabel: 'Keep it' });
    if (!ok) return;
    await runAction(button, () => api.cancelAppointment(appointment.id, 'Cancelled by client'), {
      success: { title: 'Booking cancelled', text: summary(appointment, 'client') },
      failure: 'Could not cancel the booking',
    });
  }
}

async function handleBarberAction(event, button) {
  const appointment = findAppointment(barberList, button);
  if (!appointment) return;
  const action = button.dataset.action;
  if (action === 'accept') {
    await runAction(button, () => api.acceptAppointment(appointment.id), {
      success: { title: 'Booking confirmed', text: summary(appointment, 'barber') },
      failure: 'Could not confirm the booking',
    });
  } else if (action === 'reject') {
    const ok = await confirmDialog({ title: 'Decline this request?', body: `${summary(appointment, 'barber')}. The client is told the slot is not available.`, confirmLabel: 'Decline', cancelLabel: 'Keep it' });
    if (!ok) return;
    await runAction(button, () => api.rejectAppointment(appointment.id, 'Declined by barber'), {
      success: { title: 'Request declined', text: summary(appointment, 'barber') },
      failure: 'Could not decline the request',
    });
  } else if (action === 'cancel') {
    const ok = await confirmDialog({ title: 'Cancel this booking?', body: `${summary(appointment, 'barber')}.`, confirmLabel: 'Cancel booking', cancelLabel: 'Keep it' });
    if (!ok) return;
    await runAction(button, () => api.cancelAppointment(appointment.id, 'Cancelled by barber'), {
      success: { title: 'Booking cancelled', text: summary(appointment, 'barber') },
      failure: 'Could not cancel the booking',
    });
  } else if (action === 'reschedule') {
    openReschedule(appointment, 'barber');
  } else if (action === 'note') {
    openNote(appointment);
  } else if (action === 'history') {
    await toggleHistory(button, appointment);
  }
}

async function toggleHistory(button, appointment) {
  const card = button.closest('[data-appointment-id]');
  const panel = card.querySelector('[data-history]');
  const expanded = button.getAttribute('aria-expanded') === 'true';
  if (expanded) { hide(panel); button.setAttribute('aria-expanded', 'false'); return; }
  button.setAttribute('aria-expanded', 'true');
  show(panel);
  showSkeleton(panel, skeletonRows(3));
  try {
    const data = await api.clientHistory(getIdentity().barberId, appointment.clientId);
    const items = Array.isArray(data.appointments) ? data.appointments : [];
    clearBusy(panel);
    panel.innerHTML = html`<div class="list mt-3 pt-3 border-t border-border">${items.length
      ? items.map((item) => html`<div class="list-row"><div class="grow"><p class="list-title">${item.service || 'Appointment'}</p><p class="list-text">${formatDate(item.date, { relative: false })} · ${formatTime(item.time)}</p></div>${statusChip(item.status || 'pending')}</div>`)
      : html`<p class="list-text py-2">No earlier visits from this client.</p>`}</div>`;
  } catch (err) {
    debug('history failed', err);
    clearBusy(panel);
    panel.replaceChildren(errorNotice({ title: 'History did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => { button.setAttribute('aria-expanded', 'false'); toggleHistory(button, appointment); } }));
  }
}

const DEFAULT_TIMES = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00'];
let slotSeq = 0;

function setRescheduleTimes(times, { keep } = {}) {
  els.rescheduleTime.innerHTML = html`<option value="">Choose a time</option>${times.map((time) => html`<option value="${time}">${formatTime(time)}</option>`)}`;
  if (keep && times.includes(keep)) els.rescheduleTime.value = keep;
}

// The same slot source the booking modal uses; a fixed 9-to-5 list let a client
// reschedule onto a day the shop is closed, where the barber would never see it.
async function loadRescheduleSlots(date) {
  const target = rescheduleTarget;
  const barberId = target?.appointment?.barberId;
  if (!date || !barberId) { setRescheduleTimes(DEFAULT_TIMES); els.rescheduleTimeHint.hidden = true; return; }
  const seq = ++slotSeq;
  const previous = els.rescheduleTime.value;
  els.rescheduleTimeHint.hidden = false;
  els.rescheduleTimeHint.textContent = 'Checking open times…';
  try {
    const data = await api.availableSlots(barberId, date);
    if (seq !== slotSeq || rescheduleTarget !== target) return;
    const slots = Array.isArray(data.slots) ? data.slots : [];
    if (slots.length) {
      setRescheduleTimes(slots, { keep: previous });
      els.rescheduleTimeHint.textContent = `${slots.length} open ${slots.length === 1 ? 'time' : 'times'} on ${formatDate(date)}.`;
    } else {
      setRescheduleTimes([]);
      els.rescheduleTimeHint.textContent = `No open times on ${formatDate(date)}. Pick another day.`;
    }
  } catch (err) {
    if (seq !== slotSeq || rescheduleTarget !== target) return;
    debug('reschedule slots fallback', err);
    setRescheduleTimes(DEFAULT_TIMES, { keep: previous });
    els.rescheduleTimeHint.hidden = true;
  }
}

export function openReschedule(appointment, role) {
  rescheduleTarget = { appointment, role };
  els.rescheduleInfo.innerHTML = html`<p class="list-title">${role === 'client' ? appointment.barberName : appointment.clientName}</p><p class="list-text">${appointment.service || 'Appointment'} · currently ${formatDate(appointment.date)} at ${formatTime(appointment.time)}</p>`;
  els.rescheduleSubtitle.textContent = role === 'client' ? 'Pick a new date and time. The barber confirms it.' : 'Pick a new date and time. The client is told.';
  els.rescheduleDate.min = todayIso();
  els.rescheduleDate.value = appointment.date && appointment.date >= todayIso() ? appointment.date : '';
  setRescheduleTimes(DEFAULT_TIMES, { keep: appointment.time });
  els.rescheduleTimeHint.hidden = true;
  els.rescheduleReason.value = '';
  clearFormErrors(els.rescheduleForm);
  openModal('reschedule-modal');
  if (els.rescheduleDate.value) loadRescheduleSlots(els.rescheduleDate.value);
}

async function submitReschedule(event) {
  event.preventDefault();
  if (!rescheduleTarget) return;
  clearFormErrors(els.rescheduleForm);
  const { appointment, role } = rescheduleTarget;
  const date = els.rescheduleDate.value;
  const time = els.rescheduleTime.value;
  if (!date) { setFieldError(els.rescheduleError, 'Pick a new date.', els.rescheduleDate); return; }
  if (date < todayIso()) { setFieldError(els.rescheduleError, 'Pick today or a later date.', els.rescheduleDate); return; }
  if (!time) { setFieldError(els.rescheduleError, 'Pick a new time.', els.rescheduleTime); return; }
  if (date === appointment.date && time === appointment.time) { setFieldError(els.rescheduleError, 'That is the current time. Pick a different one.', els.rescheduleTime); return; }
  const reason = els.rescheduleReason.value.trim() || (role === 'client' ? 'Rescheduled by client' : 'Rescheduled by barber');
  setBusy(els.rescheduleSubmit, true, 'Saving…');
  try {
    const data = await api.rescheduleAppointment(appointment.id, { date, time, reason });
    if (!data || data.success === false || !data.appointment) throw new ApiError((data && data.error) || 'The new time was not saved.');
    closeModal('reschedule-modal');
    notifyAppointmentsChanged(data.appointment);
    notify.success('Rescheduled', `${formatDate(date)} at ${formatTime(time)}.`);
  } catch (err) {
    debug('reschedule failed', err);
    setFieldError(els.rescheduleError, err instanceof ApiError ? err.message : 'The new time could not be saved.');
  } finally {
    setBusy(els.rescheduleSubmit, false);
  }
}

function openNote(appointment) {
  noteTarget = appointment;
  els.noteInfo.innerHTML = html`<p class="list-title">${appointment.clientName || 'Client'}</p><p class="list-text">${appointment.service || 'Appointment'} · ${formatDate(appointment.date)} at ${formatTime(appointment.time)}</p>`;
  els.noteText.value = '';
  clearFormErrors(els.noteForm);
  openModal('note-modal', { focus: els.noteText });
}

async function submitNote(event) {
  event.preventDefault();
  if (!noteTarget) return;
  const text = els.noteText.value.trim();
  if (!text) { setFieldError(els.noteError, 'Write a note first.', els.noteText); return; }
  setBusy(els.noteSubmit, true, 'Saving…');
  try {
    const data = await api.addAppointmentNote(noteTarget.id, text);
    if (!data || data.success === false || !data.appointment) throw new ApiError((data && data.error) || 'The note was not saved.');
    closeModal('note-modal');
    notifyAppointmentsChanged(data.appointment);
    notify.success('Note saved');
  } catch (err) {
    debug('note failed', err);
    setFieldError(els.noteError, err instanceof ApiError ? err.message : 'The note could not be saved.');
  } finally {
    setBusy(els.noteSubmit, false);
  }
}

export function initAppointments() {
  Object.assign(els, {
    clientList: byId('client-appointments-container'),
    clientEmpty: byId('no-appointments'),
    barberList: byId('barber-appointments-container'),
    barberEmpty: byId('barber-no-appointments'),
    barberEmptyText: byId('barber-no-appointments').querySelector('.empty-state-text'),
    filter: byId('status-filter'),
    clearFilters: byId('clear-filters'),
    rescheduleForm: byId('reschedule-form'),
    rescheduleInfo: byId('reschedule-appointment-info'),
    rescheduleSubtitle: byId('reschedule-subtitle'),
    rescheduleDate: byId('reschedule-date'),
    rescheduleTime: byId('reschedule-time'),
    rescheduleTimeHint: byId('reschedule-time-hint'),
    rescheduleReason: byId('reschedule-reason'),
    rescheduleError: byId('reschedule-error'),
    rescheduleSubmit: byId('confirm-reschedule'),
    noteForm: byId('note-form'),
    noteInfo: byId('note-appointment-info'),
    noteText: byId('note-text'),
    noteError: byId('note-error'),
    noteSubmit: byId('submit-note'),
  });
  delegate(els.clientList, 'click', '[data-action]', handleClientAction);
  delegate(els.barberList, 'click', '[data-action]', handleBarberAction);
  els.filter.addEventListener('change', renderBarber);
  els.clearFilters.addEventListener('click', () => { els.filter.value = 'all'; renderBarber(); });
  els.rescheduleForm.addEventListener('submit', submitReschedule);
  els.rescheduleDate.addEventListener('change', () => loadRescheduleSlots(els.rescheduleDate.value));
  els.noteForm.addEventListener('submit', submitNote);
  onTabShow('appointments', () => loadClientAppointments({ silent: clientList.length > 0 }));
  onTabShow('barber-schedule', () => loadBarberAppointments({ silent: barberList.length > 0 }));
}
