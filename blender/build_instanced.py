"""
build_instanced.py — bake an INSTANCED glass LED volume from config/scene.json.

Builds ONE animated glass slab (soft-body morph) and instances it on a 3D grid as
LINKED duplicates (shared mesh data) so the exporters emit real instancing:
    GLB  : EXT_mesh_gpu_instancing      (glTF GPU instancing)
    USD  : instanceable refs / PointInstancer-style
    USDZ : same, zipped for iOS AR
    ABC  : flattened Alembic cache (master)

Per-instance PHASE/COLOR variation is a runtime feature (web/UE); baked instances
share one animation by design — that is what makes instancing cheap.

Run:  blender --background --python build_instanced.py
"""
import bpy, bmesh, json, os, math
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG  = json.load(open(os.path.join(ROOT, "config", "scene.json")))
OUT  = os.path.join(ROOT, "assets", "instanced"); os.makedirs(OUT, exist_ok=True)

I, Uu, M, G, L = CFG["instancing"], CFG["unit"], CFG["motion"], CFG["glass"], CFG["led"]
FRAMES = CFG.get("frames", 48)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.frame_start = 1; bpy.context.scene.frame_end = FRAMES

def glass_mat():
    m = bpy.data.materials.new("M_GlassLED"); m.use_nodes = True; m.use_backface_culling = False
    b = m.node_tree.nodes.get("Principled BSDF")
    col = G["color"].lstrip("#"); r,g,bl = (int(col[i:i+2],16)/255 for i in (0,2,4))
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value = v
    s("Base Color",(r,g,bl,1)); s("Roughness",G["roughness"]); s("Metallic",0.0); s("IOR",G["ior"])
    s("Transmission Weight",G["transmission"]); s("Transmission",G["transmission"])
    s("Coat Weight",G["clearcoat"]); s("Emission Color",(r*0.4,g*0.6,bl,1)); s("Emission Strength",L["emissive"])
    return m

def field(u,v,t):
    edge = math.sin(math.pi*u)*math.sin(math.pi*v)
    d = M["driver"]
    if d=="waves":  return M["amp"]*(math.sin(u*M["freq"]*2+t*2)*0.5+math.sin((u+v)*M["freq"]-t*2.4)*0.5)
    if d=="heightmap":
        r=math.hypot(u-0.5,v-0.5)*8; return M["amp"]*edge*math.sin(r-t*4)*math.exp(-r*0.12)
    w1=math.sin(u*M["freq"]+t*2)*math.cos(v*M["freq"]*0.8-t*1.3)
    w2=math.sin((u+v)*M["freq"]*1.6-t*2.4)
    return M["amp"]*(1+M["softness"])*edge*(0.6*w1+0.3*w2)

def build_base():
    me = bpy.data.meshes.new("slab"); ob = bpy.data.objects.new("slab", me)
    bpy.context.collection.objects.link(ob)
    gx,gy = Uu["subdiv"]+1, Uu["subdiv"]+1; sx,sy = Uu["sizeX"], Uu["sizeY"]
    bm = bmesh.new(); vt=[[None]*gx for _ in range(gy)]
    for j in range(gy):
        for i in range(gx):
            vt[j][i]=bm.verts.new((-sx/2+sx*i/(gx-1), -sy/2+sy*j/(gy-1), 0))
    bm.verts.ensure_lookup_table()
    for j in range(gy-1):
        for i in range(gx-1):
            bm.faces.new((vt[j][i],vt[j][i+1],vt[j+1][i+1],vt[j+1][i]))
    uv=bm.loops.layers.uv.new()
    for f in bm.faces:
        for lp in f.loops:
            c=lp.vert.co; lp[uv].uv=((c.x+sx/2)/sx,(c.y+sy/2)/sy)
    bm.to_mesh(me); bm.free(); me.materials.append(glass_mat())
    base=[v.co.copy() for v in me.vertices]; ob.shape_key_add(name="Basis",from_mix=False)
    sx,sy=Uu["sizeX"],Uu["sizeY"]
    for f in range(FRAMES):
        t=f/FRAMES*6.2831853; sk=ob.shape_key_add(name=f"f{f:03d}",from_mix=False)
        for idx,v in enumerate(me.vertices):
            c=base[idx]; u=(c.x+sx/2)/sx; w=(c.y+sy/2)/sy
            sk.data[idx].co=c+Vector((0,0,field(u,w,t)))
    kbs=[k for k in me.shape_keys.key_blocks if k.name!="Basis"]
    for f in range(FRAMES):
        bpy.context.scene.frame_set(f+1)
        for k,kb in enumerate(kbs):
            kb.value=1.0 if k==f else 0.0; kb.keyframe_insert("value",frame=f+1)
    bpy.context.scene.frame_set(1); return ob

def instance(base):
    objs=[base]; cx,cy,cz,sp=I["countX"],I["countY"],I["countZ"],I["spacing"]
    ox,oy,oz=(cx-1)/2,(cy-1)/2,(cz-1)/2
    for z in range(cz):
        for y in range(cy):
            for x in range(cx):
                if x==0 and y==0 and z==0:
                    base.location=(-ox*sp,-oy*sp,-oz*sp); continue
                d=base.copy(); d.data=base.data  # LINKED duplicate -> shared mesh -> instancing
                d.location=((x-ox)*sp,(y-oy)*sp,(z-oz)*sp)
                bpy.context.collection.objects.link(d); objs.append(d)
    return objs

def export(objs):
    bpy.ops.object.select_all(action='SELECT')
    base=os.path.join(OUT,"glass_led_volume"); res={}
    try:
        bpy.ops.export_scene.gltf(filepath=base+".glb",export_format='GLB',export_morph=True,
            export_animations=True,export_morph_animation=True,export_materials='EXPORT',
            export_gpu_instances=True)
        res["glb"]=os.path.getsize(base+".glb")
    except Exception as e: res["glb"]=f"ERR {e}"
    for ext in ("usd","usdz"):
        try:
            bpy.ops.wm.usd_export(filepath=base+"."+ext,export_animation=True,
                export_materials=True,use_instancing=True)
            res[ext]=os.path.getsize(base+"."+ext)
        except Exception as e: res[ext]=f"ERR {e}"
    try:
        bpy.ops.wm.alembic_export(filepath=base+".abc",start=1,end=FRAMES)
        res["abc"]=os.path.getsize(base+".abc")
    except Exception as e: res["abc"]=f"ERR {e}"
    json.dump({"config":CFG,"instances":len(objs),"exports":res},
              open(os.path.join(OUT,"instanced_manifest.json"),"w"),indent=2)
    print("[INSTANCED]",len(objs),"instances ->",res)

reset(); export(instance(build_base())); print("[DONE]",OUT)
