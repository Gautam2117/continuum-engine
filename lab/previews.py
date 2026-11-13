"""Look-development frames: the same moment ("what if the Moon were twice as close?") in six styles.
Prototype frames drawn with PIL; they show the target look, not final animation."""
import math, random, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

K = 4                      # supersample factor over the 540x960 design space
W, H = 540, 960
FD = pathlib.Path(__file__).resolve().parents[1] / "assets" / "fonts"
OUT = pathlib.Path("/tmp/prev")
rnd = random.Random(5)


def F(name, size):
    p = {"marker": FD / "PermanentMarker.ttf", "hand": FD / "PatrickHand.ttf", "bangers": FD / "Bangers.ttf", "caveat": FD / "Caveat.ttf"}.get(name)
    if p:
        return ImageFont.truetype(str(p), int(size * K))
    import subprocess
    f = subprocess.run(["fc-match", "-f", "%{file}", name], capture_output=True, text=True).stdout
    return ImageFont.truetype(f, int(size * K))


def canvas(color=(0, 0, 0)):
    return Image.new("RGB", (W * K, H * K), color)


def done(img, name):
    img = img.convert("RGB").resize((W, H), Image.LANCZOS)
    img.save(OUT / f"{name}.jpg", quality=90)
    return img


def k(v):
    return [int(x * K) for x in v] if isinstance(v, (list, tuple)) else int(v * K)


def wob(pts, amt=1.2, seed=1):
    r = random.Random(seed)
    return [(x + r.uniform(-amt, amt), y + r.uniform(-amt, amt)) for x, y in pts]


def line(d, pts, w=4, fill=(20, 20, 20), amt=1.0, seed=1, closed=False):
    pts = wob(pts, amt, seed)
    if closed:
        pts = pts + [pts[0]]
    d.line([(int(x * K), int(y * K)) for x, y in pts], fill=fill, width=int(w * K), joint="curve")
    for x, y in (pts[0], pts[-1]):
        r = w * K / 2
        d.ellipse([x * K - r, y * K - r, x * K + r, y * K + r], fill=fill)


def circle_pts(cx, cy, r, n=48, a0=0, a1=2 * math.pi, rx=None):
    rx = rx or r
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def caption(img, words, hi, y=800, size=40, font="Inter Black"):
    d = ImageDraw.Draw(img, "RGBA")
    f = F(font, size)
    while sum(d.textlength(w + " ", font=f) for w in words) > W * K * 0.86 and size > 20:
        size -= 2
        f = F(font, size)
    sp = d.textlength(" ", font=f)
    ws = [d.textlength(w, font=f) for w in words]
    x = (W * K - (sum(ws) + sp * (len(words) - 1))) / 2
    yy = y * K
    for i, w in enumerate(words):
        if i == hi:
            d.rounded_rectangle([x - 10 * K, yy - 4 * K, x + ws[i] + 10 * K, yy + size * K * 1.15], radius=14 * K, fill=(94, 225, 255, 255))
            d.text((x, yy), w, font=f, fill=(5, 8, 20))
        else:
            d.text((x, yy), w, font=f, fill=(255, 255, 255), stroke_width=int(3.2 * K), stroke_fill=(0, 0, 0))
        x += ws[i] + sp


