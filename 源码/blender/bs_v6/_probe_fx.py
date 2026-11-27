"""_probe_fx.py —— 训练态门与发光件探针（一次性，可删）"""
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import st_fx as fx
import st_kit as st
import br_model

st.clear_scene()
m = br_model.Model(False, unwrap=False).build()
items = list(m.items)
st.bake_transforms(items)
bpy.context.view_layer.update()


def bb(names):
    rows = []
    for it in items:
        ob = it[0]
        if not ob.name.startswith(names):
            continue
        pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        rows.append((ob.name, round(min(p.x for p in pts), 2), round(max(p.x for p in pts), 2),
                     round(min(p.y for p in pts), 2), round(max(p.y for p in pts), 2),
                     round(min(p.z for p in pts), 2), round(max(p.z for p in pts), 2)))
    return rows


for r in bb(("gate_leaf",))[:4]:
    print("BEFORE", r)
n = fx.open_doors(items, ("gate_leaf", "gate_seam", "gate_iron"), 104.0)
bpy.context.view_layer.update()
print("moved", n)
for r in bb(("gate_leaf",))[:4]:
    print("AFTER ", r)
f = fx.fx_barracks()
print("fx parts", len(f))
for it in f[:3]:
    ob = it[0]
    print("  ", ob.name, ob.data.materials[0].name if ob.data.materials else None,
          ob.dimensions[:])
mat = bpy.data.materials.get("glow")
b = next((n2 for n2 in mat.node_tree.nodes if n2.type == "BSDF_PRINCIPLED"), None)
print("glow emission", tuple(round(v, 2) for v in b.inputs["Emission Color"].default_value),
      b.inputs["Emission Strength"].default_value)
