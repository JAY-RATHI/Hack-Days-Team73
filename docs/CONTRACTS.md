# Data Contracts — Person A → Person B/C

**Status: LIVE. These tables exist and are populated.** Column names below are
copied from the actual built tables, not planned.

Read `db/schema.md` first for the four schema surprises in the raw data.

---

## `screen_audience_profile` — the main handoff (D1 output)

One row per **screen × time_block** (11,163 × 6 ≈ 67K rows).

| Column | Type | Description |
|---|---|---|
| `screen_id` | TEXT | FK to screens |
| `time_block_id` | INTEGER | 1–6, FK to dim_slot |
| `profile_text` | TEXT | One-sentence human-readable summary |
| `audience_tags` | TEXT | **JSON array string** — `json.loads()` it |
| `feature_dict` | TEXT | **JSON object string** — the numbers you score against |
| `confidence` | TEXT | `high` \| `medium` \| `low` |
| `profile_source` | TEXT | `rule` \| `llm` (see two-layer note below) |

### `feature_dict` — exact shape

```json
{
  "screen_id": "LH-SCR-000001",
  "time_block_id": 1,
  "daypart": "night",
  "screen_kind": "fixed",              // "fixed" | "vehicle"
  "screen_size": "S",                  // S | M | L
  "riders_in_block": 0.0,              // fixed: corridor riders past the stop
                                       // vehicle: riders inside the vehicle
  "commuter_score": 0.443,             // share of daily riders in peak blocks 2+5
  "poi_weight_total": 84298.2,         // footfall/distance, daypart-weighted
  "poi_count": 1,
  "poi_type_weights": {"museum": 84298.2},
  "has_hub": false,                    // network interchange adjacency
  "confidence": "low",
  "zone_names": ["Zone 4"],
  "median_age": 42.0,
  "pct_18_34": 32.4,
  "pct_35_54": 25.7,
  "pct_55_plus": 22.6,
  "income_index": 97.7,                // ~100 = city average
  "pct_bachelor_or_higher": 59.6,
  "density": 2721,
  "daytime_multiplier": 2.27,          // how much the zone swells in work hours
  "dominant_occupation": "mixed",      // white_collar | blue_collar | mixed
  "footfall_tier": "unknown"           // low | medium | high | unknown
}
```

### Things you must handle, Person B

1. **`audience_tags` and `feature_dict` are JSON *strings*.** `json.loads()` before use.
2. **`riders_in_block` means different things by `screen_kind`.** For `fixed` it's total corridor riders passing that stop in the block; for `vehicle` it's average riders inside the vehicle. **Never compare the two numbers directly** — normalise within kind, or score them on separate scales.
3. **Respect `confidence`.** `low` means there was no POI and no ridership signal — the profile is zone averages only. Don't let a low-confidence screen outrank a high-confidence one on a score built from data it doesn't have. Down-weight it, and surface the flag in the UI (D6) so the rep knows.
4. **Low-confidence rows deliberately make no local claims.** No POI types, no hub flag — in text *or* tags. That's intentional, not missing data: an unsupported "near a university" in a client proposal is worse than saying nothing.
5. **`poi_weight_total` is unbounded and heavily skewed** (footfall ÷ distance, so a close flagship POI dominates). Log-scale or rank-normalise it before mixing it into a weighted score, or it will swamp every other feature.

### Two-layer profile text — why `profile_source` exists

All ~67K rows ship with `profile_source='rule'`: deterministic template text
built from `feature_dict`. Zero API cost, runs in seconds, fully traceable.

Generating LLM prose for all 67K rows would need ~1,675 Claude calls — hours
of wall clock and a large bill, for text most screens never show.

So instead, **call the enricher on your shortlist** once you've ranked:

```python
from features.enrich_profiles_llm import enrich
enrich(top_screen_ids, time_block_id=5)   # 1-2 API calls, cached forever
```

Rows come back with `profile_source='llm'` and nicer `profile_text`. **The
schema does not change** — if you never call it, everything still works with
the rule-based text.

---

## `screen_geo_map` — screen → geography (read this before joining anything)

