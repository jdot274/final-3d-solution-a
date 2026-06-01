"""
build_ue_final_aaa.py — steps 1-3 of the AAA vision (no Substrate; translucent glass).
1. Import wave_heightmap/normalmap/flipbook PNGs into /Game/FinalSolution/Textures
2. Rebuild M_GlassLED: translucent fresnel glass + animated LED TEXTURE emissive ("show anything")
   + heightmap-driven WPO displacement + normalmap tangent detail
3. Hero lighting: brighter sun, realtime sky reflections, bloom, exposure
Run via bridge run_python_file. Markers 'UEAAA:'.
"""
import unreal, os
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
def log(m): unreal.log_warning("UEAAA: " + m)

TEXROOT = "C:/Users/joeyw/Desktop/final-3d-solution-a/assets/textures"
TDEST = "/Game/FinalSolution/Textures"

def imp(fn, name, srgb, normal=False):
    task = unreal.AssetImportTask()
    task.filename = os.path.join(TEXROOT, fn); task.destination_path = TDEST
    task.destination_name = name; task.automated = True; task.save = True; task.replace_existing = True
    tools.import_asset_tasks([task])
    a = EAL.load_asset(TDEST + "/" + name)
    if a:
        try:
            a.set_editor_property("srgb", srgb)
            if normal: a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            EAL.save_asset(a.get_path_name())
        except Exception: pass
    return a

flip = imp("wave_flipbook.png", "T_LED_Flipbook", True)
hght = imp("wave_heightmap.png", "T_Wave_Height", False)
nrml = imp("wave_normalmap.png", "T_Wave_Normal", False, normal=True)
log("textures imported")

# ---- rebuild material ----
mpc = EAL.load_asset("/Game/FinalSolution/MPC_GlassLED")
mat = EAL.load_asset("/Game/FinalSolution/M_GlassLED")
MEL.delete_all_material_expressions(mat)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
for _m in ("TLM_SURFACE_PER_PIXEL_LIGHTING","TLM_SURFACE"):
    v=getattr(unreal.TranslucencyLightingMode,_m,None)
    if v is not None: mat.set_editor_property("translucency_lighting_mode", v); break
mat.set_editor_property("two_sided", True)

def E(cls,x,y): return MEL.create_material_expression(mat,cls,x,y)
def C(x,y,r): n=E(unreal.MaterialExpressionConstant,x,y); n.set_editor_property("r",r); return n
def CP(name,x,y): n=E(unreal.MaterialExpressionCollectionParameter,x,y); n.set_editor_property("collection",mpc); n.set_editor_property("parameter_name",name); return n
def MUL(a,b,x,y): n=E(unreal.MaterialExpressionMultiply,x,y); MEL.connect_material_expressions(a,"",n,"A"); MEL.connect_material_expressions(b,"",n,"B"); return n
def ADD(a,b,x,y): n=E(unreal.MaterialExpressionAdd,x,y); MEL.connect_material_expressions(a,"",n,"A"); MEL.connect_material_expressions(b,"",n,"B"); return n

col=CP("BaseColor",-1900,300); emi=CP("EmissiveStrength",-1900,420)
amp=CP("WaveAmplitude",-1900,-200); frq=CP("WaveFrequency",-1900,-120)
spd=CP("WaveSpeed",-1900,-40);     dsp=CP("Displacement",-1900,40)

# Animated LED TEXTURE (param so any image / video render-target swaps in)
uv=E(unreal.MaterialExpressionTextureCoordinate,-1500,560)
pan=E(unreal.MaterialExpressionPanner,-1300,560); pan.set_editor_property("speed_x",0.05); pan.set_editor_property("speed_y",0.03)
MEL.connect_material_expressions(uv,"",pan,"Coordinate")
ledtex=E(unreal.MaterialExpressionTextureSampleParameter2D,-1050,560)
ledtex.set_editor_property("parameter_name","LEDTexture")
if flip: ledtex.set_editor_property("texture",flip)
MEL.connect_material_expressions(pan,"",ledtex,"UVs")

# Fresnel rim
fres=E(unreal.MaterialExpressionFresnel,-1200,150); fres.set_editor_property("exponent",4.0); fres.set_editor_property("base_reflect_fraction",0.04)

# Base color, spec, rough
MEL.connect_material_property(col,"",unreal.MaterialProperty.MP_BASE_COLOR)
MEL.connect_material_property(C(-300,640,0.04),"",unreal.MaterialProperty.MP_ROUGHNESS)
MEL.connect_material_property(C(-300,710,1.0),"",unreal.MaterialProperty.MP_SPECULAR)

