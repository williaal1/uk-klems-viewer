// The readout: one industry's production function as seven pages (Overview, then K L E M S C),
// from data/readout/<file>.json (the file name comes from industries.json; UK codes contain spaces and "&"). The open page carries over when you click another industry.

const el = document.getElementById('panel');
const cache = new Map();
const PAGES = ['Overview', 'K', 'L', 'E', 'M', 'S', 'C'];
let page = 'Overview';
let current = null;   // { d, meta }

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const MINUS = '\u2212';
const sgn = (x) => (x < 0 ? MINUS : '');
// Money is £ million in the data. Negative values (e.g. imputed rent buying financial services) keep a minus sign.
export const money = (m) => {
  if (m == null || !Number.isFinite(m)) return '–';
  const a = Math.abs(m), s = a < 1e3 && Math.round(a) === 0 ? '' : sgn(m);
  return a >= 1e6 ? `${s}£${(a / 1e6).toFixed(2)}tn` : a >= 1e3 ? `${s}£${(a / 1e3).toFixed(1)}bn` : `${s}£${Math.round(a)}m`;
};
const pct = (x, d = 1) => (x == null || !Number.isFinite(x)) ? '–' : `${sgn(x)}${Math.abs(100 * x).toFixed(d)}%`;
const num = (x) => x == null ? '–' : Math.round(x).toLocaleString('en-GB');
const NP = '<span class="na" title="Not published by ONS (suppressed or unreliable)">n/p</span>';
const wage = (x) => x == null ? NP : `£${Math.round(x / 1000)}k`;
const jobs = (x) => x == null ? NP : num(x);
const codeLabel = (c) => String(c).replace(/(\d)[T_](\d)/, '$1–$2');   // C10T12 -> C10–12
const EMPTY_OCC = 'No published occupation data for this industry.';

const FACTORS = {
  K: ['Capital', 'var(--k)'], L: ['Labour', 'var(--l)'], E: ['Energy', 'var(--e)'],
  M: ['Materials', 'var(--m)'], S: ['Purchased services', 'var(--s)'], C: ['Carbon', 'var(--c)'],
};

function bars(obj, total, color) {
  if (!obj || !(total > 0)) return '';
  const rows = Object.entries(obj).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rows.map((r) => r[1]), 1);
  return `<table class="bars">${rows.map(([k, v]) => `
    <tr><td>${esc(k)}</td><td class="num">${money(v)}</td><td class="num muted">${pct(v / total)}</td>
    <td class="barcell"><i style="width:${Math.max(0, 100 * v / max).toFixed(1)}%;background:${color}"></i></td></tr>`).join('')}</table>`;
}

const src = (text) => `<p class="src">${text}</p>`;
const SRC_PA = 'ONS supply and use tables, Blue Book 2025; 2023, current prices.';

// ---------- pages ----------

function overview(d, meta) {
  const p = d.production, go = p.gross_output, c = d.carbon;
  const stack = 'KLEMS'.split('').map((k) => `<i style="width:${Math.max(0, 100 * p[k] / go).toFixed(2)}%;background:${FACTORS[k][1]}" title="${k}"></i>`).join('');
  const row = (k) => `<tr class="go" data-page="${k}"><td><b class="chip" data-f="${k}">${k}</b>${FACTORS[k][0]}</td>
    <td class="num">${money(p[k])}</td><td class="num muted">${pct(p[k] / go)}</td><td class="num arrow">›</td></tr>`;
  const mt = (t) => `${(t / 1e6).toFixed(t >= 95e3 ? 1 : 2)} Mt`;
  const carbon = c ? `<td class="num">${mt(c.direct_t)}</td><td class="num muted">CO₂e</td>` : `<td class="num muted">not published</td><td class="num muted"></td>`;
  return `
    <div class="kpis">
      <div><span class="muted">Gross output</span><b>${money(go)}</b></div>
      <div><span class="muted">Value added</span><b>${money(p.value_added)}</b></div>
      <div><span class="muted">Share of all value added</span><b>${pct(p.value_added / meta.total_value_added)}</b></div>
    </div>
    <h3>Gross output, by what it pays for</h3>
    <div class="stack">${stack}</div>
    <table class="legend">${'KLEMS'.split('').map(row).join('')}
      <tr class="go" data-page="C"><td><b class="chip" data-f="C">C</b>Carbon (an output)</td>${carbon}<td class="num arrow">›</td></tr>
    </table>
    <p class="note">Value added = K + L. Gross output = K + L + E + M + S. Carbon is produced alongside the output, not paid for.</p>
    ${src(SRC_PA)}
`;
}

