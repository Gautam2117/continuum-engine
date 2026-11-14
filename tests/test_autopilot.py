"""Offline tests: a scripted fake model drives the whole planner, so every gate and file write is exercised."""
import datetime as dt
import json
import pathlib
import subprocess
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
        {"say": "Then the sky goes dark and the pull ends.", "show": {"type": "image", "query": "Sun NASA observatory photo", "caption": "Our star"}},
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
            sc[2]["show"] = {"type": "orbit", "ratio": 0.5, "a": "Earth today", "b": "A second orbit"}
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


def test_provider_discovery_excludes_non_chat_models(monkeypatch):
    from autopilot import llm as router

    def fake_http(url, body, headers, timeout=120):
        return {"data": [{"id": name} for name in (
            "nvidia/nemotron-4-340b-reward",
            "nvidia/nemotron-4-340b-instruct",
            "some-reranker-v2",
            "openai/gpt-oss-120b",
        )]}

    monkeypatch.setattr(router, "_http", fake_http)
    found = router.discover_openai_compat("https://example.com/v1", "secret", [])
    assert "nvidia/nemotron-4-340b-instruct" in found
    assert "openai/gpt-oss-120b" in found
    assert not any("reward" in name or "rerank" in name for name in found)


def test_gemini_discovery_excludes_specialized_tool_models(monkeypatch):
    from autopilot import llm as router

    monkeypatch.delenv("LLM_GEMINI_MODELS", raising=False)
    monkeypatch.setattr(router, "_http", lambda *args, **kwargs: {"models": [
        {"name": "models/gemini-3.1-pro-preview-customtools", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-3.1-pro-preview", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
    ]})
    best, bulk = router.discover_gemini("secret")
    assert "gemini-3.1-pro-preview" in best
    assert "gemini-3.5-flash-lite" in bulk
    assert not any("customtools" in model for model in best + bulk)


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
    monkeypatch.setenv("CONTINUUM_SPEC_DIR", str(daily.SPECS))
    worker = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "worker.py"
    scan = subprocess.run(
        [sys.executable, str(worker), "scan", "--spec", shorts[0],
         "--db", str(tmp_path / "worker.sqlite3")],
        check=True, capture_output=True, text=True,
    )
    assert json.loads(scan.stdout) == {"imported": 1, "existing": 0, "invalid": 0}


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
    for offset in (0, 15):
        daily.plan([day], llm_with(Scripted()), now + dt.timedelta(minutes=offset), only=channels)
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


def test_long_revision_reuses_outline_but_regenerates_chapters():
    llm = llm_with(Scripted())
    planner = daily.Planner(llm)
    topic = {"topic": "What if gravity changed?"}
    grounding = {"text": "Gravity shapes orbits."}
    planner.draft_long("Counterfactual Atlas", topic, grounding)
    initial = llm.calls
    planner.draft_long("Counterfactual Atlas", topic, grounding, ["Clarify the visual sequence"])
    assert initial == 7
    assert llm.calls == initial + 6


def test_slot_selection_spaces_formats_around_existing_uploads():
    day = dt.date(2026, 11, 14)
    now = dt.datetime(2026, 11, 13, tzinfo=dt.timezone.utc)
    shorts = choose("Counterfactual Atlas", "short", 2, day, {}, now)
    long = choose("Counterfactual Atlas", "long", 1, day, {}, now, occupied=tuple(shorts))
    assert len(shorts) == 2 and len(long) == 1
    assert all(abs((long[0] - other).total_seconds()) >= 10800 for other in shorts)


def test_review_inventory_restores_future_specs_without_overwriting_release(tmp_path):
    from scripts.review_inventory import restore

    source = tmp_path / "inventory"
    destination = tmp_path / "specs"
    for day in ("2026-11-13", "2026-11-14"):
        (source / day).mkdir(parents=True)
        for name in ("atlas-s1", "atlas-l1"):
            (source / day / f"{name}.json").write_text(json.dumps({"id": f"{day}-{name}"}))
    release = destination / "2026-11-14" / "atlas-l1.json"
    release.parent.mkdir(parents=True)
    release.write_text("tracked release")
    today = dt.date(2026, 11, 14)
    assert restore(source, destination, today) == 1
    assert restore(source, destination, today) == 0
    assert release.read_text() == "tracked release"
    assert not (destination / "2026-11-13").exists()


def test_pending_reviews_only_skip_exact_live_artifacts(tmp_path):
    from scripts.review_inventory import pending_specs, review_artifact

    day = tmp_path / "2026-11-14"
    day.mkdir()
    paths = [day / f"atlas-s{i}.json" for i in (1, 2)]
    for path in paths:
        path.write_text(json.dumps({"id": f"{day.name}-{path.stem}", "title": "Original"}))
    available = {review_artifact(paths[0])}
    assert pending_specs(paths, available) == [paths[1].as_posix()]
    paths[0].write_text(paths[0].read_text().replace("Original", "Revised"))
    assert pending_specs(paths, available) == [path.as_posix() for path in paths]


def test_review_verification_rejects_missing_audio_and_wrong_dimensions(tmp_path):
    import pytest
    from PIL import Image
    from scripts.verify_review import verify

    thumbnail = tmp_path / "thumb.jpg"
    Image.new("RGB", (16, 16)).save(thumbnail)
    spec = {"id": "atlas", "channel": "Counterfactual Atlas", "format": "short", "scenes": [{}]}
    pack = {**spec, "durationSec": 10}
    video = {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920}
    audio = {"codec_type": "audio", "codec_name": "aac"}
    probe = {"format": {"duration": "10.04"}, "streams": [video, audio]}
    verify(spec, pack, probe, thumbnail)
    with pytest.raises(ValueError, match="AAC"):
        verify(spec, pack, {**probe, "streams": [video]}, thumbnail)
    with pytest.raises(ValueError, match="dimensions"):
        verify(spec, pack, {**probe, "streams": [{**video, "width": 1920}, audio]}, thumbnail)


def test_review_gate_rejects_missing_or_null_automated_editorial_scores(tmp_path):
    import pytest
    from PIL import Image
    from scripts.verify_review import verify

    thumbnail = tmp_path / "thumb.jpg"
    Image.new("RGB", (8, 8)).save(thumbnail)
    spec = {"id": "atlas", "channel": "Counterfactual Atlas", "format": "short",
            "scenes": [{}], "meta": {"generator": "autopilot"}}
    pack = {"id": "atlas", "channel": "Counterfactual Atlas", "format": "short", "durationSec": 3.0}
    probe = {"format": {"duration": "3.0"}, "streams": [
        {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
        {"codec_type": "audio", "codec_name": "aac"}]}
    with pytest.raises(ValueError, match="editorial score"):
        verify(spec, pack, probe, thumbnail)
    spec["meta"]["review"] = {"hook": 8, "originality": 8, "accuracy": None}
    with pytest.raises(ValueError, match="accuracy"):
        verify(spec, pack, probe, thumbnail)
    spec["meta"]["review"]["accuracy"] = 8
    with pytest.raises(ValueError, match="editorial decision"):
        verify(spec, pack, probe, thumbnail)
    spec["meta"]["review"].update({"pass": True, "fixes": [], "unsupported_claims": []})
    verify(spec, pack, probe, thumbnail)


def test_review_audio_rejects_muted_and_missing_audio_stats(tmp_path, monkeypatch):
    import pytest
    import subprocess
    from scripts.verify_review import verify_audio

    video = tmp_path / "video.mp4"
    def fake_result(stderr):
        return subprocess.CompletedProcess([], 0, "", stderr)

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake_result(
        "mean_volume: -21.6 dB\nmax_volume: -2.0 dB\n"))
    assert verify_audio(video) == (-21.6, -2.0)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake_result(
        "mean_volume: -inf dB\nmax_volume: -inf dB\n"))
    with pytest.raises(ValueError, match="Silent"):
        verify_audio(video)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake_result("no measurements"))
    with pytest.raises(ValueError, match="Missing mean_volume"):
        verify_audio(video)


