"""
D2 STEPS 2-4: Campaign-Screen Relevance Scorer.

Reads screen_audience_profile (Person A's real, verified table -- not the
mocked 5-row version) and scores every eligible screen against a parsed
CampaignSpec.

=== STEP 2: hard filter + soft score ===

HARD FILTER (geography):
  CampaignSpec.city_hint, if resolved to a real city_id, restricts to that
  city. CampaignSpec.target_zones_text is fuzzy-matched against real
  zone_demographics.zone_name (case-insensitive substring match -- good
  enough for a hackathon, upgrade to embeddings if time allows).
  If requires_broad_coverage=True, or no zone/city resolves, skip the
  geography filter entirely rather than silently returning zero screens.

SOFT SCORE (rule-based, weights match the plan's suggestion):
  +0.4 age band match     -- CampaignSpec age range vs zone pct_age_* columns
  +0.3 commuter/leisure    -- audience_descriptors vs commuter_score /
                              daypart alignment
  +0.3 POI-type relevance  -- poi_affinities vs feature_dict.poi_type_weights
  Final score normalized to [0, 1].

IMPORTANT: screen_audience_profile.feature_dict and audience_tags are JSON
*strings* (see docs/CONTRACTS.md) -- must json.loads() them.

IMPORTANT: confidence matters. A 'low' confidence profile has no local
signal at all -- its POI/commuter sub-scores are meaningless zeros, not
"this screen doesn't fit." We apply a mild score penalty AND flag it in the
reason string, rather than let it silently rank low for the wrong reason.

=== STEP 3: reason string ===
Built directly from the sub-scores actually computed -- never invented.
This mirrors the discipline Person A used for profile_text: only claim
what the numbers support.

=== STEP 4: output ===
ranked_screens: (screen_id, time_block_id, relevance_score, reason,
                 sub_scores, confidence)
sorted descending by relevance_score.

HOW TO RUN
    python scoring/relevance_scorer.py
"""
import json
import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")

W_AGE = 0.4
W_COMMUTER = 0.3
W_POI = 0.3
LOW_CONFIDENCE_PENALTY = 0.7   # multiply final score by this if confidence == 'low'

AGE_BAND_COLS = {
    "18_34": "pct_18_34",
    "35_54": "pct_35_54",
    "55_plus": "pct_55_plus",
}

# =============================================================================
# EXCLUSION RULES (added after real-brief testing -- campaign_1.docx explicitly
# said "exclude bus-rear screens and value-tier inventory in high-density
# residential areas". CampaignSpec.exclusion_criteria carries the brief's own
# phrasing; this registry maps KNOWN phrases to a real filter against actual
# screen attributes. An exclusion phrase with no matching rule is NOT
# silently ignored -- it's logged as "not enforced" so nobody assumes broader
# compliance than the code actually delivers. Add a rule here whenever a new
# exclusion phrase shows up in a real brief.
# =============================================================================

VALUE_INCOME_THRESHOLD = 90     # income_index below this = "value-tier" area
HIGH_DENSITY_THRESHOLD = 8000   # population_density_per_sqkm above this = "high-density"


def _excl_bus_rear(row, feat):
    # CORRECTED against real data: the confirmed position value for a
    # rear-facing vehicle panel is 'back', not 'rear' -- 'rear' was an
    # unverified guess. Confirmed via scoring/inspect_scoring_vocab.py:
    # vehicle screens use {'back', 'left', 'right'} (1,400 have no position
    # recorded at all -- those are never excluded by this rule, which is
    # the conservative choice: we don't exclude a screen based on a
    # position we don't actually know).
    pos = row.get("position")
    return row.get("screen_kind") == "vehicle" and isinstance(pos, str) and pos.lower() == "back"


def _excl_value_tier_high_density_residential(row, feat):
    income = feat.get("income_index")
    density = feat.get("density")
    occ = feat.get("dominant_occupation")
    if income is None or density is None:
        return False
    return (income < VALUE_INCOME_THRESHOLD and density > HIGH_DENSITY_THRESHOLD
           and occ != "white_collar")


