# Kaggle GPU render

`.github/workflows/render-kaggle.yml` pushes `kaggle/render/script.py` to a private Kaggle notebook
(`<KAGGLE_USERNAME>/continuum-render`) with GPU and internet on. The notebook clones this repo at the
workflow's commit, installs the engine plus Blender (bpy on Python 3.13 via uv), renders the given specs with
Cycles on the GPU, and the workflow downloads `out/` and attaches it to the date's release like render.yml does.

One-time setup (account owner):
1. Kaggle → Settings → Phone verification (GPU and internet in notebooks need a verified phone).
2. Kaggle → Settings → API → Create New Token. It downloads kaggle.json with "username" and "key".
3. GitHub → this repo → Settings → Secrets and variables → Actions: add `KAGGLE_USERNAME` and `KAGGLE_KEY`.
Then: Actions → "Render on Kaggle GPU" → Run workflow → specs = space-separated spec paths.
