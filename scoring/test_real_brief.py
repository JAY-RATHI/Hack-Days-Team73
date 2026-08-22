"""
Full pipeline test against a REAL brief docx -- brief_parser.py needs your
Azure key for this (unlike relevance_scorer.py/exclusions, which are pure
logic and were already tested against a hand-built spec).

HOW TO RUN
    export URBAN_DB=db/urban_media.db
    export AZURE_OPENAI_API_KEY=...
    python scoring/test_real_brief.py data/campaign_briefs/campaign_1.docx
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scoring.load_brief_docx import load_brief_text
from scoring.brief_parser import parse_brief
from scoring.relevance_scorer import score_screens


def main():
    docx_path = sys.argv[1] if len(sys.argv) > 1 else "data/campaign_briefs/campaign_1.docx"
    db_path = os.environ.get("URBAN_DB", "db/urban_media.db")

    print(f"Loading brief text from {docx_path}...")
    text = load_brief_text(docx_path)
    print(f"  {len(text)} characters extracted\n")

    print("Parsing with brief_parser.py...")
    spec = parse_brief(text)
    print(json.dumps(spec, indent=2))

    print("\n" + "=" * 70)
    print("Checking the fields that matter most for THIS brief specifically:")
    print("=" * 70)
    checks = [
        ("city_hint resolved to Las Hackland", spec.get("city_hint") and
         "hackland" in spec["city_hint"].lower()),
        ("age range captured (28-50)", spec.get("target_age_min") == 28 and
         spec.get("target_age_max") == 50),
        ("budget captured ($40,000)", spec.get("budget") == 40000.0),
        ("duration captured (45 days)", spec.get("duration_days") == 45),
        ("exclusion_criteria is non-empty", bool(spec.get("exclusion_criteria"))),
        ("rotation_slots_per_day captured (1)", spec.get("rotation_slots_per_day") == 1),
    ]
    for label, ok in checks:
        print(f"  [{'OK' if ok else 'CHECK THIS'}] {label}")

    print("\n" + "=" * 70)
    print("Running score_screens with exclusions applied...")
    print("=" * 70)
    conn = sqlite3.connect(db_path)
    ranked, meta = score_screens(spec, conn)

    print(f"\nmeta: {json.dumps({k: v for k, v in meta.items() if k != 'exclusion_log'}, default=str)}")
    print("\nexclusion_log (THIS IS THE PART TO READ CAREFULLY):")
    for entry in meta.get("exclusion_log", []):
        if entry.get("enforced"):
            print(f"  ENFORCED: '{entry['criterion']}' -> removed {entry['screens_removed']} screens")
        else:
            print(f"  *** NOT ENFORCED *** (no matching rule): '{entry['criterion']}'")
            print(f"      -> add a rule to EXCLUSION_RULES in relevance_scorer.py for this phrase")

    if ranked.empty:
        print("\nNo screens survived -- geography or exclusions may be too restrictive.")
        return

    print(f"\nTop 5 of {len(ranked)} scored+excluded screens:")
    print(ranked.head(5)[["screen_id", "time_block_id", "relevance_score", "confidence"]]
          .to_string(index=False))
    print("\nTop reason:", ranked.iloc[0].reason)


if __name__ == "__main__":
    main()