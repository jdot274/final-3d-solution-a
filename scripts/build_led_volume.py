"""
SPIN — Baked Animated LED Volume builder (standalone, runs in headless Blender).

Produces, for each of three motion drivers, a beautiful animated displaced
"LED volume" mesh baked to portable formats:
    - GLB   : morph-target (shape-key) animation  -> web / three.js / Babylon
    - USDZ  : time-sampled points (Alembic-equivalent) -> Apple AR Quick Look
    - ABC   : Alembic point cache -> DCC interchange master

Drivers:
    waves     : procedural Gerstner/sine math
    heightmap : a synthesized grayscale image SEQUENCE used as per-frame height
    video     : a synthesized RGB "video" pattern; luminance drives height
                (swap SYNTH for a real movie by setting VIDEO_PATH below)

Each mesh gets an emissive LED-grid material with a generated dot texture so the
"pixels" read in any glTF/USD viewer.

Run:  blender --background --python build_led_volume.py
"""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector

# ----------------------------- config -------------------------------------
OUT       = r"C:/Users/joeyw/Desktop/SPIN_LED_Exports"
GRID      = 48           # verts per side (48x48 = 2304 verts)
FRAMES    = 48           # baked frames
SIZE      = 2.0          # mesh extent (meters)
AMP       = 0.35         # displacement amplitude
LED_RES   = 32           # LED pixels per side for the emissive grid texture
VIDEO_PATH = ""          # set to a real .mp4/.mov to use real video; "" = synth
os.makedirs(OUT, exist_ok=True)

# ----------------------------- helpers ------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end   = FRAMES

