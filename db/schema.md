# Urban Media — Database Schema (CONFIRMED against real data)

All column names below are verified from the actual CSVs. Row counts are real.

## The four things that surprised us (read this first)

1. **There is no latitude/longitude anywhere in this dataset.** Proximity is
   pre-computed: `points_of_interest` carries `anchor_location_id` and
   `distance_to_location_km`. So "POIs near a screen" is a **join**, not a
   geospatial calculation. Don't write a haversine function.
2. **`screens` contains two fundamentally different assets.** 8,548 rows have
   `location_id` (fixed at a stop/station). 2,615 have `vehicle_id` (mounted
   inside a bus/coach). A row never has both. They need different audience
   logic — see `screen_geo_map`.
3. **`vehicles` links to `corridor_id`, not `route_id`.** A *corridor* is the
   two-way line (`LH-RT-B001`); a *route_id* is one direction of it
   (`LH-RT-B001-OUT`). Riders belong to the corridor. Join accordingly.
4. **`lost_leads` has no `lead_expiry_date`,** despite the problem statement
   saying so. Use `lead_date`, `lost_date`, and `requested_start_date` for
   recency weighting instead. **Person doing D3: this affects you.**

## Join key map

| Key | Found in | Notes |
|---|---|---|
| `screen_id` | screens, bookings, lost_leads(`anchor_screen_id`) | |
| `location_id` | locations, screens, route_stops, points_of_interest(`anchor_location_id`) | the hinge of the whole schema |
| `corridor_id` | route_stops, vehicles, route_schedules | rider-level identity |
| `route_id` | route_stops, route_schedules, ridership_actuals | one direction of a corridor |
| `zone_id` | zone_demographics, locations | demographics only reachable via location |
| `schedule_id` | route_schedules, ridership_actuals | how ridership gets a time |
| `time_block_id` | dim_slot, bookings | 1–6; **not** present in ridership data |
| `city_id` | almost everything | LH / ACS / DAT |
| `client_id` | client_facts, bookings, lost_leads | 643 lost_leads have NULL client_id |

**The critical path:** `screens.location_id → locations.zone_id → zone_demographics`
for fixed screens; `screens.vehicle_id → vehicles.corridor_id → route_stops.location_id
→ locations.zone_id` for vehicle screens.

---

## Geography

### `cities` — 3 rows
`city_id`, `city_name`, `population`, `transit_density`, `market_tier`, `timezone`
- LH = Las Hackland (3.2M, dense, **premium**), DAT = DA Town (1.45M, mixed, standard), ACS = Accordionshire (850K, sprawling, **value**)
- `market_tier` is a direct pricing input for D3 — premium/standard/value.

### `zone_demographics` — 30 rows (10 per city)
`zone_id`, `city_id`, `zone_name`, `resident_population`, `population_density_per_sqkm`,
`median_age`, `pct_age_under_18`, `pct_age_18_34`, `pct_age_35_54`, `pct_age_55_plus`,
`median_household_income`, `income_index`, `pct_bachelor_or_higher`,
`dominant_occupation`, `daytime_population_multiplier`
- `income_index` is normalised (~100 = average) → easier than raw income for scoring.
- `daytime_population_multiplier` (1.4–3.4) is how much the zone swells during work hours. **Use this to modulate daytime blocks (3, 4) — a 3.39x downtown zone is a completely different audience at midday than at night.**
- `dominant_occupation`: white_collar / blue_collar / mixed → maps well to campaign targeting.

### `locations` — 910 rows
`location_id`, `city_id`, `name`, `city_zone`, `zone_id`, `location_type`
- `location_type`: bus_stop | metro_station
- `city_zone` is a human-readable name; `zone_id` is the FK. Note `points_of_interest` and `events` carry `city_zone` (text) — join those on `anchor_location_id` instead.

## Network

### `route_stops` — 2,436 rows
`route_id`, `corridor_id`, `city_id`, `route_name`, `mode`, `direction`,
`stop_sequence`, `location_id`, `is_first_stop`, `is_last_stop`, `num_stops`
- `mode`: bus | (metro variants)
- This is the only table linking corridors to locations. It powers both audience-overlap clustering and vehicle-screen zone resolution.

### `vehicles` — 854 rows
`vehicle_id`, `city_id`, `vehicle_type`, `corridor_id`, `screen_count`
- `screen_count` should reconcile with the count of `screens` rows per vehicle — worth asserting.

### `route_schedules` — 19,838 rows
`schedule_id`, `route_id`, `corridor_id`, `direction`, `day_type`, `start_time`, `estimated_ridership`
- `day_type`: weekday | weekend
- `start_time` is a `"HH:MM"` **string**. Bucket to a time block with `hour // 4 + 1`.
- `estimated_ridership` is the *planned* figure; `ridership_actuals` has the real one. Use actuals; the gap between them is itself a signal.

### `ridership_actuals` — 2,049,632 rows ⚠️ largest table
`schedule_id`, `route_id`, `city_id`, `date`, `day_of_week`, `is_holiday`, `actual_ridership`
- **Has no `time_block_id`.** Time comes only via `schedule_id → route_schedules.start_time`.
- One row per scheduled trip per date. Aggregate in SQL, never in pandas loops.
- Pre-aggregated for you into `corridor_timeblock_ridership` (see derived tables).

## Inventory

### `screens` — 11,163 rows
`screen_id`, `city_id`, `screen_type`, `location_id`, `vehicle_id`, `position`, `screen_size`
- Nulls are meaningful, not dirty: `location_id` null (2,615) = vehicle screen; `vehicle_id` null (8,548) = fixed screen.
- `position` null for 1,400 rows. Values are top/left/right etc. — **this is placement on the fixture, NOT compass facing.** Do not use it as a line-of-sight filter; there is no facing-direction field in this data.
- `screen_size`: S/M/L → an impressions multiplier input for D4.

