"""
build_blender_hero.py — cinematic hero render of the glossy-blue glass SPIN scene.
Black void + glossy reflective blue glass court + glass LED cell volume + tennis ball
+ dramatic blue lighting. EEVEE Next (raytraced reflections/refraction). Renders a PNG.
Run: blender --background --python build_blender_hero.py
"""
import bpy, math, os
from mathutils import Vector
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/renders"; os.makedirs(OUT,exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene

# ---- engine: EEVEE Next with raytracing (fast + glassy) ----
try: sc.render.engine='BLENDER_EEVEE_NEXT'
except Exception: sc.render.engine='BLENDER_EEVEE'
try:
    sc.eevee.use_raytracing=True
    sc.eevee.ray_tracing_options.use_denoise=True
except Exception: pass
sc.render.resolution_x=1600; sc.render.resolution_y=900
sc.render.film_transparent=False
sc.view_settings.view_transform='AgX' if 'AgX' in [v.name for v in bpy.data.scenes[0].view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
sc.view_settings.look='None'

# dark world with a faint blue tint
world=bpy.data.worlds.new("W"); sc.world=world; world.use_nodes=True
bg=world.node_tree.nodes.get("Background"); bg.inputs[0].default_value=(0.004,0.008,0.02,1); bg.inputs[1].default_value=0.3

def glass_mat(name, base, emis=0.0, rough=0.04, trans=0.5):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes.get("Principled BSDF")
    def s(n,v):
        if n in b.inputs: b.inputs[n].default_value=v
    s("Base Color",(*base,1)); s("Roughness",rough); s("Metallic",0.0); s("IOR",1.5)
    s("Transmission Weight",trans); s("Coat Weight",0.8); s("Coat Roughness",0.02)
    s("Emission Color",(*base,1)); s("Emission Strength",emis)
    return m

# ---- glossy blue glass court (rounded slab) ----
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0))
court=bpy.context.object; court.scale=(6,3.2,0.18); court.name="Court"
bpy.ops.object.modifier_add(type='BEVEL'); court.modifiers[-1].width=0.12; court.modifiers[-1].segments=4
bpy.ops.object.shade_smooth()
court.data.materials.append(glass_mat("M_Court",(0.02,0.10,0.55),emis=0.6,rough=0.03,trans=0.15))
# court neon center line + edges (emissive)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.10)); line=bpy.context.object; line.scale=(6,0.04,0.02)
line.data.materials.append(glass_mat("M_Line",(0.2,0.6,1.0),emis=8.0,rough=0.2,trans=0.0))

# ---- glass LED cell volume (grid of glass cubes hovering) ----
cells=bpy.data.collections.new("Cells"); bpy.context.scene.collection.children.link(cells)
cm=glass_mat("M_Cell",(0.04,0.22,0.9),emis=2.0,rough=0.03,trans=0.4)
N=9
for j in range(5):
    for i in range(N):
        x=(i-(N-1)/2)*0.34; y=(j-2)*0.34
        z=0.9+0.18*math.sin(i*0.7+j*0.5)
        bpy.ops.mesh.primitive_cube_add(size=0.24, location=(x,y,z))
        c=bpy.context.object; c.rotation_euler=(0,0,0.2)
        bpy.ops.object.modifier_add(type='BEVEL'); c.modifiers[-1].width=0.03; c.modifiers[-1].segments=3
        bpy.ops.object.shade_smooth(); c.data.materials.append(cm)
        for col in list(c.users_collection): col.objects.unlink(c)
        cells.objects.link(c)

# ---- tennis ball (SPIN) ----
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(2.2,0.6,0.45)); ball=bpy.context.object
bpy.ops.object.shade_smooth()
bm=bpy.data.materials.new("M_Ball"); bm.use_nodes=True; bb=bm.node_tree.nodes.get("Principled BSDF")
bb.inputs["Base Color"].default_value=(0.7,0.95,0.1,1); bb.inputs["Roughness"].default_value=0.4
bb.inputs["Emission Color"].default_value=(0.6,0.9,0.1,1); bb.inputs["Emission Strength"].default_value=1.2
ball.data.materials.append(bm)

# ---- dramatic blue lighting (travels the look) ----
def area(loc,rot,energy,color,size):
    l=bpy.data.lights.new("L",'AREA'); l.energy=energy; l.color=color; l.size=size
    o=bpy.data.objects.new("L",l); o.location=loc; o.rotation_euler=rot; bpy.context.scene.collection.objects.link(o)
area((-4,-3,5),(math.radians(-50),0,math.radians(-35)),3000,(0.5,0.7,1.0),6)
area((4,3,4),(math.radians(-55),0,math.radians(140)),1800,(0.3,0.5,1.0),5)
area((0,-5,2),(math.radians(-70),0,0),1200,(0.6,0.9,1.0),4)

# ---- camera (low cinematic) ----
cam_d=bpy.data.cameras.new("Cam"); cam=bpy.data.objects.new("Cam",cam_d)
bpy.context.scene.collection.objects.link(cam); sc.camera=cam
cam.location=(-6.5,-6.5,3.2);
import mathutils
look=mathutils.Vector((0,0,0.6))-cam.location
cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler()
cam_d.lens=42

sc.render.filepath=os.path.join(OUT,"SPIN_hero.png")
bpy.ops.render.render(write_still=True)
print("[HERO] rendered ->", sc.render.filepath)
