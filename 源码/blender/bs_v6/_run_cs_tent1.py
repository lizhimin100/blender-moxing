import sys, json
sys.path.insert(0, r"D:/测试一/blender/bs_v6")
import cs_build
r = cs_build.build_one("初级帐篷", detail="low")
print("CS_RECEIPT", json.dumps({"file": r["file"], "ok": r["check"]["ok"],
      "SCAF_OVER": r["check"]["SCAF_OVER"], "H": r["height"]}, ensure_ascii=False))
