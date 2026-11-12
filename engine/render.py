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
import wave

import numpy as np
from PIL import Image, ImageDraw

from . import scenes as S
from .fonts import font
from .pad import pad as ambient
from .styles import FOOTAGE_LED, rgb, style_for
from .tts import SR, speak

UA = "ContinuumEngine/1.0 (https://studio.continuumarc.tech; gautam@continuumarc.tech)"
SIZES = {"long": (1920, 1080), "short": (1080, 1920)}


def fetch_image(p: dict) -> Image.Image | None:
    """Public-domain / CC image from Wikimedia Commons by URL or search query. Never fatal."""
    url = p.get("image_url")
    try:
        if not url and p.get("query"):
            q = urllib.parse.urlencode({
                "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                "gsrsearch": f"{p['query']} filetype:bitmap", "gsrlimit": 5, "prop": "imageinfo",
                "iiprop": "url|extmetadata", "iiurlwidth": 2000,
            })
            req = urllib.request.Request(f"https://commons.wikimedia.org/w/api.php?{q}", headers={"User-Agent": UA})
            data = json.load(_open(req, 20))
            pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda x: x.get("index", 99))
            for pg in pages:
                info = (pg.get("imageinfo") or [{}])[0]
                meta = info.get("extmetadata", {})
                lic = (meta.get("LicenseShortName", {}).get("value") or "").lower()
                if any(ok in lic for ok in ("public domain", "cc0", "cc by", "pd")):
                    url = info.get("thumburl") or info.get("url")
                    artist = meta.get("Artist", {}).get("value", "")
                    p.setdefault("credit", f"Wikimedia Commons · {lic.upper()}" + (f" · {strip_html(artist)[:60]}" if artist else ""))
                    break
        if not url:
            return None
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return Image.open(io.BytesIO(_open(req, 30).read()))
    except Exception as e:  # noqa: BLE001 — an image is never worth failing a render
        print(f"  image unavailable ({e}); using a text scene", file=sys.stderr)
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
    d = ImageDraw.Draw(img, "RGBA")
    hook = spec.get("thumb") or spec["title"]
    if style.caps_titles:
        hook = hook.upper()
    f, lines = S.fit_font(d, hook, style.display, int(W * (0.5 if image is not None else 0.84)), 128, 3, 48)
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
    mix = voice * 0.95 + bed
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
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "160k", "-shortest", str(video),
    ], stdin=subprocess.PIPE)
    bd = S.Backdrop(style, W, H, seed=len(spec["id"]))
    ctx = S.Ctx(style, W, H, bd, spec["channel"])
    first_image = None
    for sc, audio, dur in plan:
        show = dict(sc.get("show") or {"type": "say"})
        kind = show.pop("type")
        words = sc.get("say", "").split()
        fn = S.SCENES[kind]
        if kind == "image":
            im = fetch_image(show)
            first_image = first_image or im
            frames = fn(ctx, dur, show, words, image=im)
        else:
            frames = fn(ctx, dur, show, words)
        n = int(dur * S.FPS)
        cap = fmt == "short" and kind not in ("say", "title", "end")
        for k, frame in enumerate(frames):
            if cap:
                frame = S.captions(frame, ctx, words, min(1.0, k / max(1, n) * 1.05))
            ff.stdin.write(frame.tobytes())
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
    credits = [sc["show"].get("credit") for sc, _, _ in plan if (sc.get("show") or {}).get("credit")]
    if credits:
        desc += "\n\nImages: " + "; ".join(dict.fromkeys(credits))
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
