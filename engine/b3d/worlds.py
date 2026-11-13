"""More 3D looks, all procedural and original. Loaded by blender_main.py; `worlds.scenes(bm)` returns builders.

  corridor  (S6 ambient / S2 POV)  liminal corridor, pool or hotel hall; slow drift or walk;
            params: kind corridor|pool|hotel, length, lights warm|cold|flicker, door "404" (hotel), drift 0..1
            channels: BLANK HOURS, The Night Archive, Room 404, The Low Battery Show (kind room)
  room_pov  (S2 POV)  first-person room with hands on a desk, wide lens, clock; params: kind classroom|bedroom|office,
            clock "10:42", look_to -1..1 (head turn); channels: Survive This, Room 404, Next Frame, LifeSpawn
  gears     (S4 technical) a working gear train that opens up (exploded view); params: n 2-5, explode 0..1, label list
            channels: Gears Unseen, What Drives It
  extrude   (S4 technical) isometric blueprint city block / building that rises; params: blocks n, route true, amount
            channels: Heist & Con, The India Machine (bars on a grid), Unsealed Show
  panels    (S5 glass UI) floating glass cards in depth that build one by one; params: cards [{title, body}], verdict
            channels: Workflow Verdict, Brieflylatest, Foundbeam, Oddly Proven, OH THIS EXISTS, News From 2099
  voxel     (S8) a voxel island with a tiny hero walking a path; params: hero colour, level label
            channels: Pixel Fables
"""
from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector


