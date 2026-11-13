"""Best publish times. Starts from audience-geography priors and learns each channel's own best slots.

Each candidate slot is a bandit arm: UCB over the channel's own results (normalised views per slot), so a slot
that has not been tried yet is explored first, then the winners are repeated. Minutes are jittered so uploads
never land on the dot like a script would."""
import datetime as dt
import hashlib
import math

from .playbooks import SLOTS


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


def slot_key(when: dt.datetime) -> str:
    """Nearest candidate slot label for a datetime, so results map back to arms."""
    mins = when.hour * 60 + when.minute
    best = min(SLOTS, key=lambda s: abs(int(s[:2]) * 60 + int(s[3:]) - mins))
    return best
