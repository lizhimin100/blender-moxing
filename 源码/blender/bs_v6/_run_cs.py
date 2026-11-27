import sys, json
HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path: sys.path.insert(0, HERE)
import cs_build
rep = cs_build.build_one("城镇大厅二本", detail="low")
print("CS_RECEIPT " + json.dumps({k: rep.get(k) for k in
      ("file","bytes","height","footprint","z0","nl","t_end","tri_body","tri_site")},
      ensure_ascii=False))
