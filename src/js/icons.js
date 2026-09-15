// Icons come from the inline Lucide sprite in index.html (<symbol id="i-*">).
// Add new paths to the sprite, not here.
import { raw, escapeHtml } from './dom.js';

const SIZE_CLASS = { sm: 'icon-sm', lg: 'icon-lg' };

// icon('star') -> <svg class="icon" aria-hidden="true"><use href="#i-star"/></svg>
export function icon(name, { size = '', className = '', label = '' } = {}) {
  const classes = ['icon', SIZE_CLASS[size] || '', className].filter(Boolean).join(' ');
  const a11y = label ? `role="img" aria-label="${escapeHtml(label)}"` : 'aria-hidden="true"';
  return raw(`<svg class="${classes}" ${a11y}><use href="#i-${escapeHtml(name)}"/></svg>`);
}
