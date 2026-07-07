# Energy Flow Sankey Diagrams — Sweden & Japan 2023

Interactive LLNL-style energy flow (Sankey) diagrams for **Sweden (calendar 2023)** and
**Japan (fiscal 2023)**, built as a single self-contained HTML file with no external
dependencies. Created for the **MIRAI Research Group · Kyushu University**.

**Main file: `energy_sankey_2023.html`** — open directly in any modern browser.
(`llnl_sankey.html` is the earlier draft, kept for reference; its data was **not** verified
and contains substantial errors — e.g. Swedish hydro was ~2.4× too high.)

---

## Data sources (verified July 2026)

| Country | Source | Period | Unit |
|---------|--------|--------|------|
| Sweden  | Eurostat `nrg_bal_c` (complete energy balances) + `nrg_bal_peh` (electricity & heat production by fuel), retrieved via the Eurostat API, dataset update 2 Jun 2026 | Calendar 2023 | TJ |
| Japan   | METI 総合エネルギー統計 FY2023 確報 (revised), energy-unit balance table `stte_2023.xlsx` from enecho.meti.go.jp | FY2023 (Apr 2023 – Mar 2024) | TJ |

### Verification highlights

**Sweden 2023** — every box closes exactly against Eurostat:
- Gross electricity 597,935 TJ = 166.1 TWh (nuclear 48.5, hydro 66.2, wind 34.2, solar 3.1, bio 11.7, fossil 2.3 TWh)
- Electricity: 597,935 = 433,141 (sectors) + 102,571 (net export, 28.5 TWh) + 55,966 (own use & grid) + 6,257 (to DH heat pumps)
- District heat: 217,869 = 192,612 (sectors) + 25,257 (own use & distribution losses)
- Final energy consumption 1,301,926 TJ (energy use); 1,379,239 TJ incl. non-energy use

**Japan FY2023** — every box closes exactly against the METI balance table:
- Domestic primary supply 17,557,652 TJ; final consumption 11,509,459 TJ (matches METI press release: 17,575 / 11,515 PJ pre-revision)
- Electricity (utility + auto-producers, net of pumping) 3,565,033 TJ ≈ 990 TWh
  = 3,150,952 (sectors) + 194,699 (own use) + 175,617 (T&D) + 3,629 (to heat) + 40,136 (stat. difference)

### Comparison with IEA (iea.org/sankey)

The in-page methodology panels include a full reconciliation against the IEA energy Sankey.
Summary: Sweden agrees with IEA within 0.3% per fuel (differences: IEA's fixed 33% nuclear
convention and netting of electricity exports in the headline TES). Japan's METI figure is
1,714 PJ above IEA's TES; the gap decomposes exactly into gross vs. net calorific value (≈ +970 PJ),
METI's substitution method for hydro/solar/wind (≈ +916 PJ, offset by nuclear −193 and geothermal
−93), recovered energy counted only by METI (+273 PJ), and fiscal- vs. calendar-year timing.

---

## Chart structure (LLNL convention)

```
PRIMARY SUPPLY → CONVERSION (Electricity / Heat) → FINAL SECTORS → END USE
```

- **Fuel bands** (col 1): per-fuel domestic supply. Sweden additionally shows ambient heat
  (heat pumps) and industrial waste heat; Japan shows 未活用エネルギー (waste & recovered energy).
- **Conversion boxes** (col 2): Electricity generation; District heating (SE) / Steam & heat supply (JP).
- **Final sectors** (col 3): Residential, Commercial & services, Industrial, Transport,
  plus **Non-energy use** (feedstocks) and **Own use & losses** (energy-industry own use,
  refinery/coke losses, T&D, statistical difference).
- **End use** (col 4): Energy services vs. Rejected energy, using LLNL end-use efficiencies
  (residential/commercial 65%, industrial 49%, transport 21%); Sweden adds Net electricity export.

Key modelling assumptions (full details in the in-page methodology panels):
- SE: CHP fuel inputs split between electricity and district heat pro rata to each fuel's outputs;
  building-heat-pump ambient heat allocated 80/20 residential/commercial.
- JP: utility and auto-producer generation merged; auto-steam boilers + heat-supply business merged
  into one heat box; city-gas LPG feed (~163 PJ) allocated to the oil band.

---

## Features

- LLNL-style rendering: labelled boxes with values inside, value labels on major flows,
  pink sector boxes, gray Rejected energy / Energy services terminals
- **PJ ⇄ TWh unit switch** — re-renders both charts, titles and footnotes; tooltips always show both units
- Uniform headline for both countries: primary supply · electricity generated · final consumption
- Tabs for Sweden / Japan, hover tooltips on every flow and node
- **Download hi-res PNG** — 6240 × 3600 px (4×), white background, print-ready
- **Download SVG** — vector, for editing in Illustrator/Inkscape
- Collapsible "Data sources, verification & methodology" panel per country with source links
  and an IEA reconciliation section
- Single file, no external libraries or fonts; SVG text uses system fonts so exports are pixel-identical

## Implementation notes

All flow values are hard-coded in TJ in the `DATA` object (directly traceable to the sources above);
sector → services/rejected flows are derived from the LLNL efficiencies at load time. A small generic
layout engine stacks nodes per column, orders ribbons to minimise crossings, and resolves label
collisions in the left column. PNG export serialises the SVG to a blob and rasterises it via canvas.
