"""
build_ue_production.py — build the UE5 production leg of final-3d-solution-a.

Creates under /Game/FinalSolution/:
  MPC_GlassLED        Material Parameter Collection (live params, fed by bridge/ue5_remote_apply.py)
  M_GlassLED          glass+LED material: emissive blue, WPO soft-body deform driven by the MPC
  BP_GlassLEDVolume   Actor BP with an InstancedStaticMeshComponent — a versionable, instanceable
                      grid of glass LED cubes using M_GlassLED

Run via the bridge:  run_python_file  (or execute_unreal_python: exec(open(...).read()))
Results are logged with 'UEBUILD:' markers (read back with get_log_lines).
"""
import unreal

PKG = "/Game/FinalSolution"
tools = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary

def log(m): unreal.log_warning("UEBUILD: " + m)

if not EAL.does_directory_exist(PKG):
    EAL.make_directory(PKG)

# ---------------- 1. MPC --------------------------------------------------
def build_mpc():
    path = PKG + "/MPC_GlassLED"
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    mpc = tools.create_asset("MPC_GlassLED", PKG, unreal.MaterialParameterCollection,
                             unreal.MaterialParameterCollectionFactoryNew())
    def sc(n, v):
        p = unreal.CollectionScalarParameter(); p.set_editor_property("parameter_name", n); p.set_editor_property("default_value", v); return p
    mpc.set_editor_property("scalar_parameters", [
        sc("WaveSpeed", 2.0), sc("WaveAmplitude", 1.0), sc("WaveFrequency", 2.5),
        sc("WaveDecay", 0.5), sc("Displacement", 40.0), sc("EmissiveStrength", 1.6)])
    vc = unreal.CollectionVectorParameter(); vc.set_editor_property("parameter_name", "BaseColor")
    vc.set_editor_property("default_value", unreal.LinearColor(0.04, 0.22, 0.85, 1.0))
    mpc.set_editor_property("vector_parameters", [vc])
    EAL.save_asset(path)
    log("MPC_GlassLED OK")
    return mpc

# ---------------- 2. Material ---------------------------------------------
def cparam(mat, mpc, name, x, y):
    n = MEL.create_material_expression(mat, unreal.MaterialExpressionCollectionParameter, x, y)
    n.set_editor_property("collection", mpc); n.set_editor_property("parameter_name", name)
    return n

