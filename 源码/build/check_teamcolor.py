"""
check_teamcolor.py —— 阵营染色可见投影占比 / 高度分布 / 色块数量

判定口径（对应工单 3.3.1 / 3.3.5）：
  * 从 4 个方位、40° 俯角正交投影，逐像素取最近可见面（含背面剔除）；
  * 只统计 TC1 遮罩 > 0 的材质（本包中即 cloth_team / emblem）；
  * 占比 = 染色像素 / 建筑轮廓像素；
  * 高度分布按世界 Y / 建筑总高分为低 0–30% / 中 30–65% / 高 65–100%；
  * 色块数 = 屏幕空间连通域（面积 > 25 px），用于验证"不是只在一处"。

用法：
    python build/check_teamcolor.py           # 检查并返回非零码
    python build/check_teamcolor.py --json    # 输出机器可读
"""
import json
import sys

import numpy as np

from buildings import BUILD_INDEX
from weld import weld_parts
from dedup_faces import dedup
from chunks import subdivide
from raster import render

# v2 §1.5：全部建筑统一 6–9%，且低/中/高三个高度带都要有
TARGET = {
    "townhall": (6.0, 9.0), "barracks": (6.0, 9.0), "blacksmith": (6.0, 9.0),
    "farm": (6.0, 9.0), "watchtower": (6.0, 9.0), "lumbermill": (6.0, 9.0),
}
TC_MATS = {"cloth_team", "emblem"}


def _components(mask, min_area=25):
    seen = np.zeros_like(mask, bool)
    h, w = mask.shape
    n = 0
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or seen[y, x]:
                continue
            stack = [(y, x)]
            seen[y, x] = True
            area = 0
            while stack:
                cy, cx = stack.pop()
                area += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if area >= min_area:
                n += 1
    return n


def measure(name, res=260):
    parts, meta = BUILD_INDEX[name]()
    parts, _ = weld_parts(parts, max_gap=0.40, verbose=False)
    parts = subdivide(parts)
    dedup(parts, verbose=False)
    parts = [p for p in parts if p["stage"] not in (2, 12)]

    cov, low, mid, high, zones = [], 0, 0, 0, 0
    total_tc = 0
    for yaw in (35, 125, 215, 305):
        r = render(parts, res=res, yaw=yaw, elev=40)
        mask = r["mask"]
        if not mask.any():
            continue
        tc = np.isin(r["matid"], [i for i, nm in enumerate(r["names"]) if nm in TC_MATS]) & mask
        cov.append(tc.sum() / mask.sum())
        total_tc += int(tc.sum())
        H = max(p["box"][1] + p["box"][4] / 2 for p in parts)
        y = r["wy"][tc] / max(H, 1e-6)
        low += int((y < 0.30).sum())
        mid += int(((y >= 0.30) & (y < 0.65)).sum())
        high += int((y >= 0.65).sum())
        zones += _components(tc, min_area=max(18, res * res // 3000))
    pct = float(np.mean(cov) * 100) if cov else 0.0
    tot = max(low + mid + high, 1)
    bands = {"low": low / tot, "mid": mid / tot, "high": high / tot}
    return {
        "id": name, "cn": meta["cn"], "pct": round(pct, 2),
        "bands": {k: round(v * 100, 1) for k, v in bands.items()},
        "bands_ok": sum(1 for v in bands.values() if v >= 0.08) >= 3,
        "zones": zones,
        "target": TARGET[name],
        "pct_ok": TARGET[name][0] <= pct <= TARGET[name][1],
    }


def main():
    as_json = "--json" in sys.argv
    rows = []
    bad = 0
    for name in BUILD_INDEX:
        r = measure(name)
        rows.append(r)
        if not r["pct_ok"] or not r["bands_ok"] or r["zones"] < 6:
            bad += 1
        if not as_json:
            print(f"{r['cn']:6s} {r['id']:11s} 染色 {r['pct']:5.2f}% "
                  f"(目标 {r['target'][0]}–{r['target'][1]}%)  "
                  f"低/中/高 {r['bands']['low']:.1f}/{r['bands']['mid']:.1f}/{r['bands']['high']:.1f}  "
                  f"色块 {r['zones']:2d}  {'OK' if r['pct_ok'] and r['bands_ok'] and r['zones'] >= 6 else 'FAIL'}")
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n染色检查：{len(rows) - bad}/{len(rows)} 通过")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
