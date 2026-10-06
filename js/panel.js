// The readout: one industry's production function as seven pages (Overview, then K L E M S C),
// from data/readout/<code>.json. The open page carries over when you click another industry.

const el = document.getElementById('panel');
const cache = new Map();
const PAGES = ['Overview', 'K', 'L', 'E', 'M', 'S', 'C'];
let page = 'Overview';
let current = null;   // { d, meta }

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const money = (m) => m == null ? '–' : Math.abs(m) >= 1e6 ? `$${(m / 1e6).toFixed(2)}tn` : Math.abs(m) >= 1e3 ? `$${(m / 1e3).toFixed(1)}bn` : `$${Math.round(m)}m`;
const pct = (x, d = 1) => x == null ? '–' : `${(100 * x).toFixed(d)}%`;
const num = (x) => x == null ? '–' : Math.round(x).toLocaleString();
const wage = (x) => x == null ? '<span class="na" title="Not published: suppressed or top-coded by OEWS">n/p</span>' : `$${Math.round(x / 1000)}k`;

const FACTORS = {
  K: ['Capital', 'var(--k)'], L: ['Labor', 'var(--l)'], E: ['Energy', 'var(--e)'],
  M: ['Materials', 'var(--m)'], S: ['Purchased services', 'var(--s)'], C: ['Carbon', 'var(--c)'],
};

function bars(obj, total, color) {
  const rows = Object.entries(obj).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...rows.map((r) => r[1]), 1);
  return `<table class="bars">${rows.map(([k, v]) => `
    <tr><td>${esc(k)}</td><td class="num">${money(v)}</td><td class="num muted">${pct(v / total)}</td>
    <td class="barcell"><i style="width:${(100 * v / max).toFixed(1)}%;background:${color}"></i></td></tr>`).join('')}</table>`;
}

const SRC_PA = (d) => `<p class="src">BEA-BLS Integrated Production Account, ${d.year}, current dollars.</p>`;

// ---------- pages ----------

function overview(d, meta) {
  const p = d.production, go = p.gross_output;
  const stack = 'KLEMS'.split('').map((k) => `<i style="width:${(100 * p[k] / go).toFixed(2)}%;background:${FACTORS[k][1]}" title="${k}"></i>`).join('');
  const row = (k) => `<tr class="go" data-page="${k}"><td><b class="chip" data-f="${k}">${k}</b>${FACTORS[k][0]}</td>
    <td class="num">${money(p[k])}</td><td class="num muted">${pct(p[k] / go)}</td><td class="num arrow">›</td></tr>`;
  return `
    <div class="kpis">
      <div><span class="muted">Gross output</span><b>${money(go)}</b></div>
      <div><span class="muted">Value added</span><b>${money(p.value_added)}</b></div>
      <div><span class="muted">Share of all value added</span><b>${pct(p.value_added / meta.total_value_added)}</b></div>
    </div>
    <h3>Gross output, by what it pays for</h3>
    <div class="stack">${stack}</div>
    <table class="legend">${'KLEMS'.split('').map(row).join('')}
      <tr class="go" data-page="C"><td><b class="chip" data-f="C">C</b>Carbon (an output)</td><td class="num">${(d.carbon.direct_t / 1e6).toFixed(1)} Mt</td><td class="num muted">CO₂e</td><td class="num arrow">›</td></tr>
    </table>
    <p class="note">Value added = K + L. Gross output = K + L + E + M + S. Carbon is produced alongside the output, not paid for.</p>
    ${SRC_PA(d)}
`;
}

