"""
IMPLEMENTATION STEP 7: spot-check before handing off to Person B.

Prints, for a few screens, the generated profile next to the raw data it was
derived from -- so you can confirm the numbers actually trace back. Deliberately
samples one screen from EACH confidence tier and each screen_kind, because the
bugs live in the edge cases, not the average case.

HOW TO RUN
    python spot_check.py
"""
import json
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")


def show(conn, screen_id, tb):
    # Cast out of numpy types -- sqlite3 can't bind numpy.int64 as a parameter
    # and you get a confusing empty result instead of an error.
    screen_id, tb = str(screen_id), int(tb)
    prof = pd.read_sql(
        "SELECT * FROM screen_audience_profile WHERE screen_id=? AND time_block_id=?",
        conn, params=(screen_id, tb)).iloc[0]
    geo = pd.read_sql("SELECT * FROM screen_geo_map WHERE screen_id=?",
                      conn, params=(screen_id,)).iloc[0]

    print("=" * 72)
    print(f"{screen_id} | block {tb} | {geo.screen_kind} | conf={prof.confidence}")
    print(f"  TEXT: {prof.profile_text}")
    print(f"  TAGS: {prof.audience_tags}")
    print(f"  GEO : location={geo.location_id} vehicle={geo.vehicle_id} "
          f"zone={geo.zone_id} corridors={geo.corridor_ids}")

    fd = json.loads(prof.feature_dict)
    print(f"  FEATURES: riders_in_block={fd.get('riders_in_block')} "
          f"poi_count={fd.get('poi_count')} "
          f"income_index={fd.get('income_index')} "
          f"commuter_score={fd.get('commuter_score')}")

    # Trace the POI claim back to actual POI rows.
    if geo.location_id:
        pois = pd.read_sql(
            "SELECT name, poi_type, est_daily_footfall, distance_to_location_km, "
            "side_of_road, peak_daypart FROM points_of_interest "
            "WHERE anchor_location_id = ?", conn, params=(geo.location_id,))
        print(f"  RAW POIs anchored to this stop ({len(pois)}):")
        print("    " + (pois.to_string(index=False).replace("\n", "\n    ")
                        if len(pois) else "(none -- so the profile should NOT "
                                          "name any nearby draws)"))
    print()


def main():
    conn = sqlite3.connect(DB_PATH)
    prof = pd.read_sql("SELECT screen_id, time_block_id, confidence "
                       "FROM screen_audience_profile", conn)
    geo = pd.read_sql("SELECT screen_id, screen_kind FROM screen_geo_map", conn)
    df = prof.merge(geo, on="screen_id")

    print("Sampling one row per (confidence tier x screen kind):\n")
    for (conf, kind), grp in df.groupby(["confidence", "screen_kind"]):
        r = grp.sample(1, random_state=1).iloc[0]
        show(conn, r.screen_id, r.time_block_id)

    print("CHECKLIST -- verify each of these by eye:")
    print("  1. If 'nearby draws' names a POI type, does a POI of that type")
    print("     actually appear in the RAW POIs list above it?")
    print("  2. Do vehicle screens show NO location_id and a corridor instead?")
    print("  3. Is riders_in_block plausible (not 0 for a busy morning block,")
    print("     not identical across every block)?")
    print("  4. Do 'low' confidence rows avoid making specific local claims?")
    print("  5. Does income_index roughly match the screen's zone in")
    print("     zone_demographics?")


if __name__ == "__main__":
    main()