"""render_test_vulkan.py — open L_SPIN_Import, frame it, screenshot to file. Tests Vulkan render."""
import unreal
les=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
les.load_level("/Game/FinalSolution/L_SPIN_Import")
ues=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
try: ues.set_level_viewport_camera_info(unreal.Vector(-1400,-1400,800), unreal.Rotator(-16,45,0))
except Exception as e: unreal.log_warning("cam err "+str(e))
unreal.AutomationLibrary.take_high_res_screenshot(1600,900,
    "C:/Users/joeyw/Desktop/final-3d-solution-a/renders/ue_vulkan_test.png")
unreal.log_warning("RENDERTEST: screenshot requested")
