import bpy
def setup():
    try:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for sp in area.spaces:
                    if sp.type == 'VIEW_3D':
                        sp.shading.type = 'MATERIAL'
                        sp.shading.use_scene_world = False
        # frame the object and play
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                with bpy.context.temp_override(area=area, region=area.regions[-1]):
                    bpy.ops.object.select_all(action='SELECT')
                    bpy.ops.view3d.view_selected()
                    bpy.ops.screen.animation_play()
                break
    except Exception as e:
        print("preview setup:", e)
    return None
bpy.app.timers.register(setup, first_interval=1.5)
