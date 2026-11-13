"""Spike: low-poly Earth cutaway with a tunnel and a falling capsule.
Usage: python earth_cutaway.py ENGINE OUTDIR [frames] [w h]
ENGINE: EEVEE | CYCLES | WORKBENCH
"""
import sys, math, random, time, os
import bpy, bmesh
from mathutils import Vector, noise

engine = sys.argv[1].upper()
out = sys.argv[2]
frames = int(sys.argv[3]) if len(sys.argv) > 3 else 1
W, H = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (1080, 1920)
os.makedirs(out, exist_ok=True)
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.fps = 30
sc.frame_start, sc.frame_end = 1, frames

def mat(name, rgb, rough=0.6, emit=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    m.diffuse_color = (*rgb, 1)  # workbench
    return m

def hexc(h):
    h = h.lstrip("#")
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)

OCEAN, LAND, ICE = mat("ocean", hexc("#2a6fdb"), 0.35), mat("land", hexc("#4caf50")), mat("ice", hexc("#eef4ff"))
CRUST, MANTLE = mat("crust", hexc("#8d6e63")), mat("mantle", hexc("#ff7043"), emit=0.6)
OUTER, INNER = mat("outer", hexc("#ffb300"), emit=1.5), mat("inner", hexc("#fff3c4"), emit=3.0)
CAPS, TUN = mat("caps", hexc("#5ee1ff"), 0.2, emit=2.0), mat("tun", hexc("#0c1a33"), 0.9)

def lowpoly_sphere(name, r, sub, mats, displace=0.0, cut=True):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=r)
    ob = bpy.context.active_object; ob.name = name
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    for v in bm.verts:
        n = noise.noise(v.co * 1.7)
        v.co *= 1 + displace * n
    for m in mats: me.materials.append(m)
    for f in bm.faces:
        c = f.calc_center_median()
        if len(mats) > 1:
            n = noise.noise(c * 1.4 + Vector((3, 1, 2)))
            idx = 1 if n > 0.12 else 0
            if abs(c.normalized().z) > 0.86: idx = 2
            f.material_index = idx
        f.smooth = False
    if cut:  # remove the front-right wedge (x>0, y<0) to show layers
        kill = [f for f in bm.faces if all(v.co.x > 0 and v.co.y < 0 for v in f.verts)]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(me); bm.free()
    return ob

R = 3.0
lowpoly_sphere("Earth", R, 4, [OCEAN, LAND, ICE], displace=0.02)
lowpoly_sphere("Crust", R * 0.97, 3, [CRUST])
lowpoly_sphere("Mantle", R * 0.93, 3, [MANTLE])
lowpoly_sphere("Outer", R * 0.55, 3, [OUTER])
lowpoly_sphere("Inner", R * 0.19, 2, [INNER], cut=False)

# cut faces: two quarter-discs closing the wedge per layer (colored rings)
def wedge_wall(axis, r_out, r_in, m, name):
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=1, fill_type="NOTHING")
    ob = bpy.context.active_object; ob.name = name
    bm = bmesh.new()
    steps = 12
    for i in range(steps):
        a0 = math.pi * 0.5 * i / steps - math.pi / 2
        a1 = math.pi * 0.5 * (i + 1) / steps - math.pi / 2
        pts = [(r_in, a0), (r_out, a0), (r_out, a1), (r_in, a1)]
        vs = []
        for rr, a in pts:
            if axis == "xz":   # plane y=0, quadrant x>0
                vs.append(bm.verts.new((rr * math.cos(a + math.pi / 2), 0, rr * math.sin(a + math.pi / 2) * (1 if i >= 0 else 1))))
            else:              # plane x=0, quadrant y<0
                vs.append(bm.verts.new((0, -rr * math.cos(a + math.pi / 2), rr * math.sin(a + math.pi / 2))))
        bm.faces.new(vs)
    # mirror lower half
    for i in range(steps):
        a0 = -math.pi * 0.5 * i / steps; a1 = -math.pi * 0.5 * (i + 1) / steps
        vs = []
        for rr, a in [(r_in, a0), (r_out, a0), (r_out, a1), (r_in, a1)]:
            if axis == "xz":
                vs.append(bm.verts.new((rr * math.cos(a), 0, rr * math.sin(a))))
            else:
                vs.append(bm.verts.new((0, -rr * math.cos(a), rr * math.sin(a))))
        bm.faces.new(vs)
    bm.to_mesh(ob.data); bm.free()
    ob.data.materials.append(m)

