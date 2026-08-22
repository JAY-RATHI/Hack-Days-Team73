"""
D4: Impressions Optimizer.

Takes Person B's scored_priced_screens (D2+D3 merged output) and produces
the actual PACKAGE the sales rep would propose: which (screen, time_block)
pairs to include, respecting budget, and maximizing dedup-adjusted
projected impressions -- not just returning the top-N by relevance score.

=== WHY A REAL OPTIMIZER, NOT JUST "TAKE THE TOP N" ===
The deck's problem statement is explicit that reach is estimated with
real non-linearities and real overlap, not summed naively:
  - "Ads with higher number of slots per minute have higher chances of
    being noticed... account for non-linearity" -> saturating slot curve.
  - "Boards on the same route share an audience... treating them as
    independent reach is a modeling error" -> cluster/overlap dedup.
  - "A bundle isn't three independent decisions... joint pricing and
    allocation" -> one greedy pass over the WHOLE candidate pool at once,
    not per-screen decisions made in isolation.

=== IMPRESSIONS MODEL ===
daily_riders_exposed:
    fixed screens   -> corridor_timeblock_ridership.avg_daily_block_riders
                       (already a daily figure)
    vehicle screens -> avg_trip_ridership * (n_trips / n_days)
                       (converts a per-trip average into a comparable daily
                       figure -- Person A explicitly flagged these two
                       numbers as not directly comparable; this is the fix)

attention_factor: screen position affects real dwell/attention. Values are
a judgment call (there's no real "attention" column in the data) --
documented as such, easy to retune.

slot_factor: 1 - exp(-SLOT_SATURATION_K * slots_booked_per_day), saturating
near 1.0 by 6 slots (the max rotation loop size per dim_slot's design).

base_daily_impressions = daily_riders_exposed * attention_factor * slot_factor

=== DEDUP ===
Within `screen_cluster_map.cluster_id` (screens sharing an exact audience --
same stop or same corridor): each additional selected pair in the same
cluster counts at CLUSTER_DEDUP_DECAY^n of its raw impressions, n = how many
pairs from that cluster are already in the package. This is applied
DURING selection (order matters -- the highest-efficiency pair in a cluster
gets full credit, subsequent ones from the same cluster are worth less).

Cross-cluster soft overlap (`corridor_overlap` Jaccard) applies an
additional discount when a newly added corridor overlaps stops with an
already-selected corridor, even if they're in different hard clusters.

=== SELECTION ===
Greedy by efficiency = (relevance_score * marginal_dedup_impressions) / cost.
This blends FIT (relevance) and REACH (impressions) per dollar, not reach
alone -- a high-traffic screen that's a poor audience fit for THIS campaign
shouldn't win over a well-matched one just because it has bigger numbers.

If spec.budget is None: no stopping constraint from cost -- take the top
DEFAULT_TOP_N_UNCONSTRAINED pairs by efficiency instead, clearly labeled.

If spec.duration_days is None: costs/impressions are reported PER DAY,
never multiplied by a guessed campaign length -- same "don't invent a
number" discipline as budget handling in brief_parser.py.

HOW TO RUN (standalone test)
    python optimization/impressions_optimizer.py
"""
import json
import os
import sqlite3
import pandas as pd
import numpy as np

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

# --- Judgment-call constants, documented so they're easy to retune ---
SLOT_SATURATION_K = 0.5          # slot_factor(1)=0.39, (2)=0.63, (6)=0.95
MAX_ROTATION_SLOTS = 6            # dim_slot's loop size -- hard ceiling
CLUSTER_DEDUP_DECAY = 0.5         # 2nd pair in a cluster worth 50%, 3rd 25%...
OVERLAP_DISCOUNT_WEIGHT = 0.5     # soft discount strength from corridor_overlap
DEFAULT_TOP_N_UNCONSTRAINED = 30
MIN_RELEVANCE_TO_CONSIDER = 0.05  # drop near-zero-fit screens before optimizing

