// Barber home: stats computed from this barber's appointments and portfolio,
// popular services and peak times as neutral meters.
import { byId, html } from '../dom.js';
import { onTabShow, navigate, currentTab } from '../nav.js';
import { openModal } from '../ui/modal.js';
import { showSkeleton, skeletonRows, clearBusy } from '../ui/skeleton.js';
import { loadBarberAppointments, getBarberAppointments, onAppointmentsChanged } from './appointments.js';
import { loadPortfolio, getPortfolio } from './portfolio.js';
import { parsePrice, plural, formatTime, todayIso } from '../format.js';
import { debug } from '../env.js';

const COUNTED = new Set(['pending', 'confirmed', 'rescheduled', 'completed']);
const REVENUE = new Set(['confirmed', 'rescheduled', 'completed']);
const HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18];

const els = {};

function monthKey(date) { return `${date.getFullYear()}-${date.getMonth()}`; }

function parseDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ''));
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : null;
}

function compute(appointments, portfolio) {
  const now = new Date();
  const thisMonth = monthKey(now);
  const lastMonth = monthKey(new Date(now.getFullYear(), now.getMonth() - 1, 1));
  const active = appointments.filter((apt) => COUNTED.has(apt.status || 'pending'));

  const inMonth = (key) => active.filter((apt) => { const d = parseDate(apt.date); return d && monthKey(d) === key; });
  const thisMonthList = inMonth(thisMonth);
  const lastMonthList = inMonth(lastMonth);
  const revenueOf = (list) => list.filter((apt) => REVENUE.has(apt.status)).reduce((sum, apt) => sum + parsePrice(apt.price), 0);
  const revenue = revenueOf(thisMonthList);
  const lastRevenue = revenueOf(lastMonthList);

  const clients = new Set(active.map((apt) => apt.clientId).filter(Boolean));
  const firstSeen = new Map();
  active.forEach((apt) => {
    if (!apt.clientId) return;
    const d = parseDate(apt.date);
    if (!d) return;
    const prev = firstSeen.get(apt.clientId);
    if (!prev || d < prev) firstSeen.set(apt.clientId, d);
  });
  const newClients = Array.from(firstSeen.values()).filter((d) => monthKey(d) === thisMonth).length;

  const today = todayIso();
  const todayCount = active.filter((apt) => apt.date === today).length;
  const weekStart = new Date(now.getFullYear(), now.getMonth(), now.getDate() - now.getDay());
  const weekEnd = new Date(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate() + 7);
  const weekCount = active.filter((apt) => { const d = parseDate(apt.date); return d && d >= weekStart && d < weekEnd; }).length;

  // A fixed ceiling, not the barber's own hours: the card is labelled
  // "Of 176 slots a month" so the number is not read as real capacity.
  const capacity = 22 * 8;
  const utilization = Math.min(100, Math.round((thisMonthList.length / capacity) * 100));

  els.revenue.textContent = `$${Math.round(revenue).toLocaleString('en-US')}`;
  let change = 'vs last month';
  els.revenueChange.classList.remove('stat-delta-up', 'stat-delta-down');
  if (lastRevenue > 0) {
    const pct = Math.round(((revenue - lastRevenue) / lastRevenue) * 100);
    change = `${pct >= 0 ? '+' : ''}${pct}% vs last month`;
    els.revenueChange.classList.add(pct >= 0 ? 'stat-delta-up' : 'stat-delta-down');
  } else if (revenue > 0) {
    change = 'First bookings this month';
    els.revenueChange.classList.add('stat-delta-up');
  }
  els.revenueChange.textContent = change;
  els.appointments.textContent = String(thisMonthList.length);
  els.appointmentsChange.textContent = 'This month';
  els.clients.textContent = String(clients.size);
  els.newClients.textContent = `${newClients} new this month`;
  els.utilization.textContent = `${utilization}%`;
  els.today.textContent = String(todayCount);
  els.week.textContent = String(weekCount);
  els.portfolioCount.textContent = String(portfolio.length);

  renderServices(active);
  renderPeakTimes(active);
}

function renderServices(appointments) {
  clearBusy(els.services);
  const counts = new Map();
  appointments.forEach((apt) => { const name = apt.service || 'Other'; counts.set(name, (counts.get(name) || 0) + 1); });
  const total = appointments.length;
  const top = Array.from(counts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 5);
  if (!top.length) {
    els.services.innerHTML = '<p class="text-sm text-text-2 py-2">No bookings yet. Popular services show up once clients book.</p>';
    return;
  }
  els.services.innerHTML = html`${top.map(([name, count]) => {
    const pct = Math.round((count / total) * 100);
    return html`<div class="list-row"><div class="grow"><p class="list-title">${name}</p><p class="list-text">${plural(count, 'booking')} · ${pct}%</p></div><div class="meter" aria-hidden="true"><div class="meter-fill" style="width:${pct}%"></div></div></div>`;
  })}`;
}

function renderPeakTimes(appointments) {
  clearBusy(els.peak);
  const counts = new Map();
  appointments.forEach((apt) => {
    const hour = parseInt(String(apt.time || '').split(':')[0], 10);
    if (!Number.isNaN(hour)) counts.set(hour, (counts.get(hour) || 0) + 1);
  });
  const max = Math.max(0, ...counts.values());
  if (!max) {
    els.peak.innerHTML = '<p class="text-sm text-text-2 py-2">No booking times yet. Peak hours appear after a few bookings.</p>';
    return;
  }
  els.peak.innerHTML = html`${HOURS.map((hour) => {
    const count = counts.get(hour) || 0;
    const pct = Math.round((count / max) * 100);
    return html`<div class="list-row" style="min-height:40px;padding:8px 0"><span class="list-text" style="width:56px">${formatTime(`${String(hour).padStart(2, '0')}:00`).replace(':00', '')}</span><div class="meter meter-wide" aria-hidden="true"><div class="meter-fill" style="width:${pct}%"></div></div><span class="list-value">${count}</span></div>`;
  })}`;
}

export async function refreshDashboard() {
  showSkeleton(els.services, skeletonRows(3));
  showSkeleton(els.peak, skeletonRows(3));
  const [appointments, portfolio] = await Promise.all([
    loadBarberAppointments({ silent: true }).catch((err) => { debug(err); return getBarberAppointments(); }),
    loadPortfolio({ silent: true }).catch((err) => { debug(err); return getPortfolio(); }),
  ]);
  compute(appointments || [], portfolio || []);
}

export function initDashboard() {
  Object.assign(els, {
    revenue: byId('total-revenue'),
    revenueChange: byId('revenue-change'),
    appointments: byId('total-appointments'),
    appointmentsChange: byId('appointments-change'),
    clients: byId('total-clients'),
    newClients: byId('new-clients'),
    utilization: byId('utilization-rate'),
    today: byId('today-appointments'),
    week: byId('week-appointments'),
    portfolioCount: byId('portfolio-count'),
    services: byId('services-analytics'),
    peak: byId('peak-times'),
  });
  byId('add-portfolio-btn').addEventListener('click', () => openModal('upload-work-modal'));
  byId('view-schedule-btn').addEventListener('click', () => navigate('barber-schedule'));
  onTabShow('barber-dashboard', refreshDashboard);
  onAppointmentsChanged(() => { if (currentTab() === 'barber-dashboard') compute(getBarberAppointments(), getPortfolio()); });
}
