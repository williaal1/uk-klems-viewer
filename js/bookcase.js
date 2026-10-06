// The bookcase, in 2D: one shelf per kind of industry, spheres resting on it largest to smallest, left to right,
// each with an emoji and a specimen tag. Drawn as SVG in screen pixels (Common Wealth kit rule: chart text never
// scales), so text stays crisp and readable at any size and the page scrolls natively on phones.
import { openPanel, closePanel, onPanelClose, setPage } from './panel.js';

const SVGNS = 'http://www.w3.org/2000/svg';
const MOBILE = matchMedia('(max-width: 759px)');

// Fixed, in screen pixels.
const TAG_FONT = '400 12px "JetBrains Mono"';
const TAG_H = 22, TAG_PAD_L = 20, TAG_PAD_R = 10, STRING = 10;   // card height, eyelet and right padding, string
const TIE = Math.PI / 4;              // where the string leaves the sphere, from straight up
const GAP = 6;                        // between neighbouring spheres
const PAD = 14;                       // inside each shelf, left and right
const ABOVE = 8;                      // headroom above the highest sphere or tag
const PLANK = 2;                      // shelf line
const LABEL = 30;                     // under the plank, for the shelf's label
const BAY_GAP = 16, ROW_GAP = 12;     // between shelves

const app = document.getElementById('app');
const pane = document.querySelector('.shelves-pane');
const host = document.getElementById('bookcase');
const tip = document.getElementById('tip');

const { meta, industries } = await (await fetch('data/industries.json')).json();
await document.fonts.load(TAG_FONT);
await document.fonts.ready;

const money = (m) => m >= 1e6 ? `$${(m / 1e6).toFixed(2)}tn` : `$${Math.round(m / 1e3).toLocaleString()}bn`;
const vaMax = industries[0].value_added;
const measure = document.createElement('canvas').getContext('2d');
measure.font = TAG_FONT;
const LINE_H = 14;                    // second line of a two-line tag
// A long name can sit on two lines, split at the space nearest its middle (Alex's idea, 2026-10-05).
function split(name) {
  const mid = name.length / 2; let best = -1;
  for (let i = 0; i < name.length; i++) if (name[i] === ' ' && (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))) best = i;
  return best < 0 ? [name] : [name.slice(0, best), name.slice(best + 1)];
}
function setTags(breakAt) {          // names longer than breakAt characters go on two lines
  nodes.forEach((n) => {
    n.tagLines = n.short_name.length > breakAt ? split(n.short_name) : [n.short_name];
    n.tagW = Math.ceil(TAG_PAD_L + Math.max(...n.tagLines.map((t) => measure.measureText(t).width)) + TAG_PAD_R);
    n.tagH = TAG_H + LINE_H * (n.tagLines.length - 1);
  });
}
const nodes = industries.map((d) => ({ ...d, k: Math.sqrt(d.value_added / vaMax) }));
setTags(Infinity);
const shelves = [...new Set(nodes.map((n) => n.sector))].map((sector) => {
  const members = nodes.filter((n) => n.sector === sector);   // already largest first
  return { sector, name: members[0].sector_name, members, va: members.reduce((t, n) => t + n.value_added, 0) };
}).sort((a, b) => b.va - a.va);

