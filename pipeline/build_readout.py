"""Build data/readout/<code>.json: the click-through production-function readout for each KLEMS industry, 2017.

    uv run --with pandas --with pyarrow python pipeline/build_readout.py

Sources (all in the Data Sources library, read-only):
  - BEA/bea-bls-production-account: gross output, value added, K/L/E/M/S compensation, K by type
    (main workbook) and by asset class (expanded_capital workbook), L by college / non-college.
  - BLS/tfp-capital-details: capital stock, investment, costs, depreciation and income shares by asset
    (private industries only). 2017 is the base year, so 2017-dollar stocks are additive.
  - BLS/oes-occupational-wages: May 2017 national industry-specific estimates (wage and salary jobs only).
  - BEA/io-make-use-before-redefinitions: 2017 detail Use table at purchasers' prices (394 commodities x 402
    industries): what each industry buys. Detail industries -> BEA summary via EPA useeio-v25-models
    sector_crosswalk.csv, then summary -> KLEMS (identical codes, or the 13 merges in KLEMS_MERGE).
  - EPA/useeio-v25-models, model kingbird-17: 2017 GHG emissions on BEA's 71 summary industries (IPCC AR6 GWP-100),
    summed into the 63 KLEMS industries with the same 13 merges. Direct emissions = B (kg per $, by gas) x output x;
    supply-chain intensity = N (kg CO2e per $, upstream included), averaged over a merged industry by output.
    Emissions are those EPA attributes to industries; households' own emissions (cars, home heating) are excluded.
Industry mapping: pipeline/crosswalk.csv.

E / M / S split of purchases (documented approximation; Alex, 2026-10-04). BEA assigns E/M/S cell by cell at an
unpublished "working level" (~5,000 products x ~800 industries), so no rule on the 394-commodity table reproduces it
exactly. Rules applied here, from BEA's written definitions (research/ems-classification/KEY_QUOTES.md):
  - Energy: oil & gas extraction (211000), coal mining (212100), electric power (221100), natural gas
    distribution (221200), petroleum refineries (324110) ...
  - ... except that petroleum products and crude bought by petroleum refining (324) and chemicals (325) are
    materials (feedstock), and oil & gas bought by oil & gas extraction (211) is materials (own use; Claude's inference).
  - Materials: every other goods commodity (agriculture, mining, manufacturing).
  - Services: everything else (construction, utilities other than above, trade, transport, services,
    government, noncomparable imports, scrap and used goods, rest-of-world adjustment).
  The panel shows BEA's published E/M/S totals and the sum of the listed commodities side by side; nothing is scaled.

Checks (fail loudly unless noted):
  - K by asset class + intellectual property (from K by type) = K; VA = K + L        (within $5m)
    (the expanded-capital asset classes exclude intellectual property: checked 2026-10-04, gap = IPP within $2m)
  - asset-level productive stock sums to BLS "All assets" productive stock              (within 0.5%)
  - asset-level shares of capital income sum to 1                                         (within 0.01)
  - every OEWS code in the crosswalk exists in the 2017 file                                (reported)
  - each industry's purchases (E+M+S, all commodities) = production-account E+M+S          (within 0.2%)
  - every detail commodity and industry in the Use table maps to a group                    (fatal)
  - carbon: sum over gases = EPA's direct CO2e (D x) per industry; 63-industry total = 71-sector total (within 1 kt)
"""
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ECON = os.path.abspath(os.path.join(ROOT, '..', '..', '..', 'Data Sources', 'Economics'))
PA = os.path.join(ECON, 'National Accounts', 'Federal Statistical Agencies', 'BEA', 'bea-bls-production-account', 'data', 'production_account.csv')
CAP = os.path.join(ECON, 'Production', 'Federal Statistical Agencies', 'BLS', 'tfp-capital-details', 'data', 'tfp_capital_details.parquet')
OES = os.path.join(ECON, 'Employment', 'Federal Statistical Agencies', 'BLS', 'oes-occupational-wages', 'data', 'oes_occupational_wages.parquet')
YEAR = 2017
OUT = os.path.join(ROOT, 'data', 'readout')
os.makedirs(OUT, exist_ok=True)

