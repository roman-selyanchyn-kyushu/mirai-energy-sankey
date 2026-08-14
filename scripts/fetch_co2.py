"""Pull the Global Carbon Budget CO2 series for Sweden and Japan -> sources/co2.json.

Source is the Global Carbon Budget, distributed as a tidy CSV by Our World in
Data. Only the two countries and the fields the claims page uses are kept, so
the file in sources/ stays small and readable rather than a 14 MB world dump.

Re-running is safe: the file is rewritten from the current upstream release.
"""
import csv, io, json, os, urllib.request

URL = "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(os.path.dirname(HERE), "sources")
COUNTRIES = {"Sweden": "se", "Japan": "jp"}
FIELDS = ["co2", "co2_per_capita", "consumption_co2", "consumption_co2_per_capita",
          "co2_per_unit_energy", "share_global_co2", "population",
          "coal_co2", "oil_co2", "gas_co2", "cement_co2"]
FROM_YEAR = 1990


def main():
    os.makedirs(SOURCES, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "mirai-energy-sankey/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        text = r.read().decode("utf-8")

    num = lambda v: float(v) if v not in ("", None) else None
    out = {c: {} for c in COUNTRIES.values()}
    for row in csv.DictReader(io.StringIO(text)):
        code = COUNTRIES.get(row["country"])
        if not code or not row["year"] or int(row["year"]) < FROM_YEAR:
            continue
        out[code][row["year"]] = {f: num(row.get(f, "")) for f in FIELDS}

    meta = {"source": "Global Carbon Budget, distributed by Our World in Data",
            "url": URL, "fields": FIELDS, "from_year": FROM_YEAR}
    path = os.path.join(SOURCES, "co2.json")
    with open(path, "w") as fh:
        json.dump({"meta": meta, **out}, fh, ensure_ascii=False, indent=1)
    for c in out:
        yrs = sorted(int(y) for y in out[c])
        print(f"  {c}: {yrs[0]}-{yrs[-1]}, {len(yrs)} years")
    print(f"wrote {path}  ({os.path.getsize(path)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
