"""
build_real_court.py — use the USER'S REAL existing assets (TennisCourt.glb, racket, ball)
+ glossy-blue glass styling + LED cell volume + lighting. Render + export UE-ready package.
Run: blender --background --python build_real_court.py
"""
import bpy, math, os, mathutils
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"
PKG=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/scene"
for d in (OUT,PKG): os.makedirs(d,exist_ok=True)
COURT=r"C:/Users/joeyw/OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb"
RACKET=r"C:/Users/joeyw/OneDrive/EverythingExisting/TennisRacket v1.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try:
    sc.render.engine='BLENDER_EEVEE_NEXT'; sc.eevee.use_raytracing=True; sc.eevee.ray_tracing_options.use_denoise=True
except Exception: sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1920; sc.render.resolution_y=1080
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
# high gamma contrast, punchy blue-glass look
for lk in ('AgX - Very High Contrast','Very High Contrast','High Contrast','AgX - High Contrast'):
    if any(v.name==lk for v in sc.view_settings.bl_rna.properties['look'].enum_items):
        sc.view_settings.look=lk; break
sc.view_settings.exposure=0.5; sc.view_settings.gamma=1.05

world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True
bg=world.node_tree.nodes.get("Background"); bg.inputs[0].default_value=(0.006,0.012,0.03,1); bg.inputs[1].default_value=0.4

def glass(name, base, emis=0.0, rough=0.04, trans=0.4, coat=0.85):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(*base,1)); s("Roughness",rough); s("Metallic",0); s("IOR",1.5)
    s("Transmission Weight",trans); s("Coat Weight",coat); s("Coat Roughness",0.02)
    s("Emission Color",(*base,1)); s("Emission Strength",emis)
    return m

def import_any(path):
    before=set(bpy.data.objects)
    if path.lower().endswith(".glb") or path.lower().endswith(".gltf"): bpy.ops.import_scene.gltf(filepath=path)
    else: bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o not in before]

def fit(objs, target_size, z_at=0.0, center=(0,0)):
    mesh=[o for o in objs if o.type=='MESH']
    if not mesh: return
    mn=[1e9]*3; mx=[-1e9]*3
    for o in mesh:
        for c in o.bound_box:
            w=o.matrix_world@mathutils.Vector(c)
            for k in range(3): mn[k]=min(mn[k],w[k]); mx[k]=max(mx[k],w[k])
    size=max(mx[0]-mn[0], mx[1]-mn[1]) or 1.0
    s=target_size/size
    cx=(mn[0]+mx[0])/2; cy=(mn[1]+mx[1])/2
    for o in mesh:
        if o.parent: continue
        o.scale=(o.scale[0]*s,o.scale[1]*s,o.scale[2]*s)
        o.location=(o.location[0]*s-(cx*s)+center[0], o.location[1]*s-(cy*s)+center[1], o.location[2]*s-(mn[2]*s)+z_at)

def apply_mat(objs, mat):
    for o in objs:
        if o.type=='MESH':
            o.data.materials.clear(); o.data.materials.append(mat)
            try: bpy.context.view_layer.objects.active=o; bpy.ops.object.shade_smooth()
            except Exception: pass

# --- the REAL court, styled glossy blue glass ---
court=import_any(COURT); fit(court, 12.0, z_at=0.0)
apply_mat(court, glass("M_Court",(0.015,0.07,0.6),emis=0.7,rough=0.012,trans=0.08,coat=1.0))

# --- the REAL racket ---
try:
    rk=import_any(RACKET); fit(rk, 2.2, z_at=0.6, center=(-3.5,-2.0))
    apply_mat(rk, glass("M_Racket",(0.02,0.10,0.5),emis=0.4,rough=0.05,trans=0.0,coat=1.0))
except Exception as e: print("racket skip:",e)

# --- LED glass cell volume hovering over the court ---
cm=glass("M_Cell",(0.05,0.25,1.0),emis=2.6,rough=0.02,trans=0.35); N,M=12,6
for j in range(M):
    for i in range(N):
        x=(i-(N-1)/2)*0.5; y=(j-(M-1)/2)*0.5
        z=3.0+0.35*math.sin(i*0.6+j*0.5)+0.2*math.cos((i+j)*0.4)
        bpy.ops.mesh.primitive_cube_add(size=0.42,location=(x,y,z)); c=bpy.context.object
        bpy.ops.object.modifier_add(type='BEVEL'); c.modifiers[-1].width=0.05; c.modifiers[-1].segments=3
        bpy.ops.object.shade_smooth(); c.data.materials.append(cm)

# --- lighting ---
def area(loc,rot,e,col,sz):
    l=bpy.data.lights.new("L",'AREA'); l.energy=e; l.color=col; l.size=sz
    o=bpy.data.objects.new("L",l); o.location=loc; o.rotation_euler=rot; sc.collection.objects.link(o)
area((-7,-5,9),(math.radians(-50),0,math.radians(-35)),9000,(0.5,0.7,1.0),10)
area((8,5,7),(math.radians(-55),0,math.radians(140)),5000,(0.3,0.55,1.0),8)
area((0,-9,4),(math.radians(-72),0,0),3500,(0.6,0.9,1.0),7)

cam_d=bpy.data.cameras.new("Cam"); cam=bpy.data.objects.new("HeroCamera",cam_d); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(-11,-11,5.5); look=mathutils.Vector((0,0,1.2))-cam.location
cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler(); cam_d.lens=45
cam_d.dof.use_dof=True; cam_d.dof.focus_distance=16; cam_d.dof.aperture_fstop=3.2

sc.render.filepath=os.path.join(OUT,"SPIN_realcourt_final.png"); bpy.ops.render.render(write_still=True)
print("[REALCOURT] rendered ->", sc.render.filepath)
bpy.ops.object.select_all(action='SELECT'); res={}
for ext in ("usdc","glb","usdz"):
    try:
        p=os.path.join(PKG,"SPIN_RealCourt."+ext)
        if ext=="glb": bpy.ops.export_scene.gltf(filepath=p,export_format='GLB',export_materials='EXPORT',export_cameras=True,export_lights=True)
        else: bpy.ops.wm.usd_export(filepath=p,export_materials=True,export_lights=True,export_cameras=True)
        res[ext]=os.path.getsize(p)
    except Exception as e: res[ext]=f"ERR {e}"
print("[EXPORT]",res)
