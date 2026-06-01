"""
build_asset_library.py — mass categorized Blender Asset Library (content shelf).
Imports the curated SPIN assets, marks them as Assets, assigns catalogs (Courts, Rackets,
Balls, Glass, LED_Volumes, Scenes), saves SPIN_Library.blend. Open Blender Asset Browser,
point it at this folder, and drag categorized assets into any scene.
Run: blender --background --python build_asset_library.py
"""
import bpy, os, uuid
LIB=r"C:/Users/joeyw/Desktop/SPIN_AssetLibrary"; os.makedirs(LIB,exist_ok=True)

# ---- catalogs (blender_assets.cats.txt) ----
cats={"Courts":uuid.uuid4(),"Rackets":uuid.uuid4(),"Balls":uuid.uuid4(),
      "Glass":uuid.uuid4(),"LED_Volumes":uuid.uuid4(),"Scenes":uuid.uuid4()}
with open(os.path.join(LIB,"blender_assets.cats.txt"),"w") as f:
    f.write("VERSION 1\n\n")
    for name,u in cats.items(): f.write("%s:%s:%s\n"%(u,name,name))

ASSETS=[
 (r"C:/Users/joeyw/OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb","Courts","TennisCourt"),
 (r"C:/Users/joeyw/OneDrive/EverythingExisting/TennisRacket v1.fbx","Rackets","TennisRacket_v1"),
 (r"C:/Users/joeyw/OneDrive/EverythingExisting/tennis_ball.glb","Balls","TennisBall"),
 (r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/hero/GlassLED_Slab.glb","Glass","GlassLED_Slab"),
 (r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/unified/UnifiedGlassLED.glb","LED_Volumes","UnifiedGlassLED"),
 (r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/voxel/voxel_wave.glb","LED_Volumes","VoxelWave"),
 (r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/scene/SPIN_Scene.glb","Scenes","SPIN_Scene"),
]

bpy.ops.wm.read_factory_settings(use_empty=True)

def imp(path):
    before=set(bpy.data.objects)
    try:
        if path.lower().endswith((".glb",".gltf")): bpy.ops.import_scene.gltf(filepath=path)
        else: bpy.ops.import_scene.fbx(filepath=path)
    except Exception as e: print("import fail",os.path.basename(path),e); return []
    return [o for o in bpy.data.objects if o not in before]

made=[]
for path,cat,name in ASSETS:
    if not os.path.exists(path): print("MISSING",path); continue
    objs=imp(path); mesh=[o for o in objs if o.type=='MESH']
    if not mesh: continue
    # join into a single object named cleanly, parent-less
    bpy.ops.object.select_all(action='DESELECT')
    for o in mesh: o.select_set(True)
    bpy.context.view_layer.objects.active=mesh[0]
    try:
        if len(mesh)>1: bpy.ops.object.join()
    except Exception: pass
    ob=bpy.context.view_layer.objects.active; ob.name=name
    # mark as asset + catalog + metadata
    ob.asset_mark()
    ad=ob.asset_data; ad.catalog_id=str(cats[cat]); ad.author="Joey Walter (SPIN)"
    ad.description="SPIN %s asset"%cat
    try: ad.tags.new(cat); ad.tags.new("SPIN")
    except Exception: pass
    try: ob.asset_generate_preview()
    except Exception: pass
    made.append((name,cat))

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(LIB,"SPIN_Library.blend"))
print("[LIB] catalogs:",list(cats.keys()))
print("[LIB] assets:",made)
print("[LIB] saved ->",os.path.join(LIB,"SPIN_Library.blend"))
