"""
load_master_usd_stage.py — bring in the WHOLE master USD as a live USD Stage (fast,
referenced, not per-mesh import). Sets up a clean level + Lumen + camera + screenshot.
Run via bridge run_python_file. Markers 'USDSTAGE:'.
"""
import unreal
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def log(m): unreal.log_warning("USDSTAGE: "+m)
USD=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/master/all_3d_assets.usd"

try:
    les.new_level("/Game/FinalSolution/L_AllAssets")
    # USD Stage actor references the whole scene live
    stage=None
    for cls in ("/Script/USDStage.UsdStageActor",):
        c=unreal.load_class(None, cls)
        if c: stage=eas.spawn_actor_from_class(c, unreal.Vector(0,0,0)); break
    if stage is None:
        stage=eas.spawn_actor_from_class(unreal.UsdStageActor, unreal.Vector(0,0,0))
    stage.set_actor_label("AllAssets_USD")
    for prop in ("root_layer","RootLayer"):
        try: stage.set_editor_property(prop, unreal.FilePath(USD)); log("set "+prop); break
        except Exception as e: pass
    # lighting: sun + sky + skylight (Lumen GI auto)
    dl=eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,2000), unreal.Rotator(-40,135,0))
    dl.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(6.0)
    eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0,0,0))
    sl=eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0,0,1000))
    try:
        sc=sl.get_component_by_class(unreal.SkyLightComponent); sc.set_editor_property("real_time_capture",True); sc.recapture_sky()
    except Exception: pass
    # post (Lumen GI is default; add bloom/exposure)
    ppv=eas.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0,0,300)); ppv.set_editor_property("unbound",True)
    s=ppv.get_editor_property("settings")
    for p,v in [("override_bloom_intensity",True),("bloom_intensity",0.8),
                ("override_dynamic_global_illumination_method",True),
                ("dynamic_global_illumination_method",unreal.DynamicGlobalIlluminationMethod.LUMEN),
                ("override_reflection_method",True),("reflection_method",unreal.ReflectionMethod.LUMEN)]:
        try: s.set_editor_property(p,v)
        except Exception: pass
    ppv.set_editor_property("settings",s)
    cam=eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(-3000,-3000,1500), unreal.Rotator(-18,45,0)); cam.set_actor_label("HeroCamera")
    les.save_current_level()
    ues=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    try: ues.set_level_viewport_camera_info(unreal.Vector(-3000,-3000,1500), unreal.Rotator(-18,45,0))
    except Exception: pass
    unreal.AutomationLibrary.take_high_res_screenshot(1600,900,"C:/Users/joeyw/Desktop/final-3d-solution-a/renders/ue_all_assets.png")
    log("ALL DONE -> L_AllAssets with master USD stage + Lumen + camera (screenshot requested)")
except Exception as e:
    import traceback; log("FAILED "+str(e)); unreal.log_error(traceback.format_exc())