## Context

### `points_of_interest` — 1,375 rows
`poi_id`, `city_id`, `city_zone`, `name`, `poi_type`, `scale`, `est_daily_footfall`,
`anchor_location_id`, `distance_to_location_km`, `distance_to_location_mi`,
`is_network_hub`, `side_of_road`, `peak_daypart`
- **~1.5 POIs per location on average.** Any rule needing "3+ nearby POIs" will fire almost never — calibrate thresholds to this density.
- `peak_daypart` matches `dim_slot.nearest_daypart` → this is how a POI becomes *time-aware*. A mall peaking in the evening should boost block 5, not block 2.
- `side_of_road`: near_side | far_side. Used as a soft weight (far side is harder to notice), not a hard filter.
- `is_network_hub` marks interchange-scale locations — strong relevance signal.

### `events` — 367 rows
`event_id`, `city_id`, `city_zone`, `poi_id`, `anchor_location_id`, `event_name`,
`event_type`, `recurrence`, `start_date`, `end_date`, `expected_attendance`,
`attendance_tier`, `primary_impact_daypart`, `impact_radius_km`
- 86 rows have null `poi_id` — join on `anchor_location_id`, which is always present.
- **Not used in D1** (audience profiles are steady-state). This is a **D3 demand-spike input**: an event overlapping a campaign's date range near a screen justifies a price premium.
- `impact_radius_km` exists but there are no coordinates to apply it to — you can only use it relative to `anchor_location_id`. Practical approach: treat the anchored location as affected, and optionally its corridor neighbours.

## Commercial

### `client_facts` — 520 rows
`client_id`, `company_name`, `industry`, `client_tier`, `home_city_id`, `active_cities`,
`preferred_geographies`, `typical_campaign_budget`, `budget_variance_pct`,
`campaign_frequency`, `avg_campaign_duration_days`, `bundle_affinity`,
`negotiation_leverage`, `relationship_start_date`, `account_status`
- `negotiation_leverage` (low/medium/high) and `client_tier` are direct floor/cap inputs for D3 — a high-leverage client realistically gets closer to the floor.
- `bundle_affinity` tells D4 whether to even propose a multi-mode package.
- `active_cities` / `preferred_geographies` are colon-delimited strings (`"DAT:Central Yard"`) — parse, don't join.

### `dim_slot` — 6 rows
`time_block_id`, `time_block_label`, `start_hour`, `end_hour`, `nearest_daypart`
- Blocks **1 and 6 are both "night"** — a daypart→block mapping is one-to-many. Don't assume a unique inverse.

### `bookings` — 191,109 rows
`booking_id`, `deal_id`, `client_id`, `city_id`, `screen_id`, `ad_type`,
`industry_vertical`, `campaign_objective`, `time_block_id`, `daypart`,
`slots_booked_per_day`, `rotation_type`, `start_date`, `end_date`, `duration_days`,
`booked_date`, `contracted_price_per_slot_per_day`, `line_item_value`,
`deal_total_value`, `is_bundle`, `booking_status`
- **`contracted_price_per_slot_per_day` is the ground truth D3 must predict.** The spread of this column for similar screen/block/season combos *is* the floor→cap range.
- `deal_id` groups line items into one deal; `is_bundle` + `deal_total_value` reveal how bundles were actually priced vs. their parts. **This is the evidence base for the "a bundle isn't three independent decisions" nuance.**
- `booked_date` vs `start_date` = lead time, a demand signal.
- `campaign_objective` (awareness/frequency/conversion) is the label a campaign brief maps onto — critical for D2.
- Filter on `booking_status` before computing occupancy; cancelled bookings shouldn't block inventory.

### `lost_leads` — 1,450 rows
`lead_id`, `client_id`, `company_name_raw`, `industry_vertical`, `city_id`,
`requested_geography`, `anchor_screen_id`, `lead_source`, `lead_date`,
`sales_stage_reached`, `lost_date`, `requested_start_date`,
`requested_duration_days`, `requested_num_screens`, `indicated_budget`,
`quoted_price_per_slot_per_day`, `client_target_price_per_slot_per_day`,
`price_gap_pct`, `negotiation_rounds`, `competitor_mentioned`, `loss_reason`,
`loss_reason_detail`, `campaign_objective`, `ad_type`
- **The most valuable table for pricing and the least obvious.** `quoted_price` vs `client_target_price` vs `loss_reason='price_too_high'` tells you where the ceiling actually is — bookings only show prices that *worked*.
- Nulls: `client_id` 643, `quoted_price` 531, `client_target_price` 690, `price_gap_pct` 690. Leads lost early have no price data. Handle it, don't drop the rows blindly.
- Unconverted demand near a screen = demand pressure. Weight by recency using `lead_date`/`lost_date` (there is no expiry column).

---

## Derived tables (built by our scripts, not in the raw data)

| Table | Built by | Contains |
|---|---|---|
| `screen_geo_map` | `features/screen_geo_map.py` | screen → kind, location, corridors, zones |
| `screen_cluster_map` | `features/route_cluster_map.py` | screen → audience cluster (hard overlap) |
| `corridor_overlap` | `features/route_cluster_map.py` | corridor pair → Jaccard on shared stops (soft overlap) |
| `corridor_timeblock_ridership` | `features/ridership_by_block.py` | corridor × block × day_type → rider volumes |
| `screen_audience_profile` | `features/build_audience_profile.py` | screen × block → profile text, tags, features, confidence |