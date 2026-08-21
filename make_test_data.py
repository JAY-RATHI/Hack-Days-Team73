"""Generate tiny CSVs matching the REAL schema, to smoke-test the pipeline."""
import numpy as np, pandas as pd, os
from pathlib import Path
rng = np.random.default_rng(7)
D = Path("data/raw_test"); D.mkdir(parents=True, exist_ok=True)

pd.DataFrame({"city_id":["LH"],"city_name":["Las Hackland"],"population":[3200000],
 "transit_density":["dense"],"market_tier":["premium"],"timezone":["America/New_York"]}
).to_csv(D/"cities.csv",index=False)

zones=[f"LH-ZONE-{i:03d}" for i in range(1,6)]
pd.DataFrame({"zone_id":zones,"city_id":"LH","zone_name":[f"Zone {i}" for i in range(1,6)],
 "resident_population":rng.integers(50000,300000,5),"population_density_per_sqkm":rng.integers(2000,15000,5),
 "median_age":rng.uniform(30,45,5).round(1),"pct_age_under_18":rng.uniform(5,20,5).round(1),
 "pct_age_18_34":rng.uniform(20,40,5).round(1),"pct_age_35_54":rng.uniform(25,40,5).round(1),
 "pct_age_55_plus":rng.uniform(10,30,5).round(1),"median_household_income":rng.integers(60000,140000,5),
 "income_index":rng.uniform(70,145,5).round(1),"pct_bachelor_or_higher":rng.uniform(20,65,5).round(1),
 "dominant_occupation":rng.choice(["white_collar","blue_collar","mixed"],5),
 "daytime_population_multiplier":rng.uniform(1.1,3.4,5).round(2)}).to_csv(D/"zone_demographics.csv",index=False)

locs=[f"LH-LOC-{i:04d}" for i in range(1,41)]
pd.DataFrame({"location_id":locs,"city_id":"LH","name":[f"Stop {i}" for i in range(1,41)],
 "city_zone":"Z","zone_id":rng.choice(zones,40),
 "location_type":rng.choice(["bus_stop","metro_station"],40)}).to_csv(D/"locations.csv",index=False)

corridors=[f"LH-RT-B{i:03d}" for i in range(1,5)]
rs=[]
for ci,c in enumerate(corridors):
    stops=list(rng.choice(locs,12,replace=False))
    for d in ["outbound","inbound"]:
        seq=stops if d=="outbound" else stops[::-1]
        for i,l in enumerate(seq,1):
            rs.append({"route_id":f"{c}-{'OUT' if d=='outbound' else 'INB'}","corridor_id":c,
             "city_id":"LH","route_name":f"Route {ci+1}","mode":"bus","direction":d,
             "stop_sequence":i,"location_id":l,"is_first_stop":i==1,"is_last_stop":i==12,"num_stops":12})
pd.DataFrame(rs).to_csv(D/"route_stops.csv",index=False)

veh=[f"LH-VEH-{i:05d}" for i in range(1,13)]
pd.DataFrame({"vehicle_id":veh,"city_id":"LH","vehicle_type":"bus",
 "corridor_id":rng.choice(corridors,12),"screen_count":3}).to_csv(D/"vehicles.csv",index=False)

sch=[];sid=1
for c in corridors:
    for d in ["OUT","INB"]:
        for dt in ["weekday","weekend"]:
            for h in range(5,23):
                sch.append({"schedule_id":f"LH-SCH-{sid:06d}","route_id":f"{c}-{d}","corridor_id":c,
                 "direction":d,"day_type":dt,"start_time":f"{h:02d}:{rng.integers(0,59):02d}",
                 "estimated_ridership":int(rng.integers(10,120))});sid+=1
sched=pd.DataFrame(sch); sched.to_csv(D/"route_schedules.csv",index=False)

ra=[]
for s in sched.itertuples(index=False):
    for day in range(6):
        ra.append({"schedule_id":s.schedule_id,"route_id":s.route_id,"city_id":"LH",
         "date":f"2026-02-{19+day:02d}","day_of_week":"Thursday","is_holiday":False,
         "actual_ridership":int(max(1,rng.normal(s.estimated_ridership,8)))})
pd.DataFrame(ra).to_csv(D/"ridership_actuals.csv",index=False)

sc=[];n=1
for l in locs:                      # fixed screens
    for pos in ["top","left","right"]:
        sc.append({"screen_id":f"LH-SCR-{n:06d}","city_id":"LH","screen_type":"bus_stop",
         "location_id":l,"vehicle_id":None,"position":pos,
         "screen_size":rng.choice(["S","M","L"])});n+=1
for v in veh:                       # vehicle screens
    for pos in ["front","mid","rear"]:
        sc.append({"screen_id":f"LH-SCR-{n:06d}","city_id":"LH","screen_type":"bus_interior",
         "location_id":None,"vehicle_id":v,"position":pos,
         "screen_size":rng.choice(["S","M"])});n+=1
