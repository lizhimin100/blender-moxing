"""
check_floating.py —— 孤立构件检测（连通性 + 接地）

把每个长方体按 eps 膨胀后做并查集，得到"物body"连通块：
  · 任何不接地、且与主体不连通的连通块 = 悬空件（必须有旗杆/托架连回去，否则就是浮空）
  · 同时报出每块的最低点，方便判断是"挂在外墙上"还是"飘在空中"

用法： python build/check_floating.py [--eps 0.02]
"""
import sys
import argparse

import numpy as np

from buildings import BUILD_INDEX
from weld import weld_parts

EPS = 0.02


def find(n, parent):
    while parent[n] != n:
        parent[n] = parent[parent[n]]
        n = parent[n]
    return n


def union(a, b, parent):
    ra, rb = find(a, parent), find(b, parent)
    if ra != rb:
        parent[rb] = ra


def analyze(name, eps=EPS, verbose=True, welded=True):
    parts, meta = BUILD_INDEX[name]()
    if welded:
        parts, _ = weld_parts(parts, max_gap=0.40, verbose=False)
    n = len(parts)
    c = np.array([p["box"][:3] for p in parts], dtype=np.float64)
    s = np.array([p["box"][3:] for p in parts], dtype=np.float64)

    parent = list(range(n))
    half = s / 2.0

    # 必须三轴同时重叠才算接触：|c_i - c_j| <= (h_i + h_j) + eps
    ok = np.ones((n, n), dtype=bool)
    for axis in (0, 1, 2):
        d = np.abs(c[:, axis][:, None] - c[:, axis][None, :])
        lim = half[:, axis][:, None] + half[:, axis][None, :] + eps
        ok &= d <= lim
    ii, jj = np.nonzero(np.triu(ok, 1))
    for a, b in zip(ii.tolist(), jj.tolist()):
        union(a, b, parent)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i, parent), []).append(i)

    comps = []
    for root, idx in groups.items():
        idx = np.array(idx)
        y0 = float((c[idx, 1] - half[idx, 1]).min())
        y1 = float((c[idx, 1] + half[idx, 1]).max())
        x0 = float((c[idx, 0] - half[idx, 0]).min())
        x1 = float((c[idx, 0] + half[idx, 0]).max())
        z0 = float((c[idx, 2] - half[idx, 2]).min())
        z1 = float((c[idx, 2] + half[idx, 2]).max())
        comps.append({
            "n": len(idx), "idx": idx, "y0": y0, "y1": y1,
            "box": (x0, x1, y0, y1, z0, z1),
            "mats": sorted({parts[i]["mat"] for i in idx}),
        })

    # 每个悬空块到其它块的最小间隙（逐构件对的 L∞ 间距），用来区分"差几厘米"和"真飘着"
    for r in comps:
        best = 1e9
        mine = r["idx"]
        for o in comps:
            if o is r:
                continue
            other = o["idx"]
            sep = None
            for axis in (0, 1, 2):
                d = np.abs(c[mine, axis][:, None] - c[other, axis][None, :])
                lim = half[mine, axis][:, None] + half[other, axis][None, :]
                g = d - lim
                sep = g if sep is None else np.maximum(sep, g)
            best = min(best, float(sep.min()))
        r["gap"] = best

    comps.sort(key=lambda r: -r["n"])
    grounded = [r for r in comps if r["y0"] <= 0.03]
    floating = [r for r in comps if r["y0"] > 0.03]

    if verbose:
        print(f"\n=== {name} ({meta['cn']})  {n} boxes / {len(comps)} 连通块 ===")
        print(f"  接地块 {len(grounded)}，悬空块 {len(floating)}")
        if floating:
            for r in floating:
                print(f"  ! {r['n']:>3} boxes  y {r['y0']:5.2f}–{r['y1']:5.2f}  "
                      f"x {r['box'][0]:+6.2f}..{r['box'][1]:+6.2f}  "
                      f"z {r['box'][4]:+6.2f}..{r['box'][5]:+6.2f}  "
                      f"缝 {r['gap'] * 100:5.1f}cm  {r['mats']}")
    return comps, floating


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eps", type=float, default=EPS)
    ap.add_argument("only", nargs="*", default=None)
    a = ap.parse_args()

    names = a.only or list(BUILD_INDEX)
    total = 0
    for nm in names:
        _, fl = analyze(nm, a.eps)
        total += len(fl)
    print(f"\n悬空连通块合计：{total}")


if __name__ == "__main__":
    main()
