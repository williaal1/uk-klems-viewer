// Common Wealth — read the design tokens from CSS so chart code never hard-codes a colour.
// Usage (ES module):  import { tokens, seriesColors, textOn, contrast } from './cw-tokens.js';
//                     const t = tokens();  t.series1, t.rule, t.fontLabel …
// Values come from css/cw-tokens.css; change them there, never here.

function read(name, el = document.documentElement) {
  return getComputedStyle(el).getPropertyValue(name).trim();
}

export function tokens(el) {
  const r = (n) => read(n, el);
  return {
    bg: r('--color-bg'),
    panel: r('--color-panel'),
    text: r('--color-text'),
    link: r('--color-link'),
    rule: r('--color-rule'),
    grid: r('--color-grid'),
    accent: r('--color-accent'),
    onAccent: r('--color-on-accent'),
    onDark: r('--color-on-dark'),
    highlight: r('--color-highlight'),
    focus: r('--color-focus'),
    series1: r('--series-1'),   // "Your CPI": green 1, draw with strokeSeries1
    series2: r('--series-2'),   // published headline: black
    series3: r('--series-3'),
    series4: r('--series-4'),
    dash3: r('--dash-3'),
    dash4: r('--dash-4'),
    fontHeading: r('--font-heading'),
    fontBody: r('--font-body'),
    fontLabel: r('--font-label'),
    chartSize: parseFloat(r('--size-chart')) * 16,   // px (rem * 16)
    strokeAxis: parseFloat(r('--stroke-axis')),
    strokeGrid: parseFloat(r('--stroke-grid')),
    strokeSeries1: parseFloat(r('--stroke-series-1')),
    strokeSeries: parseFloat(r('--stroke-series')),
    dotRadius: parseFloat(r('--dot-radius')),
  };
}

// Series order. 1 = "Your CPI" (green 1, thick), 2 = published headline (black).
// 3 and 4 are only distinguishable from 2 by dash pattern, not colour (see TRAILHEAD).
export function seriesColors(el) {
  return [1, 2, 3, 4].map((i) => read(`--series-${i}`, el));
}

function lum(hex) {
  const h = hex.replace('#', '');
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

// WCAG 2.x contrast ratio of two #rrggbb colours.
export function contrast(a, b) {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Whichever of the kit's dark text / white text has the higher contrast on a given fill.
export function textOn(fill, el) {
  const t = tokens(el);
  return contrast(fill, t.text) >= contrast(fill, t.onDark) ? t.text : t.onDark;
}