# PERFORMANCE SAFEGUARD -- found via real-scale testing: the exact greedy loop
# is roughly O(n^2) (each iteration re-scans the remaining pool, and once
# budget is exhausted it was checking and dropping ONE over-budget row at a
# time instead of stopping). At real scale (37,014 candidates for one city)
# this took an estimated 2+ HOURS instead of seconds. Fix has two parts:
#   1. Pre-filter to the top PRE_FILTER_TOP_K candidates by a cheap raw
#      efficiency metric (no dedup/overlap adjustment yet) BEFORE running the
#      expensive exact greedy loop. Screens far down this ranking essentially
#      never survive dedup discounting into the final ~15-30 selected anyway.
#   2. Stop the loop immediately once even the CHEAPEST remaining candidate
#      can't fit the remaining budget, instead of checking every row.
PRE_FILTER_TOP_K = 500

ATTENTION_FACTOR = {
    # Judgment call -- no real "attention"/dwell column exists in the data.
    # Platform waiting implies longer dwell than a quick entrance/exit pass;
    # vehicle-interior screens are seen continuously during the ride.
    "platform": 1.3,
    "entrance_exit": 0.8,
    "left": 1.1, "right": 1.1, "top": 1.0,  # vehicle interior / fixed side panels
}
DEFAULT_ATTENTION = 1.0


def daily_riders_exposed(row, ridership_lookup):
    """Comparable daily audience figure, fixed vs vehicle (see module docstring)."""
    if row["screen_kind"] == "fixed":
        return row.get("riders_in_block") or 0.0
    corridor = row.get("primary_corridor_id")
    r = ridership_lookup.get((corridor, row["time_block_id"]))
    if r is None:
        return row.get("riders_in_block") or 0.0  # fallback to whatever's in feature_dict
    avg_trip, n_trips, n_days = r
    trips_per_day = n_trips / max(n_days, 1)
    return avg_trip * trips_per_day


def slot_factor(slots_booked_per_day):
    slots = max(1, min(slots_booked_per_day, MAX_ROTATION_SLOTS))
    return 1 - np.exp(-SLOT_SATURATION_K * slots)


def build_candidates(scored_priced_df, conn, rotation_slots_per_day):
    """Attach everything the impressions model needs to each candidate row."""
    screen_ids = scored_priced_df.screen_id.unique().tolist()
    placeholders = ",".join("?" * len(screen_ids))

    geo = pd.read_sql(
        f"SELECT screen_id, screen_kind, primary_corridor_id, position "
        f"FROM screen_geo_map g LEFT JOIN screens s USING(screen_id) "
        f"WHERE g.screen_id IN ({placeholders})", conn, params=screen_ids)
    clusters = pd.read_sql(
        f"SELECT screen_id, cluster_id FROM screen_cluster_map "
        f"WHERE screen_id IN ({placeholders})", conn, params=screen_ids)
    profiles = pd.read_sql(
        f"SELECT screen_id, time_block_id, feature_dict FROM screen_audience_profile "
        f"WHERE screen_id IN ({placeholders})", conn, params=screen_ids)

    ridership = pd.read_sql(
        "SELECT corridor_id, time_block_id, avg_trip_ridership, n_trips, n_days "
        "FROM corridor_timeblock_ridership WHERE day_type='weekday'", conn)
    ridership_lookup = {
        (r.corridor_id, r.time_block_id): (r.avg_trip_ridership, r.n_trips, r.n_days)
        for r in ridership.itertuples(index=False)
    }

    df = (scored_priced_df.merge(geo, on="screen_id", how="left")
          .merge(clusters, on="screen_id", how="left")
          .merge(profiles, on=["screen_id", "time_block_id"], how="left"))

    df["feat"] = df["feature_dict"].apply(lambda s: json.loads(s) if pd.notna(s) else {})
    df["riders_in_block"] = df["feat"].apply(lambda f: f.get("riders_in_block"))

    df["daily_riders"] = df.apply(lambda r: daily_riders_exposed(r, ridership_lookup), axis=1)
    df["attention"] = df["position"].map(ATTENTION_FACTOR).fillna(DEFAULT_ATTENTION)
    df["slots"] = rotation_slots_per_day
    df["slot_f"] = df["slots"].apply(slot_factor)
    df["base_daily_impressions"] = df.daily_riders * df.attention * df.slot_f

    df["cost_per_day"] = df.price_target * df.slots
    return df


