import importlib, os, sys
import bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "联盟", "弓箭手"), os.path.join(ROOT, "联盟", "基准")):
    if _p not in sys.path: sys.path.insert(0, _p)
import voxbase as V, poselib2 as PL, anims_lib as ALIB, clip_lib as CL
import unit_弓箭手 as U, anims_弓箭手 as A
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene; scene.render.fps = 30
g = U.build(); ob = g.build(prefix=U.PREFIX); arm = g.build_rig("RIG"); g.bind(arm, ob)
ALIB.set_sole(PL.Sole(arm, [ob]))
A.build_all(arm)
A.pose_at(arm, "attack", 23)
bpy.context.view_layer.update()
for b in ("upperarm_L","forearm_L","hand_L","weapon_L","upperarm_R","forearm_R","hand_R","weapon_R"):
    pb = arm.pose.bones[b]
    print("%-11s T=(%+.3f %+.3f %+.3f) loc=%s" % (b, *pb.matrix.translation, tuple(round(v,3) for v in pb.location)))
w = CL.Watch([ob]); geo = w.geo(bpy.context.evaluated_depsgraph_get())
for b in ("weapon_L","weapon_R"):
    vs = geo.get(b, ([],[]))[0]
    if vs: print("%-9s x %+.3f..%+.3f y %+.3f..%+.3f z %+.3f..%+.3f n=%d" % (b,
        min(v.x for v in vs), max(v.x for v in vs), min(v.y for v in vs), max(v.y for v in vs),
        min(v.z for v in vs), max(v.z for v in vs), len(vs)))
