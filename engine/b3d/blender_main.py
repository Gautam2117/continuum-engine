"""Runs INSIDE Blender's Python (the `bpy` module), never inside the engine's own Python.

    python3.13 engine/b3d/blender_main.py job.json

job.json: {"scene": "earth_tunnel", "params": {...}, "frames": 144, "fps": 24, "step": 1,
           "size": [1080, 1160], "engine": "WORKBENCH" | "CYCLES" | "EEVEE", "samples": 16,
           "palette": {"bg": "#05070f", "panel": "#0c1a33", "ink": "#eef4ff", "accent": "#5ee1ff"},
           "out": "/path/to/frames"}
Writes out/f_0001.png ... and out/done.json. Everything here is procedural and original (no third-party models).
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import time

import bpy  # noqa: I001 — bpy must load first: it puts bmesh and mathutils on the path
import bmesh
from mathutils import Vector, noise

# ------------------------------------------------------------------ helpers

def lin(h: str, k: float = 1.0) -> tuple:
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 * k for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


_MATS: dict = {}

# Screen anchors: scenes register 3D points (objects or callables) and per-frame scalars; after keyframing, main()
# projects them through the camera for every frame and writes anchors.json, so the engine can draw labels in its own
# fonts exactly on the 3D objects. LABELS tells the engine what to draw at which anchor.
ANCHORS: dict = {}   # name -> object (its world location) or fn(frame) -> Vector
SCALARS: dict = {}   # name -> fn(t 0..1) -> float
LABELS: list = []    # {"anchor": name, "text": str} | {"anchor": name, "value": scalar_name, "unit": str, "decimals": int, "style": "value"|"label"|"tag"}


def mat(name: str, hexc: str, rough: float = 0.6, emit: float = 0.0, metal: float = 0.0, alpha: float = 1.0):
    key = (name, hexc, rough, emit, metal, alpha)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    col = lin(hexc)
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*col, 1)
        b.inputs["Emission Strength"].default_value = emit
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:  # noqa: BLE001
            pass
    # Workbench reads the viewport colour; brighten emissive parts so they read as glowing there too
    vc = lin(hexc, 1.0 + min(emit, 2.0) * 0.12)
    m.diffuse_color = (*[min(1.0, v) for v in vc], alpha)
    m.roughness = rough
    _MATS[key] = m
    return m


def link(ob, m):
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return ob


def flat(ob):
    for p in ob.data.polygons:
        p.use_smooth = False
    return ob


def ico(name: str, r: float, sub: int, loc=(0, 0, 0), jitter: float = 0.0, seed: float = 0.0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    if jitter:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        for v in bm.verts:
            v.co *= 1 + jitter * noise.noise(v.co * 1.6 + Vector((seed, seed * 2, 0)))
        bm.to_mesh(ob.data)
        bm.free()
    return flat(ob)


def box(name, size, loc, m, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    return link(ob, m)


def cyl(name, r, depth, loc, m, verts=12, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    return flat(link(ob, m))


def boolean_cut(ob, cutter):
    mod = ob.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    try:
        mod.material_mode = "TRANSFER"
    except Exception:  # noqa: BLE001
        pass
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return flat(ob)


def stars(n: int, ink: str, r0=40, r1=60, avoid=None, seed=3):
    rnd = random.Random(seed)
    m = mat("star", ink, emit=3.0)
    bm = bmesh.new()
    for _ in range(n):
        v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        if v.length < 0.01:
            continue
        v = v.normalized() * rnd.uniform(r0, r1)
        if avoid and avoid(v):
            continue
        s = rnd.uniform(0.04, 0.16)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=s, matrix=__import__("mathutils").Matrix.Translation(v))
    me = bpy.data.meshes.new("stars")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("stars", me)
    bpy.context.scene.collection.objects.link(ob)
    return link(ob, m)


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def camera(loc, target, lens=50, dof_obj=None, fstop=4.0):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    cam.data.lens = lens
    cam.data.clip_end = 500
    tgt = bpy.data.objects.new("cam_target", None)
    bpy.context.scene.collection.objects.link(tgt)
    tgt.location = target
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    if dof_obj is not None:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_object = dof_obj
        cam.data.dof.aperture_fstop = fstop
    return cam, tgt


def key_path(ob, frames: int, fn, data_path="location"):
    """Keyframe ob.<data_path> = fn(t) for every frame (t in 0..1). Linear interpolation keeps motion exact."""
    for f in range(1, frames + 1):
        t = (f - 1) / max(1, frames - 1)
        setattr(ob, data_path, fn(t))
        ob.keyframe_insert(data_path, frame=f)
    ad = ob.animation_data
    if ad and ad.action:
        try:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except Exception:  # noqa: BLE001 — layered actions (Blender 5) keep their own interpolation
            pass


def lights(pal, key_energy=3.2):
    bpy.ops.object.light_add(type="SUN", location=(6, -6, 9))
    sun = bpy.context.active_object
    sun.data.energy = key_energy
    sun.data.angle = math.radians(6)
    sun.rotation_euler = (math.radians(48), math.radians(12), math.radians(38))
    bpy.ops.object.light_add(type="AREA", location=(-8, -3, 4))
    rim = bpy.context.active_object
    rim.data.energy = 900
    rim.data.size = 8
    rim.data.color = lin(pal["accent"])
    rim.rotation_euler = (math.radians(75), 0, math.radians(-60))
    return sun, rim


def world(pal):
    w = bpy.data.worlds.new("world")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*lin(pal["bg"]), 1)
    bg.inputs["Strength"].default_value = 1.0
    w.color = lin(pal["bg"])


# ------------------------------------------------------------------ scenes
# Each scene builds geometry and keyframes for `frames` frames. Units: Earth radius = 3.

def scene_earth_tunnel(p: dict, frames: int, pal: dict):
    """Earth cut open (one quarter removed), a tunnel pole to pole, a capsule falling through.
    params: t0, t1 = trip progress (0 = north surface, 0.5 = centre, 1 = south surface);
            orbit = degrees the camera swings; zoom = 0..1 dolly; labels (ignored here, HUD draws them)."""
    R = 3.0
    t0, t1 = float(p.get("t0", 0.0)), float(p.get("t1", 0.5))
    orbit, zoom = float(p.get("orbit", 26)), float(p.get("zoom", 0.25))
    ocean, land, ice = mat("ocean", "#2a6fdb", 0.35), mat("land", "#46a35a"), mat("ice", "#eef4ff")
    layers = [("crust", "#8d6e63", 0.97, 0.0), ("mantle", "#e8613a", 0.93, 0.5),
              ("outer", "#ffb300", 0.55, 1.4), ("inner", "#ffe066", 0.19, 3.0)]
    def wedge(eps):
        """A cube that removes the quarter facing the camera; eps pushes the cut planes toward the camera so
        inner layers' cut faces sit just in front of outer ones (no z-fighting, clean concentric rings)."""
        bpy.ops.mesh.primitive_cube_add(size=1, location=(R * 1.5 + eps, -R * 1.5 - eps, 0))
        cu = bpy.context.active_object
        cu.scale = (R * 3, R * 3, R * 3.2)
        return cu

    earth = ico("earth", R, 4, jitter=0.018)
    for m in (ocean, land, ice):
        earth.data.materials.append(m)
    for f in earth.data.polygons:
        c = Vector(f.center)
        n = noise.noise(c * 1.25 + Vector((3.1, 1.7, 2.3)))
        f.material_index = 2 if abs(c.normalized().z) > 0.88 else (1 if n > 0.1 else 0)
    cu = wedge(0.0)
    boolean_cut(earth, cu)
    bpy.data.objects.remove(cu)
    # drop the surface's own cut faces: the layers below show the inside
    bm = bmesh.new()
    bm.from_mesh(earth.data)
    caps = [f for f in bm.faces if all(abs(v.co.x) < 1e-3 or abs(v.co.y) < 1e-3 for v in f.verts) and f.calc_area() > 0]
    bmesh.ops.delete(bm, geom=caps, context="FACES")
    bm.to_mesh(earth.data)
    bm.free()
    for i, (name, col, k, em) in enumerate(layers):
        ob = ico(name, R * k, 3 if k > 0.3 else 2)
        link(ob, mat(name, col, 0.7, emit=em))
        if name != "inner":
            cu = wedge(0.004 * (i + 1))
            boolean_cut(ob, cu)
            bpy.data.objects.remove(cu)
    # tunnel: a dark rod with a cyan glow line, standing in the open wedge
    tun = cyl("tunnel", 0.075, 2 * R * 1.04, (0.05, -0.05, 0), mat("tunnel", pal["panel"], 0.9), verts=10)
    glow = cyl("glow", 0.02, 2 * R * 1.04, (0.13, -0.13, 0), mat("glow", pal["accent"], 0.3, emit=4.0), verts=6)
    # capsule
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=8, radius=0.2, location=(0.05, -0.05, R))
    cap = flat(link(bpy.context.active_object, mat("capsule", pal["accent"], 0.25, emit=2.0)))
    cap.scale = (1, 1, 1.9)
    # harmonic motion in a uniform Earth: z = R cos(pi * s), s = trip progress 0..1
    key_path(cap, frames, lambda t: Vector((0.05, -0.05, R * math.cos(math.pi * (t0 + (t1 - t0) * t)))))
    stars(260, pal["ink"], avoid=lambda v: False)
    lights(pal)
    d0, d1 = 14.5, 14.5 - 3.0 * zoom
    a0 = math.radians(-45 - orbit / 2)
    cam, tgt = camera((0, 0, 0), (0, 0, 1.05), lens=46)
    key_path(cam, frames, lambda t: Vector((math.cos(a0 + math.radians(orbit) * ease(t)) * (d0 + (d1 - d0) * ease(t)),
                                             math.sin(a0 + math.radians(orbit) * ease(t)) * (d0 + (d1 - d0) * ease(t)),
                                             4.2 - 0.8 * ease(t))))
    return cam


