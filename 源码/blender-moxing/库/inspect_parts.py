"""inspect_parts.py —— 导入 GLB，按连通块拆解报告（位置/大小/材质/主导骨）。

用法：blender -b --factory-startup --python 库/inspect_parts.py -- <glb> [min_verts]
输出：每行一个连通块，按体积排序。
"""
import sys
import bpy
import bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = argv[0]
MINV = int(argv[1]) if len(argv) > 1 else 4

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in list(bpy.context.scene.objects):
    if o.type == "MESH" and o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o, do_unlink=True)

for ob in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
    seen = set(); islands = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]; group = []
        seen.add(v.index)
        while stack:
            cur = stack.pop(); group.append(cur)
            for e in cur.link_edges:
                o2 = e.other_vert(cur)
                if o2.index not in seen:
                    seen.add(o2.index); stack.append(o2)
        islands.append(group)
    print("==== mesh", ob.name, "islands", len(islands))
    rows = []
    for g in islands:
        if len(g) < MINV:
            continue
        co = [v.co for v in g]
        mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
        mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
        cen = sum(co, Vector()) / len(co)
        # dominant group
        counts = {}
        for v in g:
            for ge in me.vertices[v.index].groups:
                nm = ob.vertex_groups[ge.group].name
                counts[nm] = counts.get(nm, 0) + 1
        dom = max(counts.items(), key=lambda kv: kv[1])[0] if counts else "-"
        rows.append((len(g), mn, mx, cen, dom))
    rows.sort(key=lambda r: -r[0])
    for (n, mn, mx, cen, dom) in rows:
        size = mx - mn
        print("  n=%4d  c=(%6.3f,%6.3f,%6.3f)  size=(%5.3f,%5.3f,%5.3f)  z=[%5.3f,%5.3f]  bone=%s"
              % (n, cen.x, cen.y, cen.z, size.x, size.y, size.z, mn.z, mx.z, dom))
    bm.free()
