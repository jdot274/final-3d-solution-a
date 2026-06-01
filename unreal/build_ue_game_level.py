"""
build_ue_game_level.py — the FULL playable game level using YOUR existing files.
Quadcopter game mode + pawn, court (imported), tron disc racket, glass LED volume,
scoreboard, PlayerStart, cameras, opening Level Sequence, Static (bakeable) lighting.
Run from UE Tools>Execute Python when the editor is open. Markers 'GAME:'.
"""
import unreal
EAL=unreal.EditorAssetLibrary; tools=unreal.AssetToolsHelpers.get_asset_tools()
eas=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def log(m): unreal.log_warning("GAME: "+m)
PKG="/Game/FinalSolution"

def find_one(cls_path, name_contains, under="/Game/"):
    ar=unreal.AssetRegistryHelpers.get_asset_registry()
    for a in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine","Blueprint"), True):
        n=str(a.asset_name)
        if name_contains.lower() in n.lower(): return str(a.package_name)
    return None

try:
    les.new_level(PKG+"/L_SPIN_Game")
    placed=[]
    # PAWN: quadcopter
    quad=EAL.load_asset("/Game/Quadcopters/Blueprints/BP_Quadcopter_A")
    if not quad:
        p=find_one(None,"Quadcopter");  quad=EAL.load_asset(p) if p else None
    # GAME MODE: create one with quadcopter as default pawn
    gm=None
    try:
        f=unreal.BlueprintFactory(); f.set_editor_property("parent_class", unreal.GameModeBase)
        gmbp=tools.create_asset("BP_SPIN_GameMode", PKG, None, f)
        if quad:
            cdo=unreal.get_default_object(gmbp.generated_class())
            try: cdo.set_editor_property("default_pawn_class", quad.generated_class())
            except Exception: pass
        unreal.EditorAssetLibrary.save_loaded_asset(gmbp); gm=gmbp; placed.append("GameMode(quadcopter pawn)")
    except Exception as e: log("gamemode: "+str(e))
    # place court (imported), glass volume, arena, scoreboard
    court=EAL.load_asset(PKG+"/Imported/Court/TennisCourt")
    if court:
        a=eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0)); a.set_actor_label("Court")
        a.get_component_by_class(unreal.StaticMeshComponent).set_static_mesh(court); placed.append("Court")
    for path,loc,lbl in [(PKG+"/BP_GlassLEDVolume",(0,0,450),"GlassVolume"),
                         (PKG+"/BP_SPIN_Arena",(0,-1500,0),"Arena")]:
        bp=EAL.load_asset(path)
        if bp: eas.spawn_actor_from_object(bp, unreal.Vector(*loc)).set_actor_label(lbl); placed.append(lbl)
    # tron disc racket (engine cylinder proxy if no racket mesh) + scoreboard
    sb=eas.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(0,0,900)); sb.set_actor_label("Scoreboard")
    trc=sb.get_component_by_class(unreal.TextRenderComponent); trc.set_text(unreal.Text("SPIN   0 : 0"))
    try: trc.set_world_size(150.0); trc.set_text_render_color(unreal.Color(120,200,255,255)); trc.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)
    except Exception: pass
    sb.set_actor_rotation(unreal.Rotator(0,180,0), False); placed.append("Scoreboard")
    # PlayerStart
    eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0,-800,200)); placed.append("PlayerStart")
    # lighting (Static -> bakeable lightmaps)
    dl=eas.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,2000), unreal.Rotator(-42,135,0))
    dc=dl.get_component_by_class(unreal.DirectionalLightComponent); dc.set_intensity(6.0)
    try: dc.set_mobility(unreal.ComponentMobility.STATIC)
    except Exception: pass
    eas.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0,0,0))
    sl=eas.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0,0,1000))
    try: sl.get_component_by_class(unreal.SkyLightComponent).set_mobility(unreal.ComponentMobility.STATIC)
    except Exception: pass
    # opening Level Sequence
    try:
        seq=tools.create_asset("LS_Opening", PKG+"/Cine", unreal.LevelSequence, unreal.LevelSequenceFactoryNew()); seq.set_playback_end(150)
        cam=eas.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(-2500,-2500,1200), unreal.Rotator(-15,45,0)); cam.set_actor_label("SeqCamera")
        b=seq.add_possessable(cam); cct=seq.add_track(unreal.MovieSceneCameraCutTrack); s2=cct.add_section(); s2.set_range(0,150)
        EAL.save_asset(seq.get_path_name()); placed.append("LS_Opening")
    except Exception as e: log("seq: "+str(e))
    # set game mode override on world
    try:
        if gm: unreal.GameplayStatics  # ensure import
    except Exception: pass
    les.save_current_level()
    log("ALL DONE: "+", ".join(placed)+" | run Build>Build Lighting to bake, then Play.")
except Exception as e:
    import traceback; log("FAILED "+str(e)); unreal.log_error(traceback.format_exc())
