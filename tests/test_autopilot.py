"""Offline tests: a scripted fake model drives the whole planner, so every gate and file write is exercised."""
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from autopilot import daily, insights  # noqa: E402
from autopilot.llm import LLM, LLMError, extract_json  # noqa: E402
from autopilot.normalize import speakable  # noqa: E402
from autopilot.slots import choose  # noqa: E402
from engine.spec_check import problems  # noqa: E402


def short_script(title="What if the Sun vanished for one second?"):
    scenes = [
        {"say": "What if the Sun vanished for just one second?", "show": {"type": "title", "text": "The Sun, gone for 1 second", "kicker": "What if"}},
        {"say": "You would not notice for eight minutes and twenty seconds.", "show": {"type": "number", "from": 0, "value": 500, "unit": "seconds", "label": "Light travel time from the Sun"}, "emoji": "☀️"},
        {"say": "Light takes that long to cross 149 million kilometres, and gravity travels at the same speed.", "show": {"type": "bars", "title": "Distance", "unit": "million km", "items": [{"label": "Moon", "value": 0.38}, {"label": "Sun", "value": 149.6, "highlight": True}]}},
        {"say": "So Earth keeps circling the empty spot for those eight minutes."},
        {"say": "Then the sky goes dark and the pull ends.", "show": {"type": "say", "text": "Dark, then straight on", "hero": "🌑"}},
        {"say": "Without the pull, we would fly off in a straight line at thirty kilometres a second.", "show": {"type": "list", "title": "What changes", "items": ["No more orbit", "Straight-line travel", "Cold within days"]}},
        {"say": "But it is back after one second, and nothing would feel different.", "show": {"type": "number", "from": 0, "value": 1, "unit": "second", "label": "Gone"}},
        {"say": "So the Sun could vanish, and for eight minutes the universe would not know."},
        {"say": "That is the first thing light teaches us: nothing travels faster than news of itself.", "show": {"type": "end", "text": "New what-if every day"}},
    ]
    filler = " This is a precise and calm sentence about the Sun and the Earth and the speed of light." * 0
    return {"title": title, "thumb": "Sun gone for one second", "description": "What happens if the Sun disappeared for one second, explained with the real speed of light and gravity. " + "A short explainer with numbers on screen.", "tags": ["what if", "sun"], "scenes": [{**s, "say": s["say"] + filler} for s in scenes]}


class Scripted:
    """Stands in for a provider: answers by looking at what the prompt asks for."""
    name, models, dead = "fake", ["m"], set()

    def __init__(self):
        self.n = 0

    def chat(self, model, system, user, temperature, max_tokens, want_json):
        self.n += 1
        if "Brainstorm 8 video topics" in user:
            return json.dumps({"topics": [{"topic": f"Topic {self.n} about the Sun", "axis": "astronomy and orbits", "wiki_query": "Sun"}, {"topic": "How tides move the oceans", "axis": "oceans and tides", "wiki_query": "Tide"}, {"topic": "What if the Sun vanished for one second", "axis": "astronomy and orbits", "wiki_query": "Sun"}]})
        if "strict editor" in system:
            return json.dumps({"hook": 8, "originality": 7, "accuracy": 8, "unsupported_claims": [], "fixes": [], "pass": True})
        if "Plan a long video" in user:
            return json.dumps({"title": "How the Sun keeps Earth in orbit", "thumb": "The Sun's invisible leash", "description": "A slow look at gravity and orbits.", "tags": ["gravity"], "chapters": [{"name": f"C{i}", "beats": "b", "open_loop": "l"} for i in range(6)]})
        if "Write chapter" in user:
            sc = [{"say": f"Sentence {i} about the long motion of the planets around the Sun, told clearly and calmly, with a specific number like {100 + i} kilometres per second.", "show": ([{"type": "number", "from": 0, "value": 30, "unit": "km/s", "label": "Orbital speed"}, {"type": "list", "title": "T", "items": ["a", "b"]}, None][i % 3])} for i in range(8)]
            for s in sc:
                if s["show"] is None:
                    del s["show"]
            if "last chapter" in user:
                sc[-1]["show"] = {"type": "end", "text": "Tomorrow, another"}
            if "opens the video" in user:
                sc[0]["show"] = {"type": "title", "text": "Orbits", "kicker": "Atlas"}
            return json.dumps({"scenes": sc})
        titles = ["What if the Sun vanished for one second?", "How the tides really move the oceans", "Why Mars looks red from Earth", "The tiny speed limit of everything"]
        return json.dumps(short_script(titles[self.n % len(titles)]))


def llm_with(provider):
    prov = provider
    return LLM(providers=[prov], log=lambda *_: None)


def test_extract_json_tolerates_fences():
    assert extract_json('Here you go:\n```json\n{"a": 1}\n```') == {"a": 1}


def test_speakable_numbers_and_years():
    assert speakable("In 1883, 36,000 died: 8x louder, 40% less") == "In eighteen eighty-three, thirty-six thousand died: eight times louder, forty percent less"


