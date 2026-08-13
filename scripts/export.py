"""Build the four Sankey datasets (SE/JP x 2023/2024) and emit datasets.json.

Single source of truth: the HTML page and the Excel workbook are both generated from this,
so every published number is identical across deliverables.
"""
import json, os
import derive_se, derive_jp

HERE = os.path.dirname(os.path.abspath(__file__))

# LLNL end-use efficiency assumptions
EFF = {"res": 0.65, "com": 0.65, "ind": 0.49, "tpt": 0.21}

COLORS = {
    "nuclear": "#e0454e", "hydro": "#2268b0", "wind": "#8161d1", "solar": "#f2b21c",
    "geo": "#a2643a", "bio": "#4a9b52", "amb": "#31b5a6", "wh": "#d98a45",
    "wst": "#94953f", "coal": "#606066", "gas": "#5aa7d6", "oil": "#2c6b47",
    "elec": "#f08c1e", "heat": "#e07590", "own": "#a9a9a9",
    "rej": "#c4c4c0", "svc": "#77848f", "ne": "#b3a077", "exp": "#f08c1e",
    "sector": "#f0bac2",
}

LABELS = {
    "se": {"nuclear": "Nuclear", "hydro": "Hydro", "wind": "Wind", "solar": "Solar",
           "bio": "Biomass & biofuels", "amb": "Ambient & recovered heat",
           "wst": "Other fuels & waste", "coal": "Coal & coke", "gas": "Natural gas", "oil": "Oil",
           "elec": "Electricity generation", "heat": "District heating"},
    "jp": {"nuclear": "Nuclear", "hydro": "Hydro", "wind": "Wind", "solar": "Solar",
           "geo": "Geothermal", "bio": "Biomass", "wst": "Waste & recovered energy",
           "coal": "Coal", "gas": "Natural gas & city gas", "oil": "Oil",
           "elec": "Electricity generation", "heat": "Steam & heat supply"},
}
SECTOR_LABEL = {"res": "Residential", "com": "Commercial & services",
                "ind": "Industrial", "tpt": "Transport"}
BAND_ORDER = ["nuclear", "hydro", "wind", "solar", "geo", "bio", "amb", "wh",
              "wst", "coal", "gas", "oil"]

SOURCES = {
    "se": ("Data: Energimyndigheten (Swedish Energy Agency), official annual energy balance, table EN0202_A, "
           "calendar year {year}, terajoules. "
           "End-use efficiency assumptions per LLNL: residential/commercial 65%, industrial 49%, transport 21%."),
    "jp": ("Data: METI Comprehensive Energy Statistics (総合エネルギー統計), Japan, fiscal year {year} "
           "(確報 revised), energy-unit balance table stte_{year}.xlsx. "
           "End-use efficiency assumptions per LLNL: residential/commercial 65%, industrial 49%, transport 21%."),
}
NOTES = {
    "se": ("Only top-level commodities are summed, so the source hierarchy is never double-counted. CHP fuel "
           "is split between electricity and district heating by the plants' own reported output shares. "
           "Ambient heat includes the heat-pump input the national balance does not book as a supply item."),
    "jp": ("Utility and auto-producer generation merged; auto-steam boilers and the heat-supply business merged. "
           "Aggregated bands net out product manufacture inside the band (coke ovens, refineries, gas works), "
           "so natural gas converted to city gas is not counted twice."),
}


