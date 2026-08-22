"""
Builds a DESCRIPTIVE, screen-by-screen recommendation from a run_campaign()
result -- the thing a sales rep would actually put in front of a client.

The batch runner's default report only showed a bare table (screen_id, score,
price). That's not a proposal. This module enriches every selected screen with
everything needed to justify it:

  WHERE it is      -> location name, type (metro station / bus stop), city, zone
  WHEN it runs     -> time block with real clock hours and daypart label
  WHAT it costs    -> floor / target / cap band, slots/day, per-day and campaign total
  WHO it reaches   -> audience profile text, tags, riders exposed, demographics
  WHY it was picked -> the relevance reason, plus the demand/confidence basis
  WHAT'S SHARED    -> its audience cluster, so overlap is visible not hidden

OUTPUTS (per brief)
  <name>_recommendation.json  -- complete structured detail, machine-readable
  <name>_recommendation.md    -- same content, bulleted and readable
and across all briefs:
  all_campaigns_screens.csv   -- one flat row per recommended screen

IMPRESSIONS NOTE (important, don't misread these numbers)
`marginal_daily_impressions` is a screen's contribution AFTER audience-overlap
discounting -- it is deliberately NOT the screen's standalone reach. Both are
reported (`base_daily` vs `marginal_daily`) so the difference is visible: a
big gap means that screen shares an audience with something else already in
the package. Campaign totals sum the MARGINAL figures, which is why the total
is lower than adding up standalone reach -- that's the deck's "boards on the
same route share an audience" nuance made explicit rather than papered over.
"""
import json
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")


# --------------------------------------------------------------- DB lookups
def load_lookups(conn):
    slots = pd.read_sql("SELECT * FROM dim_slot", conn).set_index("time_block_id")
    locations = pd.read_sql(
        "SELECT location_id, name, location_type, city_id, zone_id FROM locations",
        conn).set_index("location_id")
    zones = pd.read_sql(
        "SELECT zone_id, zone_name, income_index, median_age, dominant_occupation, "
        "population_density_per_sqkm FROM zone_demographics", conn).set_index("zone_id")
    cities = pd.read_sql("SELECT city_id, city_name, market_tier FROM cities",
                         conn).set_index("city_id")
    screens = pd.read_sql(
        "SELECT screen_id, screen_type, position, screen_size FROM screens",
        conn).set_index("screen_id")
    geo = pd.read_sql("SELECT * FROM screen_geo_map", conn).set_index("screen_id")
    routes = (pd.read_sql("SELECT DISTINCT corridor_id, route_name FROM route_stops", conn)
              .groupby("corridor_id")["route_name"].apply(list).to_dict())
    return {"slots": slots, "locations": locations, "zones": zones,
            "cities": cities, "screens": screens, "geo": geo, "routes": routes}


def load_profiles(conn, screen_ids, time_blocks):
    if not screen_ids:
        return {}
    q = ("SELECT screen_id, time_block_id, profile_text, audience_tags, feature_dict "
         "FROM screen_audience_profile WHERE screen_id IN ({})".format(
             ",".join("?" * len(screen_ids))))
    df = pd.read_sql(q, conn, params=list(screen_ids))
    return {(r.screen_id, r.time_block_id): r for r in df.itertuples(index=False)}


def safe_get(frame, key, col, default=None):
    """Index lookup that returns a default instead of raising on a missing key."""
    try:
        val = frame.at[key, col]
        return None if pd.isna(val) else val
    except (KeyError, ValueError, TypeError):
        return default


