"""
D5: Agentic Orchestration.

Single entry point: raw campaign brief (text or .docx) in -> complete
recommendation out -- screens, slots, pricing, projected impressions, and a
grounded explanatory narrative. This is what D6 actually calls; it should
never need to know about D2/D3/D4 individually.

=== PIPELINE ===
brief text/docx -> parse_brief (D2) -> build_scored_priced_screens (D2+D3)
                -> optimize_package (D4) -> generate_narrative (this file)

=== GROUNDING DISCIPLINE ===
The narrative LLM call is given a small, exact FACT SHEET built from the
actual computed numbers (top screens, prices, impressions, exclusions,
caveats) and instructed to reference ONLY those facts. This mirrors every
other grounding decision made across D1-D4 (rule-based text templates,
"never invent a number," dropping unmatched exclusion criteria rather than
guessing) -- the narrative step is the one place an LLM writes free-flowing
prose, so it's also the one place most likely to hallucinate if not
constrained tightly.

=== FEEDBACK LOOP ("Adapt") ===
A sales rep's follow-up note ("only metro, not bus") is parsed with the SAME
brief_parser schema (short text still extracts city/exclusion/audience
fields), then merged into the previous CampaignSpec: scalar fields are
overridden if the feedback states them, list fields (exclusion_criteria,
poi_affinities, etc.) are UNIONED rather than replaced, so an exclusion
stated in the original brief doesn't silently disappear because the
feedback didn't repeat it. The whole pipeline re-runs on the merged spec --
this is a full re-run, not an incremental patch, which is simpler and
correct even though it costs an extra LLM call.

HOW TO RUN (standalone test)
    python orchestration/agent_orchestrator.py
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.llm_client import chat_completion, CHAT_CAPABLE
from scoring.load_brief_docx import load_brief_text
from scoring.brief_parser import parse_brief
from pricing.merge_scored_priced import build_scored_priced_screens
from optimization.impressions_optimizer import optimize_package


def DB_PATH_FOR_ENRICH(conn):
    """Resolve the file path of an open sqlite3 connection (PRAGMA
    database_list), so enrichment always targets the SAME database the
    pipeline is reading -- critical when URBAN_DB points at a test db."""
    row = conn.execute("PRAGMA database_list").fetchone()
    return row[2] if row else "db/urban_media.db"

SCALAR_FEEDBACK_FIELDS = [
    "city_hint", "target_age_min", "target_age_max", "target_income_tier",
    "objective", "budget", "duration_days", "requires_broad_coverage",
    "location_type_preference", "rotation_slots_per_day", "start_date",
]
LIST_FEEDBACK_FIELDS = [
    "target_zones_text", "audience_descriptors", "poi_affinities",
    "preferred_dayparts", "exclusion_criteria",
]

TOP_N_FOR_NARRATIVE = 5

NARRATIVE_PROMPT = """You are writing a short recommendation summary for a
sales rep at a digital out-of-home advertising company, based ONLY on the
computed facts below. This goes directly to the rep -- be concrete and
concise, not generic.

RULES:
- Reference ONLY the numbers and screen details given below. Never invent a
  screen ID, price, statistic, or claim not present in the facts.
- If a caveat or exclusion-not-enforced note is present, mention it plainly
  -- don't hide limitations to sound more confident.
- 150-220 words. No headers, no bullet lists -- write it as a short brief a
  rep could read in 30 seconds before a client call.

