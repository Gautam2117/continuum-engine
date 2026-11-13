"""Hand-drawn vector sprites for the Atlas scenes (all original). Each is drawn at 3x and shrunk, so edges are smooth.

Palette is the channel's: navy space, cyan accent, ivory ink, plus coral for the person and warm tones for heat.
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

CORAL = (255, 112, 96)
CORAL_D = (214, 78, 70)
GOLD = (255, 200, 90)
IVORY = (238, 244, 255)
CYAN = (94, 225, 255)
SLATE = (86, 96, 120)
NAVY = (12, 22, 46)
SKIN = (255, 214, 186)
K = 3  # supersampling


def _canvas(w: int, h: int):
    img = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _done(img: Image.Image, w: int, h: int) -> Image.Image:
    return img.resize((max(1, w), max(1, h)), Image.LANCZOS)


def _line(d, pts, width, fill):
    d.line([(x * K, y * K) for x, y in pts], fill=fill, width=int(width * K), joint="curve")
    for x, y in (pts[0], pts[-1]):
        r = width * K / 2
        d.ellipse([x * K - r, y * K - r, x * K + r, y * K + r], fill=fill)


@lru_cache(maxsize=256)
def person(h: int, pose: str = "fall", phase: int = 0) -> Image.Image:
    """A low-poly person, h pixels tall. Poses: stand, fall (arms up, legs bent), spread (skydiver), float (relaxed, tumbling)."""
    w = int(h * 0.9)
    img, d = _canvas(w, h)
    cx = w / 2
    s = h / 100.0
    lw = 6.2 * s
    wob = math.sin(phase * 0.5) * 3 * s
    # joints (x, y) in a 100-high box
    if pose == "stand":
        head, neck, hip = (cx, 12 * s), (cx, 22 * s), (cx, 55 * s)
        arms = [((cx - 11 * s, 46 * s)), ((cx + 11 * s, 46 * s))]
        legs = [((cx - 7 * s, 98 * s)), ((cx + 7 * s, 98 * s))]
    elif pose == "spread":
        head, neck, hip = (cx, 14 * s), (cx, 24 * s), (cx, 56 * s)
        arms = [((cx - 36 * s, 20 * s + wob)), ((cx + 36 * s, 20 * s - wob))]
        legs = [((cx - 26 * s, 96 * s)), ((cx + 26 * s, 96 * s))]
    elif pose == "float":
        head, neck, hip = (cx + 6 * s, 16 * s), (cx + 4 * s, 26 * s), (cx - 2 * s, 56 * s)
        arms = [((cx - 24 * s, 36 * s)), ((cx + 26 * s, 42 * s))]
        legs = [((cx - 20 * s, 86 * s)), ((cx + 14 * s, 92 * s))]
    else:  # fall
        head, neck, hip = (cx, 15 * s), (cx, 25 * s), (cx, 56 * s)
        arms = [((cx - 24 * s, 8 * s + wob)), ((cx + 24 * s, 10 * s - wob))]
        legs = [((cx - 15 * s, 90 * s - wob)), ((cx + 15 * s, 86 * s + wob))]
    for lx, ly in legs:
        _line(d, [hip, ((hip[0] + lx) / 2 + (4 * s if lx > cx else -4 * s), (hip[1] + ly) / 2), (lx, ly)], lw, (46, 58, 92, 255))
    _line(d, [neck, hip], 12 * s, CORAL + (255,))
    for ax, ay in arms:
        _line(d, [(neck[0], neck[1] + 3 * s), ((neck[0] + ax) / 2, (neck[1] + ay) / 2), (ax, ay)], lw * 0.9, CORAL_D + (255,))
        d.ellipse([(ax - 3.2 * s) * K, (ay - 3.2 * s) * K, (ax + 3.2 * s) * K, (ay + 3.2 * s) * K], fill=SKIN + (255,))
    r = 8.2 * s
    d.ellipse([(head[0] - r) * K, (head[1] - r) * K, (head[0] + r) * K, (head[1] + r) * K], fill=SKIN + (255,))
    d.pieslice([(head[0] - r) * K, (head[1] - r) * K, (head[0] + r) * K, (head[1] + r) * K], 180, 360, fill=(40, 34, 52, 255))
    return _done(img, w, h)


@lru_cache(maxsize=64)
def car(w: int, spin: int = 0, color: tuple = CORAL) -> Image.Image:
    """Side view, heading right. spin (0..7) rotates the wheel spokes."""
    h = int(w * 0.42)
    img, d = _canvas(w, h)
    s = w / 100.0
    body = [(4, 26), (10, 17), (30, 14), (40, 4), (66, 4), (80, 14), (96, 18), (98, 30), (4, 30)]
    d.polygon([(x * s * K, (y + 8) * s * K) for x, y in body], fill=color + (255,))
    win = [(42, 14), (46, 8), (64, 8), (74, 16)]
    d.polygon([(x * s * K, (y + 3) * s * K) for x, y in win], fill=(170, 220, 255, 255))
    d.rectangle([54 * s * K, 11 * s * K, 55.5 * s * K, 19 * s * K], fill=color + (255,))
    for wx in (24, 76):
        cx, cy, r = wx * s, 37 * s, 9.5 * s
        d.ellipse([(cx - r) * K, (cy - r) * K, (cx + r) * K, (cy + r) * K], fill=(24, 30, 48, 255))
        r2 = r * 0.55
        d.ellipse([(cx - r2) * K, (cy - r2) * K, (cx + r2) * K, (cy + r2) * K], fill=IVORY + (255,))
        for k in range(3):
            a = spin * math.pi / 8 + k * math.pi / 3
            _line(d, [(cx - math.cos(a) * r2, cy - math.sin(a) * r2), (cx + math.cos(a) * r2, cy + math.sin(a) * r2)], 1.4 * s, (24, 30, 48, 255))
    d.rectangle([94 * s * K, 22 * s * K, 99 * s * K, 27 * s * K], fill=GOLD + (255,))
    return _done(img, w, h)


@lru_cache(maxsize=64)
def jet(w: int) -> Image.Image:
    h = int(w * 0.36)
    img, d = _canvas(w, h)
    s = w / 100.0
    d.ellipse([4 * s * K, 12 * s * K, 98 * s * K, 26 * s * K], fill=IVORY + (255,))          # fuselage
    d.polygon([(x * s * K, y * s * K) for x, y in [(6, 18), (2, 2), (14, 2), (26, 17)]], fill=CYAN + (255,))     # tail fin
    d.polygon([(x * s * K, y * s * K) for x, y in [(40, 20), (60, 20), (44, 34), (36, 34)]], fill=(190, 205, 235, 255))  # wing
    d.ellipse([88 * s * K, 15 * s * K, 97 * s * K, 21 * s * K], fill=(110, 170, 230, 255))   # cockpit
    for wx in range(30, 80, 7):
        d.ellipse([wx * s * K, 16 * s * K, (wx + 2.4) * s * K, 18.4 * s * K], fill=(110, 170, 230, 255))
    d.ellipse([42 * s * K, 28 * s * K, 54 * s * K, 34 * s * K], fill=(150, 165, 200, 255))   # engine
    return _done(img, w, h)


@lru_cache(maxsize=128)
def rocket(w: int, flame: int = 0) -> Image.Image:
    """Heading right: a plain two-stage rocket with a capsule, original design."""
    h = int(w * 0.30)
    img, d = _canvas(w, h)
    s = w / 100.0
    fl = 12 + 8 * ((flame % 3) / 2)
    d.polygon([(x * s * K, y * s * K) for x, y in [(18, 9), (18, 21), (0 + 18 - fl * 0.9, 15)]], fill=GOLD + (255,))
    d.polygon([(x * s * K, y * s * K) for x, y in [(18, 11), (18, 19), (18 - fl * 0.5, 15)]], fill=(255, 245, 210, 255))
    d.rectangle([18 * s * K, 7 * s * K, 62 * s * K, 23 * s * K], fill=IVORY + (255,))
    d.rectangle([40 * s * K, 7 * s * K, 62 * s * K, 23 * s * K], fill=(214, 224, 244, 255))
    d.polygon([(x * s * K, y * s * K) for x, y in [(62, 7), (62, 23), (82, 17), (82, 13)]], fill=CYAN + (255,))
    d.polygon([(x * s * K, y * s * K) for x, y in [(82, 13), (82, 17), (96, 15)]], fill=CORAL + (255,))
    d.polygon([(x * s * K, y * s * K) for x, y in [(20, 8), (32, 8), (16, 0)]], fill=CORAL + (255,))
    d.polygon([(x * s * K, y * s * K) for x, y in [(20, 22), (32, 22), (16, 30)]], fill=CORAL + (255,))
    d.ellipse([46 * s * K, 11 * s * K, 54 * s * K, 19 * s * K], fill=(120, 180, 240, 255))
    return _done(img, w, h)


@lru_cache(maxsize=64)
def train(w: int) -> Image.Image:
    """A short two-car tram, heading right."""
    h = int(w * 0.26)
    img, d = _canvas(w, h)
    s = w / 100.0
    for ox, col in ((0, CYAN), (52, CORAL)):
        d.rounded_rectangle([(ox + 2) * s * K, 4 * s * K, (ox + 48) * s * K, 22 * s * K], radius=int(4 * s * K), fill=col + (255,))
        for wx in range(7, 44, 9):
            d.rounded_rectangle([(ox + wx) * s * K, 8 * s * K, (ox + wx + 6) * s * K, 14 * s * K], radius=int(1.5 * s * K), fill=(20, 30, 56, 255))
    d.rectangle([48 * s * K, 14 * s * K, 54 * s * K, 17 * s * K], fill=(60, 70, 100, 255))
    return _done(img, w, h)


@lru_cache(maxsize=64)
def moon(r: int) -> Image.Image:
    d_ = r * 2
    img, d = _canvas(d_, d_)
    d.ellipse([0, 0, d_ * K - 1, d_ * K - 1], fill=(196, 202, 214, 255))
    for cx, cy, cr in ((0.34, 0.32, 0.17), (0.66, 0.55, 0.22), (0.42, 0.72, 0.11), (0.7, 0.22, 0.09), (0.2, 0.58, 0.08)):
        d.ellipse([(cx - cr) * d_ * K, (cy - cr) * d_ * K, (cx + cr) * d_ * K, (cy + cr) * d_ * K], fill=(160, 168, 184, 255))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d_ * K - 1, d_ * K - 1], fill=255)
    shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    sd.ellipse([-d_ * K * 0.35, -d_ * K * 0.1, d_ * K * 0.95, d_ * K * 1.1], fill=(0, 0, 0, 0))
    shade2 = Image.new("RGBA", img.size, (8, 14, 36, 110))
    img.alpha_composite(Image.composite(shade2, Image.new("RGBA", img.size, (0, 0, 0, 0)), mask.filter(ImageFilter.GaussianBlur(0)).point(lambda v: 0)))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return _done(out, d_, d_)


@lru_cache(maxsize=64)
def earth_ball(r: int) -> Image.Image:
    """A small stylised Earth: ocean, three continents, atmosphere rim."""
    d_ = r * 2
    img, d = _canvas(d_, d_)
    d.ellipse([0, 0, d_ * K - 1, d_ * K - 1], fill=(40, 110, 200, 255))
    blobs = [
        [(0.28, 0.2), (0.46, 0.16), (0.52, 0.32), (0.4, 0.46), (0.3, 0.4)],
        [(0.52, 0.5), (0.7, 0.46), (0.78, 0.66), (0.62, 0.84), (0.5, 0.7)],
        [(0.6, 0.18), (0.82, 0.24), (0.84, 0.38), (0.66, 0.36)],
        [(0.14, 0.52), (0.26, 0.5), (0.3, 0.68), (0.2, 0.74)],
    ]
    for poly in blobs:
        d.polygon([(x * d_ * K, y * d_ * K) for x, y in poly], fill=(88, 176, 112, 255))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d_ * K - 1, d_ * K - 1], fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    od = ImageDraw.Draw(out)
    od.ellipse([0, 0, d_ * K - 1, d_ * K - 1], outline=(150, 210, 255, 255), width=max(2, int(d_ * K * 0.02)))
    return _done(out, d_, d_)


def glow(size: int, color: tuple, alpha: int = 200) -> Image.Image:
    """A soft round glow, size px across."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(24):
        k = i / 23
        r = size / 2 * (1 - k)
        d.ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r], fill=(*color, int(alpha * (k ** 1.8) / 4 + 2)))
    return img.filter(ImageFilter.GaussianBlur(size * 0.04))


@lru_cache(maxsize=64)
def mug(h: int) -> Image.Image:
    w = int(h * 1.2)
    img, d = _canvas(w, h)
    s = h / 100.0
    d.rounded_rectangle([6 * s * K, 18 * s * K, 70 * s * K, 96 * s * K], radius=int(8 * s * K), fill=GOLD + (255,))
    d.arc([54 * s * K, 34 * s * K, 100 * s * K, 80 * s * K], -90, 90, fill=GOLD + (255,), width=int(9 * s * K))
    d.ellipse([10 * s * K, 12 * s * K, 66 * s * K, 28 * s * K], fill=(110, 70, 50, 255))
    return _done(img, w, h)


@lru_cache(maxsize=64)
def phone(h: int) -> Image.Image:
    w = int(h * 0.55)
    img, d = _canvas(w, h)
    d.rounded_rectangle([0, 0, w * K - 1, h * K - 1], radius=int(w * K * 0.18), fill=(30, 40, 70, 255), outline=CYAN + (255,), width=int(w * K * 0.05))
    d.rounded_rectangle([w * K * 0.14, h * K * 0.1, w * K * 0.86, h * K * 0.86], radius=int(w * K * 0.08), fill=(94, 160, 220, 255))
    return _done(img, w, h)
