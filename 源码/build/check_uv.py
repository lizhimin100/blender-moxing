"""check_uv.py —— 逐面核对图集 UV 是否落在该材质自己的格子里。

贴图错格的典型症状：某个材质的面上出现别的材质的横向条纹（例如屋面上出现木色条），
看起来像"构件没粘住"。这里直接从几何算 UV，不依赖渲染。

用法：python build/check_uv.py [building_id ...]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from buildings import BUILD_INDEX, STAGE_NAME          # noqa: E402
from weld import weld_parts                            # noqa: E402
from chunks import subdivide                          # noqa: E402
from dedup_faces import dedup                         # noqa: E402
from gltf import box_face_quads, _breakpoints, _bilinear   # noqa: E402

MATS = sorted([
    "cloth_team", "ember", "emblem", "gold", "leather", "plaster", "shingle",
    "steel", "steel_dark", "stone", "stone_dark", "thatch", "window", "wood",
    "wood_dark",
])

SIZE = 2048
CELL = SIZE // 4
PAD = 4
ART = CELL - PAD * 2


def region_of(mat):
    i = MATS.index(mat)
    x, y = (i % 4) * CELL + PAD, (i // 4) * CELL + PAD
    return (x / SIZE, y / SIZE, (x + ART) / SIZE, (y + ART) / SIZE)


def prep(bid):
    parts, meta = BUILD_INDEX[bid]()
    parts, _ = weld_parts(parts, max_gap=0.40, verbose=False)
    parts = subdivide(parts)
    dedup(parts, verbose=False)
    return parts, meta


def cell_of(u, v):
    return (min(3, int(np.floor(u * 4))), min(3, int(np.floor(v * 4))))


def uv1_vertices(uvs, region):
    """复刻 gltf.add_parts 里的图集重映射，返回 [(u1,v1,uf,vf), ...]。"""
    u0, v0, u1, v1 = region
    out = []
    bu = _breakpoints(min(u for u, _ in uvs), max(u for u, _ in uvs))
    bv = _breakpoints(min(v for _, v in uvs), max(v for _, v in uvs))
    for (ul, uh, uf) in bu:
        for (vl, vh, vf) in bv:
            su0 = (ul - uvs[0][0]) / ((uvs[1][0] - uvs[0][0]) or 1e-9)
            su1 = (uh - uvs[0][0]) / ((uvs[1][0] - uvs[0][0]) or 1e-9)
            tv0 = (vl - uvs[0][1]) / ((uvs[3][1] - uvs[0][1]) or 1e-9)
            tv1 = (vh - uvs[0][1]) / ((uvs[3][1] - uvs[0][1]) or 1e-9)
            for (s, t) in ((su0, tv0), (su1, tv0), (su1, tv1), (su0, tv1)):
                uv = _bilinear(uvs, s, t)
                out.append((u0 + (uv[0] - uf) * (u1 - u0),
                            v0 + (uv[1] - vf) * (v1 - v0), uf, vf))
    return out


def main():
    bids = sys.argv[1:] or list(BUILD_INDEX)
    bad_total = 0
    for bid in bids:
        parts, _ = prep(bid)
        wrong = {}
        nfaces = 0
        for p in parts:
            mat = p["mat"]
            region = region_of(mat)
            expect = cell_of((region[0] + region[2]) / 2, (region[1] + region[3]) / 2)
            for fi, n, pos, uvs in box_face_quads(p["box"], p["tile"]):
                if p.get("faces") is not None and not p["faces"][fi]:
                    continue
                nfaces += 1
                for (u, v, uf, vf) in uv1_vertices(uvs, region):
                    got = cell_of(u, v)
                    if got != expect:
                        k = (mat, f"{got}->{expect}", STAGE_NAME.get(p["stage"], "?"))
                        wrong[k] = wrong.get(k, 0) + 1
        bad = sum(wrong.values())
        bad_total += bad
        print(f"{bid:11s} 面 {nfaces:5d}  UV 异常顶点 {bad:6d}  {'OK' if bad == 0 else 'FAIL'}")
        for k, v in sorted(wrong.items(), key=lambda kv: -kv[1])[:4]:
            print(f"    {k[0]:11s} 落在 {k[1]:14s} 阶段={k[2]}  {v} 个顶点")
    print(f"\n合计 UV 异常顶点：{bad_total}")
    return 0 if bad_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