# ------------------------------------------------------------ per-screen row
def describe_screen(row, lk, profiles, duration_days):
    sid = row.screen_id
    tb = int(row.time_block_id)

    kind = safe_get(lk["geo"], sid, "screen_kind")
    location_id = safe_get(lk["geo"], sid, "location_id")
    corridor = safe_get(lk["geo"], sid, "primary_corridor_id")
    zone_id = safe_get(lk["geo"], sid, "zone_id")
    city_id = safe_get(lk["geo"], sid, "city_id")

    prof = profiles.get((sid, tb))
    feat = json.loads(prof.feature_dict) if prof is not None else {}
    tags = json.loads(prof.audience_tags) if prof is not None else []

    slots_per_day = int(getattr(row, "slots", 1) or 1)
    cost_per_day = float(getattr(row, "cost_per_day", row.price_target * slots_per_day))
    pair_cost = float(getattr(row, "pair_cost", cost_per_day))
    base_daily = float(getattr(row, "base_daily_impressions", 0) or 0)
    marginal_daily = float(getattr(row, "marginal_daily_impressions", base_daily) or 0)
    overlap_loss = base_daily - marginal_daily

    poi_weights = feat.get("poi_type_weights") or {}
    top_pois = sorted(poi_weights.items(), key=lambda kv: -kv[1])[:3]

    return {
        "rank": int(getattr(row, "combined_rank", 0) or 0),
        "screen_id": sid,
        "screen": {
            "kind": kind,
            "type": safe_get(lk["screens"], sid, "screen_type"),
            "mount_position": safe_get(lk["screens"], sid, "position"),
            "size": safe_get(lk["screens"], sid, "screen_size"),
        },
        "location": {
            "location_id": location_id,
            "name": safe_get(lk["locations"], location_id, "name") if location_id else None,
            "location_type": safe_get(lk["locations"], location_id, "location_type") if location_id else "vehicle-mounted (no fixed location)",
            "city_id": city_id,
            "city_name": safe_get(lk["cities"], city_id, "city_name"),
            "market_tier": safe_get(lk["cities"], city_id, "market_tier"),
            "zone_id": zone_id,
            "zone_name": safe_get(lk["zones"], zone_id, "zone_name"),
        },
        "route": {
            "primary_corridor_id": corridor,
            "route_names": lk["routes"].get(corridor, []) if corridor else [],
        },
        "time_slot": {
            "time_block_id": tb,
            "hours": safe_get(lk["slots"], tb, "time_block_label"),
            "daypart": safe_get(lk["slots"], tb, "nearest_daypart"),
            "rotation_slots_per_day": slots_per_day,
        },
        "audience": {
            "profile": prof.profile_text if prof is not None else None,
            "tags": tags,
            "riders_in_block": feat.get("riders_in_block"),
            "daily_riders_exposed": round(float(getattr(row, "daily_riders", 0) or 0), 0),
            "commuter_score": feat.get("commuter_score"),
            "income_index": feat.get("income_index"),
            "median_age": feat.get("median_age"),
            "dominant_occupation": feat.get("dominant_occupation"),
            "top_nearby_poi_types": [t for t, _ in top_pois],
            "data_confidence": getattr(row, "relevance_confidence", None) or feat.get("confidence"),
        },
        "pricing": {
            "price_floor_per_slot_per_day": round(float(row.price_floor), 2),
            "price_target_per_slot_per_day": round(float(row.price_target), 2),
            "price_cap_per_slot_per_day": round(float(row.price_cap), 2),
            "cost_per_day": round(cost_per_day, 2),
            "cost_for_campaign": round(pair_cost, 2),
            "campaign_days": duration_days,
            "demand_score": round(float(row.demand_score), 4) if pd.notna(row.demand_score) else None,
            "demand_basis": getattr(row, "demand_confidence", None),
        },
        "impressions": {
            "standalone_daily": round(base_daily, 0),
            "marginal_daily_after_overlap": round(marginal_daily, 0),
            "overlap_discount_applied": round(overlap_loss, 0),
            "marginal_weekly": round(marginal_daily * 7, 0),
            "marginal_for_campaign": round(marginal_daily * duration_days, 0) if duration_days else None,
        },
        "why_selected": {
            "relevance_score": round(float(row.relevance_score), 4),
            "reason": getattr(row, "relevance_reason", None),
            "audience_cluster": getattr(row, "cluster_id", None),
            "cluster_note": ("Shares an audience with any other selected screen in the "
                            "same cluster -- reach is discounted, not double-counted."),
        },
    }


