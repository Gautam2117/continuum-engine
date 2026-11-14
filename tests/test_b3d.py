"""3D (Blender) scenes: spec checks always run; real renders run only where Blender's bpy is installed."""
import os

import pytest

from engine import b3d
from engine import scenes as S
from engine.spec_check import problems
from engine.styles import style_for


def _spec(show):
    return {"id": "2026-11-14-x", "channel": "Counterfactual Atlas", "format": "short", "title": "t", "description": "d",
            "scenes": [{"say": "Hello there.", "show": show}, {"say": "Bye.", "show": {"type": "end", "text": "x"}}]}


def test_b3d_registered():
    assert "b3d" in S.SCENES


def test_spec_check_knows_3d_scenes():
    assert not [p for p in problems(_spec({"type": "b3d", "scene": "earth_tunnel"})) if "3D" in p or "b3d" in p]
    assert any("unknown 3D scene" in p for p in problems(_spec({"type": "b3d", "scene": "nope"})))
    assert any("needs scene" in p for p in problems(_spec({"type": "b3d"})))
    assert any("fallback" in p for p in problems(_spec({"type": "b3d", "scene": "earth_tunnel", "fallback": {"type": "zzz"}})))


def test_new_scene_names_known():
    for n in ("bars3d", "orbit3d", "fall3d"):
        assert n in b3d.SCENE_NAMES


def test_harmonic_readout_matches_capsule():
    from engine.scene3d import _progress
    p = {"params": {"t0": 0.0, "t1": 0.5}}
    assert _progress("harmonic", 0.0, p) == 0.0
    assert abs(_progress("harmonic", 1.0, p) - 1.0) < 1e-9
    # halfway in time, a harmonic fall has covered 1 - cos(pi/4) ≈ 29% of the depth
    assert abs(_progress("harmonic", 0.5, p) - 0.2929) < 1e-3


def test_falls_back_without_blender(monkeypatch):
    monkeypatch.setenv("B3D_OFF", "1")
    b3d.blender_python.cache_clear()
    b3d.blender_runner.cache_clear()
    st = style_for("Counterfactual Atlas")
    bd = S.Backdrop(st, 216, 232)
    c = S.Ctx(st, 216, 232, bd, "Counterfactual Atlas", vertical=True)
    frames = list(S.SCENES["b3d"](c, 0.5, {"scene": "earth_tunnel", "fallback": {"type": "title", "text": "Hi"}}, ["hi"]))
    assert frames and frames[0].size == (216, 232)
    b3d.blender_python.cache_clear()
    b3d.blender_runner.cache_clear()


@pytest.mark.skipif(os.environ.get("B3D_TEST") != "1", reason="set B3D_TEST=1 where Blender's bpy is installed")
@pytest.mark.parametrize("scene", b3d.SCENE_NAMES)
def test_real_render(scene, tmp_path, monkeypatch):
    monkeypatch.setenv("B3D_CACHE", str(tmp_path))
    b3d.blender_python.cache_clear()
    pal = {"bg": "#05070f", "panel": "#0c1a33", "ink": "#eef4ff", "accent": "#5ee1ff"}
    seq = b3d.render_clip(scene, {}, 4, (120, 128), pal)
    assert seq and len(seq) == 4
    a, b = b3d.load(seq[0], (120, 128)), b3d.load(seq[-1], (120, 128))
    assert a.tobytes() != b.tobytes()  # something moved
    anc = b3d.anchors(seq)
    for L in anc["labels"]:  # every label points at an anchor that was exported for every frame
        assert len(anc["points"][L["anchor"]]) == 4
