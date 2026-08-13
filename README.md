# Energy Flow Sankey Diagrams — Sweden & Japan, 2023 & 2024

Interactive LLNL-style energy flow (Sankey) diagrams for **Sweden** (calendar years 2023 and 2024)
and **Japan** (fiscal years 2023 and 2024), built from official statistics.
Created for the **MIRAI Research Group · Kyushu University**.

**Live page:** <https://roman-selyanchyn-kyushu.github.io/mirai-energy-sankey/>

| File | What it is |
|---|---|
| `energy_sankey.html` | **Main deliverable.** All four datasets, country tabs + year dropdown, PJ/TWh switch, hi-res PNG and SVG export. Self-contained, no external dependencies. |
| `energy_sankey_data.xlsx` | All numbers for all four datasets, with the full derivation trail and balance checks. |
| `scripts/` | The extraction and build pipeline — the authoritative record of how every number was produced. `derive_se.py` reads the Swedish PxWeb API, `derive_jp.py` the METI workbook. |
| `energy_sankey_2023.html` | Frozen 2023-only earlier version, kept so existing links and citations stay valid. |

---

## 1. Data sources

| Country | Source | Coverage | Unit | Retrieved |
|---|---|---|---|---|
| Sweden | **Energimyndigheten** (Swedish Energy Agency), official annual energy balance [`EN0202_A`](https://pxexternal.energimyndigheten.se/pxweb/en/Energimyndighetens_statistikdatabas/) "Energy balance, 2005–" | Calendar 2023, 2024 | TJ | PxWeb API, table updated 30 Apr 2026 |
| Japan | METI / ANRE [総合エネルギー統計](https://www.enecho.meti.go.jp/statistics/total_energy/results.html) — Comprehensive Energy Statistics, 確報 (revised), energy-unit balance table (`stte_2023.xlsx`, `stte_2024.xlsx`) | Fiscal 2023, 2024 (Apr–Mar) | TJ | enecho.meti.go.jp |

Both countries are drawn from their **national primary source**. Both Japanese years are the **確報**
(final/revised) release.

### Relationship to Eurostat

Earlier versions of these charts used Eurostat, which republishes the Swedish statistics in a harmonised
structure. The charts now use the Agency's own balance directly, at a Swedish collaborator's request and
because it makes the sourcing symmetric with METI for Japan. The two differ as follows:

| Quantity (2023) | Energimyndigheten (used here) | Eurostat | Diff |
|---|---|---|---|
| **Nuclear electricity** | 174,492 TJ | 174,492 TJ | **0.00%** |
| Gross electricity, total | 597,188 TJ | 597,935 TJ | −0.12% |
| Hydro / wind / solar electricity | 237,927 / 122,669 / 11,167 | 238,464 / 123,282 / 11,210 | −0.2 to −0.5% |
| Nuclear reactor heat | 488,248 TJ | 484,672 TJ | +0.74% |
| Gross derived heat | 220,352 TJ | 217,869 TJ | +1.14% |
| Final energy consumption | 1,271,729 TJ | 1,301,927 TJ | −2.32% |
| Non-energy use | 73,178 TJ | 77,313 TJ | −5.35% |

**Nuclear electricity matches exactly** (to 1 TJ in both years), confirming common origin. The remaining
gaps are harmonisation, not disagreement: Eurostat implies a 36.00% nuclear thermal efficiency where the
Agency reports ~35.74%, and the two differ in the scope of derived heat, final consumption and non-energy
use. The largest single cause of the final-consumption gap is **ambient heat** — Eurostat books ~63 PJ
captured by building heat pumps as final consumption, which the national balance does not record at all.
Charts published before August 2026 used the Eurostat figures and therefore differ by the amounts above.

### Reproducing the raw pulls

Sweden — PxWeb POST query against table `EN0202_A` (year 19 = 2024, unit 3 = TJ):

```bash
curl -X POST -H "Content-Type: application/json" -d '{"query":[{"code":"År","selection":{"filter":"item","values":["19"]}},{"code":"Enhet","selection":{"filter":"item","values":["3"]}}],"response":{"format":"json-stat2"}}' "https://pxexternal.energimyndigheten.se/api/v1/en/Energimyndighetens_statistikdatabas/Officiell_energistatistik/Arlig_energibalans/Balanser/EN0202_A.px"
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

### 2.1 Sweden — national balance structure

The source table is **96 hierarchical balance rows × 44 energy commodities**. Only **top-level commodities**
are summed into bands (`1. Biofuels`, `4. Crude oil…`, `9. Nuclear fuel`, …), so the hierarchy is never
double-counted — `1. Biofuels` already contains solid biofuels, bioliquids, biogas and biogenic municipal
waste. Transformation input rows are positive for fuel consumed, output rows negative for energy produced.

- **CHP split** — combined heat and power plants report electricity and heat output separately, so their
  fuel input is divided by the plants' *actual* output shares (26.6% electricity in 2023, 24.5% in 2024)
  rather than by an assumption. This is more direct than the Eurostat-based approach it replaced.
- **Ambient & recovered heat** — the balance books 18.9 PJ (2023) of primary heat into CHP and heat-only
  plants. Swedish heat-only plants deliver *more* heat than their booked fuel input, because the ambient
  heat drawn by heat pumps from air, water and sewage is not recorded as a supply item; that implicit
  ambient heat (4.8 PJ in 2023) is added so the box closes. Unlike Eurostat, the national balance does
  **not** count ambient heat captured by *building* heat pumps at all, so none reaches the final sectors.
- **Sectors** — Industrial = industry + construction; Commercial & services = commercial, public
  administration, agriculture, forestry and fishing.
- **Own use & losses** is each band's residual, bundling energy-sector own use, distribution losses,
  refinery/coke-oven/blast-furnace losses, pumped-storage consumption and the statistical difference.
- **Oil** combines crude oil and refinery feedstocks with petroleum products; Sweden is a net exporter of
  refined products, so the band is net of that trade.
- **Net electricity export** is exports − imports (102,650 TJ in 2023), *not* gross inland consumption,
  which folds in the 11,052 TJ electricity statistical difference — that is routed to own use & losses.

Both conversion boxes reconcile to the Agency's published production figures to within 2 TJ (0.000%):
gross electricity 597,188 TJ and derived heat 220,352 TJ in 2023.

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

**Sweden — physical energy content method.** Nuclear enters as *reactor heat*; hydro, wind and
solar enter as *generated electricity*. Verified from the national balance:

| Source | Input to generation (2023 / 2024) | Electricity out | Implied |
|---|---|---|---|
| Nuclear | 488,248 / 510,026 TJ | 174,492 / 182,395 TJ | **35.7%** |
| Hydro | 237,927 / 232,337 TJ | 237,927 / 232,337 TJ | 100% |
| Wind | 122,669 / 145,508 TJ | 122,669 / 145,508 TJ | 100% |
| Solar | 11,167 / 14,928 TJ | 11,167 / 14,928 TJ | 100% |

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

### 2.4 Biomass and waste scope — also not comparable

The biomass bands (Sweden 533 PJ, Japan 502 PJ in 2023) look similar but count different things.
Flagged on both charts as footnote ‡.

**Sweden** — the national balance *splits municipal waste* into a biogenic and a fossil half:

| Inside the biomass band (`1. Biofuels`) | 2023 | 2024 |
|---|---|---|
| Solid biofuels (wood fuels, black liquor, other) | 397,749 TJ | — |
| **Biogenic municipal waste (`1.4 Municipal waste -bio`)** | 36,222 TJ | 36,399 TJ |
| Bioliquids (bioethanol, biodiesel, biooils) | 94,839 TJ | — |
| Biogas | 9,612 TJ | — |
| … of which delivered to transport | 70,663 TJ | 38,249 TJ |

The fossil half of municipal waste sits with peat in the separate *Other fuels & waste* band
(`8. Other fuels`, 55.4 PJ in 2023).

**Japan** — METI does **not** split municipal waste, and keeps all of it out of biomass:

| Band | Contents | FY2023 |
|---|---|---|
| Biomass (`$N130`) | wood 179.6, waste wood 42.1, black liquor 141.6, other 118.9, liquid biofuel 19.8, biogas 0.1 PJ | 502,061 TJ |
| Waste & recovered (`$N200`) | refuse fuels — biogenic *and* fossil together, unsplit | 282,074 TJ |
| … of which **not a waste fuel at all** | recovered industrial steam 218.5 + recovered electricity 52.1 PJ | 273,020 TJ |

Three consequences:

1. **Waste-to-energy sits on opposite sides.** Sweden's biomass includes 36 PJ of biogenic municipal
   waste; Japan's excludes municipal waste entirely.
2. **Japan's waste band is half not-waste.** 273 of its 555 PJ is recovered industrial steam and
   electricity. The Swedish balance has no equivalent item at all — recovered heat appears only as the
   18.9 PJ of primary heat entering CHP and heat-only plants.
3. **Transport biofuels are invisible in Japan.** Sweden shows 71 PJ (2023) of biomass flowing to
   transport. Japan's ~20 PJ of bioethanol is blended upstream (into ETBE/gasoline) and reaches transport
   inside the *oil* band — `#800000 [$N133]` is exactly zero — so Japan's chart shows no biomass to transport.

Removing biogenic waste from Sweden's band gives 502 PJ against Japan's 502 PJ. **That closeness is a
coincidence of composition, not evidence of comparability.**

### 2.5 End use (both countries)

Each sector is split into *energy services* and *rejected energy* using the LLNL efficiency assumptions:
**residential 65%, commercial 65%, industrial 49%, transport 21%**. These are assumptions carried over from
the LLNL convention, **not** measured statistics, and they are the least certain part of both charts.

---

## 3. Verification

Every dataset is checked programmatically; results are in the workbook's **Reconciliation** sheet.

- **Node balance** — all 28 conversion/sector nodes across the four datasets have inputs = outputs to
  within 1 TJ.
- **Headline totals** match the official publications: Japan FY2023 reproduces METI's published
  17,558 PJ supply and 11,509 PJ final consumption exactly; Sweden's conversion boxes reconcile to the
  Agency's published gross electricity (597,188 TJ in 2023, 619,653 in 2024) and derived heat
  (220,352 / 213,120 TJ) to within 2 TJ.
- **Source migration check** — when Sweden moved from Eurostat to the national balance, nuclear
  electricity was confirmed identical between the two (174,492 TJ in 2023, to 1 TJ), and every other
  difference was traced to a documented harmonisation effect rather than an error (see section 1).

### Comparison with the IEA energy Sankey

The charts differ from <https://www.iea.org/sankey/> by documented convention, not by data quality.

**Sweden 2023** — IEA total energy supply 1,892 PJ vs 1,951 PJ here. Per fuel the two agree closely
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
> substitution method; the Swedish balance uses net calorific value and counts renewable electricity 1:1.

---

## 4. What the data shows

**Sweden 2023 → 2024.** Primary supply +1.9%. Electricity generation rose 165.9 → 172.1 TWh, with wind
+18.6% (34.1 → 40.4 TWh) and solar +34%. The striking change is a **−9.9% fall in biomass against +16% for
oil**, concentrated almost entirely in transport (biofuels to transport 70.7 → 38.2 PJ) — the effect of
Sweden cutting its *reduktionsplikt* biofuel blending mandate from January 2024.

**Japan FY2023 → FY2024.** Domestic supply −0.6% and final consumption −2.0%, continuing a downward trend.
Nuclear rose +9.7% (724 → 794 PJ) as reactor restarts continued, while hydro fell −3.4%.

---

## 5. Features of the page

- Country tabs (Sweden / Japan) with an independent **year dropdown** on each
- **Click-to-trace**: clicking any box dims the rest of the chart and keeps only the flows touching that
  box, with a breakdown table underneath giving each flow's value and its share of the box's total
  (both directions for the conversion boxes). Clicking a ribbon selects the box it leaves from; clicking
  empty canvas, the Clear button or <kbd>Esc</kbd> releases it. The selection survives unit and year
  changes. The dimming is applied in CSS only, so **exports are always the complete chart**
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
  derive_se.py             Sweden: Energimyndigheten PxWeb -> flows + audit trail
  derive_jp.py             Japan: METI xlsx -> flows + audit trail
  export.py                builds all four datasets -> datasets.json
  build_html.py            injects datasets into template.html -> energy_sankey.html
  build_xlsx.py            builds the Excel workbook
  template.html            page source (layout, styling, renderer)
energy_sankey_2023.html    frozen earlier 2023-only version
```

`energy_sankey.html` and `energy_sankey_data.xlsx` are **generated artefacts** — to change the charts,
edit `scripts/template.html` or the derivation scripts and re-run the pipeline.
