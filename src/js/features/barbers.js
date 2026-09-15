// Explore tab: location search, result cards, reviews modal, and
// the "where are you?" prompt used when a recommendation card asks for barbers.
import { byId, html, delegate, setFieldError, clearFieldError, errorNotice } from '../dom.js';
import { icon } from '../icons.js';
import { api, ApiError } from '../api.js';
import { getIdentity, updateIdentity } from '../state.js';
import { openModal, closeModal } from '../ui/modal.js';
import { showSkeleton, skeletonCards, skeletonRows, clearBusy } from '../ui/skeleton.js';
import { navigate, onTabShow } from '../nav.js';
import { initials, plural, money } from '../format.js';
import { UI, debug } from '../env.js';
import { openBooking } from './booking.js';

const els = {};
let results = [];
let currentStyles = [];
let pendingStyle = null;
let requestSeq = 0;
let searched = false;
let reviewsBarber = null;

export function getBarber(id) { return results.find((barber) => String(barber.id) === String(id)) || null; }

function describeQuery(location, styles, count, mock) {
  const where = location ? ` near ${location}` : '';
  const forStyles = styles.length ? ` who do ${styles.slice(0, 2).join(' or ')}` : '';
  return html`${plural(count, 'barbershop')}${where}${forStyles}.${mock ? html` <span class="chip-neutral ml-1">Sample data</span>` : ''}`;
}

// Google Places returns `hours` as `weekday_text` (seven "Monday: 9:00 AM - 8:00 PM"
// strings); the sample data returns one string. A card has room for today's line.
function todaysHours(hours) {
  if (typeof hours === 'string') return hours.trim();
  if (!Array.isArray(hours) || !hours.length) return '';
  const weekday = new Date().toLocaleDateString('en-US', { weekday: 'long' });
  const line = hours.find((entry) => typeof entry === 'string' && entry.startsWith(`${weekday}:`)) || '';
  return line ? line.slice(weekday.length + 1).trim() : '';
}

function barberCard(barber, index) {
  const rating = Number(barber.rating) || 0;
  const reviews = Number(barber.user_ratings_total) || 0;
  const specialties = Array.isArray(barber.specialties) ? barber.specialties.slice(0, 5) : [];
  const price = barber.avgCost != null && barber.avgCost !== '' ? money(barber.avgCost) : '';
  const hours = todaysHours(barber.hours);
  return html`
    <article class="card split-card" data-index="${index}">
      <div class="split-media">${barber.photo
        ? html`<img src="${barber.photo}" alt="${barber.name}" loading="lazy" width="400" height="300">`
        : icon('scissors', { size: 'lg' })}</div>
      <div class="min-w-0">
        <div class="card-header">
          <div class="min-w-0"><h3 class="card-title">${barber.name}</h3><p class="card-text">${barber.address || 'Address not listed'}</p></div>
          ${rating ? html`<span class="chip-accent">${icon('star')}${rating.toFixed(1)}</span>` : ''}
        </div>
        <div class="meta">
          ${reviews ? html`<span class="meta-item">${plural(reviews, 'review')}</span>` : ''}
          ${price ? html`<span class="meta-item">From <span class="meta-strong">${price}</span></span>` : ''}
          ${hours ? html`<span class="meta-item">${icon('clock')}${hours}</span>` : ''}
          ${barber.phone ? html`<span class="meta-item">${icon('phone')}${barber.phone}</span>` : ''}
        </div>
        ${specialties.length ? html`<div class="chip-row mt-3">${specialties.map((item) => html`<span class="chip-neutral">${item}</span>`)}</div>` : ''}
        <div class="card-footer">
          <button type="button" class="btn-primary btn-sm" data-action="book" data-index="${index}">Book</button>
          <button type="button" class="btn-secondary btn-sm" data-action="reviews" data-index="${index}">Reviews</button>
          ${barber.google_maps_url ? html`<a class="btn-ghost btn-sm" href="${barber.google_maps_url}" target="_blank" rel="noopener noreferrer">${icon('map-pin', { size: 'sm' })}Map</a>` : ''}
          ${barber.website ? html`<a class="btn-ghost btn-sm" href="${barber.website}" target="_blank" rel="noopener noreferrer">${icon('external', { size: 'sm' })}Website</a>` : ''}
          ${barber.bookingUrl || barber.booking_url ? html`<a class="btn-ghost btn-sm" href="${barber.bookingUrl || barber.booking_url}" target="_blank" rel="noopener noreferrer">${icon('external', { size: 'sm' })}Book on their site</a>` : ''}
        </div>
      </div>
    </article>`;
}

