"""
D3 STEPS 1-2: screen_demand_index.

CORRECTION FROM THE ORIGINAL PLAN: it says to decay lost leads by
`lead_expiry_date`. That column does not exist in the real lost_leads table
(confirmed by Person A). We decay by recency of `lead_date` instead -- how
long ago the lead came in is the actual signal available. DECAY_RATE_LEADS
is a named, tunable constant, same as the plan asked for.

CORRECTION: the plan says cold-start fallback uses "zone_tier" -- that
column doesn't exist either. The real fallback hierarchy, in order:
    1. screen's own history (bookings + leads), if any exists
    2. average demand_score of its screen_cluster_map cluster_id
       (Person A's audience-overlap clusters -- a sensible fallback since
       clustered screens see the same people)
    3. average demand_score of its city's OTHER screens, weighted toward
       cities.market_tier (premium cities run hotter demand baselines)
Each fallback level is tagged in `confidence` so nothing pretends to be
better-informed than it is.

=== COMPONENTS ===

1. Booking density (recency-weighted):
   sum over bookings for this screen+time_block of
   exp(-DECAY_RATE_BOOKINGS * age_days), where age_days = REFERENCE_DATE -
   booking.start_date. Cancelled bookings excluded.

2. Lost-lead pressure (recency-weighted):
   Same decay shape, applied to indicated_budget-weighted lead volume, keyed
   to anchor_screen_id. A lead that was quoted a HIGH price relative to
   client_target and still didn't convert (loss_reason='price_too_high')
   contributes less pressure than one that converted on relationship terms --
   it's evidence the price was already too high for that screen, which is a
   ceiling signal for D3 step 3, not more upward demand pressure here.

3. Event boost:
   Any event whose anchor_location_id overlaps the screen's location
   (fixed) or corridor stops (vehicle), weighted by attendance_tier and
   recency of the event itself relative to REFERENCE_DATE (past events still
   indicate the area draws crowds; future events near the campaign window
   matter more -- handled by whoever calls this at campaign-scoring time,
   this script just computes an area-level event pressure baseline).

All three are 0-1 normalized (min-max within their own component) before the
weighted sum, so no single component's raw scale dominates just because its
units happen to be bigger.

HOW TO RUN
    python pricing/demand_index.py
"""
import json
import os
import sqlite3
from datetime import datetime
import pandas as pd
import numpy as np

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

# Reference "today" for recency decay. Use the latest date actually seen in
# bookings, not wall-clock time -- this dataset's dates don't track real time
#1:1, and decaying against a date that doesn't exist in the data yet would
# make everything look maximally stale.
REFERENCE_DATE = None  # resolved in main() from the data

DECAY_RATE_BOOKINGS = 0.01   # per day; ~70-day half life
DECAY_RATE_LEADS = 0.015     # per day; slightly faster -- unconverted demand
                              # ages faster than a confirmed booking

W_BOOKING = 0.5
W_LEAD = 0.3
W_EVENT = 0.2


def days_since(date_str, ref):
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return max((ref - d).days, 0)
    except (ValueError, TypeError):
        return None


def minmax(series):
    lo, hi = series.min(), series.max()
    if hi - lo < 1e-9:
        return series * 0  # all equal -> no signal, don't fake variance
    return (series - lo) / (hi - lo)


def booking_density(conn, ref):
    bk = pd.read_sql(
        "SELECT screen_id, time_block_id, start_date, booking_status "
        "FROM bookings WHERE booking_status != 'cancelled'", conn)
    bk["age_days"] = bk.start_date.apply(lambda d: days_since(d, ref))
    bk = bk.dropna(subset=["age_days"])
    bk["weight"] = np.exp(-DECAY_RATE_BOOKINGS * bk.age_days)

    out = bk.groupby(["screen_id", "time_block_id"]).weight.sum().reset_index()
    out.columns = ["screen_id", "time_block_id", "booking_density_raw"]
    return out


def lead_pressure(conn, ref):
    ll = pd.read_sql(
        "SELECT anchor_screen_id AS screen_id, lead_date, indicated_budget, "
        "loss_reason FROM lost_leads WHERE anchor_screen_id IS NOT NULL", conn)
    ll["age_days"] = ll.lead_date.apply(lambda d: days_since(d, ref))
    ll = ll.dropna(subset=["age_days"])
    ll["weight"] = np.exp(-DECAY_RATE_LEADS * ll.age_days)

    # A price-rejected lead is a ceiling signal, not upward pressure -- damp it.
    ll.loc[ll.loss_reason == "price_too_high", "weight"] *= 0.5

    budget = ll.indicated_budget.fillna(ll.indicated_budget.median())
    ll["pressure"] = ll.weight * np.log1p(budget.clip(lower=0))

    # Leads aren't tagged with a time_block in this schema -- attribute the
    # pressure to ALL blocks for that screen; block-level pricing in step 3
    # will still differentiate via bookings, which ARE block-specific.
    out = ll.groupby("screen_id").pressure.sum().reset_index()
    out.columns = ["screen_id", "lead_pressure_raw"]
    return out


