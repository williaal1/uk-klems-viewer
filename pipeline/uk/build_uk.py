"""Build the UK viewer's data: data/industries.json and data/readout/<file>.json, 2023, Blue Book 2025 vintage.

    uv run --with pandas --with pyarrow python pipeline/uk/build_uk.py

The UK twin of pipeline/build_industries.py + pipeline/build_readout.py (US). Written by Claude, 2026-10-06, following
the design in the UK repo's NOTES.md, "Stage 2: UK data backend" (design and defaults chosen by Claude under Alex's
sign-off; each is his to overturn).

Industries: the 104 industries of the ONS supply-use tables. Everything is 2023, GBP million, current prices.

Sources (all Data Sources library modules, read-only; each module's TRAILHEAD "Before you aggregate" was read first):
  - Economics/National Accounts/Foreign Statistical Agencies/ONS (UK)/uk-supply-use-tables  (BB25; data/uk_sut_bb25.csv,
    table use_intermediate, col_type detail): gross output (P1), compensation of employees (D1), gross operating surplus
    and mixed income (GOS & MI), taxes less subsidies on production (D29-D39), GVA, intermediate use product x industry
    at purchasers' prices.
  - .../ONS (UK)/uk-labour-share  (Table_6, 2023, labour share of income by SIC section; the back-solve recipe in its TRAILHEAD)
  - Economics/Production/Foreign Statistical Agencies/ONS (UK)/uk-labour-composition  (CALI pay shares, 10 industry groups x HQ1-HQ6)
  - .../ONS (UK)/uk-capital-stocks  (workbook: gross/net stock, 13 assets x industry codes, in_sum_set; CAPSTK: CFC)
  - .../ONS (UK)/uk-gfcf-industry-asset  (GFCF by industry x asset, 2023, BB25)
  - Economics/Employment/Foreign Statistical Agencies/ONS (UK)/uk-ashe-industry-occupation  (2023 revised, All employees:
    Table 4 by SIC division, Table 29 by SIC section x SOC 2020 sub-major group; annual gross pay)
  - Environmental/Emissions and Resource Use/Foreign Statistical Agencies/ONS (UK)/uk-env-accounts-ghg  (2023, residence
    basis, SIC groups x gas, kt CO2e)
Labels: pipeline/uk/industries_uk.csv, short_names_uk.csv, emoji_uk.csv (Claude drafts, not yet reviewed by Alex).
Mappings from the 104 SUT industries to each source's own industry codes: pipeline/uk/map_*.csv (judgement calls, with a
basis and note column; this script asserts that all 104 are mapped).

Method notes (also written into each readout's `notes`):
  L = D1 + labour share x mixed income.  Section mixed income is back-solved (GOS = D1 x (100 / labour share - 1);
  mixed income = GOS & MI - GOS), then spread to the section's industries pro rata to their GOS & MI (an assumption).
  K = GVA - L, so K includes taxes less subsidies on production; VA = K + L exactly.
  E / M / S: 2023 intermediate use sorted by product (rule in NOTES.md item 5, mirroring the US rule).

Checks are fatal unless marked "reported"; both numbers are printed for every check.
"""
import json, os, re, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
YEAR = 2023

def find_library():
    p = ROOT
    while True:
        cand = os.path.join(p, 'Data Sources')
        if os.path.isdir(cand):
            return cand
        q = os.path.dirname(p)
        assert q != p, 'Data Sources/ not found above ' + ROOT
        p = q
LIB = find_library()
NA = os.path.join(LIB, 'Economics', 'National Accounts', 'Foreign Statistical Agencies', 'ONS (UK)')
SUT = os.path.join(NA, 'uk-supply-use-tables', 'data', 'uk_sut_bb25.csv')
LSHARE = os.path.join(NA, 'uk-labour-share', 'data', 'uk_labour_costs_labour_share_aug2026.csv')
CAPW = os.path.join(NA, 'uk-capital-stocks', 'data', 'uk_capstock_industry_asset_bb25.csv')
CAPS = os.path.join(NA, 'uk-capital-stocks', 'data', 'uk_capstock_timeseries_bb25.csv')
CAPD = os.path.join(NA, 'uk-capital-stocks', 'data', 'uk_capstock_dimensions.csv')
GFCF = os.path.join(NA, 'uk-gfcf-industry-asset', 'data', 'uk_gfcf_industry_asset_bb25.csv')
CALI = os.path.join(LIB, 'Economics', 'Production', 'Foreign Statistical Agencies', 'ONS (UK)', 'uk-labour-composition', 'data', 'uk_cali_underlying_we2024q4.csv')
ASHE = os.path.join(LIB, 'Economics', 'Employment', 'Foreign Statistical Agencies', 'ONS (UK)', 'uk-ashe-industry-occupation', 'data')
GHG = os.path.join(LIB, 'Environmental', 'Emissions and Resource Use', 'Foreign Statistical Agencies', 'ONS (UK)', 'uk-env-accounts-ghg', 'data', 'uk_ghg_by_industry_gas.csv')
OUT = os.path.join(ROOT, 'data', 'readout')

# Published totals the checks compare against (2023, GBP million). Sources: SUT module TRAILHEAD (GVA, GO equal the IOAT's;
# D1 equals Blue Book 2025 table 1.2 HAEA); uk-labour-share TRAILHEAD verification table (Blue Book 2025 table 1.2: GOS ABNF
# 971,499 and mixed income QWLT 169,885); uk-capital-stocks TRAILHEAD (net stock 5,545,956; CFC 409,299);
# uk-ashe TRAILHEAD (27,645 thousand jobs weekly, 22,783 annual); uk-env-accounts-ghg TRAILHEAD (479,716 kt incl. households).
PUB = dict(gva=2497390, d1=1329778, go=4819806, gos=971499, mi=169885, net_stock=5545956, cfc=409299,
           jobs_weekly=27645, jobs_annual=22783, ghg_all=479716, ghg_households=121958)

