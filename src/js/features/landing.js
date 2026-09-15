// Motion on the marketing views: elements tagged [data-reveal] fade and rise
// once when they first enter the viewport, and [data-parallax] elements drift
// against the scroll. Everything is opacity/transform only, so it composites on
// the GPU and never reflows.
//
// Two rules the rest of the app depends on:
//   - The resting (invisible) state lives behind `html.js` in input.css, so a
//     visitor with scripts blocked gets the finished page, not a blank one.
//   - Under prefers-reduced-motion nothing is observed at all: everything is
//     marked revealed up front and the scroll listener is never attached.
import { debug } from '../env.js';

const REDUCED = '(prefers-reduced-motion: reduce)';

let observer = null;
let parallaxItems = [];
let ticking = false;

function prefersReducedMotion() {
  return typeof window.matchMedia === 'function' && window.matchMedia(REDUCED).matches;
}

function revealAll(root = document) {
  root.querySelectorAll('[data-reveal]').forEach((el) => el.classList.add('is-in'));
}

function onScroll() {
  if (ticking) return;
  ticking = true;
  window.requestAnimationFrame(() => {
    ticking = false;
    const y = window.scrollY || 0;
    for (const { el, rate } of parallaxItems) {
      // Written to `translate`, not `transform`: the reveal transition owns
      // `transform` on the same element, and the two compose instead of one
      // silently winning. Capped so the drift cannot open a gap below it.
      el.style.translate = `0 ${Math.round(Math.min(y * rate, 48))}px`;
    }
  });
}

export function initLanding() {
  if (prefersReducedMotion()) { revealAll(); return; }

  if (!('IntersectionObserver' in window)) { revealAll(); return; }

  observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('is-in');
      observer.unobserve(entry.target); // reveal once; re-entering must not replay
    }
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

  document.querySelectorAll('[data-reveal]').forEach((el) => observer.observe(el));

  parallaxItems = Array.from(document.querySelectorAll('[data-parallax]')).map((el) => ({
    el,
    rate: Number(el.dataset.parallax) || 0.04,
  }));
  if (parallaxItems.length) {
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }
  debug('landing motion ready', { reveals: document.querySelectorAll('[data-reveal]').length, parallax: parallaxItems.length });
}
