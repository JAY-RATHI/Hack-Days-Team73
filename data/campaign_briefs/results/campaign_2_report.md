# Report: campaign_2

**Status:** ok

## Spec (extracted from brief)
```json
{
  "city_hint": null,
  "target_zones_text": [
    "Nightlife and Entertainment Corridors",
    "Campus-Edge Transit Nodes",
    "Event-Venue Precincts"
  ],
  "target_age_min": 18,
  "target_age_max": 30,
  "target_income_tier": "value",
  "audience_descriptors": [
    "Gen Z",
    "young professionals",
    "gym-goers",
    "night-shift workers",
    "students",
    "price-sensitive",
    "occasion-based messaging",
    "out late",
    "late study sessions",
    "post-gym slumps",
    "post-venue crowds heading home"
  ],
  "poi_affinities": [
    "stadium_arena",
    "entertainment_district",
    "university"
  ],
  "objective": "conversion",
  "preferred_dayparts": [
    "evening",
    "night",
    "morning"
  ],
  "budget": 12000.0,
  "duration_days": 21,
  "requires_broad_coverage": false,
  "exclusion_criteria": [],
  "location_type_preference": null,
  "rotation_slots_per_day": null,
  "raw_brief_text": "CLIENT BRIEF 2: EMBER ENERGY \u2014 IGNITE EVERY HOUR\nCompany Name: Ember Beverages LLC\nIndustry Vertical: FMCG / BEVERAGES (ENERGY DRINKS)\nCampaign Objective: Trial & Impulse Purchase\nTarget Audience: Gen Z and young professionals, gym-goers, night-shift workers (Ages 18-30)\nCampaign Budget: USD 12,000\nCampaign Duration: 21 Days (Proposed: Exam season / Fall semester)\n1. Executive Summary & Objective\nEmber Energy is a new zero-sugar energy drink entering a crowded category dominated by two legacy brands. Rather than compete on brand heritage, the campaign leans into moments of specific fatigue \u2014 late study sessions, night shifts, post-gym slumps \u2014 and positions Ember as the answer to that exact moment. Success is measured by trial at nearby retail points, not brand recall.\n2. Target Audience & Persona\nThe audience is young, price-sensitive, and highly responsive to occasion-based messaging rather than brand loyalty. They're out late \u2014 studying, working night shifts, or leaving the gym \u2014 and are more likely to try a new energy drink out of genuine tiredness than brand preference. They notice bold, high-contrast creative and respond to humor and directness over polish.\n3. Digital Screen Selection & Location Requirements\nNightlife and Entertainment Corridors: Bus rear screens on routes running through late-night entertainment districts, positioned to catch post-venue crowds heading home.\nCampus-Edge Transit Nodes: Screens at transit nodes serving large student populations, timed to exam-season late-study patterns.\nEvent-Venue Precincts: Digital boards near major stadium and arena precincts, where footfall spikes sharply on event nights.\nTime-of-Day Target: Heavy weighting on late evening through early morning rather than standard commute peaks.\n4. Visual / Mockup Details & Slot Parameters\nEmber will supply a dynamic motion graphic asset. Bold orange-to-red flame gradients against near-black backgrounds, high-contrast yellow callout text, and a QR code linking to a nearby-retailer locator. Because of the motion elements, the campaign is restricted to digital-only screens. Canvas: square format optimized for bus-rear and vertical poster placements.\nReference Mockup A \u2014 High-Energy \u2014 Flame Orange & Near-Black\nReference Mockup B \u2014 1:1 Square / Bus Rear-Screen or Vertical Poster\n5. RFP Requirements (Sales Team Response)\nTo accept this campaign brief, the Urban Media commercial intelligence agent must generate a formalized response containing:\n1. An inventory package combining bus-rear screens on nightlife corridors with campus-edge and event-venue digital boards.\n2. Dynamic pricing reflecting late-night demand patterns and event-night surge behaviour near major venues.\n3. A reach plan optimised for unique late-night impressions within the stated budget, prioritising frequency over broad daytime coverage."
}
```

## Meta (geography/exclusions)
```json
{
  "city_id": null,
  "zone_ids": null,
  "n_screens_scored": 66978,
  "exclusion_log": [],
  "location_filter_log": null
}
```

## Package Summary
```json
{
  "n_screen_timeblock_pairs": 15,
  "n_unique_screens": 15,
  "n_clusters_represented": 12,
  "total_cost": 11988.48,
  "budget": 12000.0,
  "budget_utilization_pct": 99.9,
  "duration_days": 21,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 467652.0,
  "total_projected_impressions_per_week": 3273562.0,
  "avg_relevance_score_selected": 0.804
}
```

## Narrative

For a conversion-focused pitch, this package is essentially fully spent at $11,988.48 on a $12,000 budget, so it’s a near-max budget recommendation with 99.9% utilization over 21 days. The selected mix is strong on the core audience: the top screens all sit in areas where 65%–66% of the local population is 18–34, with a commuter index of 0.52, and several are near university and entertainment district POIs. The best-fit evening options are LH-SCR-003202 at time block 5 with 49,678 marginal daily impressions for $56.33, and LH-SCR-004536 at time block 5 with 44,134 impressions for $54.69. If you need cheaper reach, LH-SCR-002232 delivers 39,943 impressions at $35.77, but it is outside the requested dayparts, as are LH-SCR-002837 and LH-SCR-002699. Overall projected delivery is 467,652 impressions per day, or 3,273,562 per week, with an average relevance score of 0.804 across the selected package. The main caveat to flag is that some of the lower-cost screens do not match the requested evening/night/morning dayparts, so if daypart alignment is critical, keep the conversation centered on the evening screens.

## Selected screens

```
     screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
DAT-SCR-001704              3           0.7948         33.59                37502.593712
ACS-SCR-001614              2           0.9133         24.86                22620.819932
 LH-SCR-003202              5           0.9169         56.33                49677.762725
 LH-SCR-002837              3           0.7957         45.08                44502.763464
 LH-SCR-002699              3           0.7642         44.14                42921.643872
 LH-SCR-004536              5           0.9166         54.69                44134.381054
DAT-SCR-002232              3           0.6550         35.77                39943.162055
ACS-SCR-001492              3           0.7693         26.93                25106.839265
ACS-SCR-001662              5           0.7870         27.95                24019.116528
DAT-SCR-001975              3           0.7948         31.86                23674.192526
 LH-SCR-002332              5           0.9142         50.19                31285.614306
DAT-SCR-002819              3           0.5630         35.82                34266.502610
DAT-SCR-001708              3           0.7948         33.67                16965.235831
 LH-SCR-002701              3           0.7642         45.12                21460.821936
ACS-SCR-001611              2           0.9133         24.88                 9570.303393
```