K_TYPES = {'IT equipment': 'Capital_IT Compensation', 'Software': 'Capital_Software Compensation',
           'R&D': 'Capital_R&D Compensation', 'Artistic originals': 'Capital_Art Compensation',
           'Other capital': 'Capital_Other Compensation'}
K_CLASSES = {'Computers': 'COMP_Compensation', 'Communications equipment': 'COMM_Compensation',
             'Instruments and office equipment': 'INST Compensation', 'Transport equipment': 'TRANS_Compensation',
             'Other equipment': 'OEQ_Compensation', 'Structures, land and inventories': 'STRUC_Compensation'}
TOP = {'gross_output': 'Gross Output', 'value_added': 'Value Added', 'E': 'Energy Compensation',
       'M': 'Materials Compensation', 'S': 'Service Compensation'}
L_SPLIT = {'College': 'Labor_Col Compensation', 'Non-college': 'Labor_NoCol Compensation'}

xw = pd.read_csv(os.path.join(HERE, 'crosswalk.csv'), dtype=str).fillna('')

# ---------- production account ----------
pa = pd.read_csv(PA, low_memory=False)
pa = pa[(pa.year == YEAR) & pa.workbook.isin(['main', 'expanded_capital'])].dropna(subset=['industry_code'])
pw = pa.pivot_table(index='industry_code', columns='sheet', values='value', aggfunc='first')
names = pa.drop_duplicates('industry_code').set_index('industry_code')[['industry_description', 'naics_2017']]

# ---------- capital details ----------
cap = pd.read_parquet(CAP)
cap = cap[cap.year == YEAR]

def broad_table(naics, source_file):
    g = cap[(cap.naics == naics) & (cap.source_file == source_file)]
    def pick(measure, unit_has):
        s = g[(g.measure == measure) & g.units.str.contains(unit_has, regex=False)]
        return s.set_index('asset_category').value
    cols = {
        'productive_stock_bn': pick('Productive capital stock', 'Billions of 2017'),
        'wealth_stock_bn': pick('Wealth stock', 'Billions of 2017'),
        'investment_bn': pick('Capital investment', 'Billions of 2017'),
        'capital_costs_bn': pick('Capital costs', 'Billions of current'),
        'share_of_capital_income': pick('Capital asset share in industry capital income', 'Percentage'),  # a fraction, despite BLS's unit label
        'depreciation_rate': pick('Wealth stock depreciation rate', 'Rate'),
    }
    t = pd.DataFrame(cols)
    return [{'asset': a, **{k: (None if pd.isna(v) else round(float(v), 4)) for k, v in r.items()}} for a, r in t.iterrows()]

def asset_table(naics):
    g = cap[(cap.naics == naics) & cap.source_file.str.startswith('rental')]
    def pick(measure):
        return g[g.measure == measure].set_index('asset_category').value
    t = pd.DataFrame({
        'productive_stock_m': pick('Productive capital stock'),
        'investment_m': pick('Capital investment'),
        'depreciation_rate': pick('Wealth stock depreciation rate'),
        'share_of_capital_income': pick('Capital asset share in industry capital income'),
    })
    return t

# ---------- OEWS ----------
oes = pd.read_parquet(OES, columns=['year', 'area_type', 'naics', 'own_code', 'occ_code', 'occ_title', 'o_group',
                                    'tot_emp', 'a_mean', 'a_median', 'h_pct10', 'h_pct25', 'h_median', 'h_pct75', 'h_pct90'])