pd.DataFrame(sc).to_csv(D/"screens.csv",index=False)

ptypes=["shopping_mall","museum","hotel_convention","office_tower","hospital","university"]
po=[]
for i in range(1,61):
    po.append({"poi_id":f"LH-POI-{i:04d}","city_id":"LH","city_zone":"Z","name":f"POI {i}",
     "poi_type":rng.choice(ptypes),"scale":rng.choice(["flagship","neighborhood"]),
     "est_daily_footfall":int(rng.integers(300,30000)),"anchor_location_id":rng.choice(locs),
     "distance_to_location_km":round(float(rng.uniform(0.05,1.2)),3),
     "distance_to_location_mi":0.0,"is_network_hub":bool(rng.random()<0.15),
     "side_of_road":rng.choice(["near_side","far_side"]),
     "peak_daypart":rng.choice(["morning","midday","afternoon","evening","night"])})
pd.DataFrame(po).to_csv(D/"points_of_interest.csv",index=False)

pd.DataFrame({"event_id":["LH-EVT-1"],"city_id":["LH"],"city_zone":["Z"],"poi_id":["LH-POI-0001"],
 "anchor_location_id":[locs[0]],"event_name":["Test Fest"],"event_type":["festival"],
 "recurrence":["one_time"],"start_date":["2026-09-01"],"end_date":["2026-09-01"],
 "expected_attendance":[12000],"attendance_tier":["medium"],
 "primary_impact_daypart":["evening"],"impact_radius_km":[1.2]}).to_csv(D/"events.csv",index=False)

pd.DataFrame({"client_id":["CLI-00001"],"company_name":["Test Co"],"industry":["retail"],
 "client_tier":["local_business"],"home_city_id":["LH"],"active_cities":["LH"],
 "preferred_geographies":["LH:Zone 1"],"typical_campaign_budget":[50000.0],
 "budget_variance_pct":[0.3],"campaign_frequency":["seasonal"],"avg_campaign_duration_days":[30],
 "bundle_affinity":["single_screen"],"negotiation_leverage":["low"],
 "relationship_start_date":["2024-01-01"],"account_status":["active"]}).to_csv(D/"client_facts.csv",index=False)

pd.DataFrame({"time_block_id":[1,2,3,4,5,6],
 "time_block_label":["00:00-04:00","04:00-08:00","08:00-12:00","12:00-16:00","16:00-20:00","20:00-24:00"],
 "start_hour":[0,4,8,12,16,20],"end_hour":[4,8,12,16,20,24],
 "nearest_daypart":["night","morning","midday","afternoon","evening","night"]}).to_csv(D/"dim_slot.csv",index=False)

allsc=[s["screen_id"] for s in sc]
bk=[]
for i in range(1,201):
    bk.append({"booking_id":f"LH-BKG-{i:07d}","deal_id":f"DEAL-{i:06d}","client_id":"CLI-00001",
     "city_id":"LH","screen_id":rng.choice(allsc),"ad_type":"Test (Awareness)",
     "industry_vertical":"retail","campaign_objective":"awareness",
     "time_block_id":int(rng.integers(1,7)),"daypart":"evening",
     "slots_booked_per_day":int(rng.integers(1,4)),"rotation_type":"single_rotation",
     "start_date":"2026-03-01","end_date":"2026-03-27","duration_days":27,
     "booked_date":"2026-02-08","contracted_price_per_slot_per_day":round(float(rng.uniform(40,200)),2),
     "line_item_value":3000.0,"deal_total_value":3000.0,"is_bundle":False,"booking_status":"completed"})
pd.DataFrame(bk).to_csv(D/"bookings.csv",index=False)

ll=[]
for i in range(1,21):
    ll.append({"lead_id":f"LEAD-{i:06d}","client_id":"CLI-00001","company_name_raw":None,
     "industry_vertical":"retail","city_id":"LH","requested_geography":"LH:Zone 1",
     "anchor_screen_id":rng.choice(allsc),"lead_source":"referral","lead_date":"2026-05-01",
     "sales_stage_reached":"quote_sent","lost_date":"2026-05-20","requested_start_date":"2026-06-01",
     "requested_duration_days":30,"requested_num_screens":5,"indicated_budget":40000.0,
     "quoted_price_per_slot_per_day":90.0,"client_target_price_per_slot_per_day":70.0,
     "price_gap_pct":0.22,"negotiation_rounds":2,"competitor_mentioned":False,
     "loss_reason":"price_too_high","loss_reason_detail":"x","campaign_objective":"awareness",
     "ad_type":"Test (Awareness)"})
pd.DataFrame(ll).to_csv(D/"lost_leads.csv",index=False)
print("test CSVs written to", D)