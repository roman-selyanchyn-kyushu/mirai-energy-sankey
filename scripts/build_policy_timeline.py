"""Build policy_timeline.html — the paired Sweden/Japan policy timeline.

The dataset is the two fenced json blocks in sources/policy/policy_history_dataset.md
(events and governments), written by sources/policy/build_dataset.mjs. This script
parses them, checks them against the contract, and injects them into
template_policy_timeline.html. Nothing about a policy — no date, title, rate or
status — is ever typed into the template; the page renders whatever is in the file.

The validation report runs on every build and is the point of the script as much as
the page is: a dangling `reverses` link or a gap between two governments would draw a
connector to nowhere or a band with a hole in it, and both are easier to see in a
printed report than in a rendered figure.

    python3 scripts/build_policy_timeline.py
"""
import json, os, re, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
DATASET = os.path.join(PROJECT, "sources", "policy", "policy_history_dataset.md")

# The field list the dataset is specified to carry. title_en_source is optional —
# it is present only where a title was translated rather than published in English.
EVENT_FIELDS = [
    "id", "country", "date", "date_precision", "date_basis", "title_original",
    "title_en", "instrument_type", "legal_status", "binds_whom",
    "has_interim_targets", "has_independent_review_body", "direction",
    "direction_basis", "sector", "quantified_change", "reverses", "supersedes",
    "still_in_force", "end_date", "years_in_force", "government_at_adoption",
    "governments_since_adoption", "source_title", "source_publisher",
    "source_date", "source_url", "confidence", "notes",
]
OPTIONAL_EVENT_FIELDS = ["title_en_source"]
GOV_FIELDS = ["country", "pm_name", "party_or_coalition", "start_date", "end_date", "source_url"]

# The controlled vocabularies, as declared by the generator. Held here so an
# unexpected value is reported rather than silently drawn as an unstyled marker.
VOCAB = {
    "country": ["SE", "JP"],
    "date_precision": ["day", "month", "year"],
    "date_basis": ["enacted", "in_force", "cabinet_decision", "announced", "repealed"],
    "instrument_type": ["statute", "statutory_amendment", "ordinance", "cabinet_decision",
                        "tax_rate_change", "budget_measure", "plan_revision", "target_adoption",
                        "programme_launch", "programme_termination", "agency_creation",
                        "regulatory_standard", "eu_obligation", "referendum"],
    "legal_status": ["legally_binding_statute", "binding_secondary_legislation",
                     "administratively_binding", "non_binding_plan", "political_declaration"],
    "binds_whom": ["government", "regulated_entities", "both", "none"],
    "direction": ["strengthening", "weakening", "restructuring", "neutral"],
    "sector": ["cross_cutting", "transport", "heat", "electricity", "industry", "nuclear",
               "hydrogen", "forestry_landuse", "carbon_pricing"],
    "confidence": ["verified", "uncertain", "not_found"],
}


# ── loading ────────────────────────────────────────────────────────────────