def _excl_all_buses(row, feat):
    # Broader than _excl_bus_rear -- catches phrasing like "not buses" or
    # "exclude bus screens" (no specific position mentioned), as opposed to
    # a position-specific exclusion. Distinguished from _excl_bus_rear by
    # requiring vehicle_type == 'bus' specifically, not just screen_kind ==
    # 'vehicle' -- a metro rail coach interior screen is NOT a "bus" screen.
    return row.get("vehicle_type") == "bus"


# key: a lowercase phrase fragment to match inside an exclusion_criteria entry
EXCLUSION_RULES = {
    "bus-rear": _excl_bus_rear,
    "bus rear": _excl_bus_rear,
    "value-tier": _excl_value_tier_high_density_residential,
    "value tier": _excl_value_tier_high_density_residential,
    "not buses": _excl_all_buses,
    "no buses": _excl_all_buses,
    "exclude bus screens": _excl_all_buses,
    "exclude buses": _excl_all_buses,
}


def apply_exclusions(df, exclusion_criteria):
    """Returns (filtered_df, log) where log lists which criteria were
    enforced vs. which had no matching rule (and therefore did nothing)."""
    if not exclusion_criteria:
        return df, []

    log = []
    for criterion in exclusion_criteria:
        lc = criterion.lower()
        matched_rule = None
        for phrase, rule_fn in EXCLUSION_RULES.items():
            if phrase in lc:
                matched_rule = rule_fn
                break

        if matched_rule is None:
            log.append({"criterion": criterion, "enforced": False,
                       "note": "no matching rule -- NOT applied, flag to team"})
            continue

        before = len(df)
        would_match = df.apply(lambda r: matched_rule(r, r["_feat"]), axis=1)
        removed = int(would_match.sum())
        df = df[~would_match]

        entry = {"criterion": criterion, "enforced": True, "screens_removed": removed}
        if removed == 0:
            # Distinguish "correctly found nothing in THIS filtered pool"
            # from "this rule can never match anything, likely wrong
            # vocabulary" -- check against the pool before city/zone
            # filtering wasn't done here, but at minimum confirm whether
            # the rule matches ANYTHING in the current candidate pool's
            # screen_kind at all, which is the cheap, useful signal.
            entry["note"] = ("0 removed -- if this looks wrong, check the "
                             "rule's literal string values against "
                             "scoring/inspect_scoring_vocab.py output")
        log.append(entry)

    return df, log


def resolve_geography(spec, zone_demo, cities):
    """Returns (city_id or None, list of matching zone_ids or None -> None means no filter).

    BUGFIX (found via real-data testing): `requires_broad_coverage` means
    "don't restrict to one zone/corridor WITHIN the city" -- it does NOT
    mean "ignore the city entirely." A brief can simultaneously name a city
    (e.g. "DA Town") AND ask for broad coverage inside it ("not tied to one
    corridor"). The old version treated requires_broad_coverage as a global
    escape hatch and threw away a perfectly good city match, scoring all
    three cities' inventory for a single-city campaign.

    Also handles the case where the LLM puts the city name into
    target_zones_text instead of city_hint (seen in real testing: BRIEF_02
    said "DA Town" and city_hint came back null, but 'DA Town' was in
    target_zones_text). We now check target_zones_text against real city
    names too, not just against zone names.
    """
    zone_texts = spec.get("target_zones_text") or []

    city_id = None
    if spec.get("city_hint"):
        hint = spec["city_hint"].lower()
        match = cities[cities.city_name.str.lower().str.contains(hint, na=False)]
        if not match.empty:
            city_id = match.iloc[0].city_id

    if city_id is None:
        for zt in zone_texts:
            match = cities[cities.city_name.str.lower().str.contains(zt.lower(), na=False)]
            if not match.empty:
                city_id = match.iloc[0].city_id
                break

    if spec.get("requires_broad_coverage"):
        return city_id, None  # city filter (if any) still applies; zone filter does not

    zone_ids = None
    if zone_texts:
        pool = zone_demo if city_id is None else zone_demo[zone_demo.city_id == city_id]
        matched = []
        for zt in zone_texts:
            hit = pool[pool.zone_name.str.lower().str.contains(zt.lower(), na=False)]
            matched.extend(hit.zone_id.tolist())
        zone_ids = sorted(set(matched)) if matched else None
        if zone_texts and not matched:
            zone_ids = None

    return city_id, zone_ids


