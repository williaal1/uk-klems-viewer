"""Build data/industries.json: the 63 KLEMS industries, 2017, sized by value added.

    uv run --with pandas python pipeline/build_industries.py

Source: Data Sources library, BEA/bea-bls-production-account (BEA-BLS Integrated
Industry-Level Production Account, release of 2025-04-25, consistent with the
2024-09-26 annual I-O update), sheets "Value Added", "Gross Output" and the
K / L compensation sheets, year 2017, millions of current dollars.

Checks (fail loudly):
  - exactly 63 industries with a production-account code;
  - value added = capital compensation + labor compensation, per industry (within $5m);
  - gross output = value added + energy + materials + services, per industry (within $5m).
"""
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIB = os.path.abspath(os.path.join(ROOT, '..', '..', '..', 'Data Sources', 'Economics', 'National Accounts',
                                   'Federal Statistical Agencies', 'BEA', 'bea-bls-production-account'))
YEAR = 2017
K_SHEETS = ['Capital_Art Compensation', 'Capital_IT Compensation', 'Capital_Other Compensation',
            'Capital_R&D Compensation', 'Capital_Software Compensation']
L_SHEETS = ['Labor_Col Compensation', 'Labor_NoCol Compensation']
EMS_SHEETS = ['Energy Compensation', 'Materials Compensation', 'Service Compensation']

pa = pd.read_csv(os.path.join(LIB, 'data', 'production_account.csv'), low_memory=False)
pa = pa[(pa.workbook == 'main') & (pa.year == YEAR)].dropna(subset=['industry_code'])
sheets = ['Value Added', 'Gross Output'] + K_SHEETS + L_SHEETS + EMS_SHEETS
w = pa[pa.sheet.isin(sheets)].pivot_table(index='industry_code', columns='sheet', values='value', aggfunc='first')
names = pa.drop_duplicates('industry_code').set_index('industry_code')[['industry_description', 'naics_2017']]

assert len(w) == 63, f'expected 63 industries, got {len(w)}'
assert w[sheets].notna().all().all(), 'missing cells'
k = w[K_SHEETS].sum(axis=1)
l = w[L_SHEETS].sum(axis=1)
ems = w[EMS_SHEETS].sum(axis=1)
assert (w['Value Added'] - k - l).abs().max() <= 5, 'VA != K + L'
assert (w['Gross Output'] - w['Value Added'] - ems).abs().max() <= 5, 'GO != VA + E + M + S'

# Kind of industry: BEA's sector for each summary industry (EPA useeio-v25-models sector_crosswalk.csv), with
# manufacturing split into nondurable / durable, the same groups the readout's purchase tables use.
XW = os.path.abspath(os.path.join(LIB, '..', '..', '..', '..', '..', 'Environmental', 'Emissions and Resource Use',
                                  'Federal Regulatory Agencies', 'EPA', 'useeio-v25-models', 'data', 'sector_crosswalk.csv'))
SECTORS = {'11': 'Agriculture, forestry & fishing', '21': 'Mining', '22': 'Utilities', '23': 'Construction',
           '31ND': 'Nondurable manufacturing', '33DG': 'Durable manufacturing', '42': 'Wholesale trade', '44RT': 'Retail trade',
           '48TW': 'Transportation & warehousing', '51': 'Information', 'FIRE': 'Finance, insurance & real estate',
           'PROF': 'Professional & business services', '6': 'Education & health care', '7': 'Arts, recreation, lodging & food',
           '81': 'Other services', 'G': 'Government'}
NONDURABLE = {'311FT', '313TT', '315AL', '322', '323', '324', '325', '326'}
PARTS = {'44RT': '441', '622HO': '622', '531': 'HS', 'GF': 'GFGD', 'GSL': 'GSLG'}   # a KLEMS merge takes its parts' sector
sec_of = pd.read_csv(XW, dtype=str)[['bea_sector', 'bea_summary']].dropna().drop_duplicates('bea_summary').set_index('bea_summary').bea_sector
def sector(code):
    s = sec_of[PARTS.get(code, code)]
    return ('31ND' if code in NONDURABLE else '33DG') if s == '31G' else s

# Short names for labels on the spheres: pipeline/short_names.csv (editable; source column says where each came from).
short = pd.read_csv(os.path.join(HERE, 'short_names.csv'), dtype=str).set_index('code').short_name
assert set(short.index) == set(w.index), 'short_names.csv must have exactly the 63 industries'

# An emoji per industry, drawn on its sphere: pipeline/emoji.csv (Claude's draft picks, 2026-10-04, for Alex to edit).
emoji = pd.read_csv(os.path.join(HERE, 'emoji.csv'), dtype=str).set_index('code').emoji
assert set(emoji.index) == set(w.index), 'emoji.csv must have exactly the 63 industries'

industries = []
for code, r in w.sort_values('Value Added', ascending=False).iterrows():
    naics = names.loc[code, 'naics_2017']
    industries.append({
        'code': code,
        'name': names.loc[code, 'industry_description'],
        'short_name': short[code],
        'emoji': emoji[code],
        'naics_2017': None if pd.isna(naics) else str(naics),
        'value_added': float(r['Value Added']),
        'sector': sector(code),
        'sector_name': SECTORS[sector(code)],
    })

out = {
    'meta': {
        'year': YEAR,
        'units': 'millions of current dollars',
        'measure': 'Production-account value added (= capital compensation + labor compensation)',
        'source': 'Data Sources/Economics/National Accounts/Federal Statistical Agencies/BEA/bea-bls-production-account/data/production_account.csv',
        'source_release': 'BEA-BLS Integrated Industry-Level Production Account, released 2025-04-25 (I-O annual update of 2024-09-26)',
        'total_value_added': float(w['Value Added'].sum()),
        'checks': 'VA = K + L and GO = VA + E + M + S per industry, within $5m',
        'note': ('Production-account value added differs from GDP-by-industry value added: the 63 sum to '
                 '$19,761.7bn vs $19,612.1bn GDP (bea-klems, All industries). Private industries come out lower '
                 '(gap tracks taxes on production, not exactly); government comes out higher (capital compensation '
                 'GF $484bn, GSL $907bn). Cause not yet confirmed from BEA documentation.'),
    },
    'industries': industries,
}
os.makedirs(os.path.join(ROOT, 'data'), exist_ok=True)
with open(os.path.join(ROOT, 'data', 'industries.json'), 'w') as f:
    json.dump(out, f, indent=1)
from collections import Counter
print('sectors:', dict(Counter(d['sector'] for d in industries)))
print(f"{len(industries)} industries, total VA ${out['meta']['total_value_added']/1e6:,.1f}tn; checks passed")
