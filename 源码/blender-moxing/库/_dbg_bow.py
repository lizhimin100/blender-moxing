import importlib
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "联盟", "弓箭手"), os.path.join(ROOT, "联盟", "基准")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import voxbase as V
import poselib2 as PL
import anims_lib as ALIB
import clip_lib as CL
import unit_弓箭手 as U
import anims_弓箭手 as A

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
g = U.build()
ob = g.build(prefix=U.PREFIX)
arm = g.build_rig("RIG")
g.bind(arm, ob)
ALIB.set_sole(PL.Sole(arm, [ob]))
A.build_all(arm)
A.pose_at(arm, "idle", 0)
bpy.context.view_layer.update()

w = CL.Watch([ob])
geo = w.geo(bpy.context.evaluated_depsgraph_get())
for b in ("head", "chest", "hips", "upperarm_L", "forearm_L", "hand_L", "weapon_L",
          "thigh_L", "shin_L", "foot_L"):
    vs = geo.get(b, ([], []))[0]
    if not vs:
        print("%-12s -" % b)
        continue
    print("%-12s x %+.3f..%+.3f  y %+.3f..%+.3f  z %+.3f..%+.3f  n=%d"
          % (b, min(v.x for v in vs), max(v.x for v in vs),
             min(v.y for v in vs), max(v.y for v in vs),
             min(v.z for v in vs), max(v.z for v in vs), len(vs)))
for b in ("upperarm_L", "forearm_L", "hand_L", "weapon_L", "shoulder_L"):
    pb = arm.pose.bones[b]
    print("%-12s T=(%+.3f %+.3f %+.3f)  Y=(%+.2f %+.2f %+.2f)" %
          (b, *pb.matrix.translation, *pb.matrix.col[1].xyz))
print("[grip] palm target ->", geo.get("weapon_L", ([], []))[0][:1])
