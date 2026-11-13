"""Motion-first scenes for Counterfactual Atlas: things travel, fall, race and drain instead of cards appearing.

Rules these scenes follow
- Something moves in every frame, and the first frame already shows the consequence.
- Every motion comes from engine/physics.py (or is a plain linear count), never eyeballed.
- Text is a title chip, one readout and a short label. The narration carries the explanation.
- They work in 16:9 and 9:16, drawing inside zone(c), clear of the host and the captions.
"""
from __future__ import annotations

import math
import random
from typing import Iterator

from PIL import Image, ImageDraw, ImageFilter

from . import physics as PH
from . import sprites as SP
from .fonts import font
from .scenes import FPS, Ctx, draw_earth, ease, ease_io, shown, wrap
from .styles import rgb

CORAL, GOLD, IVORY, CYAN = SP.CORAL, SP.GOLD, SP.IVORY, SP.CYAN
LAYER_COL = [(92, 104, 132), (200, 92, 80), (255, 150, 84), (255, 226, 168)]   # crust, mantle, outer core, inner core
LAYER_NAME = ["Crust", "Mantle", "Outer core: liquid", "Inner core: solid"]
BOUNDS = [35.0, 2900.0, 5151.0]                                                  # km of depth where each layer ends


# ---------- helpers ----------
def zone(c: Ctx) -> tuple[float, float, float, float]:
    """Safe drawing box: clear of the host (bottom right on long-form) and the captions."""
    if c.vertical:
        return c.W * 0.06, c.H * 0.05, c.W * 0.94, c.H * 0.95
    return c.W * 0.05, c.H * 0.07, c.W * 0.80, c.H * 0.84


def canvas(c: Ctx, t: float):
    """The channel backdrop as an RGB image with a drawing context that really blends alpha
    (an RGBA image draws alpha straight into the pixels, which is why translucent shapes came out solid)."""
    img = c.canvas(t)[0].convert("RGB")
    return img, ImageDraw.Draw(img, "RGBA")


def mix(a: tuple, b: tuple, k: float) -> tuple:
    k = max(0.0, min(1.0, k))
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def paste(img: Image.Image, sp: Image.Image, x: float, y: float, alpha: float = 1.0):
    """Centre a sprite at (x, y); safe off-screen."""
    if alpha < 0.999:
        sp = sp.copy()
        sp.putalpha(sp.getchannel("A").point(lambda v: int(v * max(0.0, alpha))))
    img.paste(sp, (int(x - sp.width / 2), int(y - sp.height / 2)), sp)


def chip(d: ImageDraw.ImageDraw, x: float, y: float, text: str, f, fg, bg=(8, 14, 34), alpha: int = 255, anchor: str = "l", pad: float = 0.5):
    """A rounded label. anchor l / c / r decides which side of x the chip grows from."""
    tw = d.textlength(text, font=f)
    p = f.size * pad
    w, h = tw + p * 2, f.size * 1.25 + p
    x0 = x if anchor == "l" else (x - w / 2 if anchor == "c" else x - w)
    d.rounded_rectangle([x0, y, x0 + w, y + h], radius=h * 0.32, fill=(*bg, int(alpha * 0.82)))
    d.text((x0 + p, y + p * 0.62), text, font=f, fill=(*fg, alpha))
    return x0, y, w, h


def big_number(d, x, y, text, f, unit, uf, col, ucol, anchor="l"):
    tw = d.textlength(text, font=f)
    uw = d.textlength(unit, font=uf) + f.size * 0.25 if unit else 0
    if anchor == "r":
        x = x - tw - uw
    d.text((x, y), text, font=f, fill=col)
    if unit:
        d.text((x + tw + f.size * 0.25, y + f.size * 0.62 - uf.size * 0.72), unit, font=uf, fill=ucol)


def mmss(minutes: float) -> str:
    s = int(round(minutes * 60))
    return f"{s // 60:02d}:{s % 60:02d}"


def sparks(d, rng_list, t, origin, spread, n_alpha, col, size):
    for (a, sp, ph, life) in rng_list:
        k = ((t * sp + ph) % life) / life
        x = origin[0] + math.cos(a) * spread * k
        y = origin[1] + math.sin(a) * spread * k
        al = int(n_alpha * (1 - k))
        if al > 4:
            r = size * (1 - k * 0.6)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(*col, al))


