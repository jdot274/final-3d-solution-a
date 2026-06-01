"""export_master_usd.py — open all_3d_assets.blend, export ONE master USD + GLB for UE/web.
Run: blender --background "<all_3d_assets.blend>" --python export_master_usd.py
"""
import bpy, os
OUT=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/master"; os.makedirs(OUT,exist_ok=True)
n_obj=len([o for o in bpy.data.objects if o.type=='MESH'])
print("[MASTER] mesh objects in file:", n_obj)
res={}
try:
    p=os.path.join(OUT,"all_3d_assets.usd")
    bpy.ops.wm.usd_export(filepath=p, export_materials=True, selected_objects_only=False)
    res["usd"]=os.path.getsize(p)
except Exception as e: res["usd"]=f"ERR {e}"
print("[MASTER] export:", res)
print("[MASTER] DONE ->", OUT)
