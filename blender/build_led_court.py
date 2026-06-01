"""
build_led_court.py — LED-SCREEN court: top emissive video layer with PULSING cube sections
+ bottom backlighting so it glows like an LED panel. Glass court base, animated, rendered.
Saves SPIN_LEDCourt.blend + renders a frame. Run: blender --background --python this.py
"""
import bpy, math, os, mathutils
PKG=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/game"; OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"
for d in (PKG,OUT): os.makedirs(d,exist_ok=True)
FLIP=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/textures/wave_flipbook.png"

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try: sc.render.engine='BLENDER_EEVEE_NEXT'; sc.eevee.use_raytracing=True; sc.eevee.ray_tracing_options.use_denoise=True
except Exception: sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1920; sc.render.resolution_y=1080; sc.frame_start=1; sc.frame_end=60
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
try: sc.view_settings.look='AgX - High Contrast'; sc.view_settings.exposure=0.2
except Exception: pass
world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True
world.node_tree.nodes.get("Background").inputs[0].default_value=(0.002,0.004,0.01,1); world.node_tree.nodes.get("Background").inputs[1].default_value=0.2

COURT_X, COURT_Y = 6.0, 3.2

# ---- glass court frame (clear, so the LED reads through) ----
def glass(name,base,emis,rough,trans,coat=1.0):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(*base,1)); s("Roughness",rough); s("IOR",1.5); s("Transmission Weight",trans); s("Coat Weight",coat); s("Coat Roughness",0.02)
    s("Emission Color",(*base,1)); s("Emission Strength",emis); return m
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,-0.05)); frame=bpy.context.object; frame.scale=(COURT_X/2+0.1,COURT_Y/2+0.1,0.08); frame.name="CourtGlass"
bpy.ops.object.modifier_add(type='BEVEL'); frame.modifiers[-1].width=0.06; frame.modifiers[-1].segments=4; bpy.ops.object.shade_smooth()
frame.data.materials.append(glass("M_CourtGlass",(0.02,0.10,0.5),0.0,0.04,0.25))

# ---- TOP LED SCREEN: grid of pulsing cube sections (the video layer) ----
SX, SY = 12, 6   # cube sections
parent=bpy.data.objects.new("LEDScreen", None); sc.collection.objects.link(parent)
for j in range(SY):
    for i in range(SX):
        x=(i-(SX-1)/2)*(COURT_X/SX); y=(j-(SY-1)/2)*(COURT_Y/SY)
        bpy.ops.mesh.primitive_cube_add(size=min(COURT_X/SX,COURT_Y/SY)*0.92, location=(x,y,0.05))
        c=bpy.context.object; c.scale=(1,1,0.12); c.name="LED_%d_%d"%(i,j); c.parent=parent
        m=bpy.data.materials.new("M_LED_%d_%d"%(i,j)); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
        # hue varies by position (video-wall look)
        h=(i/SX); col=(0.05+0.5*abs(math.sin(h*3.14)), 0.2+0.4*abs(math.sin(h*3.14+1)), 1.0)
        b.inputs["Base Color"].default_value=(0,0,0,1)
        if "Emission Color" in b.inputs: b.inputs["Emission Color"].default_value=(*col,1)
        c.data.materials.append(m)
        # PULSE: animate emission strength with phase offset per section
        es=b.inputs.get("Emission Strength")
        if es:
            phase=(i*0.5+j*0.9)
            for f in range(1,61,5):
                es.default_value=0.4+3.0*max(0,math.sin(f*0.25+phase))**2
                es.keyframe_insert("default_value",frame=f)