def led_emissive_image(name):
    """Generate an LED-dot emissive texture (round emitters on black)."""
    res = 512
    px  = np.zeros((res, res, 4), dtype=np.float32)
    px[..., 3] = 1.0
    cell = res // LED_RES
    yy, xx = np.mgrid[0:res, 0:res]
    cx = (xx // cell) * cell + cell/2
    cy = (yy // cell) * cell + cell/2
    d  = np.sqrt((xx-cx)**2 + (yy-cy)**2) / (cell*0.5)
    dot = np.clip(1.0 - d, 0.0, 1.0) ** 2
    # rainbow-ish per-cell hue so the grid reads as colored pixels
    gx = (xx // cell) / LED_RES
    gy = (yy // cell) / LED_RES
    px[..., 0] = dot * (0.5 + 0.5*np.sin(6.28*gx))
    px[..., 1] = dot * (0.5 + 0.5*np.sin(6.28*gy + 2.1))
    px[..., 2] = dot * (0.5 + 0.5*np.sin(6.28*(gx+gy) + 4.2))
    img = bpy.data.images.new(name, res, res)
    img.pixels = px.reshape(-1).tolist()
    img.pack()
    return img

def make_led_material(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex  = nt.nodes.new("ShaderNodeTexImage")
    tex.image = led_emissive_image(name + "_tex")
    tex.interpolation = 'Closest'   # crisp pixels
    # Emission (Blender 4.x Principled uses 'Emission Color' + 'Emission Strength')
    try:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 6.0
        bsdf.inputs["Base Color"].default_value = (0,0,0,1)
    except Exception:
        pass
    return mat

def build_grid(name):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    bm = bmesh.new()
    step = SIZE / (GRID-1)
    verts = [[None]*GRID for _ in range(GRID)]
    for j in range(GRID):
        for i in range(GRID):
            x = -SIZE/2 + i*step
            y = -SIZE/2 + j*step
            verts[j][i] = bm.verts.new((x, y, 0.0))
    bm.verts.ensure_lookup_table()
    for j in range(GRID-1):
        for i in range(GRID-1):
            bm.faces.new((verts[j][i], verts[j][i+1], verts[j+1][i+1], verts[j+1][i]))
    # simple planar UVs
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = ((co.x+SIZE/2)/SIZE, (co.y+SIZE/2)/SIZE)
    bm.to_mesh(me)
    bm.free()
    return ob

# ----------------------------- drivers ------------------------------------
def driver_waves(u, v, t):
    # u,v in [0,1]; Gerstner-ish sum of sines
    a = math.sin((u*6.0) + t*2.0)
    b = math.sin((v*5.0) - t*1.7 + u*3.0)
    c = math.sin((u+v)*7.0 + t*2.6)
    return (a*0.5 + b*0.3 + c*0.2)

def synth_height_seq():
    """Per-frame grayscale heightmaps (radial moving ripples) as a numpy stack."""
    R = 64
    seq = np.zeros((FRAMES, R, R), dtype=np.float32)
    yy, xx = np.mgrid[0:R, 0:R]
    cx = cy = R/2
    rad = np.sqrt((xx-cx)**2 + (yy-cy)**2)
    for f in range(FRAMES):
        t = f / FRAMES
        seq[f] = np.sin(rad*0.5 - t*6.28*2) * np.exp(-rad/40.0)
    return seq

def synth_video_seq():
    """Per-frame RGB 'video' (plasma); returns luminance stack for height."""
    R = 64
    seq = np.zeros((FRAMES, R, R), dtype=np.float32)
    yy, xx = np.mgrid[0:R, 0:R].astype(np.float32)
    for f in range(FRAMES):
        t = f / FRAMES * 6.28
        p = (np.sin(xx*0.3 + t) + np.sin(yy*0.3 - t)
             + np.sin((xx+yy)*0.2 + t) + np.sin(np.sqrt(xx*xx+yy*yy)*0.3 - t))
        seq[f] = p / 4.0
    return seq

def real_video_seq(path):
    img = bpy.data.images.load(path)
    img.source = 'MOVIE'
    nframes = img.frame_duration
    R = 64
    seq = np.zeros((min(FRAMES, nframes), R, R), dtype=np.float32)
    for f in range(seq.shape[0]):
        img.frame_current = f+1
        arr = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], -1)
        # downsample to R x R, luminance
        ys = (np.linspace(0, arr.shape[0]-1, R)).astype(int)
        xs = (np.linspace(0, arr.shape[1]-1, R)).astype(int)
        sub = arr[np.ix_(ys, xs)][..., :3]
        seq[f] = sub @ np.array([0.299, 0.587, 0.114]) - 0.5
    return seq

def sample(seq, u, v, f):
    R = seq.shape[1]
    i = min(R-1, int(u*(R-1))); j = min(R-1, int(v*(R-1)))
    return float(seq[f % seq.shape[0], j, i])

# ----------------------------- bake + export ------------------------------
def bake_variant(name, height_fn):
    ob = build_grid(name)
    me = ob.data
    ob.data.materials.append(make_led_material("M_" + name))
    base = [v.co.copy() for v in me.vertices]
    # basis shape key
    ob.shape_key_add(name="Basis", from_mix=False)
    for f in range(FRAMES):
        t = f / FRAMES * 6.28
        sk = ob.shape_key_add(name=f"f{f:03d}", from_mix=False)
        for idx, v in enumerate(me.vertices):
            co = base[idx]
            u = (co.x + SIZE/2)/SIZE
            w = (co.y + SIZE/2)/SIZE
            sk.data[idx].co = co + Vector((0.0, 0.0, AMP*height_fn(u, w, f, t)))
    # keyframe morph influence: each key peaks on its frame (triangular blend)
    kbs = [kb for kb in me.shape_keys.key_blocks if kb.name != "Basis"]
    for f in range(FRAMES):
        bpy.context.scene.frame_set(f+1)
        for k, kb in enumerate(kbs):
            kb.value = 1.0 if k == f else 0.0
            kb.keyframe_insert("value", frame=f+1)
    bpy.context.scene.frame_set(1)
    export_all(ob, name)

def export_all(ob, name):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    glb = os.path.join(OUT, name + ".glb")
    usz = os.path.join(OUT, name + ".usdz")
    abc = os.path.join(OUT, name + ".abc")
    results = {}
    try:
        bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB',
            use_selection=True, export_morph=True, export_animations=True,
            export_morph_animation=True)
        results['glb'] = os.path.getsize(glb)
    except Exception as e:
        results['glb'] = f"ERR {e}"
    try:
        bpy.ops.wm.usd_export(filepath=usz, selected_objects_only=True,
            export_animation=True, export_materials=True)
        results['usdz'] = os.path.getsize(usz)
    except Exception as e:
        results['usdz'] = f"ERR {e}"
    try:
        bpy.ops.wm.alembic_export(filepath=abc, selected=True,
            start=1, end=FRAMES)
        results['abc'] = os.path.getsize(abc)
    except Exception as e:
        results['abc'] = f"ERR {e}"
    print(f"[EXPORT] {name}: {results}")

# ----------------------------- run ----------------------------------------
def main():
    # waves
    reset_scene()
    bake_variant("LEDVolume_Waves",
        lambda u, v, f, t: driver_waves(u, v, t))
    # heightmap (image sequence)
    reset_scene()
    hseq = synth_height_seq()
    bake_variant("LEDVolume_Heightmap",
        lambda u, v, f, t: sample(hseq, u, v, f))
    # video
    reset_scene()
    vseq = real_video_seq(VIDEO_PATH) if VIDEO_PATH else synth_video_seq()
    bake_variant("LEDVolume_Video",
        lambda u, v, f, t: sample(vseq, u, v, f))
    print("[DONE] all variants exported to", OUT)

if __name__ == "__main__":
    main()
