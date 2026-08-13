"""Inject claims.json into the evidence template and write the published page."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)

claims = json.load(open(os.path.join(HERE, "claims.json")))
tpl = open(os.path.join(HERE, "template_evidence.html")).read()
assert "__CLAIMS__" in tpl, "template placeholder missing"
out = tpl.replace("__CLAIMS__", json.dumps(claims, ensure_ascii=False, separators=(",", ":")))

dest = os.path.join(PROJECT, "evidence.html")
with open(dest, "w") as fh:
    fh.write(out)
print(f"wrote {dest}  ({len(out)/1024:.0f} KB, {len(claims)} claim{'s' if len(claims)!=1 else ''})")