def test_slots_respect_lead_time_and_spacing():
    now = dt.datetime(2026, 11, 12, 20, 0, tzinfo=dt.timezone.utc)
    got = choose("Atlas", "short", 3, dt.date(2026, 11, 13), {}, now)
    assert len(got) == 3 and all(b - a >= dt.timedelta(hours=3) for a, b in zip(got, got[1:])) and all(g > now + dt.timedelta(hours=4) for g in got)


def test_slot_bandit_prefers_a_winning_slot():
    now = dt.datetime(2026, 11, 12, 0, 0, tzinfo=dt.timezone.utc)
    stats = {s: (6, 0.2) for s in ("14:00", "18:00", "00:30", "12:00", "16:00", "20:30", "03:30")}
    stats["20:30"] = (6, 0.9)
    got = choose("X", "short", 1, dt.date(2026, 11, 14), stats, now)
    assert (got[0].hour, got[0].minute // 30) in ((20, 1), (20, 0), (21, 0))


def test_short_plan_writes_a_valid_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "SPECS", tmp_path / "specs")
    monkeypatch.setattr(daily, "ground", lambda q, **k: {"text": "The Sun is 149.6 million km away.", "sources": [{"title": "Sun", "url": "https://en.wikipedia.org/wiki/Sun"}]})
    monkeypatch.setattr(insights, "STATE", tmp_path / "state")
    now = dt.datetime(2026, 11, 12, 6, 0, tzinfo=dt.timezone.utc)
    out = daily.plan([dt.date(2026, 11, 13)], llm_with(Scripted()), now, only=["Counterfactual Atlas"], log=lambda *_: None)
    shorts = [p for p in out["written"] if "-s" in p]
    assert len(shorts) == 2, out
    spec = json.loads((tmp_path / "specs" / "2026-11-13" / pathlib.Path(shorts[0]).name).read_text())
    assert problems(spec, "2026-11-13", strict=True) == []
    assert spec["publishAt"].startswith("2026-11-13T") and "Sources" in spec["description"]
    assert any(e["id"] == spec["id"] for e in json.loads((tmp_path / "state" / "ledger.json").read_text()))


def test_existing_specs_are_never_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "SPECS", tmp_path / "specs")
    monkeypatch.setattr(insights, "STATE", tmp_path / "state")
    (tmp_path / "specs" / "2026-11-13").mkdir(parents=True)
    for i, ch in enumerate(["a", "b"]):
        (tmp_path / "specs" / "2026-11-13" / f"x{i}.json").write_text(json.dumps({"channel": "Foundbeam", "format": "long" if i == 0 else "short"}))
    out = daily.plan([dt.date(2026, 11, 13)], llm_with(Scripted()), dt.datetime(2026, 11, 12, 6, tzinfo=dt.timezone.utc), only=["Foundbeam"], log=lambda *_: None)
    assert out["written"] == []


def test_no_keys_fails_cleanly():
    try:
        LLM(providers=[]).complete("s", "u")
    except LLMError as e:
        assert "no LLM key" in str(e)
    else:
        raise AssertionError


def test_long_plan_writes_valid_long_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "SPECS", tmp_path / "specs")
    monkeypatch.setattr(daily, "ground", lambda q, **k: {"text": "x", "sources": []})
    monkeypatch.setattr(insights, "STATE", tmp_path / "state")
    from autopilot import playbooks
    monkeypatch.setitem(playbooks.PLAYBOOKS["Counterfactual Atlas"], "long_words", 1300)
    out = daily.plan([dt.date(2026, 11, 14)], llm_with(Scripted()), dt.datetime(2026, 11, 12, 6, tzinfo=dt.timezone.utc), only=["Counterfactual Atlas"], log=print)
    print(out)
    longs = [p for p in out["written"] if "-l" in p]
    assert longs, out


def test_best_tier_tries_strong_models_first_and_falls_back():
    from autopilot.llm import Provider
    seen = []

    class P(Provider):
        def chat(self, model, system, user, temperature, max_tokens, want_json):
            seen.append(model)
            if model == "pro":
                from autopilot.llm import LLMError as E
                raise E("429 daily quota exceeded")
            return '{"ok": true}'

    prov = P("g", "http://x", "k", models=["lite"], best=["pro", "flash"])
    llm = LLM(providers=[prov], log=lambda *_: None)
    llm.sleep = lambda s: None
    assert llm.complete("s", "u", tier="best") == {"ok": True}
    assert seen == ["pro", "flash"] and llm.last_model == "g:flash"
    seen.clear()
    assert llm.complete("s", "u") == {"ok": True}  # bulk tier goes straight to the high-quota model
    assert seen == ["lite"]