function renderResults(data, location, styles) {
  const mock = Boolean(data.mock) || data.real_data === false;
  els.intro.innerHTML = describeQuery(location, styles, results.length, mock);
  if (!results.length) {
    els.list.innerHTML = html`<div class="empty-state">${icon('search', { size: 'lg', className: 'empty-state-icon' })}<p class="empty-state-title">No barbershops found</p><p class="empty-state-text">Try a ZIP code, or a larger nearby city.</p><button type="button" class="btn-secondary btn-sm" data-action="focus-search">Change location</button></div>`;
    return;
  }
  els.list.innerHTML = html`${results.map(barberCard)}`;
}

export async function searchBarbers(location, styles = []) {
  const query = String(location || '').trim();
  if (!query) return;
  currentStyles = styles;
  searched = true;
  updateIdentity({ lastLocation: query });
  if (els.input.value.trim() !== query) els.input.value = query;
  clearFieldError(els.error, els.input);
  const seq = ++requestSeq;
  els.intro.textContent = `Searching near ${query}…`;
  showSkeleton(els.list, skeletonCards(3));
  try {
    const data = await api.barbers(query, styles);
    if (seq !== requestSeq) return;
    results = Array.isArray(data.barbers) ? data.barbers : [];
    clearBusy(els.list);
    renderResults(data, query, styles);
  } catch (err) {
    if (seq !== requestSeq) return;
    debug('barber search failed', err);
    clearBusy(els.list);
    els.intro.textContent = '';
    els.list.replaceChildren(errorNotice({
      title: 'Search did not finish',
      text: err instanceof ApiError ? err.message : 'Something went wrong.',
      onRetry: () => searchBarbers(query, styles),
    }));
  }
}

export function searchForStyles(styles) {
  currentStyles = styles || [];
  const location = els.input.value.trim() || getIdentity().lastLocation;
  navigate('barbers');
  if (location) searchBarbers(location, currentStyles);
  else openZipcodePrompt(currentStyles[0] || null);
}

export function findBarbersForStyle(styleName) {
  openZipcodePrompt(styleName);
}

export function openZipcodePrompt(styleName) {
  pendingStyle = styleName;
  els.zipSubtitle.textContent = styleName
    ? `We'll look for barbers near you who do a ${styleName.toLowerCase()}.`
    : "We'll look for barbershops near you.";
  els.zipInput.value = getIdentity().lastLocation || '';
  clearFieldError(els.zipError, els.zipInput);
  openModal('zipcode-modal', { focus: els.zipInput });
}

function submitZipcode(event) {
  event.preventDefault();
  const location = els.zipInput.value.trim();
  if (!location) { setFieldError(els.zipError, 'Enter a ZIP code or city.', els.zipInput); return; }
  const styles = pendingStyle ? [pendingStyle] : currentStyles;
  pendingStyle = null;
  closeModal('zipcode-modal');
  navigate('barbers');
  searchBarbers(location, styles);
}

