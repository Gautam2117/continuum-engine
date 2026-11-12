"""An original animated host character per channel. Lip-synced to the narration, blinks, bobs, reacts.

Drawn with PIL at 2x and scaled down, so edges stay smooth. Characters are our own designs.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from .styles import rgb

SHAPES = {"drift": "cloud", "atlas": "planet", "10sec": "bulb", "oddly": "ghost", "crazy": "robot", "wild": "fox",
          "foundbeam": "bulb", "verdict": "robot"}


def envelope(audio: np.ndarray, sr: int, fps: int, n: int) -> np.ndarray:
    """Per-video-frame mouth openness 0..1 from the narration's loudness."""
    hop = sr // fps
    if len(audio) < hop:
        return np.zeros(n)
    m = len(audio) // hop
    rms = np.sqrt((audio[: m * hop].reshape(m, hop) ** 2).mean(axis=1))
    ref = np.percentile(rms, 90) or 1.0
    env = np.clip(rms / ref, 0, 1.2) ** 0.8
    env = np.convolve(env, [0.25, 0.5, 0.25], mode="same")
    out = np.zeros(n)
    out[: min(n, m)] = env[:n]
    return np.clip(out, 0, 1)


def mood_for(text: str, kind: str, sleepy: bool) -> str:
    if sleepy:
        return "sleepy"
    if "?" in text:
        return "curious"
    if "!" in text or kind in ("number", "fall"):
        return "excited"
    return "happy"


def _mix(a, b, k):
    return tuple(int(a[i] * (1 - k) + b[i] * k) for i in range(3))