def build_material(mpc):
    path = PKG + "/M_GlassLED"
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    mat = tools.create_asset("M_GlassLED", PKG, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("two_sided", True)
    # params
    spd=cparam(mat,mpc,"WaveSpeed",-1600,-200); amp=cparam(mat,mpc,"WaveAmplitude",-1600,-100)
    frq=cparam(mat,mpc,"WaveFrequency",-1600,0); dsp=cparam(mat,mpc,"Displacement",-1600,100)
    emi=cparam(mat,mpc,"EmissiveStrength",-1600,300); col=cparam(mat,mpc,"BaseColor",-1600,400)
    # time * speed
    t=MEL.create_material_expression(mat,unreal.MaterialExpressionTime,-1400,-260)
    tw=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-1200,-230)
    MEL.connect_material_expressions(t,"",tw,"A"); MEL.connect_material_expressions(spd,"",tw,"B")
    # worldpos . (1,1,0)
    wp=MEL.create_material_expression(mat,unreal.MaterialExpressionWorldPosition,-1400,-60)
    cv=MEL.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-1400,40)
    cv.set_editor_property("constant",unreal.LinearColor(1.0,1.0,0.0,0.0))
    dot=MEL.create_material_expression(mat,unreal.MaterialExpressionDotProduct,-1200,-20)
    MEL.connect_material_expressions(wp,"",dot,"A"); MEL.connect_material_expressions(cv,"",dot,"B")
    ph1=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-1000,-20)
    MEL.connect_material_expressions(dot,"",ph1,"A"); MEL.connect_material_expressions(frq,"",ph1,"B")
    phase=MEL.create_material_expression(mat,unreal.MaterialExpressionAdd,-820,-120)
    MEL.connect_material_expressions(ph1,"",phase,"A"); MEL.connect_material_expressions(tw,"",phase,"B")
    s=MEL.create_material_expression(mat,unreal.MaterialExpressionSine,-660,-120)
    MEL.connect_material_expressions(phase,"",s,"")
    a1=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-500,-60)
    MEL.connect_material_expressions(s,"",a1,"A"); MEL.connect_material_expressions(amp,"",a1,"B")
    a2=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-360,-40)
    MEL.connect_material_expressions(a1,"",a2,"A"); MEL.connect_material_expressions(dsp,"",a2,"B")
    sc=MEL.create_material_expression(mat,unreal.MaterialExpressionConstant,-360,60); sc.set_editor_property("r",0.1)
    a3=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-220,-20)
    MEL.connect_material_expressions(a2,"",a3,"A"); MEL.connect_material_expressions(sc,"",a3,"B")
    nrm=MEL.create_material_expression(mat,unreal.MaterialExpressionVertexNormalWS,-360,180)
    wpo=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-120,80)
    MEL.connect_material_expressions(nrm,"",wpo,"A"); MEL.connect_material_expressions(a3,"",wpo,"B")
    MEL.connect_material_property(wpo,"",unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    # emissive = color * strength ; base = color*0.1 ; rough
    em=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-220,360)
    MEL.connect_material_expressions(col,"",em,"A"); MEL.connect_material_expressions(emi,"",em,"B")
    MEL.connect_material_property(em,"",unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    bcs=MEL.create_material_expression(mat,unreal.MaterialExpressionConstant,-220,470); bcs.set_editor_property("r",0.1)
    bc=MEL.create_material_expression(mat,unreal.MaterialExpressionMultiply,-80,430)
    MEL.connect_material_expressions(col,"",bc,"A"); MEL.connect_material_expressions(bcs,"",bc,"B")
    MEL.connect_material_property(bc,"",unreal.MaterialProperty.MP_BASE_COLOR)
    rg=MEL.create_material_expression(mat,unreal.MaterialExpressionConstant,-220,560); rg.set_editor_property("r",0.06)
    MEL.connect_material_property(rg,"",unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat); EAL.save_asset(path)
    log("M_GlassLED OK")
    return mat

# ---------------- 3. Blueprint with ISM -----------------------------------
def build_blueprint(mat):
    path = PKG + "/BP_GlassLEDVolume"
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    f = unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.Actor)
    bp = tools.create_asset("BP_GlassLEDVolume", PKG, None, f)
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_blueprint(bp)
    params = unreal.AddNewSubobjectParams(parent_handle=handles[0],
        new_class=unreal.InstancedStaticMeshComponent, blueprint_context=bp)
    h, fail = sds.add_new_subobject(params)
    sds.rename_subobject(h, unreal.Text("ISM"))
    data = sds.k2_find_subobject_data_from_handle(h)
    ism = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
    ism = unreal.InstancedStaticMeshComponent.cast(ism)
    cube = EAL.load_asset("/Engine/BasicShapes/Cube.Cube")
    ism.set_static_mesh(cube)
    ism.set_material(0, mat)
    # instanceable grid (versionable: baked into the component default)
    cx,cy,cz,sp,sz = 6,4,3,160.0,55.0
    ox,oy,oz=(cx-1)/2,(cy-1)/2,(cz-1)/2
    for z in range(cz):
        for y in range(cy):
            for x in range(cx):
                tr=unreal.Transform()
                tr.set_editor_property("translation",unreal.Vector((x-ox)*sp,(y-oy)*sp,(z-oz)*sp+200))
                tr.set_editor_property("scale3d",unreal.Vector(sz/100.0,sz/100.0,sz/100.0))
                ism.add_instance(tr, False)
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    log("BP_GlassLEDVolume OK (%d instances)" % (cx*cy*cz))
    return bp

try:
    mpc = build_mpc()
    mat = build_material(mpc)
    bp  = build_blueprint(mat)
    unreal.KismetSystemLibrary.execute_console_command(None, "obj gc")
    log("ALL DONE -> /Game/FinalSolution")
except Exception as e:
    import traceback
    log("FAILED: " + str(e))
    unreal.log_error(traceback.format_exc())
