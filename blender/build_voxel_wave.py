"""
build_voxel_wave.py
===================
Builds a DEEP-BLUE GLASSY LED-VOLUME WAVE as an animated GLB.

The mesh is a rectangular field of many small rectangular bars (voxels) —
like an LED volume wall / audio equalizer — whose heights rise and fall
with a radial wave-particle equation.  Exported as:

  voxel_wave.glb            — 60-frame morph animation, deep-blue glass PBR
                              (KHR_transmission / volume / ior / specular /
                              iridescence), emissive LED glow by height.
  voxel_wave_openpbr.mtlx   — OpenPBR-surface MaterialX material (deep blue
                              glass, transmission, coat, emission) — the
                              dynamic material for the GLB.

Run:  python3 build_voxel_wave.py
"""

import io, math, os, pathlib
import numpy as np
from PIL import Image
import pygltflib
from pygltflib import (
    GLTF2, Scene, Node, Mesh, Primitive, Accessor, BufferView, Buffer,
    Material, Texture, Image as GLTFImage, Sampler, Asset,
    Animation, AnimationChannel, AnimationSampler, AnimationChannelTarget,
)

# ── CONFIG ───────────────────────────────────────────────────────────────────
TILES        = 40          # 40×40 = 1600 bars
GAP          = 0.18        # gap between bars (fraction of cell)
TOTAL_FRAMES = 60
DECAY        = 0.22
SPAN         = 200.0       # full width in cm (UE5: 1 unit = 1 cm)
BASE_H       = 6.0         # minimum bar height (cm)
AMP_H        = 60.0        # height amplitude (cm)
FPS          = 24.0
EMISSIVE_TEX = 256         # LED gradient texture resolution

print("═" * 60)
print("  Deep-Blue Glass LED-Volume Wave  —  voxel GLB generator")
print("═" * 60)

# ── WAVE FIELD ────────────────────────────────────────────────────────────────
lin = np.linspace(-5, 5, TILES)
CX, CY = np.meshgrid(lin, lin)            # bar centre coords (grid space)
R = np.sqrt(CX**2 + CY**2)

def wave(t):
    w  = np.sin(2*np.pi*R - t*2.0) * np.exp(-DECAY*R)
    w += np.sin(4*np.pi*R - t*3.5 + 1.2) * np.exp(-0.40*R) * 0.30
    w += np.sin(8*np.pi*R - t*5.0 + 2.4) * np.exp(-0.70*R) * 0.08
    return w                               # roughly [-1.2, 1.2]

def bar_heights(t):
    w = wave(t)
    h = BASE_H + AMP_H * (w * 0.5 + 0.5)   # map to [BASE_H, BASE_H+AMP_H]
    return h

# ── BUILD ONE BAR (box) ───────────────────────────────────────────────────────
# Each bar: 8 verts. Bottom 4 at z=0 (fixed), top 4 at z=h (animated).
cell  = SPAN / TILES
half  = (cell * (1.0 - GAP)) * 0.5         # half-width of a bar footprint

# Vertex template (unit bar, height 1): bottom then top
#   indices 0-3 bottom (z=0), 4-7 top (z=1)
def bar_verts(cx_cm, cy_cm, h):
    x0, x1 = cx_cm - half, cx_cm + half
    y0, y1 = cy_cm - half, cy_cm + half
    return np.array([
        [x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0],   # bottom
        [x0, y0, h], [x1, y0, h], [x1, y1, h], [x0, y1, h],   # top
    ], dtype=np.float32)

# Box faces (12 tris) — outward winding
BOX_TRIS = np.array([
    [0,1,2],[0,2,3],          # bottom
    [4,6,5],[4,7,6],          # top
    [0,4,5],[0,5,1],          # -Y
    [1,5,6],[1,6,2],          # +X
    [2,6,7],[2,7,3],          # +Y
    [3,7,4],[3,4,0],          # -X
], dtype=np.uint32)

