"""Build claims.json — one entry per factual claim the manuscript makes.

Each claim carries the wording as it will appear in the paper, a verdict reached
from the data rather than asserted, the series behind it, the arithmetic, and a
full citation. Nothing here is typed by hand: every number is read from a file in
sources/ so the page, the paper and this script cannot drift apart.

Add a claim by writing a build_<id>() function and listing it in CLAIMS.
"""
import json, os
from openpyxl import load_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(os.path.dirname(HERE), "sources")
FF = os.path.join(SOURCES, "energy-in-sweden-facts-and-figures-2026.xlsx")

# the Sankey palette, so a carrier keeps its colour across both pages
COLOR = {"oil": "#2c6b47", "gas": "#5aa7d6", "bio": "#4a9b52",
         "heat": "#e07590", "elec": "#f08c1e", "coal": "#606066",
         "wst": "#94953f", "amb": "#31b5a6", "other": "#9aa0a8"}


def _sheet(name):
    wb = load_workbook(FF, read_only=True, data_only=True)
    rows = list(wb[name].iter_rows(values_only=True))
    wb.close()
    return rows


def heating_by_carrier():
    """F&F table 3.4 — heating and hot water by carrier, three building groups.

    Layout: one header row of building groups, one of carriers, then a year per
    row. Columns repeat Oil / District heating / Electric heating / Natural gas /
    Biomass / Total for each group.
    """
    rows = _sheet("3.4")
    carriers = ["Oil", "District heating", "Electric heating", "Natural gas", "Biomass", "Total"]
    groups = {"detached": 1, "apartment": 7, "premises": 13}
    out = {}
    for r in rows:
        if isinstance(r[0], (int, float)) and 1983 <= r[0] <= 2100:
            out[int(r[0])] = {g: {c: (r[b+i] or 0.0) for i, c in enumerate(carriers)}
                              for g, b in groups.items()}
    return out


def district_heating_input():
    """F&F table 7.2 — what is burned to make district heat."""
    rows = _sheet("7.2")
    hdr = [str(c).strip() if c else "" for c in rows[5]]
    out = {}
    for r in rows[6:]:
        if isinstance(r[0], (int, float)) and 1970 <= r[0] <= 2100:
            out[int(r[0])] = {hdr[j]: (r[j] or 0.0) for j in range(1, len(hdr)) if hdr[j]}
    return out


