// Formatting helpers shared by templates. Dates are treated as local calendar
// dates (YYYY-MM-DD) so a booking never shifts by a day across time zones.

export function parseLocalDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ''));
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

export function todayIso() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function formatDate(value, { relative = true } = {}) {
  const date = parseLocalDate(value);
  if (!date) return String(value || '');
  if (relative) {
    const diff = Math.round((startOfDay(date) - startOfDay(new Date())) / 86400000);
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    if (diff === -1) return 'Yesterday';
  }
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', ...(sameYear ? {} : { year: 'numeric' }) });
}

export function formatTime(value) {
  const match = /^(\d{1,2}):(\d{2})/.exec(String(value || ''));
  if (!match) return String(value || '');
  const hours = Number(match[1]);
  const suffix = hours >= 12 ? 'PM' : 'AM';
  return `${hours % 12 || 12}:${match[2]} ${suffix}`;
}

export function appointmentDate(appointment) {
  const date = parseLocalDate(appointment?.date);
  if (!date) return null;
  const match = /^(\d{1,2}):(\d{2})/.exec(String(appointment.time || '12:00'));
  if (match) date.setHours(Number(match[1]), Number(match[2]), 0, 0);
  return date;
}

export function relativeTime(iso) {
  if (!iso) return '';
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return '';
  const seconds = Math.round((Date.now() - then.getTime()) / 1000);
  if (seconds < 45) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function initials(name) {
  const parts = String(name || '').trim().split(/[\s_.-]+/).filter(Boolean);
  if (!parts.length) return '?';
  const first = parts[0][0] || '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] || '' : '';
  return (first + last).toUpperCase();
}

export function money(value) {
  if (value == null || value === '') return '';
  const number = typeof value === 'number' ? value : parseFloat(String(value).replace(/[^0-9.-]/g, ''));
  if (Number.isNaN(number)) return String(value);
  return Number.isInteger(number) ? `$${number}` : `$${number.toFixed(2)}`;
}

export function parsePrice(value) {
  if (typeof value === 'number') return value;
  const number = parseFloat(String(value || '').replace(/[^0-9.-]/g, ''));
  return Number.isNaN(number) ? 0 : number;
}

export function capitalize(value) {
  const text = String(value || '').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : '';
}

export function titleCase(value) {
  return String(value || '').split(/\s+/).filter(Boolean).map(capitalize).join(' ');
}

export function plural(count, singular, pluralForm = `${singular}s`) {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

// Images arrive as URLs, data URLs, or bare base64 strings.
export function imageSrc(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  if (/^(https?:|data:|blob:)/i.test(text)) return text;
  // Bare base64 (a JPEG starts with "/9j/", which would otherwise look like a path).
  if (text.length > 64 && /^[A-Za-z0-9+/=\s]+$/.test(text)) return `data:image/jpeg;base64,${text.replace(/\s+/g, '')}`;
  return text;
}

export function slugify(value) {
  return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'image';
}
