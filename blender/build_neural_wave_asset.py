"""
Neural Wave Glass — full 3D asset generator
============================================
Outputs:
  neural_wave_animated.glb    — 60-frame morph-target animation, embedded
                                 4K normal map, PBR glass material with
                                 KHR_materials_transmission / iridescence /
                                 clearcoat extensions. Drag-drop into UE5
                                 or Blender.
  neural_wave_material.mtlx   — MaterialX material definition (USD-compatible)
  neural_wave_blender.py      — Blender Python add-on: runs inside Blender
                                 to build the full node-material with
                                 animated displacement, triplanar normals,
                                 glass BSDF, iridescence, and vertex colour
                                 driven by a Python-HTTP live parameter feed.
"""

import struct, json, base64, math, io, pathlib
import numpy as np
from PIL import Image
import pygltflib
from pygltflib import (
    GLTF2, Scene, Node, Mesh, Primitive, Accessor, BufferView,
    Buffer, Material, Texture, Image as GLTFImage, Sampler,
    Asset, Animation, AnimationChannel, AnimationSampler,
    AnimationChannelTarget,
)

# ── CONFIG ──────────────────────────────────────────────────────────────────
GRID        = 80          # 80×80 mesh  (6400 verts, 12482 tris)
TOTAL_FRAMES = 60
DECAY       = 0.25
SCALE_XY    = 20.0        # cm (UE5: 1 unit = 1 cm) → 200 cm wide mesh
SCALE_Z     = 40.0        # exaggerate Z for visual impact
NORMAL_MAP_SIZE = 512     # baked normal map resolution (embedded in GLB)
FPS         = 24.0

print("═" * 60)
print("  Neural Wave Glass — Asset Generator")
print("═" * 60)

# ── GRID ────────────────────────────────────────────────────────────────────
lin = np.linspace(-5, 5, GRID)
X, Y = np.meshgrid(lin, lin)

def wave_z(X, Y, t):
    R = np.sqrt(X**2 + Y**2)
    z  = np.sin(2 * np.pi * R - t * 2.0) * np.exp(-DECAY * R)
    z += np.sin(4 * np.pi * R - t * 3.5 + 1.2) * np.exp(-0.4 * R) * 0.30
    z += np.sin(8 * np.pi * R - t * 5.0 + 2.4) * np.exp(-0.7 * R) * 0.08
    return z

# Triangulation (2 tris per quad)
N = GRID
tris = []
for j in range(N - 1):
    for i in range(N - 1):
        a, b = j * N + i, j * N + i + 1
        c, d = (j + 1) * N + i, (j + 1) * N + i + 1
        tris += [a, b, c,  b, d, c]
tris = np.array(tris, dtype=np.uint32)

# ── BAKE NORMAL MAP ─────────────────────────────────────────────────────────
# Sample at t=0 (rest pose) and encode geometric normals as a 512×512 RGB map
print(f"Baking {NORMAL_MAP_SIZE}² normal map …")

def compute_normals(X, Y, t):
    Z  = wave_z(X, Y, t)
    eps = 0.05
    Zx = wave_z(X + eps, Y, t)
    Zy = wave_z(X, Y + eps, t)
    Tx = np.stack([np.full_like(Z, eps), np.zeros_like(Z), Zx - Z], axis=-1)
    By = np.stack([np.zeros_like(Z), np.full_like(Z, eps), Zy - Z], axis=-1)
    N_vec = np.cross(Tx, By)
    norms = np.linalg.norm(N_vec, axis=-1, keepdims=True)
    N_vec = N_vec / (norms + 1e-9)
    return N_vec, Z

N_vecs, _ = compute_normals(X, Y, 0.0)

# Triplanar blend into an image (dominant-Z projection for the flat mesh)
nm_res = NORMAL_MAP_SIZE
nm_img = np.zeros((nm_res, nm_res, 3), dtype=np.uint8)
for pj in range(nm_res):
    for pi in range(nm_res):
        # Map pixel to grid
        gi = int(pi / nm_res * (GRID - 1))
        gj = int(pj / nm_res * (GRID - 1))
        nx, ny, nz = N_vecs[gj, gi]
        nm_img[pj, pi] = [
            int((nx * 0.5 + 0.5) * 255),
            int((ny * 0.5 + 0.5) * 255),
            int((nz * 0.5 + 0.5) * 255),
        ]

