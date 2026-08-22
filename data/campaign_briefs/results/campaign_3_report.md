# Report: campaign_3

**Status:** ok

## Spec (extracted from brief)
```json
{
  "city_hint": null,
  "target_zones_text": [],
  "target_age_min": 20,
  "target_age_max": 40,
  "target_income_tier": "mid",
  "audience_descriptors": [
    "style-conscious shoppers",
    "working professional",
    "student",
    "shops seasonally",
    "weekend shoppers",
    "post-work weekday evenings"
  ],
  "poi_affinities": [
    "shopping_mall"
  ],
  "objective": "frequency",
  "preferred_dayparts": [
    "evening"
  ],
  "budget": 22000.0,
  "duration_days": 20,
  "requires_broad_coverage": false,
  "exclusion_criteria": [],
  "location_type_preference": null,
  "rotation_slots_per_day": null,
  "start_date": null,
  "raw_brief_text": "CLIENT BRIEF 3: LOOM & THREAD \u2014 WEAR YOUR STORY\nCompany Name: Loom & Thread Apparel Co.\nIndustry Vertical: RETAIL / FASHION\nCampaign Objective: Seasonal Footfall & Sale Awareness\nTarget Audience: Style-conscious shoppers (Ages 20-40)\nCampaign Budget: USD 22,000\nCampaign Duration: 20 Days (Proposed: Autumn Collection Launch)\n1. Executive Summary & Objective\nLoom & Thread is a mid-premium apparel brand launching its Autumn Collection alongside a citywide seasonal sale. The campaign objective is footfall to flagship and mall locations within the promotional window. Unlike the brand's usual editorial-only advertising, this campaign carries an explicit commercial call to action tied to the sale dates.\n2. Target Audience & Persona\nThe target shopper is a working professional or student who shops seasonally rather than impulsively, follows a handful of apparel brands closely, and is influenced by editorial-style imagery over discount signage. They shop on weekends and post-work weekday evenings, favoring mall and high-street retail nodes over purely residential or industrial corridors.\n3. Digital Screen Selection & Location Requirements\nPremium Mall Entry Points: High-footfall digital boards at the entrances of the network's largest shopping centres, where shoppers arrive with purchase intent already formed.\nHigh-Street Retail Corridors: Screens along established high-street shopping strips with a concentration of competing apparel retailers.\nWeekend Weighting: Requesting weighted delivery from Friday evening through Sunday, aligned with peak discretionary shopping behaviour.\n4. Visual / Mockup Details & Slot Parameters\nLoom & Thread will supply a static editorial-style visual \u2014 earthy tones, natural linen textures, and minimal sale messaging (\"Autumn Edit \u2014 Now In Store\"). Canvas optimized for tall vertical formats at mall entries and high-street poster positions.\nReference Mockup A \u2014 Editorial Warmth \u2014 Earthy Tones & Natural Textures\nReference Mockup B \u2014 9:16 Vertical Mall Entry / High-Street Poster\n5. RFP Requirements (Sales Team Response)\nTo accept this campaign brief, the Urban Media commercial intelligence agent must generate a formalized response containing:\n1. An inventory plan anchored on premium mall entry points and high-street retail corridors.\n2. Pricing reflecting weekend-weighted delivery and premium mall-entry positioning.\n3. A footfall-oriented reach projection for the 20-day sale window, with the weekend-versus-weekday impression split shown separately."
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
  "n_screen_timeblock_pairs": 24,
  "n_unique_screens": 24,
  "n_clusters_represented": 24,
  "total_cost": 21855.6,
  "budget": 22000.0,
  "budget_utilization_pct": 99.3,
  "duration_days": 20,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 840342.0,
  "total_projected_impressions_per_week": 5882396.0,
  "avg_relevance_score_selected": 0.715,
  "availability": {
    "checked": false,
    "note": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
  },
  "caveat_availability": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
}
```

## Narrative

For a frequency buy, this package is strong on reach volume and stays essentially on budget: 24 screen-timeblock pairs across 24 unique screens for 20 days, totaling $21,855.60 against a $22,000 budget (99.3% utilized). Projected delivery is 840,342 impressions per day, or 5,882,396 per week, so it should build repetition quickly.

The best-fit screens are LH-SCR-004536 and LH-SCR-003202, both in time block 5, with 85% of the local population in the target age range, commuter index 0.52, evening daypart match, and nearby shopping mall POIs. They also deliver the strongest marginal daily impressions in the set at 47,286 and 46,367, with price targets of $54.69 and $56.33. LH-SCR-003019 is also evening-aligned but has weaker age fit at 57% and a higher price target of $67.52. LH-SCR-002699 is cheaper at $44.14 and still has 45,987 marginal daily impressions, but it is outside the requested evening daypart. LH-SCR-002359 is the weakest of the top five on audience fit at 48% and commuter index 0.51.

One caveat: slot availability was not checked, so all candidates were assumed available.

## Selected screens

```
     screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
DAT-SCR-001780              5           0.9220         47.51                36918.142224
ACS-SCR-001662              5           0.6769         27.95                28386.357653
DAT-SCR-002819              3           0.6583         35.82                36071.198768
 LH-SCR-002699              3           0.5685         44.14                45986.654387
DAT-SCR-002975              3           0.7382         31.43                25063.403962
 LH-SCR-004536              5           0.6367         54.69                47285.992451
DAT-SCR-003116              3           0.7524         39.66                28850.478427
DAT-SCR-001649              5           0.9208         58.48                34746.179008
 LH-SCR-002471              5           0.7908         62.22                42845.675207
 LH-SCR-003019              5           0.8081         67.52                45352.083383
DAT-SCR-002184              5           0.6775         42.96                34104.845712
 LH-SCR-003202              5           0.6524         56.33                46366.739840
ACS-SCR-001492              3           0.5334         26.93                26899.704575
ACS-SCR-001276              3           0.5004         23.17                24484.651597
 LH-SCR-002359              5           0.6485         53.65                43494.960133
 LH-SCR-002837              3           0.5534         45.08                42348.829712
DAT-SCR-002219              5           0.6148         41.97                35380.886092
DAT-SCR-002364              5           0.7765         56.17                36843.345986
 LH-SCR-002619              5           0.6887         56.59                41769.300181
 LH-SCR-004712              5           0.9166         56.72                31070.641583
DAT-SCR-001704              3           0.4948         33.59                33896.719327
DAT-SCR-002624              5           0.8667         42.86                24273.774182
ACS-SCR-001303              5           0.8675         41.97                23534.883881
DAT-SCR-002131              5           0.8927         45.37                24366.866734
```