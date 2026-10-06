# KLEMS Viewer

The US economy in 2017 as a bookcase of 63 industries. Each sphere is sized by value added. Click one to see its production function as seven pages:

- **Overview**
- **K**: capital
- **L**: labor
- **E**: energy
- **M**: materials
- **S**: purchased services
- **C**: carbon, an output

Internal demo, Common Wealth / Green Planning Commission.
- **Static site:** `index.html` + `js/` + `data/`, built by `pipeline/`.
- **2D SVG, laid out in screen pixels,** so text stays crisp and the page scrolls natively on phones. On a phone, tapping a sphere opens its readout below the bookcase.
- **Styled with the Common Wealth web kit** in `cw/`: tokens, base CSS and the CW monogram. The fonts are Archivo, Inter and JetBrains Mono, all SIL OFL 1.1, with licences in `cw/fonts/`.

## Sources (all 2017)

| Page | Source | Vintage |
|---|---|---|
| Spheres, Overview, K and L income | BEA-BLS Integrated Industry-Level Production Account (KLEMS) | released 2025-04-25 |
| K stock | BLS Total Factor Productivity, Capital Details | pulled 2026-06-17 |
| L occupations | BLS OEWS, national industry-specific estimates | May 2017 |
| E, M, S | BEA Use table, before redefinitions, detail, purchasers' prices | 2017 benchmark |
| C | EPA USEEIO v2.5, model kingbird-17, IPCC AR6 GWP-100 | published 2025-04-16 |

## Every mapping and conversion

**Industry codes**

| From → to | How |
|---|---|
| **KLEMS industry (63)**, the spine | BEA production-account codes (`111CA`, `325`, `GF`, …), from the account's own NAICS mapping sheet |
| KLEMS → BLS capital-detail sector (61) | NAICS ranges (`311-312`, `44,45`, …), matched by name: 61/61 private industries. Government has no BLS capital detail. `pipeline/crosswalk.csv` |
| KLEMS → OEWS industry + ownership (62) | 2017 OEWS codes (NAICS 2012 basis) in `pipeline/crosswalk.csv`. Rules below this table. |
| BEA detail I-O industry (402) → BEA summary (71) | EPA USEEIO `sector_crosswalk.csv` (`bea_detail` → `bea_summary`) |
| BEA summary (71) → KLEMS (63) | 58 codes identical. 13 merge: `441 445 452 4A0` → `44RT`; `622 623` → `622HO`; `HS ORE` → `531`; `GFGD GFGN GFE` → `GF`; `GSLG GSLE` → `GSL` |
| EPA USEEIO summary sector (71) → KLEMS (63) | Same 13 merges (EPA uses BEA summary codes) |

OEWS rules for the KLEMS → OEWS row:
- Private industries use private ownership (`5`).
- `713` and `721` exist only as private + local government (`57`) and are used as is.
- Federal = `999101`; State & local = `999201` + `999301`, including government schools and hospitals.
- Farms: none, because OEWS doesn't survey them.
- Fishing (`114`) is absent from 2017.

**Grouping**

| From → to | How |
|---|---|
| KLEMS industry → shelf (16 kinds of industry) | BEA sector from the EPA crosswalk, with manufacturing split. Nondurable: `311FT 313TT 315AL 322 323 324 325 326`; the rest of manufacturing is durable. A merged KLEMS industry takes its parts' sector. |
| I-O commodity (394) → group → band (E/M/S tables) | Detail commodity → BEA summary commodity (EPA crosswalk) → BEA sector (same 16 bands, plus "Noncomparable imports & adjustments" and "Scrap & used goods") |
| Occupation (SOC 2010) → supervisory / nonsupervisory | Supervisory = SOC major group 11 (management) + the 18 occupations titled "…Supervisors…". Everything else is nonsupervisory. |

**E / M / S classification of purchases**

BEA assigns E, M and S at an unpublished finer level, so this is an approximation. It is shown beside BEA's published totals, never scaled to them.

| Commodity | Class |
|---|---|
| `211000` oil & gas, `212100` coal, `221100` electric power, `221200` natural gas distribution, `324110` refineries | **E** |
| … except crude and petroleum products (`211000 324110 324121 324122 324190`) bought by refining (`324`) or chemicals (`325`); and `211000` bought by oil & gas extraction (`211`) | **M** (feedstock / own use) |
| Every other commodity coded `1…`, `2…` or `3…` except construction `23…` (this includes water & sewage, `221300`) | **M** |
| Everything else: construction, trade, transport, services, government, noncomparable imports, scrap & used, rest-of-world adjustment | **S** |

