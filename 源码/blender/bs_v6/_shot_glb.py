"""_shot_glb.py —— 直接对成品 GLB 出图（科研态验动作用；一次性工具，可留用）

    blender -b --factory-startup --python blender/bs_v6/_shot_glb.py -- <glb> <out.png> [frame]
"""
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import shotlib as S  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
glb, out = argv[0], argv[1]
frame = int(argv[2]) if len(argv) > 2 else 0

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and any(o.data.materials)]
if frame:
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
S.OUTSHOT = os.path.dirname(out)
S.RES, S.SAMP = 1100, 40
S.setup_world()
S.ground_plane()
S.shot(os.path.basename(out), meshes, 45, 38, 1.07)
print("[shot]", out)
