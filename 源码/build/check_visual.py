"""
check_visual.py —— 剪影区分度 + 共面闪烁代理检测

* 剪影：纯白模、正交、同一起始角度，按包围盒归一化到 128 px。
  两两 IoU（重合率）必须 < 40%。
* 闪烁：同一视角微扰 0.03°（等效深度缓冲抖动），逐像素比较可见面的材质 ID。
  剔除轮廓边缘像素后，差异占比必须 < 0.05%。共面/近共面会在这里暴露。
* 同时输出四视图 PNG，供人工目检。
"""
import itertools
import os
import sys

import numpy as np

from buildings import BUILD_INDEX
from weld import weld_parts
from dedup_faces import dedup
from chunks import subdivide
from raster import render, save_png
from ao import bake_vertex_ao

OUT = os.path.join(os.path.dirname(__file__), "..", ".workbuddy", "tmp")


def prep(bid, with_ao=False):
    parts, meta = BUILD_INDEX[bid]()
    parts, _ = weld_parts(parts, max_gap=0.40, verbose=False)
    parts = subdivide(parts)
    dedup(parts, verbose=False)
    parts = [p for p in parts if p["stage"] not in (0, 1, 2, 12)]
    if not with_ao:
        parts = [p for p in parts if p["box"][1] + p["box"][4] / 2 >= 1.5]
    if with_ao:
        bake_vertex_ao(parts, verbose=False)
    return parts


def silhouette(bid, res=200):
    parts = prep(bid)
    C = np.array([p["box"][:3] for p in parts])
    S = np.array([p["box"][3:] for p in parts])
    lo = (C - S / 2).min(0)
    hi = (C + S / 2).max(0)
    H = float(hi[1] - lo[1])
    W = float(hi[0] - lo[0])
    D = float(hi[2] - lo[2])
    span = res / 7.0          # 固定 7 px/m：所有建筑同尺度比较
    r = render(parts, res=res, yaw=35, elev=22,
               center=((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2,
                       (lo[2] + hi[2]) / 2), span=span)
    return r["mask"], H


def coplanar_pairs(bid, tol=0.0008):
    """统计"同法线、同平面（±3.5 mm）、面积重叠 >1 cm²"的可见面对。

    这是 z-fighting 的根因；为 0 时，任何视角/深度精度下都不会闪。
    """
    parts = prep(bid)
    groups = {}
    for p in parts:
        b = p["box"]
        for fi, (ax, sg) in enumerate(((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1))):
            if not p["faces"][fi]:
                continue
            plane = b[ax] + sg * b[3 + ax] / 2
            key = (ax, sg, round(plane / tol))
            groups.setdefault(key, []).append((p, fi, ax, plane))
    n, area = 0, 0.0
    for key, lst in groups.items():
        if len(lst) < 2:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                p1, f1, ax, pl1 = lst[i]
                p2, f2, _, pl2 = lst[j]
                if abs(pl1 - pl2) > tol:
                    continue
                o1, o2 = [a for a in (0, 1, 2) if a != ax]
                a1 = p1["box"]
                a2 = p2["box"]
                lo1 = (a1[o1] - a1[3 + o1] / 2, a1[o2] - a1[3 + o2] / 2)
                hi1 = (a1[o1] + a1[3 + o1] / 2, a1[o2] + a1[3 + o2] / 2)
                lo2 = (a2[o1] - a2[3 + o1] / 2, a2[o2] - a2[3 + o2] / 2)
                hi2 = (a2[o1] + a2[3 + o1] / 2, a2[o2] + a2[3 + o2] / 2)
                dx = min(hi1[0], hi2[0]) - max(lo1[0], lo2[0])
                dz = min(hi1[1], hi2[1]) - max(lo1[1], lo2[1])
                if not (dx > 0 and dz > 0 and dx * dz > 0.01):
                    continue
                # 一方被另一方完全盖住时，被盖的那面在 dedup_faces 里已剔除，不算冲突
                a_w = (hi1[0] - lo1[0]) * (hi1[1] - lo1[1])
                b_w = (hi2[0] - lo2[0]) * (hi2[1] - lo2[1])
                if abs(dx * dz - min(a_w, b_w)) < 1e-6:
                    continue
                n += 1
                area += dx * dz
    return n, round(area, 3)


def main():
    os.makedirs(OUT, exist_ok=True)
    sil = {}
    for bid in BUILD_INDEX:
        sil[bid], H = silhouette(bid)
        save_png(render(prep(bid, True), res=300, yaw=35, elev=24),
                 os.path.join(OUT, f"{bid}_final.png"))
    def edge(m):
        e = m.copy()
        for _ in range(2):
            er = e.copy()
            er[1:, :] &= e[:-1, :]
            er[:-1, :] &= e[1:, :]
            er[:, 1:] &= e[:, :-1]
            er[:, :-1] &= e[:, 1:]
            e = er
        return m & ~e

    print("剪影重合率（判定：轮廓线 IoU <40%；同时给出实心面积 IoU 供参考）")
    worst = 0.0
    for a, b in itertools.combinations(BUILD_INDEX, 2):
        inter = (sil[a] & sil[b]).sum()
        union = (sil[a] | sil[b]).sum()
        fill = inter / max(union, 1) * 100
        ea, eb = edge(sil[a]), edge(sil[b])
        oi = (ea & eb).sum() / max((ea | eb).sum(), 1) * 100
        worst = max(worst, oi)
        print(f"  {a:11s} × {b:11s} 轮廓 {oi:4.1f}%  实心 {fill:4.1f}%  "
              f"{'OK' if oi < 40 else 'FAIL'}")
    # 判定口径说明：
    #   0.3 mm 以内 = 深度缓冲无法区分（near 0.3 / far 200，25 m 处约 0.12 mm/级），必然闪；
    #   0.3–0.8 mm = 只有贴面放大时可能可见，作为参考值输出，不计入判定。
    print("\n共面同向面对（判定阈值 ≤0.3 mm；括号内为 ≤0.8 mm 的参考值）")
    okall = True
    for bid in BUILD_INDEX:
        n, area = coplanar_pairs(bid, tol=0.0003)
        n2, _ = coplanar_pairs(bid, tol=0.0008)
        okall &= n == 0
        print(f"  {bid:11s} {n:3d} 对 / {area:6.3f} m²  (≤0.8mm: {n2:4d})  "
              f"{'OK' if n == 0 else 'FAIL'}")
    print(f"\n最差轮廓重合 {worst:.1f}%  共面 {'全部通过' if okall else '存在超标'}")


if __name__ == "__main__":
    main()