def test_review_rejects_silent_3d_and_image_fallbacks(tmp_path):
    import pytest
    from PIL import Image
    from scripts.verify_review import verify

    thumb = tmp_path / "thumb.jpg"
    Image.new("RGB", (40, 40)).save(thumb)
    spec = {"id": "atlas", "channel": "Counterfactual Atlas", "format": "short",
            "scenes": [{"show": {"type": "b3d", "scene": "orbit3d"}},
                       {"show": {"type": "image", "query": "full moon"}}]}
    pack = {"id": "atlas", "channel": "Counterfactual Atlas", "format": "short", "durationSec": 8}
    probe = {"format": {"duration": "8"}, "streams": [
        {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
        {"codec_type": "audio", "codec_name": "aac"}]}
    with pytest.raises(ValueError, match="3D scene"):
        verify(spec, pack, probe, thumb)
    pack["renderEvidence"] = {"b3dRequested": 1, "b3dRendered": 1, "imageFallbackScenes": [1]}
    with pytest.raises(ValueError, match="licensed image"):
        verify(spec, pack, probe, thumb)
    pack["renderEvidence"]["imageFallbackScenes"] = []
    with __import__("pytest").raises(ValueError, match="Image attribution"):
        verify(spec, pack, probe, thumb)
    credit = "File:Moon.jpg | NASA | Public domain | https://commons.wikimedia.org/wiki/File:Moon.jpg"
    pack["description"] = credit
    pack["renderEvidence"]["licensedImageAssets"] = [{"credit": credit, "author": "NASA", "license": "Public domain", "title": "File:Moon.jpg", "sourceUrl": "https://commons.wikimedia.org/wiki/File:Moon.jpg"}]
    verify(spec, pack, probe, thumb)


def test_editor_cannot_pass_scores_below_threshold(monkeypatch):
    planner = daily.Planner(llm_with(Scripted()))
    review = {"pass": True, "hook": 8, "originality": 6, "accuracy": 5, "fixes": [], "unsupported_claims": []}
    monkeypatch.setattr(planner, "_call", lambda *a, **k: review)
    result = planner.critic("Counterfactual Atlas", short_script(), {"text": ""})
    assert result["pass"] is False
    assert result["fixes"] == ["Improve accuracy: scored 5, needs 7"]


def test_pip_reach_moves_and_phone_state_changes():
    from types import SimpleNamespace
    from engine.pip import pip

    ctx = SimpleNamespace(W=270, H=375)
    frames = list(pip(ctx, 0.5, {"action": "reach"}, []))
    assert frames[0].tobytes() != frames[len(frames) // 2].tobytes()
    dead = next(pip(ctx, 0.5, {"action": "reset", "phone": "dead"}, []))
    assert frames[0].getpixel((205, 220)) != dead.getpixel((205, 220))


def test_pip_phone_stays_far_after_slip_and_dead_after_blackout():
    from engine.pip import continuity_issues

    def shot(action, **fields):
        return {"show": {"type": "pip", "action": action, **fields}}

    slip = shot("slip")
    far = shot("reach", phone="far")
    dead = shot("reset", phone="dead")
    assert not continuity_issues([slip, far, dead, dead])
    assert continuity_issues([slip, shot("reset")])
    assert continuity_issues([slip, dead, far])


def test_planner_fills_omitted_phone_state_but_preserves_explicit_errors():
    from engine.pip import continuity_issues, fill_phone_states

    shows = [{"action": "slip"}, {"action": "reach"}, {"action": "reset", "phone": "dead"},
             {"action": "reset"}, {"action": "reach", "phone": "near"}]
    scenes = [{"show": {"type": "pip", **show}} for show in shows]
    fill_phone_states(scenes)
    assert [scene["show"]["phone"] for scene in scenes] == ["near", "far", "dead", "dead", "near"]
    assert continuity_issues(scenes) == ["scene 4: phone continuity requires dead; far may transition to dead"]


def test_planning_fills_a_missing_slot_without_overwriting_an_existing_second_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "SPECS", tmp_path / "specs")
    monkeypatch.setattr(insights, "STATE", tmp_path / "state")
    date = dt.date(2026, 11, 14)
    folder = daily.SPECS / date.isoformat()
    folder.mkdir(parents=True)
    existing = folder / "atlas-s2.json"
    original = json.dumps({"channel": "Counterfactual Atlas", "format": "short"})
    existing.write_text(original)

    def make(self, channel, fmt, sid, when):
        if fmt == "long":
            return None
        return {"id": sid, "title": "Fresh short", "meta": {"axis": "space", "slot": "14:00"},
                "publishAt": when.isoformat()}

    monkeypatch.setattr(daily.Planner, "make", make)
    now = dt.datetime(2026, 11, 13, tzinfo=dt.timezone.utc)
    result = daily.plan([date], llm_with(Scripted()), now, only=["Counterfactual Atlas"])
    assert result["written"] == [str(folder / "atlas-s1.json")]
    assert existing.read_text() == original


def test_episode_budget_is_distinct_from_run_budget():
    import pytest

    llm = llm_with(Scripted())
    planner = daily.Planner(llm, max_calls=3)
    planner.episode_call_limit = 0
    with pytest.raises(daily.EpisodeCallLimit):
        planner._call("system", "user")
    planner.episode_call_limit = 4
    llm.calls = 3
    with pytest.raises(LLMError, match="call budget for this run") as error:
        planner._call("system", "user")
    assert not isinstance(error.value, daily.EpisodeCallLimit)


def test_inventory_reports_network_coverage_without_counting_invalid_specs(tmp_path, monkeypatch):
    monkeypatch.setattr(daily, "SPECS", tmp_path)
    day = dt.date(2026, 11, 14)
    folder = tmp_path / day.isoformat()
    folder.mkdir()
    spec = {"id": f"{day}-atlas-s2", "channel": "Counterfactual Atlas", "format": "short"}
    for name in ("atlas-s1", "atlas-s2"):
        (folder / f"{name}.json").write_text(json.dumps(spec))
    rows = daily.inventory([day])
    assert len({row["channel"] for row in rows}) == 48
    assert sum(row["target"] for row in rows) == 50
    assert sum(row["missing"] for row in rows) == 49


def test_extract_json_handles_fenced_script_with_trailing_bracketed_notes():
    reply = 'Draft follows:\n```json\n{"scenes": [{"say": "Hi"}]}\n```\n[notes] {unrelated}'
    assert extract_json(reply) == {"scenes": [{"say": "Hi"}]}
