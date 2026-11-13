"""Block deceptive duration, impossible puppet moves and generic Atlas visuals."""
from engine.render import NO_MASCOT
from engine.spec_check import problems


def spec(channel, scenes, *, meta=None):
    return {"id": "2026-11-16-test-s1", "channel": channel, "format": "short",
            "title": "A factual hook", "description": "A meaningful and sourced scientific explanation. " * 4,
            "tags": ["science"], "scenes": scenes, "meta": meta or {}}


def shot(say, kind, **fields):
    return {"say": say, "show": {"type": kind, **fields}}


def test_atlas_has_no_repeated_mascot_overlay():
    assert "atlas" in NO_MASCOT
    assert "lowbat" in NO_MASCOT
    assert "oddly" not in NO_MASCOT


def test_10sec_branded_video_cannot_run_like_a_normal_short():
    okay = spec("10SecScientist", [
        shot("Why does a spoon ring?", "title", text="Why spoons ring"),
        shot("Metal vibrates when struck, pushing nearby air.", "number", value=1, label="One strike"),
        shot("You hear those pressure waves as sound.", "list", items=["Metal vibrates", "Air moves"]),
        shot("That little ring is moving air.", "end", text="Sound is vibration"),
    ])
    assert problems(okay, "2026-11-16", strict=True) == []
    too_long = {**okay, "scenes": okay["scenes"] * 3}
    assert any("ten-second promise" in s for s in problems(too_long, "2026-11-16", strict=True))


def test_atlas_autopilot_needs_physical_visual_not_charts_only():
    s = spec("Counterfactual Atlas", [
        shot("What if the Moon moved?", "title", text="Moon"),
        shot("The distance could change the tides.", "number", value=2),
        shot("This is an example, not measured.", "bars", items=[{"label":"One", "value":1},{"label":"Two", "value":2}]),
        shot("The effect depends on the model.", "end", text="Compare"),
    ], meta={"generator": "autopilot"})
    assert any("visualized physical scenario" in x for x in problems(s, "2026-11-16", strict=True))
    s["scenes"][1]["show"] = {"type": "orbit", "ratio": .5}
    assert not any("visualized physical scenario" in x for x in problems(s, "2026-11-16", strict=True))


def test_low_battery_rejects_impossible_off_set_action():
    s = spec("The Low Battery Show", [
        shot("Pip notices his phone on the table.", "title", text="Phone"),
        shot("Pip reaches too far.", "pip", action="notice"),
        shot("His hand is just short.", "pip", action="reach"),
        shot("The phone slides away.", "pip", action="slip"),
        shot("He sits back and resets.", "pip", action="reset"),
        shot("The phone wins.", "end", text="Pip loses"),
    ])
    assert not any("Low Battery set cannot" in x for x in problems(s, "2026-11-16", strict=True))
    s["title"] = "The charger cable falls from the wall"
    assert any("Low Battery set cannot" in x for x in problems(s, "2026-11-16", strict=True))
