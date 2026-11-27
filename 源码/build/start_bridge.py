import bpy
import addon_utils
import traceback

print("=== bridge bootstrap ===")
print("background:", bpy.app.background)

try:
    if "dsh_blender_bridge" not in [m.__name__ for m in addon_utils.modules()]:
        print("addon module not found")
    addon_utils.enable("dsh_blender_bridge", default_set=False, persistent=True)
    print("addon enabled")
except Exception:
    traceback.print_exc()

try:
    bpy.types.dshbb_server.start()
    print("BRIDGE STARTED")
except Exception:
    traceback.print_exc()