# Per-vertex normals for a box (approx, smooth-ish via face assignment)
BOX_NRM = np.array([
    [0,0,-1],[0,0,-1],[0,0,-1],[0,0,-1],
    [0,0, 1],[0,0, 1],[0,0, 1],[0,0, 1],
], dtype=np.float32)

# ── ASSEMBLE FRAME 0 + MORPH FRAMES ───────────────────────────────────────────
print(f"Building {TILES}×{TILES} = {TILES*TILES} bars …")

cx_cm = (CX / 5.0) * (SPAN * 0.5)          # grid → cm
cy_cm = (CY / 5.0) * (SPAN * 0.5)

H0 = bar_heights(0.0)

base_verts  = []
base_nrm    = []
all_idx     = []
base_color  = []
base_uv     = []
vert_off    = 0
NB = TILES * TILES

# Pre-flatten for speed
cxf = cx_cm.ravel(); cyf = cy_cm.ravel(); h0f = H0.ravel()
maxH = BASE_H + AMP_H

for b in range(NB):
    v = bar_verts(cxf[b], cyf[b], h0f[b])
    base_verts.append(v)
    base_nrm.append(BOX_NRM)
    all_idx.append(BOX_TRIS + vert_off)
    # Deep-blue glass colour, brighter (LED) toward the top + taller bars
    htn = h0f[b] / maxH
    col = np.zeros((8, 4), dtype=np.float32)
    for k in range(8):
        topness = 1.0 if k >= 4 else 0.35
        glow = 0.15 + 0.85 * htn * topness
        col[k] = [0.0 + 0.15*glow, 0.25*glow + 0.05, 0.55 + 0.45*glow, 1.0]
    base_color.append(col)
    # UV: u = normalised height, v = topness (drives LED gradient texture)
    uv = np.array([[htn,0],[htn,0],[htn,0],[htn,0],
                   [htn,1],[htn,1],[htn,1],[htn,1]], dtype=np.float32)
    base_uv.append(uv)
    vert_off += 8

base_verts = np.concatenate(base_verts, axis=0)   # (NB*8, 3)
base_nrm   = np.concatenate(base_nrm,   axis=0)
base_color = np.concatenate(base_color, axis=0)
base_uv    = np.concatenate(base_uv,    axis=0)
indices    = np.concatenate(all_idx,    axis=0).ravel().astype(np.uint32)

NVERT = base_verts.shape[0]
NTRI  = len(indices) // 3
print(f"  {NVERT} verts · {NTRI} tris")

# Morph targets: only top-face Z changes per frame
print(f"Baking {TOTAL_FRAMES} morph frames …")
morph_deltas = []
for fI in range(1, TOTAL_FRAMES):
    t = (fI / TOTAL_FRAMES) * 2 * np.pi
    h = bar_heights(t).ravel()
    delta = np.zeros((NVERT, 3), dtype=np.float32)
    # top verts (local idx 4..7) of each bar get dz = h - h0
    dz = (h - h0f)
    for k in range(4, 8):
        delta[k::8, 2] = dz
    morph_deltas.append(delta)
    if fI % 10 == 0:
        print(f"  frame {fI:03d}")

# ── LED EMISSIVE GRADIENT TEXTURE ─────────────────────────────────────────────
print("Generating LED emissive gradient texture …")
tex = np.zeros((EMISSIVE_TEX, EMISSIVE_TEX, 3), dtype=np.uint8)
for py in range(EMISSIVE_TEX):
    for px in range(EMISSIVE_TEX):
        u = px / EMISSIVE_TEX          # height
        v = py / EMISSIVE_TEX          # topness
        glow = (0.2 + 0.8*u) * (0.4 + 0.6*v)
        tex[py, px] = [int(10*glow), int(120*glow), int(255*glow)]
buf = io.BytesIO()
Image.fromarray(tex, "RGB").save(buf, format="PNG")
emis_png = buf.getvalue()

# ── PACK BINARY ────────────────────────────────────────────────────────────────
print("Packing GLB buffer …")
bufs = []
def add(data):
    off = sum(len(b) for b in bufs); bufs.append(data); return off, len(data)

