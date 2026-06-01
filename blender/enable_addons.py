"""enable_addons.py — enable the key built-in Blender add-ons for the SPIN pipeline."""
import bpy
addons = [
    "node_wrangler",                 # material node speed-ups
    "io_import_images_as_planes",     # reference images / LED frames as planes
    "add_mesh_extra_objects",         # extra primitives
    "io_anim_camera",                 # camera import/export
    "materials_utils",                # material library utils
    "io_scene_gltf2",                 # glTF (web/AR)
    "io_scene_fbx",                   # FBX (your racket etc.)
]
ok, miss = [], []
for a in addons:
    try:
        bpy.ops.preferences.addon_enable(module=a); ok.append(a)
    except Exception as e:
        # 4.2+ extension module path
        try:
            bpy.ops.preferences.addon_enable(module="bl_ext.blender_org."+a); ok.append(a+"(ext)")
        except Exception: miss.append(a)
try: bpy.ops.wm.save_userpref()
except Exception as e: print("save pref:", e)
print("[ADDONS] enabled:", ok)
print("[ADDONS] missing:", miss)