function pageK(d) {
  const p = d.production, c = d.capital;
  const html = `
    <h3>Capital income <span class="muted">· ${money(p.K)}, ${pct(p.K / p.gross_output)} of gross output</span></h3>
    <h4>By type</h4>${bars(p.K_by_type, p.K, 'var(--k)')}
    <h4>By asset class</h4>${bars(p.K_by_asset_class, p.K, 'var(--k)')}
    ${SRC_PA(d)}`;
  if (!c) return html + `<h3>Capital stock</h3><p class="note">No asset-level capital data for this industry.</p>`;
  const order = ['Equipment', 'Structures', 'Intellectual property products', 'Rental residential capital', 'Inventories', 'Land'];
  const broad = order.map((a) => c.broad.find((b) => b.asset === a)).filter(Boolean);
  const all = c.broad.find((b) => b.asset === 'All assets');
  const bn = (x) => money(x == null ? null : x * 1e3);
  const brow = (b, cls = '') => `<tr class="${cls}"><td>${esc(b.asset)}</td><td class="num">${bn(b.productive_stock_bn)}</td>
    <td class="num">${bn(b.investment_bn)}</td><td class="num">${pct(b.depreciation_rate)}</td>
    <td class="num">${pct(b.share_of_capital_income)}</td></tr>`;
  const sub = (rows, total) => `<table class="grid sub"><thead><tr><th></th><th>Stock</th><th>Investment</th><th>Depreciation</th></tr></thead>${rows.filter((b) => b.asset !== total).map((b) => `
    <tr><td>${esc(b.asset)}</td><td class="num">${bn(b.productive_stock_bn)}</td><td class="num">${bn(b.investment_bn)}</td><td class="num">${pct(b.depreciation_rate)}</td></tr>`).join('')}</table>`;
  const max = c.assets[0]?.productive_stock_m || 1;
  const arow = (a, i) => `<tr class="${i >= 10 ? 'more' : ''}"><td>${esc(a.asset)}<span class="bar"><i style="width:${(100 * a.productive_stock_m / max).toFixed(1)}%"></i></span></td>
    <td class="num">${money(a.productive_stock_m)}</td><td class="num">${money(a.investment_m)}</td><td class="num">${pct(a.depreciation_rate)}</td><td class="num">${pct(a.share_of_capital_income)}</td></tr>`;
  return html + `
    <h3>Capital stock <span class="muted">· ${bn(all.productive_stock_bn)} productive stock</span></h3>
    <table class="grid wide"><thead><tr><th></th><th>Stock</th><th>Investment</th><th>Depreciation</th><th>Share of K income</th></tr></thead>
      <tbody>${broad.map((b) => brow(b)).join('')}${brow(all, 'total')}</tbody></table>
    <h4>Information processing equipment</h4>${sub(c.information_processing, 'Total information processing equipment')}
    <h4>Intellectual property</h4>${sub(c.intellectual_property, 'Total intellectual property products')}
    <h4>Every asset type <span class="muted">· ${c.assets.length}, largest stock first</span></h4>
    <table class="grid wide collapsible collapsed"><thead><tr><th></th><th>Stock</th><th>Investment</th><th>Depreciation</th><th>Share of K income</th></tr></thead>
      <tbody>${c.assets.map(arow).join('')}</tbody></table>
    ${c.assets.length > 10 ? `<button class="toggle" data-n="${c.assets.length}" data-top="10">Show all ${c.assets.length}</button>` : ''}
    <p class="src">BLS Total Factor Productivity, Capital Details, ${d.year}.</p>`;
}

function pageL(d) {
  const p = d.production, l = d.labor;
  const html = `
    <h3>Labor compensation <span class="muted">· ${money(p.L)}, ${pct(p.L / p.gross_output)} of gross output</span></h3>
    <h4>By education</h4>${bars(p.L_by_education, p.L, 'var(--l)')}
    ${SRC_PA(d)}`;
  if (!l) return html + `<h3>Occupations</h3><p class="note">No occupation data for this industry.</p>`;
  const TOP = 15;
  const side = (title, s) => `
    <div class="side">
      <h4>${title}</h4>
      <div class="side-sum"><b>${num(s.employment)}</b> jobs · mean ${wage(s.mean_wage)}</div>
      <table class="grid occ collapsible collapsed"><thead><tr><th>Occupation</th><th>Jobs</th><th>Mean wage</th></tr></thead>
        <tbody>${s.occupations.map((o, i) => `<tr class="${i >= TOP ? 'more' : ''}"><td>${esc(o.title)}</td><td class="num">${num(o.employment)}</td><td class="num">${wage(o.mean_wage)}</td></tr>`).join('')}</tbody></table>
      ${s.occupations.length > TOP ? `<button class="toggle" data-n="${s.occupations.length}" data-top="${TOP}">Show all ${s.occupations.length}</button>` : ''}
    </div>`;
  return html + `
    <h3>Occupations <span class="muted">· ${num(l.total_employment)} jobs · mean wage ${wage(l.mean_wage)}</span></h3>
    <div class="gap">
      <div><span class="muted">OEWS wage bill</span><b>${money(l.oews_wage_bill_m)}</b></div>
      <div><span class="muted">KLEMS labor compensation</span><b>${money(l.klems_labor_compensation_m)}</b></div>
      <div><span class="muted">Wages cover</span><b>${pct(l.oews_wage_bill_m / l.klems_labor_compensation_m, 0)}</b></div>
    </div>
    <div class="sides">${side('Supervisory', l.supervisory)}${side('Nonsupervisory', l.nonsupervisory)}</div>
    <p class="src">BLS OEWS, May ${d.year}, national industry-specific estimates.</p>`;
}