# ---------- the plunge: a falling person, the shaft scrolling past, layers and heat ----------
def scene_plunge(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    d0, d1 = float(p.get("d0", 0)), float(p.get("d1", 6371))
    pose = p.get("pose", "fall")
    curve = float(p.get("curve", 1.0))
    intro = float(p.get("intro", 0.0))
    shield, air, burn = p.get("shield"), p.get("air"), p.get("burn")
    labels, temp = p.get("labels"), p.get("temp")
    clock = p.get("clock")
    floaters, centre = p.get("floaters"), p.get("centre")
    speedo = p.get("speedo")
    title = p.get("title")
    evac = p.get("evac")
    x0, y0, x1, y1 = zone(c)
    cx = (x0 + x1) / 2
    cy = y0 + (y1 - y0) * (0.47 if not c.vertical else 0.44)
    figh = int((y1 - y0) * (0.21 if not c.vertical else 0.16))
    shaft_w = (x1 - x0) * (0.30 if not c.vertical else 0.46)
    K = c.H * 0.17
    rng = random.Random(5)
    rocks = [(rng.random(), rng.random(), rng.uniform(0.03, 0.09), rng.uniform(0.02, 0.07), rng.choice([-1, 1]), rng.uniform(0.0, 0.5)) for _ in range(110)]
    dots = [(rng.random(), rng.random(), rng.uniform(0.6, 1.4)) for _ in range(70)]
    embers = [(rng.uniform(-math.pi, 0), rng.uniform(40, 140), rng.random() * 3, rng.uniform(0.6, 1.4)) for _ in range(40)]
    f_depth, f_unit = font(s.display, int(c.u * (7 if not c.vertical else 8))), font(s.display, int(c.u * 3))
    f_small, f_chip = font(s.body, int(c.u * 2.4)), font(s.display, int(c.u * 2.7))
    shade_img = Image.new("RGBA", (c.W, c.H), (0, 0, 0, 0))
    sd_ = ImageDraw.Draw(shade_img)
    lxa, lxb = cx - shaft_w / 2, cx + shaft_w / 2
    for q in range(26):
        a_ = int(120 * (1 - q / 26) ** 2)
        wq = (lxa / 26) * 1.0
        sd_.rectangle([lxa - (q + 1) * wq, 0, lxa - q * wq, c.H], fill=(0, 0, 0, int(a_ * 0.35)))
        sd_.rectangle([lxb + q * wq * 0 + q * ((c.W - lxb) / 26), 0, lxb + (q + 1) * ((c.W - lxb) / 26), c.H], fill=(0, 0, 0, int(a_ * 0.35 * (q / 26))))
        sd_.rectangle([lxa - (q + 1) * wq, 0, lxa - q * wq, c.H], fill=(0, 0, 0, int(a_ * 0.0)))
    for q in range(10):
        sd_.rectangle([lxa - c.u * (q + 1) * 0.9, 0, lxa - c.u * q * 0.9, c.H], fill=(0, 0, 0, int(70 * (1 - q / 10))))
        sd_.rectangle([lxb + c.u * q * 0.9, 0, lxb + c.u * (q + 1) * 0.9, c.H], fill=(0, 0, 0, int(70 * (1 - q / 10))))
    floats = [("mug", 0.0, 1.0), ("phone", 2.1, 0.8), ("mug", 4.2, 0.7)] if floaters else []
    shown_layers: dict[int, float] = {}

    def ymap(db: float, D: float) -> float:
        dd = db - D
        return cy + (1 if dd >= 0 else -1) * K * math.log1p(abs(dd) / 30.0)

    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        tp = max(0.0, (t - intro) / max(0.1, dur - intro))
        D = d0 + (d1 - d0) * (tp ** curve)
        layer = sum(1 for b in BOUNDS if D >= b)
        for bi_, b_ in enumerate(BOUNDS):
            if D >= b_ and d0 < b_:
                shown_layers.setdefault(bi_ + 1, t)
        speed_px = 0.0 if t < intro else c.H * (0.55 + 0.35 * math.sin(math.pi * min(1, tp)))
        scroll = (t - intro) * speed_px if t >= intro else 0.0

        # walls: layer colour bands either side of the shaft, rock streaks scrolling up
        ys = [-9999.0] + [ymap(b, D) for b in BOUNDS] + [9999.0]
        lx0, lx1 = cx - shaft_w / 2, cx + shaft_w / 2
        gy = None
        if intro > 0 and t < intro:
            # the ground and the hole, seen from the side; the camera follows the person down
            k = ease_io((t - intro * 0.35) / (intro * 0.65))
            gy = cy + figh * 0.5 - k * (c.H * 0.95)
        for li in range(4):
            top, bot = max(ys[li], gy if gy is not None else -9999), min(ys[li + 1], 9999)
            if gy is not None and li == 0:
                top = gy
            if bot <= top:
                continue
            col = LAYER_COL[li]
            heat = 1.0 if li >= 2 else 0.0
            for (xa, xb) in ((0, lx0), (lx1, c.W)):
                d.rectangle([xa, top, xb, bot], fill=(*col, 255))
        # rock: chunky polygons scrolling up, darker toward the shaft so it reads as depth
        for (sx, sy, sw, sh_, shade, sd) in rocks:
            yy = (sy * c.H * 1.3 - scroll * (0.35 + sd)) % (c.H * 1.3) - c.H * 0.15
            side = sx < 0.5
            span = (lx0 - 0) if side else (c.W - lx1)
            xx = (sx * 2 % 1.0) * span + (0 if side else lx1)
            if gy is not None and yy < gy:
                continue
            w_, h_ = sw * c.H, sh_ * c.H
            pts = [(xx - w_ * .5, yy), (xx - w_ * .2, yy - h_ * .5), (xx + w_ * .4, yy - h_ * .4), (xx + w_ * .5, yy + h_ * .2), (xx, yy + h_ * .5)]
            d.polygon(pts, fill=(255, 255, 255, 20) if shade > 0 else (0, 0, 0, 34))
        img.paste(shade_img, (0, 0), shade_img)
        d = ImageDraw.Draw(img, "RGBA")
        # shaft: dark with edge lines
        d.rectangle([lx0, 0, lx1, c.H], fill=(6, 10, 24, 255))
        d.line([(lx0, 0), (lx0, c.H)], fill=(*IVORY, 70), width=max(2, int(c.u * 0.3)))
        d.line([(lx1, 0), (lx1, c.H)], fill=(*IVORY, 70), width=max(2, int(c.u * 0.3)))
        if gy is not None:
            d.line([(0, gy), (lx0, gy)], fill=(*IVORY, 90), width=max(2, int(c.u * 0.3)))
            d.line([(lx1, gy), (c.W, gy)], fill=(*IVORY, 90), width=max(2, int(c.u * 0.3)))
        # layer boundary lines sliding past
        for bi, b in enumerate(BOUNDS):
            yb = ymap(b, D)
            if 0 < yb < c.H:
                d.line([(0, yb), (c.W, yb)], fill=(255, 255, 255, 150), width=max(2, int(c.u * 0.5)))
        # heat glow on the core layers
        if layer >= 2:
            gl = SP.glow(int(shaft_w * 3.4), (255, 170, 70) if layer == 2 else (255, 240, 190), 120)
            paste(img, gl, cx, cy)
        # air particles in the shaft
        if air:
            k_ev = 0.0 if not evac else max(0.0, min(1.0, (tp - 0.1) / 0.5))
            for (a, b_, sz) in dots:
                if b_ < k_ev:
                    continue
                xx = lx0 + 6 + a * (shaft_w - 12)
                yy = (b_ * c.H - (scroll * 1.3 + t * 40) * (1 + k_ev * 3)) % c.H
                r = c.u * 0.34 * sz
                d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(220, 236, 255, 120))
            for sx_ in (lx0 + shaft_w * 0.18, lx0 + shaft_w * 0.5, lx0 + shaft_w * 0.82):  # wind streaks
                yy = (t * c.H * 1.6 + sx_) % (c.H * 1.2)
                d.line([(sx_, c.H - yy), (sx_, c.H - yy + c.H * 0.14)], fill=(220, 236, 255, 90), width=max(1, int(c.u * 0.3)))
        # the person
        sway = math.sin(t * 2.3) * 5
        ph = int(t * 9)
        fy = cy + math.sin(t * 2.0) * c.H * 0.006
        fx = cx
        sp = None
        alpha = 1.0
        if intro > 0 and t < intro * 0.35:
            fx = lx0 - figh * 0.45 + (lx0 + shaft_w * 0.2 - (lx0 - figh * 0.45)) * ease_io((t - intro * 0.1) / (intro * 0.22))
            sp = SP.person(figh, "stand" if t < intro * 0.12 else "fall", ph)
            fy = cy
        elif pose != "none":
            fy = cy
            if pose == "float":
                sp = SP.person(figh, "float", ph).rotate(t * 24 % 360, resample=Image.BICUBIC, expand=True)
                fx = cx + math.sin(t * 0.9) * shaft_w * 0.16
                fy = cy + math.cos(t * 0.7) * c.H * 0.03
            elif pose == "spread":
                sp = SP.person(figh, "spread", ph).rotate(sway * 0.6, resample=Image.BICUBIC, expand=True)
            else:
                sp = SP.person(figh, "fall", ph).rotate(sway, resample=Image.BICUBIC, expand=True)
        if burn:
            kb = max(0.0, min(1.0, (tp - 0.12) / 0.6))
            glw = SP.glow(int(figh * (2.0 + 3 * kb)), (255, 110, 40), 190)
            paste(img, glw, cx, cy)
            alpha = max(0.0, 1 - kb * 1.05)
            sparks(d, embers, t, (cx, cy), figh * 1.4 * (0.4 + kb), int(220 * min(1, kb * 2)), (255, 190, 90), c.u * 0.7)
        if shield and pose != "none":
            r = figh * 0.82
            sh = SP.glow(int(r * 2.5), (94, 225, 255), 80)
            paste(img, sh, cx, cy)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*CYAN, 170), width=max(2, int(c.u * 0.4)))
            d.arc([cx - r * 0.86, cy - r * 0.86, cx + r * 0.86, cy + r * 0.86], 200 + (t * 120) % 360, 250 + (t * 120) % 360, fill=(255, 255, 255, 200), width=max(2, int(c.u * 0.35)))
        if sp is not None:
            paste(img, sp, fx, fy, alpha)
        for kind, off, sc_ in floats:
            ang = t * 0.55 + off
            ox = cx + math.cos(ang) * shaft_w * 0.38
            oy = cy + math.sin(ang * 1.3) * figh * 0.9
            spr = SP.mug(int(figh * 0.26 * sc_)) if kind == "mug" else SP.phone(int(figh * 0.34 * sc_))
            paste(img, spr.rotate(t * 30 + off * 40, resample=Image.BICUBIC, expand=True), ox, oy)
        d = ImageDraw.Draw(img, "RGBA")

        # HUD (left wall)
        hx, hy = x0, y0 + (c.u * 6 if not c.vertical else c.u * 5)
        dv = D
        txt = f"{dv:,.0f}" if dv >= 100 else f"{dv:,.1f}"
        panel_w = (lx0 - x0) - c.u * 1.5 if not c.vertical else (lx0 - x0)
        if title and t < min(intro * 0.9 + 2.6, dur):
            fa = int(255 * max(0.0, min(1.0, (intro * 0.9 + 2.6 - t) / 0.5)))
            chip(d, x0, y0 + c.u * 5, title, font(s.display, int(c.u * (3.6 if not c.vertical else 4.4))), IVORY, alpha=fa)
        yb = hy + c.u * 6
        d.rounded_rectangle([hx - c.u, yb - c.u, hx + max(panel_w, c.u * 24), yb + f_depth.size * 1.9 + c.u * 3.2], radius=c.u * 1.2, fill=(6, 10, 24, 150))
        big_number(d, hx + c.u * 0.8, yb, txt, f_depth, " km", f_unit, IVORY, CYAN)
        d.text((hx + c.u * 0.8, yb + f_depth.size * 1.2), "depth", font=f_small, fill=rgb(s.muted))
        li_now = LAYER_NAME[layer]
        chip(d, hx + c.u * 0.4, yb + f_depth.size * 1.2 + c.u * 3.4, li_now, f_chip, (255, 255, 255), bg=tuple(int(v * 0.55) for v in LAYER_COL[layer]), alpha=235)
        if clock:
            m0, m1 = float(clock[0]), float(clock[1])
            chip(d, hx + c.u * 0.4, yb + f_depth.size * 1.2 + c.u * 8.6, f"{mmss(m0 + (m1 - m0) * min(1, tp))} elapsed", f_chip, IVORY, alpha=235)
        if speedo:
            cap, ghost, unit = float(speedo["cap"]), speedo.get("ghost"), speedo.get("unit", "km/h")
            sv = cap * (1 - math.exp(-tp * 5.0))
            sv = min(cap, sv)
            chip(d, hx + c.u * 0.4, yb + f_depth.size * 1.2 + c.u * 8.6, f"{sv:,.0f} {unit}", font(s.display, int(c.u * 4.4)), CYAN, alpha=240)
            if ghost and tp > 0.5:
                gk = ease((tp - 0.5) / 0.2)
                chip(d, hx + c.u * 0.4, yb + f_depth.size * 1.2 + c.u * 15, f"not {float(ghost):,.0f}", f_chip, rgb(s.muted), alpha=int(220 * gk))

        # layer name pops as each boundary is crossed
        if labels:
            for bi, ts_ in shown_layers.items():
                age = t - ts_
                if 0 <= age < 2.6 and D >= BOUNDS[bi - 1] - 40:
                    a = int(255 * min(1, age / 0.25) * min(1, (2.6 - age) / 0.5))
                    chip(d, lx1 + c.u * 2, y0 + (c.H * 0.14 if not c.vertical else c.H * 0.1), "Entering: " + LAYER_NAME[bi].split(":")[0], f_chip, (255, 255, 255), bg=tuple(int(v * 0.5) for v in LAYER_COL[bi]), alpha=a)

        # thermometer (qualitative fill; the one number is the narrated inner-core estimate)
        if temp:
            tx, ty0, ty1 = (x1 - c.u * 6 if not c.vertical else x1 - c.u * 8), y0 + (y1 - y0) * 0.24, y0 + (y1 - y0) * 0.64
            d.rounded_rectangle([tx - c.u * 1.5, ty0, tx + c.u * 1.5, ty1], radius=c.u * 1.5, fill=(8, 14, 34, 190), outline=(*IVORY, 120), width=max(1, int(c.u * 0.25)))
            frac = min(1.0, 0.1 + 0.9 * (D / 6371.0) ** 0.7)
            top_y = ty1 - (ty1 - ty0) * frac
            d.rounded_rectangle([tx - c.u * 1.0, top_y, tx + c.u * 1.0, ty1 - c.u * 0.4], radius=c.u, fill=mix((255, 150, 80), (255, 245, 200), frac) + (255,))
            if p.get("temp_label"):
                chip(d, tx, ty0 - c.u * 5.6, str(p["temp_label"]), f_chip, (255, 236, 190), alpha=240, anchor="c")
            if p.get("pressure_label"):
                chip(d, tx, ty1 + c.u * 1.6, str(p["pressure_label"]), f_small, IVORY, alpha=230, anchor="c")
        # the centre of the Earth: pulled equally from every side
        if centre and tp >= float(centre):
            kc = ease((tp - float(centre)) / 0.25)
            rr = figh * 0.7
            for a in range(8):
                ang = a * math.pi / 4
                for e in (1.0,):
                    sx_, sy_ = cx + math.cos(ang) * (rr * (2.1 - 0.4 * kc)), cy + math.sin(ang) * (rr * (2.1 - 0.4 * kc))
                    ex, ey = cx + math.cos(ang) * rr * 1.15, cy + math.sin(ang) * rr * 1.15
                    d.line([(sx_, sy_), (ex, ey)], fill=(*GOLD, int(230 * kc)), width=max(2, int(c.u * 0.5)))
                    d.ellipse([ex - c.u * 0.5, ey - c.u * 0.5, ex + c.u * 0.5, ey + c.u * 0.5], fill=(*GOLD, int(230 * kc)))
            chip(d, cx, cy + figh * 1.45, "pulled equally from every side: g = 0", f_chip, GOLD, alpha=int(245 * kc), anchor="c")
        yield img.convert("RGB")



# ---------- the Moon trip: a chase view and a race ----------
def _axis(c: Ctx, zn):
    """Map travel progress u in [0,1] and sideways v in [-1,1] to screen points: left to right on 16:9, bottom to top on 9:16."""
    x0, y0, x1, y1 = zn
    if c.vertical:
        cx, w = (x0 + x1) / 2, (x1 - x0) / 2
        return lambda u, v: (cx + v * w, y1 - u * (y1 - y0))
    cy, h = (y0 + y1) / 2, (y1 - y0) / 2
    return lambda u, v: (x0 + u * (x1 - x0), cy + v * h)


def _orient(c: Ctx, sp: Image.Image) -> Image.Image:
    return sp.rotate(90, expand=True) if c.vertical else sp


def _vehicle(kind: str, w: int, t: float):
    if kind == "jet":
        return SP.jet(w)
    if kind == "rocket":
        return SP.rocket(w, int(t * 12))
    return SP.car(w, int(t * 14) % 8)


