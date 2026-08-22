"""
app.py
-------
The AgentIQ sales-rep UI (D6).

Run from the PROJECT ROOT:
    streamlit run app/app.py

ADAPTED FROM PERSON D's MOCK-BACKED VERSION. Structure and card layout kept;
what changed and why:
  - BACKEND SWAP done: mock_backend -> backend_adapter (real pipeline).
  - Brief input now has three paths: pick a real .docx from
    data/campaign_briefs/, upload a .docx, or paste text. (The deck's D6
    description explicitly says reps "upload relevant campaign documents".)
  - status handling added: the real pipeline can return no_match /
    no_package / error -- the mock always succeeded. Each failure state
    shows the pipeline's own honest explanation instead of a blank screen.
  - Three confidence tiers (high/medium/low), matching the real data
    contract -- the mock only had two.
  - Price is a BAND (floor/target/cap), not a single number -- that's what
    D3 actually produces and what a rep negotiates with.
  - Exclusion/location-filter logs and caveats are shown -- if a client's
    stated exclusion was NOT enforced, the rep must see that here, not
    discover it in front of the client.
  - Feedback loop uses apply_feedback with the stored spec (constraints
    UNION rather than replace), not a fresh re-parse of brief+feedback text.
  - Download buttons for the full recommendation (.md and .json).
"""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ---- BACKEND SWAP -----------------------------------------------------------
from backend_adapter import (run_recommendation, run_feedback,
                             list_available_briefs)
# -----------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sample_campaign_briefs import SAMPLE_BRIEFS as SAMPLE_BRIEF_LIST

SAMPLE_BRIEFS = {b["id"]: b["text"] for b in SAMPLE_BRIEF_LIST}

# --- Page config -------------------------------------------------------------
st.set_page_config(page_title="AgentIQ", layout="wide")

# Accordion brand palette (Citron accent on gray scale; Messina Sans isn't a
# web font, so the system sans stack stands in -- flagged per brand skill).
st.markdown("""
<style>
  h1, h2, h3 { color: #1F242F; }
  .stApp { color: #525965; }
  div[data-testid="stMetricValue"] { color: #1F242F; }
  .stButton > button[kind="primary"] {
      background-color: #EEFB87; color: #1F242F; border: none; border-radius: 0;
  }
  div[data-testid="stContainer"] { border-radius: 0; }
</style>
""", unsafe_allow_html=True)

st.title("AgentIQ — campaign recommendation engine")
st.caption("Turn a messy campaign brief into the right screens, slots, pricing "
           "and projected reach — with the reasoning behind every choice.")


CONFIDENCE_BADGE = {
    "high": "🟢 High confidence",
    "medium": "🟡 Medium confidence (partial data)",
    "low": "🔴 Low confidence (zone averages only)",
}


# --- Brief input: pick a real .docx, upload one, or paste text ----------------
tab_pick, tab_upload, tab_paste = st.tabs(
    ["📁 Pick a brief", "⬆️ Upload .docx", "✏️ Paste text"])

brief_text, docx_path, brief_name = None, None, "campaign"

with tab_pick:
    available = list_available_briefs()
    if available:
        chosen = st.selectbox("Campaign briefs in data/campaign_briefs/",
                              list(available))
        docx_path = available[chosen]
        brief_name = chosen
    else:
        st.caption("No .docx files found in data/campaign_briefs/.")

with tab_upload:
    uploaded = st.file_uploader("Upload a campaign brief", type=["docx"])
    if uploaded is not None:
        tmp = Path("data/campaign_briefs") / f"_uploaded_{uploaded.name}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(uploaded.getvalue())
        docx_path = str(tmp)
        brief_name = Path(uploaded.name).stem

with tab_paste:
    preset = st.selectbox("Or start from a sample",
                          ["(write your own)"] + list(SAMPLE_BRIEFS))
    default = SAMPLE_BRIEFS.get(preset, "")
    pasted = st.text_area("Campaign brief", value=default, height=140,
                          placeholder="Paste the advertiser's request here...")
    if pasted.strip():
        brief_text = pasted
        brief_name = preset if preset in SAMPLE_BRIEFS else "pasted_brief"

if st.button("Get recommendation", type="primary"):
    if brief_text or docx_path:
        with st.spinner("Parsing brief → scoring screens → pricing → optimizing package..."):
            # Pasted text wins if both are present (it's the visible tab's input)
            if brief_text:
                st.session_state["result"] = run_recommendation(
                    brief_text=brief_text, brief_name=brief_name)
            else:
                st.session_state["result"] = run_recommendation(
                    docx_path=docx_path, brief_name=brief_name)
            st.session_state["brief_name"] = brief_name
    else:
        st.warning("Pick, upload, or paste a campaign brief first.")


