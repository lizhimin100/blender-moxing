import importlib, os, sys
import bpy
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR = os.path.abspath(argv[0]); MOD = argv[1]; ACT = argv[2]
ROOT = UNIT_DIR
while not os.path.isdir(os.path.join(ROOT, "库")): ROOT = os.path.dirname(ROOT)
for _p in (os.path.join(ROOT, "库"), UNIT_DIR):
    if _p not in sys.path: sys.path.insert(0, _p)
import unitkit2 as K
U = importlib.import_module(MOD)
AN = importlib.import_module("anims_" + U.NAME)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
u = U.build(low=False); objs = u.finish(prefix=U.PREFIX, join_by="module")
arm = U.build_rig(); u.bind(arm, objs)
AN.build_all(arm, only=[ACT])
act = [a for a in bpy.data.actions if a.name == ACT][0]
arm.animation_data.action = act; arm.animation_data.action_slot = act.slots[0]
f0, f1 = (int(v) for v in act.frame_range)
bpy.context.scene.frame_set(f0); bpy.context.view_layer.update()
m0 = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
bpy.context.scene.frame_set(f1); bpy.context.view_layer.update()
rows = []
for pb in arm.pose.bones:
    d = max(abs(a - b) for r0, r1 in zip(m0[pb.name], pb.matrix) for a, b in zip(r0, r1))
    rows.append((d, pb.name))
rows.sort(reverse=True)
for d, n in rows[:6]:
    print("%.4f  %s" % (d, n))
