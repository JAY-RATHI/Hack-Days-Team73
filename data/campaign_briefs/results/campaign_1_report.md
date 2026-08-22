# Report: campaign_1

**Status:** ok

## Spec (extracted from brief)
```json
{
  "city_hint": "Las Hackland",
  "target_zones_text": [],
  "target_age_min": 28,
  "target_age_max": 50,
  "target_income_tier": "high",
  "audience_descriptors": [
    "urban professionals",
    "eco-conscious upgraders",
    "homeowner",
    "senior professional",
    "commuters",
    "research heavily"
  ],
  "poi_affinities": [
    "office_park"
  ],
  "objective": "conversion",
  "preferred_dayparts": [
    "morning",
    "afternoon",
    "evening"
  ],
  "budget": 40000.0,
  "duration_days": 45,
  "requires_broad_coverage": false,
  "exclusion_criteria": [
    "Exclude bus-rear screens",
    "Exclude value-tier inventory in high-density residential areas"
  ],
  "location_type_preference": null,
  "rotation_slots_per_day": 1,
  "raw_brief_text": "Customer Campaign Briefs\nDigital Out-of-Home Campaign Portfolio\nCLIENT BRIEF 1: ZEPHYR EV \u2014 THE FUTURE HAS NO TAILPIPE\nCompany Name: Voltaic Motors Inc. (Brand: Zephyr EV)\nIndustry Vertical: AUTOMOTIVE / ELECTRIC VEHICLES\nCampaign Objective: Brand Awareness & Test-Drive Bookings\nTarget Audience: Urban professionals and eco-conscious upgraders (Ages 28-50)\nCampaign Budget: USD 40,000\nCampaign Duration: 45 Days (Proposed: Q1 2027 \u2014 pre-monsoon launch window)\n1. Executive Summary & Objective\nVoltaic Motors is launching the Zephyr EV, its first mass-premium electric sedan, in Las Hackland ahead of a citywide dealership rollout. The campaign must build credible brand presence in a category where commuters default to established fuel-vehicle brands, while driving measurable test-drive bookings through a QR-linked scheduling flow. The creative direction favors calm, premium confidence over aggressive discounting.\n2. Target Audience & Persona\nThe target buyer is a homeowner or senior professional currently driving a fuel vehicle, financially comfortable enough to consider an upgrade but requiring reassurance on range, charging convenience, and resale value before committing. They commute by car during peak hours but pass through metro and business-district transit corridors regularly for meetings, meaning transit advertising still reaches them even though they don't ride transit daily. They research heavily before buying and respond to clean, factual messaging over hype.\n3. Digital Screen Selection & Location Requirements\nHigh-Dwell Business-District Platforms: Metro platform boards in the city's primary commercial and financial districts, where affluent professional commuters typically spend three to six minutes waiting on the platform.\nAuto-Retail Arterial Corridors: Roadside-adjacent transit screens on major arterial routes with a dense concentration of car dealerships, positioned to intercept shoppers already actively comparing vehicles.\nExclusion Criteria: Exclude bus-rear screens and value-tier inventory in high-density residential areas \u2014 the campaign is intentionally not mass-market and should avoid diluting the premium positioning.\n4. Visual / Mockup Details & Slot Parameters\nVoltaic Motors will supply a premium static/motion hybrid asset. The creative features matte charcoal and electric-blue gradients, a single hero product shot of the Zephyr EV silhouette, and minimal copy. Layout is optimized for an ultra-wide 16:9 digital display to read clearly from across platform tracks. Leasing structure requested: 1 rotating slot (15 seconds per minute) on digital screens only.\nReference Mockup A \u2014 Premium Minimalist \u2014 Matte Charcoal & Electric Blue\nReference Mockup B \u2014 16:9 Metro Platform Wide-Screen Display\n5. RFP Requirements (Sales Team Response)\nTo accept this campaign brief, the Urban Media commercial intelligence agent must generate a formalized response containing:\n1. A curated shortlist of screens across the premium business-district platforms and auto-retail arterial corridors described above, ranked by affluent-commuter affinity.\n2. An optimal price recommendation reflecting premium-node demand, platform dwell time, and proximity to competing dealerships.\n3. Projected weekly impressions and test-drive-booking potential, with logical justification for each recommended location."
}
```

## Meta (geography/exclusions)
```json
{
  "city_id": "LH",
  "zone_ids": null,
  "n_screens_scored": 33954,
  "exclusion_log": [
    {
      "criterion": "Exclude bus-rear screens",
      "enforced": true,
      "screens_removed": 810
    },
    {
      "criterion": "Exclude value-tier inventory in high-density residential areas",
      "enforced": true,
      "screens_removed": 3060
    }
  ],
  "location_filter_log": null
}
```

## Package Summary
```json
{
  "n_screen_timeblock_pairs": 14,
  "n_unique_screens": 14,
  "n_clusters_represented": 14,
  "total_cost": 38161.35,
  "budget": 40000.0,
  "budget_utilization_pct": 95.4,
  "duration_days": 45,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 609809.0,
  "total_projected_impressions_per_week": 4268660.0,
  "avg_relevance_score_selected": 0.696
}
```

## Narrative

For this conversion-focused LH buy, the current package is strong on evening commuter reach and is using 14 screen-timeblock pairs across 14 unique screens, with 14 clusters represented. It spends $38,161.35 of the $40,000 budget, so budget utilization is 95.4% over 45 days. Projected delivery is 609,809 impressions per day, or 4,268,660 per week, with an average relevance score of 0.696.

The top opportunities are all evening daypart placements with commuter index around 0.51–0.52 and daily marginal impressions in the 46,214–47,461 range. LH-SCR-003105 is the strongest by relevance: 70% of the local population is in the 18_34/35_54 target range, commuter index is 0.52, and it matches evening, but it has no nearby office_park POIs. LH-SCR-003593 and LH-SCR-005041 both have 57% in target age range and nearby office_park POIs, while LH-SCR-003796 and LH-SCR-002359 are lower on age fit at 48%.

Two exclusions were enforced and should be noted: bus-rear screens were removed (810 screens), and value-tier inventory in high-density residential areas was removed (3,060 screens).

## Selected screens

```
    screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
LH-SCR-003593              5           0.8579         63.48                47342.207415
LH-SCR-004282              5           0.9133         68.53                45678.367224
LH-SCR-002514              5           0.7431         58.86                45180.616705
LH-SCR-005041              5           0.7838         65.01                46238.163924
LH-SCR-003105              5           0.6157         59.80                47461.440429
LH-SCR-004595              5           0.6181         58.43                44157.561253
LH-SCR-002359              5           0.5333         53.65                46214.140530
LH-SCR-003796              5           0.5792         59.68                46853.164862
LH-SCR-005519              5           0.5690         56.76                44821.268042
LH-SCR-002619              5           0.5699         56.59                44284.391577
LH-SCR-005985              5           0.9130         63.99                31140.442669
LH-SCR-005312              5           0.8372         58.87                31150.225940
LH-SCR-005255              5           0.6181         61.40                43406.298422
LH-SCR-003650              5           0.5958         62.98                45880.331971
```