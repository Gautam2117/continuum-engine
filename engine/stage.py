"""The stage around every scene: camera, stickers, host character, captions, transitions, sound effects.

Scenes draw into a viewport. Stage composes the finished frame: on Shorts the viewport sits on top with
captions and the host underneath; on long-form the host sits in a corner and captions run along the bottom.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from . import emoji, host
from .fonts import font
from .styles import rgb

FPS = 24
SR = 24000


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def spring(t: float) -> float:
    """0 -> 1 with a little overshoot, for pop-in stickers."""
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return 1 - math.exp(-6 * t) * math.cos(10 * t)


# ---------- sound effects ----------
def whoosh(dur: float = 0.34) -> np.ndarray:
    n = int(SR * dur)
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    prev = 0.0
    for i in range(n):
        k = 0.02 + 0.28 * math.sin(math.pi * i / n)  # filter opens then closes
        prev += k * (noise[i] - prev)
        out[i] = prev
    env = np.sin(np.linspace(0, math.pi, n)) ** 1.5
    out = out * env
    return (out / (np.abs(out).max() or 1) * 0.16).astype(np.float32)


def pop(dur: float = 0.12) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 720 * np.exp(-t * 18) + 180
    out = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)
    return (out * 0.22).astype(np.float32)


# ---------- layout ----------
class Layout:
    def __init__(self, W: int, H: int, fmt: str, no_host: bool = False):
        self.W, self.H, self.fmt = W, H, fmt
        self.vertical = fmt == "short"
        self.view_h = (1500 if no_host else 1160) if self.vertical else H  # persona channels: no mascot, the picture takes the room
        self.cap_y = self.view_h + (70 if no_host else 95) if self.vertical else int(H * 0.88)
        self.host_size = 640 if self.vertical else 320
        self.host_xy = ((W - self.host_size) // 2, self.view_h + 90) if self.vertical else (W - self.host_size - 40, H - self.host_size - 28)


# ---------- captions ----------
class Captions:
    """Word-timed captions. One chunk on screen, always a single line that fits the safe width."""

    def __init__(self, layout: Layout, style, words: list[str], t0: float, t1: float, mode: str = "impact"):
        self.L, self.s, self.words, self.mode = layout, style, words, mode
        u = min(layout.W, layout.H) / 100
        scales = {"impact": 1.12, "minimal": .77, "documentary": .83, "ledger": .84, "typewriter": .90, "soft": .76}
        self.base = int(u * (7.4 if layout.vertical else 3.6) * scales.get(mode, 1.0))
        self.maxw = layout.W * (0.86 if layout.vertical else 0.62)
        self.limit = 3 if layout.vertical else 7
        weights = [len(w) + 1.5 + (5 if w[-1:] in ".?!," else 0) for w in words]
        tot = sum(weights) or 1
        a, edges = t0, []
        for w in weights:
            edges.append((a, a + (t1 - t0) * w / tot))
            a += (t1 - t0) * w / tot
        self.times = edges
        probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        measure_font = "DejaVu Sans Mono:style=Bold" if mode == "typewriter" else style.display
        self.chunks: list[tuple[int, int, int]] = []  # (start, end, font size)
        i = 0
        while i < len(words):
            j = i
            while j < len(words) and j - i < self.limit:
                trial = " ".join(self._txt(w) for w in words[i:j + 1])
                if j > i and probe.textlength(trial, font=font(measure_font, self.base)) + self.base > self.maxw:
                    break
                j += 1
                if words[j - 1][-1:] in ".?!;:" or (words[j - 1][-1:] == "," and j - i >= 2):
                    break
            j = max(j, i + 1)
            size = self.base
            txt = " ".join(self._txt(w) for w in words[i:j])
            while size > 18 and probe.textlength(txt, font=font(measure_font, size)) + size > self.maxw:
                size = int(size * 0.92)
            self.chunks.append((i, j, size))
            i = j

    def _txt(self, w: str) -> str:
        if self.mode in ("ledger", "typewriter"):
            return w.upper()
        return w.upper() if self.s.caps_titles else w

    def draw(self, img: Image.Image, t: float):
        if not self.words:
            return
        idx = len(self.words) - 1
        for k, (a, b) in enumerate(self.times):
            if t < b:
                idx = k
                break
        ci = next(k for k, (a, b, _) in enumerate(self.chunks) if a <= idx < b)
        a, b, size = self.chunks[ci]
        f = font("DejaVu Sans Mono:style=Bold", size) if self.mode == "typewriter" else font(self.s.display, size)
        d = ImageDraw.Draw(img, "RGBA")
        texts = [self._txt(w) for w in self.words[a:b]]
        space = d.textlength(" ", font=f)
        widths = [d.textlength(x, font=f) for x in texts]
        total = sum(widths) + space * (len(texts) - 1)
        k_in = ease((t - self.times[a][0]) / 0.14)
        x = (self.L.W - total) / 2
        y = self.L.cap_y - size * 0.6 + (1 - k_in) * size * 0.25
        sw = max(3, int(size * 0.09))
        pad = size * 0.16
        for j, (txt, w) in enumerate(zip(texts, widths)):
            active = a + j == idx
            if active and self.mode in ("impact", "ledger"):
                d.rounded_rectangle([x - pad, y - pad * 0.5, x + w + pad, y + size * 1.12 + pad * 0.2],
                                    radius=size * (0.05 if self.mode == "ledger" else .28), fill=(*rgb(self.s.accent), 255))
                d.text((x, y), txt, font=f, fill=rgb(self.s.bg))
            elif active:
                d.text((x, y), txt, font=f, fill=rgb(self.s.accent),
                       stroke_width=0 if self.mode == "soft" else max(1, sw // 2), stroke_fill=(0, 0, 0, 150))
                if self.mode == "typewriter":
                    d.line([(x, y + size * 1.03), (x + w, y + size * 1.03)], fill=rgb(self.s.accent), width=3)
            else:
                opacity = int((195 if self.mode in ("minimal", "soft") else 255) * k_in)
                d.text((x, y), txt, font=f, fill=(*rgb(self.s.ink), opacity),
                       stroke_width=sw if self.mode == "impact" else 1,
                       stroke_fill=(0, 0, 0, int(210 * k_in)))
            x += w + space


# ---------- per-scene composition ----------
class Scene:
    def __init__(self, layout: Layout, style, slug: str, channel: str, kind: str, text: str, dur: float,
                 audio: np.ndarray, stickers: list[str], cfg: dict, first: bool):
        self.L, self.s, self.slug, self.kind, self.dur, self.first = layout, style, slug, kind, dur, first
        n = int(dur * FPS)
        self.env = host.envelope(audio, SR, FPS, n)
        self.mood = host.mood_for(text, kind, slug == "drift")
        self.stickers = stickers
        self.show_host = cfg.get("host", True)
        self.camera_mode = cfg.get("camera", "push")
        self.caption_mode = cfg.get("caption_mode", "impact")
        words = text.split()
        self.caps = None
        if cfg.get("captions", True) and words and kind not in ("say", "title", "end"):
            self.caps = Captions(layout, style, words, 0.18, max(0.5, len(audio) / SR - 0.18), self.caption_mode)
        self.wave_at = 0.5 if ("!" in text or kind in ("number",)) else None

    def camera(self, view: Image.Image, t: float) -> Image.Image:
        """Camera choreography selected by the channel's independent director.

        Crop extents are always bounded; no border pixels or black bars are
        introduced. These are real rendered differences, not prompt-only names.
        """
        mode = self.camera_mode
        progress = max(0.0, min(1.0, t / max(self.dur, 0.001)))
        enter = 1 - ease(t / 0.32)
        x_motion, y_motion = 0.0, 0.0
        if mode == "hold":
            return view
        if mode == "snap":
            z = 1 + (0 if self.first else 0.085 * max(0, 1 - ease(t / .16)))
        elif mode == "pull":
            z = 1.075 - .07 * progress
        elif mode == "float":
            z = 1.026 + .012 * math.sin(progress * math.pi)
            x_motion = .72 * math.sin(progress * math.pi * 2)
            y_motion = .55 * math.sin(progress * math.pi)
        elif mode == "drift_left":
            z = 1.055
            x_motion = 1 - 2 * progress
        elif mode == "drift_right":
            z = 1.055
            x_motion = -1 + 2 * progress
        elif mode == "parallax":
            z = 1.05 + .012 * progress
            x_motion = .75 * math.sin(progress * math.pi * 1.25)
            y_motion = -.36 + .72 * progress
        elif mode == "orbit":
            z = 1.05
            x_motion = .82 * math.sin(progress * math.pi * 1.8)
            y_motion = .6 * math.cos(progress * math.pi * 1.8)
        elif mode == "tilt":
            z = 1.045
            x_motion = -.65 + 1.3 * progress
            y_motion = .5 - progress
        else:
            z = 1.0 + .035 * progress + (.07 * enter if not self.first else 0.0)
        if z <= 1.002:
            return view
        W, H = view.size
        w, h = max(1, int(W / z)), max(1, int(H / z))
        mx, my = W - w, H - h
        x = min(mx, max(0, int(mx * (.5 + x_motion * .5))))
        y = min(my, max(0, int(my * (.5 + y_motion * .5))))
        return view.crop((x, y, x + w, y + h)).resize((W, H), Image.BILINEAR)

    def paint_stickers(self, view: Image.Image, t: float):
        W, H = view.size
        slots = [(0.80, 0.14, 0.19), (0.84, 0.90, 0.14)] if self.L.vertical else [(0.88, 0.2, 0.12), (0.9, 0.5, 0.09)]
        for i, ch in enumerate(self.stickers[:2]):
            cx, cy, rel = slots[i]
            k = spring((t - 0.25 - i * 0.25) / 0.5)
            if k <= 0:
                continue
            size = int(W * rel * max(k, 0.05))
            sp = emoji.sprite(ch, max(8, size))
            if sp is None:
                continue
            sp = sp.rotate(math.sin(t * 2 + i) * 6, resample=Image.BICUBIC, expand=True)
            x = int(W * cx - sp.width / 2)
            y = int(H * cy - sp.height / 2 + math.sin(t * 2.6 + i * 2) * H * 0.008)
            view.paste(sp, (x, y), sp)

    def paint_host(self, full: Image.Image, t: float, i: int):
        if not self.show_host:
            return
        env = float(self.env[min(i, len(self.env) - 1)]) if len(self.env) else 0.0
        wave = 0.0
        if self.wave_at is not None and 0 < t - self.wave_at < 1.1:
            wave = math.sin(math.pi * (t - self.wave_at) / 1.1)
        h = host.draw(self.L.host_size, self.slug, self.s, t, env, self.mood, wave)
        x, y = self.L.host_xy
        if not self.L.vertical:
            pad = 18
            plate = Image.new("RGBA", full.size, (0, 0, 0, 0))
            ImageDraw.Draw(plate).rounded_rectangle([x - pad, y - pad, x + self.L.host_size + pad, y + self.L.host_size + pad], radius=40, fill=(*rgb(self.s.bg), 150))
            full.alpha_composite(plate)
        full.alpha_composite(h, (x, y))


def push(prev: Image.Image, cur: Image.Image, k: float, vertical: bool) -> Image.Image:
    """Slide the new frame in over the old one."""
    W, H = cur.size
    out = Image.new("RGB", (W, H))
    if vertical:
        off = int((1 - k) * H)
        out.paste(prev, (0, -int(k * H * 0.35)))
        out.paste(cur, (0, off))
    else:
        off = int((1 - k) * W)
        out.paste(prev, (-int(k * W * 0.35), 0))
        out.paste(cur, (off, 0))
    return out


def progress_bar(full: Image.Image, style, p: float, vertical: bool):
    d = ImageDraw.Draw(full, "RGBA")
    W, H = full.size
    th = 8 if vertical else 6
    y = 0 if vertical else H - th
    d.rectangle([0, y, W, y + th], fill=(255, 255, 255, 28))
    d.rectangle([0, y, int(W * p), y + th], fill=rgb(style.accent))
