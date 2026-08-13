"""Derive Sweden Sankey flows from Eurostat energy balances (nrg_bal_c + nrg_bal_peh).

Run identically for every year so datasets stay methodologically consistent. Values in TJ.

IMPORTANT — only ADDITIVE balance components are used. Eurostat also publishes attributed
memo aggregates (BIOE "Bioenergy", FE "Fossil energy") which include the fuel embodied in
delivered heat/electricity; using those would double-count. Verified additive identity for
every final-consumption sector:  E7000 + H8000 + RA000 + O4000XBIO + G3000 + solids = TOTAL.
Bioenergy is therefore taken as the residual of RA000 after removing the renewable carriers
that are drawn as their own bands (hydro, wind, solar, ambient, geothermal).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    d = json.load(open(os.path.join(HERE, path)))
    dims, sizes = d["id"], d["size"]
    i2c = {dim: {v: k for k, v in d["dimension"][dim]["category"]["index"].items()} for dim in dims}

    def unflat(f):
        out = []
        for s in reversed(sizes):
            out.append(f % s); f //= s
        return list(reversed(out))

    res = {}
    for k, v in d["value"].items():
        c = unflat(int(k))
        codes = {dims[i]: i2c[dims[i]][c[i]] for i in range(len(dims))}
        res.setdefault(codes["nrg_bal"], {})[codes["siec"]] = v
    return res


# renewable carriers drawn as their own bands; bio = RA000 minus these
RA_SPLIT = {"hydro": ["RA100", "RA130"], "wind": ["RA300"],
            "solar": ["RA410", "RA420"], "amb": ["RA600"], "geo": ["RA500"]}
FOSSIL = {
    "coal": ["C0000X0350-0370", "C0350-0370", "P1000"],
    "gas":  ["G3000"],
    "oil":  ["O4000XBIO"],
    "wst":  ["W6100_6220"],
    "nuclear": ["N900H"],
}
ELEC_ONLY = {"nuclear", "hydro", "wind"}
SECTORS = {"res": ["FC_OTH_HH_E"],
           "com": ["FC_OTH_CP_E", "FC_OTH_AF_E", "FC_OTH_FISH_E"],
           "ind": ["FC_IND_E"],
           "tpt": ["FC_TRA_E"]}
BAND_LABEL = {"nuclear": "Nuclear", "hydro": "Hydro", "wind": "Wind", "solar": "Solar",
              "geo": "Geothermal", "bio": "Biomass & biofuels", "amb": "Ambient heat",
              "wh": "Industrial waste heat", "wst": "Non-renewable waste",
              "coal": "Coal & peat", "gas": "Natural gas", "oil": "Oil"}


def derive(year, amb_split=(0.8, 0.2)):
    bal = load(f"se_bal_{year}.json")
    peh = load(f"se_peh_{year}.json")
    flows, audit = [], []

    def g(tbl, b, siecs):
        row = tbl.get(b, {})
        return sum(row.get(s, 0.0) or 0.0 for s in siecs)

    def bio_of(b):
        """Bioenergy = RA000 minus the renewable carriers shown as their own bands."""
        return g(bal, b, ["RA000"]) - sum(g(bal, b, codes) for codes in RA_SPLIT.values())

    def band(b, fid):
        if fid == "bio":
            return bio_of(b)
        if fid in RA_SPLIT:
            return g(bal, b, RA_SPLIT[fid])
        return g(bal, b, FOSSIL[fid])

    def src(fid):
        if fid == "bio":
            return "RA000 - (hydro+wind+solar+ambient+geothermal)"
        return "+".join(RA_SPLIT[fid] if fid in RA_SPLIT else FOSSIL[fid])

    def add(s, t, v, note=""):
        v = round(v)
        if v > 0:
            flows.append((s, t, v))
            audit.append({"from": s, "to": t, "TJ": v, "derivation": note})

    BANDS = ["nuclear", "hydro", "wind", "solar", "geo", "bio", "amb", "wst", "coal", "gas", "oil"]

    # ── 1. fuel inputs to the conversion boxes (CHP split by gross output shares) ──
    for fid in BANDS:
        ti = band("TI_EHG_E", fid)
        if ti <= 0:
            continue
        if fid in ELEC_ONLY:
            add(fid, "elec", ti, f"nrg_bal_c TI_EHG_E [{src(fid)}] — electricity-only carrier")
            continue
        if fid == "amb":
            add(fid, "dh", ti, "nrg_bal_c TI_EHG_E [RA600] — large heat pumps in district heating")
            continue
        if fid == "bio":
            gep = g(peh, "GEP", ["RA000"]) - sum(g(peh, "GEP", c) for c in RA_SPLIT.values())
            ghp = g(peh, "GHP", ["RA000"]) - sum(g(peh, "GHP", c) for c in RA_SPLIT.values())
        else:
            siecs = RA_SPLIT.get(fid) or FOSSIL[fid]
            gep, ghp = g(peh, "GEP", siecs), g(peh, "GHP", siecs)
        tot = gep + ghp
        if tot <= 0:
            add(fid, "dh", ti, f"nrg_bal_c TI_EHG_E [{src(fid)}] — no generation split, to heat")
            continue
        sh = gep / tot
        add(fid, "elec", ti * sh,
            f"TI_EHG_E [{src(fid)}] {ti:,.0f} x GEP share {sh:.4f} (CHP split, nrg_bal_peh)")
        add(fid, "dh", ti * (1 - sh),
            f"TI_EHG_E [{src(fid)}] {ti:,.0f} x GHP share {1-sh:.4f} (CHP split, nrg_bal_peh)")

    # recovered industrial/flue-gas heat into district heating (input = output)
    wh = g(peh, "GHP", ["X9900"])
    add("wh", "dh", wh, "nrg_bal_peh GHP [X9900] — recovered heat, input taken equal to output")

    # ── 2. direct fuel deliveries to final sectors ────────────────────────
    for fid in BANDS:
        if fid == "amb":
            continue
        for sec, bls in SECTORS.items():
            add(fid, sec, sum(band(b, fid) for b in bls),
                f"nrg_bal_c {'+'.join(bls)} [{src(fid)}]")

    # ambient heat from building heat pumps (Eurostat reports it as non-specified)
    amb_fc = sum(band(b, "amb") for bls in SECTORS.values() for b in bls) + band("FC_OTH_NSP_E", "amb")
    add("amb", "res", amb_fc * amb_split[0], f"nrg_bal_c ambient heat in final consumption x {amb_split[0]:.0%}")
    add("amb", "com", amb_fc * amb_split[1], f"nrg_bal_c ambient heat in final consumption x {amb_split[1]:.0%}")

    # ── 3. non-energy use and energy-branch own use ───────────────────────
    for fid in BANDS:
        add(fid, "ne", band("FC_NE", fid), f"nrg_bal_c FC_NE [{src(fid)}]")
        if fid != "amb":
            add(fid, "own", band("NRG_E", fid) + band("DL", fid),
                f"nrg_bal_c NRG_E + DL [{src(fid)}]")

    # ── 4. electricity box outputs ────────────────────────────────────────
    E, H = ["E7000"], ["H8000"]
    for s, bls in SECTORS.items():
        add("elec", s, sum(g(bal, b, E) for b in bls), f"nrg_bal_c {'+'.join(bls)} [E7000]")
    add("elec", "dh", g(bal, "TI_EHG_E", E), "nrg_bal_c TI_EHG_E [E7000] — heat pumps in district heating")
    add("elec", "own", g(bal, "NRG_E", E) + g(bal, "DL", E), "nrg_bal_c NRG_E + DL [E7000] — own use + grid losses")
    net_exp = g(bal, "EXP", E) - g(bal, "IMP", E)
    if net_exp > 0:
        add("elec", "exp", net_exp, "nrg_bal_c EXP - IMP [E7000] — net electricity export")
    ein = sum(f[2] for f in flows if f[1] == "elec")
    add("elec", "rej", ein - sum(f[2] for f in flows if f[0] == "elec"),
        "conversion losses = box inputs - box outputs (balancing item)")

    # ── 5. district-heat box outputs ──────────────────────────────────────
    for s, bls in SECTORS.items():
        add("dh", s, sum(g(bal, b, H) for b in bls), f"nrg_bal_c {'+'.join(bls)} [H8000]")
    add("dh", "own", g(bal, "NRG_E", H) + g(bal, "DL", H), "nrg_bal_c NRG_E + DL [H8000]")
    din = sum(f[2] for f in flows if f[1] == "dh")
    add("dh", "rej", din - sum(f[2] for f in flows if f[0] == "dh"),
        "conversion + distribution losses = box inputs - box outputs (balancing item)")

    # ── 6. own use terminal ───────────────────────────────────────────────
    add("own", "rej", sum(f[2] for f in flows if f[1] == "own"),
        "all energy-branch own use and losses are rejected energy")

    meta = {
        "gross_electricity_TJ": round(g(peh, "GEP", ["TOTAL"])),
        "gross_heat_TJ": round(g(peh, "GHP", ["TOTAL"])),
        "net_electricity_export_TJ": round(net_exp),
        "final_consumption_energy_TJ": round(
            sum(g(bal, b, ["TOTAL"]) for bls in SECTORS.values() for b in bls)
            + g(bal, "FC_OTH_NSP_E", ["TOTAL"])),
        "non_energy_use_TJ": round(g(bal, "FC_NE", ["TOTAL"])),
    }
    return flows, audit, meta


if __name__ == "__main__":
    for y in (2023, 2024):
        fl, au, me = derive(y)
        bands = {}
        for s, t, v in fl:
            if s in BAND_LABEL:
                bands[s] = bands.get(s, 0) + v
        print(f"\n===== SWEDEN {y} =====   flows: {len(fl)}")
        for k, v in me.items():
            print(f"  {k:34}{v:>12,}")
        print(f"  {'primary supply (sum of bands)':34}{sum(bands.values()):>12,}")
        for k, v in sorted(bands.items(), key=lambda x: -x[1]):
            print(f"     {BAND_LABEL[k]:28}{v:>12,}")
