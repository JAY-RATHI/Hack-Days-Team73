"""
app.py — the AgentIQ sales-rep UI (D6).

Run from the PROJECT ROOT:
    streamlit run app/app.py

Flow (mirrors the PS's own Sense -> Plan -> Adapt framing, with REAL stage
boundaries, not cosmetic ones):
  SENSE  — parse_only(): brief -> CampaignSpec. Shown to the rep in an
           EDITABLE panel before anything runs -- if the LLM misread the
           budget or city, the rep fixes it here instead of fighting prose.
  PLAN   — run_with_spec(): score -> price -> optimize, from the spec
           exactly as displayed (no LLM reinterpretation of edits).
  ADAPT  — free-text feedback merges into the spec (union semantics) and
           re-runs; a diff panel shows exactly what changed.
"""

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend_adapter import (run_feedback, run_with_spec, parse_only,
                             compute_diff, list_available_briefs)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sample_campaign_briefs import SAMPLE_BRIEFS as SAMPLE_BRIEF_LIST

SAMPLE_BRIEFS = {b["id"]: b["text"] for b in SAMPLE_BRIEF_LIST}

st.set_page_config(page_title="AgentIQ", layout="wide")

# Accordion palette (Citron on grays; Messina Sans isn't a web font -- system
# sans stands in, flagged per brand skill).
st.markdown("""
<style>
  h1, h2, h3 { color: #1F242F; }
  .stApp { color: #525965; }
  div[data-testid="stMetricValue"] { color: #1F242F; }
  .stButton > button[kind="primary"] {
      background-color: #EEFB87; color: #1F242F; border: none; border-radius: 0;
  }
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
LOCATION_TYPE_OPTIONS = {None: "(no restriction)", "metro_only": "Metro platforms only",
                         "fixed_only": "Fixed screens only", "vehicle_only": "Vehicle screens only"}


# ------------------------------------------------------------ brief intake
tab_pick, tab_upload, tab_paste = st.tabs(
    ["📁 Pick a brief", "⬆️ Upload .docx", "✏️ Paste text"])

brief_text, docx_path, brief_name = None, None, "campaign"

with tab_pick:
    available = list_available_briefs()
    if available:
        chosen = st.selectbox("Campaign briefs in data/campaign_briefs/", list(available))
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
    preset = st.selectbox("Or start from a sample", ["(write your own)"] + list(SAMPLE_BRIEFS))
    default = SAMPLE_BRIEFS.get(preset, "")
    pasted = st.text_area("Campaign brief", value=default, height=140,
                          placeholder="Paste the advertiser's request here...")
    if pasted.strip():
        brief_text = pasted
        brief_name = preset if preset in SAMPLE_BRIEFS else "pasted_brief"


# ------------------------------------------------- SENSE: parse (stage 1)
if st.button("1 · Read the brief  (Sense)", type="primary"):
    if brief_text or docx_path:
        with st.status("**Sense** — extracting a structured campaign spec from the brief...",
                       expanded=False) as status:
            parsed = (parse_only(brief_text=brief_text) if brief_text
                      else parse_only(docx_path=docx_path))
            if parsed["status"] == "ok":
                st.session_state["spec"] = parsed["spec"]
                st.session_state["brief_name"] = brief_name
                st.session_state.pop("result", None)
                st.session_state.pop("prev_result", None)
                st.session_state.pop("last_diff", None)
                status.update(label="**Sense** — brief understood. Review below, then run.",
                              state="complete")
            else:
                status.update(label="Brief parsing failed", state="error")
                st.error(parsed["error"])
    else:
        st.warning("Pick, upload, or paste a campaign brief first.")


# ---------------------------------- editable spec panel + PLAN (stage 2)
if "spec" in st.session_state:
    spec = st.session_state["spec"]
    st.subheader("What the agent understood — correct anything before running")
    with st.expander("Extracted campaign details (editable)", expanded="result" not in st.session_state):
        c1, c2, c3 = st.columns(3)
        budget_val = c1.number_input("Budget ($, 0 = not stated)",
                                     value=float(spec.get("budget") or 0), min_value=0.0, step=1000.0)
        duration_val = c2.number_input("Duration (days, 0 = not stated)",
                                       value=int(spec.get("duration_days") or 0), min_value=0, step=1)
        slots_val = c3.number_input("Rotation slots/day",
                                    value=int(spec.get("rotation_slots_per_day") or 1),
                                    min_value=1, max_value=6)

        c4, c5, c6 = st.columns(3)
        city_val = c4.text_input("City (blank = all cities)", value=spec.get("city_hint") or "")
        start_raw = spec.get("start_date")
        use_date = c5.checkbox("Campaign start date known", value=bool(start_raw))
        date_val = c5.date_input("Start date",
                                 value=date.fromisoformat(start_raw) if start_raw else date.today(),
                                 disabled=not use_date)
        lt_keys = list(LOCATION_TYPE_OPTIONS)
        lt_val = c6.selectbox("Screen type restriction", lt_keys,
                              index=lt_keys.index(spec.get("location_type_preference")
                                                  if spec.get("location_type_preference") in lt_keys else None),
                              format_func=lambda k: LOCATION_TYPE_OPTIONS[k])

        excl_text = st.text_area("Exclusions (one per line)",
                                 value="\n".join(spec.get("exclusion_criteria") or []), height=80)
        st.caption(f"Audience: {', '.join(spec.get('audience_descriptors') or []) or '—'} · "
                   f"ages {spec.get('target_age_min')}–{spec.get('target_age_max')} · "
                   f"POI affinities: {', '.join(spec.get('poi_affinities') or []) or '—'} · "
                   f"objective: {spec.get('objective')}")

    if st.button("2 · Score, price & optimize  (Plan → Act)", type="primary"):
        edited = dict(spec)
        edited["budget"] = budget_val or None
        edited["duration_days"] = int(duration_val) or None
        edited["rotation_slots_per_day"] = int(slots_val)
        edited["city_hint"] = city_val.strip() or None
        edited["start_date"] = date_val.isoformat() if use_date else None
        edited["location_type_preference"] = lt_val
        edited["exclusion_criteria"] = [l.strip() for l in excl_text.splitlines() if l.strip()]
        st.session_state["spec"] = edited

        with st.status("**Plan** — scoring 67K screen/slot pairs → pricing → "
                       "**Act** — optimizing the package...", expanded=False) as status:
            st.session_state["result"] = run_with_spec(edited, st.session_state["brief_name"])
            ok = st.session_state["result"]["status"] == "ok"
            status.update(label="**Plan → Act** — recommendation ready." if ok
                          else "Run finished with no recommendation — see below.",
                          state="complete" if ok else "error")
        st.session_state.pop("last_diff", None)
        st.rerun()


# ----------------------------------------------------------- results view
if "result" in st.session_state:
    r = st.session_state["result"]

    if r["status"] == "error":
        st.error(f"Pipeline error: {r['narrative']}")
        st.stop()
    if r["status"] in ("no_match", "no_package"):
        st.warning(r["narrative"])
        if r.get("filters"):
            with st.expander("What was filtered, and why"):
                st.json(r["filters"])
        st.stop()

    # Feedback diff — shown right after a refine, before anything else
    diff = st.session_state.get("last_diff")
    if diff:
        st.success(
            f"**Refined.** {len(diff['screens_added'])} screen(s) added, "
            f"{len(diff['screens_removed'])} removed, {diff['n_unchanged']} unchanged · "
            f"cost {'+' if diff['cost_delta'] >= 0 else ''}${diff['cost_delta']:,.2f} · "
            f"reach {'+' if diff['reach_delta'] >= 0 else ''}{diff['reach_delta']:,}/day")
        if diff["screens_added"] or diff["screens_removed"]:
            with st.expander("Exactly what changed"):
                cA, cB = st.columns(2)
                cA.markdown("**Added**\n" + ("\n".join(f"- {x}" for x in diff["screens_added"]) or "- (none)"))
                cB.markdown("**Removed**\n" + ("\n".join(f"- {x}" for x in diff["screens_removed"]) or "- (none)"))

    cs = r["campaign_summary"]
    st.subheader("Campaign")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Objective", cs["objective"])
    c2.metric("Age range", cs["age_range"])
    c3.metric("Geography", cs["geography"])
    c4.metric("Budget", f"${cs['budget']:,.0f}" if cs["budget"] else "not stated")
    c5.metric("Duration", f"{cs['duration_days']} days" if cs["duration_days"] else "not stated")

    for caveat in r["caveats"]:
        st.warning(f"⚠️ {caveat}")

    f = r["filters"]
    with st.expander(f"Filters applied · {f['candidates_scored']:,} candidate "
                     f"screen/slot pairs scored",
                     expanded=bool(f["exclusions"] or f["location_type"])):
        if not f["exclusions"] and not f["location_type"] and not f.get("availability"):
            st.caption("No exclusions or constraints in this brief.")
        for e in f["exclusions"]:
            if e.get("enforced") and e.get("screens_removed", 0) > 0:
                st.markdown(f"✅ **Enforced:** {e['criterion']} — removed {e['screens_removed']:,} screens")
            elif e.get("enforced"):
                st.markdown(f"✅ **Enforced (nothing left to remove):** {e['criterion']}")
            else:
                st.markdown(f"❌ **NOT enforced** — {e['criterion']} — {e.get('note', 'no matching rule')}")
        lt = f["location_type"]
        if lt:
            if lt.get("applied"):
                st.markdown(f"✅ **Location type:** {lt['location_type_preference']} — "
                            f"removed {lt['screens_removed']:,} screens")
            else:
                st.markdown(f"❌ **Location type NOT applied:** {lt.get('warning', '')}")
        av = f.get("availability")
        if av:
            if av.get("checked"):
                st.markdown(f"✅ **Slot availability** checked for {av['window']} — "
                            f"{av['pairs_removed_unavailable']:,} screen/slot pairs already booked out "
                            f"(of {av['pairs_checked']:,} checked)")
            else:
                st.markdown(f"ℹ️ **Slot availability not checked:** {av.get('warning') or av.get('note', '')}")

    t = r["totals"]
    st.subheader("Package summary")
    c1, c2, c3, c4 = st.columns(4)
    budget_delta = (f"{t['budget_utilization_pct']}% of budget"
                    if t["budget_utilization_pct"] is not None else t["cost_basis"])
    c1.metric("Total price", f"${t['total_price']:,.2f}", delta=budget_delta, delta_color="off")
    c2.metric("Impressions / week", f"{t['impressions_per_week']:,.0f}")
    c3.metric("Reach after overlap dedup", f"{t['reach_after_dedup']:,}",
              delta=f"−{t['reach_before_dedup'] - t['reach_after_dedup']:,} de-duplicated",
              delta_color="off")
    c4.metric("Screens / clusters", f"{t['n_screens']} / {t['n_clusters']}")
    if t["budget_utilization_pct"] is not None:
        st.progress(min(t["budget_utilization_pct"] / 100, 1.0),
                    text=f"Budget used: {t['budget_utilization_pct']}%")
    st.caption("Screens sharing a stop or corridor reach the same commuters — "
               "reach is de-duplicated so it isn't double-counted.")

    # ---- Charts: where the reach lands, and value per dollar ----
    sdf = pd.DataFrame(r["selected_screens"])
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("**Daily reach by time block**")
        by_block = (sdf.groupby("time_block")["effective_impressions"].sum()
                    .sort_index().rename("reach/day"))
        st.bar_chart(by_block, color="#EEFB87")
    with ch2:
        st.markdown("**Cost vs reach per screen** (up-left = best value)")
        st.scatter_chart(sdf, x="cost_for_campaign", y="effective_impressions",
                         color="#1F242F", size="relevance_score")

    st.info(f"**Agent summary:** {r['narrative']}")

    st.subheader("Recommended screens")
    for s in r["selected_screens"]:
        with st.container(border=True):
            top = st.columns([3, 1, 1, 1])
            top[0].markdown(f"### {s['location']}")
            avail_txt = (f" · {s['slots_available']} of 6 slots free"
                         if s.get("slots_available") is not None else "")
            top[0].caption(f"{s['screen_id']} · {s['location_type']} · {s['zone']}, "
                           f"{s['city']} [{s['market_tier']}] · {s['time_block']}{avail_txt}")
            top[1].metric("Price target", f"${s['price_target']:,.2f}",
                          delta=f"floor ${s['price_floor']:,.2f} · cap ${s['price_cap']:,.2f}",
                          delta_color="off")
            top[2].metric("Reach / day", f"{s['effective_impressions']:,.0f}")
            top[3].metric("Campaign cost", f"${s['cost_for_campaign']:,.0f}")

            st.markdown(f"**Why this screen:** {s['reason']}")
            st.caption(f"**Who's there:** {s['audience_profile']}")

            tags = st.columns([1, 1, 2, 2])
            tags[0].caption(f"Relevance: {s['relevance_score']:.0%}")
            tags[1].caption(CONFIDENCE_BADGE.get(s["confidence"], f"⚪ {s['confidence']}"))
            tags[2].caption(f"Pricing basis: {s['demand_basis']}")
            if s["standalone_impressions"] > s["effective_impressions"]:
                overlap = s["standalone_impressions"] - s["effective_impressions"]
                tags[3].caption(f"Overlap discount: −{overlap:,.0f}/day "
                                f"(shares audience: {s['cluster']})")

    st.subheader("Export")
    d1, d2 = st.columns(2)
    d1.download_button("Download recommendation (.md)", r["detail_md"] or "",
                       file_name=f"{st.session_state['brief_name']}_recommendation.md")
    d2.download_button("Download recommendation (.json)",
                       json.dumps(r["detail"], indent=2, default=str),
                       file_name=f"{st.session_state['brief_name']}_recommendation.json")

    # -------------------------------------------- ADAPT: feedback (stage 3)
    st.subheader("Refine  (Adapt)")
    fb = st.text_input("Tell the agent what to change",
                       placeholder="e.g. 'only metro platform screens' or "
                                   "'exclude value-tier inventory'")
    if st.button("Regenerate with feedback"):
        if fb.strip():
            with st.status("**Adapt** — merging feedback into the spec and re-running...",
                           expanded=False) as status:
                prev = st.session_state["result"]
                new = run_feedback(r["spec"], fb, brief_name=st.session_state["brief_name"])
                st.session_state["prev_result"] = prev
                st.session_state["result"] = new
                st.session_state["spec"] = new.get("spec", r["spec"])
                st.session_state["last_diff"] = compute_diff(prev, new)
                status.update(label="**Adapt** — refined.", state="complete")
            st.rerun()
        else:
            st.warning("Type what you'd like changed first.")