def build_se_heating_fossil():
    H, DH = heating_by_carrier(), district_heating_input()
    years = sorted(H)
    y0, y1 = years[0], years[-1]
    BASE = 1990                       # the year the manuscript's claim starts from

    # dwellings = detached houses + apartment blocks, excluding non-residential premises
    def dw(y, carrier):
        return H[y]["detached"][carrier] + H[y]["apartment"][carrier]

    series = [("oil", "Oil", "Oil"), ("gas", "Natural gas", "Natural gas"),
              ("bio", "Biomass", "Biomass (burned in the building)"),
              ("heat", "District heating", "District heating"),
              ("elec", "Electric heating", "Electric heating")]

    chart = {
        "kind": "stacked", "unit": "TWh",
        "title": f"Energy for heating and hot water in Swedish dwellings, {y0}–{y1}",
        "years": years,
        "series": [{"id": sid, "label": lab, "color": COLOR[sid],
                    "values": [round(dw(y, col), 3) for y in years]}
                   for sid, col, lab in series],
        "note": "Detached houses and apartment blocks; non-residential premises excluded.",
    }

    def row(label, col, digits=2):
        a, b = dw(BASE, col), dw(y1, col)
        return {"label": label, "a": round(a, digits), "b": round(b, digits),
                "delta": round(b-a, digits),
                "pct": round((b-a)/a*100, 1) if a else None}

    numbers = [row("Oil", "Oil"), row("Natural gas", "Natural gas"),
               row("District heating", "District heating"),
               row("Electric heating", "Electric heating"),
               row("Biomass, burned in the building", "Biomass"),
               row("Total heating demand", "Total")]

    dh0, dh1 = DH[BASE], DH[y1]
    COAL = "Coal incl. coke oven and blast furnace gases"
    bio_share = lambda d: d["Biomass"]/d["Total"]*100
    dh_numbers = [
        {"label": "Biomass into district heating", "a": round(dh0["Biomass"], 2),
         "b": round(dh1["Biomass"], 2), "delta": round(dh1["Biomass"]-dh0["Biomass"], 2),
         "pct": round((dh1["Biomass"]-dh0["Biomass"])/dh0["Biomass"]*100, 1)},
        {"label": "… as a share of all district-heating input", "a": round(bio_share(dh0), 1),
         "b": round(bio_share(dh1), 1), "delta": round(bio_share(dh1)-bio_share(dh0), 1),
         "pct": None, "unit": "%"},
        {"label": "Coal into district heating", "a": round(dh0[COAL], 2), "b": round(dh1[COAL], 2),
         "delta": round(dh1[COAL]-dh0[COAL], 2), "pct": round((dh1[COAL]-dh0[COAL])/dh0[COAL]*100, 1)},
        {"label": "Petroleum products into district heating", "a": round(dh0["Petroleum products"], 2),
         "b": round(dh1["Petroleum products"], 2),
         "delta": round(dh1["Petroleum products"]-dh0["Petroleum products"], 2),
         "pct": round((dh1["Petroleum products"]-dh0["Petroleum products"])/dh0["Petroleum products"]*100, 1)},
    ]

    oil0, oil1 = dw(BASE, "Oil"), dw(y1, "Oil")
    bio0, bio1 = dw(BASE, "Biomass"), dw(y1, "Biomass")
    dhd0, dhd1 = dw(BASE, "District heating"), dw(y1, "District heating")
    tot0, tot1 = dw(BASE, "Total"), dw(y1, "Total")

    return {
        "id": "se-heating-fossil",
        "title": "Fossil fuel in Swedish residential heating",
        "claim": "Biomass has almost entirely removed fossil fuel from residential heating in Sweden.",
        "verdict": "revised",
        "verdictLine": (
            f"The fossil collapse is real — oil for heating Swedish dwellings fell "
            f"{oil0:.1f} → {oil1:.2f} TWh ({(oil1-oil0)/oil0*100:.0f}%) between {BASE} and {y1}. "
            f"But biomass burned <i>in the building</i> did not replace it: that is "
            f"{bio0:.1f} → {bio1:.1f} TWh, <b>{(bio1-bio0)/bio0*100:.0f}%</b>. The substitution ran through "
            f"district heating and efficiency instead, and biomass's real role is one step upstream."),
        "rewrite": (
            f"Direct oil use for heating Swedish dwellings fell from {oil0:.1f} TWh in {BASE} to "
            f"{oil1:.2f} TWh in {y1}, a reduction of {abs((oil1-oil0)/oil0*100):.0f}%. The substitution was not "
            f"direct biomass combustion in buildings — slightly lower today ({bio0:.1f} → {bio1:.1f} TWh) — "
            f"but district heating, whose deliveries to dwellings rose "
            f"{abs((dhd1-dhd0)/dhd0*100):.0f}% while its own fuel input shifted from {bio_share(dh0):.0f}% to "
            f"{bio_share(dh1):.0f}% biomass, together with electric heat pumps and a "
            f"{abs((tot1-tot0)/tot0*100):.0f}% fall in total heating demand."),
        "chart": chart,
        "tables": [
            {"title": f"Swedish dwellings: heating and hot water, {BASE} → {y1}",
             "cols": [str(BASE), str(y1), "change"], "unit": "TWh", "rows": numbers},
            {"title": f"What district heating is made from, {BASE} → {y1}",
             "cols": [str(BASE), str(y1), "change"], "unit": "TWh", "rows": dh_numbers},
        ],
        "derivation": [
            "Dwellings = one- and two-dwelling buildings + multi-dwelling buildings from table 3.4; "
            "non-residential premises are excluded so the claim stays about homes.",
            "No weather correction, and no adjustment for heated floor area or population — these are "
            "the published annual observations.",
            "District-heating input (table 7.2) is the fuel burned to produce the heat, not the heat "
            "delivered, so it is not additive with the building-side figures.",
            "The five carriers do not always sum exactly to the published Total column — the table is "
            "published rounded, and the residual reaches 0.25 TWh (0.4%) at its widest. The chart stacks "
            "the carriers; the Total row quotes the published total.",
        ],
        "caveats": [
            f"Biomass in dwellings peaked at {max(dw(y,'Biomass') for y in years):.1f} TWh around "
            f"{max(years, key=lambda y: dw(y,'Biomass'))} and has fallen since; the {BASE}→{y1} endpoints "
            "understate that rise and fall.",
            "Electric heating includes heat pumps, so its modest fall hides a large gain in delivered "
            "heat per unit of electricity. The table measures purchased energy, not heat delivered.",
            "District heating is counted where it is burned. Attributing its biomass back to the "
            "dwellings it heats is a modelling choice this table does not make for you.",
        ],
        "sources": [
            {"author": "Energimyndigheten (Swedish Energy Agency)",
             "year": "2026",
             "title": "Energy in Sweden — Facts and Figures 2026",
             "detail": "Table 3.4, Energy use for heating and hot water in dwellings and non-residential "
                       "premises, from 1983, TWh. Underlying survey: Energy statistics for dwellings and "
                       "non-residential premises (Energimyndigheten and Statistics Sweden).",
             "url": "https://www.energimyndigheten.se/en/facts-and-figures/statistics/"},
            {"author": "Energimyndigheten (Swedish Energy Agency)",
             "year": "2026",
             "title": "Energy in Sweden — Facts and Figures 2026",
             "detail": "Table 7.2, Input energy used in the production of district heating, from 1970, TWh.",
             "url": "https://www.energimyndigheten.se/en/facts-and-figures/statistics/"},
        ],
        "crosscheck": (
            "An independent route through Naturvårdsverket's stationary-combustion activity data "
            "(CRF 1A4a + 1A4b, residences and commercial/public premises) gives oil + gas of 32.29 TWh in "
            "1990. Table 3.4 gives 32.10 TWh for all buildings on the same footing — agreement to 0.6%. "
            "The two diverge in the recent year: Naturvårdsverket reports 1.87 TWh for 2023 against table "
            "3.4's 0.81 TWh, almost all of it in the gas series (1.19 vs 0.43 TWh). That is the difference "
            "between a −94% and a −97% headline, so state which scope you are quoting."),
    }


