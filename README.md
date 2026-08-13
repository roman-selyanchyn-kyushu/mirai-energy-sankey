# Energy Flow Sankey Diagrams — Sweden & Japan, 2023 & 2024

Interactive LLNL-style energy flow (Sankey) diagrams for **Sweden** (calendar years 2023 and 2024)
and **Japan** (fiscal years 2023 and 2024), built from official statistics.
Created for the **MIRAI Research Group · Kyushu University**.

**Live page:** <https://roman-selyanchyn-kyushu.github.io/mirai-energy-sankey/>

| File | What it is |
|---|---|
| `energy_sankey.html` | **Main deliverable.** All four datasets, country tabs + year dropdown, PJ/TWh switch, hi-res PNG and SVG export. Self-contained, no external dependencies. |
| `energy_sankey_data.xlsx` | All numbers for all four datasets, with the full derivation trail and balance checks. |
| `scripts/` | The extraction and build pipeline — the authoritative record of how every number was produced. |
| `energy_sankey_2023.html` | Frozen 2023-only earlier version, kept so existing links and citations stay valid. |

---

## 1. Data sources

| Country | Source | Coverage | Unit | Retrieved |
|---|---|---|---|---|
| Sweden | Eurostat [`nrg_bal_c`](https://ec.europa.eu/eurostat/databrowser/view/nrg_bal_c/default/table) (complete energy balances) + [`nrg_bal_peh`](https://ec.europa.eu/eurostat/databrowser/view/nrg_bal_peh/default/table) (electricity & heat production by fuel) | Calendar 2023, 2024 | TJ | Eurostat REST API, dataset update 2 Jun 2026 |
| Japan | METI / ANRE [総合エネルギー統計](https://www.enecho.meti.go.jp/statistics/total_energy/results.html) — Comprehensive Energy Statistics, 確報 (revised), energy-unit balance table (`stte_2023.xlsx`, `stte_2024.xlsx`) | Fiscal 2023, 2024 (Apr–Mar) | TJ | enecho.meti.go.jp |

Both Swedish years are **final** — Eurostat returns no provisional or estimated flags. Eurostat receives
Swedish figures from **Energimyndigheten** (Swedish Energy Agency), so these *are* the Agency's statistics
in Eurostat's harmonised structure. Both Japanese years are the **確報** (final/revised) release.

### Reproducing the raw pulls

Sweden (one call per year; `nrg_bal_peh` is analogous):

```bash
curl "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nrg_bal_c?format=JSON&lang=en&geo=SE&unit=TJ&time=2024&nrg_bal=TI_EHG_E&nrg_bal=FC_IND_E&siec=TOTAL&siec=RA000"
```

Japan (the site requires a browser user-agent and referer):

```bash
curl -L -A "Mozilla/5.0" -e "https://www.enecho.meti.go.jp/statistics/total_energy/results.html" -o stte_2024.xlsx "https://www.enecho.meti.go.jp/statistics/total_energy/xls/stte_2024.xlsx"
```

---

## 2. How the numbers were derived

The whole pipeline is scripted so that the web page, the Excel workbook and this documentation can never
drift apart. Run it with:

```bash
python3 scripts/export.py && python3 scripts/build_html.py && python3 scripts/build_xlsx.py
```

`derive_se.py` and `derive_jp.py` each expose one `derive(year)` function, run identically for every year,
so the two years of each country are guaranteed methodologically consistent.

### 2.1 Sweden — the double-counting trap

Eurostat publishes both *additive* balance components and *attributed memo aggregates*. The memo
aggregates `BIOE` ("Bioenergy") and `FE` ("Fossil energy") include the fuel **embodied in delivered heat
and electricity**, so using them double-counts. The size of the trap, for Swedish households in 2023:

```
BIOE  = 106,436 TJ   ← includes biomass burnt in district-heating plants
RA000 =  34,156 TJ   ← wood actually delivered to households
```

The gap is real: most Swedish district heat is biomass-fired, so `BIOE` re-attributes that fuel to the
household that received the heat. This project therefore uses **only additive components**, verified
against the identity that holds exactly for every sector:

```
E7000 + H8000 + RA000 + O4000XBIO + G3000 + solids  =  TOTAL
142,380 + 112,108 + 34,156 + 5,554 + 972            =  295,170  ✓
```

Bioenergy is taken as the residual of `RA000` after removing the renewable carriers drawn as their own
bands (hydro `RA100+RA130`, wind `RA300`, solar `RA410+RA420`, ambient `RA600`, geothermal `RA500`).

Other Swedish conventions:

- **CHP split** — combustible fuel inputs (`TI_EHG_E`) are divided between the electricity and
  district-heating boxes in proportion to that fuel's gross electricity vs. gross heat output (`nrg_bal_peh`).
- **Ambient heat** — the district-heating share comes from `TI_EHG_E [RA600]`; heat captured by *building*
  heat pumps is reported by Eurostat as non-specified and is allocated **80% residential / 20% commercial**.
  This is the one materially judgemental assumption in the Swedish chart.
- **Industrial waste heat** — Eurostat class `X9900` feeding district heating; input taken equal to output.
- **Commercial & services** = commercial/public services + agriculture, forestry and fishing.
- **Coal & peat** includes manufactured gases (coke-oven, blast-furnace) and peat.
- Marine bunkers excluded (Eurostat convention); international aviation included in transport.

### 2.2 Japan — aggregated bands and city gas

METI's table uses negative values for fuel consumed in transformation and positive for energy produced.
Primary supply is row `#190000` (国内供給), already net of exports.

The subtlety is that each drawn band aggregates a primary and a secondary product (coal + coal products,
crude + oil products, natural gas + city gas). **City gas is manufactured from natural gas** plus roughly
96 PJ of LPG feedstock from the oil band, so naively summing supply and consumption across both columns
counts the same natural gas twice — it inflated the gas band by 163 PJ in testing. The fix is to net the
intra-band product-manufacture rows into each band:

```
band throughput = #190000 + (#210000 + #220000 + #230000 + #280000) + #350000
                  supply    coke ovens, refineries, gas works, transfers   stock change
```

Stock change is included because a stock drawdown is energy genuinely supplied to the system that year.

Other Japanese conventions:

- **Electricity generation** merges utility power (事業用発電, incl. pumped-storage losses) and
  auto-producers (自家用発電, which contains most on-site and rooftop PV).
- **Steam & heat supply** merges industrial auto-steam boilers (自家用蒸気) with the heat-supply
  business (熱供給); most output returns to manufacturing.
- **Sectors** — Industrial = 農林水産鉱建設業 + 製造業; Commercial & services = 業務他. Each is shown net
  of the non-energy use booked inside it, which is drawn as its own terminal.
- **Waste & recovered energy** = 未活用エネルギー (refuse-fired power, waste tyres/plastics, recovered heat).
- **Renewables** split via METI's `$N` detail columns (PV, solar heat, wind, biomass, geothermal).
- **Own use & losses** is each band's residual, so it bundles transformation losses, energy-industry own
  use, transmission losses and the statistical difference — as the LLNL charts do.

Because band widths represent throughput, the bands sum slightly above METI's domestic-supply headline
(17,629 vs 17,558 PJ in FY2023, +0.4%). **Cite METI's headline**, which appears in the methodology panel.

### 2.3 Primary-energy conventions — why band widths are not comparable

**The two countries do not put generating sources on the same basis, and Sweden does not even do so
internally.** This is flagged as a footnote on every chart (marker †) and stated in each methodology panel,
because a reader of the figure would otherwise misread band widths as relative resource size or efficiency.

**Sweden — Eurostat physical energy content method.** Nuclear enters as *reactor heat*; hydro, wind and
solar enter as *generated electricity*. Verified from the balance tables:

| Source | Input to generation (2023 / 2024) | Electricity out | Implied |
|---|---|---|---|
| Nuclear | 484,672 / 506,226 TJ | 174,492 / 182,394 TJ | **36.0%** |
| Hydro | 238,273 / 232,614 TJ | 238,464 / 232,787 TJ | 100% |
| Wind | 123,282 / 146,236 TJ | 123,282 / 146,236 TJ | 100% |
| Solar PV | 11,210 / 14,987 TJ | 11,210 / 14,987 TJ | 100% |

So the nuclear band is ~2.8× the electricity it yields while the renewable bands are 1:1. **Band widths are
therefore not comparable across source types within the Swedish chart**, and the rejected energy leaving the
electricity node reflects this convention rather than the relative efficiency of the sources.

**Japan — METI substitution method.** Every generating source is converted at a *single* reference
efficiency, recovered from METI's own natural-units sheet (GWh × 3.6 ÷ primary energy booked):

| Source | Generated FY2023 | Primary booked | Implied factor |
|---|---|---|---|
| Nuclear | 84,055 GWh | 724,001 TJ | 41.80% |
| Hydro | 75,210 GWh | 647,815 TJ | 41.80% |
| Solar PV | 96,458 GWh | 830,836 TJ | 41.80% |
| Wind | 10,489 GWh | 90,344 TJ | 41.80% |

The factor is 41.80% in FY2023 and 42.41% in FY2024, applied identically to all four. Japan's bands are
therefore **mutually comparable with each other** — unlike Sweden's — but each is about 2.4× the electricity
actually generated. Geothermal is the exception, reported directly as heat.

> **Consequence for the manuscript:** a given amount of wind or solar electricity appears at 1.0× on the
> Swedish chart and about 2.4× on the Japanese one. Never compare band widths, totals or shares between the
> two charts without adjustment.

### 2.4 End use (both countries)

Each sector is split into *energy services* and *rejected energy* using the LLNL efficiency assumptions:
**residential 65%, commercial 65%, industrial 49%, transport 21%**. These are assumptions carried over from
the LLNL convention, **not** measured statistics, and they are the least certain part of both charts.

---

## 3. Verification

Every dataset is checked programmatically; results are in the workbook's **Reconciliation** sheet.

- **Node balance** — all 28 conversion/sector nodes across the four datasets have inputs = outputs to
  within 1 TJ.
- **Headline totals** match the official publications: Japan FY2023 reproduces METI's published
  17,558 PJ supply and 11,509 PJ final consumption exactly; Sweden's gross electricity reproduces
  Eurostat's 597,935 TJ (2023) and 620,521 TJ (2024).
- **Cross-check against the earlier hand-built 2023 chart** — the scripted derivation reproduced it to
  within 0.09% (1,974,645 vs 1,976,328 TJ), which validated both. Two differences were found and the
  scripted version adopted: bioenergy now uses the additive residual rather than `BIOE`, and Japanese
  city-gas power-plant use is read directly from the table rather than allocated proportionally between
  the gas and oil bands.

### Comparison with the IEA energy Sankey

The charts differ from <https://www.iea.org/sankey/> by documented convention, not by data quality.

**Sweden 2023** — IEA total energy supply 1,892 PJ vs 1,975 PJ here. Per fuel the two agree closely
(biofuels & waste 573.5 vs 570.4 PJ; hydro 238.3 vs 238.3; wind+solar+other 177.1 vs 177.1). The
differences are that the IEA imputes a fixed 33% nuclear efficiency (529 PJ) where Eurostat reports actual
reactor heat of ~36% (485 PJ), and the IEA headline nets out net electricity exports (−103 PJ) which this
chart draws explicitly. The IEA's own by-source total is 1,983 PJ — within 0.4% of this chart.

**Japan FY2023** — IEA 15,844 PJ (calendar) vs METI 17,558 PJ (fiscal). The ~1,714 PJ gap decomposes into:

| Driver | Effect |
|---|---|
| Gross (HHV) vs net (LHV) calorific value | ≈ +970 PJ (gas +354, oil +409, coal +204) |
| METI substitution method for hydro/solar/wind (implied factor 41.8%) | ≈ +916 PJ |
| Nuclear convention (METI actual ~38.5% vs IEA fixed 33%) | −193 PJ |
| Geothermal (IEA imputes 10% efficiency) | −93 PJ |
| Recovered energy 未活用エネルギー, counted only by METI | +273 PJ |
| Fiscal vs calendar year, LHV conversion of biomass/waste | ≈ −150 PJ |

A consequence of the substitution method: roughly 0.9 EJ of the rejected energy leaving Japan's electricity
box is an accounting artefact for hydro/solar/wind rather than physical waste heat. LLNL uses the same
convention in its U.S. chart.

> **Do not compare the two countries' totals directly.** METI uses gross calorific value and the
> substitution method; Eurostat uses net calorific value and counts renewable electricity 1:1.

---

## 4. What the data shows

**Sweden 2023 → 2024.** Primary supply +2.5%. Electricity generation rose 166.1 → 172.4 TWh, with wind
+18.6% (34.2 → 40.6 TWh) and solar +32%. The striking change is a **−9.9% fall in biomass against +16% for
oil**, concentrated almost entirely in transport (biofuels 65.9 → 32.6 PJ, oil +45.8 PJ) — the effect of
Sweden cutting its *reduktionsplikt* biofuel blending mandate from January 2024.

**Japan FY2023 → FY2024.** Domestic supply −0.6% and final consumption −2.0%, continuing a downward trend.
Nuclear rose +9.7% (724 → 794 PJ) as reactor restarts continued, while hydro fell −3.4%.

---

## 5. Features of the page

- Country tabs (Sweden / Japan) with an independent **year dropdown** on each
- **PJ ⇄ TWh switch** re-rendering titles, box values, flow labels and footnotes; tooltips always show both
- Year-on-year comparison table under each chart, in the selected unit
- LLNL-style rendering: labelled boxes with values inside, value labels on major flows, pink sector boxes,
  grey Rejected energy / Energy services terminals
- **Hi-res PNG export** at 6240 × 3600 px (4×), white background, print-ready; **SVG export** for Illustrator
- **Comparability footnotes** drawn inside the SVG (so they travel with the exported figure), with markers
  on the affected bands, plus a readable notes card on the page
- Collapsible per-country methodology panel with sources, verified totals, primary-energy conventions and
  the IEA reconciliation
- Single self-contained file — no external libraries, fonts or network calls

## 6. Repository layout

```
energy_sankey.html         published page (generated — edit scripts/template.html, not this)
energy_sankey_data.xlsx    published workbook (generated)
index.html                 redirect so the site root opens the page
scripts/
  derive_se.py             Sweden: Eurostat JSON-stat -> flows + audit trail
  derive_jp.py             Japan: METI xlsx -> flows + audit trail
  export.py                builds all four datasets -> datasets.json
  build_html.py            injects datasets into template.html -> energy_sankey.html
  build_xlsx.py            builds the Excel workbook
  template.html            page source (layout, styling, renderer)
energy_sankey_2023.html    frozen earlier 2023-only version
```

`energy_sankey.html` and `energy_sankey_data.xlsx` are **generated artefacts** — to change the charts,
edit `scripts/template.html` or the derivation scripts and re-run the pipeline.
