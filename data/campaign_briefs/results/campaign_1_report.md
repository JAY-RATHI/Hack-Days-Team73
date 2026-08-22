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
  "preferred_dayparts": [],
  "budget": 40000.0,
  "duration_days": 45,
  "requires_broad_coverage": false,
  "exclusion_criteria": [
    "Exclude bus-rear screens",
    "Exclude value-tier inventory in high-density residential areas"
  ],
  "location_type_preference": null,
  "rotation_slots_per_day": 1,
  "start_date": null,
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
  "n_screen_timeblock_pairs": 17,
  "n_unique_screens": 17,
  "n_clusters_represented": 16,
  "total_cost": 39561.75,
  "budget": 40000.0,
  "budget_utilization_pct": 98.9,
  "duration_days": 45,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 625037.0,
  "total_projected_impressions_per_week": 4375261.0,
  "avg_relevance_score_selected": 0.656,
  "availability": {
    "checked": false,
    "note": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
  },
  "caveat_availability": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
}
```

## Narrative

For a conversion-focused buy in LH, this package is tightly budgeted at $39,561.75, using 98.9% of the $40,000 budget across 17 screen-timeblock pairs on 17 unique screens and 16 clusters over 45 days. It projects 625,037 impressions per day, or 4,375,261 per week, with an average selected relevance score of 0.656.

The strongest individual options are all time block 5. LH-SCR-003593 stands out with 47,342 marginal daily impressions at $63.48 and 57% of the local population in the 18_34/35_54 target range, plus nearby office_park POIs. LH-SCR-003105 is slightly cheaper at $59.80 with 45,879 impressions and 70% target-age population, but it has no nearby office_park match. LH-SCR-004282 offers 45,678 impressions at $68.53 with 70% target-age population and office_park relevance. LH-SCR-002514 is the lowest-priced of the top five at $58.86 with 45,181 impressions and office_park relevance, though only 48% target-age population. LH-SCR-004595 is $58.43 with 44,062 impressions and 70% target-age population, but also no nearby office_park match.

Two exclusions were enforced: bus-rear screens removed 810 screens, and value-tier inventory in high-density residential areas removed 3,060 screens. Availability was not checked, so all candidates are assumed available.

## Selected screens

```
    screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
LH-SCR-003593              5           0.7979         63.48                47342.207415
LH-SCR-004282              5           0.8533         68.53                45678.367224
LH-SCR-005033              3           0.7510         57.52                41104.238927
LH-SCR-002514              5           0.6831         58.86                45180.616705
LH-SCR-003799              3           0.5412         47.09                41055.080828
LH-SCR-005502              3           0.5090         46.22                41675.698058
LH-SCR-002880              3           0.7742         48.97                28196.791994
LH-SCR-005329              3           0.8366         50.62                26958.961828
LH-SCR-002639              3           0.5099         44.06                37103.673431
LH-SCR-003105              5           0.5557         59.80                45878.601391
LH-SCR-005976              3           0.8530         54.65                27249.852779
LH-SCR-004595              5           0.5581         58.43                44061.839056
LH-SCR-005279              3           0.5581         47.81                35792.805959
LH-SCR-002375              3           0.4733         44.49                39221.210479
LH-SCR-005373              3           0.5724         50.85                36080.133183
LH-SCR-004997              3           0.5099         44.33                34992.933552
LH-SCR-003562              6           0.8117         33.44                 7464.220904
```