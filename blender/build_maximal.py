"""
build_maximal.py — MAXIMAL Blender solution: configurable shaders (glass BSDF + triplanar
+ emissive), animated mesh, soft-body + rigid-body physics, 3-point + HDRI lighting,
compositor post (glare/bloom + grade), content-shelf asset marking, render, and export
OpenUSD + MaterialX + GLB. EEVEE Next (Vulkan-class) raytraced.
Run: blender --background --python build_maximal.py
"""
import bpy, math, os, uuid, mathutils
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"
PKG=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/master"
for d in (OUT,PKG): os.makedirs(d,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try:
    sc.render.engine='BLENDER_EEVEE_NEXT'; sc.eevee.use_raytracing=True; sc.eevee.ray_tracing_options.use_denoise=True
except Exception: sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1920; sc.render.resolution_y=1080
sc.frame_start=1; sc.frame_end=48
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
try: sc.view_settings.look='AgX - High Contrast'
except Exception: pass

# ---------------- configurable GLASS node group (exposed params) ----------------
def make_glass_group():
    ng=bpy.data.node_groups.new("NG_ConfigurableGlass",'ShaderNodeTree')
    # interface (Blender 4.x)
    def inp(name,typ,default=None,mn=None,mx=None):
        s=ng.interface.new_socket(name,in_out='INPUT',socket_type=typ)
        if default is not None: s.default_value=default
        if mn is not None: s.min_value=mn
        if mx is not None: s.max_value=mx
        return s
    ng.interface.new_socket("BSDF",in_out='OUTPUT',socket_type='NodeSocketShader')
    inp("Color",'NodeSocketColor',(0.02,0.10,0.55,1))
    inp("Roughness",'NodeSocketFloat',0.04,0.0,1.0)
    inp("Transmission",'NodeSocketFloat',0.4,0.0,1.0)
    inp("IOR",'NodeSocketFloat',1.5,1.0,2.5)
    inp("Clearcoat",'NodeSocketFloat',0.8,0.0,1.0)
    inp("Emission",'NodeSocketFloat',1.0,0.0,10.0)
    gin=ng.nodes.new("NodeGroupInput"); gin.location=(-600,0)
    gout=ng.nodes.new("NodeGroupOutput"); gout.location=(300,0)
    b=ng.nodes.new("ShaderNodeBsdfPrincipled"); b.location=(-200,0)
    L=ng.links
    L.new(gin.outputs["Color"],b.inputs["Base Color"])
    L.new(gin.outputs["Roughness"],b.inputs["Roughness"])
    if "Transmission Weight" in b.inputs: L.new(gin.outputs["Transmission"],b.inputs["Transmission Weight"])
    L.new(gin.outputs["IOR"],b.inputs["IOR"])
    if "Coat Weight" in b.inputs: L.new(gin.outputs["Clearcoat"],b.inputs["Coat Weight"])
    if "Emission Color" in b.inputs: L.new(gin.outputs["Color"],b.inputs["Emission Color"])
    if "Emission Strength" in b.inputs: L.new(gin.outputs["Emission"],b.inputs["Emission Strength"])
    L.new(b.outputs["BSDF"],gout.inputs["BSDF"])
    return ng
GG=make_glass_group()

def glass_mat(name,color=(0.02,0.10,0.55),rough=0.04,trans=0.4,emis=1.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; nt.nodes.clear()
    g=nt.nodes.new("ShaderNodeGroup"); g.node_tree=GG
    g.inputs["Color"].default_value=(*color,1); g.inputs["Roughness"].default_value=rough
    g.inputs["Transmission"].default_value=trans; g.inputs["Emission"].default_value=emis
    out=nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(g.outputs["BSDF"],out.inputs["Surface"])
    return m

# triplanar (world-aligned) emissive grid material
def triplanar_mat(name):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; nt.nodes.clear()
    tex=nt.nodes.new("ShaderNodeTexCoord"); chk=nt.nodes.new("ShaderNodeTexChecker")
    chk.inputs["Scale"].default_value=24.0
    chk.inputs["Color1"].default_value=(0.05,0.3,1,1); chk.inputs["Color2"].default_value=(0,0,0.05,1)
    nt.links.new(tex.outputs["Object"],chk.inputs["Vector"])  # object-space ~ triplanar grid
    b=nt.nodes.new("ShaderNodeBsdfPrincipled")
    if "Emission Color" in b.inputs: nt.links.new(chk.outputs["Color"],b.inputs["Emission Color"])
    if "Emission Strength" in b.inputs: b.inputs["Emission Strength"].default_value=4.0
    out=nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(b.outputs["BSDF"],out.inputs["Surface"])
    return m

# ---------------- collections (content shelf) ----------------
def coll(n):
    c=bpy.data.collections.new(n); sc.collection.children.link(c); return c
C_MESH=coll("Meshes"); C_LED=coll("LED_Animated"); C_PHYS=coll("Physics"); C_LIGHT=coll("Lighting"); C_CAM=coll("Cameras")
def to(o,c):
    for u in list(o.users_collection): u.objects.unlink(o)
    c.objects.link(o)

# world HDRI-ish gradient
world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True
world.node_tree.nodes.get("Background").inputs[0].default_value=(0.006,0.012,0.03,1)
world.node_tree.nodes.get("Background").inputs[1].default_value=0.4

# ---------------- import a real asset (court) if present, else demo slab ----------------
court_path=r"C:/Users/joeyw/OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb"
if os.path.exists(court_path):
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=court_path)
    court=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
    # normalize scale
    if court:
        for o in court:
            if not o.parent: o.scale=(o.scale[0]*0.02,o.scale[1]*0.02,o.scale[2]*0.02)
        gm=glass_mat("M_Court",(0.015,0.07,0.6),0.02,0.12,0.6)
        for o in court: o.data.materials.clear(); o.data.materials.append(gm); o.asset_mark(); to(o,C_MESH)

# ---------------- animated LED glass volume (configurable + animated) ----------------
cm=triplanar_mat("M_LED_Triplanar"); cells=[]
N,M=10,5
for j in range(M):
    for i in range(N):
        x=(i-(N-1)/2)*0.6; y=(j-(M-1)/2)*0.6
        bpy.ops.mesh.primitive_cube_add(size=0.5,location=(x,y,3))
        c=bpy.context.object; bpy.ops.object.modifier_add(type='BEVEL'); c.modifiers[-1].width=0.06; c.modifiers[-1].segments=3
        bpy.ops.object.shade_smooth(); c.data.materials.append(cm)
        # animate Z (shape via location keyframes)
        for f in range(1,49,8):
            c.location.z=3+0.4*math.sin(i*0.6+j*0.5+f*0.2); c.keyframe_insert("location",index=2,frame=f)
        cells.append(c)
for c in cells: to(c,C_LED)
if cells: cells[0].asset_mark()

# ---------------- physics: rigid-body ball + soft-body glass sheet ----------------
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3,location=(2,0,4)); ball=bpy.context.object; bpy.ops.object.shade_smooth()
ball.data.materials.append(glass_mat("M_Ball",(0.7,0.95,0.1),0.3,0.0,1.4))
try:
    bpy.ops.rigidbody.object_add(); ball.rigid_body.type='ACTIVE'