oes = oes[(oes.year == YEAR) & (oes.area_type.astype(str) == '1')]
# The library file repeats some rows: exact duplicates, and codes listed at two levels (e.g. 531000 as both 3- and
# 4-digit) with identical values. Drop them, after checking every repeat carries the same numbers.
KEY = ['naics', 'own_code', 'occ_code']
VALS = ['tot_emp', 'a_mean', 'a_median', 'h_pct10', 'h_pct25', 'h_median', 'h_pct75', 'h_pct90']
rep = oes[oes.duplicated(KEY, keep=False)]
conflicts = rep.groupby(KEY)[VALS].nunique().gt(1).any(axis=1).sum()   # blanks don't count as disagreement
assert conflicts == 0, f'{conflicts} repeated OEWS keys carry different published values'
oes = oes.assign(_n=oes[VALS].notna().sum(axis=1)).sort_values('_n', ascending=False).drop_duplicates(KEY).drop(columns='_n')
oes_codes = set(zip(oes.naics.astype(str), oes.own_code.astype(str)))

# ---------- purchases (Use table, purchasers' prices) ----------
IO = os.path.join(ECON, 'National Accounts', 'Federal Statistical Agencies', 'BEA', 'io-make-use-before-redefinitions', 'data', 'io_make_use_before_redefinitions.parquet')
XW = os.path.abspath(os.path.join(ECON, '..', 'Environmental', 'Emissions and Resource Use', 'Federal Regulatory Agencies', 'EPA', 'useeio-v25-models', 'data', 'sector_crosswalk.csv'))
KLEMS_MERGE = {'441': '44RT', '445': '44RT', '452': '44RT', '4A0': '44RT', '622': '622HO', '623': '622HO', 'HS': '531', 'ORE': '531',
               'GFGD': 'GF', 'GFGN': 'GF', 'GFE': 'GF', 'GSLG': 'GSL', 'GSLE': 'GSL'}
NONDURABLE = {'311FT', '313TT', '315AL', '322', '323', '324', '325', '326'}
SECTORS = {'11': 'Agriculture, forestry & fishing', '21': 'Mining', '22': 'Utilities', '23': 'Construction',
           '31ND': 'Nondurable manufacturing', '33DG': 'Durable manufacturing', '42': 'Wholesale trade', '44RT': 'Retail trade',
           '48TW': 'Transportation & warehousing', '51': 'Information', 'FIRE': 'Finance, insurance & real estate',
           'PROF': 'Professional & business services', '6': 'Education & health care', '7': 'Arts, recreation, lodging & food',
           '81': 'Other services', 'G': 'Government', 'Other': 'Noncomparable imports & adjustments', 'Used': 'Scrap & used goods'}
FUEL = {'211000', '212100', '221100', '221200', '324110'}
FEEDSTOCK = {'211000', '324110', '324121', '324122', '324190'}

io = pd.read_parquet(IO, columns=['year', 'table_name', 'table_level', 'row_code', 'row_description', 'row_type', 'col_code', 'col_type', 'value'])
io = io[(io.year == YEAR) & (io.table_name == 'use_pur') & (io.row_type == 'Commodity') & ~io.row_code.str.match(r'^[VT]0')]
sum_names = io[io.table_level == 'summary'].drop_duplicates('row_code').set_index('row_code').row_description
use = io[(io.table_level == 'detail') & io.col_type.str.startswith('Indus') & ~io.col_code.str.match(r'^[FT]')].copy()
cwx = pd.read_csv(XW, dtype=str)[['bea_sector', 'bea_summary', 'bea_detail']].dropna().drop_duplicates('bea_detail').set_index('bea_detail')
use['ind_summary'] = use.col_code.map(cwx.bea_summary)
use['com_summary'] = use.row_code.map(cwx.bea_summary)
use['com_sector'] = use.row_code.map(cwx.bea_sector)
assert use[['ind_summary', 'com_summary', 'com_sector']].notna().all().all(), 'Use-table code missing from crosswalk'
use['klems'] = use.ind_summary.map(lambda c: KLEMS_MERGE.get(c, c))
use.loc[use.com_sector == '31G', 'com_sector'] = use.com_summary.map(lambda c: '31ND' if c in NONDURABLE else '33DG')
assert use.com_sector.isin(SECTORS.keys()).all(), f'unlabelled sectors {set(use.com_sector) - set(SECTORS)}'