# Normal detail (tangent)
norm=E(unreal.MaterialExpressionTextureSampleParameter2D,-700,800)
norm.set_editor_property("parameter_name","DetailNormal")
if nrml:
    norm.set_editor_property("texture",nrml)
    try: norm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    except Exception: pass
MEL.connect_material_expressions(uv,"",norm,"UVs")
MEL.connect_material_property(norm,"",unreal.MaterialProperty.MP_NORMAL)

# Opacity = lerp(0.07, 0.7, fresnel)
lerp=E(unreal.MaterialExpressionLinearInterpolate,-500,330)
MEL.connect_material_expressions(C(-700,300,0.07),"",lerp,"A"); MEL.connect_material_expressions(C(-700,360,0.7),"",lerp,"B")
MEL.connect_material_expressions(fres,"",lerp,"Alpha")
MEL.connect_material_property(lerp,"",unreal.MaterialProperty.MP_OPACITY)
MEL.connect_material_property(C(-300,790,1.5),"",unreal.MaterialProperty.MP_REFRACTION)

# Emissive = LEDtexture * color * strength * (fresnel rim + 0.4 base)  -> "shows anything", glows
rimbias=ADD(fres,C(-1050,250,0.4),-900,180)
e1=MUL(ledtex,col,-820,470); e2=MUL(e1,emi,-650,470); em=MUL(e2,rimbias,-480,420)
MEL.connect_material_property(em,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)

# WPO = normal * ( sin(worldpos.xy*freq + time*speed)*amp  +  heightmap*disp ) * 0.05
t=E(unreal.MaterialExpressionTime,-1700,-260); tw=MUL(t,spd,-1500,-240)
wp=E(unreal.MaterialExpressionWorldPosition,-1700,-120)
cv=E(unreal.MaterialExpressionConstant3Vector,-1700,-40); cv.set_editor_property("constant",unreal.LinearColor(1,1,0,0))
dot=E(unreal.MaterialExpressionDotProduct,-1500,-100); MEL.connect_material_expressions(wp,"",dot,"A"); MEL.connect_material_expressions(cv,"",dot,"B")
ph=ADD(MUL(dot,frq,-1300,-100),tw,-1150,-160)
s=E(unreal.MaterialExpressionSine,-1000,-160); MEL.connect_material_expressions(ph,"",s,"")
wave=MUL(s,amp,-820,-130)
# heightmap displacement
hpan=E(unreal.MaterialExpressionPanner,-1300,80); hpan.set_editor_property("speed_x",0.02)
MEL.connect_material_expressions(uv,"",hpan,"Coordinate")
htex=E(unreal.MaterialExpressionTextureSampleParameter2D,-1050,80); htex.set_editor_property("parameter_name","HeightTexture")
if hght: htex.set_editor_property("texture",hght)
MEL.connect_material_expressions(hpan,"",htex,"UVs")
hd=MUL(htex,dsp,-820,40)
disp=ADD(wave,hd,-650,-40)
amtt=MUL(disp,C(-650,90,0.05),-480,-10)
nrmw=E(unreal.MaterialExpressionVertexNormalWS,-650,160)
wpo=MUL(nrmw,amtt,-300,60)
MEL.connect_material_property(wpo,"",unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

MEL.recompile_material(mat); EAL.save_asset(mat.get_path_name())
log("M_GlassLED rebuilt: animated LED texture + heightmap WPO + normal + glass")

# ---- hero lighting ----
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if isinstance(a, unreal.DirectionalLight):
        a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(12.0)
    if isinstance(a, unreal.SkyLight):
        sc=a.get_component_by_class(unreal.SkyLightComponent)
        try: sc.set_editor_property("real_time_capture",True); sc.set_editor_property("intensity",3.0); sc.recapture_sky()
        except Exception: pass
    if isinstance(a, unreal.PostProcessVolume):
        s=a.get_editor_property("settings")
        for p,v in [("override_bloom_intensity",True),("bloom_intensity",1.4),
                    ("override_bloom_threshold",True),("bloom_threshold",-1.0),
                    ("override_auto_exposure_min_brightness",True),("auto_exposure_min_brightness",0.5),
                    ("override_auto_exposure_max_brightness",True),("auto_exposure_max_brightness",1.4)]:
            try: s.set_editor_property(p,v)
            except Exception: pass
        a.set_editor_property("settings",s)
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
log("hero lighting set ALL DONE")
