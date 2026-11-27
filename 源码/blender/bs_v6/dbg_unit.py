import bpy, sys
sys.path.insert(0, r"D:/测试一/blender/bs_v6")
import iconlib
def snap(tag):
    ms = [(o.name, o.type) for o in bpy.context.scene.objects]
    print("%-12s scene.objects=%d  %s" % (tag, len(ms), [n for n, t in ms if t == "MESH"]))
snap("before")
iconlib.clear_scene()
snap("after clear")
bpy.ops.import_scene.gltf(filepath=r"D:/测试一/assets/单位/联盟/农民/方块人_农民.glb")
bpy.context.view_layer.update()
snap("after import")
for o in bpy.context.scene.objects:
    if o.type == "MESH" and "棱角" in o.name:
        print("  球：parent=%s  hide_render=%s  users_collection=%s  modifiers=%s" % (
            o.parent, o.hide_render, [c.name for c in o.users_collection],
            [m.type for m in o.modifiers]))
