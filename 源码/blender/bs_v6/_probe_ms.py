import sys, bpy
sys.path.insert(0, r"D:/测试一/blender/bs_v6")
import ms_model, st_kit as st
st.clear_scene()
m = ms_model.Model(False, unwrap=False).build()
st.bake_transforms(list(m.items))
rows = []
for it in m.items:
    ob = it[0]
    pts = [v.co for v in ob.data.vertices]
    rows.append((max(p.y for p in pts), min(p.y for p in pts),
                 max(p.z for p in pts), min(p.z for p in pts), ob.name))
rows.sort(reverse=True)
print("FRONT ITEMS:")
for r in rows[:14]:
    print("  ymax %.2f..%.2f z %.2f..%.2f %s" % r)
