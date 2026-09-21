// Explore tab: location search, result cards with a call / map / website
// link, the reviews modal, and the "where are you?" prompt used when a
// recommendation card asks for barbers. Booking happens with the shop
// directly; LineUp does not take appointments.
import { byId, html, delegate, setFieldError, clearFieldError, errorNotice } from '../dom.js';
import { icon } from '../icons.js';
import { api, ApiError } from '../api.js';
import { getIdentity, updateIdentity, getSavedAnalysis } from '../state.js';
import { openModal, closeModal } from '../ui/modal.js';
import { showSkeleton, skeletonCards, skeletonRows, clearBusy } from '../ui/skeleton.js';
import { navigate, onTabShow } from '../nav.js';
import { initials, plural, money } from '../format.js';
import { UI, debug } from '../env.js';

const els = {};
let results = [];
let currentStyles = [];

// What this person needs, from their saved analysis: the recommended cuts and
// their hair texture. Every search on this tab ranks for it, so a plain
// location search is still "for you" once a photo has been analysed.
function savedNeed() {
  const saved = getSavedAnalysis();
  if (!saved || saved.mock || !saved.analysis) return { styles: [], hair: '' };
  const styles = (saved.recommendations || []).map((rec) => rec.styleName).filter(Boolean).slice(0, 6);
  const hair = String(saved.analysis.hairTexture || '').trim().toLowerCase();
  return { styles, hair };
}
let pendingStyle = null;
let requestSeq = 0;
let searched = false;
let reviewsBarber = null;

function describeQuery(location, count, mock, rankedFor) {
  const where = location ? ` near ${location}` : '';
  const summary = rankedFor && rankedFor.summary;
  const need = summary
    ? html`<p class="ranked-for">${icon('zap', { size: 'sm' })}<span><strong>Ranked for you.</strong> ${summary}.</span></p>`
    : html`<p class="ranked-for is-empty">${icon('info', { size: 'sm' })}<span>These are ranked by rating. <button type="button" class="link-inline" data-tab="ai">Analyze a photo</button> and we'll rank them for your cut and hair.</span></p>`;
  return html`<span>${plural(count, 'barbershop')}${where}.${mock ? html` <span class="chip-neutral ml-1">Sample data</span>` : ''}</span>${need}`;
}

// A price the card can stand behind: what reviewers paid, or Google's tier.
// The old "$55 for everyone" came from defaulting a tier Google never sent.
function priceLabel(barber) {
  if (barber.avgCost != null && barber.avgCost !== '') {
    const from = barber.price_source === 'reviews' ? 'per reviews' : (barber.price_source === 'sample' ? 'sample' : '');
    return html`<span class="meta-item">About <span class="meta-strong">${money(barber.avgCost)}</span>${from ? html`<span class="price-hint">${from}</span>` : ''}</span>`;
  }
  if (barber.price_tier) return html`<span class="meta-item"><span class="meta-strong">${barber.price_tier}</span><span class="price-hint">on Google</span></span>`;
  return '';
}

const LEVEL_LABEL = { strong: 'Strong match', good: 'Good match', some: 'Some match' };

// The badge only claims a match when the data shows one. A top card with no
// evidence for the need is "top rated", and the why-list says why.
function matchBadge(match, index, rankedFor) {
  const evidence = Boolean(rankedFor && match && match.evidence);
  if (index === 0) {
    if (evidence) {
      const what = match.top_style || (rankedFor.styles && rankedFor.styles[0]) || 'you';
      return html`<span class="best-badge">${icon('zap', { size: 'sm' })}Best match for your ${what}</span>`;
    }
    return html`<span class="best-badge is-rating">${icon('star', { size: 'sm' })}Top rated nearby</span>`;
  }
  if (!rankedFor || !match) return '';
  if (match.level) {
    const label = LEVEL_LABEL[match.level] || 'Match';
    return html`<span class="chip-neutral chip-match is-${match.level}">${label}${match.top_style ? html` · ${match.top_style}` : ''}</span>`;
  }
  return html`<span class="chip-neutral chip-match">Ranked on rating</span>`;
}

