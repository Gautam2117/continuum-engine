"""Physics checks and a smoke render of every motion scene, long-form and vertical."""
import json
import math
import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import physics as PH  # noqa: E402
from engine import scenes as S  # noqa: E402
from engine.spec_check import problems  # noqa: E402
from engine.styles import style_for  # noqa: E402


def test_uniform_half_period_is_42_minutes():
    assert abs(PH.HALF_PERIOD / 60 - 42.2) < 0.05
    mid_x, mid_v = PH.uniform_state(0.5)
    assert abs(mid_x) < 1e-9
    assert abs(mid_v - 7905) < 30          # about 7.9 km/s at the centre, the surface orbital speed


def test_layered_model_is_faster_than_uniform():
    layered = PH.layered_half_seconds() / 60
    assert 38.0 < layered < 40.0
    assert layered < PH.HALF_PERIOD / 60


def test_straight_chord_time_is_independent_of_length():
    times = []
    for theta in (0.3, 1.2, 2.4, math.pi):
        s = (1 - np.cos(np.linspace(0, math.pi, 8000))) / 2          # cosine spacing resolves the slow ends
        a, b = np.array([1.0, 0.0]), np.array([math.cos(theta), math.sin(theta)])
        pts = a * (1 - s)[:, None] + b * s[:, None]
        times.append(PH.path_times(pts)[-1] / 60)
    assert max(times) - min(times) < 0.3
    assert abs(times[-1] - 42.2) < 0.3


def test_hypocycloid_beats_the_straight_tunnel():
    theta = math.radians(70)
    s = (1 - np.cos(np.linspace(0, math.pi, 20000))) / 2
    a, b = np.array([1.0, 0.0]), np.array([math.cos(theta), math.sin(theta)])
    straight = PH.path_times(a * (1 - s)[:, None] + b * s[:, None])[-1] / 60
    curved = PH.path_times(PH.hypocycloid(theta, 20000))[-1] / 60
    assert curved < straight
    assert abs(curved - 33.4) < 0.5


KINDS = {
    "plunge": {"d0": 0, "d1": 3000, "labels": True, "shield": True, "air": True, "speedo": {"cap": 200, "ghost": 28000}},
    "journey": {"mode": "race", "racers": [{"label": "car", "kmh": 100, "kind": "car"}, {"label": "jet", "kmh": 900, "kind": "jet"}]},
    "pips": {"days": 40},
    "tank": {"litres": 5000},
    "descent": {"mode": "ocean", "mountain": True, "bracket": True, "sub": {"at": 0.1, "for": 0.6, "to": 2086}},
    "columns": {"items": [{"label": "Everest", "value": 8.849, "dir": "up", "kind": "mountain"}, {"label": "Deep", "value": 10.935, "dir": "down", "kind": "water"}]},
    "seismic": {}, "scale": {}, "shell": {}, "gravity": {"curves": ["uniform", "real"]},
    "earthfall": {"model": "race"}, "chords": {"train": True, "chords": [[172, 352]], "labels": ["A", "B"]},
    "lap": {}, "brachi": {"theta": 70}, "spin": {}, "flood": {},
    "seq": {"parts": [{"w": 1, "show": {"type": "pips", "days": 10}}, {"w": 1, "show": {"type": "tank", "litres": 2000}}]},
}


@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("vertical", [False, True])
def test_scene_renders_and_moves(kind, vertical):
    W, H, VH = (1080, 1920, 1160) if vertical else (1920, 1080, 1080)
    style = style_for("Counterfactual Atlas")
    ctx = S.Ctx(style, W, VH, S.Backdrop(style, W, H, seed=3), "Counterfactual Atlas", vertical=vertical)
    frames = list(S.SCENES[kind](ctx, 2.0, dict(KINDS[kind]), "a few words to speak".split()))
    assert len(frames) == 48
    assert frames[0].size[0] == W
    first, mid = np.asarray(frames[2]), np.asarray(frames[len(frames) // 2])
    assert np.abs(first.astype(int) - mid.astype(int)).sum() > 0      # something visibly changes


@pytest.mark.parametrize("name", ["atlas-l1", "atlas-s1", "atlas-s2"])
def test_atlas_specs_pass_strict_checks(name):
    spec = json.loads((ROOT / "specs" / "2026-11-14" / f"{name}.json").read_text())
    assert problems(spec) == []
    kinds = [sc["show"]["type"] for sc in spec["scenes"]]
    assert len(set(kinds)) >= 3 and kinds[-1] == "end"