def scene_moon_drive(p: dict, frames: int, pal: dict):
    """A glowing highway from Earth to the Moon, a tiny car driving it. params: p0, p1 = progress 0..1; shot = wide|chase."""
    p0, p1 = float(p.get("p0", 0.0)), float(p.get("p1", 0.15))
    shot = p.get("shot", "wide")
    sc_ = bpy.context.scene
    vertical = sc_.render.resolution_y > sc_.render.resolution_x
    # vertical frames stack Earth (bottom) and Moon (top); landscape frames lay them left to right
    E, M = (Vector((-2.5, 0, -6.2)), Vector((2.2, 2.0, 6.6))) if vertical else (Vector((-9, 0, -1.2)), Vector((10, 3, 2.4)))
    earth = ico("earth", 3.0, 4, loc=E, jitter=0.02)
    ocean, land, ice = mat("ocean", "#2a6fdb", 0.35), mat("land", "#46a35a"), mat("ice", "#eef4ff")
    for m in (ocean, land, ice):
        earth.data.materials.append(m)
    for f in earth.data.polygons:
        c = Vector(f.center)  # mesh coordinates are already relative to the planet's centre
        # north cap only: the planet is turned so its south pole faces the camera
        f.material_index = 2 if c.normalized().z > 0.88 else (1 if noise.noise(c * 1.25 + Vector((3, 1, 2))) > 0.1 else 0)
    earth.rotation_euler = (math.radians(-90), 0, math.radians(15))   # show oceans and land, not the ice cap
    moon = ico("moon", 0.82, 3, loc=M, jitter=0.06, seed=4.0)
    link(moon, mat("moon", "#c9ccd6", 0.9))
    # road: a curve from Earth's surface to the Moon's
    a = E + (M - E).normalized() * 3.0
    b = M - (M - E).normalized() * 0.82
    ctrl = (a + b) / 2 + (Vector((-3.0, -1.0, 0)) if vertical else Vector((0, 0, 3.2)))

    def road_pt(s):
        return (1 - s) ** 2 * a + 2 * (1 - s) * s * ctrl + s ** 2 * b

    bm = bmesh.new()
    n = 160
    prev = None
    side = Vector((0, 1, 0))
    for i in range(n + 1):
        s = i / n
        c = road_pt(s)
        tan = (road_pt(min(1, s + 0.01)) - road_pt(max(0, s - 0.01))).normalized()
        sd = tan.cross(Vector((0, -1, 0)) if vertical else Vector((0, 0, 1))).normalized() * 0.22
        v1, v2 = bm.verts.new(c + sd), bm.verts.new(c - sd)
        if prev:
            bm.faces.new((prev[0], prev[1], v2, v1))
        prev = (v1, v2)
    me = bpy.data.meshes.new("road")
    bm.to_mesh(me)
    bm.free()
    road = bpy.data.objects.new("road", me)
    bpy.context.scene.collection.objects.link(road)
    link(road, mat("road", "#3a4a6a", 0.8, emit=0.6))
    # lane dashes in the accent colour
    for i in range(0, n, 4):
        s = (i + 1) / n
        c = road_pt(s)
        bpy.ops.mesh.primitive_cube_add(size=1, location=c + Vector((0, 0, 0.02)))
        d = bpy.context.active_object
        d.scale = (0.12, 0.025, 0.01)
        tan = road_pt(min(1, s + 0.01)) - road_pt(max(0, s - 0.01))
        d.rotation_euler = (0, -math.atan2(tan.z, math.hypot(tan.x, tan.y)), math.atan2(tan.y, tan.x))
        link(d, mat("dash", pal["accent"], 0.3, emit=3.0))
    # the car: body, cabin, four wheels, parented to an empty that rides the road
    rig = bpy.data.objects.new("car", None)
    bpy.context.scene.collection.objects.link(rig)
    red = mat("car", "#ff5a3c", 0.35)
    parts = [box("body", (0.34, 0.17, 0.07), (0, 0, 0.07), red),
             box("cabin", (0.17, 0.14, 0.07), (-0.03, 0, 0.15), mat("glass", pal["ink"], 0.15, emit=0.4))]
    for dx in (-0.11, 0.11):
        for dy in (-0.09, 0.09):
            parts.append(cyl("wheel", 0.045, 0.04, (dx, dy, 0.04), mat("tyre", "#15171c", 0.9), verts=10, rot=(math.radians(90), 0, 0)))
    for o in parts:
        o.parent = rig
    rig.scale = (1.6, 1.6, 1.6)
    # headlight glow so the car reads even when small
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.06, location=(0.2, 0, 0.08))
    hl = link(bpy.context.active_object, mat("headlight", "#fff6c8", 0.2, emit=6.0))
    hl.parent = rig

    def place(t):
        s = p0 + (p1 - p0) * t
        c = road_pt(s)
        tan = road_pt(min(1, s + 0.005)) - road_pt(max(0, s - 0.005))
        return c, tan

    for f in range(1, frames + 1):
        t = (f - 1) / max(1, frames - 1)
        c, tan = place(t)
        rig.location = c + Vector((0, 0, 0.02))
        rig.rotation_euler = (0, -math.atan2(tan.z, math.hypot(tan.x, tan.y)), math.atan2(tan.y, tan.x))
        rig.keyframe_insert("location", frame=f)
        rig.keyframe_insert("rotation_euler", frame=f)
    stars(320, pal["ink"])
    lights(pal)
    if shot == "chase":
        cam, tgt = camera((0, 0, 0), (0, 0, 0), lens=30)
        for f in range(1, frames + 1):
            t = (f - 1) / max(1, frames - 1)
            c, tan = place(t)
            tn = tan.normalized()
            cam.location = c - tn * 0.9 + Vector((0, -3.4, 0.4))
            tgt.location = c + tn * 1.4
            cam.keyframe_insert("location", frame=f)
            tgt.keyframe_insert("location", frame=f)
    else:
        if vertical:
            cam, tgt = camera((0, 0, 0), (0.2, 1.0, 1.0), lens=30)
            key_path(cam, frames, lambda t: Vector((0.5 + 1.5 * ease(t), -26.0 + 2.0 * ease(t), 1.0)))
        else:
            cam, tgt = camera((0, 0, 0), (0.5, 0.8, 0.6), lens=26)
            key_path(cam, frames, lambda t: Vector((1.0 + 2.0 * ease(t), -19.0 + 1.5 * ease(t), 4.5)))
    return cam