function pageK(d) {
  const p = d.production, c = d.capital;
  const byType = bars(p.K_by_type, p.K, 'var(--k)'), byClass = bars(p.K_by_asset_class, p.K, 'var(--k)');
  const html = `
    <h3>Capital income <span class="muted">· ${money(p.K)}, ${pct(p.K / p.gross_output)} of gross output</span></h3>
    ${byType ? `<h4>By type</h4>${byType}` : ''}
    ${byClass ? `<h4>By asset class</h4>${byClass}` : ''}
    ${src(SRC_PA)}`;
  if (!c || !c.broad?.length) return html + `<h3>Capital stock</h3><p class="note">No published capital stock data for this industry.</p>`;
  const total = c.broad.find((b) => b.level === 0) || c.broad[0];
  const row = (b) => `<tr class="lv${b.level}"><td class="lv${b.level}">${esc(b.asset)}</td><td class="num">${money(b.net_stock_m)}</td>
    <td class="num">${money(b.gross_stock_m)}</td><td class="num">${money(b.investment_m)}</td><td class="num">${pct(b.depreciation_rate)}</td></tr>`;
  return html + `
    <h3>Capital stock <span class="muted">· ${money(total.net_stock_m)} net stock</span></h3>
    <p class="scope">Figures for: ${esc(c.basis_name)}${c.basis_code ? ` (${esc(codeLabel(c.basis_code))})` : ''}</p>
    <table class="grid wide"><thead><tr><th></th><th>Net stock</th><th>Gross stock</th><th>Investment</th><th>Depreciation rate</th></tr></thead>
      <tbody>${c.broad.map(row).join('')}</tbody></table>
    ${src('ONS capital stocks, November 2025 (net and gross stock; depreciation = consumption of fixed capital / net stock); ONS gross fixed capital formation by industry and asset (investment). 2023, current prices.')}`;
}

function pageL(d) {
  const p = d.production, l = d.labor;
  const edu = bars(p.L_by_education, p.L, 'var(--l)');
  const html = `
    <h3>Labour compensation <span class="muted">· ${money(p.L)}, ${pct(p.L / p.gross_output)} of gross output</span></h3>
    ${edu ? `<h4>By education</h4>${edu}` : ''}
    ${src(`${SRC_PA} Education split: ONS CALI pay shares.`)}`;
  if (!l) return html + `<h3>Occupations</h3><p class="note">${EMPTY_OCC}</p>`;
  const basis = l.ashe_basis_name != null;
  const TOP = 15;
  const side = (title, s) => !s || !s.occupations?.length ? `
    <div class="side"><h4>${title}</h4><p class="note">${EMPTY_OCC}</p></div>` : `
    <div class="side">
      <h4>${title}</h4>
      <div class="side-sum"><b>${jobs(s.employment)}</b> jobs · mean ${wage(s.mean_wage)}</div>
      <table class="grid occ collapsible collapsed"><thead><tr><th>Occupation</th><th>Jobs</th><th>Mean annual pay</th></tr></thead>
        <tbody>${s.occupations.map((o, i) => `<tr class="${i >= TOP ? 'more' : ''}"><td>${esc(o.title)}</td><td class="num">${jobs(o.employment)}</td><td class="num">${wage(o.mean_wage)}</td></tr>`).join('')}</tbody></table>
      ${s.occupations.length > TOP ? `<button class="toggle" data-n="${s.occupations.length}" data-top="${TOP}">Show all ${s.occupations.length}</button>` : ''}
    </div>`;
  const none = !l.supervisory?.occupations?.length && !l.nonsupervisory?.occupations?.length;
  return html + `
    <h3>Pay and jobs</h3>
    ${basis ? `<p class="scope">Pay and jobs: ${esc(l.ashe_basis_name)}</p>` : ''}
    <div class="gap">
      <div><span class="muted">Jobs</span><b>${num(l.total_jobs)}</b></div>
      <div><span class="muted">Mean annual pay</span><b>${l.mean_annual_pay == null ? '–' : wage(l.mean_annual_pay)}</b></div>
      <div><span class="muted">ASHE wage bill</span><b>${money(l.ashe_wage_bill_m)}</b></div>
      <div><span class="muted">Compensation of employees</span><b>${basis ? money(l.compensation_of_employees_basis_m) : '–'}</b></div>
      <div><span class="muted">Wages cover</span><b>${basis ? pct(l.ashe_wage_bill_m / l.compensation_of_employees_basis_m, 0) : '–'}</b></div>
    </div>
    <h3>Occupations</h3>
    ${l.occupation_basis_section ? `<p class="scope">Occupations: SIC section ${esc(l.occupation_basis_section)} (all industries in the section)</p>` : ''}
    ${none ? `<p class="note">${EMPTY_OCC}</p>` : `<div class="sides">${side('Supervisory', l.supervisory)}${side('Nonsupervisory', l.nonsupervisory)}</div>`}
    ${src('ONS ASHE 2023 (revised), Table 4 (pay and jobs by industry) and Table 29 (occupation by industry section); SOC 2020 groups, annual gross pay.')}`;
}

