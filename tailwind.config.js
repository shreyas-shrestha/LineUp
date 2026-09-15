/** @type {import('tailwindcss').Config} */
// Design tokens v2 ("glass on black") live in src/input.css as CSS custom
// properties and are mirrored here so Tailwind utilities (bg-surface-2,
// text-text-2, border-border, ...) match. Change both when you change one.
const tokens = {
  bg: '#000000',
  'surface-1': '#0A0A0A',
  'surface-2': '#121212',
  'surface-3': '#1A1A1A',
  'glass-1': 'rgba(255,255,255,0.04)',
  'glass-2': 'rgba(255,255,255,0.07)',
  'glass-3': 'rgba(255,255,255,0.10)',
  border: 'rgba(255,255,255,0.10)',
  'border-strong': 'rgba(255,255,255,0.14)',
  'border-hover': 'rgba(255,255,255,0.18)',
  'text-1': '#EDEDED',
  'text-2': '#A1A1A1',
  'text-3': '#6B6B6B',
  accent: '#3291FF',
  'on-accent': '#04101F',
  'accent-subtle': 'rgba(50,145,255,0.14)',
  success: '#3FB950',
  'success-subtle': 'rgba(63,185,80,0.12)',
  warning: '#D29922',
  'warning-subtle': 'rgba(210,153,34,0.12)',
  danger: '#F85149',
  'danger-text': '#F85149',
  'danger-subtle': 'rgba(248,81,73,0.12)',
  star: '#E3B341',
};

module.exports = {
  content: ['./index.html', './src/**/*.js'],
  // Component classes defined in @layer components are only emitted when a
  // scanned file uses them. JS templates build class names dynamically in a
  // few places (chip-${status}), so keep them all available.
  safelist: require('./src/safelist.js'),
  theme: {
    extend: {
      colors: {
        ...tokens,
      },
      fontFamily: {
        sans: ['Geist', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        display: ['Geist', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      maxWidth: {
        content: '960px',
        reading: '640px',
        landing: '1120px',
      },
      boxShadow: {
        elevated: '0 24px 64px rgba(0,0,0,0.6)',
        soft: '0 8px 24px rgba(0,0,0,0.45)',
        highlight: 'inset 0 1px 0 rgba(255,255,255,0.06)',
      },
      transitionDuration: {
        fast: '160ms',
        enter: '220ms',
        exit: '120ms',
      },
    },
    // Radius scale is 6 / 8 / 12 / 16 / full.
    borderRadius: {
      none: '0',
      sm: '6px',
      DEFAULT: '8px',
      md: '8px',
      lg: '12px',
      xl: '16px',
      '2xl': '16px',
      '3xl': '16px',
      full: '9999px',
    },
  },
  plugins: [],
};
