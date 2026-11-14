"""Atlas production schedule and exploration windows."""
import datetime as dt
import pytest
from autopilot.playbooks import ATLAS_END_DATE, cadence_for
from autopilot.slots import ATLAS_WINDOWS, atlas_daily_slots

UTC = dt.timezone.utc


def test_daily_shorts_weekly_longs_and_january_cutoff():
    start = dt.date(2026, 11, 16)
    for offset in range((ATLAS_END_DATE - start).days + 2):
        day = start + dt.timedelta(days=offset)
        before = dt.datetime.combine(day - dt.timedelta(days=1), dt.time(), tzinfo=UTC)
        slots = atlas_daily_slots(day, before, {}, {})
        assert {fmt: len(times) for fmt, times in slots.items()} == cadence_for("Counterfactual Atlas", day)
        assert len(slots["short"]) == (3 if day <= ATLAS_END_DATE else 0)
        assert len(slots["long"]) == int(day <= ATLAS_END_DATE and day.weekday() in (0, 2, 5))
        times = sorted(slots["short"] + slots["long"])
        assert all(b - a >= dt.timedelta(hours=3) for a, b in zip(times, times[1:]))
        assert all((time + dt.timedelta(hours=5, minutes=30)).date() == day for time in times)


def test_resumption_preserves_existing_and_rejects_close_times():
    day = dt.date(2026, 11, 18)
    before = dt.datetime(2026, 11, 17, tzinfo=UTC)
    slots = atlas_daily_slots(day, before, {}, {})
    already = (slots["short"][0],)
    rest = atlas_daily_slots(day, before, {}, {}, existing=already, need_short=2, need_long=1)
    assert len(rest["short"]) == 2 and len(rest["long"]) == 1
    assert all(abs((time - already[0]).total_seconds()) >= 10800 for time in rest["short"] + rest["long"])
    with pytest.raises(ValueError):
        atlas_daily_slots(day, dt.datetime(2026, 11, 16), {}, {})
    with pytest.raises(ValueError):
        atlas_daily_slots(day, before, {}, {}, need_short=4)


def test_real_mature_winner_gets_preferred():
    day = dt.date(2027, 1, 13)
    before = dt.datetime(2027, 1, 12, tzinfo=UTC)
    stats = {v: (12, .35) for _, region in ATLAS_WINDOWS for v in region}
    stats["17:30"] = (12, 1.0)
    result = atlas_daily_slots(day, before, stats, {})
    assert any(abs(t.hour * 60 + t.minute - 1050) <= 7 for t in result["short"])


def test_expired_slots_are_not_backfilled():
    day = dt.date(2027, 1, 14)
    now = dt.datetime(2027, 1, 14, 22, tzinfo=UTC)
    assert atlas_daily_slots(day, now, {}, {}) == {"short": [], "long": []}