def grain(img, amt=8):
    a = np.asarray(img, np.float32)
    a += np.random.default_rng(2).normal(0, amt, a.shape[:2])[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- 2. stickman
def stickman():
    img = canvas((246, 240, 226))
    d = ImageDraw.Draw(img, "RGBA")
    ink = (24, 22, 22)
    # moon
    mx, my, mr = 330, 250, 165
    d.ellipse(k([mx - mr, my - mr, mx + mr, my + mr]), fill=(236, 234, 228), outline=ink, width=k(5))
    for cx, cy, r in ((290, 200, 28), (370, 290, 40), (250, 300, 18), (390, 190, 14), (320, 340, 12)):
        d.ellipse(k([cx - r, cy - r, cx + r, cy + r]), outline=(150, 148, 142), width=k(3))
    # sea
    sea = [(0, 560)] + [(x, 560 + 14 * math.sin(x / 38)) for x in range(0, 541, 20)] + [(540, 960), (0, 960)]
    d.polygon([(int(x * K), int(y * K)) for x, y in sea], fill=(70, 150, 220))
    for yy in (600, 650, 710):
        line(d, [(x, yy + 8 * math.sin(x / 30 + yy)) for x in range(0, 541, 18)], 4, (255, 255, 255, 200), 0.6, yy)
    # big wave
    wave = [(330, 600), (350, 520), (400, 470), (455, 480), (480, 530), (440, 520), (415, 545), (430, 600)]
    d.polygon([(int(x * K), int(y * K)) for x, y in wave], fill=(40, 120, 205), outline=ink)
    line(d, wave, 5, ink, 0.8, 7, True)
    # stickman on sand
    d.rectangle(k([0, 560, 215, 960]), fill=(232, 205, 150))
    line(d, [(0, 560), (215, 560)], 5, ink)
    hx, hy = 120, 470
    d.ellipse(k([hx - 30, hy - 30, hx + 30, hy + 30]), fill=(255, 255, 255), outline=ink, width=k(5))
    for ex in (-10, 11):
        d.ellipse(k([hx + ex - 7, hy - 8, hx + ex + 7, hy + 6]), fill=(255, 255, 255), outline=ink, width=k(3))
        d.ellipse(k([hx + ex - 2, hy - 4, hx + ex + 3, hy + 2]), fill=ink)
    d.ellipse(k([hx - 6, hy + 11, hx + 6, hy + 24]), fill=ink)
    line(d, [(hx, hy + 30), (hx, 560)], 6, ink, 0.6)           # torso
    line(d, [(hx, hy + 52), (hx + 52, hy + 8), (hx + 82, hy - 24)], 6, ink, 0.6)  # arm up at the moon
    line(d, [(hx, hy + 54), (hx - 40, hy + 90)], 6, ink, 0.6)  # other arm
    line(d, [(hx, 560), (hx - 22, 640)], 6, ink, 0.6)
    line(d, [(hx, 560), (hx + 26, 640)], 6, ink, 0.6)
    for a in (-0.5, 0, 0.5):                                    # shock lines
        line(d, [(hx + 46 * math.cos(a - 2.2), hy + 46 * math.sin(a - 2.2)), (hx + 66 * math.cos(a - 2.2), hy + 66 * math.sin(a - 2.2))], 4, ink)
    # label
    d.text(k([265, 215]), "2×", font=F("bangers", 120), fill=(220, 60, 40), stroke_width=k(3), stroke_fill=ink)
    # stars
    for sx, sy in ((60, 120), (150, 70), (220, 150), (30, 250)):
        line(d, [(sx - 9, sy), (sx + 9, sy)], 3.5, ink); line(d, [(sx, sy - 9), (sx, sy + 9)], 3.5, ink)
    img = grain(img, 6)
    caption(img, ["TIDES", "TWICE", "AS", "WILD"], 3, 790, 44, "bangers")
    return done(img, "stickman")


# ---------------------------------------------------------------- 3. whiteboard
def whiteboard():
    img = canvas((250, 250, 246))
    a = np.asarray(img, np.float32)
    yy, xx = np.mgrid[0:H * K:1, 0:W * K:1]
    vig = 1 - 0.07 * (np.hypot((xx / (W * K) - 0.5), (yy / (H * K) - 0.5)) * 1.6) ** 2
    img = Image.fromarray(np.clip(a * vig[..., None], 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    black, red, blue, green = (25, 25, 30), (214, 54, 54), (30, 100, 210), (30, 150, 80)
    d.text(k([34, 40]), "IF THE MOON WAS", font=F("marker", 40), fill=black)
    d.text(k([34, 92]), "TWICE AS CLOSE…", font=F("marker", 40), fill=red)
    line(d, [(34, 150), (200, 152), (330, 148)], 4, red, 1.2, 3)
    # Earth
    ex, ey, er = 130, 360, 82
    line(d, circle_pts(ex, ey, er, 60), 5, blue, 1.2, 4)
    for (cx, cy, r) in ((100, 345, 28), (150, 385, 22), (160, 330, 14)):
        pts = circle_pts(cx, cy, r, 14)
        line(d, pts, 3, green, 1.5, int(cx))
        for t in range(-r, r, 7):                      # hatch fill
            line(d, [(cx - r * 0.7, cy + t), (cx + r * 0.7, cy + t - 6)], 2, (*green, 160), 1)
    d.text(k([88, 460]), "Earth", font=F("caveat", 40), fill=black)
    # Moon today (dashed) and moon now
    for (mx, my, mr, col, dashed) in ((470, 360, 34, (150, 150, 150), True), (310, 360, 34, black, False)):
        pts = circle_pts(mx, my, mr, 40)
        if dashed:
            for i in range(0, len(pts) - 1, 3):
                line(d, pts[i:i + 2], 4, col, 0.5, i)
        else:
            line(d, pts, 5, col, 1, 9)
            for t in range(-26, 28, 8):
                line(d, [(mx - 20, my + t), (mx + 20, my + t - 5)], 2, (120, 120, 120), 0.8)
    d.text(k([430, 410]), "today", font=F("caveat", 34), fill=(130, 130, 130))
    d.text(k([280, 410]), "now", font=F("caveat", 36), fill=black)
    # distance arrow
    line(d, [(215, 300), (300, 300)], 4, red, 1, 12)
    line(d, [(284, 290), (302, 300), (284, 310)], 4, red, 0.5, 13)
    d.text(k([200, 244]), "192,200 km", font=F("caveat", 36), fill=red)
    # tide waves
    for i, yv in enumerate((520, 556, 592)):
        line(d, [(x, yv + 12 * math.sin(x / 18 + i)) for x in range(40, 230, 8)], 4, blue, 0.8, 20 + i)
    # notes
    d.text(k([36, 600]), "tides = 8× stronger", font=F("caveat", 50), fill=black)
    d.text(k([36, 656]), "orbit = 9.7 days", font=F("caveat", 50), fill=blue)
    # half-drawn underline, with the hand
    pts = [(36, 800), (120, 804), (200, 798), (260, 802)]
    line(d, pts, 5, red, 1, 30)
    hx, hy = 262, 804
    d.polygon(k([hx, hy, hx + 14, hy - 40, hx + 30, hy - 36, hx + 16, hy + 2]), fill=(40, 40, 46))       # marker
    d.polygon(k([hx + 6, hy - 18, hx + 30, hy - 66, hx + 78, hy - 56, hx + 92, hy - 10, hx + 54, hy + 24, hx + 18, hy + 8]), fill=(238, 196, 160), outline=(180, 130, 100))
    for i in range(3):
        line(d, [(hx + 38 + i * 12, hy - 56), (hx + 42 + i * 12, hy - 36)], 2.5, (200, 150, 120))
    # tray
    d.rectangle(k([0, 912, 540, 960]), fill=(205, 205, 208))
    d.rectangle(k([0, 912, 540, 916]), fill=(160, 160, 165))
    for i, c in enumerate((black, red, blue, green)):
        d.rounded_rectangle(k([60 + i * 40, 930, 90 + i * 40, 944]), radius=k(5), fill=c)
    img = grain(img, 3)
    return done(img, "whiteboard")


# ---------------------------------------------------------------- 4. blocky 3D (Roblox-like)
class Cam:
    def __init__(self, pos, look, f=760):
        self.pos = np.array(pos, float); self.f = f
        fw = np.array(look, float) - self.pos; fw /= np.linalg.norm(fw)
        rt = np.cross(fw, [0, 1, 0]); rt /= np.linalg.norm(rt)
        self.R = np.stack([rt, np.cross(rt, fw), fw])

    def proj(self, p):
        v = self.R @ (np.array(p, float) - self.pos)
        return (W / 2 + self.f * v[0] / v[2], H * 0.62 - self.f * v[1] / v[2], v[2])


FACES = [((0, 0, -1), [0, 1, 2, 3]), ((0, 0, 1), [4, 5, 6, 7]), ((-1, 0, 0), [0, 3, 7, 4]), ((1, 0, 0), [1, 2, 6, 5]), ((0, -1, 0), [0, 1, 5, 4]), ((0, 1, 0), [3, 2, 6, 7])]
LIGHT = np.array([0.5, 0.9, -0.6]); LIGHT /= np.linalg.norm(LIGHT)


def box(d, cam, c, s, col, decal=None):
    cx, cy, cz = c; sx, sy, sz = [v / 2 for v in s]
    V = [(cx + a * sx, cy + b * sy, cz + e * sz) for e in (-1, 1) for b, a in ((-1, -1), (-1, 1), (1, 1), (1, -1))]
    P = [cam.proj(v) for v in V]
    if min(p[2] for p in P) <= 0.2:
        return
    faces = []
    for n, idx in FACES:
        center = np.mean([V[i] for i in idx], axis=0)
        if np.dot(n, cam.pos - center) <= 0:
            continue
        sh = 0.55 + 0.45 * max(0, float(np.dot(n, LIGHT)))
        faces.append((np.mean([P[i][2] for i in idx]), idx, sh, n))
    for _, idx, sh, n in sorted(faces, reverse=True):
        poly = [(P[i][0] * K, P[i][1] * K) for i in idx]
        d.polygon(poly, fill=tuple(int(min(255, c_ * sh)) for c_ in col), outline=tuple(int(c_ * 0.55) for c_ in col))
        if decal and n == (0, 0, -1):
            decal(d, poly)


def blocky():
    img = canvas()
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(H * K):                         # sky
        t = y / (H * K * 0.62)
        t = min(t, 1)
        d.line([(0, y), (W * K, y)], fill=(int(40 + 190 * t ** 1.6), int(60 + 110 * t ** 1.3), int(150 - 20 * t)))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))   # moon
    gd = ImageDraw.Draw(glow)
    gd.ellipse(k([60, 20, 480, 440]), fill=(255, 244, 210, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(40 * K / 4 * 3))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse(k([95, 55, 445, 405]), fill=(255, 246, 222))
    for cx, cy, r in ((200, 160, 40), (330, 250, 55), (250, 330, 28), (380, 130, 24)):
        d.ellipse(k([cx - r, cy - r, cx + r, cy + r]), fill=(238, 226, 196))
    cam = Cam((0, 5.2, -13.5), (0.2, 2.2, 0))
    # ground tiles
    for gz in range(-4, 14):
        for gx in range(-9, 10):
            water = gx > 1 + (gz % 3 == 0)
            col = (68, 150, 235) if water else ((236, 214, 150) if (gx + gz) % 2 else (226, 202, 138))
            if water and (gx + gz) % 2:
                col = (86, 168, 245)
            box(d, cam, (gx, -0.25, gz), (1, 0.5, 1), col)
    # waves: blocks that grow toward the far right
    for i, (gx, gz, h) in enumerate(((3, 1, 2.2), (4, 2, 3), (5, 3, 3.8), (3, 4, 2.6), (5, 6, 4.6), (6, 5, 4.2), (4, 8, 4.2), (6, 9, 5.2))):
        box(d, cam, (gx, h / 2 - 0.5, gz), (1.2, h, 1.2), (235, 245, 255))
        box(d, cam, (gx, h - 0.6, gz), (1.25, 0.5, 1.25), (255, 255, 255))
    # palm tree
    for j in range(5):
        box(d, cam, (-5, j * 0.9 - 0.2, 6), (0.6, 0.9, 0.6), (140, 90, 50))
    for lx, lz in ((-1.6, 0), (1.6, 0), (0, -1.6), (0, 1.6), (0, 0)):
        box(d, cam, (-5 + lx, 4.1, 6 + lz), (1.8, 0.35, 1.8), (60, 170, 80))
    # avatar
    def face(dd, poly):
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = poly[0], poly[1], poly[2], poly[3]
        cx_, cy_ = (x0 + x2) / 2, (y0 + y2) / 2
        s = abs(x1 - x0) / 8
        for ex_ in (-1.7, 1.7):
            dd.ellipse([cx_ + ex_ * s - s * 0.6, cy_ - s * 1.6, cx_ + ex_ * s + s * 0.6, cy_ - s * 0.2], fill=(20, 20, 20))
        dd.arc([cx_ - s * 2.2, cy_ - s * 0.6, cx_ + s * 2.2, cy_ + s * 2.4], 20, 160, fill=(20, 20, 20), width=int(s * 0.7))
    ax, az = -1.6, -1.2
    box(d, cam, (ax - 0.32, 0.55, az), (0.5, 1.1, 0.55), (60, 160, 80))        # legs
    box(d, cam, (ax + 0.32, 0.55, az), (0.5, 1.1, 0.55), (60, 160, 80))
    box(d, cam, (ax, 1.65, az), (1.2, 1.2, 0.6), (50, 110, 220))                # torso
    box(d, cam, (ax - 0.95, 2.05, az), (0.55, 1.0, 0.55), (250, 205, 70))      # arms up
    box(d, cam, (ax + 0.95, 2.05, az), (0.55, 1.0, 0.55), (250, 205, 70))
    box(d, cam, (ax, 2.95, az), (0.95, 0.95, 0.95), (250, 205, 70), face)       # head
    img = grain(img, 5)
    caption(img, ["THE", "SEA", "RISES", "FAST"], 2, 800, 44)
    return done(img, "blocky")


# ---------------------------------------------------------------- 5. painted 2D-in-3D
def painted():
    img = canvas()
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(int(H * K * 0.56)):             # twilight sky
        t = y / (H * K * 0.56)
        d.line([(0, y), (W * K, y)], fill=(int(46 + 50 * t), int(24 + 40 * t), int(92 + 90 * t)))
    # moon + glow
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(k([-30, 20, 290, 340]), fill=(255, 235, 245, 120))
    glow = glow.filter(ImageFilter.GaussianBlur(60 * K / 2))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse(k([10, 60, 250, 300]), fill=(248, 240, 246))
    far = Image.new("RGBA", img.size, (0, 0, 0, 0))   # far layer (blurred): towers + neon + clouds
    fd = ImageDraw.Draw(far)
    for x0, w_, h_, col in ((300, 110, 330, (44, 46, 150)), (400, 90, 260, (56, 58, 170)), (470, 100, 380, (40, 40, 130)), (210, 70, 150, (60, 60, 160)), (-10, 80, 190, (50, 52, 150))):
        fd.rectangle(k([x0, 540 - h_, x0 + w_, 560]), fill=col)
        for wy in range(int(540 - h_ + 14), 540, 22):
            for wx in range(x0 + 10, x0 + w_ - 8, 20):
                if rnd.random() < 0.35:
                    fd.rectangle(k([wx, wy, wx + 7, wy + 10]), fill=(255, 226, 150, 220))
    for y_, col in ((330, (80, 240, 230, 230)), (368, (255, 210, 90, 230)), (250, (120, 240, 220, 220))):
        fd.rectangle(k([340, y_, 470, y_ + 7]), fill=col)
    for cx, cy, rx, ry in ((130, 330, 150, 26), (390, 440, 160, 22), (60, 470, 120, 20)):
        fd.ellipse(k([cx - rx, cy - ry, cx + rx, cy + ry]), fill=(235, 230, 250, 150))
    for i in range(28):                              # arched string lights
        a = i / 27
        fd.ellipse(k([20 + a * 300 - 4, 430 - 70 * math.sin(a * math.pi) - 4, 20 + a * 300 + 4, 430 - 70 * math.sin(a * math.pi) + 4]), fill=(255, 140, 220, 240))
    far = far.filter(ImageFilter.GaussianBlur(2.2 * K))
    img.paste(far, (0, 0), far)
    d = ImageDraw.Draw(img, "RGBA")
    hor = 560                                        # flooded street
    for y in range(hor * K, H * K):
        t = (y - hor * K) / ((H - hor) * K)
        d.line([(0, y), (W * K, y)], fill=(int(70 + 90 * t), int(80 + 90 * t), int(200 + 25 * t)))
    refl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for i in range(40):
        t = rnd.random() ** 1.5
        y_ = hor + 8 + t * 380
        w_ = 20 + t * 220
        x_ = rnd.random() * W
        rd.ellipse(k([x_ - w_, y_, x_ + w_, y_ + 3 + t * 9]), fill=(255, 255, 255, int(40 + 120 * (1 - t) + 40 * t)))
    refl = refl.filter(ImageFilter.GaussianBlur(1.4 * K))
    img.paste(refl, (0, 0), refl)
    d = ImageDraw.Draw(img, "RGBA")
    # street lamps with bokeh
    bok = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(bok)
    for x_, y_, r in ((60, 540, 22), (170, 548, 16), (410, 536, 24), (500, 546, 18), (300, 552, 14)):
        bd.ellipse(k([x_ - r, y_ - r, x_ + r, y_ + r]), fill=(255, 214, 120, 190))
        d.line(k([x_, y_, x_, 600]), fill=(40, 40, 90), width=k(3))
    bok = bok.filter(ImageFilter.GaussianBlur(3 * K))
    img.paste(bok, (0, 0), bok)
    d = ImageDraw.Draw(img, "RGBA")
    # foam puffs
    foam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(foam)
    for x_, y_, rx, ry in ((60, 760, 120, 30), (420, 700, 130, 26), (240, 860, 180, 36), (500, 820, 90, 24), (30, 640, 90, 18)):
        fd.ellipse(k([x_ - rx, y_ - ry, x_ + rx, y_ + ry]), fill=(240, 244, 255, 150))
    foam = foam.filter(ImageFilter.GaussianBlur(9 * K / 2))
    img.paste(foam, (0, 0), foam)
    d = ImageDraw.Draw(img, "RGBA")
    # cardboard boat (foreground) + flat character with ink outline
    ink = (28, 20, 30)
    boat = [(110, 700), (470, 700), (440, 800), (150, 800)]
    d.polygon(k([c for p in boat for c in p]), fill=(232, 190, 130), outline=ink)
    d.polygon(k([110, 700, 150, 668, 430, 668, 470, 700]), fill=(246, 214, 160), outline=ink)
    d.line(k([110, 700, 470, 700]), fill=ink, width=k(3))
    d.polygon(k([150, 800, 440, 800, 420, 818, 170, 818]), fill=(120, 90, 70, 200))
    # character: dome head, white face band, black bean body, stick arms
    cx_ = 290
    d.line(k([cx_ - 18, 665, cx_ - 40, 600]), fill=ink, width=k(8))
    d.line(k([cx_ + 18, 665, cx_ + 52, 605]), fill=ink, width=k(8))
    d.ellipse(k([cx_ - 34, 575, cx_ + 34, 700]), fill=(24, 20, 32), outline=ink, width=k(3))
    d.pieslice(k([cx_ - 44, 500, cx_ + 44, 592]), 180, 360, fill=(168, 104, 70), outline=ink, width=k(4))
    for yy in range(510, 548, 8):
        d.line(k([cx_ - 36, yy, cx_ + 36, yy]), fill=(140, 84, 58, 150), width=k(1))
    d.chord(k([cx_ - 44, 538, cx_ + 44, 594]), 0, 180, fill=(250, 250, 255), outline=ink, width=k(3))
    d.ellipse(k([cx_ - 18, 546, cx_ - 6, 564]), fill=ink)
    d.ellipse(k([cx_ + 6, 546, cx_ + 18, 564]), fill=ink)
    # sign on a pole: "2×"
    d.line(k([cx_ + 62, 640, cx_ + 62, 470]), fill=(220, 220, 235), width=k(5))
    d.rounded_rectangle(k([cx_ + 62, 468, cx_ + 160, 548]), radius=k(5), fill=(250, 250, 252), outline=ink, width=k(3))
    d.text(k([cx_ + 74, 468]), "2×", font=F("bangers", 70), fill=(220, 50, 70))
    # post: vignette, bloom, grain
    a = np.asarray(img, np.float32)
    yy, xx = np.mgrid[0:H * K:1, 0:W * K:1]
    vig = 1 - 0.45 * np.clip(np.hypot(xx / (W * K) - 0.5, yy / (H * K) - 0.5) * 1.5, 0, 1) ** 2
    img = Image.fromarray(np.clip(a * vig[..., None], 0, 255).astype(np.uint8))
    img = grain(img, 7)
    caption(img, ["THE", "MOON", "COMES", "CLOSER"], 1, 790, 44)
    return done(img, "painted")


# ---------------------------------------------------------------- 6. code-built motion graphics
def motion():
    img = canvas((7, 11, 26))
    d = ImageDraw.Draw(img, "RGBA")
    for gx in range(0, W, 36):
        d.line(k([gx, 0, gx, H]), fill=(120, 150, 255, 14), width=k(1))
    for gy in range(0, H, 36):
        d.line(k([0, gy, W, gy]), fill=(120, 150, 255, 14), width=k(1))
    d.text(k([34, 52]), "DISTANCE TO THE MOON, CUT IN HALF", font=F("Inter Medium", 17), fill=(143, 163, 200))
    d.text(k([30, 86]), "192,200", font=F("Inter Display Black", 108), fill=(238, 244, 255))
    d.text(k([36, 196]), "km", font=F("Inter Display Black", 34), fill=(94, 225, 255))
    cx, cy = 270, 450
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(k([cx - 40, cy - 40, cx + 40, cy + 40]), fill=(70, 150, 255, 160))
    glow = glow.filter(ImageFilter.GaussianBlur(22 * K / 2))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse(k([cx - 24, cy - 24, cx + 24, cy + 24]), fill=(60, 130, 230))
    d.ellipse(k([cx - 10, cy - 14, cx + 4, cy - 2]), fill=(90, 190, 120))
    for r, col, a0 in ((100, (94, 225, 255), 0.9), (200, (143, 163, 200), 0.5)):
        d.ellipse(k([cx - r, cy - r, cx + r, cy + r]), outline=(*col, 120), width=k(1.5))
    for i in range(70):                                  # trail
        a = -1.1 - i * 0.03
        x, y = cx + 100 * math.cos(a), cy + 100 * math.sin(a)
        d.ellipse(k([x - 2, y - 2, x + 2, y + 2]), fill=(94, 225, 255, int(230 - i * 3)))
    mx, my = cx + 100 * math.cos(-1.1), cy + 100 * math.sin(-1.1)
    d.ellipse(k([mx - 13, my - 13, mx + 13, my + 13]), fill=(94, 225, 255))
    gx, gy = cx + 200 * math.cos(0.5), cy + 200 * math.sin(0.5)
    d.ellipse(k([gx - 11, gy - 11, gx + 11, gy + 11]), fill=(143, 163, 200))
    d.text(k([34, 600]), "Today: 27.3-day orbit", font=F("Inter Medium", 16), fill=(143, 163, 200))
    d.text(k([34, 624]), "Twice as close: 9.7 days", font=F("Inter Medium", 16), fill=(94, 225, 255))
    # chart: tidal pull ~ 1/d^3
    px0, py0, pw, ph = 34, 690, 472, 110
    d.line(k([px0, py0 + ph, px0 + pw, py0 + ph]), fill=(143, 163, 200, 180), width=k(1.5))
    d.line(k([px0, py0, px0, py0 + ph]), fill=(143, 163, 200, 180), width=k(1.5))
    pts = [(px0 + pw * t / 100, py0 + ph - ph * min(1, (0.5 / (0.5 + t / 100 * 1.5)) ** 3 * 1.0)) for t in range(0, 101, 4)]
    d.line([(x * K, y * K) for x, y in pts], fill=(94, 225, 255), width=k(3), joint="curve")
    d.text(k([px0 + 8, py0 - 24]), "Tidal pull vs distance", font=F("Inter SemiBold", 15), fill=(238, 244, 255))
    d.ellipse(k([px0 + 150 - 7, py0 + 14 - 7, px0 + 150 + 7, py0 + 14 + 7]), fill=(255, 210, 90))
    d.text(k([px0 + 164, py0 + 2]), "8×", font=F("Inter Display Black", 28), fill=(255, 210, 90))
    # the code that makes it
    d.rounded_rectangle(k([30, 828, 510, 892]), radius=k(10), fill=(18, 26, 52), outline=(70, 90, 160, 160), width=k(1.5))
    d.text(k([44, 836]), "<Orbit radius={192200} period={9.7}", font=F("DejaVu Sans Mono", 14), fill=(143, 200, 255))
    d.text(k([44, 860]), "  trail glow tidal={8} />", font=F("DejaVu Sans Mono", 14), fill=(143, 200, 255))
    caption(img, ["CLOSER", "ORBITS", "ARE", "FASTER"], 1, 902, 30)
    return done(img, "motion")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    which = sys.argv[1:] or ["stickman", "whiteboard", "blocky", "painted", "motion"]
    for n in which:
        globals()[n]()
        print("ok", n)