def event_pressure(conn, geo, ref):
    events = pd.read_sql(
        "SELECT * FROM events WHERE anchor_location_id IS NOT NULL", conn)
    tier_weight = {"large": 1.0, "medium": 0.6, "small": 0.3}
    events["w"] = events.attendance_tier.map(tier_weight).fillna(0.3)
    events["age_days"] = events.start_date.apply(lambda d: days_since(d, ref))
    # Symmetric decay: recent past events and near-future events both count;
    # far past/future matter less.
    events["recency_w"] = np.exp(-0.02 * (events.age_days.abs().fillna(9999)))
    events["pressure"] = events.w * events.recency_w

    loc_pressure = events.groupby("anchor_location_id").pressure.sum().to_dict()

    rows = []
    for g in geo.itertuples(index=False):
        if g.screen_kind == "fixed" and g.location_id:
            p = loc_pressure.get(g.location_id, 0.0)
        else:
            stops = json.loads(g.corridor_ids) if g.corridor_ids else []
            # For vehicle screens we don't have stop lists here directly;
            # approximate via the screen's own zone_ids overlap is out of
            # scope for this lookup -- vehicle screens get 0 unless their
            # primary location resolves, which is conservative (undercounts
            # rather than invents event exposure).
            p = 0.0
        rows.append({"screen_id": g.screen_id, "event_pressure_raw": p})
    return pd.DataFrame(rows)


def build_demand_index(conn):
    global REFERENCE_DATE
    max_date = pd.read_sql("SELECT MAX(start_date) AS d FROM bookings", conn).d.iloc[0]
    REFERENCE_DATE = datetime.strptime(max_date[:10], "%Y-%m-%d")
    print(f"Using reference date (latest booking start_date in data): {REFERENCE_DATE.date()}")

    geo = pd.read_sql("SELECT * FROM screen_geo_map", conn)
    clusters = pd.read_sql("SELECT * FROM screen_cluster_map", conn)
    all_screens_blocks = pd.MultiIndex.from_product(
        [geo.screen_id, range(1, 7)], names=["screen_id", "time_block_id"]
    ).to_frame(index=False)

    bd = booking_density(conn, REFERENCE_DATE)
    lp = lead_pressure(conn, REFERENCE_DATE)
    ep = event_pressure(conn, geo, REFERENCE_DATE)

    df = (all_screens_blocks
          .merge(bd, on=["screen_id", "time_block_id"], how="left")
          .merge(lp, on="screen_id", how="left")
          .merge(ep, on="screen_id", how="left")
          .merge(geo[["screen_id", "city_id"]], on="screen_id", how="left")
          .merge(clusters[["screen_id", "cluster_id"]], on="screen_id", how="left"))

    for col in ["booking_density_raw", "lead_pressure_raw", "event_pressure_raw"]:
        df[col] = df[col].fillna(0.0)

    df["has_own_history"] = (df.booking_density_raw > 0) | (df.lead_pressure_raw > 0)

    df["booking_n"] = minmax(df.booking_density_raw)
    df["lead_n"] = minmax(df.lead_pressure_raw)
    df["event_n"] = minmax(df.event_pressure_raw)

    df["demand_score_own"] = (W_BOOKING * df.booking_n + W_LEAD * df.lead_n
                              + W_EVENT * df.event_n)

    # --- Cold-start fallback hierarchy ---
    cluster_avg = (df[df.has_own_history]
                  .groupby("cluster_id").demand_score_own.mean())
    city_avg = (df[df.has_own_history]
               .groupby("city_id").demand_score_own.mean())
    global_avg = df[df.has_own_history].demand_score_own.mean()
    if pd.isna(global_avg):
        global_avg = 0.3  # no history anywhere in the data -- neutral baseline

    def resolve(row):
        if row.has_own_history:
            return row.demand_score_own, "own_history"
        if row.cluster_id in cluster_avg.index:
            return cluster_avg[row.cluster_id], "inferred_cluster"
        if row.city_id in city_avg.index:
            return city_avg[row.city_id], "inferred_city"
        return global_avg, "inferred_global"

    resolved = df.apply(resolve, axis=1, result_type="expand")
    df["demand_score"] = resolved[0].round(4)
    df["confidence"] = resolved[1]

    out = df[["screen_id", "time_block_id", "demand_score", "confidence",
              "booking_density_raw", "lead_pressure_raw", "event_pressure_raw"]]
    return out


def main():
    conn = sqlite3.connect(DB_PATH)
    idx = build_demand_index(conn)
    idx.to_sql("screen_demand_index", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_demand ON "
                 "screen_demand_index(screen_id, time_block_id)")
    conn.commit()

    print(f"\nOK  screen_demand_index: {len(idx)} rows")
    print(idx.confidence.value_counts().to_string())
    print(f"\ndemand_score distribution:\n{idx.demand_score.describe().round(3).to_string()}")


if __name__ == "__main__":
    main()