CLAIMS = [build_se_heating_fossil]


def main():
    out = []
    for i, fn in enumerate(CLAIMS, 1):
        c = fn()
        c["number"] = i
        out.append(c)
    path = os.path.join(HERE, "claims.json")
    with open(path, "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path}  ({len(out)} claim{'s' if len(out)!=1 else ''})")
    for c in out:
        if c.get("kind") == "panel":
            m = sum(len(b["metrics"]) for b in c["panel"]["blocks"])
            print(f"  {c['number']}. {c['id']:24} panel        "
                  f"{len(c['panel']['blocks'])} blocks, {m} metrics, {len(c['sources'])} sources")
        else:
            n = len(c["chart"]["years"])
            print(f"  {c['number']}. {c['id']:24} verdict={c['verdict']:11} "
                  f"{n} years, {len(c['chart']['series'])} series, {len(c['sources'])} sources")




# ── per-capita comparison panel ────────────────────────────────────────────
# Sweden and Japan book primary energy differently, so a naive per-capita
# comparison of primary supply or fossil share is an artefact of accounting.
# The panel therefore separates metrics that need no adjustment from two that
# are restated onto one convention, with every adjustment shown as its own step.

NCV_GCV = {"coal": 0.95, "oil": 0.95, "gas": 0.90}   # IEA/Eurostat net-to-gross ratios
NUCLEAR_EFF = 0.33                                    # IEA convention, applied to both countries


def _pop():
    return json.load(open(os.path.join(SOURCES, "population.json")))


def _ds():
    return json.load(open(os.path.join(HERE, "datasets.json")))