def scene_everest_flood(p: dict, frames: int, pal: dict):
    """A low-poly mountain with a town at its feet; sea level rises. params: h0, h1 = water height as a fraction of the peak."""
    h0, h1 = float(p.get("h0", 0.0)), float(p.get("h1", 0.5))
    orbit = float(p.get("orbit", 30))
    size, res, peak = 16.0, 46, 5.5
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=res, size=size)
    terr = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(terr.data)
    for v in bm.verts:
        r = math.hypot(v.co.x, v.co.y)
        main = peak * math.exp(-(r / 3.4) ** 1.6)
        ridge = 1.3 * math.exp(-((v.co.x - 2.8) ** 2 + (v.co.y + 1.5) ** 2) / 5)
        v.co.z = max(0.0, main + ridge + 0.45 * noise.noise(v.co * 0.45) + 0.2 * noise.noise(v.co * 1.3)) - 0.15
    bm.to_mesh(terr.data)
    bm.free()
    for m in (mat("grass", "#3f8f4e"), mat("rock", "#7a6f66", 0.8), mat("snow", "#f3f7ff", 0.5)):
        terr.data.materials.append(m)
    for f in terr.data.polygons:
        z = f.center.z
        f.material_index = 2 if z > peak * 0.62 else (1 if z > peak * 0.25 else 0)
    flat(terr)
    # flag on the summit
    cyl("pole", 0.025, 0.7, (0, 0, peak + 0.55), mat("pole", "#d8d8d8"), verts=6)
    box("flag", (0.32, 0.02, 0.18), (0.17, 0, peak + 0.8), mat("flag", pal["accent"], 0.4, emit=1.2))
    # little town at the foot
    rnd = random.Random(9)
    roof, wall = mat("roof", "#c75b3a"), mat("wall", "#f2e6d0")
    for i in range(26):
        ang = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(5.2, 7.2)
        x, y = math.cos(ang) * rr, math.sin(ang) * rr
        w = rnd.uniform(0.22, 0.38)
        box(f"house{i}", (w, w * 0.8, w * 0.7), (x, y, w * 0.35), wall, rot=(0, 0, ang))
        box(f"roof{i}", (w * 1.08, w * 0.88, w * 0.25), (x, y, w * 0.82), roof, rot=(0, 0, ang))
    # water: a big translucent slab whose top rises
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    water = bpy.context.active_object
    water.name = "water"
    link(water, mat("water", "#2a6fdb", 0.08, emit=0.15, alpha=0.78))
    water.scale = (size * 1.02, size * 1.02, 1)

    def wz(t):
        h = peak * (h0 + (h1 - h0) * ease(t))
        return h

    for f in range(1, frames + 1):
        t = (f - 1) / max(1, frames - 1)
        h = max(0.02, wz(t))
        water.scale = (size * 1.02, size * 1.02, h + 0.3)
        water.location = (0, 0, (h - 0.3) / 2)
        water.keyframe_insert("scale", frame=f)
        water.keyframe_insert("location", frame=f)
    stars(180, pal["ink"], r0=60, r1=80, avoid=lambda v: v.z < 5)
    lights(pal, 3.6)
    a0 = math.radians(-60)
    cam, tgt = camera((0, 0, 0), (0, 0, peak * 0.45), lens=34)
    key_path(cam, frames, lambda t: Vector((math.cos(a0 + math.radians(orbit) * ease(t)) * 17.5,
                                             math.sin(a0 + math.radians(orbit) * ease(t)) * 17.5,
                                             7.8)))
    return cam


