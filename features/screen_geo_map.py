"""
NEW FOUNDATIONAL STEP: resolve every screen to its geography.

WHY THIS EXISTS (this wasn't in the original plan -- the real data forced it)
The `screens` table has two different kinds of screen mixed together:

  - FIXED screens (8,548): have `location_id`, no `vehicle_id`.
    Bolted to one bus stop or metro station. One zone, forever.
    Their audience = the people at that stop + the POIs anchored to it.

  - VEHICLE screens (2,615): have `vehicle_id`, no `location_id`.
    Mounted inside a bus/coach that runs a whole corridor all day.
    Their audience = the riders of that corridor, across every zone it
    passes through. There is no single "nearby POI" for them.

Every downstream step (profiles, clustering, pricing) needs to know which
kind it's looking at, so we resolve it once here instead of re-deriving it
in three places.

IMPORTANT: `vehicles` links to `corridor_id`, NOT `route_id`. A corridor is
the two-way line (e.g. LH-RT-B001); a route_id is one direction of it
(LH-RT-B001-OUT / -INB). Riders belong to the corridor.

OUTPUT TABLE: screen_geo_map
    screen_id, city_id, screen_kind, location_id, vehicle_id,
    primary_corridor_id, corridor_ids (JSON list), zone_id,
    zone_ids (JSON list), n_corridors

HOW TO RUN
    python features/screen_geo_map.py
"""
import json
import os
import sqlite3
from collections import Counter
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")


def main():
    conn = sqlite3.connect(DB_PATH)

    screens = pd.read_sql("SELECT * FROM screens", conn)
    locations = pd.read_sql("SELECT location_id, zone_id, city_id FROM locations", conn)
    vehicles = pd.read_sql("SELECT vehicle_id, corridor_id FROM vehicles", conn)
    route_stops = pd.read_sql(
        "SELECT corridor_id, location_id FROM route_stops", conn
    ).drop_duplicates()

    loc_to_zone = dict(zip(locations.location_id, locations.zone_id))

    # Which corridors serve each stop (a stop can be on several corridors).
    stop_to_corridors = (
        route_stops.groupby("location_id")["corridor_id"].apply(list).to_dict()
    )
    # Which stops (and therefore zones) each corridor passes through.
    corridor_to_stops = (
        route_stops.groupby("corridor_id")["location_id"].apply(list).to_dict()
    )
    veh_to_corridor = dict(zip(vehicles.vehicle_id, vehicles.corridor_id))

    rows = []
    unresolved = []

    for s in screens.itertuples(index=False):
        has_loc = pd.notna(s.location_id)
        has_veh = pd.notna(s.vehicle_id)

        if has_loc:
            kind = "fixed"
            corridors = sorted(set(stop_to_corridors.get(s.location_id, [])))
            zone_id = loc_to_zone.get(s.location_id)
            zone_ids = [zone_id] if zone_id else []
            primary_corridor = corridors[0] if corridors else None

        elif has_veh:
            kind = "vehicle"
            corridor = veh_to_corridor.get(s.vehicle_id)
            corridors = [corridor] if corridor else []
            primary_corridor = corridor
            # Zone = the zones of every stop this corridor passes through.
            stops = corridor_to_stops.get(corridor, [])
            zones = [loc_to_zone.get(st) for st in stops if loc_to_zone.get(st)]
            zone_ids = sorted(set(zones))
            # "Primary" zone = the one it passes through most often.
            zone_id = Counter(zones).most_common(1)[0][0] if zones else None

        else:
            unresolved.append(s.screen_id)
            continue

        rows.append({
            "screen_id": s.screen_id,
            "city_id": s.city_id,
            "screen_kind": kind,
            "location_id": s.location_id if has_loc else None,
            "vehicle_id": s.vehicle_id if has_veh else None,
            "primary_corridor_id": primary_corridor,
            "corridor_ids": json.dumps(corridors),
            "zone_id": zone_id,
            "zone_ids": json.dumps(zone_ids),
            "n_corridors": len(corridors),
        })

    geo = pd.DataFrame(rows)
    geo.to_sql("screen_geo_map", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_geo_screen ON screen_geo_map(screen_id)")
    conn.commit()

    print(f"OK  screen_geo_map: {len(geo)} of {len(screens)} screens resolved")
    print(geo.screen_kind.value_counts().to_string())
    print(f"\nFixed screens with no corridor serving their stop: "
          f"{((geo.screen_kind=='fixed') & (geo.n_corridors==0)).sum()}")
    print(f"Screens with no zone resolved: {geo.zone_id.isna().sum()}")
    if unresolved:
        print(f"\n!! {len(unresolved)} screens have NEITHER location_id nor "
              f"vehicle_id -- flag to team: {unresolved[:5]}")


if __name__ == "__main__":
    main()