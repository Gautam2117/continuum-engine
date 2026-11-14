"""The 50-channel network: every automated channel has a style and a playbook, and the daily plan is Atlas 3 + 47 x 1."""
import datetime as dt

from autopilot.playbooks import PLAYBOOKS, cadence_for
from engine.styles import CHANNEL_STYLE, style_for

OWN = {"GOTZ", "Felix"}  # SG's own gaming channels, never automated


def test_every_channel_has_style_and_playbook():
    assert len(CHANNEL_STYLE) == 50
    for c in CHANNEL_STYLE:
        style_for(c)
        assert (c in PLAYBOOKS) != (c in OWN), c
    assert len(PLAYBOOKS) == 48


def test_daily_plan_is_fifty_videos():
    for d in range(14):
        day = dt.date(2026, 11, 16) + dt.timedelta(d)
        counts = {c: sum(cadence_for(c, day).values()) for c in PLAYBOOKS}
        assert counts["Counterfactual Atlas"] == 3
        assert all(n == 1 for c, n in counts.items() if c != "Counterfactual Atlas"), day
        assert sum(counts.values()) == 50


def test_each_channel_has_two_long_days_a_week_when_it_has_both_formats():
    for c, pb in PLAYBOOKS.items():
        if pb.get("fixed") or not (pb["cadence"].get("long") and pb["cadence"].get("short")):
            continue
        longs = sum(cadence_for(c, dt.date(2026, 11, 16) + dt.timedelta(d))["long"] for d in range(7))
        assert longs == 2, c


def test_safety_rules_present():
    for c, pb in PLAYBOOKS.items():
        assert pb["avoid"], c
        if pb.get("persona"):
            assert any("AI" in a for a in pb["avoid"]), c
        if pb.get("host"):
            assert "claiming" in " ".join(pb["avoid"]) or "invented" in " ".join(pb["avoid"]), c