function pageEMS(d, k) {
  const p = d.production, pu = d.purchases?.[k];
  const spent = pu ? pu.listed_total : p[k], listed = spent;
  const ii = p.E + p.M + p.S;
  let g = 0;   // running group id, so a group row can open its own items
  const rows = (pu ? pu.sectors : []).map((sec) => `
    <tr class="band"><td>${esc(sec.name)}</td><td class="num">${money(sec.value)}</td><td class="num muted">${pct(sec.value / listed)}</td></tr>
    ${sec.groups.map((grp) => {
      const id = g++, open = grp.items.length > 1;
      return `<tr class="grp${open ? ' can-open' : ''}" data-g="${id}"><td>${esc(grp.name)}</td><td class="num">${money(grp.value)}</td><td class="num muted">${pct(grp.value / listed)}</td></tr>
        ${open ? grp.items.map(([name, v]) => `<tr class="item" data-of="${id}" hidden><td>${esc(name)}</td><td class="num">${money(v)}</td><td class="num muted">${pct(v / listed)}</td></tr>`).join('') : ''}`;
    }).join('')}`).join('');
  return `
    <h3>${FACTORS[k][0]} <span class="muted">· bought from other industries</span></h3>
    <div class="kpis">
      <div><span class="muted">Spent</span><b>${money(spent)}</b></div>
      <div><span class="muted">Share of gross output</span><b>${pct(spent / p.gross_output)}</b></div>
      <div><span class="muted">Share of intermediate inputs</span><b>${pct(spent / ii)}</b></div>
    </div>
    <table class="grid ems"><thead><tr><th>What it buys, by kind of industry that makes it</th><th>£</th><th>Share</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="3" class="muted">None listed.</td></tr>'}</tbody></table>
    ${src("ONS supply and use tables, Blue Book 2025: intermediate use at purchasers' prices, 2023, by product.")}`;
}

const tonnes = (t) => t == null ? '–' : t >= 1e6 ? `${(t / 1e6).toFixed(1)} Mt` : t >= 1e3 ? `${Math.round(t / 1e3).toLocaleString('en-GB')} kt` : `${Math.round(t)} t`;
const GASES = ['Carbon dioxide', 'Methane', 'Nitrous oxide', 'Fluorinated gases'];
const kg = (v) => v == null ? '–' : `${v < 0.1 ? v.toFixed(3) : v.toFixed(2)} kg`;

