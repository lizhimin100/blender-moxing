import sys, os, bpy
HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path: sys.path.insert(0, HERE)
import shotlib as S, keep_model
for ob in list(bpy.data.objects): bpy.data.objects.remove(ob, do_unlink=True)
objs, st = keep_model.build(smooth=True, unwrap=False, bevel=True)
print("tris", st["tris"], "mats", st["materials"])
S.OUTSHOT = r"D:/测试一/docs/城镇大厅二本"
os.makedirs(S.OUTSHOT, exist_ok=True)
S.RES, S.SAMP = 1100, 48
S.setup_world(); S.ground_plane()
S.shot("预览_45x38.png", objs, 45, 38, 1.06)
S.shot("预览_正面.png", objs, 0, 12, 1.04)
