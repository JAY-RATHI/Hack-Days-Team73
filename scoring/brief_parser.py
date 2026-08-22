"""
D2 STEP 1: Brief parser -- free text campaign brief -> structured CampaignSpec.

DESIGN RULE (from the plan, worth restating): missing information becomes
None/null, never an invented default. A brief with no budget produces
budget=None, which D4 later treats as "unconstrained" -- it must NOT become
some guessed number like 10000, because that silently changes what the
optimizer is allowed to do.

FIELDS THAT MAP DIRECTLY TO REAL SCHEMA (see db/schema.md, docs/CONTRACTS.md)
    city_id            -> cities.city_id (LH / ACS / DAT)
    target_zones        -> zone_demographics.zone_name (fuzzy text, resolved
                           against real zone names at scoring time, not here)
    target_age_bands    -> maps to zone_demographics pct_age_* columns
    objective           -> bookings.campaign_objective (awareness/frequency/
                           conversion) -- keep to this vocabulary if possible
    preferred_dayparts  -> dim_slot.nearest_daypart values
    budget              -> None if not stated, never guessed
    duration_days       -> None if not stated

HOW TO RUN (as a module, or standalone for testing)
    python scoring/brief_parser.py
"""
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.llm_client import chat_completion, clean_json_response, CHAT_FAST

# Brief parsing is simple extraction -- CHAT_FAST (nano) is enough and keeps
# this cheap even if it's called on every incoming brief all day.
MODEL = CHAT_FAST

VALID_OBJECTIVES = ["awareness", "frequency", "conversion"]
VALID_DAYPARTS = ["night", "morning", "midday", "afternoon", "evening"]

# CONFIRMED against the real points_of_interest table (13 categories total,
# see scoring/inspect_scoring_vocab.py). This is a CLOSED set -- there is no
# "car_dealership" or "financial_district" category in this dataset. Before
# this fix, the LLM extracted free-text phrases straight from the brief's
# prose ("business-district", "car dealerships") that could never match any
# real poi_type, silently zeroing the POI-relevance score for most/all
# screens on almost every real-world brief.
DEFAULT_POI_VOCAB = [
    "shopping_mall", "grocery_anchor", "office_park", "residential_tower",
    "entertainment_district", "government_building", "hospital",
    "corporate_campus", "university", "hotel_convention", "museum",
    "tourist_landmark", "stadium_arena",
]

PROMPT = """Extract a structured campaign spec from this advertiser brief.
Return ONLY valid JSON, no other text, matching exactly this shape:

{{
  "city_hint": "<city name mentioned, or null if none/ambiguous>",
  "target_zones_text": ["<any specific area/zone/corridor names mentioned, verbatim>"],
  "target_age_min": <int or null>,
  "target_age_max": <int or null>,
  "target_income_tier": "<'high'|'mid'|'value'|null>",
  "audience_descriptors": ["<short free-text descriptors like 'commuters', 'families', 'nightlife'>"],
  "poi_affinities": ["<ONLY values from this exact list that plausibly match what the brief describes: {poi_vocab}. Map the brief's language to the closest real category -- e.g. 'business district'/'financial district' language usually maps to 'office_park' and/or 'corporate_campus'. If NOTHING in the list is a reasonable match for what the brief describes, return an empty list -- do NOT invent a category that isn't in this list, even if the brief's own wording suggests one (e.g. 'car dealership' has no real equivalent here).>"],
  "objective": "<one of awareness/frequency/conversion, or null if unclear>",
  "preferred_dayparts": ["<subset of night/morning/midday/afternoon/evening explicitly implied, or empty list>"],
  "budget": <number or null -- ONLY if a specific figure is stated>,
  "duration_days": <int or null -- ONLY if explicitly stated or clearly computable>,
  "requires_broad_coverage": <true if brief explicitly says "not tied to one area" / "broad" / "citywide", else false>,
  "exclusion_criteria": ["<verbatim or near-verbatim exclusion clauses, e.g. 'exclude bus-rear screens', 'exclude high-density residential value-tier inventory' -- empty list if none stated>"],
  "location_type_preference": "<'metro_only'|'fixed_only'|'vehicle_only'|null -- ONLY if the brief is explicit that ONE inventory type should be used exclusively, e.g. 'metro platform boards' as the ENTIRE focus. If the brief lists multiple screen types (as most will), use null -- don't over-constrain from one example type.>",
  "rotation_slots_per_day": <int or null -- ONLY if a specific slot count is stated, e.g. "1 rotating slot" -> 1>,
  "start_date": "<ISO date string YYYY-MM-DD, or null. ONLY if a specific start date is stated or precisely computable (e.g. 'starting March 1, 2027' -> '2027-03-01'). A vague window like 'Q1 2027' or 'pre-monsoon' is NOT a date -- use null.>"
}}

RULES:
- Never invent a number. If budget/duration isn't stated, use null.
- "audience_descriptors" and "poi_affinities" should reflect what's actually
  written, not your own elaboration.
- If the brief names a district/corridor/area, put it in target_zones_text
  verbatim -- don't try to resolve it to a real zone_id, that happens later
  against the real zone list.
- poi_affinities MUST be a subset of the provided vocabulary list, verbatim
  (exact spelling/underscores). Never return a category not in that list.
- exclusion_criteria should capture what must be EXCLUDED, not what's wanted.
  Keep each entry short and close to the brief's own wording -- these get
  matched against real inventory later using keyword rules, so don't
  paraphrase into different vocabulary than the brief used.
- Real briefs are often much more detailed than a short paragraph -- read
  the ENTIRE brief for exclusions, they're often in a separate section
  (e.g. "Exclusion Criteria:") distinct from the main targeting description.

BRIEF:
\"\"\"{brief_text}\"\"\"
"""