| Column | Description |
|---|---|
| `screen_id` | |
| `city_id` | LH \| ACS \| DAT |
| `screen_kind` | `fixed` (8,548) \| `vehicle` (2,615) |
| `location_id` | populated for `fixed` only, else NULL |
| `vehicle_id` | populated for `vehicle` only, else NULL |
| `primary_corridor_id` | main corridor |
| `corridor_ids` | **JSON array** — a stop can be served by several corridors |
| `zone_id` | fixed: its zone. vehicle: most-traversed zone. |
| `zone_ids` | **JSON array** — every zone a vehicle screen passes through |
| `n_corridors` | |

Use this instead of joining `screens` yourself — it already resolves the
fixed/vehicle split and the `vehicles → corridor_id` (not route_id) hop.

## `screen_cluster_map` — audience overlap, hard (for D4)

| Column | Description |
|---|---|
| `screen_id` | |
| `cluster_id` | `LOC::<location_id>` or `COR::<corridor_id>` or `SOLO::<screen_id>` |
| `cluster_type` | `same_stop` \| `same_corridor` \| `unresolved` |
| `n_screens_in_cluster` | |

**Screens sharing a `cluster_id` reach the same people. Do not sum their reach.**
Three panels on one shelter are one audience, not three.

## `corridor_overlap` — audience overlap, soft (for D4)

`corridor_a`, `corridor_b`, `shared_stops`, `jaccard` (only pairs ≥ 0.05)

Two corridors sharing 60% of stops carry substantially overlapping riders but
are *not* the same audience. Use `jaccard` as a **discount factor** on combined
reach, not as a merge. (We deliberately avoided transitive route merging — with
2,436 route_stops over 910 locations it collapses a whole city into one cluster.)

## `corridor_timeblock_ridership` — footfall lookup

`corridor_id`, `time_block_id`, `day_type`, `avg_trip_ridership`,
`avg_daily_block_riders`, `n_trips`, `n_days`

Pre-aggregated from the 2M-row `ridership_actuals`. `day_type` is
weekday|weekend — a campaign running Mon–Fri should not be priced off weekend
patterns. Profiles currently use **weekday**.

---

## Notes for whoever owns D3 (pricing)

Not my deliverable, but found while building D1 — saves you the rediscovery:

- **`lost_leads` has no `lead_expiry_date`** despite the problem statement claiming it. Use `lead_date` / `lost_date` for recency decay.
- `lost_leads.quoted_price_per_slot_per_day` vs `client_target_price_per_slot_per_day` vs `loss_reason='price_too_high'` is your **ceiling evidence**. `bookings` only contains prices that succeeded — it can't tell you where the cap is. This table can.
- `bookings.deal_id` + `is_bundle` + `deal_total_value` show how bundles were *actually* priced against the sum of their parts — direct evidence for the bundle nuance.
- `cities.market_tier` (premium/standard/value) and `client_facts.negotiation_leverage` are clean floor/cap modifiers.
- `events` is unused by D1 by design (profiles are steady-state). It's your demand-spike input: an event overlapping the campaign dates near a screen justifies a premium. Join on `anchor_location_id` — 86 rows have a null `poi_id`.
- `zone_demographics.daytime_population_multiplier` (up to 3.4x) should probably modulate daytime-block pricing, not just audience profiles.

## Open questions for the Hour 2 sync

- [ ] `screens.position` (top/left/right) is fixture placement, **not** compass facing — there's no facing field in the data. I use POI `side_of_road` as a soft weight instead of a hard line-of-sight filter. Object now if you disagree.
- [ ] Profiles are built on **weekday** ridership. Worth a weekend variant, or is a day_type flag on the campaign brief enough?
- [ ] `vehicles.screen_count` should reconcile with actual `screens` rows per vehicle — nobody has asserted this yet.







# Data Contracts — Person A → Person B/C

**Status: LIVE. These tables exist and are populated.** Column names below are
copied from the actual built tables, not planned.

Read `db/schema.md` first for the four schema surprises in the raw data.

---

## `screen_audience_profile` — the main handoff (D1 output)

One row per **screen × time_block** (11,163 × 6 ≈ 67K rows).