async function openReviews(barber) {
  reviewsBarber = barber;
  els.reviewsSubtitle.textContent = barber.name;
  els.reviewsSummary.innerHTML = '';
  showSkeleton(els.reviewsList, skeletonRows(4));
  openModal('reviews-modal');
  try {
    const data = await api.reviews(barber.id);
    if (reviewsBarber !== barber) return;
    clearBusy(els.reviewsList);
    const reviews = Array.isArray(data.reviews) ? data.reviews : [];
    const average = Number(data.average_rating) || Number(barber.rating) || 0;
    const total = Number(data.total_reviews) || reviews.length;
    els.reviewsSummary.innerHTML = html`
      <div class="row">
        <p class="rating-big">${average ? average.toFixed(1) : '–'}</p>
        <div class="grow"><p class="list-title">${total ? plural(total, 'review') : 'No reviews yet'}</p><p class="list-text">${data.source === 'google' ? 'From Google' : 'From LineUp clients'}</p></div>
        ${average ? html`<span class="chip-accent">${icon('star')}${average.toFixed(1)}</span>` : ''}
      </div>`;
    els.reviewsList.innerHTML = reviews.length
      ? html`${reviews.map((review) => html`
          <div class="list-row items-start">
            <div class="avatar avatar-sm" aria-hidden="true">${initials(review.username)}</div>
            <div class="grow">
              <div class="row"><p class="list-title grow">${review.username || 'Anonymous'}</p><span class="chip-accent">${icon('star')}${Number(review.rating) || 5}</span></div>
              <p class="list-text">${review.relative_time || review.date || ''}</p>
              ${review.text ? html`<p class="text-sm mt-1">${review.text}</p>` : ''}
            </div>
          </div>`)}`
      : html`<div class="empty-state">${icon('message', { size: 'lg', className: 'empty-state-icon' })}<p class="empty-state-title">No reviews yet</p><p class="empty-state-text">Reviews appear here once clients leave them.</p></div>`;
  } catch (err) {
    if (reviewsBarber !== barber) return;
    debug('reviews failed', err);
    clearBusy(els.reviewsList);
    els.reviewsList.replaceChildren(errorNotice({ title: 'Reviews did not load', text: err instanceof ApiError ? err.message : '', onRetry: () => openReviews(barber) }));
  }
}

export function initBarbers() {
  Object.assign(els, {
    form: byId('barber-search'),
    input: byId('location-search'),
    error: byId('location-search-error'),
    intro: byId('barber-intro'),
    list: byId('barber-list-container'),
    zipForm: byId('zipcode-form'),
    zipInput: byId('zipcode-input'),
    zipError: byId('zipcode-error'),
    zipSubtitle: byId('zipcode-modal-subtitle'),
    reviewsSubtitle: byId('reviews-modal-subtitle'),
    reviewsSummary: byId('reviews-summary'),
    reviewsList: byId('reviews-list'),
    reviewsBook: byId('reviews-book'),
  });
  els.input.value = getIdentity().lastLocation || '';
  els.input.placeholder = `30308 or ${UI.defaultLocation}`;

  // A search costs a credit, so it only runs when the user asks for one.
  // Searching as they type spent two or three of a new account's three credits
  // on the way to typing one ZIP code.
  els.form.addEventListener('submit', (event) => {
    event.preventDefault();
    const value = els.input.value.trim();
    if (!value) { setFieldError(els.error, 'Enter a ZIP code or city.', els.input); return; }
    searchBarbers(value, currentStyles);
  });
  els.input.addEventListener('input', () => clearFieldError(els.error, els.input));
  els.zipForm.addEventListener('submit', submitZipcode);

  delegate(els.list, 'click', '[data-action]', (event, button) => {
    const barber = getBarber(results[Number(button.dataset.index)]?.id);
    if (button.dataset.action === 'focus-search') { els.input.focus(); return; }
    if (!barber) return;
    if (button.dataset.action === 'book') openBooking(barber);
    else if (button.dataset.action === 'reviews') openReviews(barber);
  });
  els.list.addEventListener('error', (event) => {
    if (event.target instanceof HTMLImageElement) event.target.closest('.split-media')?.classList.add('is-broken');
  }, true);
  els.reviewsBook.addEventListener('click', () => {
    if (!reviewsBarber) return;
    const barber = reviewsBarber;
    closeModal('reviews-modal');
    openBooking(barber);
  });

  onTabShow('barbers', () => {
    if (searched) return;
    const location = getIdentity().lastLocation;
    if (location) searchBarbers(location, currentStyles);
  });
}
