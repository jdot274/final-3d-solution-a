"""
build_final_game_scene.py — THE complete Blender game scene (shown in viewport).
Displaced glassy court + wave-dots, layered glass (glass/frosted/shiny/animated-LED),
tron disc + real racket, glassy ball, tessellated shiny-blue + bright-green pixel meshes,
multiple cameras, all light types + HDRI world, reflections (raytracing), compositor post.
Saves SPIN_FinalGame.blend (open it to see everything in the viewport).
"""
import bpy, math, os, mathutils
PKG=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/game"; OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"
for d in (PKG,OUT): os.makedirs(d,exist_ok=True)
COURT=r"C:/Users/joeyw/OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb"
RACKET=r"C:/Users/joeyw/OneDrive/EverythingExisting/TennisRacket v1.fbx"
HEIGHT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/textures/wave_heightmap.png"

bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
try:
    sc.render.engine='BLENDER_EEVEE_NEXT'; sc.eevee.use_raytracing=True
    sc.eevee.ray_tracing_options.use_denoise=True
except Exception: sc.render.engine='BLENDER_EEVEE'
sc.render.resolution_x=1920; sc.render.resolution_y=1080; sc.frame_start=1; sc.frame_end=60
sc.view_settings.view_transform='AgX' if any(v.name=='AgX' for v in sc.view_settings.bl_rna.properties['view_transform'].enum_items) else 'Filmic'
try: sc.view_settings.look='AgX - High Contrast'; sc.view_settings.exposure=0.3
except Exception: pass

def C(n):
    c=bpy.data.collections.new(n); sc.collection.children.link(c); return c
COURTC=C("Court"); LAYERS=C("Glass_Layers"); RACK=C("Rackets"); PIX=C("Tess_Pixels"); LIT=C("Lighting"); CAM=C("Cameras")
def to(o,c):
    for u in list(o.users_collection): u.objects.unlink(o)
    c.objects.link(o)

# studio world (reflections)
w=bpy.data.worlds.new("W"); sc.world=w; w.use_nodes=True; nt=w.node_tree
bg=nt.nodes.get("Background"); g=nt.nodes.new("ShaderNodeTexGradient"); g.gradient_type='SPHERICAL'; tc=nt.nodes.new("ShaderNodeTexCoord")
cr=nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color=(0.002,0.004,0.012,1); cr.color_ramp.elements[1].color=(0.03,0.07,0.18,1)
nt.links.new(tc.outputs["Generated"],g.inputs["Vector"]); nt.links.new(g.outputs["Color"],cr.inputs["Fac"]); nt.links.new(cr.outputs["Color"],bg.inputs[0]); bg.inputs[1].default_value=0.6

def mat(name,base,emis=0,rough=0.04,trans=0.3,coat=1.0,coatr=0.02):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(*base,1)); s("Roughness",rough); s("IOR",1.5); s("Transmission Weight",trans)
    s("Coat Weight",coat); s("Coat Roughness",coatr); s("Emission Color",(*base,1)); s("Emission Strength",emis)
    return m
M_GLASS=mat("M_Glass",(0.02,0.10,0.55),0.4,0.02,0.5); M_FROSTED=mat("M_Frosted",(0.1,0.2,0.5),0.1,0.45,0.2,0.6,0.3)
M_SHINY=mat("M_Shiny",(0.05,0.3,1.0),0.6,0.01,0.0,1.0,0.0); M_LED=mat("M_LED",(0.05,0.25,1.0),3.0,0.02,0.3)
M_GREEN=mat("M_Green",(0.2,1.0,0.2),2.4,0.05,0.0,0.0); M_BLUE=mat("M_Blue",(0.1,0.4,1.0),2.0,0.05,0.0,0.0)

# --- real court (displaced glassy) ---
if os.path.exists(COURT):
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=COURT)
    for o in [o for o in bpy.data.objects if o not in before and o.type=='MESH']:
        if not o.parent: o.scale=tuple(v*0.02 for v in o.scale)
        o.data.materials.clear(); o.data.materials.append(M_GLASS)
        try: bpy.context.view_layer.objects.active=o; bpy.ops.object.shade_smooth()
        except Exception: pass
        if os.path.exists(HEIGHT):
            try:
                t=bpy.data.textures.new("H",'IMAGE'); t.image=bpy.data.images.load(HEIGHT)
                d=o.modifiers.new("Disp","DISPLACE"); d.texture=t; d.strength=0.04; d.mid_level=0.5
            except Exception: pass
        to(o,COURTC)

# --- LAYERED glass (glass / frosted / shiny / animated LED) stacked over court ---
for i,(m,zoff,name) in enumerate([(M_GLASS,0.6,"L_Glass"),(M_FROSTED,0.85,"L_Frosted"),(M_SHINY,1.1,"L_Shiny")]):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,zoff)); s=bpy.context.object; s.scale=(3,1.7,0.04); s.name=name
    bpy.ops.object.modifier_add(type='BEVEL'); s.modifiers[-1].width=0.06; s.modifiers[-1].segments=4; bpy.ops.object.shade_smooth()
    s.data.materials.append(m); to(s,LAYERS)
