from itertools import islice

from engine.scenes import Backdrop, Ctx, SCENES
from engine.styles import STYLES


def test_tide_is_a_self_contained_original_animated_schematic():
    assert "tide" in SCENES
    style = STYLES["atlas"]
    w, h = 360, 500
    ctx = Ctx(style, w, h, Backdrop(style, w, h, seed=4), "Counterfactual Atlas")
    frames = list(islice(SCENES["tide"](ctx, .5, {"title":"Coasts reshape the tide"}, []), 12))
    assert len(frames) == 12
    assert all(frame.size == (w, h) and frame.mode == "RGB" for frame in frames)
    assert frames[0].tobytes() != frames[8].tobytes()