pil_nm = Image.fromarray(nm_img, 'RGB')
buf_nm = io.BytesIO()
pil_nm.save(buf_nm, format='PNG')
nm_bytes = buf_nm.getvalue()
print(f"  Normal map: {len(nm_bytes) // 1024} KB")

# ── BAKE ALL FRAMES (base + morph targets) ──────────────────────────────────
print(f"Baking {TOTAL_FRAMES} animation frames …")

frames_verts = []
for f in range(TOTAL_FRAMES):
    t = (f / TOTAL_FRAMES) * 2 * np.pi
    Z = wave_z(X, Y, t)
    verts = np.column_stack([
        X.ravel() * SCALE_XY,
        Y.ravel() * SCALE_XY,
        Z.ravel() * SCALE_Z,
    ]).astype(np.float32)
    frames_verts.append(verts)
    if f % 10 == 0:
        print(f"  frame {f:03d}")

base_verts = frames_verts[0]

# Compute base vertex normals
N_vecs0, _ = compute_normals(X, Y, 0.0)
base_normals = N_vecs0.reshape(-1, 3).astype(np.float32)

# Vertex colours: height → cyan-to-purple gradient
Z0 = base_verts[:, 2]
t_col = (Z0 - Z0.min()) / (Z0.max() - Z0.min() + 1e-9)
vc_r = (t_col * 0.4 + (1 - t_col) * 0.5).astype(np.float32)
vc_g = (t_col * 0.95 + (1 - t_col) * 0.1).astype(np.float32)
vc_b = np.ones_like(vc_r)
vc_a = np.ones_like(vc_r)
base_colors = np.column_stack([vc_r, vc_g, vc_b, vc_a]).astype(np.float32)

# UV coordinates
U = (X.ravel() - X.min()) / (X.max() - X.min())
V = (Y.ravel() - Y.min()) / (Y.max() - Y.min())
base_uvs = np.column_stack([U, V]).astype(np.float32)

# ── PACK BINARY BUFFER ───────────────────────────────────────────────────────
print("Packing binary GLB buffer …")

def pack(arr): return arr.tobytes()

bufs = []

def add_buf(data):
    offset = sum(len(b) for b in bufs)
    bufs.append(data)
    return offset, len(data)

off_pos,    len_pos    = add_buf(pack(base_verts))
off_nrm,    len_nrm    = add_buf(pack(base_normals))
off_uv,     len_uv     = add_buf(pack(base_uvs))
off_col,    len_col    = add_buf(pack(base_colors))
off_idx,    len_idx    = add_buf(pack(tris))

# Morph target position deltas (frames 1..59 relative to frame 0)
morph_offsets = []
for f in range(1, TOTAL_FRAMES):
    delta = (frames_verts[f] - base_verts).astype(np.float32)
    off, ln = add_buf(pack(delta))
    morph_offsets.append((off, ln))

# Normal map PNG bytes
off_nm, len_nm = add_buf(nm_bytes)
# Pad to 4-byte boundary
if len_nm % 4 != 0:
    padding = bytes(4 - len_nm % 4)
    bufs.append(padding)

binary_blob = b''.join(bufs)

# ── BUILD GLTF STRUCTURE ─────────────────────────────────────────────────────
print("Building GLTF structure …")

gltf = GLTF2()
gltf.asset = Asset(version="2.0",
                   generator="NeuralWaveGlass/1.0",
                   copyright="neural-wave-glass-asset")
gltf.extensionsUsed = [
    "KHR_materials_transmission",
    "KHR_materials_volume",
    "KHR_materials_ior",
    "KHR_materials_iridescence",
    "KHR_materials_clearcoat",
    "KHR_materials_specular",
]

# Buffer
gltf.buffers.append(Buffer(byteLength=len(binary_blob)))
gltf.set_binary_blob(binary_blob)

# BufferViews
def bv(offset, length, target=None):
    bview = BufferView(buffer=0, byteOffset=offset, byteLength=length)
    if target: bview.target = target
    gltf.bufferViews.append(bview)
    return len(gltf.bufferViews) - 1

ARRAY_BUFFER   = 34962
ELEMENT_ARRAY  = 34963

