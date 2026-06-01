"""
build_beautiful_court.py — the MOST beautiful court: displacement, deep glass, HDRI-style
lighting, glow/glare effects, cinematic camera. Run: blender --background --python this.py
"""
import bpy, math, os, mathutils
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"; os.makedirs(OUT,exist_ok=True)
COURT=r"C:/Users/joeyw/OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb"
HEIGHT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/textures/wave_heightmap.png"

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try: sc.render.engine='BLENDER_EEVEE_NEXT'; sc.eevee.use_raytracing=True; sc.eevee.ray_tracing_options.use_denoise=True
except Exception: sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1920; sc.render.resolution_y=1080
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
try: sc.view_settings.look='AgX - High Contrast'; sc.view_settings.exposure=0.3
except Exception: pass

# studio gradient world (reflections)
world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True; nt=world.node_tree
bg=nt.nodes.get("Background"); grad=nt.nodes.new("ShaderNodeTexGradient"); grad.gradient_type='SPHERICAL'; tc=nt.nodes.new("ShaderNodeTexCoord")
cr=nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color=(0.002,0.004,0.012,1); cr.color_ramp.elements[1].color=(0.03,0.07,0.18,1)
nt.links.new(tc.outputs["Generated"],grad.inputs["Vector"]); nt.links.new(grad.outputs["Color"],cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"],bg.inputs[0]); bg.inputs[1].default_value=0.6

def glass(name,base,emis,rough,trans,coat=1.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(*base,1)); s("Roughness",rough); s("IOR",1.5); s("Transmission Weight",trans); s("Coat Weight",coat); s("Coat Roughness",0.01)
    s("Emission Color",(*base,1)); s("Emission Strength",emis); return m

# import + style court with subtle displacement
if os.path.exists(COURT):
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=COURT)
    court=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
    gm=glass("M_Court",(0.015,0.07,0.6),0.5,0.012,0.1)
    for o in court:
        if not o.parent: o.scale=tuple(v*0.02 for v in o.scale)
        o.data.materials.clear(); o.data.materials.append(gm)
        try: bpy.context.view_layer.objects.active=o; bpy.ops.object.shade_smooth()
        except Exception: pass
        # subtle displacement from heightmap
        if os.path.exists(HEIGHT):
            try:
                t=bpy.data.textures.new("HeightTex",'IMAGE'); t.image=bpy.data.images.load(HEIGHT)
                d=o.modifiers.new("Disp","DISPLACE"); d.texture=t; d.strength=0.04; d.mid_level=0.5
            except Exception: pass

# glowing LED cell volume above
cm=glass("M_Cell",(0.05,0.25,1.0),3.0,0.012,0.3)
for j in range(5):
    for i in range(11):
        x=(i-5)*0.34; y=(j-2)*0.34; z=1.2+0.18*math.sin(i*0.6+j*0.5)
        bpy.ops.mesh.primitive_cube_add(size=0.26,location=(x,y,z)); c=bpy.context.object
        bpy.ops.object.modifier_add(type='BEVEL'); c.modifiers[-1].width=0.035; c.modifiers[-1].segments=3
        bpy.ops.object.shade_smooth(); c.data.materials.append(cm)
# tron disc racket (torus + glow)
bpy.ops.mesh.primitive_torus_add(major_radius=0.6,minor_radius=0.04,location=(-2.6,-0.8,0.6)); rk=bpy.context.object; rk.rotation_euler=(math.radians(75),0,0.4)
rk.data.materials.append(glass("M_Racket",(0.1,0.5,1.0),6.0,0.1,0.0,0.0))
# ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2,location=(2.2,0.6,0.4)); ball=bpy.context.object; bpy.ops.object.shade_smooth()
ball.data.materials.append(glass("M_Ball",(0.7,0.95,0.1),1.6,0.3,0.0,0.0))

def area(loc,rot,e,col,sz):
    l=bpy.data.lights.new("L",'AREA'); l.energy=e; l.color=col; l.size=sz
    o=bpy.data.objects.new("L",l); o.location=loc; o.rotation_euler=rot; sc.collection.objects.link(o)
area((-7,-5,9),(math.radians(-50),0,math.radians(-35)),11000,(0.5,0.7,1.0),11)
area((8,5,7),(math.radians(-55),0,math.radians(140)),6000,(0.3,0.55,1.0),9)
area((0,-9,4),(math.radians(-72),0,0),4000,(0.6,0.9,1.0),7)

cd=bpy.data.cameras.new("Cam"); cam=bpy.data.objects.new("Cam",cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(-9,-9,4); look=mathutils.Vector((0,0,0.8))-cam.location; cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
cd.lens=46; cd.dof.use_dof=True; cd.dof.focus_distance=13; cd.dof.aperture_fstop=2.5

# glare post (guarded)
try:
    sc.use_nodes=True; cnt=getattr(sc,'node_tree',None) or getattr(sc,'compositing_node_group',None)
    if cnt:
        cnt.nodes.clear(); rl=cnt.nodes.new("CompositorNodeRLayers"); comp=cnt.nodes.new("CompositorNodeComposite")
        gl=cnt.nodes.new("CompositorNodeGlare"); gl.glare_type='FOG_GLOW'; gl.threshold=0.6
        cnt.links.new(rl.outputs["Image"],gl.inputs["Image"]); cnt.links.new(gl.outputs["Image"],comp.inputs["Image"])
except Exception as e: print("glare skip",e)

sc.render.filepath=os.path.join(OUT,"SPIN_beautiful_court.png"); bpy.ops.render.render(write_still=True)
print("[BEAUTY] rendered ->", sc.render.filepath)
