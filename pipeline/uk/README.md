# UK viewer labels (drafts for Alex to edit)

Claude drafts, 2026-10-06. Nothing here has been reviewed by Alex. Edit the CSVs directly; run `check_labels.py` afterwards.

The UK viewer's industries are the 104 industries of the ONS supply-use tables, Blue Book 2025 (library module `Data Sources/Economics/National Accounts/Foreign Statistical Agencies/ONS (UK)/uk-supply-use-tables/`). The codes and descriptions are copied exactly from `data/uk_sut_bb25.csv` (table `use_intermediate`, the 104 `col_type == "detail"` columns, 2023). The US viewer's equivalents are `pipeline/short_names.csv`, `pipeline/emoji.csv` and the SECTORS dict in `build_industries.py`, in `GPC Data Project/Microsite/KLEMS Viewer/`.

## Files

| File | What it holds |
|---|---|
| `industries_uk.csv` | `code` (ONS's, exact), `ons_description` (ONS's, exact, including its odd capitalisation), `sic_codes` (SIC 2007 divisions/groups covered, read off the code and description), `sector_key` (one of the US viewer's 16 SECTORS keys, which decides the shelf), `note` (any judgement call) |
| `short_names_uk.csv` | `code`, `short_name` (30 characters or fewer, British usage), `source` ("Claude draft 2026-10-06") |
| `emoji_uk.csv` | `code`, `emoji` (single emoji, no flags, no joined sequences), `why` |
| `check_labels.py` | Asserts 104 rows in each file, identical code sets matching the SUT data, descriptions identical to the SUT's, valid sector keys, short names within 30 characters. Run: `uv run --with pandas python check_labels.py` |

Tip: keep `sic_codes` as text when editing in a spreadsheet; values like `10.1` or `24.1-24.3` get mangled into numbers or dates.

## Sector rule used

By SIC section (A->11, B->21, D and E water->22, F->23, C->31ND or 33DG, G46->42, G47->44RT, H->48TW, I->7, J->51, K and L->FIRE, M and N->PROF, O->G, P and Q->6, R->7, S and T->81). Manufacturing is split nondurable/durable by following the US viewer's own NONDURABLE set (food, beverage and tobacco, textiles, apparel and leather, paper, printing, petroleum, chemicals, plastics and rubber); everything else in C is durable.

Counts: 11: 3, 21: 4, 22: 4, 23: 1, 31ND: 24, 33DG: 18, 42: 1, 44RT: 2, 48TW: 6, 51: 5, FIRE: 6, PROF: 16, 6: 3, 7: 6, 81: 4, G: 1 (total 104). The UK list splits food, chemicals and some metals much finer than the US list, so 31ND has 24 spheres against the US's 8.

## Judgement calls (sector_key)

1. **E36 water supply, E37 sewerage -> 22 Utilities.** The US treats water and sewage as utilities (NAICS 221).
2. **E38 waste collection and disposal, E39 remediation -> PROF.** The US viewer puts waste management (562) in Professional & business services. Alternative: 22.
3. **G45 motor trades -> 44RT.** It mixes vehicle dealers (US retail), vehicle repair (US other services) and parts wholesale. Kept as one block in retail. Alternatives: 42 or 81.
4. **C21 pharmaceuticals -> 31ND.** The US counts drugs inside chemicals (NAICS 3254), which is nondurable. **C22 rubber and plastics -> 31ND**, matching US 326. **C16 wood -> 33DG**, matching US 321.
5. **C3315 ship repair, C3316 aircraft repair, C33OTHER repair and installation -> 33DG.** SIC puts these in manufacturing (section C); NAICS would put repair in Other services (81). Followed SIC section C as asked. Alternative: 81.
6. **J62 computer programming and consultancy -> 51.** By SIC section J. The US viewer puts computer systems design (5415) in PROF. This one is likely to matter visually; Alex may prefer PROF.
7. **N77 rental and leasing -> PROF.** By SIC section N. The US viewer puts rental and leasing (532RL) in FIRE.
8. **L68A owner-occupiers' housing, L68BXL683, L683 -> FIRE.** L68A is imputed rent (no actual firm); it is the UK counterpart of the housing part of the US 531.
9. **M70 head offices and management consultancy -> PROF**, as the US does for management of companies (55).
10. **O84 -> G.** One UK government sphere; the SUT has no central/local split (the US viewer has federal and state/local).
11. **P85 education -> 6**, although UK education is mostly public. **Q86 and Q87 & Q88 -> 6.**
12. **R90-R93 -> 7** (arts, libraries and museums, gambling, sport). **S94 membership organisations and T97 households as employers -> 81**, with S95 and S96.
13. **A03 fishing -> 11.** The US pairs fishing with forestry; the UK splits them, with fishing given its own fish emoji.
14. **H493T495 land transport and pipelines, H52 warehousing and transport support, H53 post -> 48TW.** ONS combines several US industries (truck, transit, pipelines) into H493T495.

## Short names

Plain English, British usage ("Clothing", "Fertilisers", "Vets", "Restaurants, pubs & catering"). The longest names are exactly 30 characters; abbreviations were needed in "Public admin & defence" and "Estate agents & property mgmt" (the one I am least happy with). Where ONS merges industries (`B06 & B07`, `J59 & J60`, `Q87 & Q88`, `C1101T1106 & C12`) the name names the main parts. US wording was reused where the industry matches ("Banking & credit", "Insurance & pensions" in place of "Insurance", "Telecoms" in place of "Broadcasting & telecom").

## Emoji

US picks are reused where the industry is the same (farms, oil and gas, construction, retail, wholesale, banking, insurance, legal, computers and electronics, machinery, motor vehicles, aerospace, hotels, and so on). Every one of the 104 emoji is distinct. Stretches (also flagged in `why` or `note`):

- C20B petrochemicals (generic factory), C244_5 other basic metals (coin), C30OTHER other transport equipment (motorbike), C3316 aircraft repair (small plane), L683 estate agents (price tag), M74 other professional activities (camera), E39 site remediation (roadworks), T97 households as employers (laundry basket), S95 repair of computers and goods (toolbox), C20C dyes and agrochemicals (seedling, dyes not shown), C1101T1106 & C12 alcohol and tobacco (beer only).
- Newer emoji (Unicode 12-13): 🪨 B08, 🫒 C104, 🪙 C244_5, 🪵 C16, 🪪 N78. They render on iOS 15.4 and later; if the viewer needs to support older Apple devices, swap them.
- Two emoji contain a variation selector (⛏️, 🏛️ and similar, as in the US file); they are single emoji, not joined sequences.
