"""
build_lookdev_pipeline.py — LOOK-DEV in Blender + export the UE-ready pipeline package.
Refined glossy-blue glass SPIN scene (mood-board styled) -> render PNG + export
USD (.usdc, geometry+lights+cameras+materials) + GLB + USDZ. UE5 imports the USD via
Interchange; MaterialX-style Principled glass maps to Substrate.
Run: blender --background --python build_lookdev_pipeline.py
"""
import bpy, math, os, mathutils
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"; PKG=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/scene"
for d in (OUT,PKG): os.makedirs(d,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try: sc.render.engine='BLENDER_EEVEE_NEXT'
except Exception: sc.render.engine='BLENDER_EEVEE'
try:
    sc.eevee.use_raytracing=True; sc.eevee.ray_tracing_options.use_denoise=True
    sc.eevee.use_shadows=True
except Exception: pass
sc.render.resolution_x=1920; sc.render.resolution_y=1080
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
sc.view_settings.look='Medium High Contrast' if any(v.name=='Medium High Contrast' for v in sc.view_settings.bl_rna.properties['look'].enum_items) else 'None'

# studio-ish environment for glass reflections (gradient + bright strips)
world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True
nt=world.node_tree; bg=nt.nodes.get("Background")
grad=nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type='SPHERICAL'
texco=nt.nodes.new("ShaderNodeTexCoord"); cr=nt.nodes.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].color=(0.002,0.004,0.012,1); cr.color_ramp.elements[1].color=(0.02,0.05,0.13,1)
nt.links.new(texco.outputs["Generated"],grad.inputs["Vector"]); nt.links.new(grad.outputs["Color"],cr.inputs["Fac"])
nt.links.new(cr.outputs["Color"],bg.inputs[0]); bg.inputs[1].default_value=0.5

def glass(name, base, emis=0.0, rough=0.03, trans=0.45, coat=0.9):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(*base,1)); s("Roughness",rough); s("Metallic",0); s("IOR",1.5)
    s("Transmission Weight",trans); s("Coat Weight",coat); s("Coat Roughness",0.015)
    s("Emission Color",(*base,1)); s("Emission Strength",emis)
    return m

# court (rounded glossy glass slab) + neon lines
bpy.ops.mesh.primitive_cube_add(size=1); court=bpy.context.object; court.scale=(6,3.2,0.16); court.name="Court"
bpy.ops.object.modifier_add(type='BEVEL'); court.modifiers[-1].width=0.10; court.modifiers[-1].segments=5
bpy.ops.object.shade_smooth(); court.data.materials.append(glass("M_Court",(0.015,0.08,0.5),emis=0.4,rough=0.02,trans=0.1))
def neon(scale,loc,col,e):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.scale=scale
    o.data.materials.append(glass("M_Neon",col,emis=e,rough=0.3,trans=0,coat=0)); return o
neon((6,0.03,0.02),(0,0,0.085),(0.25,0.65,1.0),12)          # center line
neon((0.03,3.2,0.02),(0,0,0.085),(0.25,0.65,1.0),10)        # cross line
neon((6,3.2,0.005),(0,0,0.092),(0.05,0.2,0.6),3)            # court glow plate

# glass LED cell volume (connected-looking grid of glossy cubes, wave height)
cm=glass("M_Cell",(0.05,0.25,1.0),emis=2.6,rough=0.02,trans=0.35)
N,M=11,6
for j in range(M):
    for i in range(N):
        x=(i-(N-1)/2)*0.30; y=(j-(M-1)/2)*0.30
        z=1.0+0.16*math.sin(i*0.6+j*0.5)+0.10*math.cos((i+j)*0.4)
        bpy.ops.mesh.primitive_cube_add(size=0.26,location=(x,y,z)); c=bpy.context.object
        bpy.ops.object.modifier_add(type='BEVEL'); c.modifiers[-1].width=0.035; c.modifiers[-1].segments=3
        bpy.ops.object.shade_smooth(); c.data.materials.append(cm)

# tennis ball + a simple racket proxy
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22,location=(2.3,0.7,0.5)); ball=bpy.context.object; bpy.ops.object.shade_smooth()
bm=bpy.data.materials.new("M_Ball"); bm.use_nodes=True; bb=bm.node_tree.nodes.get("Principled BSDF")
bb.inputs["Base Color"].default_value=(0.75,0.95,0.1,1); bb.inputs["Emission Color"].default_value=(0.6,0.9,0.1,1); bb.inputs["Emission Strength"].default_value=1.5
ball.data.materials.append(bm)
bpy.ops.mesh.primitive_torus_add(major_radius=0.5,minor_radius=0.05,location=(-2.6,-0.8,0.5)); rk=bpy.context.object; rk.scale=(1,1.4,1); rk.rotation_euler=(math.radians(70),0,0.4)
bpy.ops.mesh.primitive_cylinder_add(radius=0.05,depth=1.1,location=(-2.6,-0.3,0.25)); handle=bpy.context.object; handle.rotation_euler=(math.radians(70),0,0.4)
rmat=glass("M_Racket",(0.02,0.1,0.45),emis=0.5,rough=0.05,trans=0.0,coat=1.0)
rk.data.materials.append(rmat); handle.data.materials.append(rmat)

def area(loc,rot,e,col,sz):
    l=bpy.data.lights.new("L",'AREA'); l.energy=e; l.color=col; l.size=sz
    o=bpy.data.objects.new("L",l); o.location=loc; o.rotation_euler=rot; sc.collection.objects.link(o)
area((-4,-3,5),(math.radians(-50),0,math.radians(-35)),4000,(0.5,0.7,1.0),6)
area((4.5,3,4),(math.radians(-55),0,math.radians(140)),2400,(0.3,0.55,1.0),5)
area((0,-5.5,2.2),(math.radians(-72),0,0),1600,(0.6,0.9,1.0),4)
area((0,4.5,3),(math.radians(-120),0,0),1000,(0.2,0.4,1.0),5)

cam_d=bpy.data.cameras.new("Cam"); cam=bpy.data.objects.new("HeroCamera",cam_d); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(-6.8,-6.8,3.0); look=mathutils.Vector((0,0,0.7))-cam.location
cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler(); cam_d.lens=45; cam_d.dof.use_dof=True; cam_d.dof.focus_distance=9.5; cam_d.dof.aperture_fstop=2.8

# render
sc.render.filepath=os.path.join(OUT,"SPIN_hero_v2.png"); bpy.ops.render.render(write_still=True)
print("[LOOKDEV] rendered ->", sc.render.filepath)

# export UE-ready package: USD + GLB + USDZ
bpy.ops.object.select_all(action='SELECT')
res={}
for ext,op in [("usdc",lambda p: bpy.ops.wm.usd_export(filepath=p,export_materials=True,export_lights=True,export_cameras=True)),
               ("glb",lambda p: bpy.ops.export_scene.gltf(filepath=p,export_format='GLB',export_materials='EXPORT',export_cameras=True,export_lights=True)),
               ("usdz",lambda p: bpy.ops.wm.usd_export(filepath=p,export_materials=True))]:
    try: pth=os.path.join(PKG,"SPIN_Scene."+ext); op(pth); res[ext]=os.path.getsize(pth)
    except Exception as e: res[ext]=f"ERR {e}"
print("[EXPORT]", res)
