# Report: campaign_6

**Status:** ok

## Spec (extracted from brief)
```json
{
  "city_hint": null,
  "target_zones_text": [],
  "target_age_min": 18,
  "target_age_max": 34,
  "target_income_tier": "high",
  "audience_descriptors": [
    "young women",
    "beauty-conscious commuters",
    "beauty-engaged",
    "skincare trends followers",
    "frequent mall visitors",
    "regular metro commuters"
  ],
  "poi_affinities": [
    "shopping_mall",
    "office_park"
  ],
  "objective": "awareness",
  "preferred_dayparts": [],
  "budget": 20000.0,
  "duration_days": 25,
  "requires_broad_coverage": false,
  "exclusion_criteria": [],
  "location_type_preference": null,
  "rotation_slots_per_day": null,
  "raw_brief_text": "CLIENT BRIEF 6: LUMI\u00c8RE COSMETICS \u2014 GLOW ON YOUR TERMS\nCompany Name: Lumi\u00e8re Cosmetics Group\nIndustry Vertical: BEAUTY & PERSONAL CARE\nCampaign Objective: New Product Launch Awareness\nTarget Audience: Young women, beauty-conscious commuters (Ages 18-34)\nCampaign Budget: USD 20,000\nCampaign Duration: 25 Days (Proposed: Spring product launch)\n1. Executive Summary & Objective\nLumi\u00e8re is launching a new radiance serum and wants to build product awareness among beauty-conscious commuters ahead of in-store availability. The campaign leans on elegant, aspirational creative rather than discount-driven messaging, positioning the product as a premium addition to an existing skincare routine rather than an impulse buy.\n2. Target Audience & Persona\nThe audience is young, beauty-engaged women who follow skincare trends closely and shop at both mall beauty counters and standalone retail. They are frequent mall visitors and regular metro commuters, and respond to elegant, editorial-style visuals over bold discount signage \u2014 the brand experience matters as much as the offer.\n3. Digital Screen Selection & Location Requirements\nMall Beauty-Retail Entry: Premium vertical screens at shopping centre entrances adjacent to beauty and lifestyle retail concessions, reaching shoppers moments before they pass a beauty counter.\nHigh-Street Retail Corridors: Vertical screens along high-street shopping strips with a concentration of competing beauty retailers.\nCentral Metro Entry Coverage: Supplementary vertical placements at central metro entry points, for repeated commuter exposure ahead of weekend shopping trips.\n4. Visual / Mockup Details & Slot Parameters\nLumi\u00e8re will supply a static editorial visual \u2014 soft blush pink and gold tones, elegant product photography, and refined serif-adjacent typography reading \"Glow On Your Terms.\" Canvas optimized for tall vertical formats at mall and metro entry points.\nReference Mockup A \u2014 Elegant Editorial \u2014 Blush Pink & Gold\nReference Mockup B \u2014 9:16 Vertical Mall / Metro Entry Poster\n5. RFP Requirements (Sales Team Response)\nTo accept this campaign brief, the Urban Media commercial intelligence agent must generate a formalized response containing:\n1. An inventory plan anchored on mall beauty-retail entry points and high-street retail corridors, with supplementary central metro entry coverage.\n2. Pricing reflecting premium mall-entry positioning and the value of beauty-retail adjacency.\n3. A projected reach estimate for the 25-day window, with reasoning tied to beauty-audience affinity at each recommended node type."
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
  "n_screen_timeblock_pairs": 19,
  "n_unique_screens": 19,
  "n_clusters_represented": 18,
  "total_cost": 19522.0,
  "budget": 20000.0,
  "budget_utilization_pct": 97.6,
  "duration_days": 25,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 625998.0,
  "total_projected_impressions_per_week": 4381984.0,
  "avg_relevance_score_selected": 0.633
}
```

## Narrative

For an awareness push, this package is strong on reach and nearly fully uses budget: total cost is 19,522 against a 20,000 budget, or 97.6% utilization, over 25 days. It delivers 625,998 projected impressions per day and 4,381,984 per week, with an average relevance score of 0.633 across 19 unique screen/time-block pairs spanning 18 clusters. The best-value options are the 18–34-heavy shopping mall placements in time block 3: LH-SCR-002699 at 44.14 with 45,987 marginal daily impressions, LH-SCR-002837 at 45.08 with 42,349, LH-SCR-003222 at 49.34 with 42,017, and LH-SCR-004542 at 48.06 with 40,771. LH-SCR-004282 is also strong for reach at 45,678 daily impressions, but it is pricier at 68.53 and is the only one here tied to both shopping mall and office park POIs. The relevance notes are consistent: 66% of local population in the 18–34 range for the time block 3 screens, with commuter index 0.52; LH-SCR-004282 shows 38% in range and commuter index 0.51. No exclusions were applied.

## Selected screens

```
     screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
DAT-SCR-002819              3           0.7183         35.82                37874.001227
ACS-SCR-001662              3           0.6124         24.21                28913.110798
 LH-SCR-002699              3           0.6285         44.14                45986.654387
ACS-SCR-001496              3           0.5934         26.93                26899.704575
 LH-SCR-002837              3           0.6134         45.08                42348.829712
DAT-SCR-002232              3           0.5548         35.77                36138.575869
DAT-SCR-001704              3           0.5548         33.59                33930.471661
DAT-SCR-001772              3           0.6151         33.93                29555.939425
 LH-SCR-003222              3           0.6039         49.34                42016.554844
DAT-SCR-003049              3           0.7135         45.17                31876.783468
 LH-SCR-004542              3           0.5800         48.06                40771.353239
 LH-SCR-004282              5           0.7093         68.53                45678.367224
 LH-SCR-003976              3           0.7279         47.42                29034.489599
DAT-SCR-002975              3           0.5629         31.43                24396.702031
ACS-SCR-001614              2           0.5533         24.86                19140.606786
DAT-SCR-001649              5           0.7135         58.48                34746.179008
DAT-SCR-003030              3           0.7008         59.44                35881.911425
DAT-SCR-001975              3           0.5548         31.86                23674.192526
DAT-SCR-002820              3           0.7183         36.82                17133.251305
```