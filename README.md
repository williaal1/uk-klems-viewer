# KLEMS Viewer UK

The UK economy in 2023 as a bookcase of 104 industries. Each sphere is sized by gross value added. Select one to see its production function on seven pages:

- **Overview**
- **K**: capital
- **L**: labour
- **E**: energy
- **M**: materials
- **S**: purchased services
- **C**: carbon, an output

It is the UK twin of the US KLEMS Viewer, an internal demo from Common Wealth / Green Planning Commission, in the Common Wealth web style.

- **Static site:** `index.html` + `js/` + `data/`, built by `pipeline/uk/build_uk.py` from a local data library that is not in this repo.
- **Drawing:** 2D SVG in screen pixels.
- **Style:** the Common Wealth kit, in `cw/`. Fonts are Archivo, Inter and JetBrains Mono, all SIL OFL 1.1, with licences in `cw/fonts/`.

## Sources (2023, current prices, £ million)

All are Office for National Statistics publications under the Open Government Licence v3.0.

| Page | Source | Vintage |
|---|---|---|
| Spheres, Overview, K and L income, E/M/S | Supply and use tables | Blue Book 2025 |
| L split of self-employed income | Labour costs and labour income (labour share by SIC section) | 18 Aug 2026 |
| L college / non-college | Composition-adjusted labour input (CALI), pay shares by qualification | 23 May 2025 edition (official statistics in development) |
| K stock, depreciation | Capital stocks and fixed capital consumption | 27 Nov 2025 |
| K investment | Gross fixed capital formation by industry and asset | Blue Book 2025 |
| L jobs, pay, occupations | Annual Survey of Hours and Earnings (ASHE), Tables 4 and 29 | 2023 revised |
| C | Environmental accounts, greenhouse gas emissions by industry | residence basis, 2023 |

## Every mapping and conversion

**Industries**

| From → to | How |
|---|---|
| **Industry (104)**, the spine | ONS supply-use industry codes (`A01` … `T97`), with SIC 2007 codes read from each code and description. `pipeline/uk/industries_uk.csv` |
| Industry → shelf (16 kinds of industry) | By SIC section, using the same 16 groups as the US viewer. Manufacturing is split nondurable / durable on the US list. Judgement calls are in `pipeline/uk/README.md`: computer programming sits in Information and rental & leasing in Professional services (following SIC; the US places them differently); water supply and sewerage in Utilities, waste in Professional & business; motor trades in Retail. |
| Industry → capital-stock code | `pipeline/uk/map_capital.csv`. 44 industries have their own ONS code; 60 share a wider ONS code, and their stock, investment and depreciation figures are for the whole group (named on the page). Real estate's stock is in ONS code `L`. |
| Industry → ASHE | `pipeline/uk/map_labour.csv`. Table 4 division: 67 own, 33 shared, 2 partial, 2 none (`B05`; `L68A` has no employees). Table 29: the industry's SIC section. |
| Industry → CALI group, labour-share section | `pipeline/uk/map_labour.csv`: 10 CALI groups; 20 SIC sections |
| Industry → emissions | `pipeline/uk/map_emissions.csv`. 100 map exactly to ONS groups. `C14`, `C31` and `E36` are suppressed by ONS (shown as not published). `L68A` (imputed rent) has none. |
| Product (CPA) → shelf band on E/M/S pages | The producing industry's shelf (`pipeline/uk/map_product_industry.csv`) |

**Value**