def scene_journey(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """mode "chase": one vehicle drives, Earth shrinks behind it and the Moon grows ahead, with an odometer and a day clock.
    mode "race": several vehicles cross the same gap at their real speeds on one shared clock."""
    s = c.style
    mode = p.get("mode", "chase")
    dist = float(p.get("distance", 384400))
    zn = zone(c)
    ax = _axis(c, zn)
    x0, y0, x1, y1 = zn
    span = (y1 - y0) if c.vertical else (x1 - x0)
    cross = (x1 - x0) if c.vertical else (y1 - y0)
    f_big, f_unit = font(s.display, int(c.u * (9 if not c.vertical else 10))), font(s.display, int(c.u * 3.2))
    f_chip, f_small = font(s.display, int(c.u * 2.7)), font(s.body, int(c.u * 2.3))
    rng = random.Random(9)
    stars = [(rng.random(), rng.uniform(-1, 1), rng.uniform(0.3, 1.0)) for _ in range(70)]
    title = p.get("title")
    racers = p.get("racers", [])
    kind = p.get("vehicle", "car")
    kmh = float(p.get("kmh", 100))
    p0, p1 = float(p.get("p0", 0.0)), float(p.get("p1", 1.0))
    hours_total = float(p.get("hours", dist / kmh))
    unit = p.get("clock_unit", "days")
    big_mode = p.get("big", "odometer")
    Tmax = max(dist / float(r["kmh"]) for r in racers) if racers else 0.0
    finish_times: dict[int, float] = {}
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        k = t / dur
        # stars streaming back along the axis, so something is always moving
        flow = (t * 0.55) if mode == "chase" else 0.0
        for (su, sv, sz) in stars:
            u = (su - flow * sz) % 1.0
            x, y = ax(u, sv * 0.95)
            ln = c.u * (2.0 + 6 * sz) * (1 if mode == "chase" else 0.2)
            dx, dy = (0, ln) if c.vertical else (ln, 0)
            d.line([(x, y), (x + dx, y + dy)], fill=(220, 236, 255, int(70 + 120 * sz)), width=max(1, int(c.u * 0.28)))
        if mode == "chase":
            pr = p0 + (p1 - p0) * ease_io(k)
            ex, ey = ax(-0.12 - 0.38 * pr, 0.0)
            er = (cross * 0.5) * (0.95 - 0.7 * pr)
            paste(img, SP.glow(int(er * 3.2), (94, 225, 255), 120), ex, ey)
            paste(img, SP.earth_ball(max(6, int(er))), ex, ey)
            mx, my = ax(1.45 - 0.7 * pr, 0.42 if c.vertical else -0.1)
            mr = cross * (0.06 + 0.17 * pr)
            paste(img, SP.moon(max(6, int(mr))), mx, my)
            # the road: dashes sliding back
            lane_v = 0.30
            for q in range(30):
                u = (q / 30 - flow * 2.0) % 1.0
                ax0, ay0 = ax(u, lane_v)
                ax1, ay1 = ax(u + 0.015, lane_v)
                d.line([(ax0, ay0), (ax1, ay1)], fill=(*IVORY, 150), width=max(2, int(c.u * 0.55)))
            vw = int(cross * (0.30 if kind == "car" else 0.42))
            vx, vy = ax(0.32, (lane_v if c.vertical else lane_v - 0.13) + (0.012 * math.sin(t * 9) if kind == "car" else 0))
            if kind == "rocket":
                vx, vy = ax(0.32, 0.0)
            sp = _orient(c, _vehicle(kind, vw, t))
            if kind in ("jet", "rocket"):
                paste(img, SP.glow(int(vw * 1.2), (255, 190, 90), 90), vx - (0 if c.vertical else vw * 0.45), vy + (vw * 0.45 if c.vertical else 0))
            paste(img, sp, vx, vy)
            km = dist * pr
            hrs = (hours_total) * pr
            clock_v = hrs / 24.0 if unit == "days" else hrs
            if big_mode == "odometer":
                txt, un = f"{km:,.0f}", "km"
                lab = p.get("label", "driven")
            else:
                txt, un = (f"{clock_v:,.0f}" if clock_v >= 10 else f"{clock_v:,.1f}"), unit
                lab = p.get("label", "elapsed")
            hx, hy = x0, y0 + c.u * 5.2
            d.rounded_rectangle([hx - c.u, hy - c.u, hx + c.u * (30 if not c.vertical else 44), hy + f_big.size * 1.75 + c.u * 5.8], radius=c.u * 1.2, fill=(6, 10, 24, 150))
            big_number(d, hx + c.u * 0.8, hy, txt, f_big, " " + un, f_unit, IVORY, CYAN)
            d.text((hx + c.u * 0.8, hy + f_big.size * 1.15), lab, font=f_small, fill=rgb(s.muted))
            sub = f"{clock_v:,.0f} {unit}" if big_mode == "odometer" else f"{km:,.0f} km"
            chip(d, hx + c.u * 0.4, hy + f_big.size * 1.15 + c.u * 3.2, sub, f_chip, IVORY, alpha=235)
            if title and t < 3.2:
                fa = int(255 * max(0.0, min(1.0, (3.2 - t) / 0.5)))
                chip(d, x0, y1 - c.u * 7 if c.vertical else y0 + c.u * 0.2, title, font(s.display, int(c.u * 3.6)), IVORY, alpha=fa)
        else:
            sim = Tmax * (min(1.0, t / (dur * 0.88)) ** 2.0)           # shared clock, hours
            n = len(racers)
            # the track, its distance ticks, Earth at the start, Moon at the end
            for q in range(n):
                v = (-0.62 + 1.24 * (q + 0.5) / n) if n > 1 else 0.0
                a_, b_ = ax(0.0, v), ax(1.0, v)
                d.line([a_, b_], fill=(*IVORY, 55), width=max(2, int(c.u * 0.4)))
            for tick in range(1, int(dist // 100000) + 1):
                u = tick * 100000 / dist
                tx_, ty_ = ax(u, 0.86)
                d.line([ax(u, -0.78), ax(u, 0.78)], fill=(*IVORY, 26), width=max(1, int(c.u * 0.25)))
                d.text((tx_, ty_), f"{tick * 100}k km", font=f_small, fill=(*rgb(s.muted), 180), anchor="mm")
            er = cross * 0.34
            ex, ey = ax(-0.02, 0)
            paste(img, SP.earth_ball(int(er)), ex - (0 if c.vertical else er * 0.15), ey + (er * 0.15 if c.vertical else 0))
            mx, my = ax(1.04, 0)
            paste(img, SP.moon(int(cross * 0.1)), mx, my)
            for q, r in enumerate(racers):
                v = (-0.62 + 1.24 * (q + 0.5) / n) if n > 1 else 0.0
                spd = float(r["kmh"])
                u = min(1.0, sim * spd / dist)
                x, y = ax(0.05 + u * 0.9, v)
                vw = int(cross * (0.30 if n <= 2 else 0.22))
                kd = r.get("kind", "car")
                if u > 0 and u < 1 and kd in ("jet", "rocket"):
                    tx0, ty0 = ax(0.05, v)
                    d.line([(tx0, ty0), (x, y)], fill=(255, 220, 140, 70), width=max(2, int(c.u * 0.8)))
                paste(img, _orient(c, _vehicle(kd, vw, t)), x, y - (0 if c.vertical else vw * 0.06))
                finish = dist / spd
                # the label sits at the start of its lane the whole time; the result pops at the Moon end
                lx_, ly_ = ax(0.035, v)
                chip(d, lx_, ly_ - (f_chip.size * 2.0 if not c.vertical else 0), r.get("label", ""), font(s.display, int(c.u * (2.2 if n > 2 else 2.7))), IVORY, alpha=220, anchor="c" if c.vertical else "l")
                if sim >= finish:
                    finish_times.setdefault(q, t)
                    age = t - finish_times[q]
                    days = finish / 24.0
                    rx_, ry_ = ax(0.8, v)
                    chip(d, rx_, ry_ + (0 if c.vertical else -f_chip.size * 2.1), f"{days:,.0f} days", font(s.display, int(c.u * (3.2 if n > 2 else 3.6))), (255, 255, 255) if r.get("hi") else IVORY, bg=(36, 130, 96) if r.get("hi") else (8, 14, 34), alpha=int(255 * min(1, age / 0.25)), anchor="c" if c.vertical else "r")
            days_now = sim / 24.0
            hx, hy = x0, y0 + c.u * 1.2
            chip(d, hx, hy, f"day {days_now:,.0f}", font(s.display, int(c.u * 4.6)), CYAN, alpha=245)
            if p.get("title") and t < 2.6:
                pass
        yield img.convert("RGB")


def scene_pips(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """A calendar filling up, one square per day, with a counter and a tiny car crawling along a bar."""
    s = c.style
    n = int(p.get("days", 160))
    x0, y0, x1, y1 = zone(c)
    cols = 16 if not c.vertical else 10
    rows = math.ceil(n / cols)
    gap = c.u * 0.7
    cw = ((x1 - x0) - gap * (cols - 1)) / cols
    ch = min(cw, ((y1 - y0) * 0.62 - gap * (rows - 1)) / rows)
    cw = min(cw, ch * 1.4)
    gx = x0 + ((x1 - x0) - (cw * cols + gap * (cols - 1))) / 2
    gy = y0 + (y1 - y0) * 0.26
    f_big, f_unit, f_chip = font(s.display, int(c.u * (11 if not c.vertical else 12))), font(s.display, int(c.u * 3.4)), font(s.display, int(c.u * 2.7))
    unit = p.get("unit", "days")
    label = p.get("label", "driving non-stop")
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        k = ease_io(t / (dur * 0.9))
        filled = n * k
        for q in range(n):
            r_, c_ = divmod(q, cols)
            xx, yy = gx + c_ * (cw + gap), gy + r_ * (ch + gap)
            if q < int(filled):
                d.rounded_rectangle([xx, yy, xx + cw, yy + ch], radius=c.u * 0.5, fill=(*CYAN, 235))
            elif q == int(filled):
                frac = filled - int(filled)
                d.rounded_rectangle([xx, yy, xx + cw, yy + ch], radius=c.u * 0.5, fill=(*CYAN, int(60 + 190 * frac)))
            else:
                d.rounded_rectangle([xx, yy, xx + cw, yy + ch], radius=c.u * 0.5, fill=(*IVORY, 26))
        big_number(d, x0, y0 + c.u * 1.5, f"{filled:,.0f}", f_big, " " + unit, f_unit, IVORY, CYAN)
        d.text((x0, y0 + c.u * 1.5 + f_big.size * 1.15), label, font=font(s.body, int(c.u * 2.6)), fill=rgb(s.muted))
        # a car crawling along a bar that spans the whole trip
        by = y1 - (y1 - y0) * 0.08
        d.rounded_rectangle([x0, by, x1, by + c.u * 1.1], radius=c.u * 0.55, fill=(*IVORY, 40))
        d.rounded_rectangle([x0, by, x0 + (x1 - x0) * k, by + c.u * 1.1], radius=c.u * 0.55, fill=(*CORAL, 255))
        paste(img, SP.car(int(c.u * 9), int(t * 14) % 8), x0 + (x1 - x0) * k, by - c.u * 1.6)
        yield img.convert("RGB")


def scene_tank(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """A grid of 1,000-litre tanks filling one after another while the litre counter climbs."""
    s = c.style
    litres = float(p.get("litres", 26900))
    per = float(p.get("per", 1000))
    n = math.ceil(litres / per)
    x0, y0, x1, y1 = zone(c)
    cols = 9 if not c.vertical else 5
    rows = math.ceil(n / cols)
    gap = c.u * 1.0
    cw = ((x1 - x0) - gap * (cols - 1)) / cols
    chh = min(cw * 1.05, ((y1 - y0) * 0.62 - gap * (rows - 1)) / rows)
    gx = x0 + ((x1 - x0) - (cw * cols + gap * (cols - 1))) / 2
    gy = y0 + (y1 - y0) * 0.30
    f_big, f_unit, f_chip, f_small = font(s.display, int(c.u * (11 if not c.vertical else 12))), font(s.display, int(c.u * 3.4)), font(s.display, int(c.u * 2.7)), font(s.body, int(c.u * 2.1))
    label = p.get("label", "of fuel")
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        k = ease_io(t / (dur * 0.85))
        cur = litres * k
        for q in range(n):
            r_, c_ = divmod(q, cols)
            xx, yy = gx + c_ * (cw + gap), gy + r_ * (chh + gap)
            fill = max(0.0, min(1.0, cur / per - q))
            full_here = min(1.0, (litres - q * per) / per)
            d.rounded_rectangle([xx, yy, xx + cw, yy + chh], radius=c.u * 0.8, outline=(*IVORY, 130), width=max(1, int(c.u * 0.28)), fill=(*IVORY, 14))
            if fill > 0:
                top = min(yy + chh * (1 - fill * full_here), yy + chh - c.u * 1.2)
                wob = math.sin(t * 6 + q) * c.u * 0.18 * min(1, fill * 8)
                d.rounded_rectangle([xx + c.u * 0.3, min(top + wob, yy + chh - c.u * 0.9), xx + cw - c.u * 0.3, yy + chh - c.u * 0.3], radius=c.u * 0.5, fill=(*GOLD, 235))
                if 0 < fill < 1:
                    d.line([(xx + cw / 2, y0 + (y1 - y0) * 0.22), (xx + cw / 2, top)], fill=(*GOLD, 220), width=max(2, int(c.u * 0.5)))
        big_number(d, x0, y0 + c.u * 1.5, f"{cur:,.0f}", f_big, " litres", f_unit, IVORY, GOLD)
        d.text((x0, y0 + c.u * 1.5 + f_big.size * 1.15), label, font=font(s.body, int(c.u * 2.6)), fill=rgb(s.muted))
        d.text((gx, gy + rows * (chh + gap) + c.u * 0.8), f"each box = {per:,.0f} litres", font=f_small, fill=rgb(s.muted))
        yield img.convert("RGB")



# ---------- earth cutaway helper in the warm palette ----------
def earth_cut(img: Image.Image, d: ImageDraw.ImageDraw, cx: float, cy: float, R: float, reveal: float = 1.0, rim: bool = True):
    """Mantle, liquid outer core, solid inner core, a thin crust ring. reveal 0..1 builds it from the outside in."""
    fr = (1.0, PH.R_OUTER_CORE / PH.R, PH.R_INNER_CORE / PH.R)
    cols = (LAYER_COL[1], LAYER_COL[2], LAYER_COL[3])
    for i, (f, col) in enumerate(zip(fr, cols)):
        k = max(0.0, min(1.0, reveal * 3 - i))
        if k <= 0:
            continue
        r = R * f
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*col, int(255 * k)))
    if rim and reveal > 0:
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(*LAYER_COL[0], 255), width=max(3, int(R * 0.035)))


# ---------- descents: the Kola borehole and the Mariana Trench ----------
def scene_descent(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """A side-on cut through the ground or the sea with a counter. mode "rock": a drill goes down (Kola, 12.262 km), with
    optional years and a heat gauge. mode "ocean": the 10,935 m trench, Everest standing on its floor, a submersible."""
    s = c.style
    mode = p.get("mode", "rock")
    x0, y0, x1, y1 = zone(c)
    f_big, f_unit = font(s.display, int(c.u * (8 if not c.vertical else 9))), font(s.display, int(c.u * 3))
    f_chip, f_small = font(s.display, int(c.u * 2.7)), font(s.body, int(c.u * 2.2))
    rng = random.Random(4)
    top = y0 + (y1 - y0) * (0.14 if not c.vertical else 0.21)
    bot = y1 - (y1 - y0) * 0.04
    colx0, colx1 = (x0 + (x1 - x0) * 0.26, x1 - (x1 - x0) * 0.04) if not c.vertical else (x0 + (x1 - x0) * 0.22, x1)
    cxm = (colx0 + colx1) / 2
    sparks_l = [(rng.uniform(-math.pi, 0), rng.uniform(30, 90), rng.random() * 2, rng.uniform(0.4, 0.9)) for _ in range(24)]
    years = p.get("years")
    heat = p.get("heat")
    title = p.get("title")
    note = p.get("note")
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        k = ease_io(t / (dur * 0.86))
        if mode == "rock":
            dmax = float(p.get("depth", 12.262))       # km
            ppk = (bot - top) / (dmax * 1.04)
            cur = dmax * (float(p.get("from", 0.0)) + (1 - float(p.get("from", 0.0))) * k)
            # strata
            bands = [(0, 0.12, (86, 98, 128)), (0.12, 0.34, (74, 84, 112)), (0.34, 0.6, (64, 72, 98)), (0.6, 1.1, (54, 60, 84))]
            for a, b, col in bands:
                d.rectangle([colx0, top + a * (bot - top), colx1, top + min(1.0, b) * (bot - top)], fill=(*col, 255))
            d.rectangle([colx0, top - c.u * 1.2, colx1, top], fill=(*LAYER_COL[0], 255))
            # ruler
            for km in range(0, int(dmax) + 1, 2):
                yy = top + km * ppk
                d.line([(colx0 - c.u * 2.4, yy), (colx0, yy)], fill=(*IVORY, 150), width=max(1, int(c.u * 0.3)))
                d.text((colx0 - c.u * 3.0, yy), f"{km} km", font=f_small, fill=(*IVORY, 190), anchor="rm")
            # derrick
            dx_ = cxm
            d.polygon([(dx_ - c.u * 3, top), (dx_ + c.u * 3, top), (dx_ + c.u * 0.8, top - c.u * 9), (dx_ - c.u * 0.8, top - c.u * 9)], outline=(*IVORY, 230), width=max(2, int(c.u * 0.4)))
            ty = top + cur * ppk
            d.line([(dx_, top), (dx_, ty)], fill=(*IVORY, 240), width=max(2, int(c.u * 0.5)))
            # hole behind the drill
            d.rectangle([dx_ - c.u * 0.45, top, dx_ + c.u * 0.45, ty], fill=(4, 6, 16, 255))
            hot = 0.0
            if heat:
                hot = ease((t - dur * 0.45) / (dur * 0.4))
            tip = mix((94, 225, 255), (255, 90, 60), hot)
            paste(img, SP.glow(int(c.u * 14), tip, 200), dx_, ty)
            d.ellipse([dx_ - c.u * 1.1, ty - c.u * 1.1, dx_ + c.u * 1.1, ty + c.u * 1.1], fill=(*tip, 255))
            sparks(d, sparks_l, t, (dx_, ty), c.u * 6, 220, tip, c.u * 0.45)
            oy = c.u * (3.4 if c.vertical else 0.5)
            big_number(d, x0 + c.u * 0.5, y0 + oy, f"{cur:,.3f}" if cur < 100 else f"{cur:,.0f}", f_big, " km", f_unit, IVORY, CYAN)
            d.text((x0 + c.u * 0.5, y0 + oy + f_big.size * 1.15), "deep", font=f_small, fill=rgb(s.muted))
            if years:
                y_a, y_b = float(years[0]), float(years[1])
                yr = y_a + (y_b - y_a) * min(1.0, k * 1.1)
                chip(d, colx1, y0 + c.u * 0.5, f"{int(yr)}", font(s.display, int(c.u * 6)), GOLD, alpha=245, anchor="r")
            if heat:
                gx, gy0, gy1 = colx1 - c.u * 7, top + (bot - top) * 0.10, top + (bot - top) * 0.80
                d.rounded_rectangle([gx - c.u * 1.5, gy0, gx + c.u * 1.5, gy1], radius=c.u * 1.5, fill=(6, 10, 24, 200), outline=(*IVORY, 130), width=max(1, int(c.u * 0.25)))
                tmax = 200.0
                for val, lab, col in ((100, "expected 100 °C", CYAN), (180, "found 180 °C", (255, 120, 90))):
                    yy = gy1 - (gy1 - gy0) * val / tmax
                    d.line([(gx - c.u * 2.4, yy), (gx + c.u * 2.4, yy)], fill=(*col, 255), width=max(2, int(c.u * 0.4)))
                    kk = ease((t - dur * (0.3 if val == 100 else 0.55)) / 0.5)
                    if kk > 0:
                        chip(d, gx - c.u * 3.2, yy - f_chip.size * 0.9, lab, f_chip, col, alpha=int(245 * kk), anchor="r")
                fill_v = 15 + (180 - 15) * hot
                d.rounded_rectangle([gx - c.u * 0.9, gy1 - (gy1 - gy0) * fill_v / tmax, gx + c.u * 0.9, gy1 - c.u * 0.3], radius=c.u * 0.9, fill=(*mix(CYAN, (255, 90, 60), hot), 255))
            if note and k > 0.9:
                chip(d, cxm, bot - c.u * 7, note, f_chip, GOLD, alpha=245, anchor="c")
        else:
            floor_m = float(p.get("floor", 10935))
            ev_m = float(p.get("everest", 8849))
            ppm = (bot - top) / (floor_m * 1.0)
            # water, darker with depth
            for q in range(40):
                a_ = q / 40
                col = mix((34, 110, 170), (4, 10, 30), a_ ** 0.8)
                d.rectangle([colx0, top + a_ * (bot - top), colx1, top + (a_ + 1 / 40) * (bot - top) + 1], fill=(*col, 255))
            d.rectangle([x0, top - c.u * 0.6, colx0, bot], fill=(10, 16, 36, 255))
            # surface waves
            for wx in range(int(colx0), int(colx1), 6):
                wy = top + math.sin(wx * 0.04 + t * 2.4) * c.u * 0.45
                d.line([(wx, wy), (wx + 6, wy)], fill=(200, 235, 255, 200), width=max(2, int(c.u * 0.5)))
            # floor: a V trench with a flat bottom
            fy = bot - c.u * 0.5
            d.polygon([(colx0, top + (bot - top) * 0.80), (colx0 + (colx1 - colx0) * 0.18, fy), (colx1 - (colx1 - colx0) * 0.18, fy), (colx1, top + (bot - top) * 0.80), (colx1, bot + c.u * 3), (colx0, bot + c.u * 3)], fill=(70, 62, 78, 255))
            # ruler every 1,000 m
            for m in range(0, int(floor_m) + 1, 1000):
                yy = top + m * ppm
                d.line([(colx0 - c.u * 2.2, yy), (colx0, yy)], fill=(*IVORY, 170), width=max(1, int(c.u * 0.3)))
                d.text((colx0 - c.u * 2.8, yy), f"{m:,} m", font=f_small, fill=(*IVORY, 200), anchor="rm")
            # Everest on the trench floor
            mk = ease((t - dur * float(p.get("m_at", 0.0))) / (dur * float(p.get("m_for", 0.3)))) if p.get("mountain") else 0.0
            if mk > 0:
                mw = (colx1 - colx0) * 0.66
                mh = ev_m * ppm * mk
                pts = [(-0.5, 0), (-0.32, 0.30), (-0.22, 0.26), (-0.12, 0.62), (-0.05, 0.7), (0, 1.0), (0.08, 0.74), (0.18, 0.58), (0.26, 0.40), (0.34, 0.30), (0.5, 0)]
                poly = [(cxm + px * mw, fy - py * mh) for px, py in pts]
                d.polygon(poly, fill=(120, 108, 132, 255))
                cap = [(cxm + px * mw, fy - py * mh) for px, py in [(-0.07, 0.72), (-0.05, 0.7), (0, 1.0), (0.08, 0.74), (0.1, 0.8), (0.03, 0.88), (-0.02, 0.84)]]
                d.polygon(cap, fill=(*IVORY, 255))
                peak_y = fy - mh
                if mk > 0.95 or p.get("bracket"):
                    chip(d, cxm, fy - c.u * 6.5, "Mount Everest", f_chip, IVORY, alpha=240, anchor="c")
                if p.get("bracket"):
                    bk = ease((t - dur * float(p.get("b_at", 0.0))) / (dur * 0.3))
                    if bk > 0:
                        d.line([(cxm, top), (cxm, top + (peak_y - top) * bk)], fill=(*GOLD, 235), width=max(2, int(c.u * 0.5)))
                        for dy_ in range(int(top), int(top + (peak_y - top) * bk), int(c.u * 2.2)):
                            pass
                        if bk > 0.85:
                            chip(d, colx1 - c.u * 1, (top + peak_y) / 2 - f_chip.size * 0.6, f"{floor_m - ev_m:,.0f} m of water", f_chip, GOLD, alpha=245, anchor="r")
            if p.get("band"):
                bk = 0.5 + 0.5 * math.sin(t * 3)
                d.rectangle([colx0, fy - c.u * 1.3 * (0.6 + bk * 0.4), colx1, fy], fill=(255, 220, 120, 50))
                chip(d, cxm, fy - c.u * 13.5, "surveys differ by tens of metres", f_chip, GOLD, alpha=235, anchor="c")
            # submersible
            sub = p.get("sub")
            if sub:
                end_m = float(sub.get("to", floor_m)) if isinstance(sub, dict) else floor_m
                sk = ease_io((t - dur * float(sub.get("at", 0.0) if isinstance(sub, dict) else 0.0)) / (dur * float(sub.get("for", 0.8) if isinstance(sub, dict) else 0.8)))
                sy = top + end_m * ppm * sk - (c.u * 2 if mk > 0 and end_m > floor_m * 0.9 else 0)
                paste(img, SP.glow(int(c.u * 22), (255, 230, 150), 130), cxm + c.u * 0.0, sy)
                d.rounded_rectangle([cxm - c.u * 3.4, sy - c.u * 1.8, cxm + c.u * 3.4, sy + c.u * 1.8], radius=c.u * 1.6, fill=(*GOLD, 255))
                d.ellipse([cxm + c.u * 0.8, sy - c.u * 0.9, cxm + c.u * 2.6, sy + c.u * 0.9], fill=(30, 50, 90, 255))
                d.line([(cxm, top), (cxm, sy - c.u * 1.8)], fill=(255, 255, 255, 40), width=1)
                cur_m = end_m * sk
            else:
                cur_m = float(p.get("counter_value", floor_m)) * (ease_io(t / (dur * 0.8)) if p.get("counter") == "grow" else 1.0)
            label = p.get("label", "deep")
            if p.get("counter") == "grow" and not sub:
                cur_m = float(p.get("counter_value", floor_m)) * ease_io(t / (dur * 0.7))
            oy = c.u * (3.4 if c.vertical else 0.5)
            big_number(d, x0 + c.u * 0.5, y0 + oy, f"{cur_m:,.0f}", f_big, " m", f_unit, IVORY, CYAN)
            d.text((x0 + c.u * 0.5, y0 + oy + f_big.size * 1.15), label, font=f_small, fill=rgb(s.muted))
        if title and t < 3.0:
            chip(d, x0, y1 - c.u * 6, title, font(s.display, int(c.u * 3.2)), IVORY, alpha=int(255 * min(1, (3.0 - t) / 0.4)))
        yield img.convert("RGB")


def scene_columns(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """Sea level in the middle; bars grow up (a mountain) and down (a trench, a borehole) at the same time."""
    s = c.style
    items = p["items"]          # [{label, value (km), dir: up|down, kind: mountain|water|rock}]
    x0, y0, x1, y1 = zone(c)
    vmax = max(float(it["value"]) for it in items)
    up_max = max([float(it["value"]) for it in items if it["dir"] == "up"] or [0.0])
    dn_max = max([float(it["value"]) for it in items if it["dir"] == "down"] or [0.0])
    f_chip, f_val = font(s.display, int(c.u * 2.7)), font(s.display, int(c.u * 4.6))
    total = up_max + dn_max
    ppk = (y1 - y0) * 0.70 / total
    sea = y0 + (y1 - y0) * 0.14 + up_max * ppk
    n = len(items)
    bw = (x1 - x0) / (n * 1.6)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        d.rectangle([x0, sea, x1, y1], fill=(14, 30, 64, 120))
        d.line([(x0, sea), (x1, sea)], fill=(*CYAN, 230), width=max(2, int(c.u * 0.5)))
        d.text((x0, sea - f_chip.size * 1.5), "sea level", font=font(s.body, int(c.u * 2.2)), fill=rgb(s.muted))
        for j, it in enumerate(items):
            k = ease((t - 0.3 - j * 0.35) / (dur * 0.55))
            v = float(it["value"]) * k
            xc = x0 + (x1 - x0) * (j + 0.5) / n
            col = {"mountain": (146, 134, 160), "water": (46, 150, 210), "rock": (206, 120, 86)}.get(it.get("kind", "rock"), CYAN)
            if it["dir"] == "up":
                ytop = sea - v * ppk
                d.polygon([(xc - bw * 0.7, sea), (xc - bw * 0.2, ytop + (sea - ytop) * 0.25), (xc, ytop), (xc + bw * 0.25, ytop + (sea - ytop) * 0.3), (xc + bw * 0.7, sea)], fill=(*col, 255))
                ly = ytop - f_val.size * 1.5
            else:
                d.rectangle([xc - bw * 0.35, sea, xc + bw * 0.35, sea + v * ppk], fill=(*col, 255))
                ly = sea + v * ppk + c.u * 1.0
                paste(img, SP.glow(int(c.u * 9), col, 160), xc, sea + v * ppk)
            d.text((xc, ly), f"{v:,.2f} km", font=f_val, fill=IVORY, anchor="mt")
            chip(d, xc, (y1 - c.u * 6.5) if c.vertical else (y1 - c.u * 4.5), it["label"], f_chip, IVORY, alpha=235, anchor="c")
        yield img.convert("RGB")


# ---------- seismic waves: why we know what is inside ----------
def scene_seismic(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    x0, y0, x1, y1 = zone(c)
    R = (y1 - y0) * 0.40
    cx, cy = x0 + (x1 - x0) * 0.40, (y0 + y1) / 2 - R * 0.05
    if c.vertical:
        cx, cy, R = (x0 + x1) / 2, y0 + (y1 - y0) * 0.40, (x1 - x0) * 0.40
    f_chip, f_small = font(s.display, int(c.u * 2.7)), font(s.body, int(c.u * 2.2))
    q_ang = math.radians(-135)
    qx, qy = cx + R * math.cos(q_ang), cy + R * math.sin(q_ang)
    core_r = R * PH.R_OUTER_CORE / PH.R
    # rays toward detectors on the far side; the S waves stop at the liquid core
    det_angles = [math.radians(a) for a in range(-80, 62, 20)]
    det = [(cx + R * math.cos(a), cy + R * math.sin(a), a) for a in det_angles]

    def seg_hit_core(ax_, ay_, bx_, by_):
        dx, dy = bx_ - ax_, by_ - ay_
        fx, fy = ax_ - cx, ay_ - cy
        a = dx * dx + dy * dy
        b = 2 * (fx * dx + fy * dy)
        cc = fx * fx + fy * fy - core_r ** 2
        disc = b * b - 4 * a * cc
        if disc <= 0:
            return None
        sq = math.sqrt(disc)
        t1 = (-b - sq) / (2 * a)
        return t1 if 0 < t1 < 1 else None
    trace_pts: list[float] = []
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        earth_cut(img, d, cx, cy, R, 1.0)
        pw = max(0.0, min(1.0, (t - 0.8) / (dur * 0.5)))
        sw = pw * 0.62
        # the quake
        for ring in range(3):
            kk = ((t * 0.9 + ring / 3) % 1.0)
            rr = c.u * (1 + 6 * kk)
            d.ellipse([qx - rr, qy - rr, qx + rr, qy + rr], outline=(255, 255, 255, int(220 * (1 - kk))), width=max(2, int(c.u * 0.4)))
        d.ellipse([qx - c.u, qy - c.u, qx + c.u, qy + c.u], fill=(255, 255, 255, 255))
        for (dx_, dy_, ang) in det:
            tc = seg_hit_core(qx, qy, dx_, dy_)
            # P wave goes straight through (a slight bend would be hidden at this size)
            ex, ey = qx + (dx_ - qx) * pw, qy + (dy_ - qy) * pw
            d.line([(qx, qy), (ex, ey)], fill=(*CYAN, 200), width=max(2, int(c.u * 0.35)))
            if pw > 0.02:
                d.ellipse([ex - c.u * 0.7, ey - c.u * 0.7, ex + c.u * 0.7, ey + c.u * 0.7], fill=(*CYAN, 255))
            # S wave: stops where it meets liquid
            lim = tc if tc is not None else 1.0
            sk = min(lim, sw)
            nx_, ny_ = -(dy_ - qy), (dx_ - qx)
            nl_ = math.hypot(nx_, ny_) or 1.0
            ox_, oy_ = nx_ / nl_ * c.u * 0.55, ny_ / nl_ * c.u * 0.55
            sx_, sy_ = qx + (dx_ - qx) * sk + ox_, qy + (dy_ - qy) * sk + oy_
            d.line([(qx + ox_, qy + oy_), (sx_, sy_)], fill=(*CORAL, 235), width=max(2, int(c.u * 0.4)))
            if sk < 0.999 and sw > 0.02 and (tc is None or sw < tc):
                d.ellipse([sx_ - c.u * 0.6, sy_ - c.u * 0.6, sx_ + c.u * 0.6, sy_ + c.u * 0.6], fill=(*CORAL, 255))
            if tc is not None and sw >= tc:
                d.line([(sx_ - c.u * 0.8, sy_ - c.u * 0.8), (sx_ + c.u * 0.8, sy_ + c.u * 0.8)], fill=(255, 255, 255, 255), width=max(2, int(c.u * 0.5)))
                d.line([(sx_ - c.u * 0.8, sy_ + c.u * 0.8), (sx_ + c.u * 0.8, sy_ - c.u * 0.8)], fill=(255, 255, 255, 255), width=max(2, int(c.u * 0.5)))
            # detector lights up when the P wave arrives; S only where it got through
            on_p = pw >= 0.999
            on_s = tc is None and sw >= 0.999
            d.ellipse([dx_ - c.u * 1.1, dy_ - c.u * 1.1, dx_ + c.u * 1.1, dy_ + c.u * 1.1], fill=(*CYAN, 255) if on_p else (40, 52, 90, 255), outline=(*IVORY, 200), width=max(1, int(c.u * 0.25)))
            if on_s:
                d.ellipse([dx_ - c.u * 0.5, dy_ - c.u * 0.5, dx_ + c.u * 0.5, dy_ + c.u * 0.5], fill=(*CORAL, 255))
        # legend, plus a seismograph that shows the waves arriving on the far side
        lx = x1 - c.u * 1 if not c.vertical else x0
        ly = y0 + c.u * 4 if not c.vertical else y1 - c.u * 26
        ax_ = lx if c.vertical else (x0 + (x1 - x0) * 0.72)
        chip(d, ax_, ly, "P wave: passes through", f_chip, CYAN, alpha=245)
        chip(d, ax_, ly + f_chip.size * 2.0, "S wave: stops at liquid", f_chip, CORAL, alpha=245)
        sg0x, sg1x = ax_, (x1 if not c.vertical else x1)
        sgy = ly + f_chip.size * 6.0
        sgw = (sg1x - sg0x) * (0.95 if not c.vertical else 1.0)
        d.rounded_rectangle([sg0x, sgy, sg0x + sgw, sgy + c.u * 14], radius=c.u, fill=(6, 10, 24, 170))
        d.line([(sg0x, sgy + c.u * 7), (sg0x + sgw, sgy + c.u * 7)], fill=(*IVORY, 60), width=1)
        arrive = 0.999
        amp = 0.0
        if pw >= arrive:
            amp = math.exp(-((t - (0.8 + dur * 0.5)) * 1.2)) * 1.0
        val = amp * math.sin(t * 38) * c.u * 4.5 + math.sin(t * 7) * c.u * 0.18
        trace_pts.append(val)
        trace_pts[:] = trace_pts[-int(sgw / 3):]
        pts = [(sg0x + sgw - (len(trace_pts) - j) * 3, sgy + c.u * 7 + v_) for j, v_ in enumerate(trace_pts)]
        if len(pts) > 1:
            d.line(pts, fill=(*CYAN, 255), width=max(2, int(c.u * 0.4)))
        d.text((sg0x + c.u, sgy + c.u * 0.5), "seismograph, far side", font=f_small, fill=(*rgb(s.muted), 230))
        yield img.convert("RGB")



# ---------- scale: how small a 12 km hole is next to 6,371 km ----------
def _nice(step: float) -> float:
    e = 10 ** math.floor(math.log10(step))
    for m in (1, 2, 5, 10):
        if m * e >= step:
            return m * e
    return 10 * e


def scene_scale(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    total = float(p.get("total", 6371))
    part = float(p.get("part", 12.262))
    x0, y0, x1, y1 = zone(c)
    bw = x1 - x0
    by = y0 + (y1 - y0) * 0.50
    bh = c.u * 4.5
    f_chip, f_small, f_big = font(s.display, int(c.u * 2.9)), font(s.body, int(c.u * 2.2)), font(s.display, int(c.u * 7.5))
    zmax = bw / (part / total * bw) * 0.98            # zoom at which the sliver fills the bar
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        k = ease_io((t - 0.6) / (dur * 0.62))
        Z = math.exp(math.log(zmax) * k)
        # Earth disk fades as we zoom in
        fa = max(0.0, 1 - k * 2.2)
        if fa > 0:
            er = (y1 - y0) * 0.2
            earth_cut(img, d, x1 - er * 1.1, by - (y1 - y0) * 0.24, er, 1.0)
            d.line([(x1 - er * 1.1, by - (y1 - y0) * 0.24 - er), (x1 - er * 1.1, by - (y1 - y0) * 0.24)], fill=(255, 255, 255, int(200 * fa)), width=max(2, int(c.u * 0.4)))
        # the bar, from the surface (left) towards the centre (right, off screen when zoomed)
        d.rounded_rectangle([x0, by, x0 + bw * Z, by + bh], radius=c.u * 0.8, fill=(*IVORY, 40)) if bw * Z < bw * 4000 else None
        d.rectangle([x0, by, min(x1 + 100, x0 + bw * Z), by + bh], fill=(*IVORY, 46))
        pw_ = bw * Z * part / total
        d.rectangle([x0, by, min(x1 + 100, x0 + pw_), by + bh], fill=(*CORAL, 255))
        step = _nice(total * (c.u * 22) / (bw * Z))
        km = 0.0
        while km <= total and x0 + bw * Z * km / total < x1 + 5:
            xx = x0 + bw * Z * km / total
            d.line([(xx, by + bh), (xx, by + bh + c.u * 1.6)], fill=(*IVORY, 170), width=max(1, int(c.u * 0.3)))
            d.text((xx, by + bh + c.u * 2.0), f"{km:,.0f}" if step >= 1 else f"{km:.1f}", font=f_small, fill=(*IVORY, 200), anchor="mt")
            km += step
        d.text((x0, by - c.u * 1.2), "surface", font=f_small, fill=rgb(s.muted), anchor="ls")
        if bw * Z * 0.995 < bw * 1.0:
            d.text((x1, by - c.u * 1.2), "centre of the Earth, 6,371 km", font=f_small, fill=rgb(s.muted), anchor="rs")
        pct = part / total * 100
        chip(d, x0, y0 + c.u * 3.5, f"Kola borehole: {part:,.3f} km", f_chip, CORAL, alpha=245)
        big_number(d, x0 + c.u * 0.3, y0 + c.u * 10.5, f"{pct * min(1.0, k * 1.4 + 0.04):.2f}", f_big, " % of the way", font(s.display, int(c.u * 2.8)), IVORY, CYAN)
        chip(d, x0, y1 - c.u * 3.5, f"zoom x{Z:,.0f}", f_chip, IVORY, alpha=235)
        yield img.convert("RGB")


# ---------- the shell theorem: why only the rock below you counts ----------
def _arrow(d, a, b, col, w, head):
    d.line([a, b], fill=col, width=int(w))
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for da in (2.6, -2.6):
        d.line([b, (b[0] + math.cos(ang + da) * head, b[1] + math.sin(ang + da) * head)], fill=col, width=int(w))


def scene_shell(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    x0, y0, x1, y1 = zone(c)
    R = (y1 - y0) * 0.42
    cx, cy = (x0 + (x1 - x0) * 0.42), (y0 + y1) / 2
    if c.vertical:
        cx, cy, R = (x0 + x1) / 2, y0 + (y1 - y0) * 0.42, (x1 - x0) * 0.42
    f_chip = font(s.display, int(c.u * 2.9))
    rp = R * 0.55
    pa = math.radians(-40)
    px, py = cx + rp * math.cos(pa), cy + rp * math.sin(pa)
    pull_dirs = [math.radians(a) for a in (-170, -130, -90, -50, -10, 30, 70, 110, 150)]
    for i in range(int(dur * FPS)):
        t = i / FPS
        tp = t / dur
        img, d = canvas(c, t)
        c.badge(d)
        # the Earth: shell (the rock above you) and the ball below you
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(*CYAN, 60), outline=(*CYAN, 230), width=max(2, int(c.u * 0.4)))
        ball_k = ease((tp - 0.52) / 0.12)
        d.ellipse([cx - rp, cy - rp, cx + rp, cy + rp], fill=(*mix((46, 70, 120), (255, 150, 84), ball_k), 255), outline=(*IVORY, 150), width=max(1, int(c.u * 0.3)))
        paste(img, SP.person(int(c.u * 7.5), "stand"), px, py - c.u * 3)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([px - c.u * 0.8, py - c.u * 0.8, px + c.u * 0.8, py + c.u * 0.8], fill=(255, 255, 255, 255))
        # pulls from the shell: opposite ones cancel and fade
        cancel = ease((tp - 0.22) / 0.26)
        if tp < 0.52:
            for j, a in enumerate(pull_dirs):
                L = c.u * (11 + 2 * math.sin(j * 1.7)) * (1 - cancel * 0.97)
                ex, ey = px + math.cos(a) * L, py + math.sin(a) * L
                _arrow(d, (px, py), (ex, ey), (*CORAL, int(235 * (1 - cancel * 0.8))), max(2, c.u * 0.5), c.u * 1.4)
        if tp >= 0.12:
            chip(d, x0, y1 - c.u * 7 if c.vertical else y0 + c.u * 3, "pulls from the rock above: cancel" if tp < 0.52 else "net pull", f_chip, CORAL if tp < 0.52 else GOLD, alpha=240)
        if tp >= 0.52:
            net = ease((tp - 0.56) / 0.22)
            L = c.u * 15 * net
            _arrow(d, (px, py), (px + (cx - px) * L / max(1, math.hypot(cx - px, cy - py)), py + (cy - py) * L / max(1, math.hypot(cx - px, cy - py))), (*GOLD, 255), max(3, c.u * 0.8), c.u * 2.0)
            chip(d, x0, (y1 - c.u * 14) if c.vertical else y0 + c.u * 10, "only the ball below you counts", f_chip, GOLD, alpha=int(245 * net))
        yield img.convert("RGB")


# ---------- gravity as you go down: the two models ----------
def scene_gravity(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    curves = p.get("curves", ["uniform"])
    x0, y0, x1, y1 = zone(c)
    px0, px1 = x0 + c.u * 6, (x0 + (x1 - x0) * 0.66 if not c.vertical else x1 - c.u * 2)
    py0, py1 = y0 + (y1 - y0) * 0.16, y1 - (y1 - y0) * (0.24 if not c.vertical else 0.30)
    gmax = 11.0
    f_chip, f_small, f_big = font(s.display, int(c.u * 2.7)), font(s.body, int(c.u * 2.2)), font(s.display, int(c.u * 6.2))
    N = 160
    def gcurve(kind):
        out = []
        for j in range(N + 1):
            f = j / N
            r = PH.R * (1 - f)
            out.append(PH.g_uniform(r) if kind == "uniform" else PH.g_layered(max(r, 1.0)) if f < 0.999 else 0.0)
        return out
    data = {k: gcurve(k) for k in ("uniform", "real")}
    colr = {"uniform": (*IVORY, 255), "real": (*GOLD, 255)}
    erx, ery, er = (x0 + (x1 - x0) * 0.86, (y0 + y1) / 2, (y1 - y0) * 0.28) if not c.vertical else (0, 0, 0)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        d.rounded_rectangle([px0 - c.u * 4, py0 - c.u * 2, px1 + c.u, py1 + c.u * 5], radius=c.u, fill=(6, 10, 24, 130))
        d.line([(px0, py0), (px0, py1), (px1, py1)], fill=(*IVORY, 200), width=max(2, int(c.u * 0.35)))
        for gv in (0, 5, 10):
            yy = py1 - (py1 - py0) * gv / gmax
            d.line([(px0 - c.u * 0.8, yy), (px1, yy)], fill=(*IVORY, 36), width=1)
            d.text((px0 - c.u * 1.2, yy), f"{gv}", font=f_small, fill=(*IVORY, 210), anchor="rm")
        d.text((px0, py0 - c.u * 3.2), "gravity, m/s²", font=f_small, fill=rgb(s.muted))
        d.text((px0, py1 + c.u * 1.2), "surface", font=f_small, fill=rgb(s.muted), anchor="lt")
        d.text((px1, py1 + c.u * 1.2), "centre", font=f_small, fill=rgb(s.muted), anchor="rt")
        d.text(((px0 + px1) / 2, py1 + c.u * 1.2), "depth", font=f_small, fill=rgb(s.muted), anchor="mt")
        prog = ease_io(t / (dur * 0.86))
        for kind in curves:
            pts = [(px0 + (px1 - px0) * j / N, py1 - (py1 - py0) * data[kind][j] / gmax) for j in range(N + 1)]
            upto = int(N * prog) + 1
            d.line(pts[:upto], fill=colr[kind], width=max(3, int(c.u * 0.6)), joint="curve")
            if kind == "uniform" and "real" in curves:
                pass
            j = min(N, int(N * prog))
            d.ellipse([pts[j][0] - c.u * 1.1, pts[j][1] - c.u * 1.1, pts[j][0] + c.u * 1.1, pts[j][1] + c.u * 1.1], fill=colr[kind])
        gv = data[curves[-1]][min(N, int(N * prog))]
        big_number(d, px1 - c.u * 1, py0 + c.u * 1.5, f"{gv:.1f}", f_big, " m/s²", font(s.display, int(c.u * 2.6)), IVORY if curves[-1] == "uniform" else GOLD, CYAN, anchor="r")
        ly = py1 + c.u * 5.5
        if "uniform" in curves:
            chip(d, px0, ly, "same density everywhere", f_chip, IVORY, alpha=240)
        if "real" in curves:
            chip(d, px0, ly + (f_chip.size * 2.1 if "uniform" in curves else 0), "real Earth: dense iron core", f_chip, GOLD, alpha=240)
        if er:
            earth_cut(img, d, erx - er * 0.5, ery, er, 1.0)
            ball_y = ery - er + 2 * er * prog
            d.line([(erx - er * 0.5, ery - er), (erx - er * 0.5, ery + er)], fill=(*IVORY, 150), width=max(2, int(c.u * 0.3)))
            d.ellipse([erx - er * 0.5 - c.u * 1.4, ball_y - c.u * 1.4, erx - er * 0.5 + c.u * 1.4, ball_y + c.u * 1.4], fill=(8, 14, 34, 255), outline=(*IVORY, 255), width=max(2, int(c.u * 0.4)))
        yield img.convert("RGB")



# ---------- falling through the Earth: the ball in a tunnel, with clocks ----------
def _state(model: str, f: float):
    """Position along the tunnel in [-1, 1] and speed in km/s, at trip fraction f (f in [0, 2] covers there and back)."""
    f = f % 2.0
    if model == "real":
        g = f if f <= 1.0 else 2.0 - f
        x, v = PH.layered_state(g)
        if f > 1.0:
            x = x            # mirror: coming back the position retraces the same path
        return (x if f <= 1.0 else x), v / 1e3
    x, v = PH.uniform_state(f if f <= 1.0 else 2.0 - f)
    return x, v / 1e3


def scene_earthfall(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    """The ball in the tunnel through the centre. model "uniform" (textbook, 42:12) or "real" (layered, 38:11) or
    "race" (both side by side). f0..f1 is the part of the trip shown (0..1 is surface to far side, up to 2 for the return)."""
    s = c.style
    model = p.get("model", "uniform")
    f0, f1 = float(p.get("f0", 0.0)), float(p.get("f1", 1.0))
    show_speed = bool(p.get("speed", model == "uniform"))
    chips_ = p.get("chips", [])
    dia = p.get("diameter")
    sat = p.get("satellite")
    x0, y0, x1, y1 = zone(c)
    f_chip, f_small, f_big = font(s.display, int(c.u * 2.8)), font(s.body, int(c.u * 2.2)), font(s.display, int(c.u * 6.4))
    T_U, T_R = PH.HALF_PERIOD / 60.0, 38.0 + 11 / 60.0
    if model == "race":
        R = (y1 - y0) * (0.30 if not c.vertical else 0.2)
        centres = [(x0 + (x1 - x0) * 0.22, (y0 + y1) / 2 - R * 0.1), (x0 + (x1 - x0) * 0.66, (y0 + y1) / 2 - R * 0.1)]
        if c.vertical:
            centres = [(x0 + (x1 - x0) * 0.27, y0 + (y1 - y0) * 0.45), (x0 + (x1 - x0) * 0.73, y0 + (y1 - y0) * 0.45)]
            R = (x1 - x0) * 0.22
    else:
        R = (y1 - y0) * 0.40 if not c.vertical else (x1 - x0) * 0.36
        centres = [((x0 + (x1 - x0) * 0.36) if not c.vertical else (x0 + x1) / 2, (y0 + y1) / 2 - (R * 0.05 if not c.vertical else -R * 0.2))]
    finished: dict[int, float] = {}
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        run = max(0.5, dur * 0.86)
        prog = ease_io(t / run) if model != "race" else min(1.0, t / (dur * 0.84))
        for ci, (cx, cy) in enumerate(centres):
            mdl = model if model != "race" else ("uniform" if ci == 0 else "real")
            earth_cut(img, d, cx, cy, R, 1.0)
            d.line([(cx, cy - R), (cx, cy + R)], fill=(255, 255, 255, 170), width=max(2, int(c.u * 0.45)))
            if model == "race":
                simmin = prog * T_U
                f = simmin / (T_U if mdl == "uniform" else T_R)
                f = min(1.0, f)
            else:
                f = f0 + (f1 - f0) * prog
            x, v = _state(mdl, f)
            by = cy + R * x
            if abs(v) > 0.5:
                paste(img, SP.glow(int(c.u * 12), (255, 255, 255), 120), cx, by)
            r_ = c.u * 1.9
            d.ellipse([cx - r_, by - r_, cx + r_, by + r_], fill=(8, 14, 34, 255), outline=(*IVORY, 255), width=max(2, int(c.u * 0.5)))
            if model == "race":
                mins = min(simmin, T_U if mdl == "uniform" else T_R)
                done = simmin >= (T_U if mdl == "uniform" else T_R)
                if done:
                    finished.setdefault(ci, t)
                lab = "Textbook: same density" if ci == 0 else "Real Earth: iron core"
                d.text((cx, cy - R - c.u * 4.5), lab, font=f_chip, fill=IVORY if ci == 0 else GOLD, anchor="mm")
                d.text((cx, cy + R + c.u * 5.5), mmss(mins), font=f_big, fill=(*(IVORY if ci == 0 else GOLD), 255), anchor="mm")
            elif ci == 0:
                tx = cx + R * 1.28 if not c.vertical else x0
                ty = cy - R * 0.62 if not c.vertical else cy + R * 1.25
                tmin = (T_U if mdl == "uniform" else T_R) * f
                d.text((tx, ty), mmss(tmin), font=f_big, fill=IVORY)
                d.text((tx, ty + f_big.size * 1.15), "elapsed", font=f_small, fill=rgb(s.muted))
                if show_speed:
                    sx_ = tx if not c.vertical else x0 + (x1 - x0) * 0.52
                    sy_ = ty + f_big.size * 2.5 if not c.vertical else ty
                    d.text((sx_, sy_), f"{abs(v):.1f}", font=f_big, fill=CYAN)
                    d.text((sx_ + d.textlength(f"{abs(v):.1f}", font=f_big) + c.u * 1.4, sy_ + f_big.size * 0.46), "km/s", font=font(s.display, int(c.u * 2.8)), fill=CYAN)
                    d.text((sx_, sy_ + f_big.size * 1.15), "speed (simple model)", font=f_small, fill=rgb(s.muted))
        if model == "race":
            if len(finished) == 2:
                age = t - max(finished.values())
                chip(d, (x0 + x1) / 2, y1 - c.u * 10, "the real Earth is about 4 minutes faster", f_chip, GOLD, alpha=int(245 * min(1, age / 0.4)), anchor="c")
        if dia and t > 0.4:
            cx, cy = centres[0]
            k = ease((t - 0.4) / 0.8)
            ax_ = cx + R * 1.12
            d.line([(ax_, cy - R * k), (ax_, cy + R * k)], fill=(*GOLD, 235), width=max(2, int(c.u * 0.4)))
            for sgn in (-1, 1):
                d.line([(ax_ - c.u, cy + sgn * R * k), (ax_ + c.u, cy + sgn * R * k)], fill=(*GOLD, 235), width=max(2, int(c.u * 0.4)))
            chip(d, ax_ + c.u * 2, cy - f_chip.size * 0.8, str(dia), f_chip, GOLD, alpha=int(245 * k))
        if sat:
            cx, cy = centres[0]
            ks = ease((prog - 0.45) / 0.15)
            if ks > 0:
                ang = (t * 3.2) % (2 * math.pi)
                rr = R * 1.07
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*CYAN, int(120 * ks)), width=max(1, int(c.u * 0.3)))
                paste(img, SP.glow(int(c.u * 9), CYAN, 190), cx + rr * math.cos(ang), cy + rr * math.sin(ang))
                d.ellipse([cx + rr * math.cos(ang) - c.u * 0.9, cy + rr * math.sin(ang) - c.u * 0.9, cx + rr * math.cos(ang) + c.u * 0.9, cy + rr * math.sin(ang) + c.u * 0.9], fill=(*CYAN, 255))
                chip(d, cx + R * 1.28 if not c.vertical else x0, (cy + R * 0.3) if not c.vertical else cy + R * 1.25 + f_big.size * 2.6, "same speed as a satellite skimming the surface", f_chip, CYAN, alpha=int(245 * ks))
        for ch_ in chips_:
            k = ease((prog - float(ch_["at"])) / 0.08)
            if k > 0:
                cc = {"gold": GOLD, "cyan": CYAN, "coral": CORAL}.get(ch_.get("col", "ivory"), IVORY)
                if model == "race" or c.vertical:
                    yy = (y0 + c.u * 3.4 + (c.u * 7.0) * float(ch_.get("row", 0))) if not c.vertical else (y1 - c.u * 8 - c.u * 6.5 * float(ch_.get("row", 0)))
                    xx = (x0 + (x1 - x0) * 0.60) if not c.vertical else x0
                else:
                    yy = centres[0][1] + R * 0.30 + c.u * 6.6 * float(ch_.get("row", 0))   # under the clock and speed readout
                    xx = centres[0][0] + R * 1.28
                chip(d, xx, yy, ch_["text"], f_chip, cc, alpha=int(245 * k))
        yield img.convert("RGB")


# ---------- the same time, whatever the tunnel: five chords ----------
def scene_chords(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    x0, y0, x1, y1 = zone(c)
    R = (y1 - y0) * 0.40 if not c.vertical else (x1 - x0) * 0.40
    cx, cy = (x0 + (x1 - x0) * 0.40, (y0 + y1) / 2) if not c.vertical else ((x0 + x1) / 2, y0 + (y1 - y0) * 0.42)
    chords = p.get("chords", [(200, 250), (190, 330), (165, 15), (140, 40), (110, 70)])
    train = p.get("train")
    labels = p.get("labels")
    f_chip, f_small, f_big = font(s.display, int(c.u * 2.8)), font(s.body, int(c.u * 2.2)), font(s.display, int(c.u * 6.4))
    cols = [CYAN, GOLD, CORAL, (160, 255, 190), (190, 160, 255)]
    T = PH.HALF_PERIOD / 60.0
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        earth_cut(img, d, cx, cy, R, 1.0)
        prog = min(1.0, t / (dur * 0.8))
        f = ease_io(prog) if False else prog
        pos = -math.cos(math.pi * f)
        for j, (a0, a1) in enumerate(chords):
            A = (cx + R * math.cos(math.radians(a0)), cy + R * math.sin(math.radians(a0)))
            B = (cx + R * math.cos(math.radians(a1)), cy + R * math.sin(math.radians(a1)))
            d.line([A, B], fill=(255, 255, 255, 120), width=max(2, int(c.u * 0.35)))
            u = (pos + 1) / 2
            bx, by = A[0] + (B[0] - A[0]) * u, A[1] + (B[1] - A[1]) * u
            if train and len(chords) == 1:
                ang = math.degrees(math.atan2(B[1] - A[1], B[0] - A[0]))
                sp = SP.train(int(c.u * 24)).rotate(-ang, resample=Image.BICUBIC, expand=True)
                paste(img, sp, bx, by)
            else:
                paste(img, SP.glow(int(c.u * 9), cols[j % 5], 160), bx, by)
                d.ellipse([bx - c.u * 1.5, by - c.u * 1.5, bx + c.u * 1.5, by + c.u * 1.5], fill=(*cols[j % 5], 255), outline=(8, 14, 34, 255), width=max(1, int(c.u * 0.3)))
            if labels:
                for (ax_, ay_), lab in zip((A, B), labels):
                    if train:
                        d.text((ax_, ay_ - c.u * 6.0), lab, font=f_chip, fill=IVORY, anchor="mm")
                    else:
                        d.text((ax_ + (-1 if ax_ < cx else 1) * c.u * 1.5, ay_), lab, font=f_chip, fill=IVORY, anchor="rm" if ax_ < cx else "lm")
        tx = cx + R * 1.3 if not c.vertical else x0
        ty = (cy - R * 0.5 if not train else cy + R * 0.25) if not c.vertical else cy + R * 1.2
        d.text((tx, ty), mmss(T * f), font=f_big, fill=IVORY)
        d.text((tx, ty + f_big.size * 1.15), "elapsed", font=f_small, fill=rgb(s.muted))
        if f >= 0.995:
            chip(d, tx, ty + f_big.size * 2.6, p.get("done", "all arrive together"), f_chip, GOLD, alpha=245)
        yield img.convert("RGB")


# ---------- satellite and ball: the fall is half of a lap ----------
def scene_lap(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    x0, y0, x1, y1 = zone(c)
    R = (y1 - y0) * 0.33 if not c.vertical else (x1 - x0) * 0.30
    cx, cy = (x0 + (x1 - x0) * 0.40, (y0 + y1) / 2) if not c.vertical else ((x0 + x1) / 2, y0 + (y1 - y0) * 0.42)
    f_chip, f_small, f_big = font(s.display, int(c.u * 2.8)), font(s.body, int(c.u * 2.2)), font(s.display, int(c.u * 6.2))
    T_lap, T_iss = 84.4, 92.7
    r_iss = R * (1 + 420 / 6371)
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        simmin = min(1.0, t / (dur * 0.92)) * 96.0
        th = 2 * math.pi * simmin / T_lap
        th2 = 2 * math.pi * simmin / T_iss
        earth_cut(img, d, cx, cy, R, 1.0, rim=False)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=(*CYAN, 230), width=max(2, int(c.u * 0.45)))
        d.line([(cx - R, cy), (cx + R, cy)], fill=(255, 255, 255, 170), width=max(2, int(c.u * 0.4)))
        rr = R * 1.012
        sx, sy = cx + rr * math.cos(th - math.pi), cy + rr * math.sin(th - math.pi)
        d.ellipse([cx - r_iss, cy - r_iss, cx + r_iss, cy + r_iss], outline=(*GOLD, 110), width=max(1, int(c.u * 0.3)))
        ix, iy = cx + r_iss * math.cos(th2 - math.pi), cy + r_iss * math.sin(th2 - math.pi)
        bx = cx + R * math.cos(th - math.pi)
        d.line([(sx, sy), (bx, cy)], fill=(*CYAN, 120), width=1)
        paste(img, SP.glow(int(c.u * 9), CYAN, 200), sx, sy)
        d.ellipse([sx - c.u, sy - c.u, sx + c.u, sy + c.u], fill=(*CYAN, 255))
        paste(img, SP.glow(int(c.u * 9), GOLD, 200), ix, iy)
        d.ellipse([ix - c.u, iy - c.u, ix + c.u, iy + c.u], fill=(*GOLD, 255))
        d.ellipse([bx - c.u * 1.5, cy - c.u * 1.5, bx + c.u * 1.5, cy + c.u * 1.5], fill=(8, 14, 34, 255), outline=(*IVORY, 255), width=max(2, int(c.u * 0.45)))
        tx = cx + R * 1.5 if not c.vertical else x0
        ty = cy - R * 0.9 if not c.vertical else cy + R * 1.35
        d.text((tx, ty), f"{simmin:,.0f}", font=f_big, fill=IVORY)
        d.text((tx + d.textlength(f"{simmin:,.0f}", font=f_big) + c.u * 1.2, ty + f_big.size * 0.46), "min", font=font(s.display, int(c.u * 2.8)), fill=CYAN)
        yy = ty + f_big.size * 1.5
        chip(d, tx, yy, "skimming satellite: 84 min a lap", f_chip, CYAN, alpha=240)
        if simmin >= 42.2:
            chip(d, tx, yy + f_chip.size * 2.2, "the fall: half a lap, 42 min", f_chip, IVORY, alpha=int(245 * min(1, (simmin - 42.2) / 3)))
        if simmin >= 50:
            chip(d, tx, yy + f_chip.size * 4.4, "space station, 420 km up: 92.7 min", f_chip, GOLD, alpha=int(245 * min(1, (simmin - 50) / 4)))
        yield img.convert("RGB")


# ---------- straight versus curved tunnel ----------
def scene_brachi(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    theta = math.radians(float(p.get("theta", 70)))
    x0, y0, x1, y1 = zone(c)
    R = (y1 - y0) * 0.40 if not c.vertical else (x1 - x0) * 0.40
    cx, cy = (x0 + (x1 - x0) * 0.40, (y0 + y1) / 2 + R * 0.05) if not c.vertical else ((x0 + x1) / 2, y0 + (y1 - y0) * 0.42)
    f_chip, f_small, f_big = font(s.display, int(c.u * 2.8)), font(s.body, int(c.u * 2.2)), font(s.display, int(c.u * 5.4))
    # lay the two surface points symmetrically at the top of the disk
    rot = -math.pi / 2 - theta / 2
    def to_screen(pt):
        x, y = pt
        xr, yr = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
        return cx + R * xr, cy + R * yr
    # the points are generated by cosine spacing so the slow start at rest is resolved
    n = 4000
    sp_ = (1 - np_cos(n)) / 2
    import numpy as _np
    rho = theta / (2 * math.pi)
    phi = sp_ * theta
    kk = (1 - rho) / rho
    hyp = _np.stack([(1 - rho) * _np.cos(phi) + rho * _np.cos(kk * phi), (1 - rho) * _np.sin(phi) - rho * _np.sin(kk * phi)], 1)
    chd = _np.stack([1 * (1 - sp_) + math.cos(theta) * sp_, 0 * (1 - sp_) + math.sin(theta) * sp_], 1)
    th_ = PH.path_times(hyp)
    tc_ = PH.path_times(chd)
    t_h, t_c = th_[-1] / 60.0, tc_[-1] / 60.0
    hs = [to_screen(pt) for pt in hyp[::20]]
    cs = [to_screen(pt) for pt in chd[::200]]
    for i in range(int(dur * FPS)):
        t = i / FPS
        img, d = canvas(c, t)
        c.badge(d)
        earth_cut(img, d, cx, cy, R, 1.0)
        d.line(cs, fill=(255, 255, 255, 150), width=max(2, int(c.u * 0.4)))
        d.line(hs, fill=(*CYAN, 230), width=max(2, int(c.u * 0.5)))
        simmin = min(1.0, t / (dur * 0.84)) * t_c
        for (arr, tms, col, lab, row) in ((chd, tc_, IVORY, "straight tunnel", 0), (hyp, th_, CYAN, "curved tunnel", 1)):
            sec = min(simmin * 60.0, tms[-1])
            idx = int(_np.searchsorted(tms, sec))
            idx = min(idx, len(arr) - 1)
            bx, by = to_screen(arr[idx])
            paste(img, SP.glow(int(c.u * 10), col, 190), bx, by)
            d.ellipse([bx - c.u * 1.6, by - c.u * 1.6, bx + c.u * 1.6, by + c.u * 1.6], fill=(*col, 255), outline=(8, 14, 34, 255), width=max(1, int(c.u * 0.3)))
            shown_t = min(simmin, tms[-1] / 60.0)
            yy = (cy - R * 0.3 + row * f_big.size * 2.4) if not c.vertical else (cy + R * 1.25 + row * f_big.size * 2.0)
            xx = cx + R * 1.3 if not c.vertical else x0
            d.text((xx, yy), mmss(shown_t), font=f_big, fill=(*col, 255))
            d.text((xx, yy + f_big.size * 1.1), lab, font=f_small, fill=rgb(s.muted))
        if simmin >= t_c * 0.999:
            chip(d, cx + R * 1.3 if not c.vertical else x0, (cy + R * 0.55) if not c.vertical else y1 - c.u * 9, "the curve gets there first", f_chip, CYAN, alpha=245)
        yield img.convert("RGB")


def np_cos(n):
    import numpy as _np
    return _np.cos(_np.linspace(0, _np.pi, n))


# ---------- the spinning Earth scrapes the wall; the pole-to-pole tunnel does not ----------
def scene_spin(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    x0, y0, x1, y1 = zone(c)
    R = (y1 - y0) * 0.40 if not c.vertical else (x1 - x0) * 0.40
    cx, cy = (x0 + (x1 - x0) * 0.40, (y0 + y1) / 2) if not c.vertical else ((x0 + x1) / 2, y0 + (y1 - y0) * 0.42)
    f_chip, f_small, f_big = font(s.display, int(c.u * 2.8)), font(s.body, int(c.u * 2.2)), font(s.display, int(c.u * 6.0))
    half_w = c.u * 1.0                      # tunnel half-width on screen, wider than life so it can be seen
    split = float(p.get("split", 0.62))
    ve = PH.EARTH_SPIN * PH.R
    spark_l = [(rng_a, 60 + 70 * rng_b, rng_b * 3, 0.5) for rng_a, rng_b in ((random.Random(i).uniform(0, 6.28), random.Random(i + 9).random()) for i in range(24))]
    for i in range(int(dur * FPS)):
        t = i / FPS
        tp = t / dur
        img, d = canvas(c, t)
        c.badge(d)
        if tp < split:
            k = min(1.0, tp / (split * 0.92))
            tsec = k * PH.HALF_PERIOD
            earth_cut(img, d, cx, cy, R, 1.0)
            x = PH.R * math.cos(PH.OMEGA * tsec)
            y = ve / PH.OMEGA * math.sin(PH.OMEGA * tsec)
            ang = PH.EARTH_SPIN * tsec
            along = x * math.cos(ang) + y * math.sin(ang)
            off_m = -x * math.sin(ang) + y * math.cos(ang)
            off_px = off_m / PH.R * R
            wall = half_w
            hit = abs(off_px) >= wall
            ox = max(-wall, min(wall, off_px))
            d.rectangle([cx - wall, cy - R, cx + wall, cy + R], fill=(6, 10, 24, 255), outline=(*IVORY, 150), width=max(1, int(c.u * 0.25)))
            by = cy - R + (R - along / PH.R * R)         # top of the screen is the start
            by = cy + (-R + (1 - along / PH.R) * R)
            by = cy - R * (along / PH.R)
            by = cy + R * (-math.cos(PH.OMEGA * tsec))
            bx = cx + ox
            paste(img, SP.glow(int(c.u * 10), (255, 255, 255) if not hit else (255, 150, 90), 170), bx, by)
            d.ellipse([bx - c.u * 1.3, by - c.u * 1.3, bx + c.u * 1.3, by + c.u * 1.3], fill=(8, 14, 34, 255), outline=(*IVORY, 255), width=max(2, int(c.u * 0.45)))
            if hit:
                sparks(d, spark_l, t, (bx, by), c.u * 5, 235, (255, 190, 90), c.u * 0.5)
            tx = cx + R * 1.3 if not c.vertical else x0
            ty = cy - R * 0.6 if not c.vertical else cy + R * 1.2
            d.text((tx, ty), mmss(tsec / 60.0), font=f_big, fill=IVORY)
            d.text((tx, ty + f_big.size * 1.1), "elapsed", font=f_small, fill=rgb(s.muted))
            chip(d, tx, ty + f_big.size * 2.5, f"ground speed at the equator: 1,670 km/h", f_chip, CYAN, alpha=240)
            if hit:
                chip(d, tx, ty + f_big.size * 2.5 + f_chip.size * 2.2, "scrapes the wall", f_chip, CORAL, alpha=245)
            d.text((tx, ty + f_big.size * 2.5 + f_chip.size * 4.6), f"sideways shift: {abs(off_m) / 1e3:,.0f} km (tunnel drawn wider than life)", font=f_small, fill=(*rgb(s.muted), 230))
        else:
            k = min(1.0, (tp - split) / ((1 - split) * 0.88))
            # side view, tunnel along the axis from pole to pole
            earth_cut(img, d, cx, cy, R, 1.0)
            d.rectangle([cx - half_w, cy - R, cx + half_w, cy + R], fill=(6, 10, 24, 255), outline=(*IVORY, 150), width=max(1, int(c.u * 0.25)))
            by = cy + R * (-math.cos(math.pi * k))
            paste(img, SP.glow(int(c.u * 10), (255, 255, 255), 170), cx, by)
            d.ellipse([cx - c.u * 1.3, by - c.u * 1.3, cx + c.u * 1.3, by + c.u * 1.3], fill=(8, 14, 34, 255), outline=(*IVORY, 255), width=max(2, int(c.u * 0.45)))
            # the spin axis
            d.arc([cx - R * 1.12, cy - R * 0.28, cx + R * 1.12, cy + R * 0.28], 200, 340, fill=(*GOLD, 200), width=max(2, int(c.u * 0.4)))
            chip(d, cx + R * 1.3 if not c.vertical else x0, cy - R * 0.4 if not c.vertical else cy + R * 1.2, "pole to pole: no sideways push", f_chip, GOLD, alpha=245)
            d.text((cx, cy - R - c.u * 2.5), "N", font=f_chip, fill=IVORY, anchor="mm")
            d.text((cx, cy + R + c.u * 2.5), "S", font=f_chip, fill=IVORY, anchor="mm")
        yield img.convert("RGB")


# ---------- where the tunnel comes out ----------
def scene_flood(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    s = c.style
    x0, y0, x1, y1 = zone(c)
    R = (y1 - y0) * 0.36 if not c.vertical else (x1 - x0) * 0.34
    cx, cy = (x0 + (x1 - x0) * 0.40, (y0 + y1) / 2 - R * 0.12) if not c.vertical else ((x0 + x1) / 2, y0 + (y1 - y0) * 0.40)
    f_chip, f_small = font(s.display, int(c.u * 2.8)), font(s.body, int(c.u * 2.2))
    rng = random.Random(8)
    drops = [(rng.uniform(-1.0, 0.0), rng.uniform(40, 120), rng.random() * 2, rng.uniform(0.5, 1.0)) for _ in range(28)]
    for i in range(int(dur * FPS)):
        t = i / FPS
        tp = t / dur
        img, d = canvas(c, t)
        c.badge(d)
        earth_cut(img, d, cx, cy, R, 1.0)
        # the ocean at the far side, with waves
        sea_y = cy + R
        for wx in range(int(cx - R * 1.5), int(cx + R * 1.5), 6):
            wy = sea_y + math.sin(wx * 0.05 + t * 2.4) * c.u * 0.45
            d.rectangle([wx, wy, wx + 6, wy + c.u * 6], fill=(40, 130, 200, 235))
        # land at the start
        d.rectangle([cx - R * 1.5, cy - R - c.u * 1.6, cx + R * 1.5, cy - R], fill=(88, 150, 100, 255))
        d.rectangle([cx - c.u * 1.0, cy - R - c.u * 1.6, cx + c.u * 1.0, cy + R], fill=(6, 10, 24, 255))
        fall = min(1.0, tp / 0.55)
        by = cy + R * (-math.cos(math.pi * fall))
        paste(img, SP.glow(int(c.u * 9), (255, 255, 255), 150), cx, by)
        d.ellipse([cx - c.u * 1.3, by - c.u * 1.3, cx + c.u * 1.3, by + c.u * 1.3], fill=(8, 14, 34, 255), outline=(*IVORY, 255), width=max(2, int(c.u * 0.45)))
        if tp >= 0.55:
            # splash, then the sea pours in and the tunnel floods
            sk = (tp - 0.55) / 0.12
            if sk < 1.0:
                sparks(d, [(a - math.pi / 2 * 0, sp, ph, lf) for (a, sp, ph, lf) in drops], t, (cx, sea_y), c.u * 7, int(220 * (1 - sk)), (190, 225, 255), c.u * 0.7)
            fk = ease((tp - 0.62) / 0.3)
            d.rectangle([cx - c.u * 1.0, cy + R - (2 * R) * fk, cx + c.u * 1.0, cy + R], fill=(40, 130, 200, 255))
        chip(d, x0, y0 + c.u * 3, "most land: the far side is ocean" if tp < 0.55 else ("the tunnel floods" if tp > 0.7 else "splash"), f_chip, CYAN, alpha=245)
        if tp >= 0.78:
            k = ease((tp - 0.78) / 0.12)
            chip(d, x0, y0 + c.u * 10.5, "Spain and New Zealand: close, not exact", f_chip, GOLD, alpha=int(245 * k))
            for (ang, lab) in ((-100, "Spain"), (80, "New Zealand")):
                px_, py_ = cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang))
                d.ellipse([px_ - c.u * 0.9, py_ - c.u * 0.9, px_ + c.u * 0.9, py_ + c.u * 0.9], fill=(*GOLD, int(255 * k)))
                d.text((px_ + c.u * 2, py_), lab, font=f_chip, fill=(*IVORY, int(255 * k)), anchor="lm")
        yield img.convert("RGB")


# ---------- a scene made of several (so a long line of narration gets several pictures) ----------
def scene_seq(c: Ctx, dur: float, p: dict, words: list[str]) -> Iterator[Image.Image]:
    parts = p["parts"]
    tot = sum(float(q.get("w", 1)) for q in parts)
    left = int(dur * FPS)
    for n, q in enumerate(parts):
        cnt = left if n == len(parts) - 1 else int(round(dur * FPS * float(q.get("w", 1)) / tot))
        cnt = max(1, min(cnt, left))
        show = dict(q["show"])
        kind = show.pop("type")
        from . import scenes as _all
        gen = _all.SCENES[kind](c, cnt / FPS, show, words)
        got = 0
        last = None
        for fr in gen:
            last = fr
            yield fr
            got += 1
            if got >= cnt:
                break
        while got < cnt and last is not None:
            yield last
            got += 1
        left -= cnt


SCENES = {"plunge": scene_plunge, "journey": scene_journey, "pips": scene_pips, "tank": scene_tank,
          "descent": scene_descent, "columns": scene_columns, "seismic": scene_seismic,
          "scale": scene_scale, "shell": scene_shell, "gravity": scene_gravity,
          "earthfall": scene_earthfall, "chords": scene_chords, "lap": scene_lap, "brachi": scene_brachi,
          "spin": scene_spin, "flood": scene_flood, "seq": scene_seq}
