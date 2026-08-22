"""
D3 STEP 5: merge D2 + D3 into scored_priced_screens -- the actual handoff to
Person C (and to D4/D5 for optimization and orchestration).

This is a PER-CAMPAIGN table, not a static one -- relevance_score depends on
the specific CampaignSpec, so this function is called fresh for each brief,
not run once like the D1/demand-index tables.

OUTPUT SHAPE (published to docs/CONTRACTS.md by hour 5):
    screen_id, time_block_id, relevance_score, relevance_reason,
    relevance_confidence, price_floor, price_target, price_cap,
    demand_score, demand_confidence, combined_rank

`combined_rank` sorts by relevance_score first (a perfectly-priced screen
nobody's audience matches is still useless), using price_target as a
tiebreaker only.

HOW TO RUN (standalone test against a sample brief)
    python pricing/merge_scored_priced.py
"""
import json
import os
import sqlite3
import sys
import pandas as pd

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")


def build_scored_priced_screens(spec, conn):
    from scoring.relevance_scorer import score_screens

    ranked, meta = score_screens(spec, conn)
    if ranked.empty:
        return ranked, meta

    prices = pd.read_sql("SELECT * FROM screen_price_bands", conn)

    merged = ranked.merge(
        prices, on=["screen_id", "time_block_id"], how="left",
        suffixes=("_relevance", "_demand"),
    )

    missing_price = merged.price_target.isna().sum()
    if missing_price:
        print(f"WARNING: {missing_price} screens matched D2 but have no price "
              f"band -- check that price_bands.py has been run.")

    merged = merged.rename(columns={
        "reason": "relevance_reason",
        "confidence_relevance": "relevance_confidence",
        "confidence_demand": "demand_confidence",
    })

    merged = merged.sort_values(
        ["relevance_score", "price_target"], ascending=[False, True]
    ).reset_index(drop=True)
    merged["combined_rank"] = merged.index + 1

    cols = ["combined_rank", "screen_id", "time_block_id", "relevance_score",
            "relevance_reason", "relevance_confidence", "price_floor",
            "price_target", "price_cap", "demand_score", "demand_confidence"]
    return merged[cols], meta


if __name__ == "__main__":
    sys.path.insert(0, os.getcwd())
    from sample_campaign_briefs import SAMPLE_BRIEFS
    from scoring.brief_parser import parse_brief

    conn = sqlite3.connect(DB_PATH)

    for b in SAMPLE_BRIEFS:
        print(f"\n{'=' * 70}\n{b['id']}\n{'=' * 70}")
        spec = parse_brief(b["text"])
        result, meta = build_scored_priced_screens(spec, conn)
        print("meta:", meta)
        if result.empty:
            print("No screens matched -- check geography resolution.")
            continue
        print(f"\nTop 5 of {len(result)} scored+priced screens:")
        print(result.head(5)[["combined_rank", "screen_id", "time_block_id",
                              "relevance_score", "price_target", "demand_score"]]
              .to_string(index=False))
        print("\nTop reason:", result.iloc[0].relevance_reason)