"""
build_unified_glass.py — THE unified final mesh (one connected mesh).

A single subdivided slab displaced into a grid of CONNECTED sub-domes (LED cells /
sub-spheres) + an animated wave on top → a displaced, animated, deep-blue glassy
reflective LED volume. One mesh. Baked to GLB (morph) + USDZ + .blend.

This is the single source mesh for web / GLB / USDZ / and the UE Nanite slab import.
Run: blender --background --python build_unified_glass.py
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector

OUTS = [r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/unified",
        r"C:/Users/joeyw/Downloads/SPIN_GlassLED"]
for o in OUTS: os.makedirs(o, exist_ok=True)
NAME="UnifiedGlassLED"
SIZE=3.0; RES=120; CELLS=18; FRAMES=24
CELL_H=0.10; WAVE_A=0.06; THICK=0.18

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=FRAMES

def glass_mat():
    m=bpy.data.materials.new("M_UnifiedGlass"); m.use_nodes=True; m.use_backface_culling=False
    b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(0.02,0.10,0.55,1)); s("Roughness",0.04); s("Metallic",0.0); s("IOR",1.5)
    s("Transmission Weight",0.85); s("Transmission",0.85); s("Coat Weight",0.7); s("Coat Roughness",0.03)
    s("Emission Color",(0.05,0.25,1.0,1)); s("Emission Strength",1.2)
    return m

def dome(u,v):
    cu=(u*CELLS)%1.0; cv=(v*CELLS)%1.0
    d=math.hypot(cu-0.5,cv-0.5)*2.0
    return math.sqrt(max(0.0,1.0-d*d)) if d<1.0 else 0.0

def wave(u,v,t):
    edge=math.sin(math.pi*u)*math.sin(math.pi*v)
    return edge*(math.sin(u*7+t*2)*math.cos(v*6-t*1.6)+0.5*math.sin((u+v)*9-t*2.3))

def height(u,v,t):
    return CELL_H*dome(u,v) + WAVE_A*wave(u,v,t)

def build():
    me=bpy.data.meshes.new(NAME); ob=bpy.data.objects.new(NAME,me)
    bpy.context.collection.objects.link(ob)
    bm=bmesh.new(); vt=[[None]*RES for _ in range(RES)]
    for j in range(RES):
        for i in range(RES):
            x=-SIZE/2+SIZE*i/(RES-1); y=-SIZE/2+SIZE*j/(RES-1)
            vt[j][i]=bm.verts.new((x,y,0))
    bm.verts.ensure_lookup_table()
    for j in range(RES-1):
        for i in range(RES-1):
            bm.faces.new((vt[j][i],vt[j][i+1],vt[j+1][i+1],vt[j+1][i]))
    uv=bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops:
            c=l.vert.co; l[uv].uv=((c.x+SIZE/2)/SIZE,(c.y+SIZE/2)/SIZE)
    bm.to_mesh(me); bm.free()
    me.materials.append(glass_mat())
    # solidify into a slab (thickness) so it's a volume, not a sheet
    sm=ob.modifiers.new("Solidify","SOLIDIFY"); sm.thickness=THICK; sm.offset=0
    base=[v.co.copy() for v in me.vertices]
    ob.shape_key_add(name="Basis",from_mix=False)
    for f in range(FRAMES):
        t=f/FRAMES*6.2831853; sk=ob.shape_key_add(name=f"f{f:03d}",from_mix=False)
        for idx,v in enumerate(me.vertices):
            c=base[idx]; u=(c.x+SIZE/2)/SIZE; w=(c.y+SIZE/2)/SIZE
            sk.data[idx].co=c+Vector((0,0,height(u,w,t)))
    kbs=[k for k in me.shape_keys.key_blocks if k.name!="Basis"]
    for f in range(FRAMES):
        bpy.context.scene.frame_set(f+1)
        for k,kb in enumerate(kbs):
            kb.value=1.0 if k==f else 0.0; kb.keyframe_insert("value",frame=f+1)
    bpy.context.scene.frame_set(1)
    return ob

def export(ob):
    bpy.ops.object.select_all(action='SELECT'); res={}
    for OUT in OUTS:
        base=os.path.join(OUT,NAME)
        try:
            bpy.ops.export_scene.gltf(filepath=base+".glb",export_format='GLB',export_morph=True,
                export_animations=True,export_morph_animation=True,export_materials='EXPORT')
            res[OUT+"/glb"]=os.path.getsize(base+".glb")
        except Exception as e: res[OUT+"/glb"]=f"ERR {e}"
        try:
            bpy.ops.wm.usd_export(filepath=base+".usdz",export_animation=True,export_materials=True)
            res[OUT+"/usdz"]=os.path.getsize(base+".usdz")
        except Exception as e: res[OUT+"/usdz"]=f"ERR {e}"
    try:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUTS[0],NAME+".blend"))
    except Exception: pass
    print("[UNIFIED]",res)

reset(); export(build()); print("[DONE]")
