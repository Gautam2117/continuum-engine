"""`b3d` scenes: real 3D shots rendered by Blender (engine/b3d), with the channel's HUD drawn on top.

Spec:
  {"type": "b3d", "scene": "earth_tunnel", "params": {...},
   "hud":   {"label": "DEPTH", "from": 0, "to": 6371, "unit": "km", "law": "harmonic"},   # law: ease|linear|harmonic
   "clock": {"from": 0, "to": 1266},                       # seconds, shown as m:ss (linear); "unit": "days"|"hours"
   "title": {"text": "What if you fell through the Earth?", "hl": "fell"},
   "fallback": {"type": "plunge", ...}}                     # 2D scene used when Blender is unavailable

The HUD numbers ease with the shot, so the number on screen always matches the motion.
"""
from __future__ import annotations

from typing import Iterator

from PIL import Image, ImageDraw, ImageFilter

from . import b3d
from .fonts import font
from .scenes import FPS, Ctx, ease, shown, wrap
from .styles import rgb


def _fmt_clock(sec: float) -> str:
    sec = max(0, int(round(sec)))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _num(v: float, decimals: int) -> str:
    return f"{v:,.{decimals}f}" if decimals else f"{int(round(v)):,}"


def _progress(law: str, tau: float, p: dict) -> float:
    """0..1 progress of a readout at shot time tau (0..1). The law must match the motion in the shot:
    linear = constant rate (clocks), ease = smooth start and stop, harmonic = the fall through a uniform Earth
    (depth = R(1 - cos(pi*s)) with s running t0..t1, the same formula the 3D capsule follows)."""
    import math
    if law == "linear":
        return tau
    if law == "harmonic":
        prm = p.get("params") or {}
        t0, t1 = float(prm.get("t0", 0.0)), float(prm.get("t1", 0.5))
        f = lambda s: 1 - math.cos(math.pi * s)  # noqa: E731
        a, b = f(t0), f(t1)
        return 0.0 if b == a else (f(t0 + (t1 - t0) * tau) - a) / (b - a)
    return ease(tau)


def _panel(img: Image.Image, box, radius, fill, alpha):
    """Frosted panel: blur what is behind it, then tint."""
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    if x1 <= x0 or y1 <= y0:
        return
    region = img.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(12))
    mask = Image.new("L", region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, region.width - 1, region.height - 1], radius=radius, fill=255)
    img.paste(region, (x0, y0), mask)
    ImageDraw.Draw(img, "RGBA").rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(*fill, alpha))


