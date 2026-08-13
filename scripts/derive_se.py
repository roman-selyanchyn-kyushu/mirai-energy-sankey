"""Derive Sweden Sankey flows from Energimyndigheten's official annual energy balance.

Source: Swedish Energy Agency statistics database (PxWeb), table EN0202_A
"Energy balance, 2005-", in terajoules. This is Sweden's national primary source; Eurostat
republishes the same underlying statistics in a harmonised structure, which shifts some
aggregates (see README section 1).

Run identically for every year so datasets stay methodologically consistent.

Structure of the source table: 96 hierarchical balance rows x 44 energy commodities. Only
TOP-LEVEL commodities are summed into bands, so the hierarchy is never double-counted
(e.g. "1. Biofuels" already contains solid biofuels, bioliquids, biogas and biogenic
municipal waste). Transformation input rows are positive for fuel consumed; transformation
output rows are negative for energy produced.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# ── bands: chart id -> top-level commodity names in EN0202_A ───────────────
BANDS = {
    "nuclear": ["9. Nuclear fuel"],
    "hydro":   ["11. Primary hydro power"],
    "wind":    ["12. Primary wind power"],
    "solar":   ["14. Primary solar power"],
    "bio":     ["1. Biofuels"],                     # incl. bioliquids, biogas, biogenic MSW
    "amb":     ["10.1 Primary heat"],               # ambient/recovered heat into CHP & heat plants
    "wst":     ["8. Other fuels"],                  # peat, non-biogenic waste, other
    "coal":    ["2. Hard coal and brown coal", "3. Coke oven coke",
                "7. Blast-furnace gas, coke-oven gas and oxygen"],
    "gas":     ["6. Natural gas and gaswork gas"],
    "oil":     ["4. Crude oil and refinery feedstocks", "5. Petroleum products"],
}
BAND_LABEL = {"nuclear": "Nuclear", "hydro": "Hydro", "wind": "Wind", "solar": "Solar",
              "bio": "Biomass & biofuels", "amb": "Ambient & recovered heat",
              "wst": "Other fuels & waste", "coal": "Coal & coke", "gas": "Natural gas",
              "oil": "Oil"}
ELEC, HEAT = "13. Electricity", "10.2 Derived heat"

# plant rows feeding each conversion box (CHP is split by its own output shares)
ELEC_PLANTS = ["3.2.1 Hydro power plants", "3.2.2 Wind power plants", "3.2.3 Solar power plants",
               "3.2.4.1 Nuclear power stations", "3.2.4.3 Other thermal power stations"]
HEAT_PLANTS = ["3.2.5 Heat only plants"]
CHP_IN, CHP_OUT = "3.2.4.2 CHP plants", "3.3.4.2 CHP plants"
# fuel-to-fuel transformation; its net loss belongs in own use, not in a conversion box
OTHER_TRANSFORM = ["3.2.6 Gas works", "3.2.7 Coke-oven plants",
                   "3.2.8 Blast-furnace plants", "3.2.9 Refineries"]
SECTORS = {
    "ind": ["3.7.1 Industry", "3.7.2 Construction"],
    "tpt": ["3.7.3 Transport"],
    "res": ["3.7.4.6 Households"],
    "com": ["3.7.4.1 Agriculture", "3.7.4.2 Forestry", "3.7.4.3 Fishing",
            "3.7.4.4 Public administration", "3.7.4.5 Commercial"],
}
SUPPLY = "3. Gross inland consumption"
STAT_DIFF = "2. Statistical difference"
OWN_USE, DIST_LOSS, NON_ENERGY = "3.4 Energy sector own use", "3.5 Distribution losses", "3.6 Non energy use"


def load(year):
    d = json.load(open(os.path.join(HERE, f"se_em_{year}.json")))
    dims, sizes = d["id"], d["size"]
    cat = {k: d["dimension"][k]["category"] for k in dims}
    inv = {k: {v: kk for kk, v in cat[k]["index"].items()} for k in dims}
    lab = {k: cat[k].get("label", {}) for k in dims}

    def un(i):
        o = []
        for s in reversed(sizes):
            o.append(i % s); i //= s
        return list(reversed(o))

    T = {}
    for i, v in enumerate(d["value"]):
        if v is None:
            continue
        c = un(i)
        T[(lab["Balansrad"][inv["Balansrad"][c[2]]],
           lab["Energivara"][inv["Energivara"][c[3]]])] = v
    return T


def derive(year):
    T = load(year)
    flows, audit = [], []

    def cell(row, com):
        return T.get((row, com), 0.0) or 0.0

    def band_sum(rows, fid):
        return sum(cell(r, c) for r in rows for c in BANDS[fid])

    def add(s, t, v, note=""):
        v = round(v)
        if v > 0:
            flows.append((s, t, v))
            audit.append({"from": s, "to": t, "TJ": v, "derivation": note})

    # CHP output shares — the source table reports CHP electricity and heat separately
    chp_e, chp_h = -cell(CHP_OUT, ELEC), -cell(CHP_OUT, HEAT)
    chp_tot = chp_e + chp_h
    e_share = chp_e / chp_tot if chp_tot else 0.0

    # ── 1. fuel bands into the conversion boxes ───────────────────────────
    for fid in BANDS:
        cs = " + ".join(BANDS[fid])
        e_direct = band_sum(ELEC_PLANTS, fid)
        h_direct = band_sum(HEAT_PLANTS, fid)
        chp = band_sum([CHP_IN], fid)
        add(fid, "elec", e_direct + chp * e_share,
            f"EN0202_A transformation input, {'/'.join(p.split()[0] for p in ELEC_PLANTS)} "
            f"[{cs}] plus CHP x electricity share {e_share:.4f}")
        add(fid, "heat", h_direct + chp * (1 - e_share),
            f"EN0202_A transformation input, heat-only plants [{cs}] "
            f"plus CHP x heat share {1-e_share:.4f}")

    # ── 2. direct fuel deliveries to final sectors, non-energy use ────────
    for fid in BANDS:
        cs = " + ".join(BANDS[fid])
        for sec, rows in SECTORS.items():
            add(fid, sec, band_sum(rows, fid), f"EN0202_A {'; '.join(rows)} [{cs}]")
        add(fid, "ne", band_sum([NON_ENERGY], fid), f"EN0202_A {NON_ENERGY} [{cs}]")

    # ── 3. own use and losses: residual of each band ──────────────────────
    for fid in BANDS:
        supply = band_sum([SUPPLY], fid)
        used = sum(v for s, t, v in flows if s == fid)
        add(fid, "own", supply - used,
            f"residual: {SUPPLY} [{' + '.join(BANDS[fid])}] {supply:,.0f} less conversion, final "
            f"and non-energy use — energy-sector own use, distribution and transformation losses")

    # ── 4. electricity box outputs ────────────────────────────────────────
    for sec, rows in SECTORS.items():
        add("elec", sec, sum(cell(r, ELEC) for r in rows), f"EN0202_A {'; '.join(rows)} [{ELEC}]")
    add("elec", "heat", cell(CHP_IN, ELEC) + sum(cell(r, ELEC) for r in HEAT_PLANTS),
        f"EN0202_A transformation input, CHP and heat-only plants [{ELEC}] — heat pumps and boilers")
    # own use + grid losses + the electricity statistical difference (a balancing item,
    # NOT part of net trade: gross inland consumption folds it in, so it is taken separately)
    add("elec", "own",
        cell(OWN_USE, ELEC) + cell(DIST_LOSS, ELEC) + cell(STAT_DIFF, ELEC)
        + cell("3.2.1.2 Pumped storage plants", ELEC),
        f"EN0202_A {OWN_USE} + {DIST_LOSS} + {STAT_DIFF} + pumped-storage consumption [{ELEC}]")
    net_exp = -cell("1. Total supply", ELEC)     # = exports - imports
    add("elec", "exp", net_exp,
        f"EN0202_A exports {-cell('1.3 Exports', ELEC):,.0f} less imports "
        f"{cell('1.2 Imports', ELEC):,.0f} [{ELEC}] — net electricity export")
    e_in = sum(v for s, t, v in flows if t == "elec")
    add("elec", "rej", e_in - sum(v for s, t, v in flows if s == "elec"),
        "conversion losses = box inputs - box outputs (balancing item)")

    # ── 5. district-heating box outputs ───────────────────────────────────
    for sec, rows in SECTORS.items():
        add("heat", sec, sum(cell(r, HEAT) for r in rows), f"EN0202_A {'; '.join(rows)} [{HEAT}]")
    # derived-heat balance closes exactly as: production = final consumption
    # + distribution losses + statistical difference
    add("heat", "own", cell(OWN_USE, HEAT) + cell(DIST_LOSS, HEAT) + cell(STAT_DIFF, HEAT),
        f"EN0202_A {OWN_USE} + {DIST_LOSS} + {STAT_DIFF} [{HEAT}]")
    # Heat-only plants deliver more heat than the energy booked as their input, because
    # the ambient heat that heat pumps draw from air, water and sewage is not booked as a
    # supply item in the national balance. Add that implicit ambient heat so the box closes.
    h_in = sum(v for s, t, v in flows if t == "heat")
    h_out = sum(v for s, t, v in flows if s == "heat")
    if h_out > h_in:
        add("amb", "heat", h_out - h_in,
            "implicit ambient heat: heat-plant output exceeds booked input because the national "
            "balance does not record the ambient heat drawn by heat pumps as a supply item")
        h_in = sum(v for s, t, v in flows if t == "heat")
    add("heat", "rej", h_in - h_out,
        "conversion and distribution losses = box inputs - box outputs (balancing item)")

    add("own", "rej", sum(v for s, t, v in flows if t == "own"),
        "all energy-sector own use and losses are rejected energy")

    meta = {
        "gross_electricity_TJ": round(-cell("3.3 Transformation output", ELEC)),
        "gross_heat_TJ": round(-cell("3.3 Transformation output", HEAT)),
        "net_electricity_export_TJ": round(net_exp),
        "final_consumption_energy_TJ": round(cell("3.7 Final energy consumption", "Total")),
        "non_energy_use_TJ": round(cell(NON_ENERGY, "Total")),
        "nuclear_electricity_TJ": round(-cell("3.3.4.1 Nuclear power stations", ELEC)),
        "biogenic_municipal_waste_TJ": round(cell(SUPPLY, "1.4 Municipal waste -bio")),
        "transport_biofuel_TJ": round(sum(cell(r, "1. Biofuels") for r in SECTORS["tpt"])),
        "chp_electricity_share": round(e_share, 4),
    }
    return flows, audit, meta


if __name__ == "__main__":
    for y in (2023, 2024):
        fl, au, me = derive(y)
        bands = {}
        for s, t, v in fl:
            if s in BAND_LABEL:
                bands[s] = bands.get(s, 0) + v
        inn, out = {}, {}
        for s, t, v in fl:
            out[s] = out.get(s, 0) + v; inn[t] = inn.get(t, 0) + v
        bad = [(n, inn.get(n, 0), out.get(n, 0)) for n in ("elec", "heat", "own")
               if abs(inn.get(n, 0) - out.get(n, 0)) > 2]
        print(f"\n===== SWEDEN {y} (Energimyndigheten) =====  flows: {len(fl)}  balanced: {not bad}")
        if bad:
            print("   IMBALANCE:", bad)
        for k, v in me.items():
            print(f"  {k:34}{v:>12,}" if isinstance(v, int) else f"  {k:34}{v:>12}")
        print(f"  {'primary supply (sum of bands)':34}{sum(bands.values()):>12,}")
        for k, v in sorted(bands.items(), key=lambda x: -x[1]):
            print(f"     {BAND_LABEL[k]:26}{v:>12,}")
