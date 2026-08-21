"""
Aggregate the 2.05M-row ridership_actuals table down to a small lookup:
how many riders pass through each corridor, in each time block, per day.

WHY A SEPARATE STEP
ridership_actuals has no time_block_id -- it's per scheduled trip. The trip's
time comes from route_schedules.start_time ("05:03"), which we bucket into
one of the 6 four-hour blocks in dim_slot (hour // 4 + 1). Doing this join
and aggregation once, in SQL, takes seconds; doing it inside the profile
loop for 11K screens would take forever.

We compute TWO measures, because they answer different questions:
  - avg_trip_ridership: how full a single vehicle is (matters for VEHICLE
    screens -- a screen inside a bus is seen by that bus's passengers)
  - avg_daily_block_riders: total riders across the whole corridor in that
    block per day (matters for FIXED screens at stops -- footfall past the
    stop, and for corridor-level demand)

We also split weekday vs weekend (route_schedules.day_type), because a
commuter corridor's morning peak is a completely different animal on Sunday.

OUTPUT TABLE: corridor_timeblock_ridership
    corridor_id, time_block_id, day_type,
    avg_trip_ridership, avg_daily_block_riders, n_trips, n_days

HOW TO RUN
    python features/ridership_by_block.py
"""
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

QUERY = """
WITH trips AS (
    SELECT
        s.corridor_id                                   AS corridor_id,
        (CAST(substr(s.start_time, 1, 2) AS INTEGER) / 4) + 1 AS time_block_id,
        s.day_type                                      AS day_type,
        r.date                                          AS date,
        r.actual_ridership                              AS riders
    FROM ridership_actuals r
    JOIN route_schedules s ON s.schedule_id = r.schedule_id
    WHERE r.is_holiday = 0
),
per_day AS (
    SELECT corridor_id, time_block_id, day_type, date,
           SUM(riders) AS day_block_riders,
           COUNT(*)    AS trips_that_day
    FROM trips
    GROUP BY corridor_id, time_block_id, day_type, date
)
SELECT
    corridor_id,
    time_block_id,
    day_type,
    ROUND(AVG(CAST(day_block_riders AS REAL) / trips_that_day), 1) AS avg_trip_ridership,
    ROUND(AVG(day_block_riders), 1)                               AS avg_daily_block_riders,
    SUM(trips_that_day)                                           AS n_trips,
    COUNT(*)                                                      AS n_days
FROM per_day
GROUP BY corridor_id, time_block_id, day_type
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    print("Aggregating 2M ridership rows (this takes ~10-60s)...")
    df = pd.read_sql(QUERY, conn)

    df.to_sql("corridor_timeblock_ridership", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ctr ON "
                 "corridor_timeblock_ridership(corridor_id, time_block_id, day_type)")
    conn.commit()

    print(f"OK  corridor_timeblock_ridership: {len(df)} rows "
          f"({df.corridor_id.nunique()} corridors x 6 blocks x day_types)")
    print("\nSanity check -- weekday riders by time block (should peak in "
          "blocks 2/3 and 5, trough in block 1):")
    chk = (df[df.day_type == "weekday"]
           .groupby("time_block_id")["avg_daily_block_riders"]
           .mean().round(0))
    print(chk.to_string())
    print("\nIf block 1 (00:00-04:00) isn't the lowest, something's wrong with "
          "the start_time -> time_block bucketing. Check it before moving on.")


if __name__ == "__main__":
    main()