| Column | Type | Description |
|---|---|---|
| `screen_id` | TEXT | FK to screens |
| `time_block_id` | INTEGER | 1–6, FK to dim_slot |
| `profile_text` | TEXT | One-sentence human-readable summary |
| `audience_tags` | TEXT | **JSON array string** — `json.loads()` it |
| `feature_dict` | TEXT | **JSON object string** — the numbers you score against |
| `confidence` | TEXT | `high` \| `medium` \| `low` |
| `profile_source` | TEXT | `rule` \| `llm` (see two-layer note below) |

### `feature_dict` — exact shape

```json
{
  "screen_id": "LH-SCR-000001",
  "time_block_id": 1,
  "daypart": "night",
  "screen_kind": "fixed",              // "fixed" | "vehicle"
  "screen_size": "S",                  // S | M | L
  "riders_in_block": 0.0,              // fixed: corridor riders past the stop
                                       // vehicle: riders inside the vehicle
  "commuter_score": 0.443,             // share of daily riders in peak blocks 2+5
  "poi_weight_total": 84298.2,         // footfall/distance, daypart-weighted
  "poi_count": 1,
  "poi_type_weights": {"museum": 84298.2},
  "has_hub": false,                    // network interchange adjacency
  "confidence": "low",
  "zone_names": ["Zone 4"],
  "median_age": 42.0,
  "pct_18_34": 32.4,
  "pct_35_54": 25.7,
  "pct_55_plus": 22.6,
  "income_index": 97.7,                // ~100 = city average
  "pct_bachelor_or_higher": 59.6,
  "density": 2721,
  "daytime_multiplier": 2.27,          // how much the zone swells in work hours
  "dominant_occupation": "mixed",      // white_collar | blue_collar | mixed
  "footfall_tier": "unknown"           // low | medium | high | unknown
}
```

### Things you must handle, Person B

1. **`audience_tags` and `feature_dict` are JSON *strings*.** `json.loads()` before use.
2. **`riders_in_block` means different things by `screen_kind`.** For `fixed` it's total corridor riders passing that stop in the block; for `vehicle` it's average riders inside the vehicle. **Never compare the two numbers directly** — normalise within kind, or score them on separate scales.
3. **Respect `confidence`.** `low` means there was no POI and no ridership signal — the profile is zone averages only. Don't let a low-confidence screen outrank a high-confidence one on a score built from data it doesn't have. Down-weight it, and surface the flag in the UI (D6) so the rep knows.
4. **Low-confidence rows deliberately make no local claims.** No POI types, no hub flag — in text *or* tags. That's intentional, not missing data: an unsupported "near a university" in a client proposal is worse than saying nothing.
5. **`poi_weight_total` is unbounded and heavily skewed** (footfall ÷ distance, so a close flagship POI dominates). Log-scale or rank-normalise it before mixing it into a weighted score, or it will swamp every other feature.

### Two-layer profile text — why `profile_source` exists

All ~67K rows ship with `profile_source='rule'`: deterministic template text
built from `feature_dict`. Zero API cost, runs in seconds, fully traceable.

Generating LLM prose for all 67K rows would need ~1,675 Claude calls — hours
of wall clock and a large bill, for text most screens never show.

So instead, **call the enricher on your shortlist** once you've ranked:

```python
from features.enrich_profiles_llm import enrich
enrich(top_screen_ids, time_block_id=5)   # 1-2 API calls, cached forever
```

Rows come back with `profile_source='llm'` and nicer `profile_text`. **The
schema does not change** — if you never call it, everything still works with
the rule-based text.

---

## `screen_geo_map` — screen → geography (read this before joining anything)

| Column | Description |
|---|---|
| `screen_id` | |
| `city_id` | LH \| ACS \| DAT |
| `screen_kind` | `fixed` (8,548) \| `vehicle` (2,615) |
| `location_id` | populated for `fixed` only, else NULL |
| `vehicle_id` | populated for `vehicle` only, else NULL |
| `primary_corridor_id` | main corridor |
| `corridor_ids` | **JSON array** — a stop can be served by several corridors |
| `zone_id` | fixed: its zone. vehicle: most-traversed zone. |
| `zone_ids` | **JSON array** — every zone a vehicle screen passes through |
| `n_corridors` | |

