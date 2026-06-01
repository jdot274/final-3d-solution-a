"""
build_ue_arena_bp.py — ONE reusable, LEVEL-INDEPENDENT blueprint: BP_SPIN_Arena.
Brings its own court + glossy blue material + glass LED volume + racket + scoreboard
+ dramatic self-lighting (spotlights + rect light), so it drops into ANY black/empty
level and renders complete. No dependence on level lighting.
Run via bridge run_python_file. Markers 'ARENA:'. Verify via inspect_blueprint.
"""
import unreal
EAL=unreal.EditorAssetLibrary; MEL=unreal.MaterialEditingLibrary
tools=unreal.AssetToolsHelpers.get_asset_tools()
def log(m): unreal.log_warning("ARENA: "+m)
PKG="/Game/FinalSolution"

# 1. glossy blue court material (opaque clearcoat = visible + glossy, no translucency loss)
def court_mat():
    p=PKG+"/M_CourtGlossy"
    if EAL.does_asset_exist(p): return EAL.load_asset(p)
    m=tools.create_asset("M_CourtGlossy",PKG,unreal.Material,unreal.MaterialFactoryNew())
    m.set_editor_property("shading_model",unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    def K(x,y,r): n=MEL.create_material_expression(m,unreal.MaterialExpressionConstant,x,y); n.set_editor_property("r",r); return n
    blue=MEL.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-700,0); blue.set_editor_property("constant",unreal.LinearColor(0.01,0.05,0.45,1))
    MEL.connect_material_property(blue,"",unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(K(-700,120,0.05),"",unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(K(-700,200,1.0),"",unreal.MaterialProperty.MP_SPECULAR)
    # clear coat = Custom Data 0, clear coat roughness = Custom Data 1
    cc=getattr(unreal.MaterialProperty,"MP_CUSTOMDATA0",None); ccr=getattr(unreal.MaterialProperty,"MP_CUSTOMDATA1",None)
    if cc is not None: MEL.connect_material_property(K(-700,280,1.0),"",cc)
    if ccr is not None: MEL.connect_material_property(K(-700,360,0.03),"",ccr)
    em=MEL.create_material_expression(m,unreal.MaterialExpressionConstant3Vector,-700,440); em.set_editor_property("constant",unreal.LinearColor(0.02,0.12,0.6,1))
    MEL.connect_material_property(em,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m); EAL.save_asset(p); log("M_CourtGlossy created"); return m

# 2. the blueprint with everything as components
def arena(cmat):
    p=PKG+"/BP_SPIN_Arena"
    if EAL.does_asset_exist(p): EAL.delete_asset(p)
    f=unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
    bp=tools.create_asset("BP_SPIN_Arena",PKG,None,f)
    sds=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root=sds.k2_gather_subobject_data_for_blueprint(bp)[0]
    def add(cls,name):
        pr=unreal.AddNewSubobjectParams(parent_handle=root,new_class=cls,blueprint_context=bp)
        h,fail=sds.add_new_subobject(pr); sds.rename_subobject(h,unreal.Text(name))
        d=sds.k2_find_subobject_data_from_handle(h)
        return unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
    # court
    court=unreal.StaticMeshComponent.cast(add(unreal.StaticMeshComponent,"Court"))
    cm=EAL.load_asset("/Game/GlassSphere/Meshes/SM_StadiumCourt")
    if cm: court.set_static_mesh(cm); court.set_material(0,cmat)
    court.set_editor_property("relative_scale3d",unreal.Vector(1,1,1))
    # glass LED volume as child actor
    ch=add(unreal.ChildActorComponent,"GlassVolume")
    ch=unreal.ChildActorComponent.cast(ch)
    gbp=EAL.load_asset("/Game/FinalSolution/BP_GlassLEDVolume")
    if gbp:
        try: ch.set_editor_property("child_actor_class", gbp.generated_class())
        except Exception: pass
    ch.set_editor_property("relative_location",unreal.Vector(0,0,250))
    # racket
    rk=unreal.StaticMeshComponent.cast(add(unreal.StaticMeshComponent,"Racket"))
    rm=EAL.load_asset("/Game/Racket")
    if rm: rk.set_static_mesh(rm)
    rk.set_editor_property("relative_location",unreal.Vector(300,0,120)); rk.set_editor_property("relative_rotation",unreal.Rotator(0,0,40))
    # scoreboard
    sb=unreal.TextRenderComponent.cast(add(unreal.TextRenderComponent,"Scoreboard"))
    sb.set_text(unreal.Text("SPIN   0 : 0"))
    try:
        sb.set_text_render_color(unreal.Color(120,200,255,255)); sb.set_world_size(120.0)
        sb.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    except Exception: pass
    sb.set_editor_property("relative_location",unreal.Vector(0,0,700)); sb.set_editor_property("relative_rotation",unreal.Rotator(0,180,0))
    # dramatic self-lighting (travels with the BP -> works in a black level)
    for i,(loc,rot,col,inten) in enumerate([
        ((-500,-400,900),(-55,40,0),unreal.LinearColor(0.4,0.7,1.0,1),80000.0),
        ((500,400,900),(-55,220,0),unreal.LinearColor(0.2,0.5,1.0,1),60000.0),
        ((0,-600,700),(-45,90,0),unreal.LinearColor(0.6,0.9,1.0,1),50000.0)]):
        slc=unreal.SpotLightComponent.cast(add(unreal.SpotLightComponent,"KeySpot%d"%i))
        slc.set_editor_property("relative_location",unreal.Vector(*loc)); slc.set_editor_property("relative_rotation",unreal.Rotator(*rot))
        try:
            slc.set_intensity(inten); slc.set_light_color(col)
            slc.set_editor_property("attenuation_radius",4000.0)
            slc.set_editor_property("outer_cone_angle",55.0)
        except Exception: pass
    # soft fill rect light
    rl=unreal.RectLightComponent.cast(add(unreal.RectLightComponent,"FillRect"))
    rl.set_editor_property("relative_location",unreal.Vector(0,0,1200)); rl.set_editor_property("relative_rotation",unreal.Rotator(-90,0,0))
    try: rl.set_intensity(20000.0); rl.set_light_color(unreal.LinearColor(0.3,0.5,0.9,1)); rl.set_editor_property("source_width",1500.0); rl.set_editor_property("source_height",1500.0)
    except Exception: pass

    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.get_subsystem if False else None
    log("BP_SPIN_Arena built (court+glass+racket+scoreboard+3 spots+rect, self-lit)")
    return bp

try:
    cmat=court_mat(); bp=arena(cmat)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    log("ALL DONE -> /Game/FinalSolution/BP_SPIN_Arena (drop into any level)")
except Exception as e:
    import traceback; log("FAILED "+str(e)); unreal.log_error(traceback.format_exc())
