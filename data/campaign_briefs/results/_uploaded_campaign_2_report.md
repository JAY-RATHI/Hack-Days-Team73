# Report: _uploaded_campaign_2

**Status:** ok

## Spec (extracted from brief)
```json
{
  "city_hint": null,
  "target_zones_text": [
    "Nightlife and Entertainment Corridors",
    "Campus-Edge Transit Nodes",
    "Event-Venue Precincts",
    "late-night entertainment districts",
    "exam-season late-study patterns",
    "major stadium and arena precincts",
    "event nights",
    "late evening through early morning"
  ],
  "target_age_min": 18,
  "target_age_max": 30,
  "target_income_tier": "value",
  "audience_descriptors": [
    "Gen Z",
    "young professionals",
    "gym-goers",
    "night-shift workers",
    "price-sensitive",
    "occasion-based messaging",
    "late-night audience",
    "students"
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
  "location_type_preference": "vehicle_only",
  "rotation_slots_per_day": null,
  "start_date": null,
  "raw_brief_text": "CLIENT BRIEF 2: EMBER ENERGY \u2014 IGNITE EVERY HOUR\nCompany Name: Ember Beverages LLC\nIndustry Vertical: FMCG / BEVERAGES (ENERGY DRINKS)\nCampaign Objective: Trial & Impulse Purchase\nTarget Audience: Gen Z and young professionals, gym-goers, night-shift workers (Ages 18-30)\nCampaign Budget: USD 12,000\nCampaign Duration: 21 Days (Proposed: Exam season / Fall semester)\n1. Executive Summary & Objective\nEmber Energy is a new zero-sugar energy drink entering a crowded category dominated by two legacy brands. Rather than compete on brand heritage, the campaign leans into moments of specific fatigue \u2014 late study sessions, night shifts, post-gym slumps \u2014 and positions Ember as the answer to that exact moment. Success is measured by trial at nearby retail points, not brand recall.\n2. Target Audience & Persona\nThe audience is young, price-sensitive, and highly responsive to occasion-based messaging rather than brand loyalty. They're out late \u2014 studying, working night shifts, or leaving the gym \u2014 and are more likely to try a new energy drink out of genuine tiredness than brand preference. They notice bold, high-contrast creative and respond to humor and directness over polish.\n3. Digital Screen Selection & Location Requirements\nNightlife and Entertainment Corridors: Bus rear screens on routes running through late-night entertainment districts, positioned to catch post-venue crowds heading home.\nCampus-Edge Transit Nodes: Screens at transit nodes serving large student populations, timed to exam-season late-study patterns.\nEvent-Venue Precincts: Digital boards near major stadium and arena precincts, where footfall spikes sharply on event nights.\nTime-of-Day Target: Heavy weighting on late evening through early morning rather than standard commute peaks.\n4. Visual / Mockup Details & Slot Parameters\nEmber will supply a dynamic motion graphic asset. Bold orange-to-red flame gradients against near-black backgrounds, high-contrast yellow callout text, and a QR code linking to a nearby-retailer locator. Because of the motion elements, the campaign is restricted to digital-only screens. Canvas: square format optimized for bus-rear and vertical poster placements.\nReference Mockup A \u2014 High-Energy \u2014 Flame Orange & Near-Black\nReference Mockup B \u2014 1:1 Square / Bus Rear-Screen or Vertical Poster\n5. RFP Requirements (Sales Team Response)\nTo accept this campaign brief, the Urban Media commercial intelligence agent must generate a formalized response containing:\n1. An inventory package combining bus-rear screens on nightlife corridors with campus-edge and event-venue digital boards.\n2. Dynamic pricing reflecting late-night demand patterns and event-night surge behaviour near major venues.\n3. A reach plan optimised for unique late-night impressions within the stated budget, prioritising frequency over broad daytime coverage."
}
```

## Meta (geography/exclusions)
```json
{
  "city_id": null,
  "zone_ids": null,
  "n_screens_scored": 15690,
  "exclusion_log": [],
  "location_filter_log": {
    "location_type_preference": "vehicle_only",
    "applied": true,
    "screens_removed": 51288
  }
}
```

## Package Summary
```json
{
  "n_screen_timeblock_pairs": 10,
  "n_unique_screens": 10,
  "n_clusters_represented": 10,
  "total_cost": 11815.02,
  "budget": 12000.0,
  "budget_utilization_pct": 98.5,
  "duration_days": 21,
  "cost_basis": "total_campaign",
  "total_projected_impressions_per_day": 96404.0,
  "total_projected_impressions_per_week": 674826.0,
  "avg_relevance_score_selected": 0.556,
  "availability": {
    "checked": false,
    "note": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
  },
  "caveat_availability": "Brief states no specific start date -- slot availability against existing bookings was NOT checked. All candidates assumed available."
}
```

## Narrative

For a conversion-focused buy, the strongest options are the evening time block 5 screens with the best mix of 18–34 concentration, commuter presence, and relevant nearby POIs. LH-SCR-001498 is the top pick: 32% of the local population is 18–34, commuter index is 0.52, it matches the requested evening daypart, and it has the highest marginal daily impressions at 12,844 for a price target of 73.19. LH-SCR-001163 is also strong with the highest 18–34 share at 34%, the same 0.52 commuter index, evening alignment, and 12,045 marginal daily impressions at 73.84. LH-SCR-001779 is similarly solid at 30% 18–34, 0.52 commuter index, and 12,084 impressions at 71.86, with the added stadium_arena POI. LH-SCR-001283 is slightly weaker on age mix at 29% and commuter index at 0.51, but still fits evening and delivers 11,929 impressions at 72.26.  

One lower-cost option, DAT-SCR-001267, is priced at 46.28 with 9,840 impressions and 32% 18–34, but it is outside the requested dayparts, so treat it as a caveated add-on rather than a core recommendation. The package is 10 screen-timeblock pairs across 10 unique screens, totals 11,815.02 against a 12,000 budget, and projects 96,404 impressions per day over 21 days. Availability was not checked, so assumed-open slots should be confirmed before promising inventory.

## Selected screens

```
     screen_id  time_block_id  relevance_score  price_target  marginal_daily_impressions
 LH-SCR-001498              5           0.6818         73.19                12843.783593
 LH-SCR-001283              5           0.6590         72.26                11928.643816
ACS-SCR-001156              3           0.6004         36.05                 6350.359071
DAT-SCR-001267              3           0.4916         46.28                 9839.881262
 LH-SCR-001163              5           0.5534         73.84                12045.255923
DAT-SCR-001403              3           0.5104         47.02                 8225.204081
 LH-SCR-001779              5           0.5232         71.86                12083.981982
ACS-SCR-001145              5           0.5107         41.66                 6982.972613
ACS-SCR-001180              5           0.5297         43.21                 6802.685847
DAT-SCR-001137              5           0.5027         57.25                 9300.915734
```