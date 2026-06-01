"""
build_master_blend.py — THE organized master Blender file for SPIN.
Collections: SPIN_Assets (your real court/racket/ball) · SPIN_LED_Volume · SPIN_Lighting
· SPIN_Cameras. Glossy-blue glass materials, high-contrast look, hero camera. Saves
SPIN_Master.blend + renders final + exports USD/GLB/USDZ for UE5/web/AR.
Run: blender --background --python build_master_blend.py
"""
import bpy, math, os, mathutils
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"
PKG=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/scene"
for d in (OUT,PKG): os.makedirs(d,exist_ok=True)
COURT=r"C:/Users/joeyw/OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb"
RACKET=r"C:/Users/joeyw/OneDrive/EverythingExisting/TennisRacket v1.fbx"
BALL=r"C:/Users/joeyw/OneDrive/EverythingExisting/tennis_ball.glb"

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try:
    sc.render.engine='BLENDER_EEVEE_NEXT'; sc.eevee.use_raytracing=True; sc.eevee.ray_tracing_options.use_denoise=True
except Exception: sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1920; sc.render.resolution_y=1080
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
for lk in ('AgX - High Contrast','High Contrast','Very High Contrast'):
    if any(v.name==lk for v in sc.view_settings.bl_rna.properties['look'].enum_items): sc.view_settings.look=lk; break
sc.view_settings.exposure=0.4

# ---- organized collections ----
def coll(name):
    c=bpy.data.collections.new(name); sc.collection.children.link(c); return c
C_ASSET=coll("SPIN_Assets"); C_LED=coll("SPIN_LED_Volume"); C_LIGHT=coll("SPIN_Lighting"); C_CAM=coll("SPIN_Cameras")
def to_coll(objs, c):
    for o in objs:
        for uc in list(o.users_collection): uc.objects.unlink(o)
        c.objects.link(o)

# world (dark blue gradient)
world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True
bg=world.node_tree.nodes.get("Background"); bg.inputs[0].default_value=(0.006,0.012,0.03,1); bg.inputs[1].default_value=0.4

def glass(name, base, emis=0.0, rough=0.015, trans=0.3, coat=1.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(*base,1)); s("Roughness",rough); s("Metallic",0); s("IOR",1.5)
    s("Transmission Weight",trans); s("Coat Weight",coat); s("Coat Roughness",0.02)
    s("Emission Color",(*base,1)); s("Emission Strength",emis)
    return m

def imp(path):
    before=set(bpy.data.objects)
    try:
        if path.lower().endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=path)
        else: bpy.ops.import_scene.fbx(filepath=path)
    except Exception as e: print("import fail",path,e); return []
    return [o for o in bpy.data.objects if o not in before]

def fit(objs,target,z_at=0.0,center=(0,0)):
    mesh=[o for o in objs if o.type=='MESH']
    if not mesh: return
    mn=[1e9]*3; mx=[-1e9]*3
    for o in mesh:
        for c in o.bound_box:
            w=o.matrix_world@mathutils.Vector(c)
            for k in range(3): mn[k]=min(mn[k],w[k]); mx[k]=max(mx[k],w[k])
    size=max(mx[0]-mn[0],mx[1]-mn[1]) or 1; s=target/size; cx=(mn[0]+mx[0])/2; cy=(mn[1]+mx[1])/2
    for o in mesh:
        if o.parent: continue
        o.scale=tuple(v*s for v in o.scale)
        o.location=(o.location[0]*s-cx*s+center[0], o.location[1]*s-cy*s+center[1], o.location[2]*s-mn[2]*s+z_at)

def style(objs,mat):
    for o in objs:
        if o.type=='MESH':
            o.data.materials.clear(); o.data.materials.append(mat)
            try: bpy.context.view_layer.objects.active=o; bpy.ops.object.shade_smooth()
            except Exception: pass

# ---- import + style YOUR real assets ----
court=imp(COURT); fit(court,12.0,0.0); style(court,glass("M_Court",(0.015,0.07,0.6),emis=0.6,rough=0.012)); to_coll(court,C_ASSET)
rk=imp(RACKET); fit(rk,2.4,0.6,center=(-3.8,-2.2)); style(rk,glass("M_Racket",(0.02,0.10,0.5),emis=0.4,rough=0.04,trans=0.0)); to_coll(rk,C_ASSET)
ball=imp(BALL)
if ball: fit(ball,0.45,0.5,center=(2.4,0.8)); style(ball,glass("M_Ball",(0.6,0.9,0.1),emis=1.4,rough=0.3,trans=0.0)); to_coll(ball,C_ASSET)

# ---- LED glass cell volume ----
cm=glass("M_Cell",(0.05,0.25,1.0),emis=2.8,rough=0.012,trans=0.3); N,M=12,6; cells=[]
for j in range(M):
    for i in range(N):
        x=(i-(N-1)/2)*0.5; y=(j-(M-1)/2)*0.5; z=3.0+0.35*math.sin(i*0.6+j*0.5)+0.2*math.cos((i+j)*0.4)
        bpy.ops.mesh.primitive_cube_add(size=0.42,location=(x,y,z)); c=bpy.context.object
        bpy.ops.object.modifier_add(type='BEVEL'); c.modifiers[-1].width=0.05; c.modifiers[-1].segments=3
        bpy.ops.object.shade_smooth(); c.data.materials.append(cm); cells.append(c)
to_coll(cells,C_LED)

# ---- lighting ----
def area(loc,rot,e,col,sz,nm):
    l=bpy.data.lights.new(nm,'AREA'); l.energy=e; l.color=col; l.size=sz
    o=bpy.data.objects.new(nm,l); o.location=loc; o.rotation_euler=rot; sc.collection.objects.link(o); return o
L=[area((-7,-5,9),(math.radians(-50),0,math.radians(-35)),9000,(0.5,0.7,1.0),10,"Key"),
   area((8,5,7),(math.radians(-55),0,math.radians(140)),5000,(0.3,0.55,1.0),8,"Rim"),
   area((0,-9,4),(math.radians(-72),0,0),3500,(0.6,0.9,1.0),7,"Fill")]
to_coll(L,C_LIGHT)

# ---- cameras ----
cd=bpy.data.cameras.new("HeroCamera"); cam=bpy.data.objects.new("HeroCamera",cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(-11,-11,5.5); look=mathutils.Vector((0,0,1.2))-cam.location
cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler(); cd.lens=45; cd.dof.use_dof=True; cd.dof.focus_distance=16; cd.dof.aperture_fstop=3.2
to_coll([cam],C_CAM)

# ---- save master .blend ----
blendpath=os.path.join(PKG,"SPIN_Master.blend"); bpy.ops.wm.save_as_mainfile(filepath=blendpath)
print("[MASTER] saved", blendpath)

# ---- render final ----
sc.render.filepath=os.path.join(OUT,"SPIN_master_final.png"); bpy.ops.render.render(write_still=True)
print("[MASTER] rendered", sc.render.filepath)

# ---- export UE/web/AR ----
bpy.ops.object.select_all(action='SELECT'); res={}
for ext in ("usdc","glb","usdz"):
    try:
        p=os.path.join(PKG,"SPIN_Master."+ext)
        if ext=="glb": bpy.ops.export_scene.gltf(filepath=p,export_format='GLB',export_materials='EXPORT',export_cameras=True,export_lights=True)
        else: bpy.ops.wm.usd_export(filepath=p,export_materials=True,export_lights=True,export_cameras=True)
        res[ext]=os.path.getsize(p)
    except Exception as e: res[ext]=f"ERR {e}"
print("[MASTER] exports", res)
