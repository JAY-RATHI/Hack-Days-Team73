"""
Diagnostic: real controlled vocabularies that scoring/exclusion logic
depends on. Run this before trusting any string-matching logic against
poi_type or screens.position -- both were previously guessed from a small
sample, not confirmed against the full dataset.

HOW TO RUN
    python scoring/inspect_scoring_vocab.py
"""
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")


def main():
    conn = sqlite3.connect(DB_PATH)

    print("=" * 70)
    print("points_of_interest.poi_type -- full distinct list with counts")
    print("=" * 70)
    poi = pd.read_sql("SELECT poi_type, COUNT(*) as n FROM points_of_interest "
                      "GROUP BY poi_type ORDER BY n DESC", conn)
    print(poi.to_string(index=False))

    print("\n" + "=" * 70)
    print("screens.position -- full distinct list with counts, split by kind")
    print("=" * 70)
    pos = pd.read_sql(
        "SELECT s.position, "
        "  CASE WHEN s.vehicle_id IS NOT NULL THEN 'vehicle' ELSE 'fixed' END as kind, "
        "  COUNT(*) as n "
        "FROM screens s GROUP BY s.position, kind ORDER BY kind, n DESC", conn)
    print(pos.to_string(index=False))

    print("\n" + "=" * 70)
    print("Sanity check: does ANY position value look like a rear-facing panel?")
    print("=" * 70)
    vehicle_positions = pos[pos.kind == "vehicle"].position.dropna().unique()
    print(f"Vehicle screen position values found: {list(vehicle_positions)}")
    print("If 'rear' isn't literally in that list, the exclusion rule's exact-match")
    print("against position=='rear' needs to change to whatever value IS used.")


if __name__ == "__main__":
    main()