// ---------- layout (pixels) ----------
// Sphere area ∝ value added: r = R·sqrt(VA / VA_max). Tags are a fixed, readable size. A shelf that is wider than
// its column wraps onto a further plank (phones); otherwise each shelf is one plank.
const LINE_GAP = 6;                   // between the planks of a wrapped shelf
function arrange(bays, R, angle, maxW = Infinity) {
  const cos = Math.cos(angle), sin = Math.sin(angle);
  shelves.forEach((s) => {
    s.lines = [];
    let line = null;
    s.members.forEach((n) => {
      n.r = Math.max(1.5, R * n.k);
      n.tieDx = n.r * Math.sin(TIE); n.tieDy = n.r + n.r * Math.cos(TIE);        // tie point, from the sphere's foot
      const reach = STRING + n.tagW, tagRight = n.tieDx + reach * cos + n.tagH / 2 * sin;
      const place = (ln) => {
        const prev = ln.members[ln.members.length - 1];
        const lx = prev ? Math.max(ln.x + GAP + n.r, prev.lx + (prev.tagH / 2 + n.tagH / 2 + 6) / sin) : PAD + n.r;   // parallel tags clear each other
        return { lx, right: Math.max(lx + n.r, ln.right, lx + tagRight) };
      };
      let p = line && place(line);
      if (!line || (p.right + PAD > maxW && line.members.length)) {           // start a new plank
        line = { members: [], x: PAD, right: 0, top: 0 }; s.lines.push(line); p = place(line);
      }
      n.lx = p.lx; line.x = n.lx + n.r; line.right = p.right;
      line.top = Math.max(line.top, 2 * n.r, n.tieDy + reach * sin + n.tagH / 2 * cos);
      line.members.push(n); n.line = line;
    });
    s.w = Math.max(...s.lines.map((l) => l.right)) + PAD;
    s.h = s.lines.reduce((t, l) => t + l.top + ABOVE + PLANK, 0) + LINE_GAP * (s.lines.length - 1) + LABEL;
  });
  const cols = [...Array(bays)].map((_, c) => Math.max(0, ...shelves.filter((_, i) => i % bays === c).map((s) => s.w)));
  let y = 0;
  for (let i = 0; i < shelves.length; i += bays) {
    const row = shelves.slice(i, i + bays), h = Math.max(...row.map((s) => s.h));
    row.forEach((s, j) => {
      s.x = cols.slice(0, j).reduce((t, w) => t + w + BAY_GAP, 0); s.y = y; s.cw = cols[j]; s.ch = h;
      let ly = y + h - LABEL - s.lines.reduce((t, l) => t + l.top + ABOVE + PLANK, 0) - LINE_GAP * (s.lines.length - 1);
      s.lines.forEach((l) => {
        ly += l.top + ABOVE; l.base = ly; ly += PLANK + LINE_GAP;              // top of this plank
        l.members.forEach((n) => { n.x = s.x + n.lx; n.y = l.base - n.r; n.base = l.base; });
      });
      s.base = s.lines[s.lines.length - 1].base;
    });
    y += h + ROW_GAP;
  }
  return { W: cols.reduce((t, w) => t + w, 0) + BAY_GAP * (bays - 1), H: y - ROW_GAP };
}

// Largest R for which the arrangement still fits availW (and availH, if given).
function largestR(bays, angle, availW, availH, maxW) {
  let lo = 0, hi = 220;
  for (let k = 0; k < 20; k++) {
    const mid = (lo + hi) / 2, z = arrange(bays, mid, angle, maxW);
    if (z.W <= availW && z.H <= availH) lo = mid; else hi = mid;
  }
  return lo;
}

