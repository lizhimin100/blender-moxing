import sys, bpy
HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path: sys.path.insert(0, HERE)
import keep_model, bslib as L
for ob in list(bpy.data.objects): bpy.data.objects.remove(ob, do_unlink=True)
m = keep_model.Model(False, unwrap=False).build()
bpy.context.view_layer.update()
lo = [1e9]*3; hi=[-1e9]*3
tris = 0
for it in m.items:
    ob = it[0]
    ob.data.calc_loop_triangles(); tris += len(ob.data.loop_triangles)
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        for i in range(3):
            lo[i]=min(lo[i],p[i]); hi[i]=max(hi[i],p[i])
print("KEEP items=%d tris=%d bbox %s .. %s size %s" % (len(m.items), tris,
      [round(v,2) for v in lo], [round(v,2) for v in hi],
      [round(hi[i]-lo[i],2) for i in range(3)]))
