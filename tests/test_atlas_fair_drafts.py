"""Fairness and auditability for local Atlas model attempts."""
import datetime as dt
import json
from types import SimpleNamespace

import pytest

from autopilot import daily
from autopilot.llm import LLM, OllamaProvider

UTC = dt.timezone.utc


def test_seven_day_cycle_visits_all_dates_and_both_video_formats():
    days = [dt.date(2026, 11, 15) + dt.timedelta(days=i) for i in range(7)]
    start = dt.datetime(2026, 11, 14, 0, tzinfo=UTC)
    fronts = []
    orders = set()
    for i in range(28):
        ordered, formats = daily.atlas_cycle_order(days, start + dt.timedelta(minutes=i*15))
        assert set(ordered) == set(days)
        assert len(ordered) == len(days)
        fronts.append(ordered[0])
        orders.add(formats)
    assert set(fronts) == set(days)
    assert fronts.count(days[0]) == 14
    assert orders == {("short", "long"), ("long", "short")}
    assert daily.atlas_cycle_order([], start) == ([], ("short", "long"))


def test_date_order_requires_aware_clock():
    with pytest.raises(ValueError):
        daily.atlas_cycle_order([dt.date(2026,11,15)], dt.datetime(2026,11,14))


def test_local_model_budget_preserves_multiple_episode_opportunities():
    offline = SimpleNamespace(providers=[object.__new__(OllamaProvider)])
    remote = SimpleNamespace(providers=[object()])
    assert daily.episode_call_allowance("Counterfactual Atlas", "short", offline) == 9
    assert daily.episode_call_allowance("Counterfactual Atlas", "long", offline) == 12
    assert daily.episode_call_allowance("Counterfactual Atlas", "short", remote) == 18
    assert daily.episode_call_allowance("Foundbeam", "long", offline) == 36


def test_rejected_structurally_valid_draft_is_not_publishable(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTINUUM_STATE_DIR", str(tmp_path / "state"))
    planner = daily.Planner(LLM(providers=[]), max_calls=5)
    spec = {"id":"2026-11-15-atlas-s1", "channel":"Counterfactual Atlas",
            "format":"short", "title":"A draft", "meta":{}, "scenes":[{"say":"a scene"}]}
    review = {"hook":8,"originality":7,"accuracy":2,
              "fixes":["Correct the tide scaling"],"unsupported_claims":["Eightfold sea height"]}
    planner.hold_for_independent_edit(spec, review)
    held = tmp_path/"state"/"editorial_holds"/"2026-11-15-atlas-s1.json"
    assert held.is_file()
    saved=json.loads(held.read_text())
    assert saved["meta"]["review"]["pass"] is False
    assert saved["meta"]["reviewStatus"]=="MODEL_REJECTED_DRAFT_INDEPENDENT_EDIT_REQUIRED"
    assert saved["meta"]["review"]["unsupported_claims"] == ["Eightfold sea height"]
    assert spec.get("meta") == {}
    assert list((tmp_path / "state").rglob("*.json")) == [held]