layers = [(R * 0.97, R * 0.93, CRUST), (R * 0.93, R * 0.55, MANTLE), (R * 0.55, R * 0.19, OUTER), (R * 0.19, 0.001, INNER)]
for ax in ("xz", "yz"):
    for i, (ro, ri, m) in enumerate(layers):
        wedge_wall(ax, ro, ri, m, f"wall_{ax}_{i}")

# tunnel straight through along z on the cut plane edge? place it on x=0 plane visible face
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.07, depth=2 * R * 1.02, location=(0.02, -0.02, 0))
tun = bpy.context.active_object; tun.data.materials.append(TUN)

# capsule falls from north pole to centre with g(r) ~ r (harmonic)
bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.13, location=(0.03, -0.03, R))
cap = bpy.context.active_object; cap.scale = (1, 1, 1.8); cap.data.materials.append(CAPS)
for fr in range(1, frames + 1):
    t = (fr - 1) / max(1, frames - 1)          # 0..1 over the shot = quarter period
    cap.location.z = R * math.cos(t * math.pi / 2)
    cap.keyframe_insert("location", frame=fr)

# star field
for i in range(160):
    v = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized() * random.uniform(30, 40)
    if v.x < 5 and v.y > -5: continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.03, 0.09), location=v)
    bpy.context.active_object.data.materials.append(ICE)

# lights + camera
bpy.ops.object.light_add(type="SUN", location=(5, -6, 8)); sun = bpy.context.active_object
sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
bpy.ops.object.light_add(type="AREA", location=(-6, -4, 3)); fill = bpy.context.active_object
fill.data.energy = 300; fill.data.size = 6; fill.data.color = hexc("#5ee1ff")
fill.rotation_euler = (math.radians(70), 0, math.radians(-55))

bpy.ops.object.camera_add(location=(11.5, -11.5, 4.0))
cam = bpy.context.active_object; sc.camera = cam
cam.data.lens = 50
tgt = bpy.data.objects.new("tgt", None); sc.collection.objects.link(tgt); tgt.location = (0, 0, 0.2)
c = cam.constraints.new("TRACK_TO"); c.target = tgt
# slow dolly in
cam.keyframe_insert("location", frame=1)
cam.location = (10.2, -10.2, 3.4); cam.keyframe_insert("location", frame=max(2, frames))

world = bpy.data.worlds.new("w"); sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (*hexc("#05070f"), 1)
world.color = hexc("#05070f")

if engine == "CYCLES":
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = int(os.environ.get("SAMPLES", "24")); sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3
elif engine == "EEVEE":
    sc.render.engine = "BLENDER_EEVEE"
    try: sc.eevee.taa_render_samples = 16
    except Exception: pass
else:
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "MATERIAL"
    sh.show_shadows = True; sh.show_cavity = True; sh.cavity_type = "BOTH"
    sh.show_specular_highlight = True
    sc.display.render_aa = "8"

sc.view_settings.view_transform = "AgX" if engine != "WORKBENCH" else "Standard"
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = os.path.join(out, f"{engine.lower()}_")
t0 = time.time()
if frames == 1:
    sc.render.filepath = os.path.join(out, f"{engine.lower()}.png")
    bpy.ops.render.render(write_still=True)
else:
    bpy.ops.render.render(animation=True)
print(f"RENDER {engine} {frames}f {W}x{H}: {time.time()-t0:.1f}s")
