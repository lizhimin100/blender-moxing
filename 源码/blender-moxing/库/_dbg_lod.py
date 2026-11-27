"""_dbg_lod.py —— 三档 LOD 静态体检图（后台跑，不动桥接）

  blender -b --factory-startup --python 库/_dbg_lod.py -- <unit_dir> <module> <outdir> [0,1,2]

产物：<outdir>/<module>_L<lv>_{front,side,iso}.png
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR = os.path.abspath(argv[0])
MOD = argv[1]
OUT = os.path.abspath(argv[2])
LEVELS = [int(x) for x in (argv[3] if len(argv) > 3 else "0,1,2").split(",")]
ACT = argv[4] if len(argv) > 4 else None          # 例 attack:18（验低模上的动作）

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "库"))
import vox_studio as ST  # noqa: E402

try:
    bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    bpy.context.scene.render.engine = "BLENDER_EEVEE"

U, A = ST.load(UNIT_DIR, MOD)
os.makedirs(OUT, exist_ok=True)

for lv in LEVELS:
    ST.purge()
    g0 = U.build()
    g = g0 if lv == 0 else g0.lod(level=lv)
    ob = g.build(prefix=getattr(U, "PREFIX", "vox"))
    arm = g.build_rig("RIG_" + U.NAME)
    g.bind(arm, ob)
    g.bake_preview(ob)
    ST.studio(res=560, samples=16)
    bpy.context.view_layer.update()
    if ACT:
        import anims_lib as ALIB
        import poselib2 as PL
        ALIB.set_sole(PL.Sole(arm, [ob]))
        A.build_all(arm)
        act, fr = ACT.split(":")
        A.pose_at(arm, act, int(fr))
        bpy.context.view_layer.update()
    ob.data.calc_loop_triangles()
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    H = mx.z - mn.z
    ctr = (mn + mx) * 0.5
    print("[L%d] tris=%d z=%.3f..%.3f  bbox=%.2f x %.2f x %.2f"
          % (lv, len(ob.data.loop_triangles), mn.z, mx.z,
             mx.x - mn.x, mx.y - mn.y, mx.z - mn.z))
    SC = max(H, 2.0) * 1.12
    ST.shoot("%s_L%d_front" % (MOD, lv), OUT, azim=180, elev=2, center=ctr, scale=SC)
    ST.shoot("%s_L%d_side" % (MOD, lv), OUT, azim=90, elev=2, center=ctr, scale=SC)
    ST.shoot("%s_L%d_iso" % (MOD, lv), OUT, azim=218, elev=16, center=ctr, scale=SC)
print("[done]")