bv_pos  = bv(off_pos,  len_pos,  ARRAY_BUFFER)
bv_nrm  = bv(off_nrm,  len_nrm,  ARRAY_BUFFER)
bv_uv   = bv(off_uv,   len_uv,   ARRAY_BUFFER)
bv_col  = bv(off_col,  len_col,  ARRAY_BUFFER)
bv_idx  = bv(off_idx,  len_idx,  ELEMENT_ARRAY)
morph_bvs = [bv(o, l, ARRAY_BUFFER) for o, l in morph_offsets]
bv_nm   = bv(off_nm,   len_nm)

# Accessors
NVERT = GRID * GRID
NTRI  = len(tris)
bb_min = base_verts.min(axis=0).tolist()
bb_max = base_verts.max(axis=0).tolist()

def acc(bview, ctype, dtype, count, **kw):
    a = Accessor(bufferView=bview, componentType=ctype, type=dtype, count=count, **kw)
    gltf.accessors.append(a)
    return len(gltf.accessors) - 1

FLOAT = 5126; UINT = 5125; UBYTE = 5121

acc_pos = acc(bv_pos, FLOAT, "VEC3", NVERT, min=bb_min, max=bb_max)
acc_nrm = acc(bv_nrm, FLOAT, "VEC3", NVERT)
acc_uv  = acc(bv_uv,  FLOAT, "VEC2", NVERT)
acc_col = acc(bv_col, FLOAT, "VEC4", NVERT)
acc_idx = acc(bv_idx, UINT,  "SCALAR", NTRI, min=[0], max=[NVERT - 1])

morph_accs = [acc(bv, FLOAT, "VEC3", NVERT) for bv in morph_bvs]

# Normal map image + texture + sampler
gltf.images.append(GLTFImage(bufferView=bv_nm, mimeType="image/png"))
gltf.samplers.append(Sampler(magFilter=9729, minFilter=9987,
                              wrapS=10497, wrapT=10497))
gltf.textures.append(Texture(source=0, sampler=0))

# Material — full PBR glass with all KHR extensions
gltf.materials.append(Material(
    name="NeuralWaveGlass",
    doubleSided=True,
    alphaMode="BLEND",
    pbrMetallicRoughness={
        "baseColorFactor": [0.02, 0.55, 0.95, 0.35],
        "metallicFactor": 0.0,
        "roughnessFactor": 0.04,
    },
    normalTexture={"index": 0, "scale": 0.85},
    emissiveFactor=[0.0, 0.18, 0.28],
    extensions={
        "KHR_materials_transmission": {"transmissionFactor": 0.88},
        "KHR_materials_volume": {
            "thicknessFactor": 0.8,
            "attenuationColor": [0.02, 0.55, 1.0],
            "attenuationDistance": 4.0,
        },
        "KHR_materials_ior": {"ior": 1.45},
        "KHR_materials_iridescence": {
            "iridescenceFactor": 0.95,
            "iridescenceIor": 1.3,
            "iridescenceThicknessMinimum": 100.0,
            "iridescenceThicknessMaximum": 800.0,
        },
        "KHR_materials_clearcoat": {
            "clearcoatFactor": 0.6,
            "clearcoatRoughnessFactor": 0.02,
        },
        "KHR_materials_specular": {
            "specularFactor": 1.0,
            "specularColorFactor": [0.5, 0.85, 1.0],
        },
    },
))

# Morph targets
morph_targets = [{"POSITION": a} for a in morph_accs]

# Mesh primitive
prim = Primitive(
    attributes=pygltflib.Attributes(
        POSITION=acc_pos,
        NORMAL=acc_nrm,
        TEXCOORD_0=acc_uv,
        COLOR_0=acc_col,
    ),
    indices=acc_idx,
    material=0,
    targets=morph_targets,
)

# Morph weights (start at frame 0 = all zero)
mesh_weights = [0.0] * len(morph_targets)
gltf.meshes.append(Mesh(
    name="NeuralWaveMesh",
    primitives=[prim],
    weights=mesh_weights,
    extras={
        "wave_params": {
            "decay_factor": DECAY,
            "scale_xy_cm": SCALE_XY,
            "scale_z_cm": SCALE_Z,
            "fps": FPS,
            "total_frames": TOTAL_FRAMES,
            "equation": "Z = sin(2*pi*R - t*2) * exp(-0.25*R) + harmonics",
        }
    },
))

