"""
SPIN — Layered Glassy Blue Soft-Body LED Slab (standalone, headless Blender).

Builds a JSON-driven, double-sided, glassy-reflective blue layered rectangle mesh
with soft-body-style deformation, baked to:
    GLB  (morph-target animation, KHR transmission, doubleSided) -> web/three.js
    USDZ (time-sampled points)                                   -> iOS AR
    ABC  (Alembic point cache)                                   -> DCC master
    .blend                                                       -> live preview

Config is read from glass_led_config.json (auto-created on first run) so the build
is fully JSON-parameterized. A manifest JSON is written next to the exports.
"""
import bpy, bmesh, math, os, json
import numpy as np
from mathutils import Vector

OUT = r"C:/Users/joeyw/Downloads/SPIN_GlassLED"
os.makedirs(OUT, exist_ok=True)
CFG_PATH = os.path.join(OUT, "glass_led_config.json")

DEFAULT_CFG = {
    "name": "GlassLED_Slab",
    "rect_x": 3.0, "rect_y": 1.6,      # blue rectangle proportions
    "grid_x": 44, "grid_y": 28,         # subdivisions
    "layers": 4,                        # stacked glass layers
    "layer_gap": 0.06,                  # z gap between layers
    "frames": 40,
    "amp": 0.22,                        # soft-body wobble amplitude
    "softness": 1.0,                    # higher = more jiggle on upper layers
    "color_rgb": [0.04, 0.22, 0.85],    # blue
    "roughness": 0.07,
    "transmission": 0.92,
    "ior": 1.45,
    "emission_strength": 1.2            # inner LED glow
}

def load_cfg():
    if not os.path.exists(CFG_PATH):
        json.dump(DEFAULT_CFG, open(CFG_PATH, "w"), indent=2)
        return dict(DEFAULT_CFG)
    c = dict(DEFAULT_CFG); c.update(json.load(open(CFG_PATH)))
    return c

# --------------------------------------------------------------------------
def glass_material(cfg):
    mat = bpy.data.materials.new("M_GlassBlue")
    mat.use_nodes = True
    mat.use_backface_culling = False        # -> glTF doubleSided = true
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    r, g, b = cfg["color_rgb"]
    def setin(name, val):
        if name in bsdf.inputs: bsdf.inputs[name].default_value = val
    setin("Base Color", (r, g, b, 1.0))
    setin("Roughness", cfg["roughness"])
    setin("Metallic", 0.0)
    setin("IOR", cfg["ior"])
    # Blender 4.x/5.x naming
    setin("Transmission Weight", cfg["transmission"])
    setin("Transmission", cfg["transmission"])
    setin("Emission Color", (r*0.4, g*0.6, b, 1.0))
    setin("Emission Strength", cfg["emission_strength"])
    return mat

def build_layer(cfg, li, mat):
    name = f"{cfg['name']}_L{li}"
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    gx, gy = cfg["grid_x"], cfg["grid_y"]
    sx, sy = cfg["rect_x"], cfg["rect_y"]
    z0 = li * cfg["layer_gap"]
    bm = bmesh.new()
    vt = [[None]*gx for _ in range(gy)]
    for j in range(gy):
        for i in range(gx):
            x = -sx/2 + sx*i/(gx-1)
            y = -sy/2 + sy*j/(gy-1)
            vt[j][i] = bm.verts.new((x, y, z0))
    bm.verts.ensure_lookup_table()
    for j in range(gy-1):
        for i in range(gx-1):
            bm.faces.new((vt[j][i], vt[j][i+1], vt[j+1][i+1], vt[j+1][i]))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = ((c.x+sx/2)/sx, (c.y+sy/2)/sy)
    bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    return ob, z0

def softbody_height(u, v, t, li, cfg):
    """Looping jelly/soft-body wobble; upper layers jiggle more, edges pinned."""
    soft = 1.0 + cfg["softness"] * li / max(1, cfg["layers"]-1)
    edge = math.sin(math.pi*u) * math.sin(math.pi*v)      # 0 at edges (pinned)
    w1 = math.sin(u*4.0 + t*2.0) * math.cos(v*3.0 - t*1.3)
    w2 = math.sin((u+v)*5.0 - t*2.4)
    n  = math.sin(u*11.0 + t*3.1) * math.sin(v*9.0 - t*2.2) * 0.25
    return cfg["amp"] * soft * edge * (0.6*w1 + 0.3*w2 + n)

def bake(cfg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start = 1; sc.frame_end = cfg["frames"]
    mat = glass_material(cfg)
    objs = []
    for li in range(cfg["layers"]):
        ob, z0 = build_layer(cfg, li, mat)
        me = ob.data
        base = [v.co.copy() for v in me.vertices]
        ob.shape_key_add(name="Basis", from_mix=False)
        for f in range(cfg["frames"]):
            t = f / cfg["frames"] * 6.2831853
            sk = ob.shape_key_add(name=f"f{f:03d}", from_mix=False)
            sx, sy = cfg["rect_x"], cfg["rect_y"]
            for idx, v in enumerate(me.vertices):
                co = base[idx]
                u = (co.x+sx/2)/sx; w = (co.y+sy/2)/sy
                sk.data[idx].co = co + Vector((0,0, softbody_height(u, w, t, li, cfg)))
        kbs = [k for k in me.shape_keys.key_blocks if k.name != "Basis"]
        for f in range(cfg["frames"]):
            sc.frame_set(f+1)
            for k, kb in enumerate(kbs):
                kb.value = 1.0 if k == f else 0.0
                kb.keyframe_insert("value", frame=f+1)
        objs.append(ob)
    sc.frame_set(1)
    return objs

def export_all(cfg, objs):
    bpy.ops.object.select_all(action='SELECT')
    base = os.path.join(OUT, cfg["name"])
    res = {}
    try:
        bpy.ops.export_scene.gltf(filepath=base+".glb", export_format='GLB',
            export_morph=True, export_animations=True, export_morph_animation=True,
            export_materials='EXPORT')
        res["glb"] = os.path.getsize(base+".glb")
    except Exception as e: res["glb"] = f"ERR {e}"
    try:
        bpy.ops.wm.usd_export(filepath=base+".usdz", export_animation=True,
            export_materials=True)
        res["usdz"] = os.path.getsize(base+".usdz")
    except Exception as e: res["usdz"] = f"ERR {e}"
    try:
        bpy.ops.wm.alembic_export(filepath=base+".abc", start=1, end=cfg["frames"])
        res["abc"] = os.path.getsize(base+".abc")
    except Exception as e: res["abc"] = f"ERR {e}"
    try:
        bpy.ops.wm.save_as_mainfile(filepath=base+".blend")
        res["blend"] = os.path.getsize(base+".blend")
    except Exception as e: res["blend"] = f"ERR {e}"
    json.dump({"config": cfg, "exports": res, "layers": len(objs)},
              open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
    print("[EXPORT]", res)

def main():
    cfg = load_cfg()
    objs = bake(cfg)
    export_all(cfg, objs)
    print("[DONE]", OUT)

if __name__ == "__main__":
    main()
