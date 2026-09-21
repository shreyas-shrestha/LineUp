// Formatting helpers shared by templates.

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