def scenes(bm):
    mat, link, box, cyl, ease = bm.mat, bm.link, bm.box, bm.cyl, bm.ease

    def vertical():
        sc = bpy.context.scene
        return sc.render.resolution_y > sc.render.resolution_x

    def point_light(loc, energy, col, r=0.2):
        bpy.ops.object.light_add(type="POINT", location=loc)
        l = bpy.context.active_object
        l.data.energy = energy
        l.data.color = bm.lin(col)
        l.data.shadow_soft_size = r
        return l

    # ------------------------------------------------------------ corridor / pool / hotel
    def scene_corridor(p, frames, pal):
        kind = p.get("kind", "corridor")
        L = float(p.get("length", 30))
        W, H = (3.0, 3.0) if kind != "pool" else (8.0, 4.0)
        warm = p.get("lights", "cold") == "warm"
        wall = mat("cwall", {"corridor": "#d9d2b6", "pool": "#e9f1f2", "hotel": "#5a2e3a", "room": "#e8d6c0"}.get(kind, "#d9d2b6"), 0.85)
        floor_m = mat("cfloor", {"corridor": "#a39b7c", "pool": "#ffffff", "hotel": "#2b1c26", "room": "#8a6a4c"}.get(kind, "#a39b7c"), 0.7)
        ceil = mat("cceil", "#e7e3d6", 0.9)
        box("floor", (W, L, 0.1), (0, L / 2, -0.05), floor_m)
        box("ceil", (W, L, 0.1), (0, L / 2, H + 0.05), ceil)
        box("wallL", (0.1, L, H), (-W / 2, L / 2, H / 2), wall)
        box("wallR", (0.1, L, H), (W / 2, L / 2, H / 2), wall)
        box("end", (W, 0.1, H), (0, L, H / 2), wall)
        lamp = mat("lamp", "#fff3d6" if warm else "#eef6ff", 0.2, emit=6.0)
        flick = p.get("lights") == "flicker"
        lights = []
        for k in range(int(L // 4)):
            y = 2 + k * 4
            box(f"panel{k}", (0.9, 0.5, 0.03), (0, y, H - 0.02), lamp)
            lights.append(point_light((0, y, H - 0.3), 120 if kind != "pool" else 220, "#fff1d6" if warm else "#e8f2ff", 0.6))
        if kind == "pool":
            box("water", (W - 1.2, L - 4, 0.05), (0, L / 2, 0.02), mat("pool", "#4fc3d9", 0.05, emit=0.4, alpha=0.85))
            for k in range(int(L // 2)):  # tile grid lines
                box(f"tile{k}", (W, 0.02, 0.005), (0, k * 2, 0.005), mat("grout", "#cfe3e6", 0.6))
        if kind in ("hotel", "corridor"):
            for k in range(int(L // 5)):
                for side in (-1, 1):
                    y = 3 + k * 5 + (1.2 if side > 0 else 0)
                    box(f"door{k}{side}", (0.06, 1.0, 2.1), (side * (W / 2 - 0.06), y, 1.05),
                        mat("doorc", "#6b4a2e" if kind == "hotel" else "#9a9078", 0.6))
                    if kind == "hotel":
                        box(f"plate{k}{side}", (0.03, 0.22, 0.12), (side * (W / 2 - 0.1), y, 1.75), mat("brass", "#d9b04a", 0.3, metal=0.8))
            if kind == "hotel":
                box("runner", (1.2, L, 0.01), (0, L / 2, 0.005), mat("runner", "#7a1f2b", 0.9))
                if p.get("door"):
                    bm.ANCHORS["door"] = (lambda fr: Vector((0, L - 0.2, 2.35)))
                    bm.LABELS.append({"anchor": "door", "text": str(p["door"]), "style": "tag", "hl": True})
                    box("thedoor", (1.0, 0.06, 2.1), (0, L - 0.08, 1.05), mat("thedoor", "#3a2418", 0.5))
        if flick:
            rnd = random.Random(3)
            for li in lights[::2]:
                for f in range(1, frames + 1):
                    li.data.energy = 0 if rnd.random() < 0.12 else 120
                    li.data.keyframe_insert("energy", frame=f)
        bm.world({**pal, "bg": "#0b0c0b"})
        drift = float(p.get("drift", 0.25))
        cam, tgt = bm.camera((0, 0, 0), (0, 0, 0), lens=18 if vertical() else 24)
        bm.key_path(cam, frames, lambda t: Vector((0.25 * math.sin(t * 2.0), 0.6 + L * drift * t, 1.6 + 0.03 * math.sin(t * 9))))
        bm.key_path(tgt, frames, lambda t: Vector((0.1 * math.sin(t * 1.3), L, 1.5)))
        return cam

    # ------------------------------------------------------------ first-person room
    def scene_room_pov(p, frames, pal):
        kind = p.get("kind", "classroom")
        wall = mat("rwall", {"classroom": "#cfe0d8", "bedroom": "#e8d3c0", "office": "#e2e2dc"}.get(kind, "#cfe0d8"), 0.9)
        box("rfloor", (12, 12, 0.1), (0, 2, -0.05), mat("rfl", "#b08a62", 0.8))
        box("back", (12, 0.1, 4), (0, 6, 2), wall)
        box("left", (0.1, 12, 4), (-5, 2, 2), wall)
        box("right", (0.1, 12, 4), (5, 2, 2), wall)
        box("rceil", (12, 12, 0.1), (0, 2, 4.05), mat("rceil", "#f2f0ea", 0.9))
        bpy.ops.object.light_add(type="AREA", location=(0, 2, 3.9))
        a = bpy.context.active_object
        a.data.energy = 600
        a.data.size = 4
        a.rotation_euler = (0, 0, 0)
        # desk + paper + hands (POV)
        box("pdesk", (1.6, 0.9, 0.06), (0, 0.55, 0.75), mat("pdesk", "#a87b4f", 0.6))
        box("paper", (0.42, 0.56, 0.005), (0.0, 0.55, 0.785), mat("paper", "#f7f4ea", 0.9))
        for k in range(8):
            box(f"line{k}", (0.3, 0.004, 0.002), (0.0, 0.38 + k * 0.045, 0.79), mat("pline", "#8a93a8", 0.9))
        skin = mat("hand", "#c68a5e", 0.6)
        for sx in (-0.33, 0.33):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.09, location=(sx, 0.32, 0.81))
            h_ = bpy.context.active_object
            h_.scale = (1.0, 1.4, 0.5)
            link(h_, skin)
            for pp in h_.data.polygons:
                pp.use_smooth = True
            box(f"sleeve{sx}", (0.17, 0.3, 0.14), (sx, 0.08, 0.8), mat("sleeve", pal["accent"], 0.7))
        # wall clock
        cyl("clockface", 0.38, 0.05, (0, 5.93, 2.9), mat("clockf", "#f8f6f0", 0.5), verts=32, rot=(math.radians(90), 0, 0))
        cyl("clockrim", 0.41, 0.04, (0, 5.95, 2.9), mat("clockr", "#2b2b30", 0.4), verts=32, rot=(math.radians(90), 0, 0))
        hh, mm = [int(v) for v in str(p.get("clock", "10:42")).split(":")]
        for nm, ln, ang in (("hour", 0.2, (hh % 12 + mm / 60) / 12), ("minute", 0.32, mm / 60)):
            hnd = box(nm, (0.025, 0.01, ln), (0, 5.89, 2.9 + ln / 2), mat("hand_c", "#1c1c20", 0.5))
            # rotate about the clock centre
            hnd.location = (math.sin(2 * math.pi * ang) * ln / 2, 5.89, 2.9 + math.cos(2 * math.pi * ang) * ln / 2)
            hnd.rotation_euler = (0, 2 * math.pi * ang, 0)
        if kind == "classroom":
            box("board", (4.0, 0.06, 1.6), (0, 5.92, 1.8), mat("board", "#2f4a3a", 0.8))
            box("exit", (0.6, 0.04, 0.25), (3.6, 5.92, 3.3), mat("exit", "#2ecc71", 0.2, emit=4.0))
            bm.ANCHORS["exit"] = (lambda fr: Vector((3.6, 5.85, 3.3)))
            bm.LABELS.append({"anchor": "exit", "text": "EXIT", "style": "label"})
            box("rdoor", (0.06, 1.1, 2.2), (4.94, 4.2, 1.1), mat("rdoor", "#7a5230", 0.6))
            for r in range(2):
                for c in range(4):
                    box(f"sdesk{r}{c}", (1.0, 0.6, 0.05), (-3 + c * 2, 2.4 + r * 1.6, 0.75), mat("pdesk", "#a87b4f", 0.6))
        elif kind == "bedroom":
            box("bed", (2.2, 1.6, 0.5), (-3.5, 4.5, 0.25), mat("bed", "#9fb3d1", 0.9))
            box("window", (1.8, 0.05, 1.2), (2.5, 5.93, 2.2), mat("win", "#1b2a4a", 0.2, emit=0.6))
        else:
            box("monitor", (0.9, 0.05, 0.5), (0, 1.1, 1.15), mat("mon", pal["accent"], 0.2, emit=1.4))
        if p.get("clock_label", True):
            bm.ANCHORS["clock"] = (lambda fr: Vector((-1.6, 5.88, 3.3)))
            bm.LABELS.append({"anchor": "clock", "text": str(p.get("stamp", p.get("clock", "10:42"))), "style": "tag"})
        bm.world(pal)
        look = float(p.get("look_to", 0.3))
        cam, tgt = bm.camera((0, -0.15, 1.45), (0, 6, 1.6), lens=14 if vertical() else 18)
        bm.key_path(tgt, frames, lambda t: Vector((look * 4 * ease(t), 6, 1.6 + 0.4 * ease(t))))
        bm.key_path(cam, frames, lambda t: Vector((0.02 * math.sin(t * 8), -0.15, 1.45 + 0.015 * math.sin(t * 13))))
        return cam

    # ------------------------------------------------------------ gears (exploded)
    def gear(name, r, teeth, width, m, loc):
        bpy.ops.mesh.primitive_cylinder_add(vertices=teeth * 2, radius=r, depth=width, location=loc, rotation=(math.radians(90), 0, 0))
        g = bpy.context.active_object
        g.name = name
        link(g, m)
        me = g.data
        # push every other rim vertex out to make teeth
        for v in me.vertices:
            ang = math.atan2(v.co.y, v.co.x)
            k = round((ang % (2 * math.pi)) / (2 * math.pi) * teeth * 2)
            if math.hypot(v.co.x, v.co.y) > r * 0.9 and k % 2 == 0:
                v.co.x *= 1.14
                v.co.y *= 1.14
        cyl(name + "_hub", r * 0.25, width * 1.6, loc, mat("hub", "#2b2b30", 0.4, metal=0.6), verts=16, rot=(math.radians(90), 0, 0))
        hub = bpy.context.active_object
        hub.parent = g
        hub.location = (0, 0, 0)
        return g

    def scene_gears(p, frames, pal):
        n = max(2, min(5, int(p.get("n", 3))))
        explode = float(p.get("explode", 0.6))
        labels = p.get("labels") or []
        brass = mat("brass", "#d9b04a", 0.3, metal=0.85)
        steel = mat("steel", "#c9ccd6", 0.3, metal=0.8)
        hi = mat("glowgear", pal["accent"], 0.3, emit=1.8)
        x = -2.2
        gears = []
        prev_r = None
        for i in range(n):
            r = [1.2, 0.7, 1.0, 0.55, 0.9][i]
            teeth = int(r * 16)
            if prev_r is not None:
                x += prev_r + r + 0.05
            m = hi if i == int(p.get("glow", 1)) % n else (brass if i % 2 == 0 else steel)
            g = gear(f"gear{i}", r, teeth, 0.28, m, (x, 0, 1.5))
            gears.append((g, r, x, teeth))
            prev_r = r
        cx = (gears[0][2] + gears[-1][2]) / 2
        for i, (g, r, gx, teeth) in enumerate(gears):
            ratio = gears[0][1] / r * (1 if i % 2 == 0 else -1)
            off = (i - (n - 1) / 2) * 1.0
            for f in range(1, frames + 1):
                t = (f - 1) / max(1, frames - 1)
                e = ease(min(1, max(0, (t - 0.35) / 0.5))) * explode
                g.rotation_euler = (math.radians(90), 2.4 * t * ratio, 0)
                g.location = (gx - cx, -off * 1.4 * e, 1.5 + (0.6 if i % 2 else -0.2) * e)
                g.keyframe_insert("rotation_euler", frame=f)
                g.keyframe_insert("location", frame=f)
            if i < len(labels) and labels[i]:
                bm.ANCHORS[f"gear{i}"] = g
                bm.LABELS.append({"anchor": f"gear{i}", "text": str(labels[i]), "style": "tag", "hl": i == int(p.get("glow", 1)) % n})
        bm.floor({**pal, "panel": "#2a2116"} if pal["bg"].lower() != "#05070f" else pal)
        bm.lights(pal)
        span = gears[-1][2] - gears[0][2] + 2.4
        dist = (span / 2 + 0.3) / (0.48 if vertical() else 0.9) * 0.82
        cam, tgt = bm.camera((0, 0, 0), (0, 0, 1.6), lens=32)
        bm.key_path(cam, frames, lambda t: Vector((1.2 * math.sin(0.6 + 0.5 * ease(t)), -dist, 1.6 + dist * 0.22)))
        return cam

    # ------------------------------------------------------------ extruded blueprint
    def scene_extrude(p, frames, pal):
        n = int(p.get("blocks", 7))
        rnd = random.Random(int(p.get("seed", 4)))
        grid = mat("bp", "#13253d", 0.8)
        line = mat("bpl", "#6fa8ff", 0.4, emit=1.5)
        box("bpfloor", (30, 30, 0.05), (0, 0, -0.03), grid)
        for k in range(-7, 8):
            box(f"gx{k}", (30, 0.015, 0.01), (0, k * 2, 0.0), line)
            box(f"gy{k}", (0.015, 30, 0.01), (k * 2, 0, 0.0), line)
        bld = mat("bld", "#e6f0ff", 0.6)
        hi = mat("bldhi", pal["accent"], 0.4, emit=1.0)
        items = p.get("items")  # optional: [{label, value}] makes it a 3D bar map
        cells = []
        for i in range(n if not items else len(items)):
            gx, gy = (i % 4) * 2.4 - 3.6, (i // 4) * 2.4 - 1.2
            h = rnd.uniform(0.8, 3.2) if not items else 0.4 + 4.0 * float(items[i]["value"]) / max(float(it["value"]) for it in items)
            b = box(f"b{i}", (1.6, 1.6, 1), (gx, gy, 0), hi if (items and items[i].get("highlight")) or (not items and i == 2) else bld)
            for v in b.data.vertices:
                v.co.z += 0.5
            cells.append((b, h, gx, gy))
            for f in range(1, frames + 1):
                t = (f - 1) / max(1, frames - 1)
                g = ease(min(1, max(0, (t - 0.05 * i) / 0.45)))
                b.scale = (1.6, 1.6, max(0.001, h * g))
                b.keyframe_insert("scale", frame=f)
            if items:
                bm.ANCHORS[f"b{i}"] = (lambda fr, gx=gx, gy=gy, h=h: Vector((gx, gy, h + 0.4)))
                bm.LABELS.append({"anchor": f"b{i}", "text": f"{items[i]['label']}", "style": "tag", "hl": bool(items[i].get("highlight"))})
        if p.get("route"):
            pts = [Vector((-6, -4, 0.05)), Vector((-1.2, -2.4, 0.05)), Vector((1.2, 0.0, 0.05)), Vector((4.8, 2.4, 0.05)), Vector((7, 5, 0.05))]
            red = mat("route", "#ff5d5d", 0.3, emit=3.0)
            segs = []
            for a_, b_ in zip(pts, pts[1:]):
                mid, d_ = (a_ + b_) / 2, (b_ - a_)
                s_ = box("seg", (0.12, d_.length, 0.03), mid, red, rot=(0, 0, math.atan2(-d_.x, d_.y)))
                segs.append(s_)
            for k, s_ in enumerate(segs):
                for f in range(1, frames + 1):
                    t = (f - 1) / max(1, frames - 1)
                    s_.hide_render = t < 0.3 + 0.12 * k
                    s_.keyframe_insert("hide_render", frame=f)
        bm.world({**pal, "bg": "#0b1626"})
        bm.lights(pal)
        cam, tgt = bm.camera((0, 0, 0), (0, 0, 0.8), lens=30)
        d = 13 if vertical() else 11
        bm.key_path(cam, frames, lambda t: Vector((math.cos(math.radians(-55 + 20 * ease(t))) * d,
                                                 math.sin(math.radians(-55 + 20 * ease(t))) * d, d * 0.85)))
        return cam

    # ------------------------------------------------------------ glass panels
    def scene_panels(p, frames, pal):
        cards = (p.get("cards") or [{"title": "Claim", "body": "What they say"}, {"title": "Test", "body": "What we check"},
                                    {"title": "Verdict", "body": "On paper"}])[:5]
        n = len(cards)
        glass = mat("glass", "#2a3f63", 0.15, emit=0.6, alpha=0.9)
        edge = mat("gedge", pal["accent"], 0.3, emit=3.0)
        vert = vertical()
        for i, cdef in enumerate(cards):
            x = 0 if vert else (i - (n - 1) / 2) * 3.2
            z = (n - 1 - i) * 1.55 + 0.6 if vert else 1.6
            y = i * 0.6
            cw = 4.4 if vert else 3.0
            pnl = box(f"card{i}", (cw, 0.06, 1.25), (x, y, z), glass)
            e_ = box(f"cedge{i}", (cw, 0.07, 0.03), (x, y - 0.01, z - 0.61), edge)
            for ob in (pnl, e_):
                home = ob.location.copy()
                for f in range(1, frames + 1):
                    t = (f - 1) / max(1, frames - 1)
                    g = ease(min(1, max(0, (t - 0.12 * i) / 0.3)))
                    ob.location = home + Vector((0, (1 - g) * 3.0, (1 - g) * -0.4))
                    ob.rotation_euler = (math.radians(25) * (1 - g), 0, 0)
                    ob.keyframe_insert("location", frame=f)
                    ob.keyframe_insert("rotation_euler", frame=f)
            bm.ANCHORS[f"card{i}"] = (lambda fr, pnl=pnl: pnl.matrix_world @ Vector((-0.44, -0.6, 0.18)))
            bm.ANCHORS[f"cardb{i}"] = (lambda fr, pnl=pnl: pnl.matrix_world @ Vector((-0.44, -0.6, -0.12)))
            bm.LABELS.append({"anchor": f"card{i}", "text": str(cdef.get("title", "")), "style": "cardtitle", "hl": bool(cdef.get("highlight"))})
            bm.LABELS.append({"anchor": f"cardb{i}", "text": str(cdef.get("body", "")), "style": "cardbody"})
        # particles
        rnd = random.Random(2)
        dot = mat("dot", pal["accent"], 0.2, emit=4.0)
        for k in range(60):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.025,
                                                  location=(rnd.uniform(-6, 6), rnd.uniform(2, 10), rnd.uniform(-1, 7)))
            link(bpy.context.active_object, dot)
        bm.world(pal)
        top = (n - 1) * 1.55 + 0.6 if vert else 1.6
        cam, tgt = bm.camera((0, 0, 0), (0, 0, top / 2 if vert else 1.6), lens=32)
        d = 8.2 if vert else 8.5 + n
        bm.key_path(cam, frames, lambda t: Vector((1.2 - 2.4 * ease(t), -d, (top / 2 if vert else 1.6) + 1.0)))
        return cam

    # ------------------------------------------------------------ voxel island
    def scene_voxel(p, frames, pal):
        rnd = random.Random(int(p.get("seed", 6)))
        grass, dirt, water = mat("vgrass", "#6cc24a", 0.8), mat("vdirt", "#8a5a3a", 0.9), mat("vwater", "#3aa0e8", 0.2, emit=0.2)
        stone, leaf, wood = mat("vstone", "#9a9aa3", 0.8), mat("vleaf", "#2f8f4e", 0.8), mat("vwood", "#7a5230", 0.9)
        import bmesh as _bm
        meshes = {}

        def cube_at(key, x, y, z):
            meshes.setdefault(key, []).append((x, y, z))

        R = 7
        for x in range(-R, R + 1):
            for y in range(-R, R + 1):
                d = math.hypot(x, y)
                if d > R:
                    continue
                h = int(max(0, 3 - d * 0.35 + rnd.uniform(-0.6, 0.6)))
                for z in range(-2, h):
                    cube_at("dirt" if z < h - 1 else ("stone" if d < 2.2 and h > 2 else "grass"), x, y, z)
        for x in range(-12, 13):
            for y in range(-12, 13):
                if math.hypot(x, y) > R - 0.5:
                    cube_at("water", x, y, -1)
        for tx, ty in ((-4, 2), (3, -4), (4, 3)):
            for z in range(1, 4):
                cube_at("wood", tx, ty, z)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (4, 5):
                        if abs(dx) + abs(dy) + (dz - 4) < 3:
                            cube_at("leaf", tx + dx, ty + dy, dz)
        mats = {"dirt": dirt, "grass": grass, "water": water, "stone": stone, "leaf": leaf, "wood": wood}
        for key, cells in meshes.items():
            bmm = _bm.new()
            for (x, y, z) in cells:
                _bm.ops.create_cube(bmm, size=0.5, matrix=__import__("mathutils").Matrix.Translation((x * 0.5, y * 0.5, z * 0.5)))
            me = bpy.data.meshes.new(key)
            bmm.to_mesh(me)
            bmm.free()
            ob = bpy.data.objects.new(key, me)
            bpy.context.scene.collection.objects.link(ob)
            link(ob, mats[key])
        hero = bm.box("hero", (0.35, 0.35, 0.5), (0, 0, 0), mat("hero", p.get("hero", "#ff7b54"), 0.5))
        bm.box("heroeyes", (0.2, 0.05, 0.06), (0, -0.18, 0.12), mat("eyes", "#141414", 0.4)).parent = hero
        path = [Vector((-2.5, -2.0, 1.3)), Vector((-0.5, -1.0, 1.55)), Vector((1.0, 0.2, 1.8)), Vector((2.0, 1.2, 1.55))]

        def at(t):
            s_ = t * (len(path) - 1)
            i = min(int(s_), len(path) - 2)
            u = s_ - i
            return path[i].lerp(path[i + 1], u) + Vector((0, 0, 0.12 * abs(math.sin(t * 40))))

        bm.key_path(hero, frames, at)
        bm.ANCHORS["hero"] = hero
        if p.get("level"):
            bm.LABELS.append({"anchor": "hero", "text": str(p["level"]), "style": "tag", "hl": True})
        bm.world({**pal, "bg": "#8fd3ff"})
        bm.lights(pal, 3.8)
        cam, tgt = bm.camera((0, 0, 0), (0, 0, 0.8), lens=30)
        d = 11 if vertical() else 8.5
        bm.key_path(cam, frames, lambda t: Vector((math.cos(math.radians(-60 + 25 * t)) * d, math.sin(math.radians(-60 + 25 * t)) * d, d * 0.75)))
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 9.5 if vertical() else 8.0
        return cam

    return {"corridor": scene_corridor, "room_pov": scene_room_pov, "gears": scene_gears, "extrude": scene_extrude,
            "panels": scene_panels, "voxel": scene_voxel}
