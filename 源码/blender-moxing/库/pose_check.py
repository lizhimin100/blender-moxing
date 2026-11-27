"""pose_check.py —— 内存里建单位 + 只建要看的动作 + 客观体检（迭代用）

    blender -b --factory-startup --python 库/pose_check.py -- \
        <unit_dir> <unit_module> <anims_module> [--only idle,walk] [--pairs all]
        [--step 2] [--min 0]

比 `audit_anim.py`（跑 glb）快得多：不导出、不导入，改一行姿态就能重测。
最终出货仍以 `audit_anim.py` 对 glb 的结果为准。

两种单位接入方式都支持：
  * 有 `load()` 的（步兵 / 弩兵 / 农民：导入旧 glb 再挂动作）
  * 有 `build()` 的（斥候 / 战士 / 萨满：几何即代码）
"""
import importlib
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def flag(name, default=None):
    if name in argv:
        i = argv.index(name) + 1
        return argv[i] if i < len(argv) else True
    return default


UNIT_DIR = os.path.abspath(argv[0])
UMOD = argv[1]
AMOD = argv[2]
ONLY = [s for s in str(flag("--only", "")).split(",") if s]
MODE = flag("--pairs", "all")
STEP = int(flag("--step", 2))
MIN_FRAMES = int(flag("--min", 0))

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, UNIT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

for _m in ("unitkit", "unitkit2", "gnoll_kit", "gnoll_kit2", "poselib2",
           "anims_human", UMOD, AMOD, "human_kit2", "anim_tools"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

U = importlib.import_module(UMOD)
A = importlib.import_module(AMOD)
import clip_lib as CL  # noqa: E402

if hasattr(U, "load"):
    root, arm, meshes = U.load()
    objs = [o for o in meshes]
else:
    u = U.build(low=False)
    objs = u.finish(prefix=U.PREFIX, join_by="module")
    arm = U.build_rig()
    u.bind(arm, objs)

print("[unit]", U.__name__, "meshes", [o.name for o in objs], "bones", len(arm.data.bones))

if hasattr(A, "build_all"):
    names = A.build_all(arm)
else:
    names = A.build(arm)
names = [n if isinstance(n, str) else n[0] for n in names]
print("[actions]", names)

pairs = CL.pairs_for(MODE)
watch = CL.Watch(objs)
bad = []
for nm in names:
    if ONLY and nm not in ONLY:
        continue
    act = bpy.data.actions.get(nm)
    if act is None:
        continue
    r = CL.audit_action(scene, arm, act, pairs, watch, step=STEP,
                        maxf=max(MIN_FRAMES, 26))
    if r["worst"] or r["zmin"] < -0.002:
        bad.append(nm)

arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
print("[pose_check done] bad:", bad)
