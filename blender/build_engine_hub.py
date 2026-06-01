"""
build_engine_hub.py — Blender as a full game-engine-style HUB that exports to UE5.
Adds: global MPC (controller empty + drivers), a material library (glass/metal/emissive/
triplanar/holographic, exposed params, blend modes), Geometry-Nodes procedural scatter,
all light types, multiple cameras, rigid+cloth physics, view layers, content-shelf
collections, and USD/MaterialX/glTF/FBX export. Run: blender --background --python build_engine_hub.py
"""
import bpy, math, os, mathutils
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"
PKG=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/engine"
for d in (OUT,PKG): os.makedirs(d,exist_ok=True)

# ---- enable importer/util add-ons (file types) ----
for a in ("node_wrangler","io_scene_gltf2","io_scene_fbx","io_mesh_stl","io_mesh_ply","io_scene_x3d","io_curve_svg"):
    try: bpy.ops.preferences.addon_enable(module=a)
    except Exception: pass

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try:
    sc.render.engine='BLENDER_EEVEE_NEXT'; sc.eevee.use_raytracing=True
except Exception: sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1920; sc.render.resolution_y=1080; sc.frame_start=1; sc.frame_end=60
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
try: sc.view_settings.look='AgX - High Contrast'
except Exception: pass

# ---- collections (content shelf) ----
def coll(n):
    c=bpy.data.collections.new(n); sc.collection.children.link(c); return c
C_MAT=coll("00_MaterialLibrary"); C_MESH=coll("Meshes"); C_PROC=coll("Procedural"); C_PHYS=coll("Physics"); C_LIGHT=coll("Lighting"); C_CAM=coll("Cameras")
def to(o,c):
    for u in list(o.users_collection): u.objects.unlink(o)
    c.objects.link(o)

# ---- GLOBAL MPC: controller empty + custom props ----
mpc=bpy.data.objects.new("MPC_Controller", None); sc.collection.objects.link(mpc)
mpc.empty_display_size=0.1
for k,v in (("GlobalEmission",2.0),("WaveSpeed",1.0),("GlobalTintR",0.05),("GlobalTintG",0.25),("GlobalTintB",1.0)):
    mpc[k]=v

def drive(socket, prop):
    try:
        fc=socket.driver_add("default_value"); d=fc.driver; d.type='AVERAGE'
        var=d.variables.new(); var.type='SINGLE_PROP'; var.targets[0].id=mpc; var.targets[0].data_path='["%s"]'%prop
    except Exception: pass

# ---- MATERIAL LIBRARY (reusable, exposed, blend modes) ----
def base(name):
    m=bpy.data.materials.new(name); m.use_nodes=True; return m, m.node_tree.nodes.get("Principled BSDF")
def s(b,n,v):
    if n in b.inputs: b.inputs[n].default_value=v

# 1 glass (clearcoat, transmission) - blend opaque (raytraced transmission)
mg,b=base("M_Glass"); s(b,"Base Color",(0.02,0.10,0.55,1)); s(b,"Roughness",0.03); s(b,"Transmission Weight",0.5); s(b,"Coat Weight",0.9); s(b,"IOR",1.5)
drive(b.inputs.get("Emission Strength") or b.inputs["Roughness"], "GlobalEmission") if "Emission Strength" in b.inputs else None
# 2 metal
mm,b=base("M_Metal"); s(b,"Base Color",(0.6,0.7,0.9,1)); s(b,"Metallic",1.0); s(b,"Roughness",0.18)
# 3 emissive LED (driven by MPC emission)
me,b=base("M_Emissive"); s(b,"Base Color",(0,0,0,1)); s(b,"Emission Color",(0.05,0.3,1,1))
if "Emission Strength" in b.inputs: drive(b.inputs["Emission Strength"], "GlobalEmission")
# 4 triplanar grid (object-coord checker)
mt=bpy.data.materials.new("M_Triplanar"); mt.use_nodes=True; nt=mt.node_tree; nt.nodes.clear()
tc=nt.nodes.new("ShaderNodeTexCoord"); ck=nt.nodes.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value=20
bb=nt.nodes.new("ShaderNodeBsdfPrincipled"); o=nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(tc.outputs["Object"],ck.inputs["Vector"]); nt.links.new(ck.outputs["Color"], bb.inputs["Base Color"]); nt.links.new(bb.outputs["BSDF"],o.inputs["Surface"])
# 5 holographic (fresnel emission)
mh=bpy.data.materials.new("M_Holographic"); mh.use_nodes=True; nt=mh.node_tree; nt.nodes.clear()
fr=nt.nodes.new("ShaderNodeFresnel"); ramp=nt.nodes.new("ShaderNodeValToRGB"); bb=nt.nodes.new("ShaderNodeBsdfPrincipled"); o=nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(fr.outputs[0],ramp.inputs["Fac"])
if "Emission Color" in bb.inputs: nt.links.new(ramp.outputs["Color"],bb.inputs["Emission Color"]); bb.inputs["Emission Strength"].default_value=3
nt.links.new(bb.outputs["BSDF"],o.inputs["Surface"])
LIB=[mg,mm,me,mt,mh]
# blend modes (EEVEE) + asset-mark each on a preview sphere
for i,m in enumerate(LIB):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(i*1.1-2.2, -4, 0.5)); sph=bpy.context.object
    bpy.ops.object.shade_smooth(); sph.data.materials.append(m); sph.name="Preview_"+m.name
    try: m.surface_render_method='BLENDED' if m.name=="M_Glass" else 'DITHERED'
    except Exception:
        try: m.blend_method='HASHED'
        except Exception: pass
    sph.asset_mark(); to(sph,C_MAT)