def age_score(spec, feat):
    lo, hi = spec.get("target_age_min"), spec.get("target_age_max")
    if lo is None and hi is None:
        return 0.0, "no age target stated"
    lo = lo or 0
    hi = hi or 120

    # Sum the pct_* columns whose band overlaps [lo, hi] at all.
    band_ranges = {"18_34": (18, 34), "35_54": (35, 54), "55_plus": (55, 120)}
    covered = 0.0
    matched_bands = []
    for band, (blo, bhi) in band_ranges.items():
        if blo <= hi and bhi >= lo:  # overlap
            val = feat.get(AGE_BAND_COLS[band])
            if val is not None:
                covered += val
                matched_bands.append(band)
    if not matched_bands:
        return 0.0, "age data unavailable for this screen's zone"
    # covered is a %; 60%+ overlap with target bands -> full score
    score = min(covered / 60.0, 1.0)
    return score, f"{covered:.0f}% of local population in target age range ({', '.join(matched_bands)})"


def commuter_score_fn(spec, feat):
    descriptors = " ".join(spec.get("audience_descriptors") or []).lower()
    wants_commuter = any(w in descriptors for w in ["commut", "rush hour", "worker", "professional"])
    wants_leisure = any(w in descriptors for w in ["leisure", "nightlife", "shopper", "resident", "family", "families"])

    cscore = feat.get("commuter_score") or 0.0
    daypart = feat.get("daypart")
    prefers_dp = spec.get("preferred_dayparts") or []

    parts = []
    score = 0.0
    if wants_commuter:
        score += cscore
        parts.append(f"commuter index {cscore:.2f}")
    elif wants_leisure:
        score += (1 - cscore)
        parts.append(f"non-commuter/leisure index {(1 - cscore):.2f}")
    else:
        score += 0.5  # neutral, no stated preference
        parts.append("no commuter/leisure preference stated")

    if prefers_dp and daypart in prefers_dp:
        score = min(score + 0.2, 1.0)
        parts.append(f"matches requested daypart ({daypart})")
    elif prefers_dp:
        score = max(score - 0.2, 0.0)
        parts.append(f"outside requested daypart(s) ({', '.join(prefers_dp)})")

    return min(score, 1.0), "; ".join(parts)


def poi_score_fn(spec, feat):
    affinities = [a.lower() for a in (spec.get("poi_affinities") or [])]
    poi_weights = feat.get("poi_type_weights") or {}
    if not affinities:
        return 0.0, "no POI affinity stated"
    if not poi_weights:
        return 0.0, "no nearby POI signal for this screen"

    matched = {t: w for t, w in poi_weights.items()
               if any(a in t.lower() for a in affinities)}
    if not matched:
        return 0.0, f"no nearby POIs match requested type(s): {', '.join(affinities)}"

    total = sum(poi_weights.values())
    share = sum(matched.values()) / total if total else 0
    top = ", ".join(matched.keys())
    return min(share * 2, 1.0), f"nearby {top} POI(s) relevant to campaign"


