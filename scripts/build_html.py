"""Inject the generated datasets into the HTML template and write the published page."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "/Users/romanselyanchyn/Library/CloudStorage/Dropbox/Apps/Projects/Sankey"

data = json.load(open(os.path.join(HERE, "datasets.json")))
# the audit trail lives in the Excel workbook, not in the page
slim = {k: {kk: vv for kk, vv in v.items() if kk != "audit"} for k, v in data.items()}

tpl = open(os.path.join(HERE, "template.html")).read()
assert "__DATA__" in tpl, "template placeholder missing"
out = tpl.replace("__DATA__", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))

dest = os.path.join(PROJECT, "energy_sankey.html")
with open(dest, "w") as fh:
    fh.write(out)
print(f"wrote {dest}  ({len(out)/1024:.0f} KB)")
