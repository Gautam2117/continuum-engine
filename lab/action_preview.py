"""Contact sheet of one scene: python -m lab.action_preview plunge '{"d0":0}' --long --dur 8 --out x.png [--times 0.05,0.3,...]"""
import argparse, json, pathlib
from PIL import Image, ImageDraw
from engine import scenes as S
from engine.styles import style_for

ap = argparse.ArgumentParser()
ap.add_argument("kind"); ap.add_argument("params", nargs="?", default="{}")
ap.add_argument("--dur", type=float, default=8.0); ap.add_argument("--short", action="store_true")
ap.add_argument("--times", default="0.02,0.2,0.4,0.6,0.8,0.98"); ap.add_argument("--out", default="/home/claude/work/prev/scene.png")
a = ap.parse_args()
W, H, VH = (1080, 1920, 1160) if a.short else (1920, 1080, 1080)
style = style_for("Counterfactual Atlas")
bd = S.Backdrop(style, W, H, seed=3)
ctx = S.Ctx(style, W, VH, bd, "Counterfactual Atlas", vertical=a.short)
params = json.loads(a.params)
frames = list(S.SCENES[a.kind](ctx, a.dur, params, "this is a sample narration line for the preview".split()))
ts = [float(x) for x in a.times.split(",")]
cols = 3
th = (480, 270) if not a.short else (270, 290)
sheet = Image.new("RGB", (cols * th[0], ((len(ts) + cols - 1) // cols) * th[1]), (0, 0, 0))
for i, f in enumerate(ts):
    fr = frames[min(len(frames) - 1, int(f * len(frames)))]
    sheet.paste(fr.resize(th), ((i % cols) * th[0], (i // cols) * th[1]))
sheet.save(a.out)
print(len(frames), "frames ->", a.out)
