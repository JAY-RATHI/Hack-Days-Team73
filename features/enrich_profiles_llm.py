"""
LAYER 2 (optional): polish profile_text with Claude, on demand only.

Layer 1 (build_audience_profile.py) already wrote a rule-based profile_text
for all ~67K rows. That text is accurate but reads like a database record.
This script rewrites it as fluent prose for a SPECIFIC set of screens --
normally the 20-40 screens D2 actually shortlisted for a campaign.

WHY ON-DEMAND, NOT UPFRONT
Enriching all 67K rows would take ~1,675 API calls. Enriching one campaign's
shortlist takes 1-2 calls. Results are cached in the same table with
profile_source='llm', so a screen is only ever paid for once.

USAGE
    # from the command line, for testing:
    python features/enrich_profiles_llm.py LH-SCR-000001 LH-SCR-000002

    # from Person B's code (this is the integration point):
    from features.enrich_profiles_llm import enrich
    enrich(shortlisted_screen_ids, time_block_id=5)

GROUNDING RULE
The prompt passes ONLY the feature_dict and forbids adding anything not in
it. If Claude invents "near a popular cafe" for a screen with no cafe in its
POI weights, that's a hallucinated justification in a sales proposal -- worse
than no text at all. Keep this constraint if you edit the prompt.
"""
import json
import os
import sqlite3
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.llm_client import chat_completion, clean_json_response, CHAT_CAPABLE

DB_PATH = os.environ.get("URBAN_DB", "db/urban_media.db")
# CHAT_CAPABLE (mini) -- this text goes directly in front of a sales rep on a
# small shortlist (~20-40 screens), so quality matters more than the cost
# difference vs. nano at this volume.
MODEL = CHAT_CAPABLE
BATCH_SIZE = 25

PROMPT = """You write one-sentence audience descriptions for digital advertising
screens, for a sales rep to show an advertiser.

Rules:
- Max 30 words each.
- Use ONLY the facts in the data below. Never add a landmark, business type,
  audience trait, or number that isn't there.
- If confidence is "low", say plainly that the estimate is based on area
  averages rather than screen-level data.
- Plain professional English. No marketing hype.

Return ONLY a JSON array, no other text:
[{"screen_id": "...", "time_block_id": 0, "profile_text": "...", "audience_tags": ["..."]}]

DATA:
%s
"""


def enrich(screen_ids, time_block_id=None, db_path=DB_PATH):
    """Rewrite profile_text via Claude for these screens. Skips already-enriched rows."""
    if not screen_ids:
        return 0
    conn = sqlite3.connect(db_path)

    q = ("SELECT screen_id, time_block_id, feature_dict, confidence "
         "FROM screen_audience_profile "
         f"WHERE screen_id IN ({','.join('?' * len(screen_ids))}) "
         "AND profile_source = 'rule'")
    params = list(screen_ids)
    if time_block_id is not None:
        q += " AND time_block_id = ?"
        params.append(time_block_id)

    rows = conn.execute(q, params).fetchall()
    if not rows:
        print("Nothing to enrich (already done, or no matching rows).")
        return 0

    updated = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        payload = [{"screen_id": r[0], "time_block_id": r[1],
                    "confidence": r[3], **json.loads(r[2])} for r in batch]
        try:
            text = chat_completion(
                messages=[{"role": "user", "content": PROMPT % json.dumps(payload, default=str)}],
                model=MODEL,
                max_completion_tokens=2000,
            )
            text = clean_json_response(text)
            items = json.loads(text)
        except Exception as e:
            # Layer 1 text is still in the table and still correct -- degrading
            # to it is fine. Never let a failed polish break the pipeline.
            print(f"!! batch {i} failed ({e}); keeping rule-based text")
            continue

        for it in items:
            conn.execute(
                "UPDATE screen_audience_profile "
                "SET profile_text = ?, audience_tags = ?, profile_source = 'llm' "
                "WHERE screen_id = ? AND time_block_id = ?",
                (it["profile_text"], json.dumps(it.get("audience_tags", [])),
                 it["screen_id"], it["time_block_id"]))
            updated += 1
        conn.commit()

    print(f"OK  enriched {updated} profile rows")
    return updated


if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        print(__doc__)
        print("Pass screen_ids as arguments.")
    else:
        enrich(ids)