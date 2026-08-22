"""
optimization/availability.py
-----------------------------
Slot-availability check against EXISTING bookings -- closes the PS gap
quoted directly from the business problem: "...if three other advertisers
are competing for the same inventory that week."

HOW INVENTORY WORKS (dim_slot / Time Blocks & Rotation Slots slide)
Each screen has 6 rotation slots per 4-hour time block, looping all block.
A booking claims `slots_booked_per_day` of those 6 for every day in its
[start_date, end_date] range. So for a candidate (screen, time_block) and a
campaign window, capacity remaining = 6 - sum(slots_booked_per_day of every
non-cancelled booking that overlaps the window on that screen+block).

DESIGN RULES (consistent with the rest of the codebase)
- Never invents a window. If the brief has no start_date, availability
  simply cannot be checked -- the caller gets a loud caveat, not a guess.
- If duration_days is missing but start_date exists, checks the start date
  as a 1-day window and says so.
- Peak-overlap approximation: we sum slots across ALL bookings overlapping
  the window rather than computing the true day-by-day maximum. This can
  slightly OVER-count concurrency when two bookings overlap the campaign
  window but not each other -- i.e. it errs toward calling a screen
  unavailable, never toward double-booking one. Documented tradeoff:
  conservative and O(1 query), vs. a day-by-day sweep.

USAGE
    from optimization.availability import annotate_availability
    candidates, avail_log = annotate_availability(candidates, spec, conn)
"""
from datetime import datetime, timedelta

import pandas as pd

MAX_SLOTS_PER_BLOCK = 6  # dim_slot rotation loop size


def _campaign_window(spec):
    start = spec.get("start_date")
    if not start:
        return None, None, ("Brief states no specific start date -- slot "
                            "availability against existing bookings was NOT "
                            "checked. All candidates assumed available.")
    start_dt = datetime.strptime(start[:10], "%Y-%m-%d")
    duration = spec.get("duration_days")
    if duration:
        end_dt = start_dt + timedelta(days=int(duration) - 1)
        note = None
    else:
        end_dt = start_dt
        note = ("Duration not stated -- availability checked for the start "
                "date only, not the full (unknown) campaign window.")
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"), note


def get_booked_slots(conn, screen_ids, window_start, window_end):
    """Slots already committed per (screen_id, time_block_id) over the window.
    Overlap condition: existing.start <= window_end AND existing.end >= window_start."""
    if not screen_ids:
        return {}
    placeholders = ",".join("?" * len(screen_ids))
    q = f"""
        SELECT screen_id, time_block_id,
               SUM(slots_booked_per_day) AS booked
        FROM bookings
        WHERE booking_status != 'cancelled'
          AND screen_id IN ({placeholders})
          AND date(start_date) <= date(?)
          AND date(end_date)   >= date(?)
        GROUP BY screen_id, time_block_id
    """
    df = pd.read_sql(q, conn, params=list(screen_ids) + [window_end, window_start])
    return {(r.screen_id, int(r.time_block_id)): int(r.booked)
            for r in df.itertuples(index=False)}


def annotate_availability(candidates, spec, conn):
    """Adds slots_available to candidates and removes pairs that can't fit
    the requested rotation_slots_per_day. Returns (filtered_df, log_dict).
    Never raises into the pipeline -- on unexpected failure, returns the
    input unchanged with the error in the log."""
    requested = int(spec.get("rotation_slots_per_day") or 1)

    try:
        window_start, window_end, note = _campaign_window(spec)
        if window_start is None:
            out = candidates.copy()
            out["slots_available"] = None  # unknown -- not checked
            return out, {"checked": False, "note": note}

        booked = get_booked_slots(conn, candidates.screen_id.unique().tolist(),
                                  window_start, window_end)

        out = candidates.copy()
        out["slots_available"] = out.apply(
            lambda r: MAX_SLOTS_PER_BLOCK - booked.get((r.screen_id, int(r.time_block_id)), 0),
            axis=1).clip(lower=0)

        before = len(out)
        available = out[out.slots_available >= requested]
        removed = before - len(available)

        log = {
            "checked": True,
            "window": f"{window_start} to {window_end}",
            "requested_slots_per_day": requested,
            "pairs_checked": before,
            "pairs_removed_unavailable": removed,
        }
        if note:
            log["note"] = note

        # Same safety-valve philosophy as the location filter: if the check
        # would remove EVERYTHING, that's almost certainly a data/date
        # mismatch, not a genuinely sold-out network -- keep the pool, flag it.
        if available.empty and before > 0:
            log["checked"] = False
            log["warning"] = (f"Availability check would have removed ALL {before} "
                              f"candidates for window {window_start}..{window_end}. "
                              f"Not applied -- verify the campaign dates against the "
                              f"bookings data before trusting this window.")
            return out, log

        return available, log

    except Exception as e:  # never let availability kill the pipeline
        out = candidates.copy()
        out["slots_available"] = None
        return out, {"checked": False,
                     "note": f"availability check failed ({type(e).__name__}: {e}) "
                             f"-- all candidates assumed available"}