# ---- 4K-ish video texture overlay plane (animated noise -> 'video' feel) ----
bpy.ops.mesh.primitive_plane_add(size=1, location=(0,0,0.13)); vid=bpy.context.object; vid.scale=(COURT_X/2,COURT_Y/2,1); vid.name="VideoLayer"
mv=bpy.data.materials.new("M_Video"); mv.use_nodes=True; nt=mv.node_tree; nt.nodes.clear()
out=nt.nodes.new("ShaderNodeOutputMaterial"); em=nt.nodes.new("ShaderNodeEmission")
img=None
if os.path.exists(FLIP):
    try:
        tex=nt.nodes.new("ShaderNodeTexImage"); tex.image=bpy.data.images.load(FLIP); nt.links.new(tex.outputs["Color"],em.inputs["Color"]); img=tex
    except Exception: pass
if img is None:
    nz=nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value=14; ramp=nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color=(0,0.05,0.3,1); ramp.color_ramp.elements[1].color=(0.1,0.6,1,1)
    nt.links.new(nz.outputs["Fac"],ramp.inputs["Fac"]); nt.links.new(ramp.outputs["Color"],em.inputs["Color"])
em.inputs["Strength"].default_value=2.0
mv.surface_render_method='BLENDED' if hasattr(mv,'surface_render_method') else None
try: mv.blend_method='BLEND'
except Exception: pass
nt.links.new(em.outputs["Emission"],out.inputs["Surface"]); vid.data.materials.append(mv)

# ---- BOTTOM BACKLIGHTING (LED panel glow from below) ----
bpy.ops.mesh.primitive_plane_add(size=1, location=(0,0,-0.25)); back=bpy.context.object; back.scale=(COURT_X/2+0.3,COURT_Y/2+0.3,1); back.name="Backlight"
mb=bpy.data.materials.new("M_Backlight"); mb.use_nodes=True; bb=mb.node_tree.nodes.get("Principled BSDF")
if "Emission Color" in bb.inputs: bb.inputs["Emission Color"].default_value=(0.1,0.4,1.0,1); bb.inputs["Emission Strength"].default_value=6.0
back.data.materials.append(mb)
# upward area lights under the court
for lx in (-2,0,2):
    l=bpy.data.lights.new("Under",'AREA'); l.energy=3000; l.color=(0.2,0.5,1.0); l.size=2.5
    o=bpy.data.objects.new("Under",l); o.location=(lx,0,-0.6); o.rotation_euler=(0,0,0); sc.collection.objects.link(o)

# ---- key/rim lighting + camera ----
def area(loc,rot,e,col,sz):
    l=bpy.data.lights.new("L",'AREA'); l.energy=e; l.color=col; l.size=sz
    o=bpy.data.objects.new("L",l); o.location=loc; o.rotation_euler=rot; sc.collection.objects.link(o)
area((-6,-5,8),(math.radians(-50),0,math.radians(-35)),5000,(0.5,0.7,1.0),9)
area((7,5,6),(math.radians(-55),0,math.radians(140)),3000,(0.3,0.55,1.0),7)
cd=bpy.data.cameras.new("Cam"); cam=bpy.data.objects.new("Cam",cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(-7,-7,3.2); look=mathutils.Vector((0,0,0.1))-cam.location; cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler(); cd.lens=42
cd.dof.use_dof=True; cd.dof.focus_distance=10; cd.dof.aperture_fstop=2.8

# glare post
try:
    sc.use_nodes=True; cnt=getattr(sc,'node_tree',None) or getattr(sc,'compositing_node_group',None)
    if cnt:
        cnt.nodes.clear(); rl=cnt.nodes.new("CompositorNodeRLayers"); comp=cnt.nodes.new("CompositorNodeComposite"); gl=cnt.nodes.new("CompositorNodeGlare"); gl.glare_type='FOG_GLOW'; gl.threshold=0.5
        cnt.links.new(rl.outputs["Image"],gl.inputs["Image"]); cnt.links.new(gl.outputs["Image"],comp.inputs["Image"])
except Exception: pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PKG,"SPIN_LEDCourt.blend"))
sc.frame_set(18); sc.render.filepath=os.path.join(OUT,"SPIN_led_court.png"); bpy.ops.render.render(write_still=True)
print("[LED] saved SPIN_LEDCourt.blend + rendered SPIN_led_court.png")