def floor(pal, size=300.0, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    fl = bpy.context.active_object
    return link(fl, mat("floor", pal["panel"], 0.95))


def stagger(i: int, n: int, t: float, span: float = 0.55) -> float:
    """Growth 0..1 for item i of n: items start one after another and each takes `span` of the shot."""
    start = (1 - span) * (i / max(1, n - 1)) if n > 1 else 0.0
    return ease((t - start) / span)


def scene_bars3d(p: dict, frames: int, pal: dict):
    """3D columns that rise one after another. params: items [{label, value, highlight}], unit, decimals."""
    items = (p.get("items") or [{"label": "A", "value": 1}, {"label": "B", "value": 3, "highlight": True}])[:6]
    n = len(items)
    vmax = max(float(it["value"]) for it in items) or 1.0
    Hmax, gap, w = 6.0, 3.0, 1.5
    floor(pal)
    x0 = -(n - 1) * gap / 2
    base_m = mat("bar", "#9fb3d1", 0.55)
    hi_m = mat("bar_hi", pal["accent"], 0.4, emit=0.8)
    for i, it in enumerate(items):
        x = x0 + i * gap
        h_full = max(0.05, Hmax * float(it["value"]) / vmax)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0))
        col = bpy.context.active_object
        col.name = f"bar{i}"
        link(col, hi_m if it.get("highlight") else base_m)
        # pivot at the bottom: move mesh up by 0.5 so scaling z grows upward
        for v in col.data.vertices:
            v.co.z += 0.5
        for f in range(1, frames + 1):
            g = stagger(i, n, (f - 1) / max(1, frames - 1))
            col.scale = (w, w, max(0.001, h_full * g))
            col.keyframe_insert("scale", frame=f)
        box(f"plinth{i}", (w * 1.25, w * 1.25, 0.12), (x, 0, 0.06), mat("plinth", pal["bg"], 0.9))
        ANCHORS[f"bar{i}_top"] = (lambda fr, x=x, h=h_full, i=i: Vector((x, 0, h * stagger(i, n, (fr - 1) / max(1, frames - 1)) + 0.35)))
        ANCHORS[f"bar{i}_base"] = (lambda fr, x=x: Vector((x, -w * 0.9, 0.0)))
        SCALARS[f"bar{i}"] = (lambda t, i=i, v=float(it["value"]): v * stagger(i, n, t))
        LABELS.append({"anchor": f"bar{i}_base", "text": str(it.get("label", "")), "style": "label"})
        LABELS.append({"anchor": f"bar{i}_top", "value": f"bar{i}", "unit": p.get("unit", ""),
                       "decimals": int(p.get("decimals", 0 if vmax >= 20 else 1)), "style": "value",
                       "hl": bool(it.get("highlight"))})
    lights(pal)
    sc_ = bpy.context.scene
    vertical = sc_.render.resolution_y > sc_.render.resolution_x
    span = max(4.0, n * gap)
    a0 = math.radians(-74)
    cam, tgt = camera((0, 0, 0), (0, 0, Hmax * (0.8 if vertical else 0.5)), lens=32)
    # 32 mm lens: half the frame width covers about 0.52 x distance in a vertical frame, 0.9 x in landscape
    dist = (span * 0.5 / 0.48 + 4.5) if vertical else max(Hmax * 1.45, span * 0.5 / 0.85 + 4)
    key_path(cam, frames, lambda t: Vector((math.cos(a0 + math.radians(14) * ease(t)) * dist,
                                             math.sin(a0 + math.radians(14) * ease(t)) * dist,
                                             Hmax * 0.75)))
    return cam