def get_corridor_overlap(conn):
    ov = pd.read_sql("SELECT * FROM corridor_overlap", conn)
    lookup = {}
    for r in ov.itertuples(index=False):
        lookup[(r.corridor_a, r.corridor_b)] = r.jaccard
        lookup[(r.corridor_b, r.corridor_a)] = r.jaccard
    return lookup


def optimize_package(scored_priced_df, spec, conn):
    """Returns (package_df, summary_dict). package_df is the selected subset
    of scored_priced_df's rows with impressions/cost columns added."""
    rotation_slots = spec.get("rotation_slots_per_day") or 1
    duration_days = spec.get("duration_days")  # may be None -- see docstring
    budget = spec.get("budget")  # may be None -- unconstrained

    pool = scored_priced_df[scored_priced_df.relevance_score >= MIN_RELEVANCE_TO_CONSIDER].copy()
    if pool.empty:
        return pd.DataFrame(), {"note": "no candidates above minimum relevance threshold"}

    cand = build_candidates(pool, conn, rotation_slots)
    overlap_lookup = get_corridor_overlap(conn)

    # --- PERFORMANCE FIX, part 1: pre-filter by cheap raw efficiency BEFORE
    # running the expensive exact greedy loop. Uncapped base_daily_impressions
    # (no dedup/overlap adjustment) is a fine proxy for this initial cut --
    # dedup can only ever REDUCE a candidate's value, never increase it, so a
    # candidate that's weak even before dedup will certainly still be weak
    # after it.
    raw_efficiency = (cand.relevance_score * cand.base_daily_impressions) / cand.cost_per_day.clip(lower=0.01)
    cand = cand.loc[raw_efficiency.sort_values(ascending=False).index[:PRE_FILTER_TOP_K]].copy()

    use_budget_constraint = budget is not None and duration_days is not None
    stop_by_top_n = not use_budget_constraint

    # Greedy selection loop over the pre-filtered pool ONLY. Recomputing
    # "current best next pick" each iteration (rather than sorting once up
    # front) because a pair's MARGINAL value depends on what's already been
    # selected (cluster dedup, corridor overlap) -- this is what makes it a
    # joint decision, not N independent ones. Bounded to PRE_FILTER_TOP_K
    # rows, so this is now at most ~500^2 operations, not 37,000^2.
    selected_idx = []
    cluster_counts = {}
    selected_corridors = set()
    total_cost = 0.0
    remaining = cand

    while not remaining.empty:
        # --- PERFORMANCE FIX, part 2: stop the instant nothing remaining
        # can possibly fit, instead of checking every row one at a time.
        if use_budget_constraint:
            cheapest_possible = remaining.cost_per_day.min() * duration_days
            if total_cost + cheapest_possible > budget:
                break

        n_in_cluster = remaining["cluster_id"].map(cluster_counts).fillna(0)
        dedup_factor = CLUSTER_DEDUP_DECAY ** n_in_cluster

        def overlap_discount(corridor):
            if not selected_corridors or pd.isna(corridor):
                return 1.0
            max_j = max((overlap_lookup.get((corridor, c), 0.0) for c in selected_corridors), default=0.0)
            return 1 - OVERLAP_DISCOUNT_WEIGHT * max_j

        overlap_f = remaining["primary_corridor_id"].apply(overlap_discount)
        marginal_impressions = remaining.base_daily_impressions * dedup_factor * overlap_f
        efficiency = (remaining.relevance_score * marginal_impressions) / remaining.cost_per_day.clip(lower=0.01)

        best_i = efficiency.idxmax()
        best_row = remaining.loc[best_i]
        best_marginal = marginal_impressions.loc[best_i]

        pair_cost = best_row.cost_per_day if duration_days is None else best_row.cost_per_day * duration_days

        if use_budget_constraint and total_cost + pair_cost > budget:
            remaining = remaining.drop(index=best_i)
            continue

        selected_idx.append((best_i, best_marginal, pair_cost))
        cluster_counts[best_row.cluster_id] = cluster_counts.get(best_row.cluster_id, 0) + 1
        if pd.notna(best_row.primary_corridor_id):
            selected_corridors.add(best_row.primary_corridor_id)
        total_cost += pair_cost
        remaining = remaining.drop(index=best_i)

        if stop_by_top_n and len(selected_idx) >= DEFAULT_TOP_N_UNCONSTRAINED:
            break

    if not selected_idx:
        return pd.DataFrame(), {"note": "no screens fit within budget", "budget": budget}

    ambiguous_budget_duration = duration_days is None and budget is not None

    idxs, marginals, costs = zip(*selected_idx)
    package = cand.loc[list(idxs)].copy()
    package["marginal_daily_impressions"] = marginals
    package["pair_cost"] = costs

    total_impressions_daily = package.marginal_daily_impressions.sum()
    summary = {
        "n_screen_timeblock_pairs": len(package),
        "n_unique_screens": package.screen_id.nunique(),
        "n_clusters_represented": package.cluster_id.nunique(),
        "total_cost": round(total_cost, 2),
        "budget": budget,
        "budget_utilization_pct": round(100 * total_cost / budget, 1) if (budget and not ambiguous_budget_duration) else None,
        "duration_days": duration_days,
        "cost_basis": "total_campaign" if duration_days is not None else "PER_DAY (duration_days not stated)",
        "total_projected_impressions_per_day": round(total_impressions_daily, 0),
        "total_projected_impressions_per_week": round(total_impressions_daily * 7, 0),
        "avg_relevance_score_selected": round(package.relevance_score.mean(), 3),
    }
    if ambiguous_budget_duration:
        summary["caveat"] = (
            f"Campaign duration wasn't stated, so ${budget:,.0f} couldn't be applied as a "
            f"total-campaign budget cap -- it would be misread as a per-day limit, producing "
            f"an oversized package. Showing the top {DEFAULT_TOP_N_UNCONSTRAINED} most efficient "
            f"pairs instead (same as the no-budget case). Specify a campaign duration for a "
            f"real budget-constrained package."
        )
    return package, summary


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.getcwd())
    from pricing.merge_scored_priced import build_scored_priced_screens

    fake_spec = {
        "city_hint": "Las Hackland", "target_zones_text": [],
        "target_age_min": 28, "target_age_max": 50, "target_income_tier": "high",
        "audience_descriptors": ["urban professionals", "commuters"],
        "poi_affinities": ["office_park", "corporate_campus"],
        "objective": "conversion", "preferred_dayparts": [],
        "budget": 40000.0, "duration_days": 45, "requires_broad_coverage": False,
        "exclusion_criteria": ["exclude bus-rear screens"],
        "location_type_preference": None, "rotation_slots_per_day": 1,
        "raw_brief_text": "(test)",
    }

    conn = sqlite3.connect(DB_PATH)
    scored_priced, meta = build_scored_priced_screens(fake_spec, conn)
    print("D2+D3 meta:", meta)
    print(f"{len(scored_priced)} candidates before optimization\n")

    package, summary = optimize_package(scored_priced, fake_spec, conn)
    print("PACKAGE SUMMARY:")
    print(json.dumps(summary, indent=2))
    print(f"\nTop 10 of {len(package)} selected pairs:")
    print(package.sort_values("marginal_daily_impressions", ascending=False)
          .head(10)[["screen_id", "time_block_id", "cluster_id", "relevance_score",
                     "marginal_daily_impressions", "pair_cost"]]
          .to_string(index=False))