# ── comparability footnotes ────────────────────────────────────────────────
# Each entry: marker, the node ids it flags on the chart, and the note text.
# These document places where Sweden and Japan are NOT drawn on the same basis,
# so a reader of the figure is not misled by band widths. Verified against the
# source tables (see scripts/derive_*.py); they hold for both years.
def footnotes(country, ds_flows, meta):
    band_out = {}
    for s, t, v in ds_flows:
        band_out[s] = band_out.get(s, 0) + v
    notes = []

    if country == "se":
        nuc = band_out.get("nuclear", 0) / 1000
        nel = (meta.get("nuclear_electricity_TJ") or 0) / 1000
        eff = (nel / nuc * 100) if nuc else 0
        notes.append({
            "marker": "†", "nodes": ["nuclear"],
            "text": (f"† Primary-energy convention (physical energy content method): nuclear is shown as reactor heat, "
                     f"{nuc:,.0f} PJ, of which {nel:,.0f} PJ ({eff:.1f}%) becomes electricity; hydro, wind and solar are "
                     f"shown as generated electricity (1:1). Band widths are therefore not comparable across source "
                     f"types, and the rejected energy leaving the electricity node reflects this accounting "
                     f"convention rather than the relative efficiency of the sources.")
        })
        msw = (meta.get("biogenic_municipal_waste_TJ") or 0) / 1000
        tbf = (meta.get("transport_biofuel_TJ") or 0) / 1000
        notes.append({
            "marker": "‡", "nodes": ["bio", "wst"],
            "text": (f"‡ Biomass and waste scope: the Swedish balance splits municipal waste, so the biogenic half "
                     f"({msw:,.0f} PJ) sits inside this biomass band while the fossil half sits in other fuels & waste "
                     f"together with peat. Biomass here also includes {tbf:,.0f} PJ of liquid transport biofuels. Japan "
                     f"does not split municipal waste and excludes it from biomass altogether, so neither the biomass "
                     f"nor the waste bands mean the same thing in the two charts.")
        })
    else:
        f = meta.get("primary_equivalent_factor") or 0.418
        notes.append({
            "marker": "†", "nodes": ["nuclear", "hydro", "solar", "wind"],
            "text": (f"† Primary-energy convention (METI substitution method): nuclear, hydro, solar PV and wind are all "
                     f"converted to primary-energy equivalent at one uniform reference efficiency of {f*100:.1f}%, so "
                     f"their band widths are mutually comparable but are about {1/f:.1f}x the electricity actually "
                     f"generated. Geothermal is reported directly as heat. Rejected energy leaving the electricity node "
                     f"therefore includes this accounting artefact rather than only physical losses.")
        })
        rec = (meta.get("recovered_heat_elec_TJ") or 0) / 1000
        ref = (meta.get("refuse_energy_TJ") or 0) / 1000
        lbf = (meta.get("liquid_biofuel_TJ") or 0) / 1000
        notes.append({
            "marker": "‡", "nodes": ["bio", "wst"],
            "text": (f"‡ Biomass and waste scope: biomass here excludes municipal waste, which sits — biogenic and "
                     f"fossil fractions alike, unsplit — in waste & recovered energy ({ref:,.0f} PJ of refuse fuels). "
                     f"That band also holds {rec:,.0f} PJ of recovered industrial steam and electricity, which is not a "
                     f"waste fuel at all. The {lbf:,.0f} PJ of bioethanol is blended upstream and reaches transport "
                     f"inside the oil band, so no biomass flows to transport here. Sweden splits municipal waste and "
                     f"shows transport biofuels within biomass, so neither band means the same thing in the two charts.")
        })

    notes.append({
        "marker": "§", "nodes": [],
        "text": ("§ Cross-country comparison: the Swedish and Japanese charts follow different statistical conventions "
                 "(see † and ‡ above; Sweden also uses net calorific value, Japan gross). Band widths, totals and "
                 "shares must not be compared between the two countries without adjustment — see the methodology panel.")
    })
    return notes


