"""
build_ue_showcase.py — clean AAA showcase level for the glass volume.
Creates /Game/FinalSolution/L_Showcase with cool key light, sky light, atmosphere,
a bloom/exposure post-process, the BP volume framed. Fixes the 'looks bad' lighting.
Run via bridge run_python_file. Markers 'UESHOW:'.
"""
import unreal
def log(m): unreal.log_warning("UESHOW: " + m)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

les.new_level("/Game/FinalSolution/L_Showcase")

def spawn(cls, loc=(0,0,0), rot=(0,0,0)):
    return eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))

def comp(actor, cls):
    return actor.get_component_by_class(cls)

# cool key light
dl = spawn(unreal.DirectionalLight, (0,0,600), (-40,150,0))
c = comp(dl, unreal.DirectionalLightComponent)
if c:
    c.set_intensity(4.0)
    try: c.set_light_color(unreal.LinearColor(0.70, 0.80, 1.0, 1.0))
    except Exception: pass
# sky light (reflections)
sl = spawn(unreal.SkyLight, (0,0,500))
sc = comp(sl, unreal.SkyLightComponent)
if sc:
    try: sc.set_editor_property("intensity", 1.5)
    except Exception: pass
# atmosphere + a soft fog for depth
spawn(unreal.SkyAtmosphere, (0,0,0))
try: spawn(unreal.ExponentialHeightFog, (0,0,0))
except Exception: pass
# post process: bloom + fixed exposure so the rim glow pops without blowing out
ppv = spawn(unreal.PostProcessVolume, (0,0,200))
ppv.set_editor_property("unbound", True)
s = ppv.get_editor_property("settings")
s.set_editor_property("override_bloom_intensity", True); s.set_editor_property("bloom_intensity", 1.4)
s.set_editor_property("override_auto_exposure_method", True)
s.set_editor_property("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL)
s.set_editor_property("override_auto_exposure_bias", True); s.set_editor_property("auto_exposure_bias", 11.0)
ppv.set_editor_property("settings", s)

# the glass volume
bp = unreal.EditorAssetLibrary.load_asset("/Game/FinalSolution/BP_GlassLEDVolume")
vol = eas.spawn_actor_from_object(bp, unreal.Vector(0,0,300))
vol.set_actor_label("GlassLEDVolume_Showcase")

les.save_current_level()
log("L_Showcase built + saved")
# frame it
unreal.EditorLevelLibrary.editor_set_camera_look_at_location(unreal.Vector(0,0,300))
