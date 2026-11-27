"""mk_godot_data.py —— 把九座的显影区间写成 Godot 侧的数据表。

    python build/mk_godot_data.py

读 `docs/建造系统/参数/<建筑>.json`，写 `godot/build_reveal_data.gd`。
用 .gd 常量而不是 .json，是为了绕开"导出时非资源文件不进 PCK"的坑 ——
Godot 导出预设默认不带 *.json，忘了加就会在导出版里读不到参数。
"""
import json
import os
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "建造系统", "参数")
OUT = os.path.join(ROOT, "godot", "build_reveal_data.gd")

TPL = '''class_name BuildRevealData
extends RefCounted
## 九座建筑的显影区间 —— 由 docs/建造系统/参数/<建筑>.json 生成，别手改。
##
##   h     总高（米，模型自身 Y 轴）
##   z0    显影起点：0% 时露到的高度（台基顶）
##   z1    显影终点：100%（= h）
##   t0/t1 这两个时刻之间，建筑从 z0 长到 z1（秒，相对 build 动画）
##   t_end 整条 build 动画时长（撤架 + 清场都在 t1 之后）
##
## 重新生成：python build/mk_godot_data.py

const TABLE := {
__TABLE__
}
'''


def main():
    lines = []
    for p in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        if "_" in os.path.basename(p)[:-5]:
            continue
        j = json.load(open(p, encoding="utf-8"))
        lines.append(
            '\t"%s": {"h": %.2f, "z0": %.2f, "z1": %.2f, "t0": %.2f, "t1": %.2f, "t_end": %.2f},'
            % (j["id"], j["height"], j["z0"], j["z_rev1"],
               j["t_rev0"], j["t_rev1"], j["t_end"]))
    src = TPL.replace("__TABLE__", "\n".join(lines))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"→ {OUT}  {len(lines)} 座")


if __name__ == "__main__":
    main()
