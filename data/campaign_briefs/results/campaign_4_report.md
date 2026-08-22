# Report: campaign_4

**Status:** ok

## Spec (extracted from brief)
```json
{
  "city_hint": "Las Hackland",
  "target_zones_text": [
    "Las Hackland's business district",
    "business-park food court",
    "surrounding commercial district"
  ],
  "target_age_min": 18,
  "target_age_max": 35,
  "target_income_tier": null,
  "audience_descriptors": [
    "office workers",
    "students",
    "health-conscious",
    "lunch-hour footfall",
    "short lunch window",
    "highly local"
  ],
  "poi_affinities": [
    "office_park",
    "grocery_anchor",
    "entertainment_district"
  ],
  "objective": "frequency",
  "preferred_dayparts": [
    "midday"
  ],
  "budget": 9000.0,
  "duration_days": 15,
  "requires_broad_coverage": false,
  "exclusion_criteria": [
    "Exclude all nodes outside a realistic walking distance of the outlet."
  ],
  "location_type_preference": null,
  "rotation_slots_per_day": null,
  "raw_brief_text": "CLIENT BRIEF 4: BASIL & BLOOM \u2014 FRESH, FAST, FLAVORFUL\nCompany Name: Basil & Bloom Fast-Casual Kitchens\nIndustry Vertical: FOOD & BEVERAGE / QSR\nCampaign Objective: Lunch-Hour Footfall & Local Recall\nTarget Audience: Office workers and students (Ages 18-35)\nCampaign Budget: USD 9,000\nCampaign Duration: 15 Days (Proposed: New-outlet launch window)\n1. Executive Summary & Objective\nBasil & Bloom is a fast-casual salad-and-bowl chain opening its first location in Las Hackland's business district. The campaign objective is driving trial during the two-week launch window, with success measured by lunch-hour footfall at the new outlet rather than broad brand awareness.\n2. Target Audience & Persona\nThe target customer is a health-conscious office worker or student with a short lunch window who defaults to familiar options unless given a specific reason to try something new. They are highly local \u2014 the campaign only needs to reach people within a short walk of the new outlet \u2014 and respond well to limited-time offers and \"just opened\" messaging.\n3. Digital Screen Selection & Location Requirements\nImmediate Walking Radius of the New Outlet: Screens within a short walking distance of a single new outlet located in a business-park food court \u2014 the campaign's entire reach requirement sits inside that radius.\nMidday Commercial-District Coverage: Screens in the surrounding commercial district, weighted specifically to the lunch window.\nExclusion Criteria: Exclude all nodes outside a realistic walking distance of the outlet. Reach beyond that radius is wasted spend for a single-location launch.\n4. Visual / Mockup Details & Slot Parameters\nBasil & Bloom will supply a bright static visual \u2014 vibrant green and warm yellow tones, appetizing product photography, and legible large-format copy: \"Fresh. Fast. Flavorful.\" with a \"10% Off First Order\" offer. Canvas optimized for wide-format screens visible from a distance in food-court and plaza settings.\nReference Mockup A \u2014 Fresh & Appetizing \u2014 Vibrant Green & Warm Yellow\nReference Mockup B \u2014 16:9 Food-Court / Plaza Wide-Screen Display\n5. RFP Requirements (Sales Team Response)\nTo accept this campaign brief, the Urban Media commercial intelligence agent must generate a formalized response containing:\n1. A tightly-scoped inventory list limited to screens within realistic walking distance of the single new outlet.\n2. Pricing reflecting the hyper-local, midday-weighted delivery pattern.\n3. A footfall-conversion-oriented reach estimate for the 15-day launch window, explicitly stating the walking-radius logic behind screen selection."
}
```

## Meta (geography/exclusions)
```json
{
  "city_id": "LH",
  "zone_ids": null,
  "n_screens_scored": 37824,
  "exclusion_log": [
    {
      "criterion": "Exclude all nodes outside a realistic walking distance of the outlet.",
      "enforced": false,
      "note": "no matching rule -- NOT applied, flag to team"
    }
  ],
  "location_filter_log": null
}
```

## Package Summary
```json
{
  "n_screen_timeblock_pairs": 12,
  "n_unique_screens": 12,
  "n_clusters_represented": 12,
  "total_cost": 8562.75,
  "budget": 9000.0,
  "budget_utilization_pct": 95.1,
  "duration_days": 15,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 462644.0,
  "total_projected_impressions_per_week": 3238505.0,
  "avg_relevance_score_selected": 0.857
}
```

## Narrative

For a frequency-led buy in LH, this package is a strong fit: 12 unique screens across 12 clusters for 15 days, using 95.1% of the $9,000 budget at a total cost of $8,562.75. The plan is delivering 462,644 projected impressions per day, or 3,238,505 per week, with an average relevance score of 0.857.

The strongest individual options are all midday placements (time block 3). LH-SCR-003222 is the top pick at $49.34 with 45,017 marginal daily impressions, and it hits 85% of the local population in the 18_34 and 35_54 ranges, plus nearby entertainment district POIs. LH-SCR-002837 is nearly as strong at $45.08 and 44,503 impressions, with the same 85% age fit and both grocery anchor and entertainment district POIs. LH-SCR-002699 is the cheapest of the top five at $44.14 and still delivers 42,922 impressions with the same 85% age fit.

One caveat: the walking-distance exclusion for nodes outside a realistic distance of the outlet was not enforced, so flag that to the team before finalizing.

## Selected screens

```
    screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
LH-SCR-002837              3           0.9157         45.08                44502.763464
LH-SCR-003222              3           0.8832         49.34                45016.933459
LH-SCR-002699              3           0.8062         44.14                42921.643872
LH-SCR-004542              3           0.8575         48.06                40771.353239
LH-SCR-005502              3           0.8043         46.22                41675.698058
LH-SCR-002639              3           0.8467         44.06                34996.404335
LH-SCR-005279              3           0.8746         47.81                35792.805959
LH-SCR-005373              3           0.9014         50.85                36080.133183
LH-SCR-003640              3           0.8958         52.75                36829.655701
LH-SCR-004449              3           0.8702         48.49                34359.963807
LH-SCR-002489              3           0.9181         49.56                32702.504807
LH-SCR-002375              3           0.7072         44.49                36993.677809
```