# --- Everything below only shows once we have a result -----------------------
if "result" in st.session_state:
    r = st.session_state["result"]

    # --- Honest failure states (the mock never had these) ---
    if r["status"] == "error":
        st.error(f"Pipeline error: {r['narrative']}")
        st.stop()
    if r["status"] in ("no_match", "no_package"):
        st.warning(r["narrative"])
        if r.get("filters"):
            with st.expander("What was filtered, and why"):
                st.json(r["filters"])
        st.stop()

    # --- Campaign summary bar ---
    cs = r["campaign_summary"]
    st.subheader("Campaign")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Objective", cs["objective"])
    c2.metric("Age range", cs["age_range"])
    c3.metric("Geography", cs["geography"])
    c4.metric("Budget", f"${cs['budget']:,.0f}" if cs["budget"] else "not stated")
    c5.metric("Duration", f"{cs['duration_days']} days" if cs["duration_days"]
              else "not stated")

    # --- Caveats first: if something couldn't be honored, the rep sees it
    # before the numbers, not after ---
    for caveat in r["caveats"]:
        st.warning(f"⚠️ {caveat}")

    # --- Filters applied (exclusions + location type) ---
    f = r["filters"]
    with st.expander(f"Filters applied · {f['candidates_scored']:,} candidate "
                     f"screen/slot pairs scored", expanded=bool(
                         f["exclusions"] or f["location_type"])):
        if not f["exclusions"] and not f["location_type"]:
            st.caption("No exclusions or location-type constraints in this brief.")
        for e in f["exclusions"]:
            if e.get("enforced") and e.get("screens_removed", 0) > 0:
                st.markdown(f"✅ **Enforced:** {e['criterion']} — removed "
                            f"{e['screens_removed']:,} screens")
            elif e.get("enforced"):
                st.markdown(f"✅ **Enforced (nothing left to remove):** {e['criterion']}")
            else:
                st.markdown(f"❌ **NOT enforced** — {e['criterion']} — "
                            f"{e.get('note', 'no matching rule')}")
        lt = f["location_type"]
        if lt:
            if lt.get("applied"):
                st.markdown(f"✅ **Location type:** {lt['location_type_preference']} — "
                            f"removed {lt['screens_removed']:,} screens")
            else:
                st.markdown(f"❌ **Location type NOT applied:** {lt.get('warning', '')}")

    # --- Totals + the route-overlap dedup showcase (kept from Person D) ---
    t = r["totals"]
    st.subheader("Package summary")
    c1, c2, c3, c4 = st.columns(4)
    budget_delta = (f"{t['budget_utilization_pct']}% of budget"
                    if t["budget_utilization_pct"] is not None else t["cost_basis"])
    c1.metric("Total price", f"${t['total_price']:,.2f}", delta=budget_delta,
              delta_color="off")
    c2.metric("Impressions / week", f"{t['impressions_per_week']:,.0f}")
    c3.metric("Reach after overlap dedup", f"{t['reach_after_dedup']:,}",
              delta=f"−{t['reach_before_dedup'] - t['reach_after_dedup']:,} de-duplicated",
              delta_color="off")
    c4.metric("Screens / clusters", f"{t['n_screens']} / {t['n_clusters']}")
    st.caption("Screens sharing a stop or corridor reach the same commuters — "
               "reach is de-duplicated so it isn't double-counted.")

    # --- Agent narrative ---
    st.info(f"**Agent summary:** {r['narrative']}")

    # --- Recommendation cards (the explainability core, kept from Person D) ---
    st.subheader("Recommended screens")
    for s in r["selected_screens"]:
        with st.container(border=True):
            top = st.columns([3, 1, 1, 1])
            top[0].markdown(f"### {s['location']}")
            top[0].caption(
                f"{s['screen_id']} · {s['location_type']} · {s['zone']}, "
                f"{s['city']} [{s['market_tier']}] · {s['time_block']}")
            top[1].metric("Price target", f"${s['price_target']:,.2f}",
                          delta=f"floor ${s['price_floor']:,.2f} · cap ${s['price_cap']:,.2f}",
                          delta_color="off")
            top[2].metric("Reach / day", f"{s['effective_impressions']:,.0f}")
            top[3].metric("Campaign cost", f"${s['cost_for_campaign']:,.0f}")

            # The "why" stays the hero of the card:
            st.markdown(f"**Why this screen:** {s['reason']}")
            st.caption(f"**Who's there:** {s['audience_profile']}")

            tags = st.columns([1, 1, 2, 2])
            tags[0].caption(f"Relevance: {s['relevance_score']:.0%}")
            tags[1].caption(CONFIDENCE_BADGE.get(s["confidence"],
                                                 f"⚪ {s['confidence']}"))
            tags[2].caption(f"Pricing basis: {s['demand_basis']}")
            if s["standalone_impressions"] > s["effective_impressions"]:
                overlap = s["standalone_impressions"] - s["effective_impressions"]
                tags[3].caption(f"Overlap discount: −{overlap:,.0f}/day "
                                f"(shares audience: {s['cluster']})")

    # --- Downloads: the full detailed recommendation ---
    st.subheader("Export")
    d1, d2 = st.columns(2)
    d1.download_button("Download recommendation (.md)", r["detail_md"] or "",
                       file_name=f"{st.session_state['brief_name']}_recommendation.md")
    d2.download_button("Download recommendation (.json)",
                       json.dumps(r["detail"], indent=2, default=str),
                       file_name=f"{st.session_state['brief_name']}_recommendation.json")

    # --- Feedback / adapt loop (now uses apply_feedback + stored spec) ---
    st.subheader("Refine")
    fb = st.text_input("Tell the agent what to change",
                       placeholder="e.g. 'only metro platform screens' or "
                                   "'exclude value-tier inventory'")
    if st.button("Regenerate with feedback"):
        if fb.strip():
            with st.spinner("Merging feedback into the spec and re-running..."):
                st.session_state["result"] = run_feedback(
                    r["spec"], fb, brief_name=st.session_state["brief_name"])
            st.rerun()
        else:
            st.warning("Type what you'd like changed first.")