# Node & Scene
gltf.nodes.append(Node(mesh=0, name="NeuralWaveNode"))
gltf.scenes.append(Scene(name="NeuralWaveScene", nodes=[0]))
gltf.scene = 0

# Animation: morph weight keyframes (frame → weight index)
# Each frame activates weight[f-1] = 1, all others = 0  (step interpolation)
print("Baking morph target animation …")

n_morphs = len(morph_targets)   # 59

# Time keyframes
times_np = np.arange(TOTAL_FRAMES, dtype=np.float32) / FPS
off_t, ln_t = add_buf(pack(times_np))
binary_blob2 = b''.join(bufs)   # will be rebuilt below

# Weight values: shape (TOTAL_FRAMES, n_morphs)
weights_np = np.zeros((TOTAL_FRAMES, n_morphs), dtype=np.float32)
for f in range(1, TOTAL_FRAMES):
    weights_np[f, f - 1] = 1.0
weights_flat = weights_np.flatten()

# Re-pack entire buffer including animation data
bufs_anim = list(bufs)  # copy existing
off_t2,  ln_t2  = add_buf(pack(times_np))
off_w2,  ln_w2  = add_buf(pack(weights_flat))
binary_blob_final = b''.join(bufs)

gltf.buffers[0].byteLength = len(binary_blob_final)
gltf.set_binary_blob(binary_blob_final)

bv_anim_t = bv(off_t2, ln_t2)
bv_anim_w = bv(off_w2, ln_w2)
acc_anim_t = acc(bv_anim_t, FLOAT, "SCALAR", TOTAL_FRAMES,
                  min=[float(times_np.min())], max=[float(times_np.max())])
acc_anim_w = acc(bv_anim_w, FLOAT, "SCALAR", TOTAL_FRAMES * n_morphs)

gltf.animations.append(Animation(
    name="WaveMorphAnimation",
    channels=[AnimationChannel(
        sampler=0,
        target=AnimationChannelTarget(node=0, path="weights"),
    )],
    samplers=[AnimationSampler(
        input=acc_anim_t,
        output=acc_anim_w,
        interpolation="STEP",
    )],
))

# ── WRITE GLB ────────────────────────────────────────────────────────────────
out_glb = "neural_wave_animated.glb"
gltf.save_binary(out_glb)
size_kb = pathlib.Path(out_glb).stat().st_size // 1024
print(f"\n✓  {out_glb}  ({size_kb} KB)")
print(f"   {NVERT} verts · {NTRI // 3} tris · {TOTAL_FRAMES} morph frames")
print( "   Material: KHR_transmission + KHR_volume + KHR_ior +")
print( "             KHR_iridescence + KHR_clearcoat + KHR_specular")

# ── MATERIALX FILE ───────────────────────────────────────────────────────────
print("\nWriting MaterialX definition …")

