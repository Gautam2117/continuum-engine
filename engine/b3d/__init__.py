"""Blender 3D shots for the engine.

The engine's own Python never imports bpy. It writes a job file and runs Blender's Python (`bpy`, Python 3.13)
as a subprocess, which renders PNG frames into a cache folder. If Blender is not installed, render_clip returns
None and the scene falls back to a 2D scene, so a missing Blender never breaks a render.

Environment:
  B3D_PYTHON   path to a Python that has `bpy` (default: try python3.13, then python3)
  B3D_ENGINE   WORKBENCH (fast clay look, default) | CYCLES (cinematic; GPU on Kaggle) | EEVEE
  B3D_SAMPLES  Cycles/EEVEE samples (default 16)
  B3D_CACHE    cache folder (default ~/.cache/continuum-b3d)
  B3D_OFF=1    never use Blender (always fall back)
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
MAIN = HERE / "blender_main.py"
KIT_FILES = ("blender_main.py", "clay.py", "titles.py")
SCENE_NAMES = ("earth_tunnel", "moon_drive", "everest_flood", "bars3d", "orbit3d", "fall3d", "clay", "title3d")
VERSION = "18"  # bump when blender_main.py changes in a way that should invalidate cached frames


@functools.lru_cache(maxsize=1)
def blender_python() -> str | None:
    if os.environ.get("B3D_OFF") == "1":
        return None
    cands = [os.environ.get("B3D_PYTHON"), "python3.13", "/tmp/bvenv/bin/python", sys.executable, "python3"]
    for c in cands:
        if not c:
            continue
        exe = shutil.which(c) or (c if os.path.exists(c) else None)
        if not exe:
            continue
        try:
            r = subprocess.run([exe, "-c", "import bpy; print(bpy.app.version_string)"],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                print(f"b3d: Blender {r.stdout.strip().splitlines()[-1]} via {exe}", file=sys.stderr, flush=True)
                return exe
        except Exception:  # noqa: BLE001
            continue
    return None


def available() -> bool:
    return blender_python() is not None


def render_clip(scene: str, params: dict, frames: int, size: tuple[int, int], palette: dict, fps: int = 24,
                engine: str | None = None) -> list[pathlib.Path] | None:
    """Render (or reuse) a clip. Returns one PNG path per output frame, or None if Blender is unavailable/failed."""
    py = blender_python()
    if py is None or scene not in SCENE_NAMES:
        return None
    engine = (engine or os.environ.get("B3D_ENGINE") or "WORKBENCH").upper()
    samples = int(os.environ.get("B3D_SAMPLES", "16"))
    step = int(params.get("step", 1 if engine == "WORKBENCH" else 2))
    job = {"scene": scene, "params": {k: v for k, v in params.items() if k != "step"}, "frames": int(frames), "fps": fps,
           "step": step, "size": list(size), "engine": engine, "samples": samples, "palette": palette, "v": VERSION}
    key = hashlib.sha1(json.dumps(job, sort_keys=True).encode()).hexdigest()[:16]
    root = pathlib.Path(os.environ.get("B3D_CACHE", pathlib.Path.home() / ".cache" / "continuum-b3d"))
    out = root / key
    if not (out / "done.json").exists():
        out.mkdir(parents=True, exist_ok=True)
        job["out"] = str(out)
        jp = out / "job.json"
        jp.write_text(json.dumps(job))
        print(f"b3d: rendering {scene} ({frames} frames, {engine}) → {out}", file=sys.stderr, flush=True)
        r = subprocess.run([py, str(MAIN), str(jp)], capture_output=True, text=True, timeout=60 * 60 * 3)
        for line in (r.stdout or "").splitlines():
            if line.startswith("b3d:"):
                print(line, file=sys.stderr, flush=True)
        if r.returncode != 0 or not (out / "done.json").exists():
            print(f"b3d: render failed ({r.returncode}):\n{(r.stderr or r.stdout)[-2000:]}", file=sys.stderr, flush=True)
            return None
    rendered = sorted(out.glob("f_*.png"))
    if not rendered:
        return None
    # Blender names frames by frame number; with step>1 each rendered frame is held for `step` output frames.
    by_num = {int(p.stem.split("_")[1]): p for p in rendered}
    seq, last = [], rendered[0]
    for f in range(1, frames + 1):
        last = by_num.get(f, last)
        seq.append(last)
    return seq


def anchors(seq: list[pathlib.Path]) -> dict:
    """Screen anchors written by the scene (normalised x, y per frame), scalars and label instructions."""
    f = seq[0].parent / "anchors.json"
    return json.loads(f.read_text()) if f.exists() else {"points": {}, "scalars": {}, "labels": []}


def load(path: pathlib.Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    return im if im.size == tuple(size) else im.resize(size, Image.LANCZOS)
