# Fonts: choices, licences, provenance

Built 2026-10-05. Decision (Alex, 2026-10-05): free substitutes now, self-hosted with their licence files, no CDN, no brand fonts; swapping the real fonts in later must be a token change.

## What ships

| Role in the guide | Brand font (not shipped) | Kit font | File | Licence | Source |
|---|---|---|---|---|---|
| Headings, large text | PP Formula Semi Condensed (or Neue Haas Unica W1G Light) | **Archivo** (Omnibus-Type), `wdth` axis pinned at 84, `wght` 300-700 kept, Latin subset | `cw-heading-archivo-w84.woff2` (33 KB) | SIL OFL 1.1 (`OFL-Archivo.txt`); no Reserved Font Name | https://github.com/google/fonts/tree/main/ofl/archivo (`Archivo[wdth,wght].ttf`, Version 2.001), retrieved 2026-10-05; original kept in `_tools/font-sources/` |
| Body | Neue Haas Unica W1G Light | **Inter** (rsms), `opsz` pinned at 14, `wght` 300-700 kept, Latin subset | `cw-body-inter-opsz14.woff2` (56 KB) | SIL OFL 1.1 (`OFL-Inter.txt`); no Reserved Font Name | https://github.com/google/fonts/tree/main/ofl/inter (`Inter[opsz,wght].ttf`, Version 4.001), retrieved 2026-10-05; original in `_tools/font-sources/` |
| Labels, buttons | JetBrains Mono Light | **JetBrains Mono** itself (the brand's own face) | `JetBrainsMono-{Light,Regular,Medium,Bold}.woff2` | SIL OFL 1.1 (`OFL-JetBrainsMono.txt`, `AUTHORS-JetBrainsMono.txt`) | Copied unchanged from `Work Documentation/Production/Design/Fonts/JetBrainsMono-2.304/` |

Transformations (done by `_tools/build_fonts.py`, no network): subset to Basic Latin, Latin-1, general punctuation, arrows, minus, euro; axes pinned as above; woff2 compression. Licence compliance: OFL allows modification and web embedding provided the licence text travels with the fonts (it does, in this folder) and the font is not sold alone. The fonts are loaded under the CSS names "CW Heading" and "CW Body".

## How the choice was made

Method: the brand fonts exist only as desktop files in `Work Documentation/Production/Design/Fonts/` (not licensed for web, and not shipped). I measured their metrics from those files (measurement only), set candidate open fonts beside crops of the archived live-site screenshots (`analysis/sources/site/`), and compared widths, heights and weight by eye. Comparison sheets are in `comparison/`.

Measured, in em (read from the font files):

| | x-height | cap height | average advance (sample text) |
|---|---|---|---|
| PP Formula Semi Condensed (desktop file) | 0.650 | 0.816 | 0.499 |
| Neue Haas Unica Pro Light (desktop file) | 0.508 | 0.712 | 0.470 |
| Archivo (width 100 / 87 / 75) | 0.526 | 0.686 | 0.479 / 0.429 / 0.379 |
| Inter | 0.516 | 0.728 | 0.466 |
| Others tried: Barlow Semi Condensed, Sofia Sans Semi Condensed, IBM Plex Sans Condensed, Saira Semi Condensed, Instrument Sans, Bricolage Grotesque, Archivo Narrow, Hanken Grotesk, Albert Sans, Figtree, Public Sans | see `comparison/candidates-*.png` | | |

Why Archivo for headings: PP Formula is not very condensed in width; it is a tall-x-height grotesque set with very tight tracking (-4.8px at 102px on the site). Ordinary condensed fonts (Barlow, Saira, Plex Condensed, Sofia) come out too narrow and too short at the same size. Archivo has a real width axis, so I could dial in a semi-condensed width (84) and then scale the face up with `size-adjust: 119%` so cap height lands close to PP Formula's (0.686 x 1.19 = 0.82 vs 0.816; x-height 0.63 vs 0.65). With weight 350, the same tracking as the site, the hero word, card titles and line breaks track the live site closely (`comparison/final-vs-site.png`: top row is the site, bottom row is the kit).

Why Inter for body: its metrics are nearly identical to Neue Haas Unica Pro Light (x-height 0.516 vs 0.508, advance 0.466 vs 0.470), it has a proper Light weight, tabular numerals, and it is a neo-grotesque like Unica. Tracking of +0.012em (`--tracking-body`) compensates for Inter running about 1% narrower.

Where it falls short (candid): Archivo is chunkier than PP Formula at the same weight and lacks PP Formula's single-storey curved "y" and quirky "g". Inter is a little more mechanical than Unica and its "a", "t" and "1" differ. This is a stand-in, close in size and rhythm, not a lookalike at a glance. The CSS keeps `size-adjust` on the heading face only; the body face needs none.

## Swapping in the real fonts later (a token change)

1. Confirm web licences (open question in TRAILHEAD.md): PP Formula (Pangram Pangram), Neue Haas Unica W1G (Monotype or the Adobe Fonts kit).
2. In `css/cw-fonts.css` add `@font-face` rules for the real families (without `size-adjust`).
3. In `css/cw-tokens.css` change `--font-heading` and `--font-body` to name them first, set `--weight-heading: 400` and `--tracking-body: 0`.
Nothing else in the kit names a font family. Delete the unused stand-in files afterwards.
