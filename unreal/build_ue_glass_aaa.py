"""
build_ue_glass_aaa.py — rebuild M_GlassLED IN PLACE as AAA translucent glass.

Translucent + Surface ForwardShading (best glass lighting), refraction (IOR 1.5),
deep blue, low-roughness spec (reads as clearcoat), Fresnel-driven opacity + Fresnel
rim emissive (the glassy LED glow at grazing angles), subtle WPO wave from the MPC.

Keeps the same asset path so BP_GlassLEDVolume's material reference stays intact.
Run via bridge run_python_file. Markers: 'UEGLASS:'.
"""
import unreal
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
def log(m): unreal.log_warning("UEGLASS: " + m)

mpc = EAL.load_asset("/Game/FinalSolution/MPC_GlassLED")
mat = EAL.load_asset("/Game/FinalSolution/M_GlassLED")
MEL.delete_all_material_expressions(mat)

# --- material domain / glass setup ---
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
for _m in ("TLM_SURFACE_PER_PIXEL_LIGHTING","TLM_SURFACE","TLM_SURFACE_FORWARD_SHADING"):
    _v = getattr(unreal.TranslucencyLightingMode, _m, None)
    if _v is not None:
        mat.set_editor_property("translucency_lighting_mode", _v); break
mat.set_editor_property("two_sided", True)
try: mat.set_editor_property("refraction_method", unreal.RefractionMode.REFRACTION_MODE_INDEX_OF_REFRACTION)
except Exception: pass

def C(x,y,r): n=MEL.create_material_expression(mat,unreal.MaterialExpressionConstant,x,y); n.set_editor_property("r",r); return n
def CP(name,x,y): n=MEL.create_material_expression(mat,unreal.MaterialExpressionCollectionParameter,x,y); n.set_editor_property("collection",mpc); n.set_editor_property("parameter_name",name); return n
def MUL(a,b,x,y): n=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,x,y); MEL.connect_material_expressions(a,"",n,"A"); MEL.connect_material_expressions(b,"",n,"B"); return n
def ADD(a,b,x,y): n=MEL.create_material_expression(mat,unreal.MaterialExpressionAdd,x,y); MEL.connect_material_expressions(a,"",n,"A"); MEL.connect_material_expressions(b,"",n,"B"); return n

col = CP("BaseColor",-1700,300)
emi = CP("EmissiveStrength",-1700,420)
amp = CP("WaveAmplitude",-1700,-200); frq = CP("WaveFrequency",-1700,-120)
spd = CP("WaveSpeed",-1700,-40);     dsp = CP("Displacement",-1700,40)

# Fresnel rim
fres = MEL.create_material_expression(mat,unreal.MaterialExpressionFresnel,-1200,150)
fres.set_editor_property("exponent",4.0); fres.set_editor_property("base_reflect_fraction",0.04)

# Base color (deep blue) + spec/rough -> glassy clearcoat read
MEL.connect_material_property(col,"",unreal.MaterialProperty.MP_BASE_COLOR)
MEL.connect_material_property(C(-300,520,0.04),"",unreal.MaterialProperty.MP_ROUGHNESS)
MEL.connect_material_property(C(-300,600,1.0),"",unreal.MaterialProperty.MP_SPECULAR)
MEL.connect_material_property(C(-300,680,0.0),"",unreal.MaterialProperty.MP_METALLIC)

# Opacity = lerp(0.06, 0.65, fresnel) -> glass thin face, opaque rim
op_lo=C(-700,300,0.06); op_hi=C(-700,360,0.65)
lerp=MEL.create_material_expression(mat,unreal.MaterialExpressionLinearInterpolate,-500,330)
MEL.connect_material_expressions(op_lo,"",lerp,"A"); MEL.connect_material_expressions(op_hi,"",lerp,"B")
MEL.connect_material_expressions(fres,"",lerp,"Alpha")
MEL.connect_material_property(lerp,"",unreal.MaterialProperty.MP_OPACITY)

# Refraction (IOR ~1.5)
MEL.connect_material_property(C(-300,760,1.5),"",unreal.MaterialProperty.MP_REFRACTION)

# Emissive = blue * strength * fresnel rim glow
rim = MUL(col,fres,-900,440)
em  = MUL(rim,emi,-700,440)
MEL.connect_material_property(em,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)

# WPO subtle wave: normal * sin(worldpos.x*freq + time*speed) * amp * (disp*0.05)
t=MEL.create_material_expression(mat,unreal.MaterialExpressionTime,-1500,-260)
tw=MUL(t,spd,-1300,-240)
wp=MEL.create_material_expression(mat,unreal.MaterialExpressionWorldPosition,-1500,-120)
cv=MEL.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-1500,-40); cv.set_editor_property("constant",unreal.LinearColor(1,1,0,0))
dot=MEL.create_material_expression(mat,unreal.MaterialExpressionDotProduct,-1300,-100)
MEL.connect_material_expressions(wp,"",dot,"A"); MEL.connect_material_expressions(cv,"",dot,"B")
ph=ADD(MUL(dot,frq,-1100,-100),tw,-950,-160)
s=MEL.create_material_expression(mat,unreal.MaterialExpressionSine,-820,-160); MEL.connect_material_expressions(ph,"",s,"")
a1=MUL(s,amp,-650,-120); a2=MUL(a1,dsp,-500,-100); a3=MUL(a2,C(-650,20,0.05),-360,-60)
nrm=MEL.create_material_expression(mat,unreal.MaterialExpressionVertexNormalWS,-500,60)
wpo=MUL(nrm,a3,-200,0)
MEL.connect_material_property(wpo,"",unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

MEL.recompile_material(mat); EAL.save_asset(mat.get_path_name())
# dial emissive default down so glass reads (rim glow, not blowout)
for p in mpc.get_editor_property("scalar_parameters"):
    if p.get_editor_property("parameter_name") == "EmissiveStrength":
        p.set_editor_property("default_value", 2.5)
mpc.set_editor_property("scalar_parameters", mpc.get_editor_property("scalar_parameters"))
EAL.save_asset(mpc.get_path_name())
log("M_GlassLED rebuilt as translucent fresnel glass OK")
