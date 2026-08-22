"""
VERIFICATION REPORT for D2/D3 — run against your REAL database.

HOW TO RUN
    export URBAN_DB=db/urban_media.db
    export ANTHROPIC_API_KEY=...
    python verify_scoring_pricing.py > verify_b_report.txt
Paste me verify_b_report.txt.

WHAT IT CHECKS
1. Brief parser: does it produce valid CampaignSpec JSON for all 3 sample
   briefs, and does it correctly leave budget=null when not stated?
2. Demand index: sane row count, non-degenerate confidence distribution,
   cold-start hierarchy actually firing.
3. Price bands: floor <= target <= cap always holds (this MUST be true or
   D4/D6 will show nonsense numbers), monotonic demand->price relationship.
4. Merge: at least one sample brief returns a non-empty ranked+priced list,
   with reasons that reference real numbers.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")
PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
results = []


def check(name, status, detail=""):
    results.append(status)
    print(f"[{status:4}] {name}" + (f" — {detail}" if detail else ""))


def main():
    sys.path.insert(0, os.getcwd())
    conn = sqlite3.connect(DB_PATH)

    print("=" * 70)
    print("SECTION 1: Brief parser")
    print("=" * 70)
    from sample_campaign_briefs import SAMPLE_BRIEFS
    from scoring.brief_parser import parse_brief

    specs = {}
    for b in SAMPLE_BRIEFS:
        try:
            spec = parse_brief(b["text"])
            specs[b["id"]] = spec
            check(f"parse {b['id']}", PASS)
            print(f"    city_hint={spec.get('city_hint')!r}  "
                  f"requires_broad_coverage={spec.get('requires_broad_coverage')!r}  "
                  f"target_zones_text={spec.get('target_zones_text')!r}")
        except Exception as e:
            check(f"parse {b['id']}", FAIL, str(e))

    no_budget_spec = specs.get("BRIEF_02_no_budget")
    if no_budget_spec:
        check("no-budget brief -> budget is null, not invented",
              PASS if no_budget_spec.get("budget") is None else FAIL,
              f"got budget={no_budget_spec.get('budget')}")

    print("\n" + "=" * 70)
    print("SECTION 2: Demand index")
    print("=" * 70)
    env = dict(os.environ, URBAN_DB=DB_PATH)
    r = subprocess.run([sys.executable, "pricing/demand_index.py"],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        log = tempfile.NamedTemporaryFile(mode="w", suffix="_di.log",
                                          delete=False, encoding="utf-8")
        log.write(r.stdout + "\n" + r.stderr)
        log.close()
        check("demand_index.py runs without error", FAIL, f"see {log.name}")
    else:
        check("demand_index.py runs without error", PASS)

    di = pd.read_sql("SELECT * FROM screen_demand_index", conn)
    n_screens = conn.execute("SELECT COUNT(*) FROM screens").fetchone()[0]
    check("row count = screens x 6", PASS if len(di) == n_screens * 6 else FAIL,
          f"{len(di)} vs expected {n_screens*6}")
    conf_counts = di.confidence.value_counts().to_dict()
    print("confidence distribution:", conf_counts)
    check("cold-start hierarchy has more than one tier represented",
          PASS if len(conf_counts) > 1 else WARN, str(conf_counts))
    check("demand_score in [0,1]", PASS if di.demand_score.between(0, 1).all() else FAIL,
          f"min={di.demand_score.min()}, max={di.demand_score.max()}")

    print("\n" + "=" * 70)
    print("SECTION 3: Price bands")
    print("=" * 70)
    r = subprocess.run([sys.executable, "pricing/price_bands.py"],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        log = tempfile.NamedTemporaryFile(mode="w", suffix="_pb.log",
                                          delete=False, encoding="utf-8")
        log.write(r.stdout + "\n" + r.stderr)
        log.close()
        check("price_bands.py runs without error", FAIL, f"see {log.name}")
    else:
        check("price_bands.py runs without error", PASS)

    pb = pd.read_sql("SELECT * FROM screen_price_bands", conn)
    check("row count = screens x 6", PASS if len(pb) == n_screens * 6 else FAIL,
          f"{len(pb)} vs expected {n_screens*6}")
    order_ok = (pb.price_floor <= pb.price_target + 0.01).all() and \
               (pb.price_target <= pb.price_cap + 0.01).all()
    check("floor <= target <= cap holds for every row (CRITICAL)",
          PASS if order_ok else FAIL,
          "" if order_ok else "some rows violate ordering — check price_bands.py logic")
    check("no null prices", PASS if pb.price_floor.notna().all() and
          pb.price_target.notna().all() and pb.price_cap.notna().all() else FAIL)

    corr = pb.demand_score.corr(pb.price_target)
    check("positive correlation between demand_score and price_target",
          PASS if corr > 0.1 else WARN, f"correlation = {corr:.3f}")

    print("\n" + "=" * 70)
    print("SECTION 4: End-to-end merge on sample briefs")
    print("=" * 70)
    from pricing.merge_scored_priced import build_scored_priced_screens

    for b in SAMPLE_BRIEFS:
        spec = specs.get(b["id"])
        if spec is None:
            continue
        result, meta = build_scored_priced_screens(spec, conn)
        status = PASS if not result.empty else WARN
        check(f"{b['id']} -> non-empty scored+priced result", status,
              f"{len(result)} screens, meta={meta}")
        if not result.empty:
            top_reason = result.iloc[0].relevance_reason
            check(f"{b['id']} -> top reason references real evidence, not generic",
                  PASS if any(ch.isdigit() for ch in top_reason) or "%" in top_reason else WARN,
                  top_reason[:100])

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"PASS: {results.count(PASS)}   WARN: {results.count(WARN)}   FAIL: {results.count(FAIL)}")


if __name__ == "__main__":
    main()