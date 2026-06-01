"""
build_ue_import_clean.py — cleanly bring the user's REAL files into UE via Interchange.
Imports TennisCourt.glb (-> Nanite static mesh), applies glossy-blue glass (M_CourtGlossy),
assembles L_SPIN_Import with the glass LED volume + HDRIBackdrop + lighting. Vulkan-safe.
Run via bridge run_python_file. Markers 'IMPORT:'.
"""
import unreal, os
EAL=unreal.EditorAssetLibrary; tools=unreal.AssetToolsHelpers.get_asset_tools()
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def log(m): unreal.log_warning("IMPORT: "+m)
PKG="/Game/FinalSolution"
COURT=r"C:/Users/joeyw/OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb"

def imp_mesh(path, dest, nanite=True):
    if not os.path.exists(path): log("MISSING "+path); return None
    t=unreal.AssetImportTask(); t.filename=path; t.destination_path=dest
    t.automated=True; t.save=True; t.replace_existing=True
    tools.import_asset_tasks([t])
    paths=list(t.get_editor_property("imported_object_paths") or [])
    sm=None
    for p in paths:
        a=EAL.load_asset(p)
        if isinstance(a, unreal.StaticMesh):
            sm=a
            if nanite:
                ns=a.get_editor_property("nanite_settings"); ns.set_editor_property("enabled",True)
                a.set_editor_property("nanite_settings",ns); EAL.save_asset(a.get_path_name())
    log("imported %s -> %d assets (mesh=%s)" % (os.path.basename(path), len(paths), bool(sm)))
    return sm

try:
    court=imp_mesh(COURT, PKG+"/Imported/Court", nanite=True)
    cmat=EAL.load_asset(PKG+"/M_CourtGlossy")
    # clean level
    les.new_level(PKG+"/L_SPIN_Import")
    # HDRI backdrop studio env
    bp=EAL.load_asset("/HDRIBackdrop/Blueprints/HDRIBackdrop")
    if bp:
        hb=eas.spawn_actor_from_object(bp, unreal.Vector(0,0,0)); hb.set_actor_label("HDRIBackdrop")
        try: hb.set_editor_property("Cubemap", EAL.load_asset("/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1"))
        except Exception: pass
    # the court
    if court:
        ca=eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0)); ca.set_actor_label("Court")
        smc=ca.get_component_by_class(unreal.StaticMeshComponent); smc.set_static_mesh(court)
        if cmat:
            for i in range(max(1,smc.get_num_materials())): smc.set_material(i,cmat)
        ca.set_actor_scale3d(unreal.Vector(3,3,3))
    # glass LED volume (existing reusable BP)
    gbp=EAL.load_asset(PKG+"/BP_GlassLEDVolume")
    if gbp: eas.spawn_actor_from_object(gbp, unreal.Vector(0,0,400)).set_actor_label("GlassVolume")
    # the reusable arena BP too (brings its own scoreboard/lighting)
    abp=EAL.load_asset(PKG+"/BP_SPIN_Arena")
    if abp: eas.spawn_actor_from_object(abp, unreal.Vector(0,-1200,0)).set_actor_label("SPIN_Arena")
    # key sun
    dl=eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,1500), unreal.Rotator(-40,135,0))
    dl.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(6.0)
    les.save_current_level()
    log("ALL DONE -> /Game/FinalSolution/L_SPIN_Import (real court + glass + arena + HDRI)")
except Exception as e:
    import traceback; log("FAILED "+str(e)); unreal.log_error(traceback.format_exc())