def draw(size: int, slug: str, style, t: float, env: float, mood: str = "happy", wave: float = 0.0) -> Image.Image:
    N = size * 2
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    main = rgb(style.accent)
    dark = _mix(rgb(style.bg), (0, 0, 0), 0.5)
    light = _mix(main, (255, 255, 255), 0.45)
    shade = _mix(main, dark, 0.35)
    shape = SHAPES.get(slug, "blob")
    r = N * 0.31
    cx = N / 2
    bob = math.sin(t * 2.3) * N * 0.012 + env * N * 0.012
    cy = N * 0.5 + bob
    rx, ry = r * (1 + 0.025 * env), r * (1 - 0.025 * env)
    ow = max(3, int(N * 0.012))

    # ground shadow
    d.ellipse([cx - rx * 0.9, N * 0.9 - N * 0.02, cx + rx * 0.9, N * 0.9 + N * 0.02], fill=(0, 0, 0, 60))

    if shape == "planet":
        ring = [cx - rx * 1.7, cy - ry * 0.34, cx + rx * 1.7, cy + ry * 0.34]
        d.ellipse(ring, outline=light, width=int(N * 0.03))
    if shape == "bulb":
        d.ellipse([cx - rx * 1.3, cy - ry * 1.3, cx + rx * 1.3, cy + ry * 1.3], fill=(*main, 38))
        d.rounded_rectangle([cx - rx * 0.36, cy + ry * 0.85, cx + rx * 0.36, cy + ry * 1.3], radius=int(N * 0.02), fill=(170, 175, 185), outline=dark, width=ow)
        d.line([(cx - rx * 0.3, cy + ry * 1.05), (cx + rx * 0.3, cy + ry * 1.05)], fill=dark, width=ow)
    if shape == "robot":
        d.line([(cx, cy - ry * 0.85), (cx, cy - ry * 1.3)], fill=dark, width=ow * 2)
        d.ellipse([cx - N * 0.03, cy - ry * 1.3 - N * 0.03, cx + N * 0.03, cy - ry * 1.3 + N * 0.03], fill=(255, 90, 80) if int(t * 2) % 2 else light, outline=dark, width=ow)
    if shape == "fox":
        for sgn in (-1, 1):
            tip = (cx + sgn * rx * 0.85, cy - ry * 1.45)
            d.polygon([(cx + sgn * rx * 0.25, cy - ry * 0.85), tip, (cx + sgn * rx * 1.05, cy - ry * 0.35)], fill=main, outline=dark)
            d.polygon([(cx + sgn * rx * 0.5, cy - ry * 0.85), (cx + sgn * rx * 0.85, cy - ry * 1.2), (cx + sgn * rx * 0.95, cy - ry * 0.5)], fill=dark)

    # body
    if shape == "cloud":
        blobs = [(-0.62, 0.12, 0.62), (0.62, 0.12, 0.62), (0, -0.28, 0.82), (-0.28, 0.38, 0.7), (0.28, 0.38, 0.7)]
        for ox, oy, rr in blobs:
            d.ellipse([cx + ox * r - rr * r - ow, cy + oy * r - rr * r - ow, cx + ox * r + rr * r + ow, cy + oy * r + rr * r + ow], fill=dark)
        for ox, oy, rr in blobs:
            d.ellipse([cx + ox * r - rr * r, cy + oy * r - rr * r, cx + ox * r + rr * r, cy + oy * r + rr * r], fill=main)
    elif shape == "ghost":
        pts = [(cx + rx * math.cos(a), cy - ry * 0.1 + ry * 0.95 * math.sin(a)) for a in np.linspace(math.pi, 2 * math.pi, 28)]
        base = cy + ry * 1.0
        for i in range(0, 13):
            x = cx + rx - (2 * rx) * i / 12
            pts.append((x, base + math.sin(i * math.pi / 2 + t * 4) * ry * 0.09 + (ry * 0.1 if i % 2 else 0)))
        d.polygon(pts, fill=main, outline=dark)
        d.line(pts + [pts[0]], fill=dark, width=ow)
    elif shape == "robot":
        box = [cx - rx * 0.98, cy - ry * 0.85, cx + rx * 0.98, cy + ry * 0.95]
        d.rounded_rectangle(box, radius=int(r * 0.38), fill=main, outline=dark, width=ow)
        for sgn in (-1, 1):
            d.ellipse([cx + sgn * rx * 1.0 - N * 0.025, cy - N * 0.025, cx + sgn * rx * 1.0 + N * 0.025, cy + N * 0.025], fill=shade, outline=dark, width=ow)
    else:
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=main, outline=dark, width=ow)
    # soft highlight
    if shape not in ("cloud", "ghost"):
        hl = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        ImageDraw.Draw(hl).ellipse([cx - rx * 0.72, cy - ry * 0.82, cx - rx * 0.12, cy - ry * 0.4], fill=(255, 255, 255, 70))
        img.alpha_composite(hl)
        d = ImageDraw.Draw(img, "RGBA")
    if shape == "planet":
        d.arc([cx - rx * 1.7, cy - ry * 0.34, cx + rx * 1.7, cy + ry * 0.34], 0, 180, fill=light, width=int(N * 0.03))
        for ox, oy, rr in ((0.55, 0.45, 0.1), (-0.65, 0.5, 0.07), (0.7, -0.5, 0.06)):
            d.ellipse([cx + ox * r - rr * r, cy + oy * r - rr * r, cx + ox * r + rr * r, cy + oy * r + rr * r], fill=(*shade, 200))

    # face
    fy = cy - ry * 0.05
    sleepy = mood == "sleepy"
    phase = t % 3.4
    blink = 0.08 if (phase < 0.12 or (2.5 < phase < 2.6)) else 1.0
    look = math.sin(t * 0.8) * 0.06 * r
    ex, ey, erx, ery = r * 0.36, fy - r * 0.1, r * 0.17, r * (0.23 if mood != "excited" else 0.28)
    for sgn in (-1, 1):
        x0 = cx + sgn * ex
        h = ery * blink
        d.ellipse([x0 - erx, ey - h, x0 + erx, ey + h], fill=(250, 250, 252), outline=dark, width=max(2, ow // 2))
        if blink > 0.5:
            d.ellipse([x0 - r * 0.11 + look, ey - r * 0.11, x0 + r * 0.11 + look, ey + r * 0.11], fill=dark)
            d.ellipse([x0 - r * 0.03 + look, ey - r * 0.07, x0 + r * 0.04 + look, ey], fill=(255, 255, 255))
        if sleepy:
            d.rectangle([x0 - erx - 2, ey - ery - 2, x0 + erx + 2, ey - ery * 0.1], fill=main if shape != "cloud" else main)
            d.line([(x0 - erx, ey - ery * 0.1), (x0 + erx, ey - ery * 0.1)], fill=dark, width=ow)
    bw = max(3, int(N * 0.016))
    for sgn in (-1, 1):
        x0 = cx + sgn * ex
        y0 = ey - ery - r * 0.12
        if mood == "curious":
            y0 -= r * (0.14 if sgn > 0 else 0.0)
        elif mood == "excited":
            y0 -= r * 0.1
        elif sleepy:
            y0 += r * 0.08
        tilt = 0.0
        d.line([(x0 - erx * 0.9, y0 + sgn * tilt), (x0 + erx * 0.9, y0 - sgn * tilt)], fill=dark, width=bw)
    # cheeks
    for sgn in (-1, 1):
        d.ellipse([cx + sgn * r * 0.62 - r * 0.13, fy + r * 0.2 - r * 0.08, cx + sgn * r * 0.62 + r * 0.13, fy + r * 0.2 + r * 0.08], fill=(255, 110, 140, 150))
    # mouth
    my = fy + r * 0.42
    if env < 0.1:
        d.arc([cx - r * 0.22, my - r * 0.18, cx + r * 0.22, my + r * 0.12], 20, 160, fill=dark, width=bw)
    else:
        mh = r * (0.05 + 0.34 * env)
        mw = r * (0.2 + 0.12 * env + 0.04 * math.sin(t * 17))
        d.ellipse([cx - mw, my - mh * 0.4, cx + mw, my + mh], fill=dark)
        if mh > r * 0.16:
            d.ellipse([cx - mw * 0.6, my + mh * 0.35, cx + mw * 0.6, my + mh * 0.95], fill=(240, 110, 130))
    # hands
    for sgn in (-1, 1):
        hx = cx + sgn * rx * 1.05
        hy = cy + ry * 0.45 + math.sin(t * 2.3 + sgn) * N * 0.01
        if sgn > 0 and wave > 0:
            hy = cy - ry * 0.2 - wave * ry * 0.5
            hx += math.sin(t * 10) * r * 0.1 * wave
        d.ellipse([hx - r * 0.15, hy - r * 0.15, hx + r * 0.15, hy + r * 0.15], fill=main, outline=dark, width=ow)
    out = img.resize((size, size), Image.LANCZOS)
    tilt = math.sin(t * 1.3) * 2.0 + (3 if mood == "curious" else 0)
    return out.rotate(tilt, resample=Image.BICUBIC, center=(size / 2, size * 0.8))
