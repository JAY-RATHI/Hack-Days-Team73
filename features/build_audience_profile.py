"""
IMPLEMENTATION STEPS 3-6 (rewritten): the real screen_audience_profile.

=== THE ARCHITECTURAL CHANGE, AND WHY ===
The original plan said: build a feature dict per screen, then send batches of
30-50 screens to Claude to write the profile text.

The real data makes that impossible on a hackathon clock:
    11,163 screens x 6 time blocks = 66,978 profile rows
    / 40 per batch = ~1,675 Claude calls
That is hours of wall-clock time and a large API bill, for text that most
screens will never surface in any recommendation.

So this splits into two layers, WITHOUT changing the contract Person B codes
against:
    Layer 1 (this script): compute feature_dict for all ~67K rows and write
        a rule-based profile_text from a template. Deterministic, no API
        calls, runs in seconds, costs nothing, and is fully explainable --
        which the judging rubric rewards more than pretty prose.
    Layer 2 (enrich_profiles_llm.py): re-write profile_text with Claude for
        ONLY the screens that actually appear in a recommendation (top ~20-40
        per campaign). Cached, so each screen is only ever polished once.

The table's columns are identical either way. `profile_source` tells you which
layer produced a given row ('rule' or 'llm').

=== HOW PROXIMITY WORKS NOW (no lat/lon in this data) ===
points_of_interest has `anchor_location_id` + `distance_to_location_km`
already computed. So "nearby POIs" is a join on anchor_location_id, filtered
by distance -- no haversine needed.

  - FIXED screen  -> POIs anchored to its own location_id
  - VEHICLE screen -> POIs anchored to any stop along its corridor, averaged
                      per stop (a bus rider passes many stops, so its POI
                      exposure is the corridor's average, not a sum)

POI weighting: est_daily_footfall / distance, then
  x0.6 if side_of_road == 'far_side'  (harder to notice from across the road)
  x1.5 if the POI's peak_daypart matches this time block's daypart

NOTE ON side_of_road vs screens.position: I did NOT use screens.position
(top/left/right) as a facing filter. `position` describes where on the
shelter the panel sits, not which way it faces -- there's no field in this
data that gives true facing direction. Using far/near side as a soft weight
is defensible; a hard filter on `position` would be inventing information.
Flag this at the sync in case someone disagrees.

OUTPUT TABLE: screen_audience_profile
    screen_id, time_block_id, profile_text, audience_tags, feature_dict,
    confidence, profile_source

HOW TO RUN (after screen_geo_map, ridership_by_block)
    python features/build_audience_profile.py
"""
import json
import os
import sqlite3
from collections import defaultdict
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

MAX_POI_DIST_KM = 1.0    # POIs further than this don't meaningfully drive attention
FAR_SIDE_WEIGHT = 0.6
DAYPART_MATCH_BOOST = 1.5
# CONFIDENCE TIERS -- calibrated to the real data, not guessed.
# The raw data has 1,375 POIs spread over 910 locations: ~1.5 POIs per stop.
# So a "needs 3+ POIs" bar (the original plan's guess) would mark nearly every
# fixed screen low-confidence and the flag would carry no information.
# Instead:
#   high   = POI signal AND ridership signal  -> trust the profile
#   medium = one of the two is missing        -> usable, note the gap
#   low    = neither                          -> pure zone-average fallback,
#            D2 should down-weight these and the UI should say so out loud
POI_STRONG = 2           # >= this many nearby POIs counts as a real POI signal
DAY_TYPE = "weekday"     # profiles built on weekday patterns


# ---------------------------------------------------------------- POI layer
def build_location_poi(pois, dayparts):
    """POI exposure per (location_id, daypart). Returns nested dict."""
    pois = pois[pois.distance_to_location_km <= MAX_POI_DIST_KM].copy()
    pois["base_w"] = (pois.est_daily_footfall
                      / pois.distance_to_location_km.clip(lower=0.05))
    pois.loc[pois.side_of_road == "far_side", "base_w"] *= FAR_SIDE_WEIGHT

    out = defaultdict(lambda: defaultdict(lambda: {
        "poi_weight_total": 0.0, "poi_count": 0,
        "poi_type_weights": defaultdict(float), "has_hub": False,
    }))

    for p in pois.itertuples(index=False):
        for dp in dayparts:
            w = p.base_w * (DAYPART_MATCH_BOOST if p.peak_daypart == dp else 1.0)
            cell = out[p.anchor_location_id][dp]
            cell["poi_weight_total"] += w
            cell["poi_count"] += 1
            cell["poi_type_weights"][p.poi_type] += w
            if p.is_network_hub:
                cell["has_hub"] = True
    return out


