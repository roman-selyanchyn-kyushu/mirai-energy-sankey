"""Pull every year of Energimyndigheten EN0202_A (2005-) as json-stat2, in TJ.

The API's 'Ar' selection value is a positional index, not the year: 0 = 2005.
Years are discovered from the table metadata rather than hardcoded, so this keeps
working as the Agency publishes new years. Files land in sources/ and existing
ones are skipped, so the script is safe to re-run.
"""
import json, os, time, urllib.request

BASE = ("https://pxexternal.energimyndigheten.se/api/v1/en/Energimyndighetens_statistikdatabas/"
        "Officiell_energistatistik/Arlig_energibalans/Balanser/EN0202_A.px")
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(os.path.dirname(HERE), "sources")


def meta():
    with urllib.request.urlopen(BASE, timeout=60) as r:
        d = json.load(r)
    v = {x["code"]: x for x in d["variables"]}
    year = v.get("År") or v.get("Ar")
    return dict(zip(year["valueTexts"], year["values"]))


def pull(year, idx):
    os.makedirs(SOURCES, exist_ok=True)
    path = os.path.join(SOURCES, f"se_em_{year}.json")
    if os.path.exists(path) and os.path.getsize(path) > 40000:
        return "cached"
    q = {"query": [{"code": "År", "selection": {"filter": "item", "values": [idx]}},
                   {"code": "Enhet", "selection": {"filter": "item", "values": ["3"]}}],
         "response": {"format": "json-stat2"}}
    req = urllib.request.Request(BASE, data=json.dumps(q).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        body = r.read()
    d = json.loads(body)
    # the API ignores an out-of-range index rather than erroring, so confirm the year
    assert list(d["dimension"]["År"]["category"]["label"].values()) == [str(year)], year
    with open(path, "wb") as fh:
        fh.write(body)
    return f"{len(body)/1024:.0f} KB"


if __name__ == "__main__":
    m = meta()
    print("years in EN0202_A:", ", ".join(sorted(m)))
    for y in sorted(m):
        print(f"  {y}  {pull(int(y), m[y])}", flush=True)
        time.sleep(1.5)
