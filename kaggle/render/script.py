"""Runs on a Kaggle GPU notebook (pushed by .github/workflows/render-kaggle.yml).

Clones this public repo at a fixed commit, installs the engine and Blender (bpy needs Python 3.13, so uv fetches
one), renders the listed specs with Cycles on the GPU, and leaves out/ in /kaggle/working for the workflow to collect.
REPO_SHA and SPECS are filled in by the workflow before the push. No secrets live in this file.
"""
import os
import subprocess
import sys

REPO = "https://github.com/Gautam2117/continuum-engine"
REPO_SHA = "__REPO_SHA__"
SPECS = "__SPECS__".split()
W = "/kaggle/working"


def sh(cmd, **kw):
    print("+", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True, **kw)


sh(f"git clone -q {REPO} {W}/ce && cd {W}/ce && git checkout -q {REPO_SHA}")
sh("apt-get update -qq && apt-get install -y -qq ffmpeg fonts-inter fonts-crosextra-caladea fonts-dejavu-core "
   "fonts-noto-core fonts-noto-color-emoji libegl1 libxkbcommon0 libsm6 libxi6 libxrender1 libxxf86vm1 libxfixes3 > /dev/null")
sh(f"{sys.executable} -m pip install -q -r {W}/ce/requirements.txt")
sh(f"{sys.executable} -m pip install -q uv && uv venv -q -p 3.13 {W}/bvenv && VIRTUAL_ENV={W}/bvenv uv pip install -q bpy==5.3.0")
env = dict(os.environ, B3D_PYTHON=f"{W}/bvenv/bin/python", B3D_ENGINE="CYCLES", B3D_SAMPLES=os.environ.get("B3D_SAMPLES", "48"),
           B3D_CACHE=f"{W}/b3dcache")
sh(f"cd {W}/ce && {sys.executable} -m engine.render {' '.join(SPECS)} --out {W}/out", env=env)
sh(f"rm -rf {W}/ce {W}/bvenv {W}/b3dcache")
print("done", flush=True)