FACTS:
{facts}
"""


def build_fact_sheet(spec, meta, package, summary):
    top = package.sort_values("marginal_daily_impressions", ascending=False).head(TOP_N_FOR_NARRATIVE)
    top_screens = [
        {
            "screen_id": r.screen_id,
            "time_block_id": r.time_block_id,
            "relevance_reason": r.relevance_reason,
            "price_target": round(r.price_target, 2),
            "marginal_daily_impressions": round(r.marginal_daily_impressions, 0),
        }
        for r in top.itertuples(index=False)
    ]
    return {
        "campaign_objective": spec.get("objective"),
        "city": meta.get("city_id"),
        "geography_note": meta.get("note"),
        "exclusion_log": meta.get("exclusion_log", []),
        "top_screens": top_screens,
        "package_summary": summary,
    }


def generate_narrative(spec, meta, package, summary):
    facts = build_fact_sheet(spec, meta, package, summary)
    text = chat_completion(
        messages=[{"role": "user", "content": NARRATIVE_PROMPT.format(facts=json.dumps(facts, indent=2, default=str))}],
        model=CHAT_CAPABLE,
        max_completion_tokens=500,
        temperature=0.3,  # some room for natural phrasing, but low --
                         # this still needs to stay close to the facts
    )
    return text


def run_campaign(conn, brief_text=None, brief_docx_path=None, spec=None, poi_vocab=None):
    """Main D5 entry point. Provide exactly one of brief_text / brief_docx_path
    / spec (spec lets the feedback loop re-run without re-parsing from raw
    text)."""
    if spec is None:
        if brief_docx_path:
            brief_text = load_brief_text(brief_docx_path)
        if not brief_text:
            raise ValueError("Provide brief_text, brief_docx_path, or spec")
        spec = parse_brief(brief_text, poi_vocab=poi_vocab)

    scored_priced, meta = build_scored_priced_screens(spec, conn)
    if scored_priced.empty:
        note = meta.get("note", "")
        if "exclu" in note.lower():
            message = f"All candidate screens were removed by exclusion criteria. {note}"
        else:
            message = f"No screens matched this campaign's geography. {note} Try broadening the target area."
        return {
            "status": "no_match", "spec": spec, "meta": meta,
            "package": None, "summary": None,
            "narrative": message,
        }

    package, summary = optimize_package(scored_priced, spec, conn)
    if package.empty:
        return {
            "status": "no_package", "spec": spec, "meta": meta,
            "package": None, "summary": summary,
            "narrative": ("Screens matched this campaign's audience, but none fit within "
                         f"the stated budget. {summary.get('note', '')}"),
        }

    # D1's "Leverage AI to infer profiles": polish the audience prose for
    # EXACTLY the screens in the final package (Layer 2 of the two-layer
    # design -- ~1 API call, cached forever via profile_source='llm').
    # Guarded so an LLM hiccup NEVER blocks the pipeline: the rule-based
    # Layer-1 text is always already in the table as a valid fallback.
    try:
        from features.enrich_profiles_llm import enrich
        for tb, grp in package.groupby("time_block_id"):
            enrich(grp.screen_id.unique().tolist(), time_block_id=int(tb),
                   db_path=getattr(conn, "_db_path", None) or DB_PATH_FOR_ENRICH(conn))
    except Exception as e:
        print(f"  (profile enrichment skipped: {type(e).__name__}: {e} -- "
              f"rule-based profile text remains in place)")

    narrative = generate_narrative(spec, meta, package, summary)
    return {
        "status": "ok", "spec": spec, "meta": meta,
        "package": package, "summary": summary, "narrative": narrative,
    }


def apply_feedback(conn, previous_spec, feedback_text, poi_vocab=None):
    """Re-run the pipeline with a sales rep's follow-up note merged in.
    Returns the same shape as run_campaign()."""
    feedback_spec = parse_brief(feedback_text, poi_vocab=poi_vocab)

    merged = dict(previous_spec)
    for key in SCALAR_FEEDBACK_FIELDS:
        if feedback_spec.get(key) is not None:
            merged[key] = feedback_spec[key]
    for key in LIST_FEEDBACK_FIELDS:
        if feedback_spec.get(key):
            # Union, preserving order, no duplicates -- feedback ADDS to the
            # original brief's constraints, it doesn't erase them.
            merged[key] = list(dict.fromkeys((previous_spec.get(key) or []) + feedback_spec[key]))

    merged["raw_brief_text"] = (previous_spec.get("raw_brief_text", "")
                                + f"\n\n[SALES REP FEEDBACK]: {feedback_text}")

    return run_campaign(conn, spec=merged, poi_vocab=poi_vocab)


if __name__ == "__main__":
    conn = sqlite3.connect(os.environ.get("URBAN_DB", "db/urban_media.db"))
    docx_path = sys.argv[1] if len(sys.argv) > 1 else "data/campaign_briefs/campaign_1.docx"

    print(f"Running full D5 pipeline on {docx_path}...\n")
    result = run_campaign(conn, brief_docx_path=docx_path)

    print(f"status: {result['status']}\n")
    if result["status"] == "ok":
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(json.dumps(result["summary"], indent=2, default=str))
        print("\n" + "=" * 70)
        print("NARRATIVE")
        print("=" * 70)
        print(result["narrative"])

        print("\n" + "=" * 70)
        print("Testing feedback loop: 'Only use metro platform screens, not buses'")
        print("=" * 70)
        result2 = apply_feedback(conn, result["spec"],
                                 "Only use metro platform screens, not buses")
        print(f"status: {result2['status']}")

        # DIAGNOSTIC: print exactly what changed in the spec/meta between the
        # two runs, so we can see WHY the package did or didn't change,
        # instead of guessing from the final numbers alone.
        print("\n--- DIAGNOSTIC: spec/meta comparison ---")
        print("ORIGINAL spec.location_type_preference:", result["spec"].get("location_type_preference"))
        print("ORIGINAL spec.exclusion_criteria:", result["spec"].get("exclusion_criteria"))
        print("ORIGINAL meta.n_screens_scored:", result["meta"].get("n_screens_scored"))
        print("ORIGINAL meta.location_filter_log:", result["meta"].get("location_filter_log"))
        print("ORIGINAL meta.exclusion_log:", result["meta"].get("exclusion_log"))
        print()
        print("FEEDBACK spec.location_type_preference:", result2["spec"].get("location_type_preference"))
        print("FEEDBACK spec.exclusion_criteria:", result2["spec"].get("exclusion_criteria"))
        print("FEEDBACK meta.n_screens_scored:", result2["meta"].get("n_screens_scored"))
        print("FEEDBACK meta.location_filter_log:", result2["meta"].get("location_filter_log"))
        print("FEEDBACK meta.exclusion_log:", result2["meta"].get("exclusion_log"))
        print("--- END DIAGNOSTIC ---\n")

        if result2["status"] == "ok":
            print(json.dumps(result2["summary"], indent=2, default=str))
            print("\n", result2["narrative"])
    else:
        print(result["narrative"])