# ------------------------------------------------------------ full structure
def build_detailed_recommendation(result, conn, brief_name):
    spec = result.get("spec") or {}
    meta = result.get("meta") or {}
    summary = result.get("summary") or {}
    package = result.get("package")

    detail = {
        "brief": brief_name,
        "status": result.get("status"),
        "campaign": {
            "objective": spec.get("objective"),
            "target_audience": {
                "age_range": [spec.get("target_age_min"), spec.get("target_age_max")],
                "income_tier": spec.get("target_income_tier"),
                "descriptors": spec.get("audience_descriptors"),
                "poi_affinities": spec.get("poi_affinities"),
            },
            "budget": spec.get("budget"),
            "duration_days": spec.get("duration_days"),
            "rotation_slots_per_day": spec.get("rotation_slots_per_day"),
            "requested_dayparts": spec.get("preferred_dayparts"),
            "requested_geography": spec.get("target_zones_text"),
            "city_resolved_to": meta.get("city_id"),
        },
        "filters_applied": {
            "exclusions": meta.get("exclusion_log"),
            "location_type": meta.get("location_filter_log"),
            "candidates_scored": meta.get("n_screens_scored"),
        },
        "package_totals": summary,
        "caveats": [c for c in [summary.get("caveat"), summary.get("note"),
                                (meta.get("location_filter_log") or {}).get("warning")] if c],
        "recommended_screens": [],
    }

    if result.get("status") != "ok" or package is None or package.empty:
        detail["narrative"] = result.get("narrative")
        return detail

    lk = load_lookups(conn)
    profiles = load_profiles(conn, package.screen_id.unique().tolist(),
                             package.time_block_id.unique().tolist())
    duration_days = spec.get("duration_days")

    rows = [describe_screen(r, lk, profiles, duration_days)
            for r in package.itertuples(index=False)]
    rows.sort(key=lambda d: -d["impressions"]["marginal_daily_after_overlap"])
    detail["recommended_screens"] = rows
    detail["narrative"] = result.get("narrative")
    return detail


# ------------------------------------------------------------ markdown render
def render_markdown(detail):
    d = detail
    L = [f"# Recommendation: {d['brief']}", "", f"**Status:** {d['status']}", ""]

    c = d["campaign"]
    L += ["## Campaign", "",
          f"- **Objective:** {c['objective']}",
          f"- **Target age:** {c['target_audience']['age_range'][0]}–{c['target_audience']['age_range'][1]}",
          f"- **Income tier:** {c['target_audience']['income_tier']}",
          f"- **Audience:** {', '.join(c['target_audience']['descriptors'] or []) or '—'}",
          f"- **POI affinities:** {', '.join(c['target_audience']['poi_affinities'] or []) or '—'}",
          f"- **Budget:** {c['budget']}",
          f"- **Duration:** {c['duration_days']} days",
          f"- **Requested dayparts:** {', '.join(c['requested_dayparts'] or []) or 'none stated'}",
          f"- **City resolved to:** {c['city_resolved_to'] or 'all cities (none named in brief)'}",
          ""]

    if d["caveats"]:
        L += ["## Caveats — read these", ""] + [f"- {x}" for x in d["caveats"]] + [""]

    f = d["filters_applied"]
    L += ["## Filters applied", "", f"- **Candidates scored:** {f['candidates_scored']}"]
    for e in (f["exclusions"] or []):
        status = "enforced" if e.get("enforced") else "NOT ENFORCED"
        L.append(f"- **Exclusion** ({status}): {e['criterion']} — removed {e.get('screens_removed', 0)} screens")
    if f["location_type"]:
        lt = f["location_type"]
        L.append(f"- **Location type:** {lt.get('location_type_preference')} "
                 f"(applied={lt.get('applied')}, removed {lt.get('screens_removed', 0)})")
    L.append("")

    t = d["package_totals"]
    if t:
        L += ["## Package totals", "",
              f"- **Screens selected:** {t.get('n_unique_screens')} "
              f"({t.get('n_screen_timeblock_pairs')} screen/time-slot pairs)",
              f"- **Distinct audience clusters:** {t.get('n_clusters_represented')}",
              f"- **Total cost:** {t.get('total_cost')} of {t.get('budget')} budget "
              f"({t.get('budget_utilization_pct')}% used)",
              f"- **Cost basis:** {t.get('cost_basis')}",
              f"- **Projected impressions:** {t.get('total_projected_impressions_per_day'):,.0f}/day · "
              f"{t.get('total_projected_impressions_per_week'):,.0f}/week"
              if t.get('total_projected_impressions_per_day') is not None else "",
              f"- **Average relevance of selected screens:** {t.get('avg_relevance_score_selected')}",
              ""]

    if d.get("narrative"):
        L += ["## Summary for the rep", "", d["narrative"], ""]

    if not d["recommended_screens"]:
        return "\n".join(L)

    L += ["---", "", "## Recommended screens (highest reach first)", ""]
    for i, s in enumerate(d["recommended_screens"], 1):
        loc, ts, pr, im, wh, au = (s["location"], s["time_slot"], s["pricing"],
                                   s["impressions"], s["why_selected"], s["audience"])
        title = loc["name"] or f"{s['screen']['kind']} screen"
        L += [f"### {i}. {s['screen_id']} — {title}", "",
              f"- **Where:** {title} ({loc['location_type']}) · "
              f"{loc['zone_name'] or '—'}, {loc['city_name'] or '—'} "
              f"[{loc['market_tier'] or '—'} tier]",
              f"- **Screen:** {s['screen']['type']} · size {s['screen']['size']} · "
              f"mount {s['screen']['mount_position']}"]
        if s["route"]["route_names"]:
            L.append(f"- **Routes:** {', '.join(s['route']['route_names'][:4])}")
        L += [f"- **Time slot:** block {ts['time_block_id']} · {ts['hours']} "
              f"({ts['daypart']}) · {ts['rotation_slots_per_day']} rotation slot(s)/day",
              f"- **Price:** target **{pr['price_target_per_slot_per_day']}** per slot/day "
              f"(floor {pr['price_floor_per_slot_per_day']} · cap {pr['price_cap_per_slot_per_day']})",
              f"- **Cost:** {pr['cost_per_day']}/day → **{pr['cost_for_campaign']}** for "
              f"{pr['campaign_days']} days",
              f"- **Demand:** score {pr['demand_score']} (basis: {pr['demand_basis']})",
              f"- **Audience reached:** {im['marginal_daily_after_overlap']:,.0f}/day · "
              f"{im['marginal_weekly']:,.0f}/week"
              + (f" · {im['marginal_for_campaign']:,.0f} over the campaign"
                 if im['marginal_for_campaign'] else ""),
              f"- **Standalone reach:** {im['standalone_daily']:,.0f}/day "
              f"(overlap discount applied: −{im['overlap_discount_applied']:,.0f})",
              f"- **Who's there:** {au['profile'] or '—'}",
              f"- **Audience tags:** {', '.join(au['tags'] or []) or '—'}",
              f"- **Nearby POIs:** {', '.join(au['top_nearby_poi_types']) or 'none with signal'}",
              f"- **Data confidence:** {au['data_confidence']}",
              f"- **Why this screen (relevance {wh['relevance_score']}):** {wh['reason']}",
              f"- **Audience cluster:** {wh['audience_cluster']}",
              ""]
    return "\n".join(L)


