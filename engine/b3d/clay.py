"""Clay kit (style S3): procedural clay characters, sets and props, all original.

Loaded by blender_main.py inside Blender: `clay.scenes(bm)` returns scene builders, where `bm` is blender_main's
module (materials, anchors, camera helpers). Used by Samjho System, Wild Creature Files, Tiny Histories,
Money Has Mechanics, Think Beyond This, The Odd Units, OHGUMMY and Majority Rules.

Spec (inside a b3d show):
  {"scene": "clay", "params": {
     "set": "tabletop" | "street" | "office" | "shop" | "space" | "studio",
     "cast": [{"name": "Asha", "kind": "person" | "robot" | "mannequin" | "gummy", "color": "#ff7ab6", "skin": "#e0a87a",
               "x": -1.0, "action": "talk" | "wave" | "point" | "walk" | "think" | "cheer" | "idle",
               "to": 1.5, "face": "happy" | "neutral" | "worried" | "shock", "says": "short bubble text"}],
     "props": [{"kind": "rickshaw" | "chai_cart" | "coins" | "house" | "tree" | "desk" | "laptop" | "phone" | "sign"
                        | "box" | "jar" | "lamp", "x": 2.0, "y": 1.0, "n": 5, "label": "₹500", "color": "#..."}],
     "camera": "wide" | "push" | "orbit" | "close" , "focus": 0}}          # focus = cast index for close/push
"""
from __future__ import annotations

import math
import random

import bmesh
import bpy
from mathutils import Vector

SKINS = ["#e0a87a", "#c68a5e", "#a8724a", "#f1c9a5", "#8d5a3b"]


