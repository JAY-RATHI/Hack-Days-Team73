"""
app/backend_adapter.py
----------------------
The REAL backend behind the AgentIQ UI -- replaces mock_backend.py.

Person D built the UI against a mock with a simpler shape. Rather than
rewrite their UI from scratch, this adapter maps the real pipeline output
(orchestration.agent_orchestrator + recommendation_report) into a
UI-friendly dict, and adds the fields the mock didn't know existed:

  - status ("ok" / "no_match" / "no_package" / "error") -- the mock always
    succeeded; the real pipeline has honest failure modes the UI must show
  - three confidence tiers (high/medium/low), not two
  - price BANDS (floor/target/cap), not a single price
  - exclusion/location-filter logs and caveats -- the "trust" part of
    Explainability & Trust
  - the parsed spec, kept so the feedback loop re-runs against the merged
    spec (apply_feedback) instead of re-parsing the brief from scratch

USAGE (from the UI):
    from backend_adapter import run_recommendation, run_feedback

    result = run_recommendation(brief_text)          # pasted text
    result = run_recommendation(docx_path=path)      # uploaded/selected file
    result = run_feedback(result["spec"], "only metro screens")
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

# The app lives in app/, the pipeline lives at the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.agent_orchestrator import run_campaign, apply_feedback
from orchestration.recommendation_report import (
    build_detailed_recommendation, render_markdown)

DB_PATH = os.environ.get("URBAN_DB", str(PROJECT_ROOT / "db" / "urban_media.db"))


def _connect():
    return sqlite3.connect(DB_PATH)


def _to_ui_shape(result, conn, brief_name="campaign"):
    """Map a run_campaign() result into the dict the UI renders."""
    status = result.get("status", "error")
    spec = result.get("spec") or {}
    meta = result.get("meta") or {}
    summary = result.get("summary") or {}

    ui = {
        "status": status,
        "spec": spec,                       # needed for the feedback loop
        "narrative": result.get("narrative"),
        "campaign_summary": {
            "target_audience": ", ".join(spec.get("audience_descriptors") or [])[:60] or "—",
            "age_range": (f"{spec.get('target_age_min')}–{spec.get('target_age_max')}"
                          if spec.get("target_age_min") else "not stated"),
            "geography": meta.get("city_id") or "all cities (none named)",
            "objective": spec.get("objective") or "—",
            "budget": spec.get("budget"),
            "duration_days": spec.get("duration_days"),
        },
        "filters": {
            "exclusions": meta.get("exclusion_log") or [],
            "location_type": meta.get("location_filter_log"),
            "availability": summary.get("availability"),
            "candidates_scored": meta.get("n_screens_scored"),
        },
        "totals": None,
        "selected_screens": [],
        "caveats": [],
        "detail": None,      # full recommendation_report structure
        "detail_md": None,   # rendered markdown, for the download button
    }

    if status != "ok":
        return ui

    detail = build_detailed_recommendation(result, conn, brief_name)
    ui["detail"] = detail
    ui["detail_md"] = render_markdown(detail)
    ui["caveats"] = detail.get("caveats") or []

    screens = detail.get("recommended_screens", [])
    reach_before = sum(s["impressions"]["standalone_daily"] for s in screens)
    reach_after = sum(s["impressions"]["marginal_daily_after_overlap"] for s in screens)

    ui["totals"] = {
        "total_price": summary.get("total_cost"),
        "budget": summary.get("budget"),
        "budget_utilization_pct": summary.get("budget_utilization_pct"),
        "cost_basis": summary.get("cost_basis"),
        "impressions_per_day": summary.get("total_projected_impressions_per_day"),
        "impressions_per_week": summary.get("total_projected_impressions_per_week"),
        "reach_before_dedup": round(reach_before),
        "reach_after_dedup": round(reach_after),
        "n_screens": summary.get("n_unique_screens"),
        "n_clusters": summary.get("n_clusters_represented"),
        "avg_relevance": summary.get("avg_relevance_score_selected"),
    }

    for s in screens:
        ui["selected_screens"].append({
            "screen_id": s["screen_id"],
            "location": s["location"]["name"] or f"{s['screen']['kind']} screen",
            "location_type": s["location"]["location_type"],
            "city": s["location"]["city_name"],
            "zone": s["location"]["zone_name"],
            "market_tier": s["location"]["market_tier"],
            "routes": s["route"]["route_names"][:3],
            "time_block": (f"Block {s['time_slot']['time_block_id']} · "
                           f"{s['time_slot']['hours']} ({s['time_slot']['daypart']})"),
            "slots_per_day": s["time_slot"]["rotation_slots_per_day"],
            "slots_available": s["time_slot"].get("slots_available"),
            "price_floor": s["pricing"]["price_floor_per_slot_per_day"],
            "price_target": s["pricing"]["price_target_per_slot_per_day"],
            "price_cap": s["pricing"]["price_cap_per_slot_per_day"],
            "cost_for_campaign": s["pricing"]["cost_for_campaign"],
            "demand_basis": s["pricing"]["demand_basis"],
            "effective_impressions": s["impressions"]["marginal_daily_after_overlap"],
            "standalone_impressions": s["impressions"]["standalone_daily"],
            "weekly_impressions": s["impressions"]["marginal_weekly"],
            "reason": s["why_selected"]["reason"],
            "relevance_score": s["why_selected"]["relevance_score"],
            "confidence": s["audience"]["data_confidence"] or "unknown",
            "audience_profile": s["audience"]["profile"],
            "audience_tags": s["audience"]["tags"],
            "nearby_pois": s["audience"]["top_nearby_poi_types"],
            "cluster": s["why_selected"]["audience_cluster"],
        })

    return ui


def run_recommendation(brief_text=None, docx_path=None, brief_name="campaign"):
    """Fresh run from a pasted brief or a .docx path."""
    conn = _connect()
    try:
        result = run_campaign(conn, brief_text=brief_text, brief_docx_path=docx_path)
        return _to_ui_shape(result, conn, brief_name)
    except Exception as e:
        return {"status": "error", "spec": {}, "narrative": f"{type(e).__name__}: {e}",
                "campaign_summary": None, "filters": None, "totals": None,
                "selected_screens": [], "caveats": [], "detail": None, "detail_md": None}
    finally:
        conn.close()


def run_feedback(previous_spec, feedback_text, brief_name="campaign"):
    """Refine an existing recommendation with a rep's follow-up note.
    Uses apply_feedback so the merged spec UNIONS constraints (an exclusion
    from the original brief never silently disappears)."""
    conn = _connect()
    try:
        result = apply_feedback(conn, previous_spec, feedback_text)
        return _to_ui_shape(result, conn, brief_name)
    except Exception as e:
        return {"status": "error", "spec": previous_spec,
                "narrative": f"{type(e).__name__}: {e}",
                "campaign_summary": None, "filters": None, "totals": None,
                "selected_screens": [], "caveats": [], "detail": None, "detail_md": None}
    finally:
        conn.close()


def parse_only(brief_text=None, docx_path=None):
    """SENSE stage on its own: brief -> CampaignSpec, no scoring yet.
    Lets the UI show (and let the rep edit) what the LLM understood BEFORE
    committing to a full run."""
    try:
        from scoring.load_brief_docx import load_brief_text
        from scoring.brief_parser import parse_brief
        if docx_path:
            brief_text = load_brief_text(docx_path)
        if not brief_text:
            return {"status": "error", "error": "No brief provided", "spec": None}
        spec = parse_brief(brief_text)
        return {"status": "ok", "spec": spec, "error": None}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}", "spec": None}


def run_with_spec(spec, brief_name="campaign"):
    """PLAN/ACT stages: score -> price -> optimize -> narrate, from an
    already-parsed (possibly rep-edited) spec. Skips the parse entirely, so
    an edited spec is used EXACTLY as shown -- no LLM reinterpretation."""
    conn = _connect()
    try:
        result = run_campaign(conn, spec=spec)
        return _to_ui_shape(result, conn, brief_name)
    except Exception as e:
        return {"status": "error", "spec": spec, "narrative": f"{type(e).__name__}: {e}",
                "campaign_summary": None, "filters": None, "totals": None,
                "selected_screens": [], "caveats": [], "detail": None, "detail_md": None}
    finally:
        conn.close()


def compute_diff(prev_ui, new_ui):
    """What changed between two 'ok' results -- powers the feedback diff
    chips. Keys screens by (screen_id, time_block) so a screen moving to a
    different slot counts as a real change, not a no-op."""
    if not prev_ui or prev_ui.get("status") != "ok" or new_ui.get("status") != "ok":
        return None

    def keys(ui):
        return {(s["screen_id"], s["time_block"]) for s in ui["selected_screens"]}

    prev_k, new_k = keys(prev_ui), keys(new_ui)
    pt, nt = prev_ui["totals"], new_ui["totals"]
    return {
        "screens_added": sorted(k[0] for k in (new_k - prev_k)),
        "screens_removed": sorted(k[0] for k in (prev_k - new_k)),
        "n_unchanged": len(prev_k & new_k),
        "cost_delta": round((nt["total_price"] or 0) - (pt["total_price"] or 0), 2),
        "reach_delta": round((nt["reach_after_dedup"] or 0) - (pt["reach_after_dedup"] or 0)),
        "impressions_week_delta": round((nt["impressions_per_week"] or 0)
                                        - (pt["impressions_per_week"] or 0)),
    }


def list_available_briefs():
    """The .docx briefs sitting in data/campaign_briefs/, for the UI picker."""
    briefs_dir = PROJECT_ROOT / "data" / "campaign_briefs"
    if not briefs_dir.exists():
        return {}
    return {p.stem: str(p) for p in sorted(briefs_dir.glob("*.docx"))}