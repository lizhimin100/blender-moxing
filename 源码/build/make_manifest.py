"""
make_manifest.py —— 生成「纯建筑」资产清单

预览台与 Godot 侧共用同一份清单：
  glb   ：相对 preview/index.html 的路径（浏览器 fetch 用）
  godot ：res:// 路径（拷进 Godot 工程后直接可用）
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WB = os.path.join(ROOT, "assets", "warband")

BUILD_META = [
    ("townhall",   "城镇大厅", "门廊塔 + 交叉山墙 + 钟楼"),
    ("barracks",   "兵营",     "瞭望塔 + 营门木栅"),
    ("blacksmith", "铁匠铺",   "单坡薄壳 + 外露炉膛"),
    ("farm",       "农场",     "陡坡谷仓 + 筒仓"),
    ("watchtower", "哨塔",     "实体基座 + 观景廊"),
    ("lumbermill", "伐木场",   "敞棚 + 原木堆"),
]


def main():
    man = {"buildings": []}
    for bid, cn, note in BUILD_META:
        p = os.path.join(WB, "buildings", bid + ".glb")
        if not os.path.exists(p):
            continue
        man["buildings"].append({
            "id": bid, "cn": cn, "kind": "building", "note": note,
            "glb": f"../assets/warband/buildings/{bid}.glb",
            "godot": f"res://assets/warband/buildings/{bid}.glb",
        })

    # 施工阶段 / 尺寸 / 构件数并进清单，前端与运行时都不用硬编码
    rep_p = os.path.join(WB, "buildings", "_buildings_report.json")
    if os.path.exists(rep_p):
        with open(rep_p, encoding="utf-8") as f:
            rep = json.load(f)
        for e in man["buildings"]:
            r = rep.get(e["id"])
            if r:
                e["height"] = r["height"]
                e["boxes"] = r["boxes"]
                e["materials"] = r.get("materials", 1)
                e["draw_calls"] = r.get("draw_calls", 2)
                e["chunks"] = r.get("chunks", 0)
                e["triangles"] = r.get("triangles", 0)
                e["rubble_height"] = r.get("rubble_height", 0)
                e["roof"] = r.get("roof", "")
                e["stage_times"] = r["stage_times"]
                e["team_zones"] = r.get("team_zones", [])

    out = os.path.join(WB, "manifest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    print(f"manifest: {len(man['buildings'])} buildings -> {out}")


if __name__ == "__main__":
    main()