const ANGLE = Math.PI / 4;
const R_MIN_DESKTOP = 36;             // below this the big industries stop reading as the big ones
const R_MAX_DESKTOP = 46;             // above this the bookcase only gets taller
function solve(availW, availH, mobile) {
  let pick;
  if (mobile) {
    // One column; a shelf wider than the screen wraps onto another plank. Search tag angle, two-line names and
    // sphere size for the fewest planks; then, within 5% of the shortest page, the biggest spheres and shallowest tags.
    const cands = [];
    for (const breakAt of [Infinity, 20]) {
      setTags(breakAt);
      for (const deg of [55, 60, 65, 70, 75]) for (const frac of [0.12, 0.11, 0.10, 0.09, 0.08]) {
        const R = Math.min(frac * availW, 60), angle = deg * Math.PI / 180, z = arrange(1, R, angle, availW);
        cands.push({ bays: 1, R, angle, deg, breakAt, planks: shelves.reduce((t, s) => t + s.lines.length, 0), H: z.H });
      }
    }
    const fewest = Math.min(...cands.map((c) => c.planks));
    const pool = cands.filter((c) => c.planks === fewest);
    const shortest = Math.min(...pool.map((c) => c.H));
    const best = pool.filter((c) => c.H <= 1.05 * shortest)                    // within 5% of the shortest page:
      .reduce((a, c) => (c.R > a.R || (c.R === a.R && c.deg < a.deg) ? c : a)); // the biggest spheres, then the shallowest tags
    setTags(best.breakAt);
    Object.assign(best, arrange(1, best.R, best.angle, availW));
    return best;
  }
  setTags(Infinity);                  // desktop: one-line tags
  // Desktop: fit the whole bookcase on screen if any arrangement can at a decent size; otherwise use the most bays
  // that keep spheres decent (tags at 45°, or 60° if that buys a bay), let the bookcase scroll, size spheres to width.
  const options = [];
  for (const angle of [ANGLE, Math.PI / 3]) for (const bays of [1, 2, 3, 4]) {
    options.push({ bays, angle, fitR: largestR(bays, angle, availW, availH), wideR: Math.min(R_MAX_DESKTOP, largestR(bays, angle, availW, Infinity)) });
  }
  const fits = options.filter((z) => z.fitR >= R_MIN_DESKTOP);
  if (fits.length) { pick = fits.reduce((a, z) => (z.fitR > a.fitR ? z : a)); pick.R = Math.min(pick.fitR, R_MAX_DESKTOP); }
  else {
    const ok = options.filter((z) => z.wideR >= R_MIN_DESKTOP);
    pick = ok.length ? ok.reduce((a, z) => (z.bays > a.bays || (z.bays === a.bays && z.angle < a.angle) ? z : a))
                     : options.reduce((a, z) => (z.wideR > a.wideR ? z : a));
    pick.R = pick.wideR;
  }
  Object.assign(pick, arrange(pick.bays, pick.R, pick.angle));
  return pick;
}

// ---------- drawing ----------
const el = (tag, attrs = {}, parent) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
};
let layoutNow = null, selected = null;

function draw() {
  const mobile = MOBILE.matches;
  const availW = host.clientWidth;
  const availH = mobile ? Infinity : Math.max(320, pane.clientHeight - (host.offsetTop - pane.offsetTop) - pane.querySelector('.source').offsetHeight - 24);
  const L = layoutNow = solve(availW, availH, mobile);
  const deg = -L.angle * 180 / Math.PI, cos = Math.cos(L.angle), sin = Math.sin(L.angle);
  const svg = el('svg', { width: Math.ceil(L.W), height: Math.ceil(L.H), viewBox: `0 0 ${Math.ceil(L.W)} ${Math.ceil(L.H)}`, class: 'cw-chart bookcase', role: 'group' });
  shelves.forEach((s) => {
    el('rect', { x: s.x, y: s.y, width: s.cw, height: s.ch, class: 'shelf-bg' }, svg);
    s.lines.forEach((l) => el('line', { x1: s.x, x2: s.x + s.cw, y1: l.base + PLANK / 2, y2: l.base + PLANK / 2, class: 'plank' }, svg));
    const t = el('text', { x: s.x + PAD, y: s.base + PLANK + 19, class: 'shelf-label' }, svg);
    t.textContent = s.name;
    el('tspan', { class: 'shelf-value', dx: 8 }, t).textContent = money(s.va);
    // tags first, so spheres (and their emoji) sit on top of the strings
    s.members.forEach((n) => {
      const tx = n.x + n.tieDx, ty = n.base - n.tieDy;
      const g = el('g', { class: 'tag', 'data-code': n.code }, svg);
      el('line', { x1: tx, y1: ty, x2: tx + cos * (STRING + 3), y2: ty - sin * (STRING + 3), class: 'string' }, g);
      const card = el('g', { transform: `translate(${tx + cos * STRING} ${ty - sin * STRING}) rotate(${deg})` }, g);
      el('rect', { x: 0, y: -n.tagH / 2, width: n.tagW, height: n.tagH, rx: TAG_H / 2, class: 'card' }, card);
      el('circle', { cx: 10, cy: 0, r: 3, class: 'eyelet' }, card);
      n.tagLines.forEach((t, i) => {
        el('text', { x: TAG_PAD_L, y: 0.5 + (i - (n.tagLines.length - 1) / 2) * LINE_H, class: 'tag-text', 'dominant-baseline': 'middle' }, card).textContent = t;
      });
    });
    s.members.forEach((n) => {
      const g = el('g', { class: 'ind', 'data-code': n.code, tabindex: 0, role: 'button', 'aria-label': `${n.name}, ${money(n.value_added)} value added` }, svg);
      if (selected === n.code) g.classList.add('selected');
      el('circle', { cx: n.x, cy: n.y, r: n.r, class: 'sphere' }, g);
      if (n.r >= 7) el('text', { x: n.x, y: n.y, class: 'emoji', style: `font-size:${(1.05 * n.r).toFixed(1)}px`, 'text-anchor': 'middle', 'dominant-baseline': 'central' }, g).textContent = n.emoji;
    });
  });
  host.replaceChildren(svg);
}