def scene_orbit3d(p: dict, frames: int, pal: dict):
    """The Moon's orbit today and in the what-if, both moving with Kepler's third law (period ∝ r^1.5).
    params: ratio (what-if radius ÷ today's), a, b (labels), turns (how many of today's orbits the shot shows, default 0.35)."""
    ratio = float(p.get("ratio", 0.5))
    turns = float(p.get("turns", 0.35))
    r0 = 7.0
    r1 = r0 * ratio
    earth = ico("earth", 1.6, 4, jitter=0.02)
    for m in (mat("ocean", "#2a6fdb", 0.35), mat("land", "#46a35a"), mat("ice", "#eef4ff")):
        earth.data.materials.append(m)
    for f in earth.data.polygons:
        c = Vector(f.center)
        f.material_index = 2 if abs(c.normalized().z) > 0.88 else (1 if noise.noise(c * 2.2 + Vector((3, 1, 2))) > 0.1 else 0)
    for name, r, col in (("ring_a", r0, "#9fb3d1"), ("ring_b", r1, pal["accent"])):
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.03, major_segments=128, minor_segments=6)
        link(bpy.context.active_object, mat(name, col, 0.4, emit=1.5 if name == "ring_b" else 0.3))
    moon_a = ico("moon_a", 0.5, 3, jitter=0.06, seed=4)
    link(moon_a, mat("moon", "#c9ccd6", 0.9))
    moon_b = ico("moon_b", 0.5, 3, jitter=0.06, seed=4)
    link(moon_b, mat("moon_b", "#e8ebf5", 0.8, emit=0.4))
    wa = 2 * math.pi * turns
    wb = wa * ratio ** -1.5   # Kepler: closer orbit, shorter period
    key_path(moon_a, frames, lambda t: Vector((r0 * math.cos(wa * t + 0.4), r0 * math.sin(wa * t + 0.4), 0)))
    key_path(moon_b, frames, lambda t: Vector((r1 * math.cos(wb * t + 2.6), r1 * math.sin(wb * t + 2.6), 0)))
    rot = (lambda t: wa * t)
    key_path(earth, frames, lambda t: Vector((0, 0, rot(t) * 2.0)), data_path="rotation_euler")
    ANCHORS["moon_a"] = moon_a
    ANCHORS["moon_b"] = moon_b
    LABELS.append({"anchor": "moon_a", "text": str(p.get("a", "Today")), "style": "tag"})
    LABELS.append({"anchor": "moon_b", "text": str(p.get("b", "What if")), "style": "tag", "hl": True})
    stars(260, pal["ink"])
    lights(pal)
    cam, tgt = camera((0, 0, 0), (0, 0, 0), lens=36)
    key_path(cam, frames, lambda t: Vector((0.0 + 2.0 * ease(t), -r0 * 2.35 + 1.0 * ease(t), r0 * 1.15)))
    return cam