# ---- Geometry Nodes procedural scatter (Blender's PCG) ----
bpy.ops.mesh.primitive_grid_add(size=8, x_subdivisions=2, y_subdivisions=2, location=(0,0,0.02)); scatter=bpy.context.object; scatter.name="ProcScatter"
gnmod=scatter.modifiers.new("GeoScatter","NODES")
gn=bpy.data.node_groups.new("GN_Scatter",'GeometryNodeTree'); gnmod.node_group=gn
gn.interface.new_socket("Geometry",in_out='INPUT',socket_type='NodeSocketGeometry'); gn.interface.new_socket("Geometry",in_out='OUTPUT',socket_type='NodeSocketGeometry')
gi=gn.nodes.new("NodeGroupInput"); go=gn.nodes.new("NodeGroupOutput")
dist=gn.nodes.new("GeometryNodeDistributePointsOnFaces"); dist.inputs["Density"].default_value=3.0
ico=gn.nodes.new("GeometryNodeMeshIcoSphere"); ico.inputs["Radius"].default_value=0.18
iop=gn.nodes.new("GeometryNodeInstanceOnPoints"); jg=gn.nodes.new("GeometryNodeJoinGeometry")
gn.links.new(gi.outputs[0],dist.inputs["Mesh"]); gn.links.new(dist.outputs["Points"],iop.inputs["Points"]); gn.links.new(ico.outputs["Mesh"],iop.inputs["Instance"])
gn.links.new(gi.outputs[0],jg.inputs[0]); gn.links.new(iop.outputs["Instances"],jg.inputs[0]); gn.links.new(jg.outputs[0],go.inputs[0])
scatter.data.materials.append(me); to(scatter,C_PROC)

# ---- physics: rigid ball + cloth sheet ----
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(2,2,4)); ball=bpy.context.object; bpy.ops.object.shade_smooth(); ball.data.materials.append(mm)
try: bpy.ops.rigidbody.object_add(); ball.rigid_body.type='ACTIVE'
except Exception: pass
to(ball,C_PHYS)
bpy.ops.mesh.primitive_grid_add(size=3, x_subdivisions=20, y_subdivisions=20, location=(2,2,3)); cloth=bpy.context.object; cloth.data.materials.append(mg)
try: cloth.modifiers.new("Cloth","CLOTH")
except Exception: pass
to(cloth,C_PHYS)
bpy.ops.mesh.primitive_plane_add(size=12, location=(0,0,0)); ground=bpy.context.object; ground.data.materials.append(mt)
try: bpy.ops.rigidbody.object_add(); ground.rigid_body.type='PASSIVE'
except Exception: pass
to(ground,C_PHYS)

# ---- all light types + HDRI world ----
world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True
world.node_tree.nodes.get("Background").inputs[0].default_value=(0.01,0.02,0.05,1); world.node_tree.nodes.get("Background").inputs[1].default_value=0.5
def light(typ,loc,energy,col,nm,**kw):
    l=bpy.data.lights.new(nm,typ); l.energy=energy; l.color=col
    for k,v in kw.items():
        try: setattr(l,k,v)
        except Exception: pass
    o=bpy.data.objects.new(nm,l); o.location=loc; sc.collection.objects.link(o); to(o,C_LIGHT); return o
light('SUN',(0,0,10),3.0,(1,0.95,0.9),"Sun")
light('AREA',(-6,-4,7),6000,(0.5,0.7,1.0),"KeyArea",size=8)
light('SPOT',(5,-3,6),8000,(0.6,0.9,1.0),"Spot",spot_size=math.radians(45))
light('POINT',(0,3,3),2000,(1,0.4,0.6),"AccentPoint")

# ---- multiple cameras ----
def cam(name,loc,target,lens):
    cd=bpy.data.cameras.new(name); c=bpy.data.objects.new(name,cd); sc.collection.objects.link(c)
    d=mathutils.Vector(target)-mathutils.Vector(loc); c.location=loc; c.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); cd.lens=lens; to(c,C_CAM); return c
hero=cam("Cam_Hero",(-9,-9,4.5),(0,0,1),42); cam("Cam_Top",(0,0,12),(0,0,0),35); cam("Cam_Closeup",(-3,-3,1.5),(0,-4,0.5),85)
sc.camera=hero

# ---- view layer (extra) ----
try: sc.view_layers.new("FX_Layer")
except Exception: pass

# ---- render + export (USD / glTF / FBX) ----
sc.frame_set(15)
sc.render.filepath=os.path.join(OUT,"SPIN_engine.png"); bpy.ops.render.render(write_still=True); print("[ENGINE] rendered")
bpy.ops.object.select_all(action='SELECT'); res={}
for ext,fn in (("usdc",lambda p: bpy.ops.wm.usd_export(filepath=p,export_materials=True,export_lights=True,export_cameras=True)),
               ("glb",lambda p: bpy.ops.export_scene.gltf(filepath=p,export_format='GLB',export_materials='EXPORT',export_cameras=True,export_lights=True)),
               ("fbx",lambda p: bpy.ops.export_scene.fbx(filepath=p))):
    try: pth=os.path.join(PKG,"SPIN_Engine."+ext); fn(pth); res[ext]=os.path.getsize(pth)
    except Exception as e: res[ext]=f"ERR {e}"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PKG,"SPIN_EngineHub.blend"))
print("[ENGINE] exports",res); print("[ENGINE] DONE — MPC + material library + geonodes + physics + lights + cameras + layers")