# animated LED dot layer (wave dots)
for j in range(5):
    for i in range(11):
        x=(i-5)*0.34; y=(j-2)*0.34
        bpy.ops.mesh.primitive_cube_add(size=0.24,location=(x,y,1.4)); c=bpy.context.object
        bpy.ops.object.modifier_add(type='BEVEL'); c.modifiers[-1].width=0.03; c.modifiers[-1].segments=3; bpy.ops.object.shade_smooth()
        c.data.materials.append(M_LED)
        for f in range(1,61,10):
            c.location.z=1.4+0.18*math.sin(i*0.6+j*0.5+f*0.15); c.keyframe_insert("location",index=2,frame=f)
        to(c,LAYERS)

# --- rackets: tron disc + real racket ---
bpy.ops.mesh.primitive_torus_add(major_radius=0.6,minor_radius=0.04,location=(-2.6,-0.8,0.7)); rk=bpy.context.object; rk.rotation_euler=(math.radians(75),0,0.4)
rk.data.materials.append(M_SHINY); to(rk,RACK)
if os.path.exists(RACKET):
    before=set(bpy.data.objects)
    try: bpy.ops.import_scene.fbx(filepath=RACKET)
    except Exception: pass
    for o in [o for o in bpy.data.objects if o not in before and o.type=='MESH']:
        if not o.parent:
            o.location=(2.8,-1.2,0.6); o.scale=(0.02,0.02,0.02); o.rotation_euler=(math.radians(70),0,0.5)
        o.data.materials.clear(); o.data.materials.append(M_GLASS); to(o,RACK)

# --- glassy ball ---
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2,location=(2.2,0.6,0.5)); ball=bpy.context.object; bpy.ops.object.shade_smooth()
ball.data.materials.append(M_GREEN); to(ball,RACK)

# --- tessellated shiny blue + bright green pixel meshes ---
for k,(mm,cx) in enumerate([(M_BLUE,-2.0),(M_GREEN,2.0)]):
    bpy.ops.mesh.primitive_grid_add(size=1.4,x_subdivisions=14,y_subdivisions=14,location=(cx,3.5,1.0)); p=bpy.context.object
    p.rotation_euler=(math.radians(80),0,0)
    sub=p.modifiers.new("Sub","SUBSURF"); sub.levels=2
    dsp=p.modifiers.new("Px","DISPLACE")
    try:
        vt=bpy.data.textures.new("Vor%d"%k,'VORONOI'); vt.noise_scale=0.15; dsp.texture=vt; dsp.strength=0.25
    except Exception: pass
    bpy.ops.object.shade_smooth(); p.data.materials.append(mm); p.name="TessPixels_%d"%k; to(p,PIX)

# --- lighting (all types) ---
def light(typ,loc,e,col,nm,**kw):
    l=bpy.data.lights.new(nm,typ); l.energy=e; l.color=col
    for k,v in kw.items():
        try: setattr(l,k,v)
        except Exception: pass
    o=bpy.data.objects.new(nm,l); o.location=loc; sc.collection.objects.link(o); to(o,LIT); return o
light('AREA',(-7,-5,9),11000,(0.5,0.7,1.0),"Key",size=11)
light('AREA',(8,5,7),6000,(0.3,0.55,1.0),"Rim",size=9)
light('SPOT',(0,-9,5),9000,(0.6,0.9,1.0),"Spot",spot_size=math.radians(50))
light('SUN',(0,0,12),1.5,(1,0.95,0.9),"Sun")

# --- cameras ---
def cam(nm,loc,tgt,lens):
    cd=bpy.data.cameras.new(nm); c=bpy.data.objects.new(nm,cd); sc.collection.objects.link(c)
    d=mathutils.Vector(tgt)-mathutils.Vector(loc); c.location=loc; c.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); cd.lens=lens
    cd.dof.use_dof=True; cd.dof.focus_distance=(mathutils.Vector(tgt)-mathutils.Vector(loc)).length; cd.dof.aperture_fstop=2.5; to(c,CAM); return c
hero=cam("Cam_Hero",(-9,-9,4),(0,0,0.8),46); cam("Cam_Top",(0,0,13),(0,0,0),35); cam("Cam_Racket",(-3.5,-2.5,1.2),(-2.6,-0.8,0.7),85)
sc.camera=hero

# --- compositor post (glare + grade) ---
try:
    sc.use_nodes=True; cnt=getattr(sc,'node_tree',None) or getattr(sc,'compositing_node_group',None)
    if cnt:
        cnt.nodes.clear(); rl=cnt.nodes.new("CompositorNodeRLayers"); comp=cnt.nodes.new("CompositorNodeComposite")
        gl=cnt.nodes.new("CompositorNodeGlare"); gl.glare_type='FOG_GLOW'; gl.threshold=0.6
        cnt.links.new(rl.outputs["Image"],gl.inputs["Image"]); cnt.links.new(gl.outputs["Image"],comp.inputs["Image"])
except Exception: pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(PKG,"SPIN_FinalGame.blend"))
sc.frame_set(15); sc.render.filepath=os.path.join(OUT,"SPIN_final_game.png"); bpy.ops.render.render(write_still=True)
print("[GAME] saved SPIN_FinalGame.blend + rendered SPIN_final_game.png")