def scene_b3d(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    n = max(1, int(dur * FPS))
    pal = {"bg": s.bg, "panel": s.bg2, "ink": s.ink, "accent": s.accent}
    clip = b3d.render_clip(p.get("scene", ""), dict(p.get("params") or {}), n, (c.W, c.H), pal, fps=FPS)
    if clip is None:
        from .scenes import SCENES
        fb = dict(p.get("fallback") or {"type": "say"})
        kind = fb.pop("type", "say")
        yield from SCENES[kind](c, dur, fb, words)
        return
    acc, ink, muted = rgb(s.accent), rgb(s.ink), rgb(s.muted)
    hud, clock, title = p.get("hud"), p.get("clock"), p.get("title")
    big = font(s.display, int(c.u * (9.5 if c.vertical else 6.2)))
    unit_f = font(s.display, int(c.u * (3.6 if c.vertical else 2.4)))
    lab_f = font(s.body, int(c.u * (2.9 if c.vertical else 1.8)))
    clk_f = font(s.display, int(c.u * (6.0 if c.vertical else 3.8)))
    serif = font("Caladea:style=Bold", int(c.u * (6.4 if c.vertical else 4.2)))
    m = c.margin
    title_lines = []
    if title:
        tmp = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        title_lines = wrap(tmp, title["text"], serif, int(c.W * (0.84 if c.vertical else 0.6)))
    for k in range(n):
        t = k / FPS
        tau = k / max(1, n - 1)
        img = b3d.load(clip[k], (c.W, c.H))
        d = ImageDraw.Draw(img, "RGBA")
        fade_in = min(1.0, t / 0.45)
        # title: serif question, one word in the accent colour, top of frame
        if title_lines:
            a = int(255 * fade_in * (1.0 if t < dur - 0.4 else max(0.0, (dur - t) / 0.4)))
            y = m * (1.9 if c.vertical else 1.4)
            hl = (title.get("hl") or "").lower().strip(".,?!")
            for line in title_lines:
                lw = d.textlength(line, font=serif)
                x = (c.W - lw) / 2
                for i, w in enumerate(line.split(" ")):
                    col = acc if hl and w.lower().strip(".,?!") == hl else ink
                    d.text((x + 3, y + 3), w, font=serif, fill=(0, 0, 0, int(a * 0.55)))
                    d.text((x, y), w, font=serif, fill=(*col, a))
                    x += d.textlength(w + " ", font=serif)
                y += serif.size * 1.12
        # counter panel bottom-left
        if hud:
            v = float(hud.get("from", 0)) + (float(hud.get("to", 0)) - float(hud.get("from", 0))) * _progress(hud.get("law", "ease"), tau, p)
            txt = _num(v, int(hud.get("decimals", 0)))
            unit = hud.get("unit", "")
            tw = max(d.textlength(txt, font=big) + (d.textlength(" " + unit, font=unit_f) if unit else 0),
                     d.textlength(hud.get("label", "").upper(), font=lab_f))
            pw, ph = tw + c.u * 5, big.size * 1.0 + lab_f.size * 2.2
            x0, y1 = m * 0.8, c.H - m * (1.2 if c.vertical else 1.0)
            _panel(img, (x0, y1 - ph, x0 + pw, y1), c.u * 1.6, rgb(s.bg), int(150 * fade_in))
            d = ImageDraw.Draw(img, "RGBA")
            al = int(255 * fade_in)
            d.text((x0 + c.u * 2.5, y1 - ph + c.u * 1.2), hud.get("label", "").upper(), font=lab_f, fill=(*muted, al))
            d.text((x0 + c.u * 2.5, y1 - big.size * 1.12 - c.u * 0.6), txt, font=big, fill=(*acc, al))
            if unit:
                d.text((x0 + c.u * 2.5 + d.textlength(txt + " ", font=big) * 0.98, y1 - unit_f.size * 1.55 - c.u * 0.6), unit, font=unit_f, fill=(*ink, al))
        # clock panel bottom-right
        if clock:
            sec = float(clock.get("from", 0)) + (float(clock.get("to", 0)) - float(clock.get("from", 0))) * _progress(clock.get("law", "linear"), tau, p)
            cu_ = clock.get("unit")
            txt = f"{sec / 86400:,.0f} days" if cu_ == "days" else (f"{sec / 3600:,.0f} h" if cu_ == "hours" else _fmt_clock(sec))
            tw = max(d.textlength(txt, font=clk_f), d.textlength(clock.get("label", "ELAPSED").upper(), font=lab_f))
            pw, ph = tw + c.u * 4.5, clk_f.size * 1.0 + lab_f.size * 2.2
            x1, y1 = c.W - m * 0.8, c.H - m * (1.2 if c.vertical else 1.0)
            _panel(img, (x1 - pw, y1 - ph, x1, y1), c.u * 1.6, rgb(s.bg), int(150 * fade_in))
            d = ImageDraw.Draw(img, "RGBA")
            al = int(255 * fade_in)
            d.text((x1 - pw + c.u * 2.2, y1 - ph + c.u * 1.2), clock.get("label", "ELAPSED").upper(), font=lab_f, fill=(*muted, al))
            d.text((x1 - pw + c.u * 2.2, y1 - clk_f.size * 1.12 - c.u * 0.6), txt, font=clk_f, fill=(*ink, al))
        yield img


SCENES = {"b3d": scene_b3d}