o_pos,l_pos = add(base_verts.tobytes())
o_nrm,l_nrm = add(base_nrm.tobytes())
o_uv ,l_uv  = add(base_uv.tobytes())
o_col,l_col = add(base_color.tobytes())
o_idx,l_idx = add(indices.tobytes())
morph_offs  = [add(d.tobytes()) for d in morph_deltas]
o_emis,l_emis = add(emis_png)
if l_emis % 4: bufs.append(bytes(4 - l_emis % 4))

times = (np.arange(TOTAL_FRAMES, dtype=np.float32) / FPS)
o_t,l_t = add(times.tobytes())
nM = len(morph_deltas)
W = np.zeros((TOTAL_FRAMES, nM), dtype=np.float32)
for fI in range(1, TOTAL_FRAMES):
    W[fI, fI-1] = 1.0
o_w,l_w = add(W.ravel().tobytes())
blob = b"".join(bufs)

# ── GLTF ──────────────────────────────────────────────────────────────────────
print("Building glTF …")
g = GLTF2()
g.asset = Asset(version="2.0", generator="VoxelWaveGlass/1.0")
g.extensionsUsed = [
    "KHR_materials_transmission","KHR_materials_volume",
    "KHR_materials_ior","KHR_materials_specular","KHR_materials_emissive_strength",
]
g.buffers.append(Buffer(byteLength=len(blob)))
g.set_binary_blob(blob)

AB, EA = 34962, 34963
def bv(o,l,t=None):
    x = BufferView(buffer=0, byteOffset=o, byteLength=l)
    if t: x.target=t
    g.bufferViews.append(x); return len(g.bufferViews)-1
bv_pos=bv(o_pos,l_pos,AB); bv_nrm=bv(o_nrm,l_nrm,AB); bv_uv=bv(o_uv,l_uv,AB)
bv_col=bv(o_col,l_col,AB); bv_idx=bv(o_idx,l_idx,EA)
bv_m=[bv(o,l,AB) for o,l in morph_offs]; bv_em=bv(o_emis,l_emis)
bv_t=bv(o_t,l_t); bv_w=bv(o_w,l_w)

F,U=5126,5125
def ac(b,c,ty,n,**k):
    g.accessors.append(Accessor(bufferView=b,componentType=c,type=ty,count=n,**k))
    return len(g.accessors)-1
a_pos=ac(bv_pos,F,"VEC3",NVERT,min=base_verts.min(0).tolist(),max=base_verts.max(0).tolist())
a_nrm=ac(bv_nrm,F,"VEC3",NVERT); a_uv=ac(bv_uv,F,"VEC2",NVERT); a_col=ac(bv_col,F,"VEC4",NVERT)
a_idx=ac(bv_idx,U,"SCALAR",len(indices),min=[0],max=[NVERT-1])
a_m=[ac(b,F,"VEC3",NVERT) for b in bv_m]
a_t=ac(bv_t,F,"SCALAR",TOTAL_FRAMES,min=[0.0],max=[float(times.max())])
a_w=ac(bv_w,F,"SCALAR",TOTAL_FRAMES*nM)

g.images.append(GLTFImage(bufferView=bv_em, mimeType="image/png"))
g.samplers.append(Sampler(magFilter=9729,minFilter=9987,wrapS=10497,wrapT=10497))
g.textures.append(Texture(source=0,sampler=0))

g.materials.append(Material(
    name="DeepBlueGlassLED",
    doubleSided=True, alphaMode="BLEND",
    pbrMetallicRoughness={
        "baseColorFactor":[0.0,0.12,0.45,0.45],
        "metallicFactor":0.0,"roughnessFactor":0.06},
    emissiveTexture={"index":0},
    emissiveFactor=[0.05,0.45,1.0],
    extensions={
        "KHR_materials_transmission":{"transmissionFactor":0.85},
        "KHR_materials_volume":{"thicknessFactor":1.2,
            "attenuationColor":[0.0,0.18,0.55],"attenuationDistance":3.0},
        "KHR_materials_ior":{"ior":1.5},
        "KHR_materials_specular":{"specularFactor":1.0,
            "specularColorFactor":[0.3,0.6,1.0]},
        "KHR_materials_emissive_strength":{"emissiveStrength":2.5},
    }))