// ---------- interaction ----------
const byCode = new Map(nodes.map((n) => [n.code, n]));
const owner = (e) => e.target.closest?.('[data-code]')?.dataset.code;
host.addEventListener('click', (e) => { const c = owner(e); if (c) select(c); });
host.addEventListener('keydown', (e) => { if ((e.key === 'Enter' || e.key === ' ') && owner(e)) { e.preventDefault(); select(owner(e)); } });
host.addEventListener('pointermove', (e) => {
  const c = e.pointerType === 'mouse' ? owner(e) : null;
  host.querySelectorAll('.ind.hover').forEach((g) => g.classList.remove('hover'));
  if (!c) { tip.hidden = true; return; }
  host.querySelector(`.ind[data-code="${CSS.escape(c)}"]`)?.classList.add('hover');
  const n = byCode.get(c);
  tip.innerHTML = `<div class="cw-tooltip__value">${n.name}</div><div>${n.sector_name}</div><div>${money(n.value_added)} value added · ${(100 * n.value_added / meta.total_value_added).toFixed(1)}%</div>`;
  tip.style.left = `${e.clientX + 14}px`; tip.style.top = `${e.clientY + 14}px`; tip.hidden = false;
});
host.addEventListener('pointerleave', () => { tip.hidden = true; host.querySelectorAll('.ind.hover').forEach((g) => g.classList.remove('hover')); });
addEventListener('keydown', (e) => { if (e.key === 'Escape') closePanel(); });

function select(code) {
  selected = code;
  host.querySelectorAll('.ind').forEach((g) => g.classList.toggle('selected', g.dataset.code === code));
  return openPanel(byCode.get(code), meta).then(() => {
    if (MOBILE.matches) document.getElementById('panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}
onPanelClose(() => {
  selected = null;
  host.querySelectorAll('.ind.selected').forEach((g) => g.classList.remove('selected'));
});

// Redraw whenever the space changes: window size, or the panel opening, closing or changing width.
let queued = false;
new ResizeObserver(() => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; draw(); }); } }).observe(pane);
draw();

// Hooks for the checks in _checks/ (geometry in page pixels, relative to the drawing).
window.__viz = {
  // explore phone layouts: planks and height for a given angle (degrees) and R
  tryLayout: (deg, R, w, breakAt = Infinity) => { setTags(breakAt); const z = arrange(1, R, deg * Math.PI / 180, w); const out = { planks: shelves.reduce((t, s) => t + s.lines.length, 0), H: Math.round(z.H) }; setTags(Infinity); return out; },
  nodes, shelves, meta, setPage, select: (code) => select(code),
  planks: () => shelves.map((s) => s.lines.length),
  layout: () => ({ breakAt: layoutNow.breakAt, planks: shelves.reduce((t, s) => t + s.lines.length, 0), bays: layoutNow.bays, R: layoutNow.R, angle: layoutNow.angle, W: layoutNow.W, H: layoutNow.H, TAG_H, STRING }),
  screenOf: (code) => { const n = byCode.get(code), b = host.querySelector('svg').getBoundingClientRect(); return [b.left + n.x, b.top + n.y]; },
};
