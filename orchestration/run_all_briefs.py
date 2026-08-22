"""
Runs the full D2->D3->D4->D5 pipeline on EVERY .docx in data/campaign_briefs/,
not just one. Each brief may look completely different (we already learned
campaign_1.docx didn't match our synthetic test assumptions at all -- others
may too), so this:
  - handles each brief independently (one bad/unusual file doesn't kill the batch)
  - writes a readable per-brief report to data/campaign_briefs/results/
  - prints a compact comparison table at the end so you can spot outliers
    fast (e.g. a brief that scores 0 screens, or blows way past budget)

HOW TO RUN
    python orchestration/run_all_briefs.py
    (optionally: python orchestration/run_all_briefs.py path/to/other/folder)
"""
import json
import os
import sqlite3
import sys
import traceback
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from orchestration.agent_orchestrator import run_campaign
from orchestration.recommendation_report import (
    build_detailed_recommendation, render_markdown, flatten_for_csv)

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")
DEFAULT_BRIEFS_DIR = "data/campaign_briefs"


def run_one_brief(conn, docx_path):
    """Never raises -- always returns a result dict, even on total failure,
    so one broken file can't stop the batch."""
    try:
        result = run_campaign(conn, brief_docx_path=str(docx_path))
        result["error"] = None
        return result
    except Exception as e:
        return {
            "status": "error", "spec": None, "meta": None, "package": None,
            "summary": None, "narrative": None,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }


def write_report(docx_path, result, out_dir):
    name = Path(docx_path).stem
    out_path = out_dir / f"{name}_report.md"

    lines = [f"# Report: {name}", "", f"**Status:** {result['status']}", ""]

    if result["status"] == "error":
        lines += ["## Error", "```", result["error"], "", result.get("traceback", ""), "```"]
    else:
        lines += ["## Spec (extracted from brief)", "```json",
                  json.dumps(result["spec"], indent=2, default=str), "```", ""]
        lines += ["## Meta (geography/exclusions)", "```json",
                  json.dumps(result["meta"], indent=2, default=str), "```", ""]
        if result["summary"]:
            lines += ["## Package Summary", "```json",
                      json.dumps(result["summary"], indent=2, default=str), "```", ""]
        lines += ["## Narrative", "", result["narrative"] or "(none)", ""]
        if result["package"] is not None and not result["package"].empty:
            cols = result["package"][["screen_id", "time_block_id", "relevance_score",
                                      "price_target", "marginal_daily_impressions"]]
            try:
                table_text = cols.to_markdown(index=False)
            except ImportError:
                # `tabulate` isn't installed -- fall back to a plain text
                # table rather than crashing the whole batch over formatting.
                table_text = "```\n" + cols.to_string(index=False) + "\n```"
            lines += ["## Selected screens", "", table_text]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def main():
    briefs_dir = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRIEFS_DIR)
    docx_files = sorted(briefs_dir.glob("*.docx"))

    if not docx_files:
        print(f"No .docx files found in {briefs_dir}")
        return

    out_dir = briefs_dir / "results"
    out_dir.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    rows = []
    all_screen_rows = []

    print(f"Found {len(docx_files)} brief(s) in {briefs_dir}\n")

    for path in docx_files:
        print(f"--- Running {path.name} ---")
        result = run_one_brief(conn, path)
        report_path = write_report(path, result, out_dir)
        print(f"  status: {result['status']}  ->  debug report: {report_path}")

        # Detailed, client-facing recommendation: full per-screen breakdown
        # (where / when / price band / audience reached / why chosen).
        if result["status"] != "error":
            try:
                detail = build_detailed_recommendation(result, conn, path.stem)
                json_path = out_dir / f"{path.stem}_recommendation.json"
                json_path.write_text(json.dumps(detail, indent=2, default=str), encoding="utf-8")
                md_path = out_dir / f"{path.stem}_recommendation.md"
                md_path.write_text(render_markdown(detail), encoding="utf-8")
                all_screen_rows.extend(flatten_for_csv(detail))
                print(f"  detailed: {md_path.name} + {json_path.name} "
                      f"({len(detail.get('recommended_screens', []))} screens described)")
            except Exception as e:
                print(f"  !! detailed report failed: {type(e).__name__}: {e}")
                traceback.print_exc()

        row = {"file": path.name, "status": result["status"]}
        if result["status"] == "ok":
            s = result["summary"]
            row.update({
                "n_screens_scored": result["meta"].get("n_screens_scored"),
                "pairs_selected": s.get("n_screen_timeblock_pairs"),
                "total_cost": s.get("total_cost"),
                "budget": s.get("budget"),
                "budget_util_pct": s.get("budget_utilization_pct"),
                "impressions_per_week": s.get("total_projected_impressions_per_week"),
                "avg_relevance": s.get("avg_relevance_score_selected"),
            })
        elif result["status"] == "error":
            row["note"] = result["error"]
        else:
            row["note"] = result.get("narrative", "")[:80]
        rows.append(row)
        print()

    print("=" * 100)
    print("COMPARISON ACROSS ALL BRIEFS")
    print("=" * 100)
    import pandas as pd
    summary_df = pd.DataFrame(rows)
    print(summary_df.to_string(index=False))

    n_ok = (summary_df.status == "ok").sum()
    n_error = (summary_df.status == "error").sum()
    n_other = len(summary_df) - n_ok - n_error
    print(f"\n{n_ok} succeeded, {n_error} errored, {n_other} returned no_match/no_package")
    if n_error:
        print("\n*** Check the error reports above -- these need investigation, not just re-running. ***")

    summary_df.to_csv(out_dir / "_comparison.csv", index=False)
    print(f"\nFull comparison also saved to {out_dir / '_comparison.csv'}")

    if all_screen_rows:
        flat = pd.DataFrame(all_screen_rows)
        flat_path = out_dir / "all_campaigns_screens.csv"
        flat.to_csv(flat_path, index=False)
        print(f"Flat per-screen table across ALL briefs ({len(flat)} rows): {flat_path}")
        print(f"Per-brief detail: {out_dir}/<brief>_recommendation.md (readable) "
              f"and .json (structured)")


if __name__ == "__main__":
    main()