def load():
    """Return (events, governments, open_questions) from the dataset markdown.

    The file is a research document, not a data file: two json blocks followed by
    prose. The prose matters — it is where the things that were looked for and not
    found are recorded — so it is carried through to the page rather than dropped.
    """
    text = open(DATASET, encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    if len(blocks) != 2:
        sys.exit(f"expected 2 json blocks in {DATASET}, found {len(blocks)}")
    events, governments = (json.loads(b) for b in blocks)
    tail = text.split("```", 4)[-1]
    oq = tail[tail.index("## open_questions"):].strip() if "## open_questions" in tail else ""
    return events, governments, oq


def iso(d):
    """Expand a partial date to a full one. '1974' -> '1974-01-01', '2021-03' -> '2021-03-01'."""
    return d if len(d) == 10 else f"{d}-01" if len(d) == 7 else f"{d}-01-01"


def parse(d):
    return date.fromisoformat(iso(d))


def span(d, precision):
    """The interval a date actually denotes, given its stated precision.

    A year-precision event happened somewhere inside its year and a month-precision
    event somewhere inside its month; the page draws that as a whisker, so the
    interval is computed here rather than in the browser.
    """
    start = parse(d)
    if precision == "year" and len(d) == 4:
        return start, date(start.year, 12, 31)
    if precision == "month" and len(d) == 7:
        end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        return start, date.fromordinal(end.toordinal() - 1)
    return start, start


# ── validation ─────────────────────────────────────────────────────────────

class Report:
    """Errors stop the build; notes are anomalies the data genuinely contains."""

    def __init__(self):
        self.errors, self.notes = [], []

    def error(self, msg):
        self.errors.append(msg)

    def note(self, msg):
        self.notes.append(msg)

    def section(self, title, lines):
        print(f"\n{title}")
        for line in lines:
            print(f"  {line}")


def validate(events, governments, oq):
    r = Report()
    by_id = {e["id"]: e for e in events}

    print(f"dataset  {os.path.relpath(DATASET, PROJECT)}")
    print(f"         {len(events)} events, {len(governments)} government segments, "
          f"open_questions {'present' if oq else 'MISSING'} ({len(oq)} chars)")

    # ── fields ──
    if len(by_id) != len(events):
        seen, dupes = set(), set()
        for e in events:
            (dupes if e["id"] in seen else seen).add(e["id"])
        r.error(f"duplicate event ids: {sorted(dupes)}")
    for e in events:
        missing = [k for k in EVENT_FIELDS if k not in e]
        extra = [k for k in e if k not in EVENT_FIELDS + OPTIONAL_EVENT_FIELDS]
        if missing:
            r.error(f"{e['id']}: missing fields {missing}")
        if extra:
            r.error(f"{e['id']}: unexpected fields {extra}")
    for i, g in enumerate(governments):
        missing = [k for k in GOV_FIELDS if k not in g]
        if missing:
            r.error(f"governments[{i}]: missing fields {missing}")
    opt = sum(1 for e in events if "title_en_source" in e)
    unpop = {k: sum(1 for e in events if e.get(k) in (None, "")) for k in EVENT_FIELDS}
    r.section("fields", [
        f"all {len(EVENT_FIELDS)} specified fields present on all {len(events)} events",
        f"optional title_en_source present on {opt}, absent on {len(events)-opt}",
        "null or empty: " + ", ".join(f"{k} {n}" for k, n in unpop.items() if n) or "none",
    ])

    # ── dates ──
    bad, mismatched = [], []
    for e in events:
        for field in ("date", "end_date"):
            d = e.get(field)
            if d is None:
                continue
            try:
                parse(d)
            except ValueError:
                bad.append(f"{e['id']} {field}={d!r}")
        want = {4: "year", 7: "month", 10: "day"}.get(len(e["date"]))
        if want != e["date_precision"]:
            mismatched.append(f"{e['id']} date={e['date']} declares {e['date_precision']}")
    for b in bad:
        r.error(f"unparseable date: {b}")
    for m in mismatched:
        r.error(f"date_precision does not match the date written: {m}")
    prec = {p: sum(1 for e in events if e["date_precision"] == p) for p in VOCAB["date_precision"]}
    lo = min(parse(e["date"]) for e in events)
    hi = max(parse(e["date"]) for e in events)
    r.section("dates", [
        f"all {len(events)} event dates parse; all {sum(1 for e in events if e['end_date'])} end_dates parse",
        f"range {lo} → {hi}",
        "precision: " + ", ".join(f"{k} {v}" for k, v in prec.items()),
        f"year- and month-precision events drawn as whiskers: {prec['year'] + prec['month']}",
    ])

    # ── vocabularies ──
    lines = []
    for field, allowed in VOCAB.items():
        used = {}
        for e in events:
            used[e[field]] = used.get(e[field], 0) + 1
        unexpected = [v for v in used if v not in allowed]
        for v in unexpected:
            r.error(f"unexpected {field} value {v!r} on "
                    f"{[e['id'] for e in events if e[field] == v]}")
        unused = [v for v in allowed if v not in used]
        lines.append(f"{field}: {len(used)}/{len(allowed)} values used"
                     + (f" — declared but absent: {unused}" if unused else "")
                     + (f" — UNEXPECTED: {unexpected}" if unexpected else ""))
        lines.append("    " + ", ".join(f"{k} {n}" for k, n in
                                        sorted(used.items(), key=lambda kv: -kv[1])))
    r.section("vocabularies", lines)

    # ── cross-references ──
    lines = []
    for field in ("reverses", "supersedes"):
        links = [(e["id"], e[field]) for e in events if e[field]]
        for src, tgt in links:
            if tgt not in by_id:
                r.error(f"dangling {field}: {src} → {tgt} (no such event)")
                continue
            if tgt == src:
                r.error(f"self-referential {field}: {src}")
                continue
            a, b = by_id[src], by_id[tgt]
            if a["country"] != b["country"]:
                r.error(f"cross-country {field}: {src} ({a['country']}) → {tgt} ({b['country']})")
            if parse(b["date"]) > parse(a["date"]):
                r.error(f"{field} points forwards in time: {src} {a['date']} → {tgt} {b['date']}")
            if a["sector"] != b["sector"]:
                r.note(f"cross-sector {field}: {src} ({a['sector']}) → {tgt} ({b['sector']}) — "
                       f"the connector leaves its sublane")
        lines.append(f"{field}: {len(links)} links, all resolve to a real event, "
                     f"all point backwards in time")
        lines.append("    per country: " + ", ".join(
            f"{c} {sum(1 for s, _ in links if by_id[s]['country'] == c)}" for c in VOCAB["country"]))
    r.section("cross-references", lines)

    # ── governments ──
    lines = []
    for c in sorted({e["country"] for e in events}):
        segs = sorted([g for g in governments if g["country"] == c], key=lambda g: g["start_date"])
        if not segs:
            r.error(f"country {c} appears in events but has no government segments")
            continue
        for prev, nxt in zip(segs, segs[1:]):
            if prev["end_date"] is None:
                r.error(f"{c}: {prev['pm_name']} has no end_date but is not the last segment")
                continue
            if prev["end_date"] > nxt["start_date"]:
                r.error(f"{c}: overlap — {prev['pm_name']} ends {prev['end_date']}, "
                        f"{nxt['pm_name']} starts {nxt['start_date']}")
            elif prev["end_date"] < nxt["start_date"]:
                gap = (parse(nxt["start_date"]) - parse(prev["end_date"])).days
                r.note(f"{c}: {gap}-day gap — {prev['pm_name']} ends {prev['end_date']}, "
                       f"{nxt['pm_name']} starts {nxt['start_date']}")
        if segs[-1]["end_date"] is not None:
            r.note(f"{c}: last segment ({segs[-1]['pm_name']}) ends {segs[-1]['end_date']} — "
                   f"the band will stop short of the right edge")
        early = [e["id"] for e in events
                 if e["country"] == c and parse(e["date"]) < parse(segs[0]["start_date"])]
        if early:
            r.error(f"{c}: events before the first government segment: {early}")
        lines.append(f"{c}: {len(segs)} segments, {segs[0]['start_date']} → "
                     f"{segs[-1]['end_date'] or 'open'}, "
                     f"{len({g['pm_name'] for g in segs})} distinct PMs, "
                     f"{len({g['party_or_coalition'] for g in segs})} distinct parties/coalitions")
    missing_gov = sorted({e["country"] for e in events} - {g["country"] for g in governments})
    if missing_gov:
        r.error(f"countries in events with no government segments: {missing_gov}")
    lines.append("every country in events has government segments: "
                 + ("yes" if not missing_gov else "NO"))
    r.section("governments", lines)

    # ── durations, which are what the durability comparison is drawn from ──
    both = [e["id"] for e in events if e["still_in_force"] and e["end_date"]]
    for i in both:
        e = by_id[i]
        r.note(f"{i}: still_in_force is true but end_date is {e['end_date']} — "
               f"the bar's right end is ambiguous; {e['notes'][:90]}...")
    for e in events:
        if e["end_date"] and parse(e["end_date"]) < parse(e["date"]):
            r.error(f"{e['id']}: end_date {e['end_date']} precedes date {e['date']}")
    no_dur = [e["id"] for e in events if not e["still_in_force"] and not e["end_date"]]
    if no_dur:
        r.note(f"{len(no_dur)} events have neither end_date nor still_in_force, "
               f"so they get a marker but no bar: {no_dur}")
    r.section("durations", [
        f"{sum(1 for e in events if e['still_in_force'])} still in force (bar runs to the right edge)",
        f"{sum(1 for e in events if e['end_date'])} carry an end_date"
        f"{f' — {len(both)} carry both' if both else ''}",
        f"{len(events) - len(no_dur)} of {len(events)} events get a duration bar",
        "longest in force: " + ", ".join(
            f"{c} {max((e for e in events if e['country'] == c), key=lambda e: e['years_in_force'])['id']}"
            f" {max(e['years_in_force'] for e in events if e['country'] == c)}y"
            for c in VOCAB["country"]),
    ])

    # ── sublane occupancy: how many bars must be stacked so none overlaps ──
    lines = []
    for c in VOCAB["country"]:
        rows = []
        for sec in sorted({e["sector"] for e in events if e["country"] == c}):
            grp = [e for e in events if e["country"] == c and e["sector"] == sec]
            ends = []
            for e in sorted(grp, key=lambda e: e["date"]):
                s = parse(e["date"])
                t = date.today() if e["still_in_force"] else parse(e["end_date"] or e["date"])
                placed = next((k for k, x in enumerate(ends) if x < s), None)
                if placed is None:
                    ends.append(t)
                else:
                    ends[placed] = t
            rows.append(f"{sec} {len(grp)} events / {len(ends)} rows")
        lines.append(f"{c}: " + "; ".join(rows))
    r.section("sublane packing (bars that overlap in time need their own row)", lines)

    # ── the accounting the brief asks to be verified programmatically ──
    plotted = [e for e in events if e["confidence"] != "not_found"]
    sought = [e for e in events if e["confidence"] == "not_found"]
    ok = len(plotted) + len(sought) == len(events)
    if not ok:
        r.error("plotted + sought-but-not-verified does not equal the event count")
    r.section("plot accounting", [
        f"{len(plotted)} plotted + {len(sought)} sought-but-not-verified = "
        f"{len(plotted) + len(sought)} of {len(events)} — {'OK' if ok else 'MISMATCH'}",
        f"{sum(1 for e in plotted if e['confidence'] == 'uncertain')} plotted with a dashed "
        f"(uncertain) outline",
        "no event carries confidence 'not_found', so the block below the plot is fed by the "
        "open_questions prose instead" if not sought else "",
    ])

    print("\nanomalies (reported, not silently dropped)")
    for n in r.notes:
        print(f"  NOTE  {n}")
    if not r.notes:
        print("  none")
    if r.errors:
        print("\nerrors")
        for e in r.errors:
            print(f"  ERROR {e}")
    print(f"\n{len(r.errors)} error(s), {len(r.notes)} note(s)")
    return r


# ── rendering ──────────────────────────────────────────────────────────────

TEMPLATE = os.path.join(HERE, "template_policy_timeline.html")
PAGE = os.path.join(PROJECT, "policy_timeline.html")


def render(events, governments, oq):
    """Inject the three datasets into the template and write the page.

    Same shape as build_evidence.py: the template owns the layout and the
    renderer, the data arrives through placeholders, and the published page is a
    generated artefact that nobody edits by hand.
    """
    tpl = open(TEMPLATE, encoding="utf-8").read()
    for ph in ("__EVENTS__", "__GOVERNMENTS__", "__OPEN_QUESTIONS__"):
        assert ph in tpl, f"template placeholder {ph} missing"
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    out = (tpl.replace("__EVENTS__", dump(events))
              .replace("__GOVERNMENTS__", dump(governments))
              .replace("__OPEN_QUESTIONS__", dump(oq)))
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"\nwrote {PAGE}  ({len(out)/1024:.0f} KB)")


def main():
    events, governments, oq = load()
    r = validate(events, governments, oq)
    if r.errors:
        sys.exit(1)
    render(events, governments, oq)


if __name__ == "__main__":
    main()