prim = Primitive(
    attributes=pygltflib.Attributes(POSITION=a_pos,NORMAL=a_nrm,
                                    TEXCOORD_0=a_uv,COLOR_0=a_col),
    indices=a_idx, material=0,
    targets=[{"POSITION":a} for a in a_m])
g.meshes.append(Mesh(name="VoxelWave",primitives=[prim],weights=[0.0]*nM,
    extras={"type":"LED_volume_wave","tiles":TILES,"fps":FPS}))
g.nodes.append(Node(mesh=0,name="VoxelWaveNode"))
g.scenes.append(Scene(name="Scene",nodes=[0])); g.scene=0
g.animations.append(Animation(name="WaveBars",
    channels=[AnimationChannel(sampler=0,
        target=AnimationChannelTarget(node=0,path="weights"))],
    samplers=[AnimationSampler(input=a_t,output=a_w,interpolation="STEP")]))

out="voxel_wave.glb"; g.save_binary(out)
kb=pathlib.Path(out).stat().st_size//1024
print(f"\n✓  {out}  ({kb} KB)  ·  {TILES*TILES} bars · {TOTAL_FRAMES} frames")

# ── OPENPBR MATERIALX ─────────────────────────────────────────────────────────
print("Writing OpenPBR MaterialX …")
mtlx = '''<?xml version="1.0"?>
<!--
  DeepBlueGlassLED.mtlx — OpenPBR Surface material (MaterialX 1.39)
  Deep-blue glassy LED-volume material for the voxel wave GLB.
  OpenPBR is the AcademySoftwareFoundation successor to Standard Surface,
  supported by UE5 (Substrate), Arnold, RenderMan, MaterialX, USD.
-->
<materialx version="1.39" colorspace="lin_rec709">
  <open_pbr_surface name="SR_deep_blue_glass" type="surfaceshader">
    <!-- Base (deep blue) -->
    <input name="base_weight"        type="float"  value="1.0" />
    <input name="base_color"         type="color3" value="0.0 0.10 0.42" />
    <input name="base_metalness"     type="float"  value="0.0" />

    <!-- Specular / glass -->
    <input name="specular_weight"    type="float"  value="1.0" />
    <input name="specular_color"     type="color3" value="0.35 0.62 1.0" />
    <input name="specular_roughness" type="float"  value="0.06" />
    <input name="specular_ior"       type="float"  value="1.5" />

    <!-- Transmission (glassy see-through) -->
    <input name="transmission_weight"      type="float"  value="0.85" />
    <input name="transmission_color"       type="color3" value="0.0 0.18 0.55" />
    <input name="transmission_depth"       type="float"  value="3.0" />
    <input name="transmission_scatter"     type="color3" value="0.0 0.12 0.40" />

    <!-- Coat (clear glassy lacquer) -->
    <input name="coat_weight"        type="float" value="0.6" />
    <input name="coat_roughness"     type="float" value="0.02" />
    <input name="coat_ior"           type="float" value="1.5" />

    <!-- Thin-film iridescence on the glass surface -->
    <input name="thin_film_weight"   type="float" value="0.4" />
    <input name="thin_film_thickness" type="float" value="380.0" />

    <!-- Emission (LED glow, driven by height texture) -->
    <input name="emission_luminance" type="float"  value="1500.0" />
    <input name="emission_color"     type="color3" value="0.05 0.45 1.0" />

    <!-- Geometry -->
    <input name="geometry_opacity"   type="float"  value="0.92" />
  </open_pbr_surface>

  <surfacematerial name="M_DeepBlueGlassLED" type="material">
    <input name="surfaceshader" type="surfaceshader" nodename="SR_deep_blue_glass" />
  </surfacematerial>
</materialx>
'''
open("voxel_wave_openpbr.mtlx","w").write(mtlx)
print("✓  voxel_wave_openpbr.mtlx")
print("\nDone.  Drag voxel_wave.glb into Blender / UE5.")