def merge_poi_cells(cells):
    """Average several locations' POI exposure (for a corridor's stops)."""
    if not cells:
        return {"poi_weight_total": 0.0, "poi_count": 0,
                "poi_type_weights": {}, "has_hub": False}
    n = len(cells)
    types = defaultdict(float)
    for c in cells:
        for t, w in c["poi_type_weights"].items():
            types[t] += w / n
    return {
        "poi_weight_total": sum(c["poi_weight_total"] for c in cells) / n,
        "poi_count": int(sum(c["poi_count"] for c in cells) / n),
        "poi_type_weights": dict(types),
        "has_hub": any(c["has_hub"] for c in cells),
    }


# -------------------------------------------------------------- demographics
def blend_zones(zone_ids, zdemo):
    """Weighted-average demographics across the zones a corridor passes."""
    rows = zdemo[zdemo.zone_id.isin(zone_ids)]
    if rows.empty:
        return None
    w = rows.resident_population.clip(lower=1)
    def wavg(col):
        return float((rows[col] * w).sum() / w.sum())
    return {
        "zone_names": rows.zone_name.tolist()[:4],
        "median_age": round(wavg("median_age"), 1),
        "pct_18_34": round(wavg("pct_age_18_34"), 1),
        "pct_35_54": round(wavg("pct_age_35_54"), 1),
        "pct_55_plus": round(wavg("pct_age_55_plus"), 1),
        "income_index": round(wavg("income_index"), 1),
        "pct_bachelor_or_higher": round(wavg("pct_bachelor_or_higher"), 1),
        "density": int(wavg("population_density_per_sqkm")),
        "daytime_multiplier": round(wavg("daytime_population_multiplier"), 2),
        "dominant_occupation": rows.dominant_occupation.mode().iloc[0],
    }


def income_tier(idx):
    if idx is None: return "unknown"
    return "high" if idx >= 120 else "mid" if idx >= 90 else "value"


def footfall_tier(v, p33, p66):
    if v is None or v <= 0: return "unknown"
    return "high" if v >= p66 else "medium" if v >= p33 else "low"


# ------------------------------------------------------------- text template
def make_text(row):
    kind = ("bus/coach interior" if row["screen_kind"] == "vehicle"
            else "roadside/platform panel")
    parts = [f"{row['daypart'].capitalize()} block, {kind}"]

    if row.get("zone_names"):
        parts.append(f"serving {', '.join(row['zone_names'][:2])}")
    if row.get("income_index"):
        parts.append(f"{income_tier(row['income_index'])}-income area "
                     f"({row.get('dominant_occupation','mixed')} skew)")
    if row.get("riders_in_block"):
        parts.append(f"~{int(row['riders_in_block']):,} riders in this block")

    # Only make specific local claims when there IS a local signal.
    # A 'low' confidence row naming "nearby draws: university" while also
    # saying "no local signal" is self-contradicting -- and in a sales
    # proposal it's an unsupported claim. Suppress it.
    if row["confidence"] != "low":
        tw = row.get("poi_type_weights") or {}
        if tw:
            top = sorted(tw.items(), key=lambda kv: -kv[1])[:2]
            parts.append("nearby draws: " + ", ".join(t.replace("_", " ") for t, _ in top))
        if row.get("has_hub"):
            parts.append("network hub adjacency")

    if row["confidence"] == "low":
        parts.append("NO local signal - zone averages only, treat as indicative")
    elif row["confidence"] == "medium":
        missing = "ridership" if not row.get("riders_in_block") else "nearby-POI"
        parts.append(f"partial data ({missing} signal absent)")
    return "; ".join(parts) + "."


def make_tags(row):
    tags = [row["daypart"], row["screen_kind"]]
    if row.get("income_index"):
        tags.append(f"{income_tier(row['income_index'])}-income")
    if row.get("dominant_occupation"):
        tags.append(row["dominant_occupation"])
    tags.append(f"{row['footfall_tier']}-footfall")
    # Same rule as make_text: no POI/hub tags without a real local signal,
    # otherwise D2 will score a no-data screen as if it had a university
    # next door.
    if row["confidence"] != "low":
        tw = row.get("poi_type_weights") or {}
        if tw:
            tags.append(max(tw, key=tw.get))
        if row.get("has_hub"):
            tags.append("network-hub")
    if row["confidence"] == "low":
        tags.append("low-data-fallback")
    elif row["confidence"] == "medium":
        tags.append("partial-data")
    return tags


