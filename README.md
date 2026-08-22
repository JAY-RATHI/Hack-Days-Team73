# AgentIQ — Urban Media Commercial Intelligence Platform

**Hack Days 2026: The AgentIQ Frontier — Team 73**

Turns a messy advertiser campaign brief (free text or .docx) into a complete,
budget-optimized recommendation: best-fit screens, right time slots, a
floor/target/cap price band per screen, de-duplicated projected reach, and a
grounded plain-English justification for every choice.

## The problem (from the brief)

Urban Media's 50 sales reps price 11,163 transit screens by spreadsheet and
gut feel — same screen quoted at different prices, no demand signal, no way
to match advertisers to the right inventory. This system replaces that with
a Sense → Plan → Adapt pipeline over the company's own 14-table dataset.

## Architecture at a glance

```
campaign brief (.docx / text)
        │
        ▼
 D2 brief parser (Azure OpenAI, temperature=0, vocab-constrained)
        │  CampaignSpec: audience, geography, budget, exclusions...
        ▼
 D2 relevance scorer  ──reads──  D1 screen_audience_profile (66,978 rows)
        │  hard filters (geography, exclusions, location type) + scored fit
        ▼
 D3 pricing merge     ──reads──  demand index + price bands (floor/target/cap)
        │  scored_priced_screens (per campaign)
        ▼
 D4 impressions optimizer — greedy joint selection, budget-constrained,
        │  audience-overlap de-duplication (cluster + corridor Jaccard)
        ▼
 D5 orchestrator — one call in, complete result out; grounded LLM narrative;
        │  feedback loop merges rep notes into the spec and re-runs
        ▼
 D6 Streamlit UI — upload/pick/paste a brief, see every filter and caveat,
    refine with feedback, export .md/.json recommendation
```

Full data contracts between every stage: `docs/CONTRACTS.md`.
Confirmed database schema + the four gotchas that shaped the design:
`db/schema.md`. C4 diagrams: `docs/c4_model.html` (open in a browser,
print to PDF).

## Setup (once)

```bash
pip install -r requirements.txt
```

1. Put the 14 raw CSVs in `data/raw/` (they are NOT in this repo — 2M-row
   ridership table exceeds GitHub limits; regenerate everything from CSVs).
2. Put campaign brief `.docx` files in `data/campaign_briefs/`.
3. Create `.env` in the project root (never commit it — already gitignored):
   ```
   AZURE_OPENAI_API_KEY=<key 1 from the team dashboard>
   ```
   Endpoint/API version are hardcoded team-wide defaults in
   `common/llm_client.py`; only the key is secret.

## Build the data layer (once per fresh clone, ~3–5 min total)

Run everything **from the project root**:

```bash
python db/load.py                          # 14 tables -> db/urban_media.db
python features/screen_geo_map.py          # fixed vs vehicle screen resolution
python features/route_cluster_map.py       # audience-overlap clusters
python features/ridership_by_block.py      # 2M rows -> corridor/timeblock lookup
python features/build_audience_profile.py  # 66,978 audience profiles (no LLM)
python pricing/demand_index.py             # demand scores w/ cold-start fallback
python pricing/price_bands.py              # floor/target/cap from real bookings
```

Verify (both should end with 0 FAILs):

```bash
python verify_pipeline.py           # 32 checks on the data layer
python verify_scoring_pricing.py    # 19 checks on scoring + pricing (uses LLM)
```

## Run it

**UI (D6):**
```bash
streamlit run app/app.py
```
(Binds to localhost only via `.streamlit/config.toml` — no firewall prompt.)

**Batch: every brief in data/campaign_briefs/ (D5):**
```bash
python orchestration/run_all_briefs.py
```
Writes per-brief detailed recommendations (`.md` + `.json`) and a flat
per-screen CSV across all campaigns to `data/campaign_briefs/results/`.

**Single brief from the command line:**
```bash
python orchestration/agent_orchestrator.py data/campaign_briefs/campaign_1.docx
```

## Validation status

- Data layer: 32/32 automated checks pass on the full real dataset, plus a
  manual spot-check protocol (`spot_check.py`) run against real screens.
- Scoring/pricing: 19/19 checks; `floor <= target <= cap` holds for every
  one of 66,978 rows; demand→price correlation positive.
- End-to-end: all 6 real campaign briefs succeed, 95–99.9% budget
  utilization across budgets from $9K to $40K, relevance varying 0.63–0.80.
- Feedback loop verified to genuinely change results (location filters,
  merged exclusions) and to *say so honestly* when a constraint turns out
  to be non-binding.

## Design decisions worth knowing (the honest ones)

- **Impressions are estimates.** Slot exposure uses a saturating curve (the
  deck's non-linearity nuance); attention factors by mount position are a
  documented judgment call — there is no dwell-time column in the data.
- **Reach is de-duplicated, not summed.** Screens sharing a stop/corridor
  share an audience; each report shows standalone vs marginal reach so the
  discount is visible, not hidden.
- **Nothing invents numbers.** No budget stated → optimizer runs
  unconstrained (top-30) and says so. No duration → costs reported per-day
  with an explicit caveat. Exclusion phrases with no matching rule are
  flagged "NOT enforced", never silently dropped.
- **Known limitation:** no slot-availability check against existing
  bookings (CampaignSpec has no start_date yet); block 1 (00:00–04:00) has
  no transit service in this dataset, so its profiles are POI-only by
  necessity.

## Repo map

```
app/            D6 Streamlit UI + backend adapter
common/         shared Azure OpenAI client (retry, deployments, .env)
db/             loader + confirmed schema docs (DB file itself gitignored)
features/       D1 audience profile engine
scoring/        D2 brief parser + relevance scorer + exclusions
pricing/        D3 demand index + price bands + D2/D3 merge
optimization/   D4 impressions optimizer
orchestration/  D5 orchestrator, feedback loop, batch runner, reports
docs/           CONTRACTS.md (data contracts), c4_model.html, demo script
verify_*.py     automated verification suites
```