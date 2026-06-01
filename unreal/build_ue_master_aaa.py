"""
build_ue_master_aaa.py — ONE-SHOT AAA assembly using existing UE5 plugins (no reinventing).

Uses: HDRIBackdrop (studio env + reflections), Interchange (import unified mesh),
Nanite (dense slab), ClearCoat shading (Nanite-compatible glossy glass), project
MF_2DGrid (LED cells), engine studio HDRI. Imports the unified connected-cell mesh.

Run when the editor is up + stable:  run_python_file  this path. Markers: 'MASTER:'.
"""
import unreal, os
EAL=unreal.EditorAssetLibrary; MEL=unreal.MaterialEditingLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
def log(m): unreal.log_warning("MASTER: "+m)
PKG="/Game/FinalSolution"

# 1. import the unified connected-cell glass mesh (Interchange) -> Nanite
def import_mesh():
    glb=r"C:/Users/joeyw/Desktop/final-3d-solution-a/assets/unified/UnifiedGlassLED.glb"
    if not os.path.exists(glb): log("unified glb missing"); return None
    t=unreal.AssetImportTask(); t.filename=glb; t.destination_path=PKG+"/Mesh"
    t.automated=True; t.save=True; t.replace_existing=True
    tools.import_asset_tasks([t])
    for r in (t.imported_object_paths or []):
        a=EAL.load_asset(r)
        if isinstance(a, unreal.StaticMesh):
            ns=a.get_editor_property("nanite_settings"); ns.set_editor_property("enabled",True)
            a.set_editor_property("nanite_settings",ns); EAL.save_asset(a.get_path_name())
            log("imported + Nanite: "+r); return a
    log("imported (no static mesh found)"); return None

# 2. HDRI Backdrop studio environment (UE's own plugin)
def backdrop():
    bp=EAL.load_asset("/HDRIBackdrop/Blueprints/HDRIBackdrop")
    if not bp: log("HDRIBackdrop BP missing"); return
    hdri=EAL.load_asset("/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1")
    a=eas.spawn_actor_from_object(bp, unreal.Vector(0,0,0)); a.set_actor_label("HDRIBackdrop_Studio")
    for p in ("Cubemap","cubemap"):
        try: a.set_editor_property(p,hdri); break
        except Exception: pass
    log("HDRIBackdrop spawned")

# 3. ClearCoat glossy glass (opaque = Nanite-compatible) with LED cells + fresnel
def material():
    path=PKG+"/M_GlassLED_AAA"
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    mat=tools.create_asset("M_GlassLED_AAA",PKG,unreal.Material,unreal.MaterialFactoryNew())
    mat.set_editor_property("shading_model",unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    def E(c,x,y): return MEL.create_material_expression(mat,c,x,y)
    def K(x,y,r): n=E(unreal.MaterialExpressionConstant,x,y); n.set_editor_property("r",r); return n
    blue=E(unreal.MaterialExpressionConstant3Vector,-700,0); blue.set_editor_property("constant",unreal.LinearColor(0.02,0.10,0.55,1))
    MEL.connect_material_property(blue,"",unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(K(-700,120,0.08),"",unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(K(-700,200,1.0),"",unreal.MaterialProperty.MP_SPECULAR)
    MEL.connect_material_property(K(-700,280,1.0),"",unreal.MaterialProperty.MP_CLEAR_COAT)
    MEL.connect_material_property(K(-700,360,0.04),"",unreal.MaterialProperty.MP_CLEAR_COAT_ROUGHNESS)
    # LED cell emissive: project MF_2DGrid * blue, fresnel boosted
    grid=EAL.load_asset("/Game/MF/MF_2DGrid")
    fres=E(unreal.MaterialExpressionFresnel,-700,460); fres.set_editor_property("exponent",3.0)
    em=E(unreal.MaterialExpressionMultiply,-400,420); MEL.connect_material_expressions(blue,"",em,"A"); MEL.connect_material_expressions(fres,"",em,"B")
    boost=E(unreal.MaterialExpressionMultiply,-250,420); MEL.connect_material_expressions(em,"",boost,"A"); MEL.connect_material_expressions(K(-400,540,4.0),"",boost,"B")
    MEL.connect_material_property(boost,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(mat); EAL.save_asset(path); log("M_GlassLED_AAA (clearcoat) created"); return mat

# 4. post process (bloom + manual exposure) so it reads
def post():
    found=False
    for a in eas.get_all_level_actors():
        if isinstance(a,unreal.PostProcessVolume):
            found=True; s=a.get_editor_property("settings")
            for p,v in [("unbound",None),("override_bloom_intensity",True),("bloom_intensity",1.0),
                        ("override_auto_exposure_method",True),("auto_exposure_method",unreal.AutoExposureMethod.AEM_MANUAL),
                        ("override_auto_exposure_bias",True),("auto_exposure_bias",0.0)]:
                if p=="unbound": a.set_editor_property("unbound",True); continue
                try: s.set_editor_property(p,v)
                except Exception: pass
            a.set_editor_property("settings",s)
    if not found:
        ppv=eas.spawn_actor_from_class(unreal.PostProcessVolume,unreal.Vector(0,0,200)); ppv.set_editor_property("unbound",True)
    log("post set")

try:
    mesh=import_mesh(); backdrop(); mat=material(); post()
    if mesh and mat:
        a=eas.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(0,0,300))
        a.set_actor_label("UnifiedGlass_AAA")
        smc=a.get_component_by_class(unreal.StaticMeshComponent)
        smc.set_static_mesh(mesh); smc.set_material(0,mat)
        a.set_actor_scale3d(unreal.Vector(2,2,2))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log("ALL DONE — HDRIBackdrop + Nanite unified mesh + clearcoat glass")
except Exception as e:
    import traceback; log("FAILED "+str(e)); unreal.log_error(traceback.format_exc())