def scene_fall3d(p: dict, frames: int, pal: dict):
    """Objects dropped from the same height in different gravity, side by side, in true proportion of time.
    params: height (m), items [{label, g}]. The shot lasts as long as the slowest fall."""
    items = (p.get("items") or [{"label": "Earth", "g": 9.8}, {"label": "Moon", "g": 1.62}])[:4]
    hm = float(p.get("height", 20))
    n = len(items)
    tl = [math.sqrt(2 * hm / float(it["g"])) for it in items]
    T = max(tl)
    Hs, gap = 7.0, 3.2   # scene units: drop height and lane spacing
    x0 = -(n - 1) * gap / 2
    colours = ["#3f8f4e", "#9a9aa3", "#c4553a", "#c9a227"]
    for i, it in enumerate(items):
        x = x0 + i * gap
        box(f"ground{i}", (2.6, 2.6, 0.4), (x, 0, -0.2), mat(f"ground{i}", colours[i % 4], 0.9))
        box(f"tower{i}", (0.25, 0.25, Hs + 0.5), (x - 0.9, 0.6, (Hs + 0.5) / 2), mat("tower", "#3a4a6a", 0.8))
        box(f"ledge{i}", (0.9, 0.5, 0.1), (x - 0.45, 0.4, Hs + 0.5), mat("tower", "#3a4a6a", 0.8))
        ball = ico(f"ball{i}", 0.38, 2)
        link(ball, mat("ball", pal["accent"], 0.3, emit=1.0))
        g = float(it["g"])
        zf = (lambda t, g=g: max(0.38, 0.38 + Hs * (1 - (0.5 * g * (t * T) ** 2) / hm)))
        key_path(ball, frames, lambda t, x=x, zf=zf: Vector((x, 0, zf(t))))
        ANCHORS[f"lane{i}"] = (lambda fr, x=x: Vector((x, -1.6, -0.4)))
        ANCHORS[f"ball{i}"] = ball
        SCALARS[f"t{i}"] = (lambda t, tli=tl[i]: min(t * T, tli))
        LABELS.append({"anchor": f"lane{i}", "text": str(it.get("label", "")), "style": "label"})
        LABELS.append({"anchor": f"ball{i}", "value": f"t{i}", "unit": "s", "decimals": 1, "style": "tag"})
    floor(pal, z=-0.4)
    lights(pal)
    sc_ = bpy.context.scene
    vertical = sc_.render.resolution_y > sc_.render.resolution_x
    cam, tgt = camera((0, 0, 0), (0, 0, Hs * 0.5), lens=32)
    dist = ((n * gap + 2.6) * 0.5 / 0.48 + 1.5) if vertical else (Hs * 1.55)
    key_path(cam, frames, lambda t: Vector((1.2 * ease(t), -dist, Hs * 0.62)))
    return cam


