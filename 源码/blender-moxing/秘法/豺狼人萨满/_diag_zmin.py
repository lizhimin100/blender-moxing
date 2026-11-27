"""逐帧 zmin：找出阵亡动作里哪个模块沉到地下。"""
import importlib
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    ROOT = os.path.dirname(ROOT)
LIB = os.path.join(ROOT, "库")
for _p in (LIB, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import unitkit2 as K  # noqa: E402

for _m in ("unitkit2", "unit_萨满", "anims_萨满"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import unit_萨满 as U  # noqa: E402
import anims_萨满 as A  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ACT = argv[0] if argv else "death"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
u = U.build(low=False)
objs = u.finish(prefix=U.PREFIX, join_by="module")
arm = U.build_rig()
u.bind(arm, objs)
A.build_all(arm, only=[ACT])

act = [a for a in bpy.data.actions if a.name == ACT][0]
arm.animation_data.action = act
arm.animation_data.action_slot = act.slots[0]
f0, f1 = (int(v) for v in act.frame_range)

worst = {}
for f in range(f0, f1 + 1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    row = []
    for ob in objs:
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        mw = oe.matrix_world
        z = min((mw @ v.co).z for v in me.vertices)
        oe.to_mesh_clear()
        row.append((ob.name.split("_")[-1], z))
        if z < worst.get(ob.name, (9, 0))[0]:
            worst[ob.name] = (z, f)
    if f % 4 == 0 or min(z for _, z in row) < -0.01:
        print("f%3d  " % f + "  ".join("%s %+.3f" % r for r in row))
print("[worst]", {k.split('_')[-1]: (round(v[0], 3), v[1]) for k, v in worst.items()})