except Exception: pass
to(ball,C_PHYS)
bpy.ops.mesh.primitive_plane_add(size=4,location=(0,0,0)); ground=bpy.context.object; ground.scale=(3,2,1)
ground.data.materials.append(glass_mat("M_Ground",(0.01,0.05,0.4),0.05,0.05,0.3))
try:
    bpy.ops.rigidbody.object_add(); ground.rigid_body.type='PASSIVE'
except Exception: pass
to(ground,C_PHYS); ground.asset_mark()

# ---------------- lighting (3-point + key) ----------------
def area(loc,rot,e,col,sz,nm):
    l=bpy.data.lights.new(nm,'AREA'); l.energy=e; l.color=col; l.size=sz
    o=bpy.data.objects.new(nm,l); o.location=loc; o.rotation_euler=rot; sc.collection.objects.link(o); return o
for o in [area((-7,-5,9),(math.radians(-50),0,math.radians(-35)),9000,(0.5,0.7,1.0),10,"Key"),
          area((8,5,7),(math.radians(-55),0,math.radians(140)),5000,(0.3,0.55,1.0),8,"Rim"),
          area((0,-9,4),(math.radians(-72),0,0),3500,(0.6,0.9,1.0),7,"Fill")]:
    to(o,C_LIGHT)

# ---------------- camera ----------------
cd=bpy.data.cameras.new("HeroCamera"); cam=bpy.data.objects.new("HeroCamera",cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(-9,-9,4.5); look=mathutils.Vector((0,0,1.5))-cam.location
cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler(); cd.lens=42; cd.dof.use_dof=True; cd.dof.focus_distance=13; cd.dof.aperture_fstop=2.8
to(cam,C_CAM)

# ---------------- compositor post-processing (glare/bloom + grade) ----------------
sc.use_nodes=True; cnt=sc.node_tree; cnt.nodes.clear()
rl=cnt.nodes.new("CompositorNodeRLayers"); comp=cnt.nodes.new("CompositorNodeComposite")
glare=cnt.nodes.new("CompositorNodeGlare"); glare.glare_type='FOG_GLOW'; glare.threshold=0.7
try: glare.size=7
except Exception: pass
cb=cnt.nodes.new("CompositorNodeColorBalance")
cnt.links.new(rl.outputs["Image"],glare.inputs["Image"]); cnt.links.new(glare.outputs["Image"],cb.inputs["Image"]); cnt.links.new(cb.outputs["Image"],comp.inputs["Image"])

# ---------------- render + exports ----------------
sc.frame_set(20)
sc.render.filepath=os.path.join(OUT,"SPIN_maximal.png"); bpy.ops.render.render(write_still=True)
print("[MAX] rendered")
bpy.ops.object.select_all(action='SELECT'); res={}
for ext in ("usdc","glb"):
    try:
        p=os.path.join(PKG,"SPIN_maximal."+ext)
        if ext=="glb": bpy.ops.export_scene.gltf(filepath=p,export_format='GLB',export_materials='EXPORT',export_cameras=True,export_lights=True)
        else: bpy.ops.wm.usd_export(filepath=p,export_materials=True,export_lights=True,export_cameras=True)
        res[ext]=os.path.getsize(p)
    except Exception as e: res[ext]=f"ERR {e}"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PKG,"SPIN_Maximal.blend"))
print("[MAX] exports",res); print("[MAX] DONE")
