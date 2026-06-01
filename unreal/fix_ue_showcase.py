"""
fix_ue_showcase.py — fix the black viewport + make glass read.
Root cause (from editor warning): multiple competing DirectionalLights break forward-shading
translucency. Fix: single sun, real-time sky-light capture (reflections!), sane auto-exposure.
Run via bridge run_python_file. Markers 'UEFIX:'.
"""
import unreal
def log(m): unreal.log_warning("UEFIX: " + m)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = eas.get_all_level_actors()

# 1. one directional light only, make it the atmosphere sun
dls = [a for a in actors if isinstance(a, unreal.DirectionalLight)]
for extra in dls[1:]:
    eas.destroy_actor(extra)
if dls:
    dl = dls[0]
    dl.set_actor_rotation(unreal.Rotator(-35, 130, 0), False)
    c = dl.get_component_by_class(unreal.DirectionalLightComponent)
    c.set_intensity(6.0)
    try: c.set_light_color(unreal.LinearColor(0.85, 0.9, 1.0, 1.0))
    except Exception: pass
    for prop, val in [("atmosphere_sun_light", True), ("forward_shading_priority", 0),
                      ("used_as_atmosphere_sun_light", True)]:
        try: c.set_editor_property(prop, val)
        except Exception: pass

# 2. sky light: real-time capture of the atmosphere -> reflections on the glass
sls = [a for a in actors if isinstance(a, unreal.SkyLight)]
if sls:
    sc = sls[0].get_component_by_class(unreal.SkyLightComponent)
    for prop, val in [("real_time_capture", True), ("intensity", 2.5),
                      ("source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)]:
        try: sc.set_editor_property(prop, val)
        except Exception: pass
    try: sc.recapture_sky()
    except Exception: pass

# 3. sane auto-exposure + tasteful bloom
for a in actors:
    if isinstance(a, unreal.PostProcessVolume):
        s = a.get_editor_property("settings")
        s.set_editor_property("override_auto_exposure_method", True)
        s.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM)
        for prop, val in [("override_auto_exposure_min_brightness", True),
                          ("auto_exposure_min_brightness", 0.4),
                          ("override_auto_exposure_max_brightness", True),
                          ("auto_exposure_max_brightness", 1.6),
                          ("override_bloom_intensity", True), ("bloom_intensity", 0.85),
                          ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0)]:
            try: s.set_editor_property(prop, val)
            except Exception: pass
        a.set_editor_property("settings", s)

unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("scene fixed: single sun + realtime skylight + histogram exposure")