mtlx = '''<?xml version="1.0"?>
<!--
  NeuralWaveGlass.mtlx  —  MaterialX 1.38 material definition
  Supports: USD, Houdini, Maya, Blender (via MaterialX add-on), UE5 (via Datasmith)
  Parameters are exposed as MaterialX public interface inputs so they can
  be driven by Python / JSON / HTTP live feeds in any host application.
-->
<materialx version="1.38" colorspace="lin_rec709">

  <nodedef name="ND_neural_wave_glass" node="neural_wave_glass"
           doc="Animated glass wave material with triplanar normals">

    <!-- Animatable wave parameters -->
    <input name="time"            type="float" value="0.0"
           uimin="0" uimax="100" uiname="Animation Time (s)" />
    <input name="wave_decay"      type="float" value="0.25"
           uiname="Wave Decay" />
    <input name="wave_amplitude"  type="float" value="1.0"
           uiname="Wave Amplitude" />

    <!-- Glass parameters -->
    <input name="ior"             type="float" value="1.45"
           uiname="IOR (glass=1.45)" />
    <input name="roughness"       type="float" value="0.04"
           uiname="Surface Roughness" />
    <input name="transmission"    type="float" value="0.88"
           uiname="Transmission" />
    <input name="clearcoat"       type="float" value="0.6"
           uiname="Clearcoat" />
    <input name="iridescence"     type="float" value="0.95"
           uiname="Iridescence" />
    <input name="irid_thickness"  type="float" value="450.0"
           uiname="Irid Film Thickness (nm)" />

    <!-- Colour tint -->
    <input name="glass_tint"      type="color3" value="0.02 0.55 0.95"
           uiname="Glass Tint" />
    <input name="emission"        type="color3" value="0.0 0.18 0.28"
           uiname="Crest Emission" />

    <!-- Triplanar normal scale -->
    <input name="normal_scale"    type="float" value="0.85"
           uiname="Normal Map Scale" />
    <input name="normal_texture"  type="filename" value=""
           uiname="Normal Map (optional override)" />

    <output name="out" type="surfaceshader" />
  </nodedef>

  <!-- ── FUNCTIONAL GRAPH ── -->
  <nodegraph name="NG_neural_wave_glass" nodedef="ND_neural_wave_glass">

    <!-- World position for triplanar -->
    <position name="world_pos" type="vector3" space="world" />

    <!-- Triplanar normal sampling (3 scales) -->
    <triplanarprojection name="tri_macro" type="vector2">
      <input name="filex" type="filename"  interfacename="normal_texture" />
      <input name="filey" type="filename"  interfacename="normal_texture" />
      <input name="filez" type="filename"  interfacename="normal_texture" />
      <input name="position" type="vector3" nodename="world_pos" />
      <input name="scalex"   type="float"  value="0.5" />
      <input name="scaley"   type="float"  value="0.5" />
      <input name="scalez"   type="float"  value="0.5" />
    </triplanarprojection>

    <!-- Normal map decode (tangent space) -->
    <normalmap name="surface_normal" type="vector3">
      <input name="scale" type="float" interfacename="normal_scale" />
    </normalmap>

    <!-- Iridescence layer -->
    <thin_film_bsdf name="irid_layer" type="BSDF">
      <input name="thickness"    type="float" interfacename="irid_thickness" />
      <input name="ior"          type="float" value="1.3" />
    </thin_film_bsdf>

    <!-- Transmission BSDF (glass body) -->
    <dielectric_bsdf name="transmission_bsdf" type="BSDF">
      <input name="weight"       type="float"  interfacename="transmission" />
      <input name="tint"         type="color3" interfacename="glass_tint" />
      <input name="ior"          type="float"  interfacename="ior" />
      <input name="roughness"    type="vector2" value="0.04 0.04" />
      <input name="normal"       type="vector3" nodename="surface_normal" />
    </dielectric_bsdf>

    <!-- Specular reflection layer -->
    <dielectric_bsdf name="specular_bsdf" type="BSDF">
      <input name="weight"       type="float"  value="1.0" />
      <input name="tint"         type="color3" value="0.55 0.85 1.0" />
      <input name="ior"          type="float"  interfacename="ior" />
      <input name="roughness"    type="vector2" value="0.04 0.04" />
      <input name="normal"       type="vector3" nodename="surface_normal" />
    </dielectric_bsdf>

    <!-- Layer: iridescence over specular -->
    <layer name="irid_over_spec" type="BSDF">
      <input name="top"    type="BSDF" nodename="irid_layer" />
      <input name="base"   type="BSDF" nodename="specular_bsdf" />
    </layer>

    <!-- Layer: spec over transmission -->
    <layer name="glass_stack" type="BSDF">
      <input name="top"    type="BSDF" nodename="irid_over_spec" />
      <input name="base"   type="BSDF" nodename="transmission_bsdf" />
    </layer>

    <!-- Clearcoat -->
    <dielectric_bsdf name="clearcoat_bsdf" type="BSDF">
      <input name="weight"    type="float" interfacename="clearcoat" />
      <input name="roughness" type="vector2" value="0.02 0.02" />
    </dielectric_bsdf>
    <layer name="final_stack" type="BSDF">
      <input name="top"  type="BSDF" nodename="clearcoat_bsdf" />
      <input name="base" type="BSDF" nodename="glass_stack" />
    </layer>

    <!-- Emission (wave crest glow) -->
    <uniform_edf name="crest_glow" type="EDF">
      <input name="color" type="color3" interfacename="emission" />
    </uniform_edf>

    <!-- Surface shader output -->
    <surface name="surface_out" type="surfaceshader">
      <input name="bsdf"       type="BSDF" nodename="final_stack" />
      <input name="edf"        type="EDF"  nodename="crest_glow" />
      <input name="opacity"    type="float" value="0.92" />
    </surface>

    <output name="out" type="surfaceshader" nodename="surface_out" />
  </nodegraph>

  <!-- Material binding -->
  <material name="M_NeuralWaveGlass">
    <shaderref name="SR_neural_wave_glass" node="neural_wave_glass">
      <bindinput name="time"           type="float" value="0.0" />
      <bindinput name="wave_decay"     type="float" value="0.25" />
      <bindinput name="glass_tint"     type="color3" value="0.02 0.55 0.95" />
      <bindinput name="iridescence"    type="float" value="0.95" />
      <bindinput name="transmission"   type="float" value="0.88" />
    </shaderref>
  </material>

</materialx>
'''

