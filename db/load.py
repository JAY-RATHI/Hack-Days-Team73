"""
STEP 3: Load all 14 raw tables into db/urban_media.db

UPDATED against the real schema from inspect_tables.py.

KEY NOTES
- Uses plain sqlite3 from the standard library -- no sqlalchemy needed, so
  `pip install pandas anthropic` is your whole dependency list.
- ridership_actuals is 2.05M rows -> loaded in chunks so it doesn't blow memory.
- Indexes are created on the join keys that actually exist in this data
  (corridor_id and location_id matter as much as route_id here).
- screens.location_id and screens.vehicle_id are BOTH nullable by design:
  a screen is either fixed at a location OR mounted on a vehicle, never both.

HOW TO RUN (from project root)
    python db/load.py
"""
import os
import sqlite3
import pandas as pd
from pathlib import Path

RAW_DIR = Path(os.environ.get("URBAN_RAW", "data/raw"))
DB_PATH = Path(os.environ.get("URBAN_DB", "db/urban_media.db"))
DB_PATH.parent.mkdir(exist_ok=True, parents=True)

# Real row counts from inspect_tables.py, for a load sanity check.
EXPECTED_ROWS = {
    "cities": 3, "zone_demographics": 30, "locations": 910,
    "route_stops": 2436, "vehicles": 854, "route_schedules": 19838,
    "ridership_actuals": 2049632, "screens": 11163,
    "points_of_interest": 1375, "events": 367,
    "client_facts": 520, "dim_slot": 6, "bookings": 191109, "lost_leads": 1450,
}

# Confirmed from the real data.
PRIMARY_KEYS = {
    "cities": "city_id",
    "zone_demographics": "zone_id",
    "locations": "location_id",
    "route_stops": None,        # composite: route_id + stop_sequence
    "vehicles": "vehicle_id",
    "route_schedules": "schedule_id",
    "ridership_actuals": None,  # composite: schedule_id + date
    "screens": "screen_id",
    "points_of_interest": "poi_id",
    "events": "event_id",
    "client_facts": "client_id",
    "dim_slot": "time_block_id",
    "bookings": "booking_id",
    "lost_leads": "lead_id",
}

JOIN_COLUMNS = [
    "screen_id", "zone_id", "route_id", "corridor_id", "location_id",
    "vehicle_id", "schedule_id", "time_block_id", "city_id", "client_id",
    "poi_id", "anchor_location_id", "city_zone", "date",
]

BIG_TABLES = {"ridership_actuals", "bookings"}


def main():
    conn = sqlite3.connect(DB_PATH)
    loaded = []

    for table in EXPECTED_ROWS:
        csv_path = RAW_DIR / f"{table}.csv"
        if not csv_path.exists():
            print(f"!! Skipping {table}: {csv_path} not found")
            continue

        if table in BIG_TABLES:
            # Chunked load so 2M rows don't sit in memory all at once.
            total = 0
            first = True
            for chunk in pd.read_csv(csv_path, chunksize=200_000):
                chunk.to_sql(table, conn,
                             if_exists="replace" if first else "append",
                             index=False)
                total += len(chunk)
                first = False
            n = total
        else:
            df = pd.read_csv(csv_path)
            df.to_sql(table, conn, if_exists="replace", index=False)
            n = len(df)

        loaded.append(table)
        expected = EXPECTED_ROWS[table]
        flag = "" if n == expected else f"  <-- expected {expected}, check this"
        print(f"OK  {table}: {n} rows (PK: {PRIMARY_KEYS[table]}){flag}")

    n_idx = 0
    for table in loaded:
        cols = pd.read_sql(f"SELECT * FROM {table} LIMIT 0", conn).columns
        for col in JOIN_COLUMNS:
            if col in cols:
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} "
                    f"ON {table}({col})"
                )
                n_idx += 1
    conn.commit()
    conn.close()

    print(f"\nDone. {len(loaded)}/{len(EXPECTED_ROWS)} tables, {n_idx} indexes -> {DB_PATH}")


if __name__ == "__main__":
    main()