def ems_class(com, ind):
    if com in FUEL:
        if com in FEEDSTOCK and ind in ('324', '325'): return 'M'
        if com == '211000' and ind == '211': return 'M'
        return 'E'
    if com in FEEDSTOCK and ind in ('324', '325'): return 'M'
    return 'M' if com[0] in '123' and not com.startswith('23') else 'S'
use['f'] = [ems_class(c, k) for c, k in zip(use.row_code, use.klems)]

def purchases(code):
    g = use[use.klems == code].groupby(['f', 'com_sector', 'com_summary', 'row_code', 'row_description'], as_index=False).value.sum()
    out = {}
    for f, gf in g.groupby('f'):
        sectors = []
        for sec, gs in gf.groupby('com_sector'):
            groups = []
            for sm, gg in gs.groupby('com_summary'):
                items = [[r.row_description.strip(), round(float(r.value), 1)] for r in gg.sort_values('value', ascending=False).itertuples()]
                groups.append({'name': str(sum_names.get(sm, sm)).strip(), 'value': round(float(gg.value.sum()), 1), 'items': items})
            groups.sort(key=lambda d: -d['value'])
            sectors.append({'name': SECTORS[sec], 'value': round(float(gs.value.sum()), 1), 'groups': groups})
        sectors.sort(key=lambda d: -d['value'])
        out[f] = {'listed_total': round(float(gf.value.sum()), 1), 'sectors': sectors}
    return out

# ---------- carbon (EPA USEEIO v2.5, kingbird-17) ----------
EPA = os.path.abspath(os.path.join(ECON, '..', 'Environmental', 'Emissions and Resource Use', 'Federal Regulatory Agencies', 'EPA', 'useeio-v25-models', 'data'))
MODEL = 'kingbird-17'
flows = pd.read_csv(os.path.join(EPA, 'ghg_flows_by_sector.csv'))
impacts = pd.read_csv(os.path.join(EPA, 'ghg_impacts_by_sector.csv'))
xv = pd.read_csv(os.path.join(EPA, 'output_vectors.csv'))
gwp = pd.read_csv(os.path.join(EPA, 'characterization_factors.csv')).set_index('flow_id').gwp_ar6
ex = xv[(xv.model == MODEL) & (xv.vector == 'x')].set_index('sector').usd
Bg = flows[(flows.model == MODEL) & (flows.matrix == 'B')].pivot_table(index='sector', columns='flow_id', values='value')
co2e_t = Bg.mul(ex, axis=0) * gwp.reindex(Bg.columns).fillna(1) / 1000   # tonnes CO2e, by sector x gas
def gas(flow):
    return {'Carbon dioxide': 'Carbon dioxide', 'Methane': 'Methane', 'Nitrous oxide': 'Nitrous oxide'}.get(flow.split('/')[0], 'Fluorinated gases')
by_gas = co2e_t.T.groupby(co2e_t.columns.map(gas)).sum().T
Dimp = impacts[(impacts.model == MODEL) & (impacts.matrix == 'D')].set_index('sector').value
Nimp = impacts[(impacts.model == MODEL) & (impacts.matrix == 'N')].set_index('sector').value
direct_t = Dimp * ex / 1000
assert (by_gas.sum(axis=1) - direct_t).abs().max() < 1, 'gases do not sum to D x'
epa_k = pd.Series(ex.index, index=ex.index).map(lambda c: KLEMS_MERGE.get(c, c))
EPA_TOTAL_T = float(direct_t.sum())

def carbon(code):
    secs = epa_k[epa_k == code].index
    assert len(secs), f'{code}: no EPA sector'
    xs = ex[secs]
    return {
        'epa_sectors': list(secs),
        'direct_t': float(direct_t[secs].sum()),
        'share_of_industry_total': float(direct_t[secs].sum() / EPA_TOTAL_T),
        'by_gas_t': {g: float(by_gas.loc[secs, g].sum()) for g in by_gas.columns},
        'output_usd': float(xs.sum()),
        'direct_kg_per_usd': float((Dimp[secs] * xs).sum() / xs.sum()),
        'supply_chain_kg_per_usd': float((Nimp[secs] * xs).sum() / xs.sum()),
    }