function whyBlock(match, rankedFor) {
  const reasons = match && Array.isArray(match.reasons) ? match.reasons.filter(Boolean).slice(0, 3) : [];
  if (!reasons.length) return '';
  return html`
    <div class="why">
      <p class="why-title">${rankedFor ? "Why it's ranked for you" : 'Why it ranks here'}</p>
      <ul class="why-list">${reasons.map((reason) => html`<li class="${/^No reviews mention/.test(reason) ? 'is-gap' : ''}">${icon(/^No reviews mention/.test(reason) ? 'info' : 'check', { size: 'sm' })}<span>${reason}</span></li>`)}</ul>
    </div>`;
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

function barberCard(barber, index, rankedFor) {
  const rating = Number(barber.rating) || 0;
  const reviews = Number(barber.user_ratings_total) || 0;
  const specialties = Array.isArray(barber.specialties) ? barber.specialties.slice(0, 5) : [];
  const hours = todaysHours(barber.hours);
  const match = barber.match || null;
  const best = index === 0;
  return html`
    <article class="card split-card ${best ? 'is-best' : ''}" data-index="${index}">
      <div class="split-media">
        <span class="rank-badge" aria-label="Rank ${index + 1}">${index + 1}</span>
        ${barber.photo
          ? html`<img src="${barber.photo}" alt="${barber.name}" loading="lazy" width="400" height="300">`
          : icon('scissors', { size: 'lg' })}
      </div>
      <div class="min-w-0">
        ${matchBadge(match, index, rankedFor)}
        <div class="card-header">
          <div class="min-w-0"><h3 class="card-title">${barber.name}</h3><p class="card-text">${barber.address || 'Address not listed'}</p></div>
          ${rating ? html`<span class="chip-accent">${icon('star')}${rating.toFixed(1)}</span>` : ''}
        </div>
        <div class="meta">
          ${reviews ? html`<span class="meta-item">${plural(reviews, 'review')}</span>` : ''}
          ${priceLabel(barber)}
          ${hours ? html`<span class="meta-item">${icon('clock')}${hours}</span>` : ''}
          ${barber.phone ? html`<a class="meta-item link-quiet" href="tel:${String(barber.phone).replace(/[^+\d]/g, '')}">${icon('phone')}${barber.phone}</a>` : ''}
        </div>
        ${whyBlock(match, rankedFor)}
        ${specialties.length ? html`<div class="chip-row mt-3">${specialties.map((item) => html`<span class="chip-neutral">${item}</span>`)}</div>` : ''}
        <div class="card-footer">
          ${barber.bookingUrl || barber.booking_url
            ? html`<a class="btn-primary btn-sm" href="${barber.bookingUrl || barber.booking_url}" target="_blank" rel="noopener noreferrer">${icon('external', { size: 'sm' })}Book on their site</a>`
            : (barber.website ? html`<a class="btn-primary btn-sm" href="${barber.website}" target="_blank" rel="noopener noreferrer">${icon('external', { size: 'sm' })}Website</a>` : '')}
          <button type="button" class="btn-secondary btn-sm" data-action="reviews" data-index="${index}">Reviews</button>
          ${barber.google_maps_url ? html`<a class="btn-ghost btn-sm" href="${barber.google_maps_url}" target="_blank" rel="noopener noreferrer">${icon('map-pin', { size: 'sm' })}Map</a>` : ''}
          ${(barber.bookingUrl || barber.booking_url) && barber.website ? html`<a class="btn-ghost btn-sm" href="${barber.website}" target="_blank" rel="noopener noreferrer">${icon('external', { size: 'sm' })}Website</a>` : ''}
        </div>
      </div>
    </article>`;
}

function renderResults(data, location) {
  const mock = Boolean(data.mock) || data.real_data === false;
  const rankedFor = data.ranked_by_style && data.ranked_for ? data.ranked_for : null;
  els.intro.innerHTML = describeQuery(location, results.length, mock, rankedFor);
  if (!results.length) {
    els.list.innerHTML = html`<div class="empty-state">${icon('search', { size: 'lg', className: 'empty-state-icon' })}<p class="empty-state-title">No barbershops found</p><p class="empty-state-text">Try a ZIP code, or a larger nearby city.</p><button type="button" class="btn-secondary btn-sm" data-action="focus-search">Change location</button></div>`;
    return;
  }
  els.list.innerHTML = html`${results.map((barber, index) => barberCard(barber, index, rankedFor))}`;
}

export async function searchBarbers(location, styles = []) {
  const query = String(location || '').trim();
  if (!query) return;
  // Rank for what the person needs even when they only typed a location:
  // the cuts they were recommended, and their hair texture.
  const need = savedNeed();
  currentStyles = styles.length ? styles : need.styles;
  const hair = need.hair;
  searched = true;
  updateIdentity({ lastLocation: query });
  if (els.input.value.trim() !== query) els.input.value = query;
  clearFieldError(els.error, els.input);
  const seq = ++requestSeq;
  els.intro.textContent = `Searching near ${query}…`;
  showSkeleton(els.list, skeletonCards(3));
  try {
    const data = await api.barbers(query, currentStyles, hair);
    if (seq !== requestSeq) return;
    results = Array.isArray(data.barbers) ? data.barbers : [];
    clearBusy(els.list);
    renderResults(data, query);
  } catch (err) {
    if (seq !== requestSeq) return;
    debug('barber search failed', err);
    clearBusy(els.list);
    els.intro.textContent = '';
    els.list.replaceChildren(errorNotice({
      title: 'Search did not finish',
      text: err instanceof ApiError ? err.message : 'Something went wrong.',
      onRetry: () => searchBarbers(query, currentStyles),
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
    const barber = results[Number(button.dataset.index)] || null;
    if (button.dataset.action === 'focus-search') { els.input.focus(); return; }
    if (!barber) return;
    if (button.dataset.action === 'reviews') openReviews(barber);
  });
  els.list.addEventListener('error', (event) => {
    if (event.target instanceof HTMLImageElement) event.target.closest('.split-media')?.classList.add('is-broken');
  }, true);
  onTabShow('barbers', () => {
    if (searched) return;
    const location = getIdentity().lastLocation;
    if (location) searchBarbers(location, currentStyles);
  });
}
