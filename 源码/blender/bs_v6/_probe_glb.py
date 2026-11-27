import sys, bpy
from mathutils import Vector
p = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=p)
for ob in bpy.context.scene.objects:
    if ob.type != "MESH":
        print("OBJ", ob.type, ob.name, tuple(round(v,2) for v in ob.location)); continue
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    print("MESH", ob.name, "z %.2f..%.2f" % (lo[2], hi[2]), "y %.2f..%.2f" % (lo[1], hi[1]), "verts", len(pts))
