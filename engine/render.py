"""Render one spec to out/<id>/: video.mp4, thumb.jpg and pack.json (everything an upload needs).

Usage: python -m engine.render specs/2026-11-13/atlas-short.json [--out out] [--preview SECONDS]
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import wave

import numpy as np
from PIL import Image, ImageDraw

from . import emoji, stage
from .asset_rights import provenance
from . import scenes as S
from .fonts import font
from .pad import pad as ambient
from .styles import FOOTAGE_LED, rgb, style_for
from .tts import SR, speak

UA = "ContinuumEngine/1.0 (https://studio.continuumarc.tech; gautam@continuumarc.tech)"
SIZES = {"long": (1920, 1080), "short": (1080, 1920)}
# Science what-if scenes own the visual field; no repeated cartoon mascot overlay.
NO_MASCOT = frozenset({"atlas", "lowbat", "sienna", "aditi", "kiara"})
NO_STICKERS = frozenset({"atlas", "lowbat"})


def fetch_persona(p: dict, spec_id: str, scene_no: int) -> Image.Image | None:
    """A still of a disclosed AI persona (Sienna, Aditi, Kiara) from the private character-sheet set.

    The sheets live in a private Kaggle dataset, never in this public repo; the render workflow downloads them into
    PERSONA_DIR. `who` is sienna | aditi | kiara; `look` is portrait | outfit | place. A `_clean` copy of a file
    always wins over its original. Never fatal: without the images the scene falls back to a text scene."""
    import os
    import re
    folder = pathlib.Path(os.environ.get("PERSONA_DIR", ".cache/personas"))
    who = str(p.get("who", "")).lower()
    files = sorted(folder.glob(f"{who}_*.jp*g")) if who and folder.exists() else []
    stems = {f.stem for f in files}
    files = [f for f in files if not (f.stem + "_clean" in stems)]
    if str(p.get("look")) == "outfit":
        p["look"] = "portrait"  # head-and-shoulders only: full-body and outfit shots are not used in videos
    pats = {
        "portrait": r"_[a-z]\d+_(front|three_quarter|profile|laugh|wink|pout|surprise|eyeroll|softsmile|sideglance|annoyed|thoughtful|smirk|empathetic)",
        "outfit": r"_[a-z]\d+_(body_|festive|boutique|evening|street_style)",
    }
    pat = pats.get(str(p.get("look", "portrait")))
    if str(p.get("look")) == "place":
        pool = [f for f in files if not re.search(pats["portrait"], f.name.lower()) and not re.search(pats["outfit"], f.name.lower())]
    else:
        pool = [f for f in files if pat and re.search(pat, f.name.lower())]
    pool = pool or files
    if not pool:
        return None
    pick = pool[(sum(map(ord, spec_id)) + scene_no * 7) % len(pool)]
    try:
        p.setdefault("credit", "AI-generated persona")
        return Image.open(pick).convert("RGB")
    except Exception as e:  # noqa: BLE001
        print(f"  persona image unavailable ({e}); using a text scene", file=sys.stderr)
        return None


def fetch_image(p: dict) -> Image.Image | None:
    """Retrieve an explicitly commercial-use compatible Commons still and its credit.

    Do not fetch arbitrary model-supplied image_url addresses: they bypass licence
    validation and can be copyright-incompatible or point at internal services.
    """
    if p.get("image_url"):
        print("  unverified direct image URL blocked; provide a Wikimedia query", file=sys.stderr)
        return None
    query = p.get("query")
    if not isinstance(query, str) or not query.strip():
        return None
    try:
        q = urllib.parse.urlencode({
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"{query[:160]} filetype:bitmap", "gsrlimit": 8, "prop": "imageinfo",
            "iiprop": "url|extmetadata", "iiurlwidth": 2000,
        })
        req = urllib.request.Request(f"https://commons.wikimedia.org/w/api.php?{q}", headers={"User-Agent": UA})
        data = json.load(_open(req, 20))
        pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda x: x.get("index", 99))
        for page in pages:
            for info in page.get("imageinfo") or []:
                proof = provenance(page, info)
                if not proof:
                    continue
                req = urllib.request.Request(proof["downloadUrl"], headers={"User-Agent": UA})
                try:
                    payload = _open(req, 30).read(12 * 1024 * 1024 + 1)
                    if len(payload) > 12 * 1024 * 1024:
                        continue
                    with Image.open(io.BytesIO(payload)) as photo:
                        photo.load()
                        image = photo.convert("RGB")
                except (OSError, ValueError, TimeoutError, urllib.error.HTTPError):
                    continue
                p["credit"] = proof["credit"]
                p["assetProvenance"] = {k: v for k, v in proof.items() if k != "downloadUrl"}
                return image
        print("  no Commons image with verified commercial-use licence available", file=sys.stderr)
        return None
    except (OSError, ValueError, TimeoutError, urllib.error.URLError, KeyError) as error:
        print(f"  licensed image lookup unavailable ({error}); review held", file=sys.stderr)
        return None


def _open(req, timeout: int):
    """urlopen with polite retries on 429/5xx (Wikimedia rate limits bursts)."""
    import urllib.error
    for attempt in range(4):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s).strip()


def write_wav(path: pathlib.Path, audio: np.ndarray):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def thumbnail(spec: dict, style, path: pathlib.Path, image: Image.Image | None):
    W, H = 1280, 720
    bd = S.Backdrop(style, W, H, seed=hash(spec["id"]) % 1000)
    img = bd.frame(0).convert("RGBA")
    if image is not None:
        iw, ih = image.size
        sc = max(W * 0.55 / iw, H / ih)
        ph = image.convert("RGB").resize((int(iw * sc), int(ih * sc)))
        img.paste(ph.crop((0, 0, int(W * 0.55), H)), (int(W * 0.45), 0))
        fade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fade)
        for x in range(int(W * 0.25)):
            fd.line([(int(W * 0.45) + x, 0), (int(W * 0.45) + x, H)], fill=(*rgb(style.bg), int(255 * (1 - x / (W * 0.25)))))
        img.alpha_composite(fade)
    art = spec.get("thumb_art") == "earth" and image is None
    if art:  # drawn art instead of a stock image: the Earth in cross-section
        S.draw_earth(img, W * 0.76, H * 0.52, H * 0.40, style, 1.0)
    d = ImageDraw.Draw(img, "RGBA")
    hook = spec.get("thumb") or spec["title"]
    if style.caps_titles:
        hook = hook.upper()
    f, lines = S.fit_font(d, hook, style.display, int(W * (0.5 if (image is not None or art) else 0.84)), 128, 3, 48)
    y = H / 2 - len(lines) * f.size * 1.05 / 2
    for li, line in enumerate(lines):
        col = rgb(style.accent) if li == len(lines) - 1 else rgb(style.ink)
        d.text((64, y + li * f.size * 1.05), line, font=f, fill=col, stroke_width=4, stroke_fill=(0, 0, 0))
    d.rectangle([64, 48, 64 + 18, 48 + 18], fill=rgb(style.accent))
    d.text((96, 42), spec["channel"], font=font(style.body, 26), fill=rgb(style.muted))
    img.convert("RGB").save(path, quality=92)


def render(spec_path: pathlib.Path, out_root: pathlib.Path, preview: float | None = None) -> pathlib.Path:
    spec = json.loads(spec_path.read_text())
    style = style_for(spec["channel"])
    fmt = spec.get("format", "long")
    W, H = SIZES[fmt]
    out = out_root / spec["id"]
    out.mkdir(parents=True, exist_ok=True)
    started = time.time()

    # 1. Narration per scene; the scene lasts as long as its line (plus a beat).
    plan = []
    for sc in spec["scenes"]:
        text = sc.get("say", "").strip()
        audio = speak(text, style.voice, style.speed, style.lang) if text else np.zeros(int(SR * 0.4), np.float32)
        dur = max(float(sc.get("min", 2.4)), len(audio) / SR + float(sc.get("hold", 0.35)))
        plan.append((sc, audio, dur))
        if preview and sum(p[2] for p in plan) >= preview:
            break
    total = sum(p[2] for p in plan)
    print(f"{spec['id']}: {len(plan)} scenes, {total:.0f}s", flush=True)

    # 2. One continuous voice track, the ambient bed underneath.
    voice = np.zeros(int(total * SR) + SR, np.float32)
    cursor = 0.0
    for sc, audio, dur in plan:
        i = int(cursor * SR)
        voice[i:i + len(audio)] += audio
        cursor += dur
    bed = ambient(len(voice) / SR, style.pad, SR, seed=len(spec["id"]))
    sfx = np.zeros_like(voice)
    wh, pp = stage.whoosh(), stage.pop()
    cursor = 0.0
    for si, (sc, audio, dur) in enumerate(plan):
        if si:
            i = int((cursor - 0.02) * SR)
            sfx[i:i + len(wh)] += wh[: len(sfx) - i]
        if (sc.get("show") or {}).get("type") not in ("title", "end"):
            i = int((cursor + 0.28) * SR)
            sfx[i:i + len(pp)] += pp[: max(0, len(sfx) - i)]
        cursor += dur
    mix = voice * 0.95 + bed + sfx
    # gentle fade in/out
    fade = int(0.6 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    wav = out / "audio.wav"
    write_wav(wav, mix)

    # 3. Frames straight into ffmpeg.
    video = out / "video.mp4"
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(S.FPS), "-i", "-",
        "-i", str(wav),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24" if fmt == "long" else "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "160k", "-shortest", str(video),
    ], stdin=subprocess.PIPE)
    layout = stage.Layout(W, H, fmt, no_host=style.slug in NO_MASCOT)
    bd = S.Backdrop(style, W, H, seed=len(spec["id"]))
    ctx = S.Ctx(style, W, layout.view_h, bd, spec["channel"], vertical=layout.vertical)
    slug = style.slug
    from autopilot.directors import DIRECTORS
    direction = DIRECTORS.get(spec["channel"])
    first_image = None
    asset_provenance: list[dict] = []
    elapsed = 0.0
    prev_full = None
    b3d_requested = b3d_rendered = 0
    b3d_fallback_scenes: list[int] = []
    image_fallback_scenes: list[int] = []
    persona_fallback_scenes: list[int] = []
    for si, (sc, audio, dur) in enumerate(plan):
        show = dict(sc.get("show") or {"type": "say"})
        kind = show.pop("type")
        say = sc.get("say", "")
        words = say.split()
        ems = sc.get("emoji")
        ems = [ems] if isinstance(ems, str) else (ems if ems is not None else emoji.pick(say))
        # Unrelated stickers must not obscure Atlas physical diagrams.
        if slug in NO_STICKERS:
            ems = []
        if kind == "say" and ems:
            show["hero"], ems = ems[0], []
        if kind in ("title", "end"):
            ems = ems[:1]
        cfg = {"captions": not (slug == "drift" and fmt == "long"),
               "host": sc.get("host", True) and slug not in NO_MASCOT,
               "camera": direction.camera if direction else "push",
               "caption_mode": direction.captions if direction else "impact"}
        stg = stage.Scene(layout, style, slug, spec["channel"], kind, say, dur, audio, ems, cfg, first=(si == 0))
        fn = S.SCENES[kind]
        if kind in ("image", "persona"):
            im = fetch_persona(show, spec["id"], si) if kind == "persona" else fetch_image(show)
            first_image = first_image or im
            if im is None:
                (persona_fallback_scenes if kind == "persona" else image_fallback_scenes).append(si)
            elif kind == "image" and isinstance(show.get("assetProvenance"), dict):
                asset_provenance.append({"scene": si, **show["assetProvenance"]})
            frames = fn(ctx, dur, show, words, image=im)
        else:
            if kind == "b3d":
                b3d_requested += 1
            frames = fn(ctx, dur, show, words)
        for k, vframe in enumerate(frames):
            t = k / S.FPS
            view = stg.camera(vframe, t)
            stg.paint_stickers(view, t)
            if layout.vertical:
                full = bd.frame(t).convert("RGB")
                full.paste(view, (0, 0))
            else:
                full = view
            if prev_full is not None and t < 0.3:
                full = stage.push(prev_full, full, stage.ease(t / 0.3), layout.vertical)
            full = full.convert("RGBA")
            stg.paint_host(full, t, k)
            if stg.caps:
                stg.caps.draw(full, t)
            stage.progress_bar(full, style, (elapsed + t) / total, layout.vertical)
            out_frame = full.convert("RGB")
            ff.stdin.write(out_frame.tobytes())
        if kind == "b3d":
            if show.get("_rendered3d") is True:
                b3d_rendered += 1
            else:
                b3d_fallback_scenes.append(si)
        prev_full = out_frame
        elapsed += dur
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg failed")
    wav.unlink(missing_ok=True)

    # 4. Thumbnail and upload pack.
    thumbnail(spec, style, out / "thumb.jpg", first_image)
    links = spec.get("links") or []
    desc = spec.get("description", "").strip()
    if links:
        desc += "\n\n" + "\n".join(f"{l['label']}: {l['url']}" for l in links)
    credits = [asset["credit"] for asset in asset_provenance]
    if credits:
        desc += "\n\nImage attributions (Wikimedia Commons):\n" + "\n".join(dict.fromkeys(credits))
    pack = {
        "id": spec["id"],
        "channel": spec["channel"],
        "format": fmt,
        "title": spec["title"][:100],
        "description": desc[:5000],
        "tags": spec.get("tags", []),
        "publishAt": spec.get("publishAt"),
        "synthetic": True,  # voice is synthetic: declare it
        "madeForKids": False,
        "durationSec": round(total, 1),
        "renderEvidence": {
            "b3dRequested": b3d_requested, "b3dRendered": b3d_rendered,
            "b3dFallbackScenes": b3d_fallback_scenes,
            "imageFallbackScenes": image_fallback_scenes,
            "personaFallbackScenes": persona_fallback_scenes,
            "licensedImageAssets": asset_provenance,
        },
        "footageNeeded": spec["channel"] in FOOTAGE_LED,
    }
    (out / "pack.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False))
    print(f"  done in {time.time() - started:.0f}s → {video} ({video.stat().st_size / 1e6:.1f} MB)", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, default=pathlib.Path("out"))
    ap.add_argument("--preview", type=float, default=None, help="render only the first N seconds")
    a = ap.parse_args()
    for sp in a.specs:
        render(sp, a.out, a.preview)


if __name__ == "__main__":
    main()