def test_busy_errors_are_retried_and_do_not_kill_the_model():
    from autopilot.llm import Provider
    calls = []

    class P(Provider):
        def chat(self, model, system, user, temperature, max_tokens, want_json):
            calls.append(model)
            if len(calls) < 3:
                raise LLMError('503 {"status": "UNAVAILABLE", "message": "high demand"}')
            return '{"ok": true}'

    prov = P("g", "http://x", "k", models=["flash"])
    waits = []
    llm = LLM(providers=[prov], log=lambda *_: None)
    llm.sleep = waits.append
    assert llm.complete("s", "u") == {"ok": True}
    assert calls == ["flash", "flash", "flash"] and "flash" not in prov.dead and len(waits) == 2


def test_free_tier_limit_zero_marks_model_dead_quickly():
    from autopilot.llm import Provider

    class P(Provider):
        def chat(self, model, system, user, temperature, max_tokens, want_json):
            if model == "pro":
                raise LLMError("429 You exceeded your current quota: limit: 0")
            return '{"ok": true}'

    prov = P("g", "http://x", "k", models=["lite"], best=["pro"])
    llm = LLM(providers=[prov], log=lambda *_: None)
    llm.sleep = lambda s: (_ for _ in ()).throw(AssertionError("should not wait"))
    assert llm.complete("s", "u", tier="best") == {"ok": True} and "pro" in prov.dead


def test_list_replies_do_not_crash_the_planner():
    assert daily.as_obj([{"topics": [1]}], "topics") == {"topics": [1]}
    assert daily.as_obj([{"say": "a"}], "scenes") == {"scenes": [{"say": "a"}]}
    try:
        daily.as_obj("text", "scenes")
        raise AssertionError("should reject")
    except LLMError:
        pass


def test_retry_attempts_stop_at_call_budget():
    import pytest
    from autopilot.llm import Provider

    class Busy(Provider):
        def chat(self, *args):
            raise LLMError("503 unavailable")

    llm = LLM(providers=[Busy("busy", "", "", ["m"])], log=lambda *_: None)
    waits = []
    llm.sleep = waits.append
    with pytest.raises(LLMError, match="call budget"):
        llm.complete("s", "u", max_calls=2)
    assert waits == [8]
    assert llm.attempts_by_model == {"busy:m": 2}
    assert llm.by_provider == {}


def test_backoff_respects_planner_deadline(monkeypatch):
    import pytest
    from autopilot import llm as router
    from autopilot.llm import Provider

    class Busy(Provider):
        def chat(self, *args):
            raise LLMError("503 unavailable")

    monkeypatch.setattr(router.time, "monotonic", lambda: 100)
    llm = LLM(providers=[Busy("busy", "", "", ["m"])])
    waits = []
    llm.sleep = waits.append
    with pytest.raises(LLMError, match="time limit"):
        llm.complete("s", "u", deadline=104)
    assert llm.calls == 1
    assert waits == []


def test_missing_editor_decision_holds_spec(monkeypatch):
    import pytest

    planner = daily.Planner(llm_with(Scripted()))
    monkeypatch.setattr(planner, "_call", lambda *a, **k: {"fixes": []})
    with pytest.raises(LLMError, match="valid pass decision"):
        planner.critic("Counterfactual Atlas", short_script(), {"text": ""})


def test_network_plan_rotates_first_channel_between_windows(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "SPECS", tmp_path / "specs")
    monkeypatch.setattr(insights, "STATE", tmp_path / "state")
    channels = ["Counterfactual Atlas", "10SecScientist"]
    day = dt.date(2026, 11, 14)
    seen = []

    def exhaust_budget(self, channel, *args):
        seen.append(channel)
        raise LLMError("call budget for this run is used up")

    monkeypatch.setattr(daily.Planner, "make", exhaust_budget)
    now = dt.datetime(2026, 11, 13, tzinfo=dt.timezone.utc)
    for offset in (0, 4):
        daily.plan([day], llm_with(Scripted()), now + dt.timedelta(hours=offset), only=channels)
    assert set(seen) == set(channels)
    assert len(seen) == 2


def test_heal_recovers_incomplete_release_even_when_pack_exists(tmp_path, monkeypatch):
    import subprocess
    from scripts import autopilot as cli

    tag = dt.date.today().isoformat()
    folder = tmp_path / "specs" / tag
    folder.mkdir(parents=True)
    sid = f"{tag}-atlas-s1"
    spec = folder / "atlas-s1.json"
    spec.write_text(json.dumps({"id": sid}))
    assets = [{"name": f"{sid}-pack.json"}, {"name": f"{sid}-video.mp4"}]
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "sh", lambda *args: "100")
    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        args, 0, stdout=json.dumps({"assets": assets}), stderr=""
    ))
    outputs = []
    monkeypatch.setattr(cli, "emit", lambda *args: outputs.append(args))

    assert cli.cmd_heal(None) == 0
    assert outputs[-1] == ("heal", str(spec.relative_to(tmp_path)))
    assets.append({"name": f"{sid}-thumb.jpg"})
    assert cli.cmd_heal(None) == 0
    assert outputs[-1] == ("heal", "")