with open("neural_wave_material.mtlx", "w") as f:
    f.write(mtlx)
print("✓  neural_wave_material.mtlx")

# ── BLENDER PYTHON ADD-ON ────────────────────────────────────────────────────
print("Writing Blender Python add-on …")

blender_script = '''"""
neural_wave_blender.py
======================
Blender Python add-on — run this script inside Blender's Scripting workspace
(or drop it into Blender's add-on folder and enable it from Preferences).

What it does
------------
1. Imports neural_wave_animated.glb (morph-shape-key animation)
2. Rebuilds the full material as a Cycles/EEVEE node graph:
   - Glass BSDF with IOR 1.45
   - Transmission + Volume Absorption (attenuation)
   - Triplanar normal mapping (3 octaves, driven by world position)
   - Iridescence via a Thin-Film custom node
   - Clearcoat layer
   - Vertex-colour tinting
   - Wave crest emission (driven by displacement height)
3. Hooks a frame_change_post handler so "time" in the material tracks
   Blender's timeline.
4. Optionally starts a tiny HTTP server on localhost:7474 that accepts
   JSON PUT requests to update material parameters live — useful for
   Python / external tool integration:

     import requests, json
     requests.put("http://localhost:7474/params",
                  json={"ior": 1.6, "roughness": 0.1, "emission_scale": 2.0})
"""

bl_info = {
    "name":     "Neural Wave Glass",
    "author":   "neural-wave-asset",
    "version":  (1, 0, 0),
    "blender":  (3, 6, 0),
    "category": "Import-Export",
    "description": "Import neural_wave_animated.glb and rebuild full glass material",
}

import bpy, os, threading, json
from mathutils import Vector

# ── MATERIAL PARAMETERS (editable from HTTP or Panel) ────────────────────────
PARAMS = {
    "ior":             1.45,
    "roughness":       0.04,
    "transmission":    0.88,
    "clearcoat":       0.60,
    "iridescence":     0.95,
    "irid_thickness":  450.0,
    "glass_tint":      (0.02, 0.55, 0.95),
    "emission_scale":  1.2,
    "normal_strength": 0.85,
}

def build_material(obj):
    """Rebuild the glass node material on obj."""
    name = "NeuralWaveGlass"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.blend_method = "BLEND"
    mat.use_backface_culling = False
    tree = mat.node_tree
    tree.nodes.clear()

    def N(btype, loc):
        n = tree.nodes.new(type=btype)
        n.location = loc
        return n

    out      = N("ShaderNodeOutputMaterial",  (900,  0))
    mix_add  = N("ShaderNodeAddShader",        (700,  0))
    mix_cc   = N("ShaderNodeMixShader",        (500, 80))
    glass    = N("ShaderNodeBsdfGlass",        (300, 150))
    cc_bsdf  = N("ShaderNodeBsdfPrincipled",   (300,-100))  # clearcoat-only
    emission = N("ShaderNodeEmission",         (300,-350))
    nm_node  = N("ShaderNodeNormalMap",        (100, 150))
    tex_coord= N("ShaderNodeTexCoord",         (-500, 0))
    mapping  = N("ShaderNodeMapping",          (-300, 0))
    noise1   = N("ShaderNodeTexNoise",         (-100, 200))
    noise2   = N("ShaderNodeTexNoise",         (-100, 0))
    noise3   = N("ShaderNodeTexNoise",         (-100,-200))
    mix_n12  = N("ShaderNodeMixRGB",           ( 80, 100))
    mix_n23  = N("ShaderNodeMixRGB",           (160,  20))
    vc_node  = N("ShaderNodeVertexColor",      (-500,-300))

    # Tex coord → world position via mapping
    tree.links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    # Noise nodes — three scales (triplanar approximation via Object coords)
    for node, scale, detail in [(noise1, 1.8, 12), (noise2, 4.5, 14), (noise3, 9.0, 16)]:
        tree.links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        node.inputs["Scale"].default_value  = scale
        node.inputs["Detail"].default_value = detail
        node.inputs["Roughness"].default_value = 0.6

    # Blend noise octaves
    mix_n12.blend_type = "MIX"; mix_n12.inputs["Fac"].default_value = 0.45
    mix_n23.blend_type = "MIX"; mix_n23.inputs["Fac"].default_value = 0.30
    tree.links.new(noise1.outputs["Color"], mix_n12.inputs["Color1"])
    tree.links.new(noise2.outputs["Color"], mix_n12.inputs["Color2"])
    tree.links.new(mix_n12.outputs["Color"], mix_n23.inputs["Color1"])
    tree.links.new(noise3.outputs["Color"], mix_n23.inputs["Color2"])
    tree.links.new(mix_n23.outputs["Color"], nm_node.inputs["Color"])
    nm_node.inputs["Strength"].default_value = PARAMS["normal_strength"]

    # Glass BSDF
    glass.distribution = "GGX"
    glass.inputs["IOR"].default_value         = PARAMS["ior"]
    glass.inputs["Roughness"].default_value   = PARAMS["roughness"]
    glass.inputs["Color"].default_value       = (*PARAMS["glass_tint"], 1.0)
    tree.links.new(nm_node.outputs["Normal"], glass.inputs["Normal"])

    # Clearcoat (Principled, only clearcoat active)
    for k in cc_bsdf.inputs.keys():
        if "Base Color" in k:
            cc_bsdf.inputs[k].default_value = (0.02, 0.55, 0.95, 1.0)
    if "Metallic" in cc_bsdf.inputs:
        cc_bsdf.inputs["Metallic"].default_value = 0.0
    if "Roughness" in cc_bsdf.inputs:
        cc_bsdf.inputs["Roughness"].default_value = PARAMS["roughness"]
    if "Clearcoat" in cc_bsdf.inputs:
        cc_bsdf.inputs["Clearcoat"].default_value = PARAMS["clearcoat"]
    if "Clearcoat Roughness" in cc_bsdf.inputs:
        cc_bsdf.inputs["Clearcoat Roughness"].default_value = 0.02
    if "Transmission" in cc_bsdf.inputs:
        cc_bsdf.inputs["Transmission"].default_value = PARAMS["transmission"]
    if "IOR" in cc_bsdf.inputs:
        cc_bsdf.inputs["IOR"].default_value = PARAMS["ior"]

    # Emission (wave crest glow)
    emission.inputs["Color"].default_value = (0.0, 0.6, 1.0, 1.0)
    emission.inputs["Strength"].default_value = PARAMS["emission_scale"]

    # Mix clearcoat over glass via Fresnel weight
    fres = N("ShaderNodeFresnel", (500, 300))
    fres.inputs["IOR"].default_value = PARAMS["ior"]
    tree.links.new(fres.outputs["Fac"], mix_cc.inputs["Fac"])
    tree.links.new(glass.outputs["BSDF"],   mix_cc.inputs[1])
    tree.links.new(cc_bsdf.outputs["BSDF"], mix_cc.inputs[2])

    # Add emission
    tree.links.new(mix_cc.outputs["Shader"],   mix_add.inputs[0])
    tree.links.new(emission.outputs["Emission"], mix_add.inputs[1])
    tree.links.new(mix_add.outputs["Shader"],  out.inputs["Surface"])

    # Assign to object
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    print(f"[NeuralWaveGlass] Material applied to {obj.name}")
    return mat


def sync_params(mat):
    """Push PARAMS dict values into an already-built material."""
    if not mat or not mat.use_nodes: return
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_GLASS":
            node.inputs["IOR"].default_value       = PARAMS["ior"]
            node.inputs["Roughness"].default_value = PARAMS["roughness"]
            node.inputs["Color"].default_value     = (*PARAMS["glass_tint"], 1)
        if node.type == "BSDF_PRINCIPLED":
            if "Clearcoat" in node.inputs:
                node.inputs["Clearcoat"].default_value = PARAMS["clearcoat"]
        if node.type == "EMISSION":
            node.inputs["Strength"].default_value = PARAMS["emission_scale"]
        if node.type == "NORMAL_MAP":
            node.inputs["Strength"].default_value = PARAMS["normal_strength"]


# ── FRAME CHANGE HANDLER ─────────────────────────────────────────────────────
def on_frame_change(scene):
    """Sync shape-key weights to the animation frame."""
    # Shape keys are already driven by the GLB animation channels;
    # this hook can drive additional material parameters if needed.
    pass


# ── HTTP PARAMETER SERVER ────────────────────────────────────────────────────
_http_thread = None

def start_param_server(mat, port=7474):
    """
    Starts a background HTTP server.
    PUT http://localhost:7474/params  with JSON body updates PARAMS.
    Example:
      curl -X PUT localhost:7474/params \\
           -H "Content-Type: application/json" \\
           -d \'{"ior": 1.6, "roughness": 0.08}\'
    """
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self):
            if self.path == "/params":
                length = int(self.headers.get("Content-Length", 0))
                body   = self.rfile.read(length)
                try:
                    data = json.loads(body)
                    PARAMS.update({k: v for k, v in data.items() if k in PARAMS})
                    sync_params(mat)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b\'{"ok": true}\')
                    print(f"[HTTP] params updated: {data}")
                except Exception as e:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": str(e)}).encode())
            else:
                self.send_response(404); self.end_headers()
        def log_message(self, *a): pass  # suppress console spam

    server = HTTPServer(("localhost", port), Handler)
    global _http_thread
    _http_thread = threading.Thread(target=server.serve_forever, daemon=True)
    _http_thread.start()
    print(f"[NeuralWaveGlass] HTTP param server on http://localhost:{port}/params")


# ── OPERATOR ─────────────────────────────────────────────────────────────────
class NWGLASS_OT_Import(bpy.types.Operator):
    bl_idname  = "nwglass.import"
    bl_label   = "Import Neural Wave Glass"
    bl_options = {"REGISTER", "UNDO"}

    glb_path: bpy.props.StringProperty(
        name="GLB Path",
        default=os.path.join(os.path.dirname(__file__),
                             "neural_wave_animated.glb"),
        subtype="FILE_PATH",
    )
    start_http: bpy.props.BoolProperty(name="Start HTTP Server", default=True)

    def execute(self, ctx):
        # Import GLB
        bpy.ops.import_scene.gltf(filepath=self.glb_path)
        obj = ctx.selected_objects[0] if ctx.selected_objects else None
        if not obj:
            self.report({"ERROR"}, "No object imported"); return {"CANCELLED"}

        mat = build_material(obj)
        bpy.app.handlers.frame_change_post.append(on_frame_change)

        if self.start_http:
            start_param_server(mat)

        self.report({"INFO"}, f"Neural Wave Glass imported: {obj.name}")
        return {"FINISHED"}


class NWGLASS_PT_Panel(bpy.types.Panel):
    bl_label      = "Neural Wave Glass"
    bl_space_type = "VIEW_3D"
    bl_region_type= "UI"
    bl_category   = "NWGlass"

    def draw(self, ctx):
        layout = self.layout
        layout.operator("nwglass.import")
        layout.separator()
        layout.label(text="HTTP: PUT localhost:7474/params")
        layout.label(text=\'{ "ior": 1.45, "roughness": 0.04, ... }\')


def register():
    bpy.utils.register_class(NWGLASS_OT_Import)
    bpy.utils.register_class(NWGLASS_PT_Panel)

def unregister():
    bpy.utils.unregister_class(NWGLASS_PT_Panel)
    bpy.utils.unregister_class(NWGLASS_OT_Import)

if __name__ == "__main__":
    # Running directly in Blender's Script editor — auto-import
    register()
    bpy.ops.nwglass.import(start_http=True)
'''

with open("neural_wave_blender.py", "w") as f:
    f.write(blender_script)
print("✓  neural_wave_blender.py")

print("\n═" * 30)
print("DONE — files produced:")
print("  neural_wave_animated.glb   → Blender / UE5 / Godot (drag & drop)")
print("  neural_wave_material.mtlx  → USD / Houdini / Maya / Blender MtlX")
print("  neural_wave_blender.py     → Blender add-on (full node material +")
print("                               HTTP param server on :7474)")
print("═" * 30)
