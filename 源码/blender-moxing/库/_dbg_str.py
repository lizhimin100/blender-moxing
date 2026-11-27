"""_dbg_str.py —— 弓弦是否真的被拉开（打印骨缩放 + 弦顶点世界坐标）

  blender -b --factory-startup --python 库/_dbg_str.py -- <unit_dir> <module> <act> <frame>
"""
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR, MOD, ACT, FR = argv[0], argv[1], argv[2], int(argv[3])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "库"))
import vox_studio as ST  # noqa: E402

S = ST.open_unit(UNIT_DIR, MOD, act=True)
arm, ob = S["arm"], S["ob"]
ST.pose(S, ACT, FR)
bpy.context.view_layer.update()

for bn in ("bow_up", "bow_dn"):
    pb = arm.pose.bones.get(bn)
    if not pb:
        print("[miss]", bn)
        continue
    print("[bone] %-8s T=%s  scale=%s  len=%.3f  ydir=%s"
          % (bn, tuple(round(v, 3) for v in pb.matrix.translation),
             tuple(round(v, 3) for v in pb.scale), pb.length,
             tuple(round(v, 3) for v in (pb.matrix.to_3x3() @ Vector((0, 1, 0))))))
    print("[tail] %-8s %s" % (bn, tuple(round(v, 3) for v in pb.tail)))

dg = bpy.context.evaluated_depsgraph_get()
oe = ob.evaluated_get(dg)
me = oe.to_mesh()
for pn in ("bowstring_up", "bowstring_dn", "bow"):
    rng = ob.get("vox_parts", {}).get(pn)
    if not rng:
        continue
    vs = [oe.matrix_world @ me.vertices[i].co for i in range(rng[0], rng[1])]
    xs = [v.x for v in vs]
    ys = [v.y for v in vs]
    zs = [v.z for v in vs]
    print("[part] %-12s n=%3d  x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f"
          % (pn, len(vs), min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    if pn.startswith("bowstring"):
        v0 = ob.data.vertices[rng[0]]
        print("   [grp]", [(ob.vertex_groups[g.group].name, round(g.weight, 2))
                           for g in v0.groups])
oe.to_mesh_clear()

pb = arm.pose.bones["hand_R"]
palm = pb.matrix.translation + (pb.matrix.to_3x3() @ Vector((0, 0.10, 0)))
print("[palmR]", tuple(round(v, 3) for v in palm))
