"""
D3 STEPS 3-4: price_bands.

=== price_floor ===
Plan says: "base cost-recovery rate from dim_slot/client_facts historical
minimums." Neither table stores a price -- dim_slot is just time-of-day
labels, client_facts is advertiser data. The actual historical price data
lives in bookings.contracted_price_per_slot_per_day.

So price_floor is built from real precedent, at the tightest grouping that
still has enough data to be stable:
    1. this exact screen + time_block, if it has >= MIN_N_FOR_OWN bookings
    2. else this screen's cluster (screen_cluster_map) + time_block
    3. else this city's market_tier (cities.market_tier) + time_block
using the 10th percentile of contracted_price_per_slot_per_day as the floor
(a true minimum is too easily an outlier/discount; p10 is a stable "what a
rep could safely never go below").

=== price_target ===
price_floor * (1 + demand_score * TARGET_MULTIPLIER)
demand_score comes from Person B's own demand_index.py output.

=== price_cap ===
price_floor * MAX_MULTIPLIER, but ALSO checked against lost_leads evidence:
if this screen/cluster has a lost lead with loss_reason='price_too_high',
the cap is pulled down toward that lead's quoted_price_per_slot_per_day --
that's a real, observed point where a real client walked away. Ignoring it
and pricing above it would repeat a mistake the data already tells you about.

HOW TO RUN (needs screen_demand_index from demand_index.py)
    python pricing/price_bands.py
"""
import os
import sqlite3
import pandas as pd
import numpy as np

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

MIN_N_FOR_OWN = 5
TARGET_MULTIPLIER = 0.6   # price_target = floor * (1 + demand*0.6)
MAX_MULTIPLIER = 1.8      # price_cap = floor * 1.8, before lead-evidence pull-down


def p10(s):
    return s.quantile(0.10) if len(s) else np.nan


def build_price_floors(conn):
    bk = pd.read_sql(
        "SELECT screen_id, time_block_id, contracted_price_per_slot_per_day AS price "
        "FROM bookings WHERE booking_status != 'cancelled'", conn)
    geo = pd.read_sql("SELECT screen_id, city_id FROM screen_geo_map", conn)
    clusters = pd.read_sql("SELECT screen_id, cluster_id FROM screen_cluster_map", conn)
    cities = pd.read_sql("SELECT city_id, market_tier FROM cities", conn)

    bk = bk.merge(geo, on="screen_id").merge(clusters, on="screen_id").merge(cities, on="city_id")

    own = (bk.groupby(["screen_id", "time_block_id"])
           .agg(floor_own=("price", p10), n_own=("price", "size")).reset_index())

    cluster_floor = (bk.groupby(["cluster_id", "time_block_id"])
                     .agg(floor_cluster=("price", p10)).reset_index())

    tier_floor = (bk.groupby(["market_tier", "time_block_id"])
                  .agg(floor_tier=("price", p10)).reset_index())
    global_floor = bk.groupby("time_block_id").price.apply(p10).rename("floor_global").reset_index()

    all_pairs = geo[["screen_id", "city_id"]].merge(clusters, on="screen_id").merge(cities, on="city_id")
    all_pairs = (all_pairs.assign(key=1)
                 .merge(pd.DataFrame({"time_block_id": range(1, 7), "key": 1}), on="key")
                 .drop(columns="key"))

    df = (all_pairs
          .merge(own, on=["screen_id", "time_block_id"], how="left")
          .merge(cluster_floor, on=["cluster_id", "time_block_id"], how="left")
          .merge(tier_floor, on=["market_tier", "time_block_id"], how="left")
          .merge(global_floor, on="time_block_id", how="left"))

    def resolve_floor(row):
        if pd.notna(row.floor_own) and row.n_own >= MIN_N_FOR_OWN:
            return row.floor_own, "own_history"
        if pd.notna(row.floor_cluster):
            return row.floor_cluster, "cluster_history"
        if pd.notna(row.floor_tier):
            return row.floor_tier, "market_tier_history"
        return row.floor_global, "global_fallback"

    resolved = df.apply(resolve_floor, axis=1, result_type="expand")
    df["price_floor"] = resolved[0].round(2)
    df["floor_source"] = resolved[1]
    return df[["screen_id", "time_block_id", "price_floor", "floor_source"]]


def build_price_ceiling_evidence(conn):
    """Lowest quoted_price on a price_too_high lost lead, per screen."""
    ll = pd.read_sql(
        "SELECT anchor_screen_id AS screen_id, quoted_price_per_slot_per_day AS q "
        "FROM lost_leads WHERE loss_reason = 'price_too_high' "
        "AND quoted_price_per_slot_per_day IS NOT NULL "
        "AND anchor_screen_id IS NOT NULL", conn)
    if ll.empty:
        return pd.DataFrame(columns=["screen_id", "rejected_price_evidence"])
    out = ll.groupby("screen_id").q.min().reset_index()
    out.columns = ["screen_id", "rejected_price_evidence"]
    return out


def main():
    conn = sqlite3.connect(DB_PATH)

    floors = build_price_floors(conn)
    demand = pd.read_sql("SELECT * FROM screen_demand_index", conn)
    ceiling_evidence = build_price_ceiling_evidence(conn)

    df = (floors.merge(demand, on=["screen_id", "time_block_id"], how="left")
          .merge(ceiling_evidence, on="screen_id", how="left"))
    df["demand_score"] = df.demand_score.fillna(0.3)
    df["confidence"] = df.confidence.fillna("inferred_global")

    df["price_target"] = (df.price_floor * (1 + df.demand_score * TARGET_MULTIPLIER)).round(2)
    df["price_cap_raw"] = (df.price_floor * MAX_MULTIPLIER).round(2)

    # Pull cap down toward observed rejection evidence, but never below floor.
    df["price_cap"] = df[["price_cap_raw", "rejected_price_evidence"]].min(axis=1, skipna=True)
    df["price_cap"] = df[["price_cap", "price_floor"]].max(axis=1).round(2)
    df["cap_adjusted_by_lost_lead"] = df.rejected_price_evidence.notna() & \
                                       (df.price_cap < df.price_cap_raw)

    # target should never exceed cap
    df["price_target"] = df[["price_target", "price_cap"]].min(axis=1).round(2)

    out = df[["screen_id", "time_block_id", "price_floor", "price_target", "price_cap",
              "demand_score", "confidence", "floor_source", "cap_adjusted_by_lost_lead"]]

    out.to_sql("screen_price_bands", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_price ON "
                 "screen_price_bands(screen_id, time_block_id)")
    conn.commit()

    print(f"OK  screen_price_bands: {len(out)} rows")
    print("\nfloor_source distribution:")
    print(out.floor_source.value_counts().to_string())
    print(f"\n{out.cap_adjusted_by_lost_lead.sum()} screen/blocks had their cap "
          f"pulled down by a real rejected quote")
    print("\nSanity: does higher demand -> higher target, on average?")
    print(out.groupby(pd.cut(out.demand_score, 4)).price_target.mean().round(2).to_string())


if __name__ == "__main__":
    main()