import os, sys
import bpy
HERE = r"D:/测试一/blender/bs_v6"; ROOT = r"D:/测试一"
sys.path.insert(0, HERE)
import iconlib, shotlib as S
SRC = os.path.join(ROOT, "assets", "建筑", "零件")
OUT = os.path.join(ROOT, "docs", "图标", "试拍")
os.makedirs(OUT, exist_ok=True)
iconlib.clear_scene()
bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, "双扇石门.glb"))
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.context.view_layer.update()
xs = [(o.matrix_world @ v.co).x for o in objs for v in o.data.vertices]
zs = [(o.matrix_world @ v.co).z for o in objs for v in o.data.vertices]
ys = [(o.matrix_world @ v.co).y for o in objs for v in o.data.vertices]
print("BBOX x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (
    min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
S.shot(os.path.join(OUT, "_门检查.png"), objs, -18, 8, 1.05, res=760, samples=24)
print("DOOR_OK")