SCENES = {"earth_tunnel": scene_earth_tunnel, "moon_drive": scene_moon_drive, "everest_flood": scene_everest_flood,
          "bars3d": scene_bars3d, "orbit3d": scene_orbit3d, "fall3d": scene_fall3d}


# ------------------------------------------------------------------ render

def use_gpu(sc) -> bool:
    """Switch Cycles to an NVIDIA/AMD GPU when one is present (Kaggle T4s). Prints what it chose."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except Exception as e:  # noqa: BLE001
        print(f"b3d: no cycles prefs ({e}); CPU", flush=True)
        return False
    for kind in ("OPTIX", "CUDA", "HIP"):
        try:
            prefs.compute_device_type = kind
            try:
                prefs.refresh_devices()
            except Exception:  # noqa: BLE001
                prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type == kind]
            if not gpus:
                continue
            for d in prefs.devices:
                d.use = d.type == kind
            sc.cycles.device = "GPU"
            if kind == "OPTIX":
                try:
                    sc.cycles.denoiser = "OPTIX"  # denoise on the GPU too
                except Exception:  # noqa: BLE001
                    pass
            print(f"b3d: Cycles GPU {kind}: {', '.join(d.name for d in gpus)}", flush=True)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"b3d: {kind} unavailable ({e})", flush=True)
    print("b3d: Cycles on CPU", flush=True)
    return False


def setup_engine(engine: str, samples: int, pal: dict):
    sc = bpy.context.scene
    if engine == "CYCLES":
        sc.render.engine = "CYCLES"
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 4
        sc.cycles.device = "CPU"
        sc.render.use_persistent_data = True
        use_gpu(sc)
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in [i.identifier for i in sc.view_settings.bl_rna.properties["look"].enum_items] else "None"
    elif engine == "EEVEE":
        sc.render.engine = "BLENDER_EEVEE"
        try:
            sc.eevee.taa_render_samples = samples
        except Exception:  # noqa: BLE001
            pass
        sc.view_settings.view_transform = "AgX"
    else:  # WORKBENCH: flat-shaded clay with soft shadows, cavity and outlines; fast on any CPU
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_shadows = True
        sh.shadow_intensity = 0.55
        sh.show_cavity = True
        sh.cavity_type = "BOTH"
        sh.cavity_ridge_factor = 1.0
        sh.cavity_valley_factor = 1.2
        sh.show_specular_highlight = True
        sh.show_object_outline = True
        sh.object_outline_color = lin(pal["bg"])
        try:
            sh.use_dof = True
        except Exception:  # noqa: BLE001
            pass
        sc.display.render_aa = "16"
        sc.view_settings.view_transform = "Standard"


def export_anchors(out: str, frames: int):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    cam = sc.camera
    pts = {k: [] for k in ANCHORS}
    for f in range(1, frames + 1):
        sc.frame_set(f)
        for k, src in ANCHORS.items():
            co = src(f) if callable(src) else src.matrix_world.translation
            v = world_to_camera_view(sc, cam, Vector(co))
            pts[k].append([round(v.x, 5), round(1 - v.y, 5), 1 if v.z > 0 else 0])
    sca = {k: [round(fn((f - 1) / max(1, frames - 1)), 4) for f in range(1, frames + 1)] for k, fn in SCALARS.items()}
    json.dump({"points": pts, "scalars": sca, "labels": LABELS}, open(os.path.join(out, "anchors.json"), "w"))


def main(job_path: str):
    job = json.load(open(job_path))
    out = job["out"]
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()
    sc = bpy.context.scene
    W, H = job["size"]
    frames, step = int(job["frames"]), int(job.get("step", 1))
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.fps = int(job.get("fps", 24))
    sc.frame_start, sc.frame_end, sc.frame_step = 1, frames, step
    pal = job.get("palette") or {"bg": "#05070f", "panel": "#0c1a33", "ink": "#eef4ff", "accent": "#5ee1ff"}
    world(pal)
    ANCHORS.clear()
    SCALARS.clear()
    LABELS.clear()
    SCENES[job["scene"]](job.get("params") or {}, frames, pal)
    export_anchors(out, frames)
    setup_engine(job.get("engine", "WORKBENCH").upper(), int(job.get("samples", 16)), pal)
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = os.path.join(out, "f_")
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    took = time.time() - t0
    json.dump({"frames": frames, "step": step, "seconds": round(took, 1)}, open(os.path.join(out, "done.json"), "w"))
    print(f"b3d: {job['scene']} {frames}f/{step} {W}x{H} {job.get('engine')} in {took:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[-1])