# --------------------------------------------------------------------- main
def main():
    conn = sqlite3.connect(DB_PATH)

    geo = pd.read_sql("SELECT * FROM screen_geo_map", conn)
    screens = pd.read_sql("SELECT screen_id, screen_type, position, screen_size FROM screens", conn)
    slots = pd.read_sql("SELECT * FROM dim_slot", conn)
    pois = pd.read_sql("SELECT * FROM points_of_interest", conn)
    zdemo = pd.read_sql("SELECT * FROM zone_demographics", conn)
    route_stops = pd.read_sql("SELECT corridor_id, location_id FROM route_stops", conn).drop_duplicates()
    rider = pd.read_sql(
        f"SELECT * FROM corridor_timeblock_ridership WHERE day_type = '{DAY_TYPE}'", conn)

    geo = geo.merge(screens, on="screen_id", how="left")
    dayparts = slots.nearest_daypart.unique().tolist()
    block_to_daypart = dict(zip(slots.time_block_id, slots.nearest_daypart))

    print("Building POI exposure per location/daypart...")
    loc_poi = build_location_poi(pois, dayparts)
    corridor_to_stops = route_stops.groupby("corridor_id")["location_id"].apply(list).to_dict()

    # Ridership lookups
    rider_daily = {(r.corridor_id, r.time_block_id): r.avg_daily_block_riders
                   for r in rider.itertuples(index=False)}
    rider_trip = {(r.corridor_id, r.time_block_id): r.avg_trip_ridership
                  for r in rider.itertuples(index=False)}

    # Commuter score per corridor: share of daily riders in the 2 peak blocks.
    tot = rider.groupby("corridor_id").avg_daily_block_riders.sum()
    peak = (rider[rider.time_block_id.isin([2, 5])]
            .groupby("corridor_id").avg_daily_block_riders.sum())
    commuter_score = (peak / tot.clip(lower=1)).round(3).to_dict()

    zone_cache = {}
    print(f"Assembling {len(geo)} screens x {len(slots)} blocks...")

    records = []
    for g in geo.itertuples(index=False):
        corridors = json.loads(g.corridor_ids) if g.corridor_ids else []
        zone_ids = json.loads(g.zone_ids) if g.zone_ids else []

        zkey = tuple(sorted(zone_ids))
        if zkey not in zone_cache:
            zone_cache[zkey] = blend_zones(zone_ids, zdemo)
        demo = zone_cache[zkey] or {}

        # Which locations' POIs this screen is exposed to
        if g.screen_kind == "fixed" and g.location_id:
            poi_locs = [g.location_id]
        else:
            poi_locs = [s for c in corridors for s in corridor_to_stops.get(c, [])]

        for tb in slots.time_block_id:
            dp = block_to_daypart[tb]
            cells = [loc_poi[l][dp] for l in poi_locs if l in loc_poi]
            poi = merge_poi_cells(cells)

            if g.screen_kind == "vehicle":
                riders = max((rider_trip.get((c, tb), 0) for c in corridors), default=0)
            else:
                riders = sum(rider_daily.get((c, tb), 0) for c in corridors)

            cscore = max((commuter_score.get(c, 0) for c in corridors), default=0)
            has_poi = poi["poi_count"] >= POI_STRONG
            has_riders = riders > 0
            if has_poi and has_riders:
                conf = "high"
            elif has_poi or has_riders:
                conf = "medium"
            else:
                conf = "low"

            records.append({
                "screen_id": g.screen_id,
                "time_block_id": int(tb),
                "daypart": dp,
                "screen_kind": g.screen_kind,
                "screen_size": g.screen_size,
                "riders_in_block": round(riders, 1),
                "commuter_score": cscore,
                "poi_weight_total": round(poi["poi_weight_total"], 1),
                "poi_count": poi["poi_count"],
                "poi_type_weights": {k: round(v, 1) for k, v in poi["poi_type_weights"].items()},
                "has_hub": poi["has_hub"],
                "confidence": conf,
                **demo,
            })

    df = pd.DataFrame(records)

    p33, p66 = df.riders_in_block.quantile([0.33, 0.66])
    df["footfall_tier"] = df.riders_in_block.apply(lambda v: footfall_tier(v, p33, p66))

    print("Writing profile text...")
    rows = df.to_dict("records")
    out = pd.DataFrame({
        "screen_id": df.screen_id,
        "time_block_id": df.time_block_id,
        "profile_text": [make_text(r) for r in rows],
        "audience_tags": [json.dumps(make_tags(r)) for r in rows],
        "feature_dict": [json.dumps(r, default=str) for r in rows],
        "confidence": df.confidence,
        "profile_source": "rule",
    })

    out.to_sql("screen_audience_profile", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prof ON "
                 "screen_audience_profile(screen_id, time_block_id)")
    conn.commit()

    print(f"\nOK  screen_audience_profile: {len(out)} rows")
    print(out.confidence.value_counts().to_string())
    low = out[out.confidence == "low"].screen_id.unique()
    print(f"\n{len(low)} distinct screens hit the pure-fallback path "
          f"(good demo material -- show one of these).")
    print(f"    examples: {list(low[:5])}")
    print("\nSample profile:")
    print(f"  {out.profile_text.iloc[0]}")


if __name__ == "__main__":
    main()