def combine(rows):
    """Combine one occupation across several OEWS industries: employment sums; mean wage is employment-weighted."""
    emp = rows.tot_emp.sum(min_count=1)
    w = rows.dropna(subset=['tot_emp', 'a_mean'])
    mean = (w.tot_emp * w.a_mean).sum() / w.tot_emp.sum() if len(w) and w.tot_emp.sum() > 0 else None
    return emp, mean

def clean(v):
    """Missing values (NaN) become null, recursively."""
    if isinstance(v, dict): return {k: clean(x) for k, x in v.items()}
    if isinstance(v, list): return [clean(x) for x in v]
    if isinstance(v, float) and v != v: return None
    return v

missing_codes = []
ems_ratio = []
carbon_sum = []
summary = []
for _, x in xw.iterrows():
    code = x.klems_code
    r = pw.loc[code]
    k_types = {k: float(r[v]) for k, v in K_TYPES.items()}
    k_classes = {k: float(r[v]) for k, v in K_CLASSES.items()}
    l_split = {k: float(r[v]) for k, v in L_SPLIT.items()}
    K, L = sum(k_types.values()), sum(l_split.values())
    # The expanded-capital asset classes cover tangible capital only; intellectual property is the remainder.
    k_classes['Intellectual property (software, R&D, artistic originals)'] = k_types['Software'] + k_types['R&D'] + k_types['Artistic originals']
    assert abs(sum(k_classes.values()) - K) <= 5, f'{code}: K by asset class + intellectual property != K'
    assert abs(r['Value Added'] - K - L) <= 5, f'{code}: VA != K + L'
    top = {k: float(r[v]) for k, v in TOP.items()}
    naics = names.loc[code, 'naics_2017']
    out = {
        'code': code,
        'name': names.loc[code, 'industry_description'],
        'naics_2017': None if pd.isna(naics) else str(naics),
        'year': YEAR,
        'units_note': 'production function in millions of current dollars',
        'production': {**top, 'K': K, 'L': L, 'K_by_type': k_types, 'K_by_asset_class': k_classes, 'L_by_education': l_split},
        'capital': None,
        'labor': None,
        'notes': [n for n in [x.note] if n],
    }

    # capital stock (private industries)
    if x.bls_capital_naics:
        n = x.bls_capital_naics
        at = asset_table(n)
        broad = broad_table(n, 'capital_details')
        all_assets = next(b for b in broad if b['asset'] == 'All assets')
        stock_sum = at.productive_stock_m.sum() / 1000
        assert abs(stock_sum - all_assets['productive_stock_bn']) <= 0.005 * all_assets['productive_stock_bn'], f'{code}: asset stocks do not sum to All assets'
        assert abs(at.share_of_capital_income.sum() - 1) <= 0.01, f'{code}: asset income shares do not sum to 1'
        at = at[at.productive_stock_m > 0].sort_values('productive_stock_m', ascending=False)
        out['capital'] = {
            'bls_naics': n,
            'broad': broad,
            'information_processing': broad_table(n, 'ipe_details'),
            'intellectual_property': broad_table(n, 'ipp_details'),
            'assets': [{'asset': a, **{k: (None if pd.isna(v) else round(float(v), 6)) for k, v in rr.items()}} for a, rr in at.iterrows()],
        }
        summary.append((code, 'capital', len(at), round(all_assets['productive_stock_bn'], 1)))

    # labor by occupation
    if x.oews_naics:
        codes = x.oews_naics.split(';')
        owns = x.oews_own_code.split(';')
        owns = owns if len(owns) == len(codes) else owns * len(codes)
        pairs = []
        for c, o in zip(codes, owns):
            if (c, o) in oes_codes:
                pairs.append((c, o))
                continue
            # No row for exactly this ownership: fall back to the narrowest published ownership group that contains it
            # (e.g. 713000 exists only as 57 = private + local government in 2017), and say so on the panel.
            alts = sorted((oo for cc, oo in oes_codes if cc == c and o in oo), key=len)
            if alts:
                pairs.append((c, alts[0]))
                out['notes'].append(f'OEWS publishes {c} only for ownership group {alts[0]} (not {o} alone); used as is.')
            else:
                missing_codes.append(f'{code}:{c}/{o}')
        sel = pd.concat([oes[(oes.naics.astype(str) == c) & (oes.own_code.astype(str) == o)] for c, o in pairs])
        tot = sel[sel.occ_code == '00-0000']
        total_emp, total_mean = combine(tot)
        wage_bill = float((tot.tot_emp * tot.a_mean).sum()) / 1e6  # millions of dollars
        # Supervisory = every management occupation (SOC major group 11) plus every first-line supervisor occupation
        # (title contains "Supervisor"; 18 occupations in SOC 2010). Everything else is nonsupervisory. (Claude, 2026-10-04)
        sides = {'supervisory': [], 'nonsupervisory': []}
        for (occ, title), g in sel[sel.o_group == 'detailed'].groupby(['occ_code', 'occ_title']):
            emp, mean = combine(g)
            side = 'supervisory' if occ.startswith('11-') or 'Supervisor' in title else 'nonsupervisory'
            sides[side].append({'code': occ, 'title': title, 'employment': None if pd.isna(emp) else float(emp), 'mean_wage': mean})
        def side_summary(rows):
            rows.sort(key=lambda d: -(d['employment'] or 0))
            w = [r for r in rows if r['employment'] and r['mean_wage']]
            emp = sum(r['employment'] or 0 for r in rows)
            mean = sum(r['employment'] * r['mean_wage'] for r in w) / sum(r['employment'] for r in w) if w else None
            return {'employment': emp, 'mean_wage': mean, 'occupations': rows}
        out['labor'] = {
            'oews_industries': [f'{c} (ownership {o})' for c, o in pairs],
            'total_employment': None if pd.isna(total_emp) else float(total_emp),
            'mean_wage': total_mean,
            'oews_wage_bill_m': wage_bill,
            'klems_labor_compensation_m': L,
            'supervisory': side_summary(sides['supervisory']),
            'nonsupervisory': side_summary(sides['nonsupervisory']),
        }
        summary.append((code, 'labor', len(sides['supervisory']) + len(sides['nonsupervisory']), total_emp))

    out['carbon'] = carbon(code)
    carbon_sum.append(out['carbon']['direct_t'])
    out['purchases'] = purchases(code)
    listed = sum(v['listed_total'] for v in out['purchases'].values())
    published = top['E'] + top['M'] + top['S']
    assert abs(listed / published - 1) <= 0.002, f'{code}: Use-table purchases {listed:.0f} vs production account E+M+S {published:.0f}'
    ems_ratio.append((code, *(out['purchases'].get(k, {}).get('listed_total', 0) / top[k] if top[k] else None for k in 'EMS')))

    with open(os.path.join(OUT, f'{code}.json'), 'w') as f:
        json.dump(clean(out), f, separators=(',', ':'), allow_nan=False)  # browsers reject NaN in JSON

print(f'{len(xw)} industries written to data/readout/')
print('capital panels:', sum(1 for s in summary if s[1] == 'capital'), '| labor panels:', sum(1 for s in summary if s[1] == 'labor'))
print('OEWS codes not in the 2017 file:', missing_codes or 'none')
r = pd.DataFrame(ems_ratio, columns=['code', 'E', 'M', 'S']).set_index('code')
print('listed / published, by industry (median, min, max):', {k: (round(r[k].median(), 3), round(r[k].min(), 2), round(r[k].max(), 2)) for k in 'EMS'})
print('industries within 5% of published:', {k: int((abs(r[k] - 1) < 0.05).sum()) for k in 'EMS'}, 'of', len(r))
assert abs(sum(carbon_sum) - EPA_TOTAL_T) < 1000, 'carbon: 63-industry total differs from the 71-sector total'
print(f'carbon: {sum(carbon_sum)/1e6:,.1f} Mt CO2e across 63 industries = EPA {MODEL} total {EPA_TOTAL_T/1e6:,.1f} Mt')
