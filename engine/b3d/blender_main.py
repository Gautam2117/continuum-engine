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
        f.material_index = 2 if abs(c.normalized().z) > 0.88 else (1 if noise.noise(c * 1.25 + Vector((3, 1, 2))) > 0.1 else 0)
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


SCENES = {"earth_tunnel": scene_earth_tunnel, "moon_drive": scene_moon_drive, "everest_flood": scene_everest_flood}


# ------------------------------------------------------------------ render

def setup_engine(engine: str, samples: int, pal: dict):
    sc = bpy.context.scene
    if engine == "CYCLES":
        sc.render.engine = "CYCLES"
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 4
        sc.cycles.device = "CPU"
        try:  # use a GPU when there is one (Kaggle)
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for kind in ("OPTIX", "CUDA"):
                try:
                    prefs.compute_device_type = kind
                    prefs.get_devices()
                    gpus = [d for d in prefs.devices if d.type == kind]
                    if gpus:
                        for d in prefs.devices:
                            d.use = d.type == kind
                        sc.cycles.device = "GPU"
                        print(f"b3d: Cycles on {kind} ({len(gpus)} device)", flush=True)
                        break
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            pass
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
    SCENES[job["scene"]](job.get("params") or {}, frames, pal)
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
