import sys, bpy
from mathutils import Vector
p = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=p)
for ob in bpy.context.scene.objects:
    if ob.type != "MESH" or not any(ob.data.materials): continue
    me = ob.data
    for poly in me.polygons:
        n = (ob.matrix_world.to_3x3() @ poly.normal).normalized()
        if abs(n.z) < 0.9: continue
        pts = [ob.matrix_world @ me.vertices[i].co for i in poly.vertices]
        z = sum(q.z for q in pts)/len(pts)
        if z > 0.12: continue
        xs=[q.x for q in pts]; ys=[q.y for q in pts]
        area = (max(xs)-min(xs))*(max(ys)-min(ys))
        if area > 0.35:
            print("FLAT z=%.3f area=%.2f x %.2f..%.2f y %.2f..%.2f mat=%s" % (
                z, area, min(xs), max(xs), min(ys), max(ys),
                me.materials[poly.material_index].name))
