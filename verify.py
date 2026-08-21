"""
VERIFICATION REPORT — run this against your REAL database and paste me the
full output. It checks the things that are easy to get subtly wrong: row
counts, referential integrity, and whether the numbers are directionally
sane (not just "the script didn't crash").

HOW TO RUN
    export URBAN_DB=db/urban_media.db     # your real DB, not the test one
    python verify_pipeline.py > verify_report.txt
Paste me verify_report.txt.
"""
import json
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

# From the real inspect_tables.py output you already confirmed.
EXPECTED = {
    "cities": 3, "zone_demographics": 30, "locations": 910,
    "route_stops": 2436, "vehicles": 854, "route_schedules": 19838,
    "ridership_actuals": 2049632, "screens": 11163,
    "points_of_interest": 1375, "events": 367,
    "client_facts": 520, "dim_slot": 6, "bookings": 191109, "lost_leads": 1450,
}

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
results = []

def check(name, status, detail=""):
    results.append((status, name, detail))
    print(f"[{status:4}] {name}" + (f" — {detail}" if detail else ""))


def main():
    conn = sqlite3.connect(DB_PATH)
    print("=" * 70)
    print("SECTION 1: Raw table load")
    print("=" * 70)

    for table, expected_n in EXPECTED.items():
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError:
            check(f"table {table} exists", FAIL, "table not found in DB")
            continue
        status = PASS if n == expected_n else FAIL
        check(f"{table} row count", status, f"{n} (expected {expected_n})")

    print("\n" + "=" * 70)
    print("SECTION 2: screen_geo_map")
    print("=" * 70)

    geo = pd.read_sql("SELECT * FROM screen_geo_map", conn)
    n_screens = conn.execute("SELECT COUNT(*) FROM screens").fetchone()[0]
    check("screen_geo_map covers all screens", PASS if len(geo) == n_screens else FAIL,
          f"{len(geo)} of {n_screens}")

    kind_counts = geo.screen_kind.value_counts().to_dict()
    n_fixed = kind_counts.get("fixed", 0)
    n_vehicle = kind_counts.get("vehicle", 0)
    check("fixed screen count ~8548", PASS if abs(n_fixed - 8548) < 50 else WARN,
          f"got {n_fixed}")
    check("vehicle screen count ~2615", PASS if abs(n_vehicle - 2615) < 50 else WARN,
          f"got {n_vehicle}")
    check("fixed+vehicle = total, no leftover kind", PASS if n_fixed + n_vehicle == len(geo) else FAIL,
          f"{n_fixed}+{n_vehicle} vs {len(geo)}")

    no_zone = geo.zone_id.isna().sum()
    check("screens with no zone resolved", PASS if no_zone == 0 else WARN,
          f"{no_zone} screens have null zone_id — these will fall back to nothing in demographics")

    fixed_no_corridor = ((geo.screen_kind == "fixed") & (geo.n_corridors == 0)).sum()
    check("fixed screens with zero corridors serving their stop", PASS if fixed_no_corridor < len(geo)*0.05 else WARN,
          f"{fixed_no_corridor} ({fixed_no_corridor/len(geo)*100:.1f}%) — these get riders_in_block=0, "
          f"likely to land in low/medium confidence")

    print("\n" + "=" * 70)
    print("SECTION 3: screen_cluster_map / corridor_overlap")
    print("=" * 70)

    clu = pd.read_sql("SELECT * FROM screen_cluster_map", conn)
    max_cluster = clu.n_screens_in_cluster.max()
    check("largest cluster size (should be tens, not thousands)",
          PASS if max_cluster < 200 else FAIL,
          f"{max_cluster} screens in the biggest cluster")
    check("cluster count vs screen count (many small clusters expected)",
          PASS if clu.cluster_id.nunique() > len(clu) * 0.1 else WARN,
          f"{clu.cluster_id.nunique()} clusters for {len(clu)} screens")

    unresolved = (clu.cluster_type == "unresolved").sum()
    check("screens with unresolved clustering", PASS if unresolved == 0 else WARN,
          f"{unresolved} screens (these have neither location nor corridor info)")

    ov = pd.read_sql("SELECT * FROM corridor_overlap", conn)
    check("corridor_overlap has rows", PASS if len(ov) > 0 else WARN,
          f"{len(ov)} overlapping corridor pairs found")
    if len(ov):
        check("jaccard values in valid range [0,1]",
              PASS if ov.jaccard.between(0, 1).all() else FAIL,
              f"min={ov.jaccard.min()}, max={ov.jaccard.max()}")

    print("\n" + "=" * 70)
    print("SECTION 4: corridor_timeblock_ridership")
    print("=" * 70)

    rider = pd.read_sql("SELECT * FROM corridor_timeblock_ridership WHERE day_type='weekday'", conn)
    by_block = rider.groupby("time_block_id").avg_daily_block_riders.mean()
    print(by_block.round(0).to_string())
    if 1 in by_block.index:
        block1_lowest = by_block.loc[1] == by_block.min()
        check("block 1 (00:00-04:00) has lowest ridership", PASS if block1_lowest else FAIL,
              f"block 1 = {by_block.get(1):.0f}, min = {by_block.min():.0f}")
    else:
        check("block 1 present in ridership data", WARN, "no night-block trips at all — check if that's expected")

    peak_blocks_highest = by_block.reindex([2,3,5]).mean() > by_block.reindex([1,4,6]).mean()
    check("peak blocks (2,3,5) higher than off-peak on average", PASS if peak_blocks_highest else WARN)

    print("\n" + "=" * 70)
    print("SECTION 5: screen_audience_profile (the main deliverable)")
    print("=" * 70)

    prof = pd.read_sql("SELECT * FROM screen_audience_profile", conn)
    expected_rows = n_screens * 6
    check("row count = screens x 6 blocks", PASS if len(prof) == expected_rows else FAIL,
          f"{len(prof)} (expected {expected_rows})")

    dup = prof.duplicated(subset=["screen_id", "time_block_id"]).sum()
    check("no duplicate (screen_id, time_block_id) pairs", PASS if dup == 0 else FAIL,
          f"{dup} duplicates")

    conf_counts = prof.confidence.value_counts().to_dict()
    print("Confidence distribution:", conf_counts)
    low_pct = conf_counts.get("low", 0) / len(prof) * 100
    check("confidence distribution isn't degenerate (not ~100% one tier)",
          PASS if 0 < low_pct < 90 else WARN,
          f"{low_pct:.1f}% low-confidence")

    # Contradiction check: low-confidence rows should not name specific POI types.
    poi_type_words = set()
    for tw in prof.feature_dict.sample(min(2000, len(prof)), random_state=1):
        d = json.loads(tw)
        poi_type_words.update(d.get("poi_type_weights", {}).keys())
    poi_type_words = {t.replace("_", " ") for t in poi_type_words}

    low_rows = prof[prof.confidence == "low"]
    contradiction_count = 0
    for txt in low_rows.profile_text.sample(min(500, len(low_rows)), random_state=1) if len(low_rows) else []:
        if any(t in txt.lower() for t in poi_type_words) or "hub" in txt.lower():
            contradiction_count += 1
    check("low-confidence rows don't name specific POIs (sampled 500)",
          PASS if contradiction_count == 0 else FAIL,
          f"{contradiction_count} contradictions found" if contradiction_count
          else "clean")

    empty_text = (prof.profile_text.str.len() < 10).sum()
    check("no empty/near-empty profile_text", PASS if empty_text == 0 else FAIL,
          f"{empty_text} rows")

    print("\n" + "=" * 70)
    print("SECTION 6: cross-table referential integrity")
    print("=" * 70)

    orphan_profiles = (~prof.screen_id.isin(
        pd.read_sql("SELECT screen_id FROM screens", conn).screen_id)).sum()
    check("every profile screen_id exists in screens", PASS if orphan_profiles == 0 else FAIL,
          f"{orphan_profiles} orphans")

    orphan_geo = (~geo.zone_id.dropna().isin(
        pd.read_sql("SELECT zone_id FROM zone_demographics", conn).zone_id)).sum()
    check("every resolved zone_id exists in zone_demographics", PASS if orphan_geo == 0 else FAIL,
          f"{orphan_geo} orphans")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    n_pass = sum(1 for s, _, _ in results if s == PASS)
    n_warn = sum(1 for s, _, _ in results if s == WARN)
    n_fail = sum(1 for s, _, _ in results if s == FAIL)
    print(f"PASS: {n_pass}   WARN: {n_warn}   FAIL: {n_fail}")
    if n_fail:
        print("\nFAILs to fix before handoff:")
        for s, name, detail in results:
            if s == FAIL:
                print(f"  - {name}: {detail}")
    if n_warn:
        print("\nWARNs worth a second look (may be fine depending on your data):")
        for s, name, detail in results:
            if s == WARN:
                print(f"  - {name}: {detail}")


if __name__ == "__main__":
    main()