def _format_prompt(brief_text, poi_vocab):
    return PROMPT.format(brief_text=brief_text, poi_vocab=", ".join(poi_vocab))


# Real cities in this dataset -- used as a deterministic fallback below.
# Hardcoded rather than queried from the DB because this module has no DB
# connection and shouldn't need one just to sanity-check city names; there
# are only 3 and they don't change mid-hackathon.
KNOWN_CITIES = {"las hackland": "Las Hackland", "accordionshire": "Accordionshire",
                "da town": "DA Town"}


def parse_brief(brief_text: str, poi_vocab=None) -> dict:
    poi_vocab = poi_vocab or DEFAULT_POI_VOCAB
    text = chat_completion(
        messages=[{"role": "user", "content": _format_prompt(brief_text, poi_vocab)}],
        model=MODEL,
        max_completion_tokens=800,
        temperature=0,   # structured extraction, not creative writing --
                         # don't sample. Found via testing: the same brief
                         # returned a different city_hint across two runs
                         # at default temperature.
    )
    text = clean_json_response(text)
    spec = json.loads(text)

    # Deterministic safety net: if the LLM missed a city name the brief
    # literally states, catch it here rather than silently scoring the
    # wrong geography. This is a fallback, not a replacement -- the LLM
    # still does the real extraction work for everything else.
    if not spec.get("city_hint"):
        lowered = brief_text.lower()
        for key, proper_name in KNOWN_CITIES.items():
            if key in lowered:
                spec["city_hint"] = proper_name
                break

    # Guardrails: don't trust the LLM's vocabulary blindly.
    valid_poi = set(poi_vocab)
    raw_affinities = spec.get("poi_affinities") or []
    spec["poi_affinities"] = [a for a in raw_affinities if a in valid_poi]
    dropped = [a for a in raw_affinities if a not in valid_poi]
    if dropped:
        spec["_dropped_poi_affinities"] = dropped  # kept for debugging/logging, not used downstream

    if spec.get("objective") not in VALID_OBJECTIVES:
        spec["objective"] = None
    spec["preferred_dayparts"] = [
        d for d in spec.get("preferred_dayparts", []) if d in VALID_DAYPARTS
    ]
    if spec.get("budget") is not None:
        try:
            spec["budget"] = float(spec["budget"])
        except (TypeError, ValueError):
            spec["budget"] = None
    if spec.get("duration_days") is not None:
        try:
            spec["duration_days"] = int(spec["duration_days"])
        except (TypeError, ValueError):
            spec["duration_days"] = None
    if spec.get("start_date"):
        from datetime import datetime
        try:
            datetime.strptime(str(spec["start_date"])[:10], "%Y-%m-%d")
            spec["start_date"] = str(spec["start_date"])[:10]
        except (TypeError, ValueError):
            spec["start_date"] = None
    else:
        spec["start_date"] = None

    spec["raw_brief_text"] = brief_text
    return spec


if __name__ == "__main__":
    from sample_campaign_briefs import SAMPLE_BRIEFS
    for b in SAMPLE_BRIEFS:
        print(f"=== {b['id']} ===")
        try:
            spec = parse_brief(b["text"])
            print(json.dumps(spec, indent=2))
        except Exception as e:
            print(f"FAILED: {e}")
        print()