def scenes(bm):
    mat, link, box, cyl, ease = bm.mat, bm.link, bm.box, bm.cyl, bm.ease

    # -------------------------------------------------------------- primitives
    def smooth(ob, level=2):
        for p in ob.data.polygons:
            p.use_smooth = True
        m = ob.modifiers.new("sub", "SUBSURF")
        m.levels = level
        m.render_levels = level
        return ob

    def bevel(ob, width=0.035, segments=2):
        """Soft clay edges on hard shapes (a subdivided box would melt into an egg)."""
        m = ob.modifiers.new("bev", "BEVEL")
        m.width = width
        m.segments = segments
        m.limit_method = "ANGLE"
        for p_ in ob.data.polygons:
            p_.use_smooth = False
        return ob

    def blob(name, size, loc, m, parent=None, level=2):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1, location=loc)
        ob = bpy.context.active_object
        ob.name = name
        ob.scale = size
        link(ob, m)
        smooth(ob, level)
        if parent:
            ob.parent = parent
        return ob

    def capsule(name, r, length, m, parent=None):
        """A capsule with its pivot at the top end (shoulder/hip), hanging down -z."""
        piv = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(piv)
        if parent:
            piv.parent = parent
        bpy.ops.mesh.primitive_cylinder_add(vertices=14, radius=r, depth=length, location=(0, 0, -length / 2))
        c = bpy.context.active_object
        link(c, m)
        smooth(c, 1)
        c.parent = piv
        for z in (0, -length):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=r, location=(0, 0, z))
            e = bpy.context.active_object
            link(e, m)
            smooth(e, 1)
            e.parent = piv
        return piv

    def empty(name, loc=(0, 0, 0), parent=None):
        e = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(e)
        e.location = loc
        if parent:
            e.parent = parent
        return e

    # -------------------------------------------------------------- characters
    def character(i, spec, frames, pal):
        kind = spec.get("kind", "person")
        x0 = float(spec.get("x", 0.0))
        col = spec.get("color", ["#ff7ab6", "#5ee1ff", "#ffcf4a", "#7bd389", "#b46bff"][i % 5])
        skin = spec.get("skin", SKINS[i % len(SKINS)])
        rig = empty(f"char{i}", (x0, 0, 0))
        body_m = mat(f"body{i}", col, 0.55)
        if kind == "robot":
            head_m, limb_m = mat(f"rhead{i}", "#cfd6e4", 0.35, metal=0.3), mat(f"rlimb{i}", "#8e97a8", 0.4, metal=0.4)
        elif kind == "mannequin":
            head_m = limb_m = body_m = mat("mannequin", "#e9e4da", 0.6)
        elif kind == "gummy":
            head_m = limb_m = body_m = mat(f"gummy{i}", col, 0.15, emit=0.25, alpha=0.92)
        else:
            head_m, limb_m = mat(f"skin{i}", skin, 0.6), mat(f"skin{i}", skin, 0.6)
        # body and head (round, toy proportions: big head)
        if kind == "robot":
            body = box(f"rbody{i}", (0.62, 0.46, 0.7), (0, 0, 0.75), body_m)
            body.parent = rig
            bevel(body, 0.06, 3)
            head = box(f"rhead{i}", (0.6, 0.5, 0.48), (0, 0, 1.42), head_m)
            head.parent = rig
            bevel(head, 0.06, 3)
            ant = cyl(f"ant{i}", 0.02, 0.25, (0, 0, 1.78), limb_m, verts=6)
            ant.parent = rig
            blob(f"antball{i}", (0.06, 0.06, 0.06), (0, 0, 1.92), mat(f"antg{i}", pal["accent"], 0.2, emit=3.0), rig, 1)
        else:
            blob(f"body{i}", (0.34, 0.27, 0.42), (0, 0, 0.78), body_m, rig)
            head = blob(f"head{i}", (0.33, 0.31, 0.33), (0, 0, 1.45), head_m, rig)
            if kind == "person":
                hair = blob(f"hair{i}", (0.345, 0.32, 0.2), (0, 0.04, 1.62), mat(f"hair{i}", ["#2b1d16", "#1d1d22", "#5a3a22", "#2b1d16", "#3b2a20"][i % 5], 0.8), rig)
                hair.rotation_euler = (math.radians(-12), 0, 0)
        # face on the -y side (towards camera)
        fy = -0.3 if kind != "robot" else -0.26
        eye_m = mat("eye", "#141414" if kind != "robot" else pal["accent"], 0.3, emit=0.0 if kind != "robot" else 3.0)
        eyes = []
        for sx in (-0.11, 0.11):
            e = blob(f"eye{i}{sx}", (0.045, 0.02, 0.06), (sx, fy, 1.5), eye_m, rig, 1)
            eyes.append(e)
            if kind != "robot":
                blob(f"glint{i}{sx}", (0.014, 0.01, 0.014), (sx + 0.015, fy - 0.018, 1.525), mat("glint", "#ffffff", 0.2, emit=2.0), rig, 0)
        if kind in ("person", "gummy"):
            for sx in (-0.19, 0.19):
                blob(f"cheek{i}{sx}", (0.05, 0.015, 0.03), (sx, fy + 0.03, 1.4), mat("cheek", "#ff8a8a", 0.7), rig, 1)
        mouth = blob(f"mouth{i}", (0.07, 0.02, 0.02), (0, fy - 0.005, 1.33), mat("mouth", "#5b1f22", 0.6), rig, 1)
        brows = [box(f"brow{i}{sx}", (0.09, 0.02, 0.018), (sx, fy - 0.01, 1.6), mat("brow", "#2a1c16", 0.8)) for sx in (-0.11, 0.11)]
        for b in brows:
            b.parent = rig
        # limbs
        arms = []
        for side, sx in (("L", -0.36), ("R", 0.36)):
            a = capsule(f"arm{i}{side}", 0.075, 0.48, limb_m if kind != "person" else body_m, rig)
            a.location = (sx, 0, 1.05)
            hand = blob(f"hand{i}{side}", (0.085, 0.085, 0.085), (0, 0, -0.52), limb_m, a, 1)
            arms.append(a)
        legs = []
        for side, sx in (("L", -0.13), ("R", 0.13)):
            lg = capsule(f"leg{i}{side}", 0.085, 0.32, limb_m if kind == "robot" else mat("trouser", "#2e3442", 0.8), rig)
            lg.location = (sx, 0, 0.42)
            blob(f"shoe{i}{side}", (0.1, 0.13, 0.06), (0, -0.03, -0.38), mat("shoe", "#1c1c20", 0.7), lg, 1)
            legs.append(lg)
        # expression
        face = spec.get("face", "happy")
        if face == "worried":
            brows[0].rotation_euler = (0, math.radians(-18), 0)
            brows[1].rotation_euler = (0, math.radians(18), 0)
        elif face == "shock":
            for b in brows:
                b.location.z += 0.04
        elif face == "happy":
            mouth.scale = (0.08, 0.02, 0.025)
        # action keyframes
        action = spec.get("action", "idle")
        x1 = float(spec.get("to", x0))
        fps = bpy.context.scene.render.fps
        for f in range(1, frames + 1):
            t = (f - 1) / max(1, frames - 1)
            sec = (f - 1) / fps
            bob = 0.025 * math.sin(sec * 2 * math.pi * 0.8 + i)
            rig.location = (x0 + (x1 - x0) * ease(t) if action == "walk" else x0, 0, bob)
            rig.rotation_euler = (0, 0, math.radians(8 * math.sin(sec * 0.9 + i)) if action != "walk" else 0)
            la, ra = arms
            la.rotation_euler = (0, math.radians(-8), 0)
            ra.rotation_euler = (0, math.radians(8), 0)
            ll, rl = legs
            ll.rotation_euler = (0, 0, 0)
            rl.rotation_euler = (0, 0, 0)
            talk = action in ("talk", "point", "wave") or bool(spec.get("says"))
            mz = 0.02 + (0.045 * abs(math.sin(sec * 11 + i)) if talk else 0)
            mouth.scale = (0.07 if face != "shock" else 0.06, 0.02, mz if face != "shock" else 0.07)
            if action == "wave":
                ra.rotation_euler = (0, math.radians(150 + 22 * math.sin(sec * 9)), 0)
            elif action == "point":
                ra.rotation_euler = (math.radians(-10), math.radians(95), 0)
            elif action == "think":
                ra.rotation_euler = (math.radians(-70), math.radians(35), 0)
                rig.rotation_euler = (0, 0, math.radians(10))
            elif action == "cheer":
                k = abs(math.sin(sec * 6))
                la.rotation_euler = (0, math.radians(-150), 0)
                ra.rotation_euler = (0, math.radians(150), 0)
                rig.location.z = bob + 0.25 * k
            elif action == "walk":
                sw = math.sin(sec * 2 * math.pi * 1.6)
                ll.rotation_euler = (math.radians(28 * sw), 0, 0)
                rl.rotation_euler = (math.radians(-28 * sw), 0, 0)
                la.rotation_euler = (math.radians(-24 * sw), math.radians(-8), 0)
                ra.rotation_euler = (math.radians(24 * sw), math.radians(8), 0)
                rig.location.z = 0.04 * abs(sw)
            elif action == "talk":
                ra.rotation_euler = (math.radians(-35 - 12 * math.sin(sec * 3)), math.radians(25), 0)
            for o in (rig, la, ra, ll, rl, mouth):
                o.keyframe_insert("location" if o is rig else "rotation_euler", frame=f)
                if o is rig:
                    o.keyframe_insert("rotation_euler", frame=f)
                if o is mouth:
                    o.keyframe_insert("scale", frame=f)
        bm.ANCHORS[f"head{i}"] = (lambda fr, rig=rig: rig.matrix_world @ Vector((0, 0, 1.95)))
        bm.ANCHORS[f"feet{i}"] = (lambda fr, rig=rig: rig.matrix_world @ Vector((0, -0.4, -0.05)))
        if spec.get("says"):
            bm.LABELS.append({"anchor": f"head{i}", "text": str(spec["says"]), "style": "bubble"})
        if spec.get("name") and spec.get("show_name", True):
            bm.LABELS.append({"anchor": f"feet{i}", "text": str(spec["name"]), "style": "label"})
        return rig

    # -------------------------------------------------------------- props
    def prop(j, spec, pal):
        k = spec.get("kind", "box")
        x, y = float(spec.get("x", 2.0)), float(spec.get("y", 0.6))
        col = spec.get("color")
        root = empty(f"prop{j}", (x, y, 0))
        root.rotation_euler = (0, 0, math.radians(float(spec.get("rot", 0))))

        def add(o):
            o.parent = root
            return o

        if k == "rickshaw":
            yel, grn, blk = mat("rick_y", "#ffcf3a", 0.45), mat("rick_g", "#2f8f4e", 0.5), mat("tyre", "#15171c", 0.9)
            add(bevel(box("rk_body", (1.1, 0.8, 0.55), (0, 0, 0.55), grn)))
            add(bevel(box("rk_top", (1.05, 0.85, 0.12), (0.05, 0, 1.35), yel)))
            for px in (-0.45, 0.5):
                add(cyl("rk_post", 0.03, 0.55, (px, 0.38, 1.05), yel, verts=8))
                add(cyl("rk_post", 0.03, 0.55, (px, -0.38, 1.05), yel, verts=8))
            add(bevel(box("rk_nose", (0.35, 0.45, 0.5), (0.68, 0, 0.55), yel)))
            for wx, wy in ((0.75, 0), (-0.4, 0.42), (-0.4, -0.42)):
                add(cyl("rk_wheel", 0.2, 0.1, (wx, wy, 0.2), blk, verts=16, rot=(math.radians(90), 0, 0)))
        elif k == "chai_cart":
            wood = mat("wood", "#9a6a43", 0.8)
            add(bevel(box("cart", (1.3, 0.7, 0.6), (0, 0, 0.75), wood)))
            add(cyl("kettle", 0.16, 0.28, (0.3, 0, 1.2), mat("steel", "#c9ccd6", 0.25, metal=0.8), verts=16))
            for cx in (-0.35, -0.15, 0.05):
                add(cyl("cup", 0.05, 0.11, (cx, -0.15, 1.11), mat("cup", "#f4efe6", 0.5), verts=10))
            add(cyl("cart_wheel", 0.28, 0.06, (-0.4, 0.38, 0.28), mat("tyre", "#15171c", 0.9), verts=16, rot=(math.radians(90), 0, 0)))
            add(box("awning", (1.45, 0.85, 0.06), (0, 0, 1.75), mat("awn", pal["accent"], 0.5)))
            for px in (-0.65, 0.65):
                add(cyl("pole", 0.025, 0.7, (px, 0.3, 1.4), wood, verts=6))
        elif k == "coins":
            n = int(spec.get("n", 5))
            gold = mat("gold", "#e8b923", 0.25, metal=0.9, emit=0.15)
            for c in range(n):
                add(cyl("coin", 0.22, 0.06, (0.02 * math.sin(c * 1.7), 0.02 * math.cos(c), 0.03 + c * 0.065), gold, verts=24))
        elif k == "house":
            wall = mat(f"hwall{j}", col or random.Random(j).choice(["#f2b880", "#9fd3b5", "#f7d070", "#e88f8f", "#a7c4f2"]), 0.85)
            h = float(spec.get("h", 1.6))
            add(bevel(box("hb", (1.4, 1.1, h), (0, 0, h / 2), wall)))
            add(box("roofslab", (1.55, 1.25, 0.12), (0, 0, h + 0.06), mat("slab", "#e9e2d0", 0.8)))
            for wx in (-0.35, 0.35):
                add(box("win", (0.28, 0.04, 0.32), (wx, -0.56, h * 0.62), mat("win", "#3a4a6a", 0.3, emit=0.4)))
            add(box("door", (0.32, 0.04, 0.55), (0, -0.56, 0.28), mat("doorw", "#7a4b2a", 0.7)))
        elif k == "tree":
            add(cyl("trunk", 0.09, 0.9, (0, 0, 0.45), mat("trunk", "#7a5230", 0.9), verts=8))
            add(smooth(bm.ico("canopy", 0.6, 2, loc=(0, 0, 1.25), jitter=0.12), 1)).data.materials.append(mat("leaf", "#3f8f4e", 0.8))
        elif k == "desk":
            wood = mat("deskw", "#b88a5a", 0.6)
            add(bevel(box("top", (1.6, 0.8, 0.08), (0, 0, 0.78), wood)))
            for lx in (-0.72, 0.72):
                for ly in (-0.32, 0.32):
                    add(box("leg", (0.06, 0.06, 0.76), (lx, ly, 0.38), wood))
        elif k == "laptop":
            add(bevel(box("base", (0.5, 0.35, 0.03), (0, 0, 0.84), mat("alu", "#c9ccd6", 0.3, metal=0.6))))
            scr = add(box("screen", (0.5, 0.025, 0.33), (0, 0.17, 1.0), mat("scr", pal["accent"], 0.2, emit=1.5)))
            scr.rotation_euler = (math.radians(-12), 0, 0)
        elif k == "phone":
            add(bevel(box("ph", (0.16, 0.03, 0.32), (0, 0, 1.0), mat("phb", "#1c1c20", 0.3))))
            add(box("phs", (0.14, 0.01, 0.29), (0, -0.02, 1.0), mat("phs", pal["accent"], 0.2, emit=1.8)))
        elif k == "sign":
            add(cyl("signpost", 0.04, 1.4, (0, 0, 0.7), mat("post", "#5b5f6b", 0.6), verts=8))
            add(bevel(box("board", (1.0, 0.06, 0.55), (0, 0, 1.55), mat("board", col or pal["accent"], 0.5))))
            if spec.get("label"):
                bm.ANCHORS[f"sign{j}"] = (lambda fr, root=root: root.matrix_world @ Vector((0, -0.1, 1.68)))
                bm.LABELS.append({"anchor": f"sign{j}", "text": str(spec["label"]), "style": "label", "hl": True})
        elif k == "jar":
            add(smooth(cyl("jar", 0.16, 0.34, (0, 0, 0.17), mat("glass", "#cfe8ff", 0.05, alpha=0.6), verts=16), 1))
            add(cyl("lid", 0.17, 0.05, (0, 0, 0.36), mat("lid", col or "#ff5a3c", 0.4), verts=16))
        elif k == "lamp":
            add(cyl("lp", 0.04, 2.4, (0, 0, 1.2), mat("post", "#5b5f6b", 0.6), verts=8))
            add(bevel(box("lh", (0.35, 0.2, 0.12), (0.12, 0, 2.42), mat("lh", "#3a3f4a", 0.5))))
            add(box("bulb", (0.2, 0.12, 0.03), (0.12, 0, 2.35), mat("bulb", "#fff3c4", 0.2, emit=6.0)))
        else:  # box / crate / parcel
            s_ = float(spec.get("s", 0.5))
            add(bevel(box("crate", (s_, s_, s_), (0, 0, s_ / 2), mat(f"crate{j}", col or "#c9a227", 0.7))))
        if spec.get("label") and k != "sign":
            bm.ANCHORS[f"prop{j}"] = (lambda fr, root=root: root.matrix_world @ Vector((0, 0, 1.9 if k in ("rickshaw", "chai_cart", "house", "tree") else 1.0)))
            bm.LABELS.append({"anchor": f"prop{j}", "text": str(spec["label"]), "style": "tag", "hl": True})
        return root

    # -------------------------------------------------------------- sets
    def build_set(name, pal):
        rnd = random.Random(5)
        if name == "tabletop":
            top = cyl("table", 7.5, 0.4, (0, 0, -0.2), mat("tablewood", "#b98b5e", 0.7), verts=64)
            smooth(top, 1)
            cyl("cloth", 7.0, 0.02, (0, 0, 0.01), mat("cloth", "#e9e2d0", 0.95), verts=64)
            bm.world({**pal, "bg": "#2a2420"})
        elif name == "street":
            bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
            link(bpy.context.active_object, mat("paving", "#d9ccb4", 0.9))
            box("road", (60, 3.2, 0.02), (0, 3.4, 0.01), mat("asphalt", "#3a3d45", 0.9))
            box("kerb", (60, 0.3, 0.12), (0, 1.65, 0.06), mat("kerb", "#c9c2b3", 0.8))
            for k_ in range(9):
                x = -10 + k_ * 2.4
                prop(100 + k_, {"kind": "house", "x": x, "y": 6.8, "h": rnd.uniform(1.4, 2.6)}, pal)
            # bunting
            flags = [mat(f"flag{c}", c, 0.6) for c in ("#ff7a59", "#ffcf4a", "#5ee1ff", "#7bd389", "#ff7ab6")]
            for k_ in range(26):
                x = -8 + k_ * 0.62
                z = 3.3 - 0.35 * math.sin(math.pi * (k_ % 13) / 12)
                bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.17, depth=0.01, location=(x, 4.9, z), rotation=(math.radians(90), math.radians(180), 0))
                link(bpy.context.active_object, flags[k_ % 5])
            prop(200, {"kind": "tree", "x": -6.5, "y": 1.2}, pal)
            prop(201, {"kind": "lamp", "x": 6.0, "y": 1.3}, pal)
            bm.world({**pal, "bg": "#9fc6e8"})
        elif name == "office":
            bm.floor(pal, size=40)
            box("wall", (30, 0.2, 6), (0, 4.0, 3.0), mat("wallo", "#e8e4dc", 0.9))
            box("window", (3.2, 0.05, 1.8), (-3.0, 3.88, 2.4), mat("windo", "#bfe3ff", 0.2, emit=1.2))
            prop(300, {"kind": "desk", "x": 0, "y": 1.2}, pal)
            prop(301, {"kind": "laptop", "x": 0.1, "y": 1.2}, pal)
            prop(302, {"kind": "tree", "x": 3.4, "y": 2.6}, pal)
            bm.world({**pal, "bg": "#d9d4ca"})
        elif name == "shop":
            bm.floor(pal, size=40)
            box("backwall", (30, 0.2, 6), (0, 3.2, 3.0), mat("wallshop", "#f4e3c1", 0.9))
            for row in range(3):
                box(f"shelf{row}", (6, 0.5, 0.06), (0, 2.9, 1.0 + row * 0.8), mat("shelfw", "#9a6a43", 0.8))
                for c in range(9):
                    prop(400 + row * 10 + c, {"kind": "jar" if (c + row) % 2 else "box", "x": -2.6 + c * 0.65, "y": 2.85,
                                              "s": 0.35, "color": ["#ff5a3c", "#5ee1ff", "#ffcf4a", "#7bd389"][(c + row) % 4]}, pal)
                    bpy.context.scene.objects[f"prop{400 + row * 10 + c}"].location.z = 1.03 + row * 0.8
            bevel(box("counter", (5.0, 0.9, 1.0), (0, 0.9, 0.5), mat("counter", "#ffd166", 0.55)))
            bm.world({**pal, "bg": "#2b3a5c"})
        elif name == "space":
            bm.stars(400, pal["ink"], r0=25, r1=45)
            disc = cyl("platform", 3.2, 0.25, (0, 0, -0.125), mat("plat", pal["panel"], 0.6), verts=48)
            smooth(disc, 1)
            cyl("ring", 3.25, 0.04, (0, 0, 0.01), mat("ringg", pal["accent"], 0.3, emit=3.0), verts=48)
        else:  # studio: seamless backdrop
            bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
            link(bpy.context.active_object, mat("studio", pal["panel"], 0.95))
            box("cyc", (40, 0.2, 20), (0, 8, 10), mat("studio", pal["panel"], 0.95))

    # -------------------------------------------------------------- scene
    def scene_clay(p, frames, pal):
        setn = p.get("set", "studio")
        build_set(setn, pal)
        cast = (p.get("cast") or [{"name": "", "action": "wave", "says": "Hi!"}])[:5]
        rigs = [character(i, c, frames, pal) for i, c in enumerate(cast)]
        for j, pr in enumerate((p.get("props") or [])[:12]):
            prop(j, pr, pal)
        # lighting: warm key, cool rim
        bpy.ops.object.light_add(type="SUN", location=(4, -6, 8))
        sun = bpy.context.active_object
        sun.data.energy = 4.0 if setn in ("street", "tabletop", "office") else 2.6
        sun.data.angle = math.radians(12)
        sun.data.color = bm.lin("#fff1dc")
        sun.rotation_euler = (math.radians(52), math.radians(8), math.radians(28))
        bpy.ops.object.light_add(type="AREA", location=(-5, -3, 4))
        rim = bpy.context.active_object
        rim.data.energy = 500
        rim.data.size = 6
        rim.data.color = bm.lin(pal["accent"])
        rim.rotation_euler = (math.radians(70), 0, math.radians(-55))
        # camera
        sc = bpy.context.scene
        vertical = sc.render.resolution_y > sc.render.resolution_x
        # frame the cast; props may sit at the edges
        xs = [float(c.get("x", 0)) for c in cast] + [float(c.get("to", c.get("x", 0))) for c in cast]
        span = (max(xs) - min(xs)) if xs else 0
        cx = (max(xs) + min(xs)) / 2 if xs else 0
        mode = p.get("camera", "push")
        fi = int(p.get("focus", 0)) % max(1, len(rigs))
        focus_obj = rigs[fi] if rigs else None
        half_w = 0.48 if vertical else 0.9
        dist = max(3.4, (span / 2 + 0.9) / half_w)
        tilt = setn == "tabletop"
        cam, tgt = bm.camera((0, 0, 0), (cx, 0, 1.05), lens=32, dof_obj=focus_obj if tilt or mode == "close" else None,
                             fstop=0.9 if tilt else 2.8)
        h = dist * 0.75 + 1.0 if tilt else 1.75
        if mode == "close" and focus_obj:
            fx = float(cast[fi].get("x", 0))
            bm.key_path(cam, frames, lambda t: Vector((fx + 0.3 * ease(t), -3.4 + 0.3 * ease(t), 1.55)))
            bm.key_path(tgt, frames, lambda t: Vector((fx, 0, 1.3)))
        elif mode == "orbit":
            a0 = math.radians(-90 - 18)
            bm.key_path(cam, frames, lambda t: Vector((cx + math.cos(a0 + math.radians(36) * ease(t)) * dist,
                                                     math.sin(a0 + math.radians(36) * ease(t)) * dist, h)))
        elif mode == "wide":
            bm.key_path(cam, frames, lambda t: Vector((cx + 0.4 * ease(t), -dist * 1.15, h)))
        else:  # push in
            bm.key_path(cam, frames, lambda t: Vector((cx, -dist * (1.18 - 0.25 * ease(t)), h * (1.0 - 0.15 * ease(t)))))
        return cam

    return {"clay": scene_clay}
