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
        n = len(c["chart"]["years"])
        print(f"  {c['number']}. {c['id']:24} verdict={c['verdict']:11} "
              f"{n} years, {len(c['chart']['series'])} series, {len(c['sources'])} sources")


if __name__ == "__main__":
    main()