Use this instead of joining `screens` yourself — it already resolves the
fixed/vehicle split and the `vehicles → corridor_id` (not route_id) hop.

## `screen_cluster_map` — audience overlap, hard (for D4)

| Column | Description |
|---|---|
| `screen_id` | |
| `cluster_id` | `LOC::<location_id>` or `COR::<corridor_id>` or `SOLO::<screen_id>` |
| `cluster_type` | `same_stop` \| `same_corridor` \| `unresolved` |
| `n_screens_in_cluster` | |

**Screens sharing a `cluster_id` reach the same people. Do not sum their reach.**
Three panels on one shelter are one audience, not three.

## `corridor_overlap` — audience overlap, soft (for D4)

`corridor_a`, `corridor_b`, `shared_stops`, `jaccard` (only pairs ≥ 0.05)

Two corridors sharing 60% of stops carry substantially overlapping riders but
are *not* the same audience. Use `jaccard` as a **discount factor** on combined
reach, not as a merge. (We deliberately avoided transitive route merging — with
2,436 route_stops over 910 locations it collapses a whole city into one cluster.)

## `corridor_timeblock_ridership` — footfall lookup

`corridor_id`, `time_block_id`, `day_type`, `avg_trip_ridership`,
`avg_daily_block_riders`, `n_trips`, `n_days`

Pre-aggregated from the 2M-row `ridership_actuals`. `day_type` is
weekday|weekend — a campaign running Mon–Fri should not be priced off weekend
patterns. Profiles currently use **weekday**.

---

## Notes for whoever owns D3 (pricing)

Not my deliverable, but found while building D1 — saves you the rediscovery:

- **`lost_leads` has no `lead_expiry_date`** despite the problem statement claiming it. Use `lead_date` / `lost_date` for recency decay.
- `lost_leads.quoted_price_per_slot_per_day` vs `client_target_price_per_slot_per_day` vs `loss_reason='price_too_high'` is your **ceiling evidence**. `bookings` only contains prices that succeeded — it can't tell you where the cap is. This table can.
- `bookings.deal_id` + `is_bundle` + `deal_total_value` show how bundles were *actually* priced against the sum of their parts — direct evidence for the bundle nuance.
- `cities.market_tier` (premium/standard/value) and `client_facts.negotiation_leverage` are clean floor/cap modifiers.
- `events` is unused by D1 by design (profiles are steady-state). It's your demand-spike input: an event overlapping the campaign dates near a screen justifies a premium. Join on `anchor_location_id` — 86 rows have a null `poi_id`.
- `zone_demographics.daytime_population_multiplier` (up to 3.4x) should probably modulate daytime-block pricing, not just audience profiles.

## Open questions for the Hour 2 sync

- [ ] `screens.position` (top/left/right) is fixture placement, **not** compass facing — there's no facing field in the data. I use POI `side_of_road` as a soft weight instead of a hard line-of-sight filter. Object now if you disagree.
- [ ] Profiles are built on **weekday** ridership. Worth a weekend variant, or is a day_type flag on the campaign brief enough?
- [ ] `vehicles.screen_count` should reconcile with actual `screens` rows per vehicle — nobody has asserted this yet.

---

## `scored_priced_screens` — D2+D3 merged handoff to Person C (D6)

**Status: LIVE**, but per-campaign, not a static table — this is the output of
`pricing/merge_scored_priced.py`, called fresh for each parsed campaign brief.
Not persisted to the DB; returned as a DataFrame/JSON from the function call.

```python
from pricing.merge_scored_priced import build_scored_priced_screens
result_df, meta = build_scored_priced_screens(campaign_spec, conn)
```

| Column | Type | Description |
|---|---|---|
| `combined_rank` | int | 1 = best. Sorted by relevance_score desc, price_target asc as tiebreak |
| `screen_id` | str | |
| `time_block_id` | int | 1–6 |
| `relevance_score` | float [0,1] | D2 output |
| `relevance_reason` | str | Human-readable, built ONLY from computed sub-scores — never invented |
| `relevance_confidence` | str | `high`/`medium`/`low`, inherited from screen_audience_profile |
| `price_floor` | float | Never go below this |
| `price_target` | float | Recommended quote |
| `price_cap` | float | Scarcity ceiling — pulled down from real rejected-quote evidence where available |
| `demand_score` | float [0,1] | D3 demand index |
| `demand_confidence` | str | `own_history` / `inferred_cluster` / `inferred_city` / `inferred_global` |

