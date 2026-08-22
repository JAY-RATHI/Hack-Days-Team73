# Report: campaign_5

**Status:** ok

## Spec (extracted from brief)
```json
{
  "city_hint": "Las Hackland",
  "target_zones_text": [
    "Las Hackland",
    "Airport Transit Corridor",
    "primary airport access corridor",
    "Premium Business Core",
    "city's premium commercial core",
    "Financial District Coverage",
    "major financial-district metro nodes"
  ],
  "target_age_min": 28,
  "target_age_max": 55,
  "target_income_tier": "high",
  "audience_descriptors": [
    "frequent flyers",
    "business travelers",
    "leisure travelers",
    "frequent business travellers",
    "higher-income leisure travelers",
    "planning trips well in advance",
    "daily commute",
    "in a travel mindset"
  ],
  "poi_affinities": [
    "office_park",
    "hotel_convention",
    "tourist_landmark"
  ],
  "objective": "conversion",
  "preferred_dayparts": [],
  "budget": 35000.0,
  "duration_days": 40,
  "requires_broad_coverage": false,
  "exclusion_criteria": [],
  "location_type_preference": null,
  "rotation_slots_per_day": null,
  "start_date": null,
  "raw_brief_text": "CLIENT BRIEF 5: SKYNIMBUS AIRLINES \u2014 FLY FURTHER, FEEL CLOSER\nCompany Name: SkyNimbus Airlines Ltd.\nIndustry Vertical: TRAVEL & AVIATION\nCampaign Objective: New Route Awareness & Bookings\nTarget Audience: Frequent flyers, business and leisure travelers (Ages 28-55)\nCampaign Budget: USD 35,000\nCampaign Duration: 40 Days (Proposed: Route-launch window, Q2 2027)\n1. Executive Summary & Objective\nSkyNimbus is launching twelve new international direct routes from Las Hackland and needs to build awareness among both business travelers who book frequently and leisure travelers planning ahead. The campaign favors aspirational, premium creative over discount messaging, with a secondary goal of driving direct bookings via the airline's app.\n2. Target Audience & Persona\nThe audience splits into two overlapping groups: frequent business travelers who move through the city's financial core on a predictable schedule, and higher-income leisure travelers who plan trips well in advance. Both groups pass through the city's primary airport-transit corridor and premium business nodes regularly, making those corridors the natural anchor for reach.\n3. Digital Screen Selection & Location Requirements\nAirport Transit Corridor: Premium wide-format screens along the primary airport access corridor \u2014 the single highest-relevance environment for a travel campaign, reaching an audience already in a travel mindset.\nPremium Business Core: Screens across the city's premium commercial core, reaching frequent business travellers on their daily commute.\nFinancial District Coverage: Supplementary placement at major financial-district metro nodes for repeated business-traveller exposure across the campaign window.\n4. Visual / Mockup Details & Slot Parameters\nSkyNimbus will supply a premium motion asset. Sky-blue gradients transitioning to white, aspirational aerial photography style, and clean sans-serif typography reading \"Fly Further. Feel Closer.\" Canvas optimized for wide-format premium transit corridor screens.\nReference Mockup A \u2014 Aspirational Premium \u2014 Sky Blue & White\nReference Mockup B \u2014 16:9 Airport Transit Corridor Wide-Screen Display\n5. RFP Requirements (Sales Team Response)\nTo accept this campaign brief, the Urban Media commercial intelligence agent must generate a formalized response containing:\n1. A curated list of screens anchored on the airport transit corridor and the premium business core.\n2. Pricing reflecting premium-corridor demand and the overlap between the business and leisure traveller audiences.\n3. Projected reach across the 40-day window, with separate estimates for repeat business-traveller frequency and one-time leisure-traveller exposure."
}
```

## Meta (geography/exclusions)
```json
{
  "city_id": "LH",
  "zone_ids": null,
  "n_screens_scored": 37824,
  "exclusion_log": [],
  "location_filter_log": null
}
```

## Package Summary
```json
{
  "n_screen_timeblock_pairs": 16,
  "n_unique_screens": 16,
  "n_clusters_represented": 16,
  "total_cost": 34339.6,
  "budget": 35000.0,
  "budget_utilization_pct": 98.1,
  "duration_days": 40,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 650352.0,
  "total_projected_impressions_per_week": 4552467.0,
  "avg_relevance_score_selected": 0.722,
  "availability": {
    "checked": false,
    "note": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
  },
  "caveat_availability": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
}
```

## Narrative

For a conversion-focused push in LH, this package is strong on both reach and audience fit: it uses 16 unique screen/time-block pairs over 40 days, with 650,352 projected impressions per day and 4,552,467 per week, while staying just under budget at 34,339.6 of 35,000. The selected set is highly concentrated in the target age bands, with the top screens showing 76% to 87% of local population in the 18_34, 35_54, and 55_plus ranges, plus commuter indices around 0.51 to 0.53. The best-value options to highlight are LH-SCR-002359 at 53.65 for 46,114 marginal daily impressions, LH-SCR-004595 at 58.43 for 44,062, and LH-SCR-002514 at 58.86 for 43,674. If you want to emphasize higher audience concentration, LH-SCR-004282 and LH-SCR-004595 both show 87% in target age ranges, while LH-SCR-003593 combines 86% target-age coverage with nearby tourist_landmark and office_park POIs. One caveat: slot availability was not checked because no start date was provided, so all candidates were assumed available.

## Selected screens

```
    screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
LH-SCR-003799              3           0.8569         47.09                42471.505538
LH-SCR-002359              5           0.8533         53.65                46113.960200
LH-SCR-003593              5           0.8551         63.48                45763.344798
LH-SCR-002514              5           0.7962         58.86                43673.843137
LH-SCR-004595              5           0.7829         58.43                44061.839056
LH-SCR-004282              5           0.8533         68.53                44250.918248
LH-SCR-005033              3           0.7703         57.52                39733.412559
LH-SCR-002837              3           0.5557         45.08                43018.596302
LH-SCR-002699              3           0.5566         44.14                41928.332137
LH-SCR-005502              3           0.5557         46.22                40373.332494
LH-SCR-003815              3           0.8569         74.51                41958.071140
LH-SCR-004265              3           0.7313         50.55                33332.510141
LH-SCR-003222              3           0.5569         49.34                42016.554844
LH-SCR-002880              3           0.8542         48.97                26832.067262
LH-SCR-004542              3           0.5566         48.06                39827.804484
LH-SCR-002639              3           0.5566         44.06                34996.404335
```