function pageEMS(d, k) {
  const p = d.production, ii = p.E + p.M + p.S, pu = d.purchases[k];
  const listed = pu ? pu.listed_total : 0;
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
      <div><span class="muted">Spent</span><b>${money(p[k])}</b></div>
      <div><span class="muted">Share of gross output</span><b>${pct(p[k] / p.gross_output)}</b></div>
      <div><span class="muted">Share of intermediate inputs</span><b>${pct(p[k] / ii)}</b></div>
    </div>
    <table class="grid ems"><thead><tr><th>What it buys, by kind of industry that makes it</th><th>$</th><th>Share</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="3" class="muted">None listed.</td></tr>'}</tbody></table>
    <p class="src">BEA Use table, 2017 detail benchmark (before redefinitions, purchasers' prices). Click a group to see its detailed commodities.</p>`;
}

const tonnes = (t) => t == null ? '–' : t >= 1e6 ? `${(t / 1e6).toFixed(1)} Mt` : t >= 1e3 ? `${Math.round(t / 1e3).toLocaleString()} kt` : `${Math.round(t)} t`;
const GASES = ['Carbon dioxide', 'Methane', 'Nitrous oxide', 'Fluorinated gases'];
const kg = (v) => `${v < 0.1 ? v.toFixed(3) : v.toFixed(2)} kg`;

function pageC(d) {
  const c = d.carbon;
  const gases = Object.fromEntries(GASES.map((g) => [g, c.by_gas_t[g] || 0]));
  const max = Math.max(c.direct_kg_per_usd, c.supply_chain_kg_per_usd);
  const per = (label, v) => `<tr><td>${label}</td><td class="num">${kg(v)}</td>
    <td class="barcell"><i style="width:${(100 * v / max).toFixed(1)}%;background:var(--c)"></i></td></tr>`;
  const upstream = 1 - c.direct_kg_per_usd / c.supply_chain_kg_per_usd;
  return `
    <h3>Carbon <span class="muted">· an output, produced alongside the industry's goods and services</span></h3>
    <div class="kpis">
      <div><span class="muted">Direct emissions</span><b>${tonnes(c.direct_t)} CO₂e</b></div>
      <div><span class="muted">Share of all industry emissions</span><b>${pct(c.share_of_industry_total)}</b></div>
      <div><span class="muted">Per dollar of output</span><b>${kg(c.direct_kg_per_usd)}</b></div>
    </div>
    <h4>By gas <span class="muted">· CO₂-equivalent</span></h4>
    <table class="bars">${GASES.map((g) => `<tr><td>${g}</td><td class="num">${tonnes(gases[g])}</td><td class="num muted">${pct(c.direct_t ? gases[g] / c.direct_t : null)}</td>
      <td class="barcell"><i style="width:${(100 * gases[g] / Math.max(...Object.values(gases), 1)).toFixed(1)}%;background:var(--c)"></i></td></tr>`).join('')}</table>
    <h4>Per dollar of output <span class="muted">· kg CO₂e</span></h4>
    <table class="bars">${per('Direct, in the industry itself', c.direct_kg_per_usd)}${per('Including its supply chain', c.supply_chain_kg_per_usd)}</table>
    <p class="note">${pct(upstream, 0)} of the emissions behind a dollar of this industry's output happen upstream, in the industries it buys from (at home and abroad).</p>
    <p class="src">EPA USEEIO v2.5 (model kingbird-17): 2017 greenhouse-gas emissions, IPCC AR6 100-year warming potentials.</p>`;
}

function render() {
  const { d, meta } = current;
  const body = page === 'Overview' ? overview(d, meta) : page === 'K' ? pageK(d) : page === 'L' ? pageL(d) : page === 'C' ? pageC(d) : pageEMS(d, page);
  el.innerHTML = `
    <header>
      <button class="close" aria-label="Close">×</button>
      <h2>${esc(d.name)}</h2>
      <div class="muted">BEA ${esc(d.code)}${d.naics_2017 ? ` · NAICS ${esc(d.naics_2017)}` : ''} · ${d.year}</div>
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
  if (!cache.has(node.code)) cache.set(node.code, fetch(`data/readout/${encodeURIComponent(node.code)}.json`).then((r) => r.json()));
  try { current = { d: await cache.get(node.code), meta }; } catch (err) {
    cache.delete(node.code);
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
