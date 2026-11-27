"""_dbg_pose.py —— 动作定格体检图（后台跑，不动桥接）

  blender -b --factory-startup --python 库/_dbg_pose.py -- <unit_dir> <module> <outdir> <action:frames> [azim,elev]

例：-- "联盟/长枪兵" unit_长枪兵 docs/_tmp/pose attack:0,6,13,19,23,30 218,14
"""
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR = os.path.abspath(argv[0])
MOD = argv[1]
OUT = os.path.abspath(argv[2])
SPEC = argv[3] if len(argv) > 3 else "attack:0,10,20,30"
VIEWS = [float(x) for x in (argv[4] if len(argv) > 4 else "218,14").split(",")]
RES = int(argv[argv.index("--res") + 1]) if "--res" in argv else 520

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "库"))
import vox_studio as ST  # noqa: E402

try:
    bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    bpy.context.scene.render.engine = "BLENDER_EEVEE"

S = ST.open_unit(UNIT_DIR, MOD, act=True)
ob = S["ob"]
ST.studio(res=RES, samples=16)
os.makedirs(OUT, exist_ok=True)

pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
H = mx.z - mn.z
ctr = (mn + mx) * 0.5
c2 = Vector((0.0, 0.0, H * 0.55))
SC = max(H, 1.9) * 1.30
print("[bbox] %.2f x %.2f x %.2f" % (mx.x - mn.x, mx.y - mn.y, H))

for spec in SPEC.split(","):
    if ":" not in spec:
        continue
    act, frames = spec.split(":")
    for fr in [int(x) for x in frames.split("+")]:
        ST.pose(S, act, fr)
        bpy.context.view_layer.update()
        name = "%s_%s_%03d_a%03d" % (MOD, act, fr, int(VIEWS[0]))
        ST.shoot(name, OUT, azim=VIEWS[0], elev=VIEWS[1], center=c2, scale=SC)
print("[done]")
