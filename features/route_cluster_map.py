"""
IMPLEMENTATION STEP 1 (rewritten for the real data): audience overlap.

WHY THE ORIGINAL PLAN'S APPROACH WOULD HAVE FAILED
The plan said: union-find, merge any two routes sharing a stop, transitively.
With 2,436 route_stops over only 910 locations, corridors share stops
constantly -- transitive merging collapses nearly every corridor in a city
into ONE giant cluster. A cluster containing half the city's inventory tells
D4 nothing useful.

WHAT WE DO INSTEAD -- two levels:

  1. HARD CLUSTERS (screen_cluster_map): screens that reach a genuinely
     identical audience.
       - fixed screens -> cluster = their location_id
         (three screens on one bus shelter see the same people, full stop)
       - vehicle screens -> cluster = their corridor_id
         (every screen on buses along one corridor sees that corridor's riders)
     Within a cluster, reach should NOT be summed -- it's the same people.

  2. SOFT OVERLAP (corridor_overlap): a Jaccard score between every pair of
     corridors that share at least one stop. Two corridors sharing 60% of
     their stops carry substantially overlapping riders, but they are not
     the same audience -- so this is a discount factor, not a merge.

D4 uses (1) to collapse duplicates and (2) to shade combined reach down.
This is the "boards on the same route share an audience" nuance from the
deck, handled without destroying inventory granularity.

OUTPUT TABLES
    screen_cluster_map(screen_id, cluster_id, cluster_type, n_screens_in_cluster)
    corridor_overlap(corridor_a, corridor_b, shared_stops, jaccard)

HOW TO RUN (needs screen_geo_map first)
    python features/route_cluster_map.py
"""
import os
import sqlite3
from itertools import combinations
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")
MIN_JACCARD = 0.05   # below this, overlap is noise -- don't store the pair


def main():
    conn = sqlite3.connect(DB_PATH)

    geo = pd.read_sql("SELECT * FROM screen_geo_map", conn)
    route_stops = pd.read_sql(
        "SELECT corridor_id, location_id FROM route_stops", conn
    ).drop_duplicates()

    # ---- 1. Hard clusters -------------------------------------------------
    def cluster_of(row):
        if row.screen_kind == "fixed" and pd.notna(row.location_id):
            return f"LOC::{row.location_id}", "same_stop"
        if row.screen_kind == "vehicle" and pd.notna(row.primary_corridor_id):
            return f"COR::{row.primary_corridor_id}", "same_corridor"
        # No geography resolved -- treat as its own audience, don't silently
        # lump it in with anything else.
        return f"SOLO::{row.screen_id}", "unresolved"

    clusters = [cluster_of(r) for r in geo.itertuples(index=False)]
    geo["cluster_id"] = [c[0] for c in clusters]
    geo["cluster_type"] = [c[1] for c in clusters]

    sizes = geo.cluster_id.value_counts().to_dict()
    geo["n_screens_in_cluster"] = geo.cluster_id.map(sizes)

    out = geo[["screen_id", "cluster_id", "cluster_type", "n_screens_in_cluster"]]
    out.to_sql("screen_cluster_map", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_clu_screen ON screen_cluster_map(screen_id)")

    print(f"OK  screen_cluster_map: {len(out)} screens -> "
          f"{out.cluster_id.nunique()} clusters")
    print(out.cluster_type.value_counts().to_string())
    print(f"    largest cluster holds {out.n_screens_in_cluster.max()} screens "
          f"(sanity check: should be small, not thousands)")

    # ---- 2. Soft corridor overlap ----------------------------------------
    corridor_stops = (
        route_stops.groupby("corridor_id")["location_id"].apply(set).to_dict()
    )

    pairs = []
    for a, b in combinations(sorted(corridor_stops), 2):
        sa, sb = corridor_stops[a], corridor_stops[b]
        shared = sa & sb
        if not shared:
            continue
        jac = len(shared) / len(sa | sb)
        if jac >= MIN_JACCARD:
            pairs.append({"corridor_a": a, "corridor_b": b,
                          "shared_stops": len(shared), "jaccard": round(jac, 4)})

    overlap = pd.DataFrame(pairs)
    if overlap.empty:
        overlap = pd.DataFrame(columns=["corridor_a", "corridor_b",
                                        "shared_stops", "jaccard"])
    overlap.to_sql("corridor_overlap", conn, if_exists="replace", index=False)
    conn.commit()

    print(f"\nOK  corridor_overlap: {len(overlap)} overlapping corridor pairs "
          f"(of {len(corridor_stops)} corridors)")
    if not overlap.empty:
        print("    highest-overlap pairs:")
        print(overlap.nlargest(5, "jaccard").to_string(index=False))


if __name__ == "__main__":
    main()