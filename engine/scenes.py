"""Scene renderers. Each scene yields PIL frames for its duration, drawn over the channel's backdrop.

Coordinates scale from the shorter side, so every scene works in 16:9 long-form and 9:16 Shorts.
"""
from __future__ import annotations

import math
import random
from typing import Iterator

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import emoji as _emoji
from .fonts import font
from .styles import Style, rgb

FPS = 24


# ---------- helpers ----------
def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_io(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_font(draw, text: str, pattern: str, width: int, max_size: int, max_lines: int, min_size: int = 20):
    size = max_size
    while size > min_size:
        f = font(pattern, size)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines:
            return f, lines
        size = int(size * 0.92)
    f = font(pattern, min_size)
    return f, wrap(draw, text, f, width)


def compact(n: float) -> str:
    a = abs(n)
    for div, s in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div * 10:
            return f"{n / div:,.0f}{s}"
    if a >= 100:
        return f"{n:,.0f}"
    if a >= 10:
        return f"{n:,.1f}".rstrip("0").rstrip(".")
    return f"{n:,.2f}".rstrip("0").rstrip(".")


def shown(n: float) -> str:
    """A number as people read it: 10,935 not 11K; 8.85 not 8.8500."""
    a = abs(n)
    if a >= 1e6:
        return compact(n)
    if a >= 100:
        return f"{n:,.0f}"
    if a >= 10:
        return f"{n:,.1f}".rstrip("0").rstrip(".")
    return f"{n:,.2f}".rstrip("0").rstrip(".")


class Backdrop:
    """The channel's background: gradient + motif, slightly larger than the frame so it can drift."""

    def __init__(self, style: Style, W: int, H: int, seed: int = 1):
        self.W, self.H, self.style = W, H, style
        m = int(min(W, H) * 0.06)
        self.m = m
        bw, bh = W + 2 * m, H + 2 * m
        y = np.linspace(0, 1, bh)[:, None]
        x = np.linspace(0, 1, bw)[None, :]
        c1, c2 = np.array(rgb(style.bg), float), np.array(rgb(style.bg2), float)
        mix = np.clip(0.55 * y + 0.45 * (1 - np.hypot(x - 0.7, y - 0.25)), 0, 1)[..., None]
        arr = c1 * (1 - mix) + c2 * mix
        rng = np.random.default_rng(seed)
        img = Image.fromarray(arr.astype(np.uint8), "RGB")
        d = ImageDraw.Draw(img, "RGBA")
        ink = rgb(style.ink)
        if style.motif == "stars":
            for _ in range(int(bw * bh / 2600)):
                r = rng.choice([1, 1, 1, 2])
                px, py = rng.integers(0, bw), rng.integers(0, bh)
                d.ellipse([px, py, px + r, py + r], fill=(*ink, int(rng.integers(40, 170))))
        elif style.motif == "grid":
            step = int(min(W, H) / 14)
            for gx in range(0, bw, step):
                d.line([(gx, 0), (gx, bh)], fill=(*ink, 14), width=1)
            for gy in range(0, bh, step):
                d.line([(0, gy), (bw, gy)], fill=(*ink, 14), width=1)
        elif style.motif == "scan":
            for gy in range(0, bh, 4):
                d.line([(0, gy), (bw, gy)], fill=(0, 0, 0, 40), width=1)
        noise_amt = {"paper": 20, "film": 16, "grain": 10}.get(style.motif, 6)
        noise = rng.normal(0, noise_amt, (bh, bw, 1))
        arr2 = np.clip(np.asarray(img, float) + noise, 0, 255)
        # vignette
        vig = 1 - 0.38 * np.clip(np.hypot(x - 0.5, y - 0.5) * 1.5, 0, 1) ** 2
        self.big = Image.fromarray((arr2 * vig[..., None]).astype(np.uint8), "RGB")

    def frame(self, t: float) -> Image.Image:
        dx = self.m + math.sin(t * 0.05) * self.m * 0.8
        dy = self.m + math.cos(t * 0.04) * self.m * 0.8
        return self.big.crop((int(dx), int(dy), int(dx) + self.W, int(dy) + self.H))


class Ctx:
    def __init__(self, style: Style, W: int, H: int, backdrop: Backdrop, channel: str, vertical: bool | None = None):
        """W x H is the viewport scenes draw into; the backdrop may be taller (Shorts keep room for captions)."""
        self.style, self.W, self.H, self.bd, self.channel = style, W, H, backdrop, channel
        self.u = min(W, H) / 100  # one unit = 1% of the short side
        self.vertical = (H > W) if vertical is None else vertical
        if self.vertical:
            self.u = W / 100
        self.margin = int(self.u * (7 if self.vertical else 8))
        rng = np.random.default_rng(11)
        # floating bokeh: x, y0, radius (units), speed, phase, alpha
        self.motes = [(rng.random(), rng.random(), rng.uniform(0.35, 1.3), rng.uniform(0.012, 0.04), rng.random() * 6.28, int(rng.integers(14, 38))) for _ in range(20)]

    def canvas(self, t: float):
        img = self.bd.frame(t).crop((0, 0, self.W, self.H)).convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        acc, ink = rgb(self.style.accent), rgb(self.style.ink)
        for j, (mx, my, mr, sp, ph, al) in enumerate(self.motes):
            y = (my - sp * t) % 1.15 - 0.05
            x = mx + math.sin(t * 0.5 + ph) * 0.02
            r = mr * self.u
            fade = min(1.0, y * 6, (1.1 - y) * 6) if 0 <= y <= 1.1 else 0
            if fade <= 0:
                continue
            d.ellipse([x * self.W - r, y * self.H - r, x * self.W + r, y * self.H + r], fill=(*(acc if j % 3 == 0 else ink), int(al * fade)))
        return img, d

    def badge(self, d: ImageDraw.ImageDraw, alpha: int = 255):
        s = self.style
        f = font(s.body, int(self.u * 2.6))
        label = self.channel.upper() if s.caps_titles else self.channel
        x, y = self.margin, int(self.margin * 0.75)
        d.rounded_rectangle([x, y + self.u * 0.6, x + self.u * 1.4, y + self.u * 3.4], radius=self.u * 0.4, fill=(*rgb(s.accent), alpha))
        d.text((x + self.u * 2.4, y), label, font=f, fill=(*rgb(s.muted), alpha))


# ---------- scenes ----------
def scene_title(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    text = p.get("text", "")
    kicker = p.get("kicker", "")
    if s.caps_titles:
        text = text.upper()
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        w = c.W - 2 * c.margin
        f, lines = fit_font(d, text, s.display, w, int(c.u * (13 if c.vertical else 11)), 4)
        lh = f.size * 1.08
        total = lh * len(lines)
        y0 = c.H / 2 - total / 2
        if kicker:
            kf = font(s.body, int(c.u * 3.2))
            a = int(255 * ease(t / 0.6))
            d.text((c.margin, y0 - kf.size * 2), kicker, font=kf, fill=(*rgb(s.accent), a))
        for li, line in enumerate(lines):
            k = ease((t - 0.15 - li * 0.12) / 0.7)
            d.text((c.margin, y0 + li * lh + (1 - k) * c.u * 4), line, font=f, fill=(*rgb(s.ink), int(255 * k)))
        bar_k = ease((t - 0.5) / 1.0)
        d.rectangle([c.margin, y0 + total + c.u * 2, c.margin + (w * 0.22) * bar_k, y0 + total + c.u * 2.6], fill=rgb(s.accent))
        yield img.convert("RGB")


def scene_say(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """The on-screen line builds word by word in step with the narration. *word* = accent."""
    s = c.style
    raw = p.get("text") or " ".join(words[:16])
    tokens = raw.split()
    marks = [tok.startswith("*") and tok.rstrip(".,!?;:").endswith("*") for tok in tokens]
    tokens = [tok.replace("*", "") for tok in tokens]
    probe = Image.new("RGB", (10, 10))
    pd = ImageDraw.Draw(probe)
    w = c.W - 2 * c.margin
    if p.get("hero") and not c.vertical:
        w = int(w * 0.62)
    f, _ = fit_font(pd, " ".join(tokens), s.display, w, int(c.u * (9.5 if c.vertical else 7.5)), 5 if c.vertical else 4)
    # lay out word positions once
    space = pd.textlength(" ", font=f)
    lines: list[list[int]] = [[]]
    x = 0.0
    for idx, tok in enumerate(tokens):
        tw = pd.textlength(tok, font=f)
        if x + tw > w and lines[-1]:
            lines.append([])
            x = 0.0
        lines[-1].append(idx)
        x += tw + space
    lh = f.size * 1.18
    hero = p.get("hero")
    y0 = c.H * (0.56 if c.vertical else 0.36) if hero else c.H / 2 - lh * len(lines) / 2
    pos = {}
    for li, line in enumerate(lines):
        x = 0.0
        for idx in line:
            pos[idx] = (c.margin + x, y0 + li * lh)
            x += pd.textlength(tokens[idx], font=f) + space
    reveal_span = max(0.6, dur * 0.8)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        if hero:
            k = max(0.0, 1 - math.exp(-6 * t) * math.cos(10 * t)) if t > 0 else 0.0
            sp = _emoji.sprite(hero, max(8, int((c.W * 0.34 if c.vertical else c.H * 0.3) * max(k, 0.05))))
            if sp is not None:
                sp = sp.rotate(math.sin(t * 2.2) * 7, resample=Image.BICUBIC, expand=True)
                hx, hy = (c.W / 2, c.H * 0.3) if c.vertical else (c.W * 0.8, c.H * 0.42)
                img.paste(sp, (int(hx - sp.width / 2), int(hy - sp.height / 2 + math.sin(t * 2.6) * c.H * 0.012)), sp)
        for idx, tok in enumerate(tokens):
            appear = 0.1 + reveal_span * idx / max(1, len(tokens))
            k = ease((t - appear) / 0.35)
            if k <= 0:
                continue
            col = rgb(s.accent) if marks[idx] else rgb(s.ink)
            px, py = pos[idx]
            d.text((px, py + (1 - k) * c.u * 1.5), tok, font=f, fill=(*col, int(255 * k)))
        yield img.convert("RGB")


def scene_number(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    start, value = float(p.get("from", 0)), float(p["value"])
    unit, label, prefix = p.get("unit", ""), p.get("label", ""), p.get("prefix", "")
    nf = font(s.display, int(c.u * (20 if c.vertical else 17)))
    uf = font(s.display, int(c.u * 6))
    lf_pat = s.body
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        k = ease_io(t / min(2.2, dur * 0.6))
        v = start + (value - start) * k
        exact = float(p.get("decimals", 0 if abs(value - round(value)) < 1e-9 else 1))
        txt = prefix + (f"{v:,.{int(exact)}f}" if abs(value) < 1e7 else compact(v))
        tw = d.textlength(txt, font=nf)
        size = nf
        uw = (d.textlength(unit, font=uf) + c.u * 2) if unit else 0
        if tw + uw > c.W - 2 * c.margin:
            size = font(s.display, int(nf.size * (c.W - 2 * c.margin - uw) / tw))
            tw = d.textlength(txt, font=size)
        y = c.H * 0.36
        d.text((c.margin, y), txt, font=size, fill=rgb(s.ink))
        if unit:
            d.text((c.margin + tw + c.u * 2, y + size.size * 0.62 - uf.size), unit, font=uf, fill=rgb(s.accent))
        if label:
            lf, lines = fit_font(d, label, lf_pat, c.W - 2 * c.margin, int(c.u * 4.2), 3)
            a = int(255 * ease((t - 0.4) / 0.6))
            for li, line in enumerate(lines):
                d.text((c.margin, y + size.size * 1.25 + li * lf.size * 1.3), line, font=lf, fill=(*rgb(s.muted), a))
        yield img.convert("RGB")


def scene_bars(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    items = p["items"][:6]
    unit = p.get("unit", "")
    title = p.get("title", "")
    mx = max(float(it["value"]) for it in items) or 1
    lf = font(s.body, int(c.u * 3.4))
    vf = font(s.display, int(c.u * 4))
    tf = font(s.display, int(c.u * 5))
    area_top = c.H * (0.3 if c.vertical else 0.28)
    area_h = c.H * (0.5 if c.vertical else 0.56)
    row = area_h / len(items)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        if title:
            d.text((c.margin, area_top - tf.size * 2.2), title, font=tf, fill=rgb(s.ink))
        for j, it in enumerate(items):
            k = ease((t - 0.2 - j * 0.18) / 1.2)
            y = area_top + j * row
            d.text((c.margin, y), it["label"], font=lf, fill=rgb(s.muted))
            bw = (c.W - 2 * c.margin) * 0.78 * float(it["value"]) / mx * k
            by = y + lf.size * 1.4
            bh = max(c.u * 2.2, row * 0.32)
            hi = it.get("highlight")
            d.rounded_rectangle([c.margin, by, c.margin + max(bw, c.u), by + bh], radius=bh / 2, fill=rgb(s.accent) if hi else (*rgb(s.ink), 90))
            d.text((c.margin + bw + c.u * 1.5, by + bh / 2 - vf.size * 0.6), f"{shown(float(it['value']) * k)}{unit}", font=vf, fill=(*rgb(s.ink), int(255 * k)))
        yield img.convert("RGB")


def scene_orbit(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """Two orbits compared: today vs the what-if. Trails, glow, and a live distance readout."""
    s = c.style
    ratio = float(p.get("ratio", 0.5))  # what-if radius ÷ today's radius
    label_a, label_b = p.get("a", "Today"), p.get("b", "What if")
    cx, cy = c.W / 2, c.H / 2 + (c.u * 4 if c.vertical else 0)
    R = min(c.W, c.H) * 0.36
    r1, r2 = R, R * ratio if ratio <= 1 else R
    if ratio > 1:
        r1 = R / ratio
    lf = font(s.body, int(c.u * 3))
    trail1, trail2 = [], []
    period = 9.0
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        glow = Image.new("RGBA", (c.W, c.H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        pr = c.u * 5
        gd.ellipse([cx - pr * 1.8, cy - pr * 1.8, cx + pr * 1.8, cy + pr * 1.8], fill=(*rgb(s.accent), 50))
        glow = glow.filter(ImageFilter.GaussianBlur(c.u * 2))
        img.alpha_composite(glow)
        d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=(70, 130, 220))
        d.ellipse([cx - pr * 0.6, cy - pr * 0.9, cx + pr * 0.3, cy - pr * 0.1], fill=(110, 170, 120))
        for rr, col in ((r1, (*rgb(s.muted), 70)), (r2, (*rgb(s.accent), 110))):
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col, width=max(1, int(c.u * 0.25)))
        # Kepler: period scales with r^1.5
        a1 = 2 * math.pi * t / period
        a2 = 2 * math.pi * t / (period * (r2 / r1) ** 1.5)
        p1 = (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1))
        p2 = (cx + r2 * math.cos(a2), cy + r2 * math.sin(a2))
        trail1 = (trail1 + [p1])[-40:]
        trail2 = (trail2 + [p2])[-40:]
        for tr, col in ((trail1, rgb(s.muted)), (trail2, rgb(s.accent))):
            for k, (x, y) in enumerate(tr):
                a = int(140 * k / len(tr))
                rr = c.u * 0.5
                d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(*col, a))
        mr = c.u * 1.5
        d.ellipse([p1[0] - mr, p1[1] - mr, p1[0] + mr, p1[1] + mr], fill=(*rgb(s.muted), 255))
        d.ellipse([p2[0] - mr * 1.2, p2[1] - mr * 1.2, p2[0] + mr * 1.2, p2[1] + mr * 1.2], fill=rgb(s.accent))
        d.text((c.margin, c.H - c.margin - lf.size * 2.6), f"● {label_a}", font=lf, fill=rgb(s.muted))
        d.text((c.margin, c.H - c.margin - lf.size * 1.2), f"● {label_b}", font=lf, fill=rgb(s.accent))
        yield img.convert("RGB")


def scene_fall(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """Drop the same object under different gravities, side by side, to scale."""
    s = c.style
    items = p["items"][:4]
    height = float(p.get("height", 20))  # metres
    lf = font(s.body, int(c.u * 3.2))
    vf = font(s.display, int(c.u * 3.6))
    cols = len(items)
    top, bottom = c.H * 0.24, c.H * 0.84
    span = bottom - top
    for i in range(int(dur * FPS)):
        t = max(0.0, i / FPS - 0.6)
        img, d = c.canvas(i / FPS)
        c.badge(d)
        for j, it in enumerate(items):
            g = float(it["g"])
            x = c.margin + (c.W - 2 * c.margin) * (j + 0.5) / cols
            fall = min(height, 0.5 * g * t * t)
            y = top + span * fall / height
            d.line([(x, top), (x, bottom)], fill=(*rgb(s.ink), 30), width=max(1, int(c.u * 0.2)))
            d.line([(x - c.u * 4, bottom), (x + c.u * 4, bottom)], fill=(*rgb(s.ink), 120), width=max(1, int(c.u * 0.4)))
            r = c.u * 2.2
            landed = fall >= height
            d.ellipse([x - r, y - r, x + r, y + r], fill=rgb(s.accent) if landed else rgb(s.ink))
            lw = d.textlength(it["label"], font=lf)
            d.text((x - lw / 2, top - lf.size * 2.6), it["label"], font=lf, fill=rgb(s.muted))
            tt = math.sqrt(2 * height / g)
            txt = f"{tt:.1f}s" if landed else f"{t:.1f}s"
            tw = d.textlength(txt, font=vf)
            d.text((x - tw / 2, bottom + c.u * 2), txt, font=vf, fill=rgb(s.accent) if landed else rgb(s.ink))
        yield img.convert("RGB")


def scene_image(c: Ctx, dur: float, p: dict, words: list[str], image: Image.Image | None = None) -> Iterator[Image.Image]:
    """Slow push-in on a still (public-domain photo or map), with a caption and source credit."""
    s = c.style
    caption, credit = p.get("caption", ""), p.get("credit", "")
    if image is None:
        yield from scene_say(c, dur, {"text": caption or " ".join(words[:14])}, words)
        return
    # cover-fit at 112% so we can push in
    iw, ih = image.size
    scale = max(c.W / iw, c.H / ih) * 1.12
    big = image.convert("RGB").resize((int(iw * scale), int(ih * scale)), Image.LANCZOS)
    bw, bh = big.size
    cf = font(s.body, int(c.u * 3.4))
    crf = font(s.body, int(c.u * 1.8))
    shade = Image.new("RGBA", (c.W, c.H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for k in range(int(c.H * 0.4)):
        a = int(215 * (1 - k / (c.H * 0.4)) ** 1.6)
        sd.line([(0, c.H - k), (c.W, c.H - k)], fill=(*rgb(s.bg), a))
    for i in range(int(dur * FPS)):
        t = i / FPS
        z = 1.0 + 0.07 * ease_io(t / dur)
        w, h = bw / z, bh / z
        x0 = (bw - w) * (0.5 + 0.08 * math.sin(t * 0.07))
        y0 = (bh - h) * 0.5
        frame = big.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((c.W, c.H), Image.BILINEAR).convert("RGBA")
        frame.alpha_composite(shade)
        d = ImageDraw.Draw(frame, "RGBA")
        c.badge(d)
        if caption:
            a = int(255 * ease((t - 0.3) / 0.8))
            lines = wrap(d, caption, cf, c.W - 2 * c.margin)
            for li, line in enumerate(lines[:3]):
                d.text((c.margin, c.H - c.margin - (len(lines[:3]) - li) * cf.size * 1.3 - crf.size * 1.6), line, font=cf, fill=(*rgb(s.ink), a))
        if credit:
            d.text((c.margin, c.H - c.margin - crf.size), credit, font=crf, fill=(*rgb(s.muted), 200))
        yield frame.convert("RGB")


def scene_list(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    items = p["items"][:6]
    title = p.get("title", "")
    tf = font(s.display, int(c.u * 6))
    w = c.W - 2 * c.margin - c.u * 6
    probe = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    lf, _ = fit_font(probe, max(items, key=len), s.body, w, int(c.u * 4.4), 2)
    blocks = [wrap(probe, it, lf, w) for it in items]
    lh = lf.size * 1.35
    total = sum(len(b) * lh + c.u * 2.4 for b in blocks)
    y0 = c.H / 2 - total / 2 + (tf.size if title else 0)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        if title:
            d.text((c.margin, y0 - tf.size * 2), title, font=tf, fill=rgb(s.ink))
        y = y0
        for j, block in enumerate(blocks):
            k = ease((t - 0.2 - j * dur * 0.7 / len(blocks)) / 0.5)
            dx = (1 - k) * c.u * 3
            d.rounded_rectangle([c.margin + dx, y + lf.size * 0.25, c.margin + dx + c.u * 1.6, y + lf.size * 0.25 + c.u * 1.6], radius=c.u * 0.4, fill=(*rgb(s.accent), int(255 * k)))
            for li, line in enumerate(block):
                d.text((c.margin + c.u * 4 + dx, y + li * lh), line, font=lf, fill=(*rgb(s.ink), int(255 * k)))
            y += len(block) * lh + c.u * 2.4
        yield img.convert("RGB")


def scene_timeline(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    ev = p["events"][:6]
    yf = font(s.display, int(c.u * 5))
    lf = font(s.body, int(c.u * 2.8))
    n = len(ev)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        if c.vertical:
            x = c.margin + c.u * 2
            top, bottom = c.H * 0.2, c.H * 0.85
            k_line = ease(t / 1.2)
            d.line([(x, top), (x, top + (bottom - top) * k_line)], fill=(*rgb(s.ink), 80), width=int(c.u * 0.4))
            for j, e in enumerate(ev):
                k = ease((t - 0.3 - j * 0.5) / 0.6)
                y = top + (bottom - top) * j / max(1, n - 1)
                r = c.u * 1.4
                d.ellipse([x - r, y - r, x + r, y + r], fill=(*rgb(s.accent), int(255 * k)))
                d.text((x + c.u * 4, y - yf.size * 0.7), str(e["year"]), font=yf, fill=(*rgb(s.ink), int(255 * k)))
                for li, line in enumerate(wrap(d, e["label"], lf, c.W - x - c.u * 4 - c.margin)[:2]):
                    d.text((x + c.u * 4, y + yf.size * 0.5 + li * lf.size * 1.25), line, font=lf, fill=(*rgb(s.muted), int(255 * k)))
        else:
            y = c.H * 0.5
            left, right = c.margin, c.W - c.margin
            d.line([(left, y), (left + (right - left) * ease(t / 1.2), y)], fill=(*rgb(s.ink), 80), width=int(c.u * 0.4))
            colw = (right - left) / n
            for j, e in enumerate(ev):
                k = ease((t - 0.3 - j * 0.5) / 0.6)
                x = left + colw * (j + 0.5)
                r = c.u * 1.4
                d.ellipse([x - r, y - r, x + r, y + r], fill=(*rgb(s.accent), int(255 * k)))
                yw = d.textlength(str(e["year"]), font=yf)
                d.text((x - yw / 2, y - yf.size * 2), str(e["year"]), font=yf, fill=(*rgb(s.ink), int(255 * k)))
                for li, line in enumerate(wrap(d, e["label"], lf, colw * 0.9)[:3]):
                    lw = d.textlength(line, font=lf)
                    d.text((x - lw / 2, y + c.u * 3 + li * lf.size * 1.25), line, font=lf, fill=(*rgb(s.muted), int(255 * k)))
        yield img.convert("RGB")


def scene_verdict(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    scores = p["scores"][:5]
    overall = float(p.get("overall", sum(float(x["score"]) for x in scores) / len(scores)))
    name = p.get("name", "")
    lf = font(s.body, int(c.u * 3.2))
    of = font(s.display, int(c.u * 16))
    nf = font(s.display, int(c.u * 5))
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        d.text((c.margin, c.H * 0.16), name, font=nf, fill=rgb(s.ink))
        colx = c.margin
        top = c.H * (0.3 if c.vertical else 0.32)
        barw = (c.W - 2 * c.margin) * (0.9 if c.vertical else 0.5)
        for j, sc in enumerate(scores):
            k = ease((t - 0.2 - j * 0.25) / 0.9)
            y = top + j * lf.size * 3
            d.text((colx, y), sc["label"], font=lf, fill=rgb(s.muted))
            d.rounded_rectangle([colx, y + lf.size * 1.4, colx + barw, y + lf.size * 1.4 + c.u * 1.2], radius=c.u * 0.6, fill=(*rgb(s.ink), 30))
            d.rounded_rectangle([colx, y + lf.size * 1.4, colx + barw * float(sc["score"]) / 10 * k, y + lf.size * 1.4 + c.u * 1.2], radius=c.u * 0.6, fill=rgb(s.accent))
        k = ease((t - 0.4 - len(scores) * 0.25) / 0.8)
        txt = f"{overall * k:.1f}"
        ox = c.margin if c.vertical else c.W * 0.62
        oy = c.H * 0.68 if c.vertical else c.H * 0.36
        d.text((ox, oy), txt, font=of, fill=(*rgb(s.ink), int(255 * k)))
        d.text((ox + d.textlength(txt, font=of) + c.u * 2, oy + of.size * 0.55), "/ 10", font=nf, fill=(*rgb(s.accent), int(255 * k)))
        yield img.convert("RGB")


def scene_end(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    line = p.get("text", "Subscribe for the next one.")
    product = p.get("product", "")
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        f, lines = fit_font(d, line, s.display, c.W - 2 * c.margin, int(c.u * 8), 3)
        y0 = c.H * 0.4
        for li, ln in enumerate(lines):
            k = ease((t - li * 0.15) / 0.6)
            d.text((c.margin, y0 + li * f.size * 1.1), ln, font=f, fill=(*rgb(s.ink), int(255 * k)))
        if product:
            pf = font(s.body, int(c.u * 3.4))
            k = ease((t - 0.6) / 0.6)
            d.text((c.margin, y0 + len(lines) * f.size * 1.1 + c.u * 3), product, font=pf, fill=(*rgb(s.accent), int(255 * k)))
        c.badge(d)
        yield img.convert("RGB")


EARTH_LAYERS = (  # (outer radius as a share of Earth's 6,371 km radius, label, how strongly it is drawn)
    (1.0, "Mantle", 0.16),
    (3480 / 6371, "Outer core: liquid", 0.45),
    (1221 / 6371, "Inner core: solid", 1.0),
)


def draw_earth(img: Image.Image, cx: float, cy: float, R: float, s: Style, reveal: float = 1.0, labels: bool = False, fnt=None):
    """Cut-away of the Earth: mantle, liquid outer core, solid inner core. reveal 0..1 draws the layers from the outside in."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))  # drawn on its own layer so the alpha blends instead of replacing
    d = ImageDraw.Draw(layer)
    acc, ink, muted = rgb(s.accent), rgb(s.ink), rgb(s.muted)
    n = len(EARTH_LAYERS)
    for i, (frac, label, strength) in enumerate(EARTH_LAYERS):
        k = max(0.0, min(1.0, reveal * n - i))
        if k <= 0:
            continue
        r = R * frac
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*acc, int(255 * strength * k)), outline=(*ink, int(200 * k)), width=max(2, int(R * 0.012)))
        if labels and fnt is not None:
            inner = EARTH_LAYERS[i + 1][0] if i + 1 < n else 0.0
            ly = cy - R * (frac + inner) / 2 if inner else cy
            lx = cx + R * 1.08
            d.line([(cx, ly), (lx - R * 0.04, ly)], fill=(*muted, int(160 * k)), width=2)
            d.text((lx, ly - fnt.size * 0.6), label, font=fnt, fill=(*ink, int(255 * k)))
    img.alpha_composite(layer)


def scene_earth(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """The Earth in cross-section. mode "layers": the layers build up. mode "fall": a tunnel through the centre with a falling
    marker, a clock and a speed readout, in the simple uniform-density model (simple harmonic motion)."""
    s = c.style
    mode = p.get("mode", "layers")
    minutes = float(p.get("minutes", 42.2))
    vmax = float(p.get("vmax", 7.9))
    cap = p.get("caption", "")
    if c.vertical:
        cx, cy, R = c.W * 0.36, c.H * 0.40, c.W * 0.27
    else:
        cx, cy, R = c.W * 0.32, c.H * 0.54, c.H * 0.36
    lf = font(s.body, int(c.u * 3.1))
    vf = font(s.display, int(c.u * 6.2))
    cf = font(s.body, int(c.u * 2.8))
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = c.canvas(t)
        c.badge(d)
        reveal = ease(t / min(2.4, dur * 0.5))
        if mode == "layers":
            draw_earth(img, cx, cy, R, s, reveal, labels=True, fnt=lf)
        else:
            draw_earth(img, cx, cy, R, s, 1.0)
            d = ImageDraw.Draw(img, "RGBA")
            run = max(0.5, dur - 1.2)
            tau = max(0.0, min(1.0, (t - 0.6) / run))
            ball = -math.cos(math.pi * tau)  # -1 = top, +1 = far side
            by = cy + R * ball
            d.line([(cx, cy - R), (cx, cy + R)], fill=(*rgb(s.ink), 150), width=max(2, int(c.u * 0.45)))
            r = c.u * 1.9
            d.ellipse([cx - r, by - r, cx + r, by + r], fill=rgb(s.bg), outline=rgb(s.ink), width=max(2, int(c.u * 0.5)))
            sec = tau * minutes * 60
            speed = vmax * math.sin(math.pi * tau)
            tx = cx + R * 1.25 if not c.vertical else c.margin
            ty = cy - R * 0.55 if not c.vertical else cy + R * 1.2
            d.text((tx, ty), f"{int(sec // 60):02d}:{int(sec % 60):02d}", font=vf, fill=rgb(s.ink))
            d.text((tx, ty + vf.size * 1.15), "elapsed", font=cf, fill=rgb(s.muted))
            sx = tx if not c.vertical else c.W / 2 + c.u * 4
            sy = ty + vf.size * 2.6 if not c.vertical else ty
            d.text((sx, sy), f"{speed:.1f} km/s", font=vf, fill=rgb(s.accent))
            d.text((sx, sy + vf.size * 1.15), "speed", font=cf, fill=rgb(s.muted))
        if cap:
            d.text((c.margin, c.H - c.margin - cf.size * 1.4), cap, font=cf, fill=rgb(s.muted))
        yield img.convert("RGB")


SCENES = {
    "title": scene_title,
    "say": scene_say,
    "number": scene_number,
    "bars": scene_bars,
    "orbit": scene_orbit,
    "fall": scene_fall,
    "image": scene_image,
    "list": scene_list,
    "timeline": scene_timeline,
    "verdict": scene_verdict,
    "earth": scene_earth,
    "end": scene_end,
}


random.seed(7)
