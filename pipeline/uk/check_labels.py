"""Check the three UK label files against the ONS SUT industry codes (Blue Book 2025, 2023).
Run: uv run --with pandas python check_labels.py"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SUT = ("../../../../../Data Sources/Economics/National Accounts/Foreign Statistical Agencies/"
       "ONS (UK)/uk-supply-use-tables/data/uk_sut_bb25.csv")
SECTORS = {'11', '21', '22', '23', '31ND', '33DG', '42', '44RT', '48TW', '51', 'FIRE', 'PROF', '6', '7', '81', 'G'}

d = pd.read_csv(SUT, dtype=str, usecols=['year', 'table', 'col_code', 'col_desc', 'col_type'])
u = d[(d.year == '2023') & (d.table == 'use_intermediate') & (d.col_type == 'detail')][['col_code', 'col_desc']].drop_duplicates()
assert len(u) == 104, len(u)
sut = dict(zip(u.col_code, u.col_desc))

ind = pd.read_csv(os.path.join(HERE, 'industries_uk.csv'), dtype=str, keep_default_na=False)
sn = pd.read_csv(os.path.join(HERE, 'short_names_uk.csv'), dtype=str, keep_default_na=False)
em = pd.read_csv(os.path.join(HERE, 'emoji_uk.csv'), dtype=str, keep_default_na=False)

for name, df in [('industries_uk', ind), ('short_names_uk', sn), ('emoji_uk', em)]:
    assert len(df) == 104, (name, len(df))
    assert df.code.is_unique, name
    assert set(df.code) == set(sut), (name, set(df.code) ^ set(sut))
assert dict(zip(ind.code, ind.ons_description)) == sut, 'ons_description differs from SUT col_desc'
assert set(ind.sector_key) <= SECTORS, set(ind.sector_key) - SECTORS
assert (ind.sic_codes != '').all()
assert sn.short_name.str.len().max() <= 30 and (sn.short_name != '').all()
assert sn.short_name.is_unique
assert (em.emoji != '').all() and (em.why != '').all()
assert (sn.source == 'Claude draft 2026-10-06').all()
print('OK: 104 rows in each file, same code set as the SUT, descriptions exact, sector keys valid, short names <= 30 chars')
print('longest short name:', sn.short_name.str.len().max())
print('distinct emoji:', em.emoji.nunique(), 'of 104')
print(ind.sector_key.value_counts().reindex(sorted(SECTORS), fill_value=0).to_string())