def score_screens(spec, conn):
    zone_demo = pd.read_sql("SELECT * FROM zone_demographics", conn)
    cities = pd.read_sql("SELECT * FROM cities", conn)
    city_id, zone_ids = resolve_geography(spec, zone_demo, cities)

    profiles = pd.read_sql("SELECT * FROM screen_audience_profile", conn)
    geo = pd.read_sql("SELECT screen_id, city_id, zone_id, zone_ids AS zone_ids_json, "
                      "location_id FROM screen_geo_map", conn)
    # `position` is needed for exclusion rules (e.g. "bus-rear") but isn't in
    # feature_dict -- pull it straight from screens.
    positions = pd.read_sql("SELECT screen_id, position, vehicle_id FROM screens", conn)
    vehicle_types = pd.read_sql("SELECT vehicle_id, vehicle_type FROM vehicles", conn)
    positions = positions.merge(vehicle_types, on="vehicle_id", how="left")
    # BUGFIX: vehicle_id used to be dropped here, which silently broke the
    # `vehicle_only` location filter (its check for the column always failed,
    # so it excluded EVERY screen). Found via campaign_2.docx, which asks for
    # bus-rear screens on nightlife routes and got zero results.
    # screen_geo_map also has a vehicle_id; suffix to avoid a silent collision.
    profiles = profiles.merge(geo, on="screen_id", how="left").merge(
        positions, on="screen_id", how="left", suffixes=("", "_screens"))

    if city_id:
        profiles = profiles[profiles.city_id == city_id]

    if zone_ids:
        def zone_hit(row):
            if row.zone_id in zone_ids:
                return True
            extra = json.loads(row.zone_ids_json) if pd.notna(row.zone_ids_json) else []
            return any(z in zone_ids for z in extra)
        profiles = profiles[profiles.apply(zone_hit, axis=1)]

    if profiles.empty:
        return pd.DataFrame(), {"city_id": city_id, "zone_ids": zone_ids,
                                "note": "no screens matched the geography filter"}

    # BUGFIX (found via real feedback-loop testing on campaign_1.docx): this
    # field existed in CampaignSpec but was NEVER actually enforced anywhere.
    # A rep's "only use metro platform screens" feedback silently did nothing
    # -- caught because the narrative LLM honestly noticed the fact sheet
    # didn't reflect the request, rather than pretending compliance.
    location_type_pref = spec.get("location_type_preference")
    if location_type_pref:
        loc_types = pd.read_sql("SELECT location_id, location_type FROM locations", conn)
        profiles = profiles.merge(loc_types, on="location_id", how="left")

        # Resolve which column actually holds vehicle_id after the merges
        # above, instead of assuming a name (the suffix depends on whether
        # both source frames carried it).
        veh_col = "vehicle_id" if "vehicle_id" in profiles.columns else (
            "vehicle_id_screens" if "vehicle_id_screens" in profiles.columns else None)

        if location_type_pref == "metro_only":
            # "Metro platform" means fixed screens at a metro_station
            # specifically -- not bus stops, not vehicle-mounted screens.
            mask = (profiles["location_type"] == "metro_station")
        elif location_type_pref == "fixed_only":
            mask = profiles["location_id"].notna()
        elif location_type_pref == "vehicle_only":
            mask = profiles[veh_col].notna() if veh_col else pd.Series(True, index=profiles.index)
        else:
            mask = pd.Series(True, index=profiles.index)

        before_n = len(profiles)
        filtered = profiles[mask]

        # SAFETY VALVE: never let a location-type preference wipe out the
        # ENTIRE pool. A brief expressing a preference ("bus-rear screens on
        # nightlife routes") should not end up with zero recommendations
        # because our interpretation of that preference was too narrow --
        # better to return the unfiltered pool with a loud flag than to
        # return nothing and blame the brief.
        if filtered.empty:
            location_filter_log = {
                "location_type_preference": location_type_pref,
                "applied": False,
                "screens_removed": 0,
                "warning": (f"'{location_type_pref}' would have excluded ALL "
                           f"{before_n} candidate screens, so it was NOT applied. "
                           f"This usually means the preference was mis-extracted or "
                           f"our interpretation of it is too narrow -- surface this "
                           f"to the user rather than returning an empty result."),
            }
        else:
            profiles = filtered
            location_filter_log = {"location_type_preference": location_type_pref,
                                   "applied": True,
                                   "screens_removed": before_n - len(profiles)}
    else:
        location_filter_log = None

    # Apply hard exclusions BEFORE scoring -- an excluded screen shouldn't
    # even be considered, not just ranked low.
    exclusion_criteria = spec.get("exclusion_criteria") or []
    exclusion_log = []
    if exclusion_criteria:
        profiles = profiles.copy()
        profiles["_feat"] = profiles["feature_dict"].apply(json.loads)
        profiles["screen_kind"] = profiles["_feat"].apply(lambda f: f.get("screen_kind"))
        profiles, exclusion_log = apply_exclusions(profiles, exclusion_criteria)
        profiles = profiles.drop(columns=["_feat", "screen_kind"], errors="ignore")

    if profiles.empty:
        # Report the ACTUAL cause. Previously this always blamed exclusion
        # criteria, which sent debugging in the wrong direction when the real
        # cause was the location-type filter (campaign_2.docx).
        if exclusion_log and any(e.get("screens_removed", 0) > 0 for e in exclusion_log):
            note = "all screens removed by exclusion criteria -- criteria may be too broad"
        elif location_filter_log and location_filter_log.get("screens_removed", 0) > 0:
            note = (f"all screens removed by location_type_preference="
                    f"'{location_filter_log.get('location_type_preference')}'")
        else:
            note = ("no screens remained after filtering, but no single filter "
                    "reports removing them -- check geography resolution")
        return pd.DataFrame(), {"city_id": city_id, "zone_ids": zone_ids,
                                "exclusion_log": exclusion_log,
                                "location_filter_log": location_filter_log,
                                "note": note}

    results = []
    for r in profiles.itertuples(index=False):
        feat = json.loads(r.feature_dict)

        a_score, a_reason = age_score(spec, feat)
        c_score, c_reason = commuter_score_fn(spec, feat)
        p_score, p_reason = poi_score_fn(spec, feat)

        raw = W_AGE * a_score + W_COMMUTER * c_score + W_POI * p_score
        final = raw * LOW_CONFIDENCE_PENALTY if r.confidence == "low" else raw

        reason_parts = [a_reason, c_reason, p_reason]
        if r.confidence == "low":
            reason_parts.append("score discounted -- screen has no local data signal")
        reason = "; ".join(reason_parts)

        results.append({
            "screen_id": r.screen_id,
            "time_block_id": r.time_block_id,
            "relevance_score": round(final, 4),
            "reason": reason,
            "sub_scores": json.dumps({"age": round(a_score, 3), "commuter": round(c_score, 3),
                                       "poi": round(p_score, 3)}),
            "confidence": r.confidence,
        })

    out = pd.DataFrame(results).sort_values("relevance_score", ascending=False)
    meta = {"city_id": city_id, "zone_ids": zone_ids, "n_screens_scored": len(out),
            "exclusion_log": exclusion_log, "location_filter_log": location_filter_log}
    return out, meta


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.getcwd())
    from sample_campaign_briefs import SAMPLE_BRIEFS
    from scoring.brief_parser import parse_brief

    conn = sqlite3.connect(DB_PATH)
    b = SAMPLE_BRIEFS[0]
    print(f"Testing against: {b['id']}")
    spec = parse_brief(b["text"])
    print("Parsed spec:", json.dumps(spec, indent=2))

    ranked, meta = score_screens(spec, conn)
    print("\nMeta:", meta)
    print(f"\nTop 5 of {len(ranked)} scored screens:")
    print(ranked.head(5)[["screen_id", "time_block_id", "relevance_score", "confidence"]]
          .to_string(index=False))
    print("\nSample reason:")
    print(" ", ranked.iloc[0].reason)