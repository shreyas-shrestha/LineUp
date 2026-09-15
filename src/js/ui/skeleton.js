// Skeleton placeholders for lists and grids. Containers get aria-busy while
// loading so assistive tech knows content is pending.
const widths = [70, 55, 62, 80, 48, 66];

export function skeletonCards(count = 3) {
  return Array.from({ length: count }, (_, i) => `
    <div class="skeleton-card" aria-hidden="true">
      <div class="skeleton skeleton-title" style="width:${widths[i % widths.length]}%"></div>
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text" style="width:${widths[(i + 2) % widths.length]}%"></div>
      <div class="skeleton skeleton-text" style="width:${widths[(i + 4) % widths.length]}%"></div>
    </div>`).join('');
}

export function skeletonRows(count = 4) {
  const rows = Array.from({ length: count }, (_, i) => `<div class="skeleton skeleton-text" style="width:${widths[i % widths.length]}%"></div>`).join('');
  return `<div class="skeleton-rows" aria-hidden="true">${rows}</div>`;
}

export function showSkeleton(container, markup) {
  if (!container) return;
  container.setAttribute('aria-busy', 'true');
  container.innerHTML = markup;
}

export function clearBusy(container) {
  if (container) container.removeAttribute('aria-busy');
}
