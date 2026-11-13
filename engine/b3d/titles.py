"""3D title cards: extruded, bevelled type in the channel's own font and colours, words flipping in one by one.

Used for openers, chapter cards and the footage-channel overlay (style F). Spec (inside a b3d show):
  {"scene": "title3d", "params": {"text": "THE HEIST", "hl": "HEIST", "sub": "Episode 4", "look": "plinth" | "float"}}
The engine fills params.font with the channel's display font file.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector


def scenes(bm):
    mat, ease = bm.mat, bm.ease

    def word_obj(txt, font, size, m):
        cu = bpy.data.curves.new("t", "FONT")
        cu.body = txt
        if font:
            try:
                cu.font = bpy.data.fonts.load(font, check_existing=True)
            except Exception:  # noqa: BLE001
                pass
        cu.size = size
        cu.extrude = size * 0.11
        cu.bevel_depth = size * 0.018
        cu.bevel_resolution = 2
        cu.align_x = "LEFT"
        cu.align_y = "BOTTOM"
        ob = bpy.data.objects.new("word", cu)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(m)
        return ob

    def scene_title3d(p, frames, pal):
        text = str(p.get("text", "TITLE")).strip()
        hl = {w.strip(".,?!:").lower() for w in str(p.get("hl", "")).split()}
        font = p.get("font")
        sc = bpy.context.scene
        vertical = sc.render.resolution_y > sc.render.resolution_x
        max_w = 7.0 if vertical else 13.0
        ink, acc = mat("t_ink", pal["ink"], 0.35), mat("t_acc", pal["accent"], 0.3, emit=1.2)
        size = 1.25
        words = text.split()
        # lay words into lines that fit max_w
        objs, lines, cur, cur_w = [], [], [], 0.0
        space = size * 0.32
        for w in words:
            ob = word_obj(w, font, size, acc if w.strip(".,?!:").lower() in hl else ink)
            bpy.context.view_layer.update()
            ww = ob.dimensions.x
            if cur and cur_w + space + ww > max_w:
                lines.append((cur, cur_w))
                cur, cur_w = [], 0.0
            cur.append((ob, ww))
            cur_w += (space if len(cur) > 1 else 0) + ww
            objs.append(ob)
        if cur:
            lines.append((cur, cur_w))
        lh = size * 1.18
        total_h = lh * len(lines)
        idx = 0
        n = len(objs)
        for li, (row, rw) in enumerate(lines):
            x = -rw / 2
            z = total_h / 2 - (li + 1) * lh + size * 0.2 + 1.2
            for ob, ww in row:
                home = Vector((x, 0, z))
                k = idx
                for f in range(1, frames + 1):
                    t = (f - 1) / max(1, frames - 1)
                    st = 0.05 + 0.45 * (k / max(1, n - 1)) if n > 1 else 0.05
                    g = min(1.0, max(0.0, (t - st) / 0.22))
                    over = 1 + 0.12 * math.sin(math.pi * g) if g < 1 else 1.0   # small overshoot
                    ob.location = home + Vector((0, 0, (1 - ease(g)) * -0.6))
                    # Blender lays text flat on the floor; standing it up (90°) faces the camera. Words start flat and stand up.
                    ob.rotation_euler = (math.radians(90) * min(1.0, ease(g) * over), 0, 0)
                    ob.scale = (1, 1, 1)
                    ob.keyframe_insert("location", frame=f)
                    ob.keyframe_insert("rotation_euler", frame=f)
                x += ww + space
                idx += 1
        if p.get("look", "plinth") == "plinth":
            pw = max(rw for _, rw in lines) + 1.4
            bm.box("plinth", (pw, 1.6, 0.18), (0, 0.5, 1.2 - total_h / 2 - 0.25), mat("t_plinth", pal["panel"], 0.6))
            bm.box("edge", (pw, 0.04, 0.05), (0, -0.31, 1.2 - total_h / 2 - 0.16), mat("t_edge", pal["accent"], 0.3, emit=3.0))
        if p.get("sub"):
            bm.ANCHORS["sub"] = (lambda fr: Vector((0, 0, 1.2 - total_h / 2 - 0.75)))
            bm.LABELS.append({"anchor": "sub", "text": str(p["sub"]), "style": "label"})
        bm.floor(pal, z=1.2 - total_h / 2 - 0.35)
        bpy.ops.object.light_add(type="AREA", location=(0, -6, 6))
        key = bpy.context.active_object
        key.data.energy = 900
        key.data.size = 8
        key.rotation_euler = (math.radians(45), 0, 0)
        bpy.ops.object.light_add(type="SPOT", location=(-6, -3, 3))
        sweep = bpy.context.active_object
        sweep.data.energy = 1500
        sweep.data.color = bm.lin(pal["accent"])
        sweep.data.spot_size = math.radians(40)
        bm.key_path(sweep, frames, lambda t: Vector((-6 + 12 * t, -3, 3)))
        bm.world(pal)
        dist = (max_w / 2 + 0.6) / (0.48 if vertical else 0.9)
        cam, tgt = bm.camera((0, 0, 0), (0, 0, 1.2), lens=32)
        bm.key_path(cam, frames, lambda t: Vector((0.6 - 1.2 * ease(t), -dist * (1.08 - 0.08 * ease(t)), 1.2 + dist * 0.12)))
        return cam

    return {"title3d": scene_title3d}
