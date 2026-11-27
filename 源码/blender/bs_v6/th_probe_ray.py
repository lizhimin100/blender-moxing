"""th_probe_ray.py -- 从正面打进拱门，看命中谁。"""
import importlib, sys
import bpy
from mathutils import Vector
HERE=r"D:/测试一/blender/bs_v6"
if HERE not in sys.path: sys.path.insert(0,HERE)
for _m in ("bslib","br_model","th_model"):
    if _m in sys.modules: importlib.reload(sys.modules[_m])
import th_model
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
m=th_model.Model(False, unwrap=False).build()
bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get()
for (x,z) in ((0,1.2),(0,2.2),(0,3.0),(0,3.6),(0,4.1),(-0.6,2.0),(0.6,2.0),(0,0.9)):
    hit,loc,nor,idx,ob,mat = bpy.context.scene.ray_cast(dg, Vector((x,12,z)), Vector((0,-1,0)))
    print("(%4.1f,%4.1f) ->" % (x,z), ob.name if hit else "MISS", tuple(round(v,2) for v in loc) if hit else "")