### `meta` dict returned alongside

```python
{"city_id": "LH", "zone_ids": None, "n_screens_scored": 936}
```
If `n_screens_scored` is 0, the UI (D6) should show "no screens matched — try
broadening geography" rather than an empty table with no explanation.

### Things Person C needs to know

1. **`price_floor <= price_target <= price_cap` is a hard invariant** — verified in `verify_scoring_pricing.py`. If you ever see this violated, it's a bug to report, not something to work around in the UI.
2. **Show `relevance_confidence` and `demand_confidence` in the UI**, not just the scores. A `low` relevance_confidence screen ranking well should visually read differently from a `high` one — the rep needs to know which recommendations to trust more.
3. **`relevance_reason` is a semicolon-joined string of the actual sub-score evidence** — safe to show verbatim in a card, no further processing needed.
4. **This function must be called once per (brief, and optionally per time_block if you want block-specific views)** — it's not a lookup against a pre-built table like D1's `screen_audience_profile`.

### Known limitations, flagged honestly

- **Lead pressure (part of `demand_score`) is not time-block specific** — `lost_leads` has no time_block column, so a lead's pressure applies to all 6 blocks of that screen equally. Booking density IS block-specific, so blocks still differentiate overall.
- **Event pressure only applies to `fixed` screens currently** — vehicle screens get `event_pressure_raw = 0` rather than an invented estimate, since matching an event to "any stop this bus passes" needs a join not yet wired up. If this matters for the demo, flag it and I'll wire it in.
- **`price_target`/`price_cap` are built on `db/test.db`-scale sanity checks; re-verify the demand→price correlation on the real 11K-screen data** (`verify_scoring_pricing.py` Section 3 checks this automatically).

---

## LLM provider: Azure OpenAI (not Anthropic) — read this before writing any prompt code

The team's actual credentials are Azure OpenAI, not Claude. **One shared
client module, `common/llm_client.py`, handles this for everyone** — import
from it rather than calling `AzureOpenAI()` yourself, so endpoint/deployment
names/retry logic live in exactly one place.

```python
from common.llm_client import chat_completion, clean_json_response, CHAT_FAST, CHAT_CAPABLE

text = chat_completion(
    messages=[{"role": "user", "content": your_prompt}],
    model=CHAT_FAST,              # or CHAT_CAPABLE for higher-stakes output
    max_completion_tokens=1000,   # NOT max_tokens
)
```

**Setup (once, per machine):**
```bash
pip install openai        # NOT anthropic
export AZURE_OPENAI_API_KEY=<key 1 from the team dashboard>
```
(Endpoint and API version are hardcoded as defaults in `llm_client.py` since
they're shared, non-secret team values — only the key needs an env var.)

**Which deployment to use:**
- `CHAT_FAST` (gpt-5.4-nano) — high-volume, low-stakes text. Used for D1's
  batch profile generation (~67K rows) and D2's brief parsing.
- `CHAT_CAPABLE` (gpt-5.4-mini) — final-mile polish shown directly to a
  sales rep. Used for D1's on-demand enrichment layer and should be used
  for D5's final agentic recommendation write-up too.
- `EMBEDDING` (text-embedding-3-small) — only needed if D2's scoring is
  upgraded from rule-based to embedding cosine similarity.

**Rate limit: 500 req/min per deployment, shared across the whole team.**
`chat_completion()` already retries with exponential backoff on a 429 — call
it instead of the raw SDK method so you get this for free. If the team hits
limits during a demo (everyone testing at once), that's a shared-key
problem, not a bug in your code — coordinate in chat rather than debugging
your own script.

**Files already migrated:** `scoring/brief_parser.py`,
`features/enrich_profiles_llm.py`. `features/build_audience_profile.py`
never called an LLM directly (it's deterministic by design — see its
docstring) so nothing to migrate there.