"""Best publish times. Starts from audience-geography priors and learns each channel's own best slots.

Each candidate slot is a bandit arm: UCB over the channel's own results (normalised views per slot), so a slot
that has not been tried yet is explored first, then the winners are repeated. Minutes are jittered so uploads
never land on the dot like a script would."""
import datetime as dt
import hashlib
import math

from .playbooks import SLOTS, cadence_for


def _h(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest(), 16)


def choose(channel: str, fmt: str, n: int, day: dt.date, stats: dict[str, tuple[int, float]], now: dt.datetime, min_lead_h: float = 4.5, *, occupied: tuple[dt.datetime, ...] = ()) -> list[dt.datetime]:
    """n publish datetimes (UTC) on `day`, at least 3 h apart and at least `min_lead_h` ahead of `now`."""
    total = sum(c for c, _ in stats.values())
    scored = []
    for k, slot in enumerate(SLOTS):
        c, mean = stats.get(slot, (0, 0.0))
        explore = 2.0 if c == 0 else 0.6 * math.sqrt(math.log(total + 2) / c)
        prior = (len(SLOTS) - k) / len(SLOTS) * 0.25  # earlier in SLOTS = better prior
        jitter = (_h(channel, fmt, day, slot) % 100) / 1000
        scored.append((mean + explore + prior + jitter, slot))
    picked: list[dt.datetime] = []
    for _, slot in sorted(scored, reverse=True):
        hh, mm = map(int, slot.split(":"))
        minute_shift = (_h(channel, fmt, day, slot, "m") % 15) - 7
        when = dt.datetime.combine(day, dt.time(hh, mm), tzinfo=dt.timezone.utc) + dt.timedelta(minutes=minute_shift)
        if when < now + dt.timedelta(hours=min_lead_h):
            continue
        if any(abs((when - p).total_seconds()) < 3 * 3600 for p in (*occupied, *picked)):
            continue
        picked.append(when)
        if len(picked) == n:
            break
    return sorted(picked)


def slot_key(when: dt.datetime, *, atlas: bool = False) -> str:
    """Nearest candidate slot label for a datetime, so results map back to arms."""
    mins = when.hour * 60 + when.minute
    candidates = [slot for _, slots in ATLAS_WINDOWS for slot in slots] + list(ATLAS_LONG_SLOTS) if atlas else SLOTS
    best = min(candidates, key=lambda s: abs(int(s[:2]) * 60 + int(s[3:]) - mins))
    return best


# Three genuinely separated geographic experiments for Counterfactual Atlas.
# Times are UTC, not local-device times; the daily plan survives travel or DST.
# Actual per-format, maturity-filtered YouTube metrics supersede the cold-start
# ordering once enough genuine channel videos have been observed.
ATLAS_WINDOWS = (
    ("Asia-Pacific", ("00:30", "03:30")),
    ("Europe-Africa", ("12:00", "14:00")),
    ("Americas", ("17:30", "18:00")),
)


ATLAS_LONG_SLOTS = ("07:00", "08:00")


def atlas_daily_slots(day: dt.date, now: dt.datetime,
                      stats_short: dict[str, tuple[int, float]],
                      stats_long: dict[str, tuple[int, float]], *,
                      existing: tuple[dt.datetime, ...] = (),
                      need_short: int | None = None, need_long: int | None = None,
                      min_lead_h: float = 4.5) -> dict[str, list[dt.datetime]]:
    """Three independent daily slots, one per geographic window; never claim
    a best time when there is no meaningful observed audience data.

    A completed partial plan keeps its existing times. On restarts we fill only
    missing slots; any time already occupied is excluded from new suggestions.
    Failed or late drafts cannot be assigned a slot in the past.
    """
    if now.tzinfo is None or any(x.tzinfo is None for x in existing):
        raise ValueError("Atlas slot scheduling requires timezone-aware timestamps")
    target = cadence_for("Counterfactual Atlas", day)
    need_short = target["short"] if need_short is None else need_short
    need_long = target["long"] if need_long is None else need_long
    if not 0 <= need_short <= target["short"] or not 0 <= need_long <= target["long"]:
        raise ValueError("Atlas slot requests exceed the date's format targets")
    results: dict[str, list[dt.datetime]] = {"short": [], "long": []}
    occupied = tuple(existing)
    windows = [slots for _, slots in ATLAS_WINDOWS]
    allocation = [("short", range(len(windows)))] * need_short
    if need_long:
        # Midday in India, with at least three hours to either neighboring Short.
        allocation.append(("long", (len(windows),)))
        windows.append(ATLAS_LONG_SLOTS)
    used_windows: set[int] = set()
    for fmt, order in allocation:
        for window_index in order:
            if window_index in used_windows:
                continue
            slots = windows[window_index]
            stats = stats_long if fmt == "long" else stats_short
            samples = sum(count for count, _ in stats.values())
            choices = []
            for k, slot in enumerate(slots):
                hh, mm = map(int, slot.split(":"))
                jitter = (_h("atlas", day, fmt, slot, "jitter") % 15) - 7
                when = dt.datetime.combine(day, dt.time(hh, mm), tzinfo=dt.timezone.utc) + dt.timedelta(minutes=jitter)
                if when < now + dt.timedelta(hours=min_lead_h):
                    continue
                if any(abs((when - other).total_seconds()) < 3 * 3600 for other in (*occupied, *results["long"], *results["short"])):
                    continue
                count, mean = stats.get(slot, (0, 0.0))
                # Cold-start: deterministic 50/50 exploration within each region.
                # Later: an evidence-backed UCB preference for mature performance.
                exploration = (2.0 if count == 0 else
                               0.5 * math.sqrt(math.log(samples + 2) / count))
                prior = (_h("atlas", day, window_index, slot, "explore") % 1000) / 10000
                choices.append((mean + exploration + prior, when))
            if choices:
                _, chosen = max(choices)
                results[fmt].append(chosen)
                used_windows.add(window_index)
                break
    for fmt in results:
        results[fmt].sort()
    return results