**Value conversions**

| Quantity | Conversion |
|---|---|
| Value added (sphere size) | Production-account value added = capital + labor compensation. It is not GDP-by-industry value added: the 63 sum to $19,762bn vs $19,612bn GDP. Sphere area ∝ value added. |
| K by asset class | Six tangible classes + intellectual property (software + R&D + artistic originals, from K by type) = K |
| Capital stocks | BLS 2017 chained dollars = current dollars, since 2017 is the base year, so asset stocks add up. Shares of capital income are fractions. |
| Wages across merged industries | Jobs summed. Mean wage weighted by jobs. Medians and percentiles are not combinable, so not shown. Wage bill = jobs × mean wage, set against KLEMS labor compensation. |
| OEWS repeated rows | Duplicate (code, ownership, occupation) rows dropped after checking that no two published values disagree |
| Purchases | Purchasers' prices: margins folded into goods, as BEA values KLEMS inputs. Each industry's total = production-account E + M + S within 0.2%. |
| Emissions by gas | Direct = EPA `B` (kg per $, by flow) × output `x` × AR6 GWP. Flows grouped as CO₂, methane, nitrous oxide, fluorinated (all HFCs, PFCs, SF₆, NF₃). Sum over gases = EPA `D·x`. |
| Emissions per dollar | Direct `D`, and with supply chain `N` (kg CO₂e per $ of EPA output), averaged over a merged industry by output. Supply-chain figures are never summed across industries. |
| Short names, emoji | `pipeline/short_names.csv`, `pipeline/emoji.csv` (editable) |

## Caveats (kept here, not on the pages)

**Value added**
- Sphere size uses the production account's value added (capital + labor compensation), not GDP-by-industry value added: the 63 sum to $19,762bn vs $19,612bn GDP.
  - Government comes out larger than in GDP. State & local is $2,352bn vs $1,689bn, with large capital compensation.
  - Trade and other industries come out smaller; the gaps track their taxes on production.
  - BEA's documentation does not state the cause.

**K: capital**
- BLS capital details cover private industries only, so Federal and State & local have no asset-level capital.
- Stocks and investment are in 2017 dollars (equal to current dollars in the base year). Depreciation is the wealth-stock rate.
- BLS's own capital-cost estimate differs from the production account's K and is not shown.

**L: labor**
- OEWS counts wages and salaries of employees only. KLEMS labor compensation also covers benefits and the self-employed, so "wages cover" is below 100% (33–98%, median 61%).
- Occupations OEWS suppresses are in the total jobs but in neither column.
- `n/p` = wage not published (suppressed or top-coded; the source data cannot tell which).
- Supervisory is an occupation-based definition (above). It is narrower than BLS's CES "production and nonsupervisory" split: 9.9% of jobs here vs 17.6% of private jobs in CES, May 2017.
- Farms have no occupation data; OEWS does not survey crop and animal production.
- `713` and `721` use OEWS's private + local government row, so a few local-government jobs are also counted in State & local (+0.2% on the private total).

**E / M / S: purchases**
- Every dollar row is a published BEA Use-table cell, or a sum of cells. Nothing is estimated or allocated.
- The approximation is only which page a commodity sits on (rules above). So a page's listed total can differ from BEA's published E, M or S for the industry.
  - Economy-wide: E +1.0%, M +1.0%, S −0.7%.
  - Within 5% for 49 (E), 44 (M) and 42 (S) of 63 industries.
  - Largest misses: chemicals' E (66% of published), air transport's M (199%).
- Across the three pages, the totals equal BEA's published E + M + S within 0.2%.
- "Share" is a share of the page's listed total.

**C: carbon**
- These are emissions EPA attributes to industries. Households' own emissions (cars, home heating) are not in any industry: industry CO₂ is 73% of EIA's total 2017 energy CO₂.
- Per-dollar figures use EPA's own 2017 output, which differs from the production account's gross output for a few industries (State & local 0.80×, retail 1.13×).
- Public power is in the government-enterprise industries (`GSLE`, `GFE` → State & local, Federal), not in Utilities.

**Codes**
- BEA lists `511` as NAICS 511 and 516; 516 does not exist after 2007.

## Rebuild

`pipeline/build_industries.py` and `pipeline/build_readout.py` read from a local data library that is not in this repo. Each stops on a failed check: identities, totals, crosswalk coverage.