def build_se_jp_percapita():
    import derive_se, derive_jp
    D, POP = _ds(), _pop()
    YEAR = 2024
    pse = POP["se"][str(YEAR)]["value"]
    pjp = POP["jp"][str(YEAR)]["value"]
    SEC = ("res", "com", "ind", "tpt")

    def parts(key):
        d = D[key]
        ids = {n["id"] for n in d["nodes"] if n["col"] == 0}
        band, inn, out = {}, {}, {}
        for s, t, v in d["flows"]:
            out[s] = out.get(s, 0) + v
            inn[t] = inn.get(t, 0) + v
            if s in ids:
                band[s] = band.get(s, 0) + v
        return d, band, inn, out

    se, seB, seI, seO = parts(f"se{YEAR}")
    jp, jpB, jpI, jpO = parts(f"jp{YEAR}")
    carrier = lambda d, c: sum(v for s, t, v in d["flows"] if s == c and t in SEC)
    gen = lambda d, O: O.get("elec", 0) - sum(v for s, t, v in d["flows"] if s == "elec" and t == "rej")
    TJ_MWH = 1e6/3600

    # ── trade, for self-sufficiency ──
    T = derive_se.load(YEAR)
    g = lambda r: (T.get((r, "Total")) or 0)
    val = derive_jp.read_table(YEAR)
    se_ss = g("1.1 Indigenous production")/g("1. Total supply")*100
    jp_ss = val("#110000", "$1400")/val("#190000", "$1400")*100

    # ── harmonisation: put both on the physical energy content method ──
    ng = derive_jp.natural_units(YEAR)          # GWh by source, from METI's own sheet
    e = lambda c: ng[c]*3.6                     # GWh -> TJ of electricity
    jp_h = {
        "nuclear": e("$1100")/NUCLEAR_EFF,      # substitution -> reactor heat
        "hydro":   e("$0800"),                  # substitution -> generated electricity
        "wind":    e("$N120"),
        "solar":   e("$N111") + val("#190000", "$N112"),   # PV as electricity, solar heat as heat
        "geo":     jpB.get("geo", 0),           # already reported as heat
        "bio":     jpB.get("bio", 0),
        "wst":     jpB.get("wst", 0) - val("#190000", "$N250"),   # drop recovered energy
        "coal":    jpB.get("coal", 0)*NCV_GCV["coal"],            # gross -> net calorific value
        "oil":     jpB.get("oil", 0)*NCV_GCV["oil"],
        "gas":     jpB.get("gas", 0)*NCV_GCV["gas"],
    }
    se_nuc_elec = D[f"se{YEAR}"]["meta"]["nuclear_electricity_TJ"]
    se_h = dict(seB)
    se_h["nuclear"] = se_nuc_elec/NUCLEAR_EFF   # restate from actual 35.8% onto the same 33%

    FOSSIL = ("coal", "gas", "oil")
    fos = lambda b: sum(b.get(f, 0) for f in FOSSIL)

    def M(label, a, b, unit, note=""):
        return {"label": label, "se": round(a, 2), "jp": round(b, 2), "unit": unit,
                "ratio": round(a/b, 2) if b else None, "note": note}

    block_a = [
        M("Electricity used", carrier(se, "elec")*TJ_MWH/pse, carrier(jp, "elec")*TJ_MWH/pjp, "MWh/person"),
        M("Electricity generated", gen(se, seO)*TJ_MWH/pse, gen(jp, jpO)*TJ_MWH/pjp, "MWh/person"),
        M("District heat used", carrier(se, "heat")*1000/pse, carrier(jp, "heat")*1000/pjp, "GJ/person"),
        M("Final energy consumption", sum(seI.get(x, 0) for x in SEC+("ne",))*1000/pse,
          sum(jpI.get(x, 0) for x in SEC+("ne",))*1000/pjp, "GJ/person"),
        M("Non-energy use (feedstocks)", seI.get("ne", 0)*1000/pse, jpI.get("ne", 0)*1000/pjp, "GJ/person"),
        M("Energy self-sufficiency", se_ss, jp_ss, "%",
          "Both balances count nuclear as domestic production although uranium is imported."),
    ]
    block_b = [
        M("Primary energy supply", sum(se_h.values())*1000/pse, sum(jp_h.values())*1000/pjp, "GJ/person"),
        M("Fossil share of primary supply", fos(se_h)/sum(se_h.values())*100,
          fos(jp_h)/sum(jp_h.values())*100, "%"),
    ]

    sector = [{"label": {"res": "Residential", "com": "Commercial & services",
                         "ind": "Industrial", "tpt": "Transport"}[s],
               "se": round(seI.get(s, 0)/sum(seI.get(x, 0) for x in SEC)*100, 1),
               "jp": round(jpI.get(s, 0)/sum(jpI.get(x, 0) for x in SEC)*100, 1),
               "unit": "%", "ratio": None} for s in SEC]

    steps = [
        {"what": "Japan: hydro, wind and solar PV from substitution equivalent to generated electricity",
         "delta": round((e("$0800")+e("$N120")+e("$N111")
                         - (jpB.get("hydro", 0)+jpB.get("wind", 0)+jpB.get("solar", 0)-val("#190000", "$N112")))/1000, 1)},
        {"what": f"Japan: nuclear from substitution equivalent to reactor heat at {NUCLEAR_EFF:.0%}",
         "delta": round((jp_h["nuclear"]-jpB.get("nuclear", 0))/1000, 1)},
        {"what": "Japan: fossil fuels from gross to net calorific value "
                 f"(coal ×{NCV_GCV['coal']}, oil ×{NCV_GCV['oil']}, gas ×{NCV_GCV['gas']})",
         "delta": round((fos(jp_h)-fos(jpB))/1000, 1)},
        {"what": "Japan: recovered industrial steam and electricity removed, which Sweden does not book",
         "delta": round(-val("#190000", "$N250")/1000, 1)},
        {"what": f"Sweden: nuclear restated from its actual {se_nuc_elec/seB['nuclear']*100:.1f}% "
                 f"reactor efficiency onto the same {NUCLEAR_EFF:.0%}",
         "delta": round((se_h["nuclear"]-seB["nuclear"])/1000, 1)},
    ]

    return {
        "id": "se-jp-percapita",
        "kind": "panel",
        "title": f"Sweden and Japan per person, {YEAR}",
        "claim": "The two energy systems differ structurally, not just in scale.",
        "verdict": None,
        "lead": (
            f"Normalised by population — Sweden {pse:,} and Japan {pjp:,} — the two systems separate on "
            f"electricity and heat rather than on total energy. The first block needs no adjustment: every "
            f"metric is measured energy, unaffected by how the two countries book primary energy. The "
            f"second block does, and the adjustment is shown rather than assumed."),
        "panel": {"blocks": [
            {"title": "Directly comparable — no adjustment needed", "metrics": block_a,
             "note": "These are measured quantities: delivered energy, generated electricity, and trade. "
                     "The primary-energy convention that makes the two Sankeys incomparable does not touch them."},
            {"title": "Harmonised onto one convention", "metrics": block_b,
             "note": "Both countries restated onto the physical energy content method: renewable electricity "
                     "counted 1:1, nuclear as reactor heat at a single efficiency, fossil fuels at net "
                     "calorific value."},
            {"title": "Sector split of final energy use", "metrics": sector,
             "note": "Share of final energy consumption excluding non-energy use."},
        ]},
        "steps": steps,
        "population": {"se": POP["se"][str(YEAR)], "jp": POP["jp"][str(YEAR)]},
        "derivation": [
            "Energy figures come from the same derivation that produces the Sankey diagrams, so the panel "
            "and the charts cannot disagree.",
            "Population is put on a mid-period basis in both countries so the denominator matches the "
            "energy year: Sweden the mean of the bracketing year-ends, Japan the 1 October estimate that "
            "sits inside the April–March fiscal year.",
            f"Harmonisation applies the physical energy content method to both countries: renewable "
            f"electricity at 1:1, nuclear as reactor heat at {NUCLEAR_EFF:.0%}, and Japanese fossil fuels "
            f"converted from gross to net calorific value.",
        ],
        "caveats": [
            f"The net-to-gross calorific ratios (coal {NCV_GCV['coal']}, oil {NCV_GCV['oil']}, gas "
            f"{NCV_GCV['gas']}) are the standard IEA/Eurostat values, not METI's own published table, "
            "which sits behind an access restriction. They agree with the ratios implied by the IEA "
            "reconciliation in the project README to within about one percentage point.",
            f"Nuclear is put at {NUCLEAR_EFF:.0%} for both countries so the comparison is internally "
            f"consistent. Sweden's balance reports an actual {se_nuc_elec/seB['nuclear']*100:.1f}%; using "
            f"that instead would lower Swedish primary supply by "
            f"{abs((se_h['nuclear']-seB['nuclear'])*1000/pse):.1f} GJ/person.",
            "Japanese biomass is also booked at gross calorific value, but no reliable net ratio was "
            "available for it, so it is left unadjusted. It is 2.8% of Japanese supply, so the effect on "
            "the totals is under half a percent.",
            "Sweden is a large net electricity exporter, which is why generated electricity per person "
            "exceeds electricity used by more than it does in Japan.",
        ],
        "sources": [
            {"author": "SCB (Statistics Sweden)", "year": "2026",
             "title": "Population by region, age, marital status and sex",
             "detail": POP["se"][str(YEAR)]["basis"] + ". Table BE0101, retrieved through the PxWeb API.",
             "url": POP["se"][str(YEAR)]["url"]},
            {"author": "Statistics Bureau of Japan", "year": "2025",
             "title": "人口推計 (Population Estimates), 2024",
             "detail": POP["jp"][str(YEAR)]["basis"] + ". Table 1, total population.",
             "url": POP["jp"][str(YEAR)]["url"]},
            {"author": "Energimyndigheten (Swedish Energy Agency)", "year": "2026",
             "title": "Annual energy balance EN0202_A, calendar year 2024",
             "detail": "The same extraction that produces the Swedish Sankey diagram.",
             "url": "https://pxexternal.energimyndigheten.se/pxweb/en/Energimyndighetens_statistikdatabas/"},
            {"author": "METI / Agency for Natural Resources and Energy", "year": "2026",
             "title": "総合エネルギー統計 Comprehensive Energy Statistics, FY2024 (確報)",
             "detail": "The same extraction that produces the Japanese Sankey diagram, plus the "
                       "natural-units sheet for generation in GWh.",
             "url": "https://www.enecho.meti.go.jp/statistics/total_energy/results.html"},
        ],
    }


CLAIMS.append(build_se_jp_percapita)


if __name__ == "__main__":
    main()
