"""
build_ue_spin_level.py — assemble a playable showcase LEVEL from EXISTING game assets
+ lights + post + camera + the glass LED volume. Uses what's already in the project.
Run via bridge run_python_file. Markers 'SPINLVL:'.
"""
import unreal
EAL=unreal.EditorAssetLibrary; eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def log(m): unreal.log_warning("SPINLVL: "+m)

les.new_level("/Game/FinalSolution/L_SPIN_Showcase")

def spawn_obj(path, loc, rot=(0,0,0), scale=(1,1,1), label=None):
    a=EAL.load_asset(path)
    if not a: log("MISSING "+path); return None
    act=eas.spawn_actor_from_object(a, unreal.Vector(*loc), unreal.Rotator(*rot))
    if act:
        act.set_actor_scale3d(unreal.Vector(*scale))
        if label: act.set_actor_label(label)
    return act

def spawn_cls(cls, loc=(0,0,0), rot=(0,0,0), label=None):
    a=eas.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
    if a and label: a.set_actor_label(label)
    return a

# --- existing game assets ---
spawn_obj("/Game/GlassSphere/Meshes/SM_StadiumCourt", (0,0,0), label="Court")
spawn_obj("/Game/Quadcopters/Blueprints/BP_Quadcopter_A", (0,0,400), label="Quadcopter")
spawn_obj("/Game/Racket", (250,0,120), rot=(0,0,30), label="Racket")
# the glass LED volume
spawn_obj("/Game/FinalSolution/BP_GlassLEDVolume", (-400,0,300), label="GlassLEDVolume")

# --- lighting: directional sun + sky + skylight(HDRI) + fog ---
dl=spawn_cls(unreal.DirectionalLight, (0,0,1500), (-42,135,0), "Sun")
c=dl.get_component_by_class(unreal.DirectionalLightComponent)
c.set_intensity(8.0)
try:
    c.set_editor_property("used_as_atmosphere_sun_light", True)
    c.set_editor_property("light_source_angle", 1.0)
except Exception: pass
spawn_cls(unreal.SkyAtmosphere, (0,0,0), label="SkyAtmosphere")
sl=spawn_cls(unreal.SkyLight, (0,0,800), label="SkyLight")
sc=sl.get_component_by_class(unreal.SkyLightComponent)
try:
    hdri=EAL.load_asset("/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1")
    sc.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sc.set_editor_property("cubemap", hdri); sc.set_editor_property("intensity", 2.0); sc.recapture_sky()
except Exception: pass
spawn_cls(unreal.ExponentialHeightFog, (0,0,0), label="Fog")
# a hero spotlight on the volume
sp=spawn_cls(unreal.SpotLight, (-400,-300,800), (-55,45,0), "HeroSpot")
spc=sp.get_component_by_class(unreal.SpotLightComponent)
try: spc.set_intensity(50000.0); spc.set_light_color(unreal.LinearColor(0.6,0.8,1.0,1))
except Exception: pass

# --- post process (cinematic) ---
ppv=spawn_cls(unreal.PostProcessVolume, (0,0,300), label="PostProcess")
ppv.set_editor_property("unbound", True)
s=ppv.get_editor_property("settings")
for p,v in [("override_bloom_intensity",True),("bloom_intensity",1.0),
            ("override_auto_exposure_method",True),("auto_exposure_method",unreal.AutoExposureMethod.AEM_HISTOGRAM),
            ("override_auto_exposure_min_brightness",True),("auto_exposure_min_brightness",0.4),
            ("override_auto_exposure_max_brightness",True),("auto_exposure_max_brightness",1.5),
            ("override_vignette_intensity",True),("vignette_intensity",0.4)]:
    try: s.set_editor_property(p,v)
    except Exception: pass
ppv.set_editor_property("settings", s)

# --- cine camera ---
cam=spawn_cls(unreal.CineCameraActor, (-1100,-1100,650), (-12,45,0), "HeroCamera")

les.save_current_level()
log("L_SPIN_Showcase built: court+quadcopter+racket+glass + sun/sky/skylight/fog/spot + post + cine cam")
