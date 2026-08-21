# Person A Runbook — D1 Audience Profile Engine

Everything runs from the **project root**. Dependencies: `pip install pandas anthropic`
(sqlalchemy no longer needed — we use stdlib `sqlite3`).

## Order of operations

```bash
# 0. put the 14 raw CSVs in data/raw/  (screens.csv, bookings.csv, ...)

python inspect_tables.py > inspect_report.txt   # DONE ✅

python db/load.py                    # ~1-3 min (2M-row table, chunked)
python features/screen_geo_map.py    # seconds  — resolves fixed vs vehicle screens
python features/route_cluster_map.py # seconds  — audience overlap clusters
python features/ridership_by_block.py# 10-60s   — collapses 2M rows to a lookup
python features/build_audience_profile.py  # 1-3 min — builds all ~67K profiles
python spot_check.py                 # READ THE OUTPUT, don't skip this
```

Then post `db/schema.md` + `docs/CONTRACTS.md` to the team. That unblocks B and C.

## What each step writes

| Step | Table produced |
|---|---|
| `db/load.py` | the 14 raw tables + indexes |
| `screen_geo_map.py` | `screen_geo_map` |
| `route_cluster_map.py` | `screen_cluster_map`, `corridor_overlap` |
| `ridership_by_block.py` | `corridor_timeblock_ridership` |
| `build_audience_profile.py` | `screen_audience_profile` ← **the handoff** |

Every script is idempotent (`if_exists="replace"`) — safe to re-run after a fix.

## Sanity checks that must pass before you hand off

- `load.py` prints no `<-- expected N` warnings (row counts are hardcoded from your real inspect output).
- `screen_geo_map.py` shows roughly **8,548 fixed / 2,615 vehicle**. A big deviation means the location/vehicle null logic is wrong.
- `route_cluster_map.py`: largest cluster is **tens, not thousands**. Thousands means the mega-cluster bug is back.
- `ridership_by_block.py`: block 1 (00:00–04:00) has the **lowest** riders; blocks 2/3/5 are highest. If not, the `start_time → hour // 4 + 1` bucketing is off.
- `spot_check.py`: work the 5-point checklist it prints. It already caught one real bug (low-confidence rows naming POIs they had no evidence for).

## Timing against the 24–36h clock

| Hours | Task |
|---|---|
| 0–1 | load + geo map + clusters + ridership (all fast) |
| 1–2 | **publish schema.md + CONTRACTS.md** — do not delay this, it's the unblock |
| 2 | Hour-2 sync: confirm the contract, raise the open questions |
| 2–4 | build profiles, spot-check, fix what the spot-check finds |
| 4+ | help D3 (hand them the pricing notes in CONTRACTS.md — saves them an hour) |
| last 3h | reserve for QA on B/C's edge cases. Don't disappear. |

## If something breaks

- **`sqlite3.InterfaceError: unsupported type`** → you're passing a numpy int/float as a query param. Wrap in `int()` / `str()`. (Already handled in `spot_check.py`.)
- **Empty query result where you expected rows** → same numpy-type cause; sqlite silently matches nothing instead of erroring.
- **All screens come out `low` confidence** → `corridor_timeblock_ridership` is probably empty or `corridor_ids` didn't resolve. Check `screen_geo_map.n_corridors` isn't 0 everywhere.
- **`build_audience_profile.py` slow or memory-heavy** → it caches zone blends and pre-aggregates POIs, so it shouldn't be. If it is, confirm `ridership_by_block.py` actually ran (otherwise it's hitting the 2M-row table per screen).
- **Claude enrichment fails** → by design it keeps the rule-based text and continues. Never blocks the pipeline.

## Two things to tell the team out loud

1. **`lost_leads` has no `lead_expiry_date`** — the problem statement is wrong about this. Whoever owns D3 needs to know before they design recency weighting.
2. **There are no coordinates in this dataset.** Anyone planning geospatial work should stop and read `db/schema.md` first — POI proximity is a pre-computed join.