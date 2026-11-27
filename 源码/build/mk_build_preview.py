"""mk_build_preview.py —— 把九座的建造参数灌进预览台模板，生成 建造系统.html。

    python build/mk_build_preview.py

参数源在 `docs/建造系统/参数/<建筑>.json`（资产目录只留 GLB + 图标）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "blender", "bs_v6"))
from assets_path import asset_path  # noqa: E402

ASSET = asset_path()
DOCS = os.path.join(ROOT, "docs", "建造系统")
TPL = os.path.join(ROOT, "build", "build_site_shell.html")
OUT = os.path.join(ROOT, "建造系统.html")

ORDER = ["折壳入口", "地牢", "地下城入口", "酒馆内部", "箭塔", "城镇大厅", "兵营", "铁匠铺",
         "农场", "哨塔", "伐木场", "神秘圣地", "蒸汽车坊"]


def main():
    items = []
    for cn in ORDER:
        p = os.path.join(DOCS, "参数", f"{cn}.json")
        if not os.path.exists(p):
            print("skip", cn)
            continue
        j = json.load(open(p, encoding="utf-8"))
        chk = j.get("check", {})
        items.append({
            "id": cn,
            "cn": cn,
            "file": "assets/" + os.path.relpath(os.path.join(asset_path(cn), j["file"]), ASSET).replace("\\", "/"),
            "fp": [round(j["footprint"][0], 3), round(j["footprint"][1], 3)],
            "h": round(j["height"], 3),
            "z0": round(j["z0"], 3),
            "t_rev0": round(j["t_rev0"], 3),
            "t_rev1": round(j["t_rev1"], 3),
            "rev": round(j["rev"], 3),
            "t_end": round(j["t_end"], 3),
            "t_clean": round(j["t_clean"], 3),
            "lifts": j["lifts"],
            "nl": j["n_lifts"],
            "kb": int(round(j["bytes"] / 1024)),
            "tri_body": chk.get("tri_body", 0),
            "tri_site": chk.get("tri_site", 0),
        })
    data = {"buildings": items}
    tpl = open(TPL, encoding="utf-8").read()
    html = tpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("→", OUT, len(html) // 1024, "KB", len(items), "buildings")


main()