| Quantity | Conversion |
|---|---|
| Value added (sphere size) | GVA at basic prices = compensation of employees (D1) + gross operating surplus and mixed income + taxes less subsidies on production. The 104 sum to £2,497,390m, equal to Blue Book 2025. Sphere area ∝ GVA. |
| Labour (L) | D1 + the labour part of mixed income. Each section's mixed income is back-solved from its published labour share (GOS = D1 × (1 / share − 1); mixed income = GOS & MI − GOS), then multiplied by the labour share. The sections' totals reproduce Blue Book GOS and mixed income within £18m. Mixed income is spread over a section's industries pro rata to their GOS & MI, except owner-occupiers' imputed rent (`L68A`), which takes none. |
| Capital (K) | GVA − L, so it includes taxes less subsidies on production. It is negative where subsidies exceed operating surplus (rail −£1,271m; `B05` −£5m). |
| College / non-college | The industry's CALI group pay shares × L. College = degree or higher (HQ5 + HQ6); HQ4 (higher education below degree) counts as non-college. |
| E / M / S | Each product's 2023 intermediate use, sorted by rule:<br>• Energy = `CPA_B05`, `CPA_B06 & B07`, `CPA_C19`, `CPA_D351`, `CPA_D352_3`, except crude and refined products bought by refining and chemicals, and oil and gas bought by oil and gas extraction, which count as materials.<br>• Every other good (CPA A, B, C) is materials.<br>• Everything else is services.<br>Totals: E £261,534m, M £714,964m, S £1,345,918m. Each industry's E + M + S = its intermediate use exactly. |
| Capital stock | Net and gross stock, current prices. Depreciation rate = CFC / net stock: 45 industries have CFC at their own coverage; 59 use their CAPSTK group's rate. |
| Jobs and pay | ASHE 2023 revised, all employees, gross annual pay. Jobs are ONS weighted counts (thousands × 1,000). Mean pay. |
| Supervisory / nonsupervisory | SOC 2020 major group 1 (managers, directors and senior officials: sub-major groups 11 and 12) vs the other sub-major groups. That is the only split ASHE Table 29's detail allows. |
| Emissions | kt CO₂e (ONS) → tonnes. Grouped as CO₂, methane, nitrous oxide, fluorinated (HFC, PFC, SF₆, NF₃). Per £ = direct emissions / gross output. |

## Caveats (kept here, not on the pages)

- **No published UK KLEMS account exists for 2023.** The account here is built from the supply-use tables by the rules above. ONS's own productivity accounts are coarser (16–19 industries), index-only, or under review.
- **E / M / S:** there is no published UK split to compare against.
  - `CPA_B06 & B07` combines crude oil and gas with metal ores, and `CPA_D352_3` includes steam and air conditioning.
  - Mining support (`B09`) and repair services (`C33`) count as materials under the rule.
  - Owner-occupiers' imputed rent buys −£20.8bn of financial services: this is how the accounts allocate banks' interest margins (FISIM).
- **Capital:**
  - The UK publishes 13 asset types per industry (the US viewer shows 27–77); no land and no inventories.
  - No productive stock or user cost by industry × asset for recent years, so no share of capital income by asset.
  - 60 industries' figures are for a wider ONS group.
  - One depreciation rate rounds to 100% (transport equipment `C13T15`: £6m on £6m).
  - ONS revises other buildings and structures upward in its June 2026 preliminary release (not used here).
- **Labour:**
  - ASHE counts employee jobs only, rounded to thousands and "indicative only"; it excludes the self-employed.
  - The ASHE wage bill (jobs × mean annual pay) is compared with D1 for the same ASHE industry basis. Nationally it is about 61% of D1: D1 also includes employer social contributions.
  - Occupation groups are 26 SOC 2020 sub-major groups per SIC section (the US viewer lists every detailed occupation per industry). Suppressed cells are shown as not published. Section B (mining) has none.
  - College / non-college shares are applied at CALI's 10 industry groups.
- **Carbon:**
  - Residence basis, direct emissions only. There is no supply-chain figure (it would need a Leontief calculation on the UK input-output tables).
  - Industry emissions total 357,757 kt; households' own 121,958 kt are not in any industry.
  - Three groups are suppressed by ONS (676 kt).
- **Labels** (short names, emoji, shelves) are Claude's drafts in `pipeline/uk/`, for editing.

## Rebuild

`uv run --with pandas --with pyarrow python pipeline/uk/build_uk.py` rebuilds `data/` from the library. It stops on any failed check:
- GVA, D1 and gross output = Blue Book 2025;
- VA = K + L and GO = K + L + E + M + S for every industry;
- the mixed-income back-solve;
- net stock, CFC and GFCF totals = ONS;
- ASHE jobs = Table 4;
- emissions = ONS section totals less suppressed groups.