def build(country, year):
    if country == "se":
        flows, audit, meta = derive_se.derive(year)
        flows = [("heat" if s == "dh" else s, "heat" if t == "dh" else t, v) for s, t, v in flows]
        for a in audit:
            a["from"] = "heat" if a["from"] == "dh" else a["from"]
            a["to"] = "heat" if a["to"] == "dh" else a["to"]
    else:
        flows, audit, meta = derive_jp.derive(year)

    # end-use split: each sector into energy services vs rejected energy
    inflow = {}
    for s, t, v in flows:
        inflow[t] = inflow.get(t, 0) + v
    for sec, eff in EFF.items():
        tot = inflow.get(sec, 0)
        if tot <= 0:
            continue
        svc = round(tot * eff)
        flows.append((sec, "svc", svc))
        flows.append((sec, "rej", tot - svc))
        audit.append({"from": sec, "to": "svc", "TJ": svc,
                      "derivation": f"sector input {tot:,} x LLNL end-use efficiency {eff:.0%}"})
        audit.append({"from": sec, "to": "rej", "TJ": tot - svc,
                      "derivation": f"sector input {tot:,} x (1 - {eff:.0%}) end-use losses"})

    present = {s for s, _, _ in flows} | {t for _, t, v in flows}
    nodes = []
    for b in BAND_ORDER:
        if b in present and b in LABELS[country]:
            nodes.append({"id": b, "label": LABELS[country][b], "col": 0, "color": COLORS[b]})
    for c in ("elec", "heat"):
        if c in present:
            nodes.append({"id": c, "label": LABELS[country][c], "col": 1, "color": COLORS[c], "box": True})
    nodes.append({"id": "own", "label": "Own use & losses", "col": 2, "color": COLORS["own"], "box": True})
    for sec in ("res", "com", "ind", "tpt"):
        nodes.append({"id": sec, "label": SECTOR_LABEL[sec], "col": 2,
                      "color": COLORS["sector"], "box": True, "eff": EFF[sec]})
    nodes.append({"id": "ne", "label": "Non-energy use", "col": 2, "color": COLORS["ne"],
                  "box": True, "terminal": True})
    if "exp" in present:
        nodes.append({"id": "exp", "label": "Net electricity export", "col": 3,
                      "color": COLORS["exp"], "box": True, "terminal": True})
    nodes.append({"id": "rej", "label": "Rejected energy", "col": 3, "color": COLORS["rej"],
                  "box": True, "terminal": True})
    nodes.append({"id": "svc", "label": "Energy services", "col": 3, "color": COLORS["svc"],
                  "box": True, "terminal": True})

    cname = "Sweden" if country == "se" else "Japan"
    ylab = str(year) if country == "se" else f"FY{year}"
    return {
        "country": cname, "code": country, "year": year, "yearLabel": ylab,
        "title": f"Estimated Energy Flows in {cname}, {ylab}",
        "file": f"{cname}_Energy_Flow_{ylab}",
        "source": SOURCES[country].format(year=year),
        "note": NOTES[country],
        "nodes": nodes,
        "flows": [[s, t, v] for s, t, v in flows],
        "meta": meta,
        "footnotes": footnotes(country, flows, meta),
        "audit": audit,
    }


def main():
    out = {}
    for c in ("se", "jp"):
        for y in (2023, 2024):
            out[f"{c}{y}"] = build(c, y)
    with open(os.path.join(HERE, "datasets.json"), "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print("dataset            flows   primary(PJ)  elec gen(PJ)  final(PJ)  balanced")
    for k, d in out.items():
        i, o = {}, {}
        for s, t, v in d["flows"]:
            o[s] = o.get(s, 0) + v
            i[t] = i.get(t, 0) + v
        bal = all(abs(i.get(n, 0) - o.get(n, 0)) <= 2 for n in ("elec", "heat", "own", "res", "com", "ind", "tpt"))
        prim = sum(v for s, t, v in d["flows"] if s in BAND_ORDER)
        egen = o.get("elec", 0) - sum(v for s, t, v in d["flows"] if s == "elec" and t == "rej")
        fin = sum(i.get(x, 0) for x in ("res", "com", "ind", "tpt", "ne"))
        print(f"{k:18}{len(d['flows']):>6}{prim/1000:>13,.0f}{egen/1000:>13,.0f}{fin/1000:>11,.0f}   {bal}")


if __name__ == "__main__":
    main()
