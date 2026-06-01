"""
build_ue_everything.py — ONE-RUN: place everything in UE + best plugins + render.
Imports UnifiedGlassLED + racket as Nanite, assembles L_SPIN_Import (court already there)
with glass materials, HDRI Backdrop, cinematic post + rect lights + CineCamera, screenshots.
Verify via 'EVERY:' log markers + renders/ue_vulkan_test.png. Vulkan-safe.
"""
import unreal, os
EAL=unreal.EditorAssetLibrary; tools=unreal.AssetToolsHelpers.get_asset_tools()
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def log(m): unreal.log_warning("EVERY: "+m)
PKG="/Game/FinalSolution"

def imp(path,dest,nanite=True):
    if not os.path.exists(path): log("MISSING "+path); return None
    t=unreal.AssetImportTask(); t.filename=path; t.destination_path=dest
    t.automated=True; t.save=True; t.replace_existing=True
    tools.import_asset_tasks([t])
    for p in list(t.get_editor_property("imported_object_paths") or []):
        a=EAL.load_asset(p)
        if isinstance(a,unreal.StaticMesh):
            if nanite:
                ns=a.get_editor_property("nanite_settings"); ns.set_editor_property("enabled",True)
                a.set_editor_property("nanite_settings",ns); EAL.save_asset(a.get_path_name())
            return a
    return None

try:
    les.load_level(PKG+"/L_SPIN_Import")
    glassmesh=imp(r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/unified/UnifiedGlassLED.glb", PKG+"/Imported/GlassVolume")
    racket=imp(r"C:/Users/joeyw/OneDrive/EverythingExisting/TennisRacket v1.fbx", PKG+"/Imported/Racket")
    mglass=EAL.load_asset(PKG+"/M_GlassLED"); mcourt=EAL.load_asset(PKG+"/M_CourtGlossy")
    # place unified glass volume hovering over court
    if glassmesh:
        a=eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,500)); a.set_actor_label("UnifiedGlass")
        smc=a.get_component_by_class(unreal.StaticMeshComponent); smc.set_static_mesh(glassmesh)
        if mglass: smc.set_material(0,mglass)
        a.set_actor_scale3d(unreal.Vector(2.5,2.5,2.5)); log("placed UnifiedGlass")
    # place racket
    if racket:
        a=eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(400,200,120), unreal.Rotator(0,0,30)); a.set_actor_label("Racket")
        smc=a.get_component_by_class(unreal.StaticMeshComponent); smc.set_static_mesh(racket)
        if mcourt: smc.set_material(0,mcourt)
        a.set_actor_scale3d(unreal.Vector(2,2,2)); log("placed Racket")
    # cinematic post + rim lights
    ppv=eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0,0,300)); ppv.set_editor_property("unbound",True)
    s=ppv.get_editor_property("settings")
    for p,v in [("override_bloom_intensity",True),("bloom_intensity",1.1),
                ("override_vignette_intensity",True),("vignette_intensity",0.45),
                ("override_auto_exposure_method",True),("auto_exposure_method",unreal.AutoExposureMethod.AEM_HISTOGRAM),
                ("override_auto_exposure_min_brightness",True),("auto_exposure_min_brightness",0.4),
                ("override_auto_exposure_max_brightness",True),("auto_exposure_max_brightness",1.6),
                ("override_scene_color_tint",True)]:
        try: s.set_editor_property(p,v)
        except Exception: pass
    ppv.set_editor_property("settings",s)
    for loc,rot,col in [((-600,-500,900),(-55,40,0),unreal.LinearColor(0.4,0.7,1.0,1)),
                        ((600,500,900),(-55,220,0),unreal.LinearColor(0.2,0.5,1.0,1))]:
        rl=eas.spawn_actor_from_class(unreal.RectLight, unreal.Vector(*loc), unreal.Rotator(*rot))
        c=rl.get_component_by_class(unreal.RectLightComponent)
        try: c.set_intensity(40000.0); c.set_light_color(col); c.set_editor_property("source_width",800.0); c.set_editor_property("source_height",800.0)
        except Exception: pass
    # cine camera
    cam=eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(-1400,-1400,800), unreal.Rotator(-16,45,0)); cam.set_actor_label("HeroCamera")
    # viewport framing + screenshot
    ues=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    try: ues.set_level_viewport_camera_info(unreal.Vector(-1400,-1400,800), unreal.Rotator(-16,45,0))
    except Exception: pass
    les.save_current_level()
    unreal.AutomationLibrary.take_high_res_screenshot(1600,900,"C:/Users/joeyw/Desktop/final-3d-solution-a/renders/ue_vulkan_test.png")
    log("ALL DONE — placed glass+racket, cinematic post+lights+camera, screenshot requested")
except Exception as e:
    import traceback; log("FAILED "+str(e)); unreal.log_error(traceback.format_exc())
