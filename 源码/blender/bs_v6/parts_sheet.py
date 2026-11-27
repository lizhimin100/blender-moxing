"""把 13 件零件摆一排出一张检查图（每件独立导回，验证 GLB 本身没问题）。"""
import math, os, sys
import bpy
HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
sys.path.insert(0, HERE)
import iconlib
import shotlib as S

SRC = os.path.join(ROOT, "assets", "建筑", "零件")
names = sorted(f for f in os.listdir(SRC) if f.endswith(".glb"))
iconlib.clear_scene()
x = 0.0
allobjs = []
for i, fn in enumerate(names):
    bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, fn))
    new = [o for o in bpy.context.scene.objects
           if o.type == "MESH" and o.get("pid") != "moved"]
    for o in new:
        o["pid"] = "moved"
        allobjs.append(o)
    for o in new:
        xs = [(o.matrix_world @ v.co).x for v in o.data.vertices]
        ys = [(o.matrix_world @ v.co).y for v in o.data.vertices]
        zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
        # 归到本格中心：xy 居中，z 沉到 0
        dx = x - (min(xs) + max(xs)) * 0.5
        dz = -min(zs)
        o.location.x += dx
        o.location.z += dz
    x += 1.9
bpy.context.view_layer.update()
OUTP = os.path.join(ROOT, "docs", "图标", "试拍")
os.makedirs(OUTP, exist_ok=True)
S.shot(os.path.join(OUTP, "_零件检查.png"), allobjs, 0, 12, 1.04,
       res=1400, samples=24)
print("SHEET_OK", len(allobjs), "件")