SECTORS = {'11': 'Agriculture, forestry & fishing', '21': 'Mining', '22': 'Utilities', '23': 'Construction',
           '31ND': 'Nondurable manufacturing', '33DG': 'Durable manufacturing', '42': 'Wholesale trade', '44RT': 'Retail trade',
           '48TW': 'Transportation & warehousing', '51': 'Information', 'FIRE': 'Finance, insurance & real estate',
           'PROF': 'Professional & business services', '6': 'Education & health care', '7': 'Arts, recreation, lodging & food',
           '81': 'Other services', 'G': 'Government'}

CHECKS = []
def check(name, actual, expected, tol, fatal=True, note=''):
    ok = abs(actual - expected) <= tol
    line = f'{"PASS" if ok else ("FAIL" if fatal else "NOTE")}  {name}: {actual:,.2f} vs {expected:,.2f} (diff {actual - expected:+,.2f}, band {tol:g}) {note}'.rstrip()
    print(line)
    CHECKS.append(line)
    if fatal and not ok:
        sys.exit('CHECK FAILED: ' + line)

def fileify(code):
    return re.sub(r'[^A-Za-z0-9._-]', '_', code)

def num(v):
    return None if v is None or (isinstance(v, float) and v != v) or pd.isna(v) else float(v)

def clean(v):
    if isinstance(v, dict): return {k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [clean(x) for x in v]
    if isinstance(v, (np.floating, float)): return None if v != v else float(v)
    if isinstance(v, np.integer): return int(v)
    return v

# ------------------------------------------------------------------ labels and maps
lab = pd.read_csv(os.path.join(HERE, 'industries_uk.csv'), dtype=str).fillna('').set_index('code')
short = pd.read_csv(os.path.join(HERE, 'short_names_uk.csv'), dtype=str).set_index('code').short_name
emoji = pd.read_csv(os.path.join(HERE, 'emoji_uk.csv'), dtype=str).set_index('code').emoji
m_cap = pd.read_csv(os.path.join(HERE, 'map_capital.csv'), dtype=str).fillna('').set_index('code')
m_lab = pd.read_csv(os.path.join(HERE, 'map_labour.csv'), dtype=str).fillna('').set_index('code')
m_em = pd.read_csv(os.path.join(HERE, 'map_emissions.csv'), dtype=str).fillna('').set_index('code')
m_prod = pd.read_csv(os.path.join(HERE, 'map_product_industry.csv'), dtype=str).set_index('product_code')

# ------------------------------------------------------------------ supply-use tables
sut = pd.read_csv(SUT, low_memory=False)
sut = sut[(sut.year == YEAR) & (sut.table == 'use_intermediate')]
det = sut[sut.col_type == 'detail']
codes = sorted(det.col_code.unique())
assert len(codes) == 104, f'expected 104 SUT industries, got {len(codes)}'
for name, idx in [('industries_uk.csv', lab.index), ('short_names_uk.csv', short.index), ('emoji_uk.csv', emoji.index),
                  ('map_capital.csv', m_cap.index), ('map_labour.csv', m_lab.index), ('map_emissions.csv', m_em.index)]:
    assert set(idx) == set(codes) and len(idx) == 104, f'{name}: codes differ from the SUT: {set(idx) ^ set(codes)}'
assert sorted(m_prod.index) == sorted(det[det.row_type == 'product'].row_code.unique()) and set(m_prod.industry_code) == set(codes), 'map_product_industry.csv incomplete'
desc = det.drop_duplicates('col_code').set_index('col_code').col_desc
assert all(lab.loc[c, 'ons_description'] == desc[c] for c in codes), 'industries_uk.csv descriptions differ from the SUT'
print(f'PASS  104 industries; codes match the SUT exactly in all label and map files')

va = det[det.row_type == 'value_added'].pivot_table(index='col_code', columns='row_code', values='value', aggfunc='sum')
tot = det[det.row_type == 'total'].pivot_table(index='col_code', columns='row_code', values='value', aggfunc='sum')
x = pd.concat([va, tot], axis=1).loc[codes]
prod = det[det.row_type == 'product'].assign(value=lambda d: d.value.fillna(0))   # one blank cell in the source (A02 x C235_6): read as zero (SUT trailhead trap 10)
use = prod.pivot_table(index='row_code', columns='col_code', values='value', aggfunc='sum')
II = use.sum(axis=0).loc[codes]
x['II'] = II
assert (x['II'] - x['_T']).abs().max() <= 0.5, 'product rows do not sum to the published intermediate-use total'
assert (x['D1'] + x['GOS & MI'] + x['D29-D39'] - x['GVA']).abs().max() <= 0.5, 'D1 + GOS&MI + taxes != GVA'
assert (x['II'] + x['GVA'] - x['P1']).abs().max() <= 0.5, 'II + GVA != P1'
check('sum GVA (BB25)', x.GVA.sum(), PUB['gva'], 0.5)
check('sum D1 compensation of employees (BB25)', x.D1.sum(), PUB['d1'], 0.5)
check('sum gross output P1 (BB25)', x.P1.sum(), PUB['go'], 0.5)

# ------------------------------------------------------------------ labour, capital K, mixed income
ls = pd.read_csv(LSHARE, dtype={'industry_code': str})
ls = ls[(ls.table == 'Table_6') & (ls.year == YEAR) & (ls.industry_level == 'section')].set_index('industry_code').value / 100.0
assert len(ls) == 20
x['section'] = [c[0] for c in x.index]
sec = x.groupby('section')[['D1', 'GOS & MI']].sum()
sec['ls'] = ls
sec['GOS'] = sec.D1 * (1 / sec.ls - 1)
sec['MI'] = sec['GOS & MI'] - sec.GOS
check('mixed-income back-solve: sum of section GOS vs Blue Book GOS', sec.GOS.sum(), PUB['gos'], 50)
check('mixed-income back-solve: sum of section mixed income vs Blue Book mixed income', sec.MI.sum(), PUB['mi'], 50)
assert sec.MI.min() > -1, f'negative section mixed income: {sec.MI.min()}'
x['MI'] = [sec.MI[s] * g / sec['GOS & MI'][s] if sec['GOS & MI'][s] else 0.0 for s, g in zip(x.section, x['GOS & MI'])]
x['lab_mi'] = [m * ls[s] for m, s in zip(x.MI, x.section)]
x['L'] = x.D1 + x.lab_mi
x['K'] = x.GVA - x.L
x['E_M_S'] = x.II
anom = x[(x.MI < -0.5) | (x.MI > x['GOS & MI'].clip(lower=0) + 0.5)]
print(f'NOTE  industries whose pro-rata mixed income falls outside [0, GOS&MI]: {list(anom.index) or "none"} (reported)')
print(f'NOTE  industries with negative K = GVA - L: {[(c, round(v)) for c, v in x.K[x.K < 0].items()] or "none"} (reported)')

# ------------------------------------------------------------------ purchases: E / M / S
FUEL = {'CPA_B05', 'CPA_B06 & B07', 'CPA_C19', 'CPA_D351', 'CPA_D352_3'}
FEED_IND = {'C19', 'C20A', 'C20B', 'C20C', 'C203', 'C204', 'C205'}
def ems_class(p, ind):
    if p in FUEL:
        if p in ('CPA_B06 & B07', 'CPA_C19') and ind in FEED_IND: return 'M'      # crude/refined bought by refining and chemicals: feedstock
        if p == 'CPA_B06 & B07' and ind == 'B06 & B07': return 'M'                # oil and gas bought by oil and gas extraction: own use
        return 'E'
    return 'M' if p[4] in 'ABC' else 'S'                                           # other goods -> materials; everything else -> services
pl = prod[prod.value != 0].copy()
pl['f'] = [ems_class(p, i) for p, i in zip(pl.row_code, pl.col_code)]
pl['sector'] = pl.row_code.map(lambda p: lab.loc[m_prod.loc[p, 'industry_code'], 'sector_key'])
assert pl.sector.isin(SECTORS).all()
emsum = pl.groupby(['col_code', 'f']).value.sum().unstack(fill_value=0).reindex(codes).fillna(0)
for f in 'EMS':
    x[f] = emsum[f] if f in emsum else 0.0
assert (x.E + x.M + x.S - x.II).abs().max() <= 0.5
assert (x.GVA - x.K - x.L).abs().max() <= 0.001
go_gap = (x.P1 - (x.K + x.L + x.E + x.M + x.S)).abs()
assert go_gap.max() <= 1, f'GO != K+L+E+M+S, worst {go_gap.idxmax()} {go_gap.max()}'
print(f'PASS  per industry: VA = K + L (max gap {(x.GVA - x.K - x.L).abs().max():.6f}); GO = K+L+E+M+S (max gap {go_gap.max():.6f}); E+M+S = SUT intermediate use (max gap {(x.E + x.M + x.S - x.II).abs().max():.6f}); all within GBP 1m')
CHECKS.append('per industry: VA = K + L, GO = K + L + E + M + S, E + M + S = SUT intermediate use, all within GBP 1m')
tE, tM, tS = x.E.sum(), x.M.sum(), x.S.sum()
print(f'NOTE  E/M/S totals (reported): E {tE:,.0f} ({tE / x.II.sum():.1%}), M {tM:,.0f} ({tM / x.II.sum():.1%}), S {tS:,.0f} ({tS / x.II.sum():.1%}) of {x.II.sum():,.0f}; spine hunt (same rule) E 261,534 / M 714,964 / S 1,345,918')

def purchases(code):
    g = pl[pl.col_code == code]
    out = {}
    for f, gf in g.groupby('f'):
        sectors = []
        for s, gs in gf.groupby('sector'):
            groups = [{'name': r.row_desc.strip(), 'value': round(float(r.value), 1), 'items': []}
                      for r in gs.sort_values('value', ascending=False).itertuples()]
            sectors.append({'name': SECTORS[s], 'value': round(float(gs.value.sum()), 1), 'groups': groups})
        sectors.sort(key=lambda d: -d['value'])
        out[f] = {'listed_total': round(float(gf.value.sum()), 1), 'sectors': sectors}
    return out

# ------------------------------------------------------------------ capital
dim = pd.read_csv(CAPD, dtype=str)
ind_label = dim[(dim.dim_table == 'industry_asset_workbook') & (dim.dimension == 'industry')].set_index('code').label
cap = pd.read_csv(CAPW, dtype={'industry_code': str})
cap = cap[(cap.year == YEAR) & (cap.price_basis == 'current_prices')]
stock = {m: cap[cap.measure == m].pivot_table(index='industry_code', columns='asset_code', values='value', aggfunc='first', dropna=False)
         for m in ('net_stock', 'gross_stock')}
sumset = cap[cap.in_sum_set].industry_code.unique()
bases = set(m_cap.stock_code)
assert bases <= set(sumset), f'stock bases outside in_sum_set: {bases - set(sumset)}'
unused = set(sumset) - bases
net_n11 = stock['net_stock'].loc[sorted(bases), 'N11'].sum()
check('capital: net stock, sum of de-duplicated in_sum_set bases (asset N11) vs ONS total', net_n11, PUB['net_stock'], 0.5, note=f'(bases unused: {sorted(unused)}, all z or zero)')
assert all(cap[(cap.industry_code == u) & (cap.measure == 'net_stock') & (cap.asset_code == 'N11')].value.isna().all() for u in unused)

ASSETS = [  # code, name, level, GFCF sheet, CFC spec (CAPSTK asset codes; None = not published by industry)
    ('N11', 'Total fixed assets', 0, 'Total_assets', ['total']),
    ('N111', 'Dwellings (excluding land)', 1, 'Dwellings', ['dwellings']),
    ('N112', 'Other buildings and structures', 1, 'Buildings_and_transfer_costs', ['land_improvements', 'other_buildings', 'other_structures']),
    ('N11M', 'Machinery, equipment and weapons systems', 1, 'Machinery_and_equipment', ['plant', 'transport']),
    ('N1131', 'Transport equipment', 2, 'Transport', ['transport']),
    ('N1132', 'ICT equipment', 2, 'ICT', None),
    ('N11321', 'Computer hardware', 3, 'Hardware', None),
    ('N11322', 'Telecommunications equipment', 3, 'Telecoms', None),
    ('N11O', 'Other machinery, equipment and weapons systems', 2, 'Other_machinery_and_equipment', None),
    ('N115', 'Cultivated biological resources', 1, 'Cultivated_assets', ['cultivated']),
    ('N117', 'Intellectual property products', 1, 'Intellectual_property_products', ['ipp']),
    ('N1171', 'Research and development', 2, 'Research_and_development', ['rnd']),
    ('N1173', 'Computer software and databases', 2, 'Software', ['software']),
]
# CFC from CAPSTK (S.1, current prices, GBP m); series ONS flags with a documented defect are dropped (null), never corrected.
cs = pd.read_csv(CAPS, dtype=str)
cs['year'] = cs.year.astype(int); cs['value'] = pd.to_numeric(cs.value)
cs = cs[(cs.year == YEAR) & (cs.measure == 'cfc') & (cs.price_basis == 'CP') & (cs.sector_code == 'S.1') & (cs.is_duplicate == 'FALSE')]
assert (cs.unit == '£m').all()
n_flag = int(cs.series_issue.notna().sum())
cfc = cs[cs.series_issue.isna()].pivot_table(index='industry_code', columns='asset_code', values='value', aggfunc='first')
cfc_leaf = sorted(set(m_cap.capstk_code))
check('capital: CFC total assets, sum of the CAPSTK leaf industries used vs ONS total industry', cfc.loc[cfc_leaf, 'total'].sum(), PUB['cfc'], 5, fatal=False)
print(f'NOTE  CAPSTK CFC series dropped for a documented defect (reported): {n_flag}')
cap_group = m_cap.groupby('capstk_code').stock_code.apply(lambda s: sorted(set(s)))   # bases inside each CAPSTK industry

def cfc_value(capstk_code, spec):
    if spec is None or capstk_code not in cfc.index: return None
    vals = [num(cfc.loc[capstk_code].get(a)) for a in spec]
    if len(spec) == 1: return vals[0]
    if spec == ['plant', 'transport']: return None if any(v is None for v in vals) else sum(vals)
    present = [v for v in vals if v is not None]          # N112: land improvements + other buildings + other structures; an absent series is "none"
    return sum(present) if present else None

g = pd.read_csv(GFCF, dtype={'industry_code': str})
g = g[(g.year == YEAR) & (g.price_basis == 'current_prices')]
gf = {(r.asset_code, r.industry_code): (num(r.value), r.flag) for r in g.itertuples()}
gsheets = {a: set(g[g.asset_code == a].industry_code) for a in g.asset_code.unique()}
check('capital: GFCF total (Total_assets, TOTAL) vs SUT Table 4 total', gf[('Total_assets', 'TOTAL')][0], 520091, 0.5)

def investment(sheet, gcode):
    if not gcode: return None
    if gcode not in gsheets[sheet]:
        return 0.0 if sheet in ('Dwellings', 'Cultivated_assets') else None      # asset sheets list only the industries that have the asset: absent = none
    v, flag = gf[(sheet, gcode)]
    return v                                                                     # None when ONS suppresses the cell ([c])

def names_of(codes_):
    return ', '.join(short[c] for c in codes_)

def capital(code):
    r = m_cap.loc[code]
    sc, cc, gc = r.stock_code, r.capstk_code, r.gfcf_code
    exact_cfc = len(cap_group[cc]) == 1
    others = [c for c in m_cap.index[m_cap.stock_code == sc] if c != code]
    broad = []
    for ac, an, lvl, sheet, spec in ASSETS:
        net = num(stock['net_stock'].loc[sc].get(ac)); gross = num(stock['gross_stock'].loc[sc].get(ac))
        inv = investment(sheet, gc)
        cf = cfc_value(cc, spec) if exact_cfc else None
        if exact_cfc:
            rate = cf / net if cf is not None and net else None
        else:
            gcf = cfc_value(cc, spec)
            gnet = [num(stock['net_stock'].loc[b].get(ac)) for b in cap_group[cc]]
            gnet = sum(v for v in gnet if v is not None) if any(v is not None for v in gnet) else None
            rate = gcf / gnet if gcf is not None and gnet else None
        if net is None and gross is None and cf is None and rate is None and not inv: continue   # nothing published (investment 0 = the asset sheet lists no such industry)
        broad.append({'asset': an, 'asset_code': ac, 'level': lvl, 'net_stock_m': net, 'gross_stock_m': gross, 'investment_m': inv,
                      'cfc_m': cf, 'depreciation_rate': rate})
    # basis note
    sbl = ind_label[sc].split(': ', 1)[-1]
    sbl = sbl.capitalize() if sbl.isupper() else sbl
    if r.stock_basis == 'same':
        note = f'Stocks are ONS industry {sc} ({sbl}), which is this industry.'
    else:
        note = (f'Stocks, investment and depreciation are for ONS industry {sc} ({sbl}), a wider group that this industry shares with '
                f'{names_of(others)}; the figures are for the whole group, not this industry alone.')
    if gc == '':
        note += ' ONS publishes no investment (GFCF) for this industry.'
    else:
        note += f' Investment is ONS GFCF industry "{gc}"' + (', which also covers other UK industries in this viewer.' if r.gfcf_basis == 'shared' else '.')
    if not exact_cfc:
        note += (f' Depreciation published only for CAPSTK industry {cc} ({", ".join(cap_group[cc])}); the rate shown is that group\'s '
                 f'depreciation divided by the group\'s net stock, and no depreciation amount is shown for this industry.')
    if r.note and not (gc == '' and 'no column for SIC 97' in r.note): note += ' ' + r.note + '.'
    return {'basis_code': sc, 'basis_name': sbl.capitalize() if sbl.isupper() else sbl, 'basis_note': note, 'broad': broad}, exact_cfc

# ------------------------------------------------------------------ labour: ASHE and CALI
th = pd.read_parquet(os.path.join(ASHE, 'ashe_table4_industry.parquet'))
th = th[(th.year == YEAR) & (th.edition == 'revised') & (th.employee_group == 'All') & (th.measure == 'annual_pay_gross')]
t4 = {s: th[th.statistic == s].set_index('industry_code') for s in ('jobs', 'mean')}
t4name = th.drop_duplicates('industry_code').set_index('industry_code').industry_name
t29 = pd.read_parquet(os.path.join(ASHE, 'ashe_table29_industry_occupation.parquet'))
t29 = t29[(t29.year == YEAR) & (t29.edition == 'revised') & (t29.employee_group == 'All') & (t29.measure == 'annual_pay_gross')]
t29w = pd.read_parquet(os.path.join(ASHE, 'ashe_table29_industry_occupation.parquet'))
t29w = t29w[(t29w.year == YEAR) & (t29w.edition == 'revised') & (t29w.employee_group == 'All') & (t29w.measure == 'weekly_pay_gross')]
allocc = t29[(t29.occupation_level == 'all') & (t29.statistic == 'jobs')].set_index('industry_code').value
allocc_w = t29w[(t29w.occupation_level == 'all') & (t29w.statistic == 'jobs')].set_index('industry_code').value
check('ASHE (weekly pay, Table 29): sum of section jobs (thousand) vs published all employees', allocc_w.sum(), PUB['jobs_weekly'], 0.5)
check('ASHE (annual pay, Table 29): sum of section jobs (thousand) vs Table 4 all employees', allocc.sum(), PUB['jobs_annual'], 15, note='(sections U and NC are suppressed in the annual table)')
ALL_INDUSTRIES_ANNUAL = float(t4['jobs'].loc['ALL_INDUSTRIES', 'value'])
sub = t29[(t29.occupation_level == 'sub_major')]
occ_jobs = sub[sub.statistic == 'jobs'].set_index(['industry_code', 'occupation_code'])
occ_mean = sub[sub.statistic == 'mean'].set_index(['industry_code', 'occupation_code'])
OCC_ORDER = list(sub.drop_duplicates('occupation_code').occupation_code)
OCC_TITLE = sub.drop_duplicates('occupation_code').set_index('occupation_code').occupation_name
SUPERVISORY = {'11', '12'}                                              # SOC 2020 major group 1 sub-major groups

def ashe_header(code):
    r = m_lab.loc[code]
    divs = r.ashe_t4_divisions.split('+')
    jobs = [num(t4['jobs'].value.get(d)) for d in divs]
    mean = [num(t4['mean'].value.get(d)) for d in divs]
    names = [str(t4name.get(d, d)) for d in divs]
    have_all_jobs = all(j is not None for j in jobs)
    tj = sum(jobs) * 1000 if have_all_jobs else None
    mp = (sum(j * m for j, m in zip(jobs, mean)) / sum(jobs)) if have_all_jobs and all(m is not None for m in mean) and sum(jobs) > 0 else None
    # a division with a mean but no jobs count (ONS suppresses the count): the mean is real, the weight is unknown
    if mp is None and len(divs) == 1 and mean[0] is not None: mp = mean[0]
    return divs, names, tj, mp

def occupations(code):
    s = m_lab.loc[code].t29_section
    rows = []
    for oc in OCC_ORDER:
        j = num(occ_jobs.value.get((s, oc))); m = num(occ_mean.value.get((s, oc))); cv = num(occ_mean.cv.get((s, oc))) if m is not None else None
        rows.append({'code': oc, 'title': str(OCC_TITLE[oc]), 'employment': None if j is None else j * 1000, 'mean_wage': m, 'cv': cv})
    def side(rs):
        rs = sorted(rs, key=lambda d: (d['employment'] is None, -(d['employment'] or 0)))
        w = [r for r in rs if r['employment'] and r['mean_wage'] is not None]
        emp = [r['employment'] for r in rs if r['employment'] is not None]
        return {'employment': sum(emp) if emp else None,
                'mean_wage': (sum(r['employment'] * r['mean_wage'] for r in w) / sum(r['employment'] for r in w)) if w else None,
                'occupations': rs}
    sup = [r for r in rows if r['code'] in SUPERVISORY]; non = [r for r in rows if r['code'] not in SUPERVISORY]
    vis = sum(r['employment'] for r in rows if r['employment'] is not None)
    tot = allocc.get(s)
    cover = (vis / 1000 / tot) if tot and tot == tot else None
    nvis = sum(1 for r in rows if r['employment'] is not None)
    return side(sup), side(non), cover, nvis

cali = pd.read_csv(CALI)
cali = cali[cali.year == YEAR]
grp = cali.groupby('industry_group').pay_share.sum()
col = cali[cali.qualification.isin(['HQ5', 'HQ6'])].groupby('industry_group').pay_share.sum() / grp
check('CALI: pay shares over all 360 cells sum to 1', cali.pay_share.sum(), 1.0, 1e-9)
CALI_GROUP_DESC = cali.drop_duplicates('industry_group').set_index('industry_group').industry_group_desc

# ------------------------------------------------------------------ carbon
ghg = pd.read_csv(GHG, dtype={'sic_group_code': str})
ghg = ghg[ghg.year == YEAR]
gg = ghg[(ghg.level == 'group') & (ghg.row_role == 'industry')]
gtot = gg[gg.gas == 'GHG_total'].set_index('sic_group_code')
gname = gtot.industry_name
gas = {k: gg[gg.gas == k].set_index('sic_group_code').value_kt_co2e for k in ('CO2', 'CH4', 'N2O', 'HFC', 'PFC', 'SF6', 'NF3')}
used = [c for s_ in m_em.group_codes for c in s_.split('|') if c]
assert sorted(used) == sorted(gtot.index), f'emission groups: used vs ONS differ: {set(used) ^ set(gtot.index)}'
assert len(used) == len(set(used)) == 129, 'every ONS industry group must be used exactly once (no apportioning needed)'
sec_ghg = ghg[(ghg.level == 'section') & (ghg.row_role == 'industry') & (ghg.gas == 'GHG_total')].value_kt_co2e.sum()
hh = ghg[(ghg.level == 'section') & (ghg.row_role == 'consumer_expenditure') & (ghg.gas == 'GHG_total')].value_kt_co2e.sum()
tot_all = ghg[(ghg.level == 'section') & (ghg.row_role == 'total') & (ghg.gas == 'GHG_total')].value_kt_co2e.sum()
check('emissions: industry sections + households vs ONS total, 2023 (kt CO2e)', sec_ghg + hh, tot_all, 5, note='(21 cells each rounded to a whole kt)')
check('emissions: ONS total vs module TRAILHEAD figure (kt CO2e, includes households)', tot_all, PUB['ghg_all'], 0.5)
check('emissions: households vs module TRAILHEAD figure (kt CO2e)', hh, PUB['ghg_households'], 0.5)
SUPPRESSED = set(m_em.index[m_em.basis == 'suppressed'])

def carbon(code):
    r = m_em.loc[code]; go = x.P1[code]
    gcodes = [c for c in r.group_codes.split('|') if c]
    if r.basis == 'suppressed':
        return None
    kt = float(sum(gtot.value_kt_co2e[c] for c in gcodes)) if gcodes else 0.0
    def gsum(keys):
        return float(sum(num(gas[k].get(c)) or 0.0 for k in keys for c in gcodes)) * 1000
    by = {'Carbon dioxide': gsum(['CO2']), 'Methane': gsum(['CH4']), 'Nitrous oxide': gsum(['N2O']), 'Fluorinated gases': gsum(['HFC', 'PFC', 'SF6', 'NF3'])}
    if r.basis == 'none':
        note = r.note + '.'
        bc, bn = None, None
    else:
        bc = ' + '.join(gcodes); bn = '; '.join(str(gname[c]) for c in gcodes)
        note = (f'ONS industry group(s) {bc} cover this industry exactly (no apportioning). 2023, residence basis, direct (scope 1) emissions only, '
                f'IPCC AR5 weights; households\' own emissions are not in any industry. Fluorinated gases are the published HFC, PFC, SF6 and NF3 cells '
                f'([low] cells are blank in the source, so this can be slightly short).')
    return {'basis_code': bc, 'basis_name': bn, 'direct_t': kt * 1000, 'share_of_industry_total': kt / sec_ghg,
            'by_gas_t': by, 'direct_kg_per_gbp': kt * 1000 * 1000 / (go * 1e6), 'supply_chain_kg_per_gbp': None, 'basis_note': note}, sum(by.values()) / 1000 - kt

# ------------------------------------------------------------------ build
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith('.json'): os.remove(os.path.join(OUT, f))
files = {c: fileify(c) + '.json' for c in codes}
assert len(set(files.values())) == 104 and len({v.lower() for v in files.values()}) == 104, 'readout file names collide'

industries, summary = [], []
gas_gaps, carbon_total, cfc_exact, carbon_by_code = [], 0.0, 0, {}
ashe_cov = []
for code in x.sort_values('GVA', ascending=False).index:
    r = x.loc[code]
    L = lab.loc[code]; ml = m_lab.loc[code]; mc = m_cap.loc[code]
    industries.append({'code': code, 'file': files[code][:-5], 'name': L.ons_description, 'short_name': short[code], 'emoji': emoji[code],
                       'sic_codes': L.sic_codes, 'sector': L.sector_key, 'sector_name': SECTORS[L.sector_key], 'value_added': float(r.GVA)})
    notes = []
    s = r.section
    notes.append(f'Labour (L) = compensation of employees (D1, GBP {r.D1:,.0f}m) plus GBP {r.lab_mi:,.0f}m of the industry\'s mixed income (the self-employed\'s income): '
                 f'section {s}\'s labour share of income ({ls[s]:.1%}, uk-labour-share) times mixed income of GBP {r.MI:,.0f}m. Mixed income by section is back-solved '
                 f'(GOS = D1 x (1 / labour share - 1); mixed income = GOS & MI - GOS) and spread over the section\'s industries pro rata to their gross operating surplus '
                 f'and mixed income. That spread is an assumption (Claude, 2026-10-06). Capital (K) = gross value added - L, so K includes taxes less subsidies on production (GBP {r.get("D29-D39"):,.0f}m).')
    notes.append('Energy, materials and services (E, M, S) sort this industry\'s 2023 intermediate use at purchasers\' prices by product: energy = coal, crude oil and gas & metal ores (B06 & B07), refined petroleum, electricity, gas and steam; '
                 'crude and refined products bought by refining and chemicals, and oil and gas bought by oil and gas extraction, count as materials; all other goods (CPA sections A, B, C) are materials; everything else is services. '
                 'This is Claude\'s rule, not an ONS or BEA classification; no UK published E/M/S exists to compare with. Weak spots: B06 & B07 mixes oil and gas with metal ores; D352_3 includes steam and air conditioning; B09 mining support and C33 repair services count as goods.')
    cp, exact_cfc = capital(code)
    cp = cp if cp['broad'] else None
    cfc_exact += exact_cfc
    if cp:
        if mc.stock_basis != 'same': notes.append(f'Capital: stock, investment and depreciation figures are for the wider ONS group {mc.stock_code}, shared with other industries (see the capital basis note).')
    # labour
    divs, dnames, tj, mp = ashe_header(code)
    wb = tj * mp / 1e6 if tj is not None and mp is not None else None
    sup, non, cover, nvis = occupations(code)
    basis_kind = ml.ashe_basis
    if basis_kind == 'none':
        ab_code, ab_name = None, None
        ab_note = 'ASHE Table 4 has no row for this industry'
    else:
        ab_code, ab_name = '+'.join(divs), ' + '.join(dnames)
    basis_comp = float(x.D1[[c for c in m_lab.index if m_lab.ashe_t4_divisions[c] == ml.ashe_t4_divisions]].sum())
    labor = {'ashe_basis_code': ab_code, 'ashe_basis_name': ab_name, 'total_jobs': tj, 'mean_annual_pay': mp, 'ashe_wage_bill_m': wb,
             'compensation_of_employees_m': float(r.D1), 'compensation_of_employees_basis_m': basis_comp,
             'occupation_basis_section': s, 'supervisory': sup, 'nonsupervisory': non}
    if basis_kind == 'none':
        labor.update({'total_jobs': None, 'mean_annual_pay': None, 'ashe_wage_bill_m': None})
    notes.append(f'Labour figures are ASHE 2023 revised, all employees, gross annual pay (tax year to April 2023, employees in the same job for the whole year; this covers {PUB["jobs_annual"]:,} thousand jobs against {PUB["jobs_weekly"]:,} thousand in the April pay-period tables). '
                 f'Jobs are rounded to the thousand and are indicative, not headcount. The ASHE wage bill (jobs x mean annual pay) is a sample-based figure that runs well below national-accounts compensation of employees, so the two are not expected to match.')
    if basis_kind in ('shared', 'partial'):
        notes.append(f'Labour header: ASHE division {ml.ashe_t4_divisions} ({ab_name}) is wider than this industry or only part of it; compensation of employees for all UK industries on that basis is GBP {basis_comp:,.0f}m (compensation_of_employees_basis_m), the fair comparison for the ASHE wage bill. ' + (ml.note + '.' if ml.note else ''))
    elif ml.note:
        notes.append('Labour header: ' + ml.note + '.')
    notes.append(f'Occupation tables are for the whole SIC section {s}, not for this industry alone (ASHE Table 29 has sections only): {nvis} of {len(OCC_ORDER)} two-digit occupation groups are published, covering {cover:.0%} of the section\'s annual-pay jobs. '
                 'Withheld cells (CV above 20%, or disclosive) are null, never zero, so occupation totals on the page are lower bounds. Supervisory = SOC 2020 major group 1 (sub-major groups 11 and 12); nonsupervisory = all other sub-major groups.' if cover is not None else
                 f'Occupation tables are for the whole SIC section {s}; no ASHE jobs count is published for it, so the cells are null.')
    ashe_cov.append((code, cover))
    # education
    if code == 'L68A':
        notes.append('Owner-occupiers\' imputed rent is household operating surplus, but the pro rata spread of section L mixed income above still gives this industry GBP %s m of mixed income (a side effect of the assumption; the alternative is to leave it out and give the section\'s mixed income to the other two real-estate industries).' % f'{r.MI:,.0f}')
    cg = ml.cali_group
    cshare = float(col[cg])
    L_edu = {'College': float(r.L * cshare), 'Non-college': float(r.L * (1 - cshare))}
    notes.append(f'College / non-college split uses ONS CALI pay shares for the industry group {cg} ({CALI_GROUP_DESC[cg]}), 2023: degree or higher (qualification levels HQ5 + HQ6) = {cshare:.1%} of the group\'s pay; HQ4 (higher education below degree) counts as non-college. '
                 'Applied to this industry\'s L as an assumption that every industry in the group has the group\'s mix.')
    carb = carbon(code)
    if carb is None:
        notes.append('Carbon: ONS withholds this industry\'s 2023 emissions (low reliability) and says they must not be derived from other data, so none is shown.')
        carbon_block = None
    else:
        carbon_block, gap = carb
        gas_gaps.append(gap); carbon_total += carbon_block['direct_t'] / 1000; carbon_by_code[code] = carbon_block['direct_t'] / 1000
        notes.append('Carbon: ' + carbon_block['basis_note'])
    prod_block = {'gross_output': float(r.P1), 'value_added': float(r.GVA), 'K': float(r.K), 'L': float(r.L), 'E': float(r.E), 'M': float(r.M), 'S': float(r.S),
                  'compensation_of_employees': float(r.D1), 'labour_mixed_income': float(r.lab_mi), 'taxes_on_production': float(r['D29-D39']),
                  'K_by_type': None, 'K_by_asset_class': None, 'L_by_education': L_edu, 'cali_group': cg}
    out = {'code': code, 'name': L.ons_description, 'sic_codes': L.sic_codes, 'year': YEAR, 'currency': 'GBP', 'notes': notes,
           'production': prod_block, 'capital': cp, 'labor': labor, 'purchases': purchases(code), 'carbon': carbon_block}
    with open(os.path.join(OUT, files[code]), 'w', encoding='utf-8') as fh:
        json.dump(clean(out), fh, separators=(',', ':'), allow_nan=False, ensure_ascii=False)

# ------------------------------------------------------------------ whole-build checks
print(f'NOTE  CFC: {cfc_exact} industries have CAPSTK CFC at their own coverage (cfc_m shown); {104 - cfc_exact} use their CAPSTK group\'s rate (reported)')
visible_groups_kt = float(gtot.value_kt_co2e.sum())          # TRAILHEAD: 357,081 kt visible groups; section total 357,757; gap 677 = the three suppressed groups
check(f'emissions: direct emissions summed over the {len(carbon_by_code)} readouts with a value vs the ONS visible-group total (kt CO2e)', carbon_total, visible_groups_kt, 0.5)
print(f'NOTE  suppressed groups 14, 31, 36 (null carbon): ONS section total {sec_ghg:,.0f} - visible groups {visible_groups_kt:,.0f} = {sec_ghg - visible_groups_kt:,.0f} kt; module TRAILHEAD documents 677 kt (reported)')
vis_sec = ghg[(ghg.level == 'section') & (ghg.row_role == 'industry') & (ghg.gas == 'GHG_total')].set_index('sic_section').value_kt_co2e
by_sec = pd.Series(carbon_by_code).groupby(lambda c: c[0]).sum()
for sct in vis_sec.index:
    d_ = vis_sec[sct] - by_sec.get(sct, 0.0)
    if sct in ('C', 'E'):
        print(f'NOTE  section {sct}: ONS {vis_sec[sct]:,.0f} kt, readouts {by_sec.get(sct, 0.0):,.1f} kt, gap {d_:,.1f} kt = suppressed groups (reported)')
    else:
        assert abs(d_) <= 5, f'section {sct}: readouts {by_sec.get(sct, 0.0)} vs ONS {vis_sec[sct]}'
print('PASS  every other section: readouts sum to the ONS section total within 5 kt (ONS rounding bound)')
CHECKS.append('emissions: readouts sum to ONS section totals within 5 kt except sections C and E (suppressed groups 14, 31, 36)')
print(f'NOTE  readout carbon: max |sum of gas cells - GHG_total| per industry = {max(abs(g_) for g_ in gas_gaps):.2f} kt (rounding: totals are whole kt, gases 0.1 kt; reported)')
mx = max(abs(g_) for g_ in gas_gaps)
assert mx < 2.0, f'gas cells differ from GHG_total by {mx} kt'
cov = pd.DataFrame(ashe_cov, columns=['code', 'cover']).dropna()
print(f'NOTE  ASHE occupation coverage (share of the section\'s annual jobs in published cells): min {cov.cover.min():.0%}, median {cov.cover.median():.0%}, max {cov.cover.max():.0%} (reported); annual coverage over the whole table {sub[(sub.statistic == "jobs")].value.sum() / allocc.sum():.1%}')
tj_unique = {}
for c in codes:
    d = m_lab.ashe_t4_divisions[c]
    divs_, _, tj_, _ = ashe_header(c)
    if m_lab.ashe_basis[c] != 'none': tj_unique[d] = tj_
visible = sum(v for v in tj_unique.values() if v is not None) / 1000
check('ASHE Table 4 (annual): jobs summed over distinct mapped divisions vs ALL_INDUSTRIES (thousand)', visible, ALL_INDUSTRIES_ANNUAL, 130, fatal=False,
      note=f'(reported; gap = divisions ONS does not publish or withholds: {sorted(d for d, v in tj_unique.items() if v is None)} and divisions 05, 07, 12, 99)')

meta = {'country': 'UK', 'year': YEAR, 'currency': 'GBP', 'units': '£ million', 'measure': 'Gross value added at basic prices',
        'total_value_added': float(x.GVA.sum()),
        'source': 'ONS Input-Output Supply and Use Tables, Blue Book 2025 (Data Sources: uk-supply-use-tables), 104 industries, 2023, current prices; labour, capital, occupation and emissions detail from the ONS modules listed in pipeline/uk/build_uk.py (uk-labour-share, uk-labour-composition, uk-capital-stocks, uk-gfcf-industry-asset, uk-ashe-industry-occupation, uk-env-accounts-ghg)',
        'vintage': 'Blue Book 2025',
        'checks': CHECKS,
        'note': 'Value added is GVA at basic prices = compensation of employees + gross operating surplus and mixed income + taxes less subsidies on production. Labels (short names, emoji, sectors) are Claude drafts awaiting Alex\'s review.'}
with open(os.path.join(ROOT, 'data', 'industries.json'), 'w', encoding='utf-8') as fh:
    json.dump(clean({'meta': meta, 'industries': industries}), fh, indent=1, allow_nan=False, ensure_ascii=False)
print(f'{len(industries)} industries and {len(files)} readouts written; total GVA GBP {meta["total_value_added"]:,.0f}m; checks passed')