# --------------------------------------------------------------- flat export
def flatten_for_csv(detail):
    rows = []
    for s in detail.get("recommended_screens", []):
        rows.append({
            "brief": detail["brief"],
            "objective": detail["campaign"]["objective"],
            "screen_id": s["screen_id"],
            "screen_kind": s["screen"]["kind"],
            "screen_type": s["screen"]["type"],
            "mount_position": s["screen"]["mount_position"],
            "screen_size": s["screen"]["size"],
            "location_name": s["location"]["name"],
            "location_type": s["location"]["location_type"],
            "zone_name": s["location"]["zone_name"],
            "city_name": s["location"]["city_name"],
            "market_tier": s["location"]["market_tier"],
            "routes": "; ".join(s["route"]["route_names"][:4]),
            "time_block_id": s["time_slot"]["time_block_id"],
            "time_block_hours": s["time_slot"]["hours"],
            "daypart": s["time_slot"]["daypart"],
            "slots_per_day": s["time_slot"]["rotation_slots_per_day"],
            "price_floor": s["pricing"]["price_floor_per_slot_per_day"],
            "price_target": s["pricing"]["price_target_per_slot_per_day"],
            "price_cap": s["pricing"]["price_cap_per_slot_per_day"],
            "cost_per_day": s["pricing"]["cost_per_day"],
            "cost_for_campaign": s["pricing"]["cost_for_campaign"],
            "demand_score": s["pricing"]["demand_score"],
            "demand_basis": s["pricing"]["demand_basis"],
            "impressions_standalone_daily": s["impressions"]["standalone_daily"],
            "impressions_marginal_daily": s["impressions"]["marginal_daily_after_overlap"],
            "impressions_marginal_weekly": s["impressions"]["marginal_weekly"],
            "relevance_score": s["why_selected"]["relevance_score"],
            "relevance_reason": s["why_selected"]["reason"],
            "audience_cluster": s["why_selected"]["audience_cluster"],
            "data_confidence": s["audience"]["data_confidence"],
            "audience_profile": s["audience"]["profile"],
            "nearby_pois": "; ".join(s["audience"]["top_nearby_poi_types"]),
        })
    return rows