function pageC(d) {
  const c = d.carbon;
  if (!c) return `<h3>Carbon <span class="muted">· an output, produced alongside the industry's goods and services</span></h3>
    <p class="note">ONS does not publish emissions for this industry.</p>`;
  const gases = Object.fromEntries(GASES.map((g) => [g, c.by_gas_t?.[g] || 0]));
  const gmax = Math.max(...Object.values(gases), 1);
  return `
    <h3>Carbon <span class="muted">· an output, produced alongside the industry's goods and services</span></h3>
    <div class="kpis">
      <div><span class="muted">Direct emissions</span><b>${tonnes(c.direct_t)} CO₂e</b></div>
      <div><span class="muted">Share of all industry emissions</span><b>${pct(c.share_of_industry_total)}</b></div>
      <div><span class="muted">Per £ of output</span><b>${kg(c.direct_kg_per_gbp)}</b></div>
    </div>
    <h4>By gas <span class="muted">· CO₂-equivalent</span></h4>
    <table class="bars">${GASES.map((g) => `<tr><td>${g}</td><td class="num">${tonnes(gases[g])}</td><td class="num muted">${pct(c.direct_t ? gases[g] / c.direct_t : null)}</td>
      <td class="barcell"><i style="width:${(100 * gases[g] / gmax).toFixed(1)}%;background:var(--c)"></i></td></tr>`).join('')}</table>
    ${src('ONS environmental accounts: greenhouse gas emissions by industry, 2023, residence basis, direct emissions.')}`;
}

function render() {
  const { d, meta } = current;
  const body = page === 'Overview' ? overview(d, meta) : page === 'K' ? pageK(d) : page === 'L' ? pageL(d) : page === 'C' ? pageC(d) : pageEMS(d, page);
  el.innerHTML = `
    <header>
      <button class="close" aria-label="Close">×</button>
      <h2>${esc(d.name)}</h2>
      <div class="muted">ONS ${esc(d.code)} · SIC ${esc(d.sic_codes)} · ${d.year}</div>
      <nav class="tabs" role="tablist">${PAGES.map((t) => `<button role="tab" data-page="${t}" aria-selected="${t === page}">${t}</button>`).join('')}</nav>
    </header>
    <div class="page">${body}</div>`;
  el.querySelector('.close').onclick = () => closePanel();
  el.querySelectorAll('[data-page]').forEach((b) => b.onclick = () => go(b.dataset.page));
  el.querySelectorAll('tr.grp.can-open').forEach((tr) => tr.onclick = () => {
    const open = tr.classList.toggle('open');
    el.querySelectorAll(`tr.item[data-of="${tr.dataset.g}"]`).forEach((r) => { r.hidden = !open; });
  });
  el.querySelectorAll('.toggle').forEach((b) => b.onclick = () => {
    const t = b.previousElementSibling;
    t.classList.toggle('collapsed');
    b.textContent = t.classList.contains('collapsed') ? `Show all ${b.dataset.n}` : `Show top ${b.dataset.top}`;
  });
}

function go(p) { page = p; if (!current) return; render(); el.scrollTop = 0; }

export async function openPanel(node, meta) {
  const key = node.file;   // fetch by file name: UK codes contain spaces and "&"
  if (!cache.has(key)) cache.set(key, fetch(`data/readout/${encodeURIComponent(key)}.json`).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }));
  try { current = { d: await cache.get(key), meta }; } catch (err) {
    cache.delete(key);
    el.innerHTML = `<header><button class="close" aria-label="Close">×</button><h2>${esc(node.name)}</h2><p class="note">Could not load this readout (${esc(err.message)}).</p></header>`;
    el.hidden = false;
    el.querySelector('.close').onclick = () => closePanel();
    return;
  }
  el.hidden = false;
  render();
  el.scrollTop = 0;
}

// ← / → step through the pages while the panel is open.
addEventListener('keydown', (e) => {
  if (el.hidden || !current || !['ArrowLeft', 'ArrowRight'].includes(e.key)) return;
  const i = PAGES.indexOf(page) + (e.key === 'ArrowRight' ? 1 : -1);
  go(PAGES[(i + PAGES.length) % PAGES.length]);
});

export const setPage = (p) => go(p);
let onClose = () => {};
export function onPanelClose(fn) { onClose = fn; }
export function closePanel() {
  el.hidden = true; current = null; onClose();
  if (matchMedia('(max-width: 759px)').matches) scrollTo({ top: 0, behavior: 'smooth' });   // back up to the shelves
}
