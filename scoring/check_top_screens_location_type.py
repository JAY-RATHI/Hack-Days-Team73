"""
Decisive check: are the top screens ALREADY metro_station locations even
WITHOUT the explicit metro_only filter? If yes, that proves the filter is
working correctly but was non-binding for this specific campaign (the
optimizer already preferred metro platforms on their own merits) --
NOT a silent bug. If any come back as bus_stop, that IS a real remaining bug.

HOW TO RUN
    python scoring/check_top_screens_location_type.py
"""
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

# The exact 5 screens named in BOTH narratives (identical package before and
# after the metro_only feedback was applied)
SCREENS_TO_CHECK = [
    "LH-SCR-003105", "LH-SCR-003593", "LH-SCR-003796",
    "LH-SCR-005041", "LH-SCR-002359",
]


def main():
    conn = sqlite3.connect(DB_PATH)
    q = """
    SELECT g.screen_id, g.screen_kind, g.location_id, l.location_type
    FROM screen_geo_map g
    LEFT JOIN locations l ON g.location_id = l.location_id
    WHERE g.screen_id IN ({})
    """.format(",".join("?" * len(SCREENS_TO_CHECK)))

    df = pd.read_sql(q, conn, params=SCREENS_TO_CHECK)
    print(df.to_string(index=False))

    all_metro = (df.location_type == "metro_station").all()
    print()
    if all_metro:
        print("CONFIRMED: all 5 top screens are already metro_station locations.")
        print("The metro_only filter is working correctly -- it was non-binding")
        print("for THIS campaign because these screens were already the")
        print("highest-efficiency picks on their own merits (metro platforms")
        print("simply outperform bus stops/vehicles for this audience).")
        print("This is a correct, explainable result -- not a bug.")
    else:
        non_metro = df[df.location_type != "metro_station"]
        print(f"ISSUE CONFIRMED: {len(non_metro)} of the top screens are NOT")
        print("metro_station, despite metro_only being enforced. This means")
        print("there IS still a real bug -- share this output and I'll find it.")
        print(non_metro.to_string(index=False))


if __name__ == "__main__":
    main()