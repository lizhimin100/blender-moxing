"""
build_buildings.py —— 装配：焊接 → 切长条 → 面剔除 → 顶点 AO → 切块 → 骨骼动画 → GLB

节点/骨骼结构（1 个蒙皮网格，1 个材质，1 draw call）：

    Armature
      └─ stage_00 … stage_12          ← build 只动这一层
           └─ chunk_00_00 …           ← destroy 只动这一层
      └─ dust_00 … dust_12            ← 扬尘，destroy 里 scale 0→2.2→0

为什么用骨骼而不是普通节点：
  工单要求"每座 1 个材质、draw call ≤2"，同时又要求 chunk 级独立运动。
  普通节点必须一块一个 mesh，draw call 会等于块数；蒙皮网格把所有块合进
  1 个 primitive，骨骼负责各自的位移/旋转，两个要求才能同时成立。
"""
import json
import math
import os

import numpy as np
import sys

from gltf import Model, quat_from_euler
from buildings import BUILD_INDEX, STAGES, STAGE_NAME, S_SCAF, S_RUB
from weld import weld_parts
from dedup_faces import dedup
from chunks import subdivide, make_chunks, add_dust
from snap_wood import snap as snap_wood
import detail
from ao import bake_vertex_ao, bake_poly_vcol
import atlas

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEX = os.path.join(ROOT, "assets", "warband", "textures")
OUT = os.path.join(ROOT, "assets", "warband", "buildings")

DUR_BUILD = 4.8
DUR_DESTROY = 3.8
ATLAS_ON = os.environ.get("NO_ATLAS", "") != "1"

# 全包共用的 15 套材质 → 一张 2048 图集（4×4），六座 GLB 共享同一组贴图
ATLAS_MATS = [
    "cloth_team", "ember", "emblem", "gold", "leather", "plaster", "shingle",
    "steel", "steel_dark", "stone", "stone_dark", "thatch", "window", "wood",
    "wood_dark",
]
_ATLAS = None


def ensure_atlas():
    global _ATLAS
    if _ATLAS is None:
        _ATLAS = atlas.build("warband", ATLAS_MATS, TEX, verbose=True)
    return _ATLAS


def _local(bones, i):
    b = bones[i]
    p = b["pivot"]
    par = b.get("parent")
    if par is None:
        return p
    pp = bones[par]["pivot"]
    return (p[0] - pp[0], p[1] - pp[1], p[2] - pp[2])


def build_building(bid, verbose=True):
    parts, meta = BUILD_INDEX[bid]()
    n0 = len(parts)
    parts, nweld = weld_parts(parts, max_gap=0.40, verbose=verbose)
    snap_wood(parts, verbose=verbose)
    if detail.LOW:
        import detail as _d
        parts = [p for p in parts if _d.keep(p)]
    parts = subdivide(parts, max_len=2.35)
    # 多面体不参与按盒切分（会把楔形切碎），切块阶段按质心归并
    dedup(parts, verbose=verbose)
    bake_vertex_ao(parts, verbose=verbose)
    bake_poly_vcol(parts, verbose=verbose)

    bones, bone_parts, chunk_meta, stage_meta = make_chunks(parts, max_per_stage=10)
    parts = add_dust(parts, bones, bone_parts, stage_meta)

    m = Model(bid)
    m.set_texture_dir(TEX, "../textures")
    if ATLAS_ON:
        region, files = ensure_atlas()
        missing = sorted({p["mat"] for p in parts} - set(region))
        if missing:
            raise RuntimeError(f"{bid}: 材质未进图集 {missing}")
        m.add_atlas_material(bid, files)
        m.atlas = region
    ids, mnode, _skin = m.add_skinned_building(parts, bones,
                                               mesh_name=f"{bid}_mesh")
    rest = {ids[i]: _local(bones, i) for i in range(len(bones))}
    stage_ids = {s: ids[sm["bone"]] for s, sm in stage_meta.items()}
    total_h = max(sm["hi"][1] for sm in stage_meta.values())

    # ---------------- 建造
    chans = []
    stage_info = []
    for (stage, sname, a, b) in STAGES:
        if stage not in stage_meta:
            continue
        drop = stage_meta[stage]["hi"][1] + 0.45
        t0, t1 = a * DUR_BUILD, b * DUR_BUILD
        over = t0 + (t1 - t0) * 0.86
        keys = [
            (0.0, (0, -drop, 0)),
            (round(t0, 3), (0, -drop, 0)),
            (round(over, 3), (0, 0.038, 0)),
            (round(t1, 3), (0, 0.0, 0)),
            (DUR_BUILD, (0, 0.0, 0)),
        ]
        chans.append((stage_ids[stage], "translation", keys))
        stage_info.append({"stage": stage, "name": sname,
                           "t0": round(t0, 3), "t1": round(t1, 3)})
    # 复位 chunk（防止上一段动画的旋转/位移残留）
    for cm in chunk_meta:
        chans.append((ids[cm["bone"]], "translation", [(0.0, (0, 0, 0)), (DUR_BUILD, (0, 0, 0))]))
        chans.append((ids[cm["bone"]], "rotation", [(0.0, quat_from_euler(0, 0, 0)),
                                                    (DUR_BUILD, quat_from_euler(0, 0, 0))]))
    if S_SCAF in stage_ids:
        a = next(x[2] for x in STAGES if x[0] == S_SCAF) * DUR_BUILD
        nid = stage_ids[S_SCAF]
        chans.append((nid, "scale", [
            (0.0, (0.02, 0.02, 0.02)),
            (round(a, 3), (0.02, 0.02, 0.02)),
            (round(a + 0.035 * DUR_BUILD, 3), (1.0, 1.0, 1.0)),
            (round(0.93 * DUR_BUILD, 3), (1.0, 1.0, 1.0)),
            (DUR_BUILD, (0.02, 0.02, 0.02)),
        ]))
    if S_RUB in stage_ids:
        chans.append((stage_ids[S_RUB], "scale", [(0.0, (0.001,) * 3), (DUR_BUILD, (0.001,) * 3)]))
    m.add_animation("build", chans, DUR_BUILD, rest, extras={"kind": "construction"})

    # ---------------- 摧毁：chunk 级自由落体
    dch = []
    final_top = 0.0
    order = sorted(chunk_meta, key=lambda c: (c["pivot"][1], c["pivot"][0], c["pivot"][2]))
    n = max(len(order), 1)
    for i, cm in enumerate(order):
        px, py, pz = cm["pivot"]
        ang = (18.0 + (i * 13) % 38) * (1 if i % 2 else -1)
        angz = (4.0 + (i * 7) % 5) * (1 if i % 3 else -1)
        yaw = (12.0 + (i * 11) % 16) * (1 if i % 4 else -1)
        # 细长的块（多是饰件）转角收敛，否则一块 6 m 长的饰条倒下来会比房子还高
        big = max(cm["size"][0], cm["size"][2], cm["height"])
        ang *= float(np.clip(2.2 / max(big, 1e-3), 0.22, 1.0))
        # 落地堆叠 + 顶面封顶：保证末帧废墟不超过 3.6 m，同时不穿地
        qx, qy, qz, qw = quat_from_euler(ang * 1.02, yaw, angz)
        R = np.array([
            [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
            [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
            [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)],
        ])
        rel = []
        for dxc in (-cm["size"][0] / 2, cm["size"][0] / 2):
            for dyc in (0.0, cm["height"]):
                for dzc in (-cm["size"][2] / 2, cm["size"][2] / 2):
                    rel.append(float(R[1] @ np.array([dxc, dyc, dzc])))
        top_rel = max(rel)
        low_rel = min(rel)
        lift = -low_rel
        base_y = 0.08 + (i / n) * 0.70 + (cm["height"] * 0.05) + lift
        # 允许略沉入地面（Ground 会盖住），保证末帧顶面不超过 3.5 m
        rest_y = min(base_y, 3.50 - top_rel)
        dx = (0.10 + 0.55 * ((i * 37) % 7) / 6) * (1 if i % 2 else -1)
        dz = (0.08 + 0.50 * ((i * 53) % 5) / 4) * (1 if i % 3 else -1)
        t0 = 0.025 + i * 0.0055
        fall = min(0.52, 0.30 + py * 0.014)
        land = min(DUR_DESTROY - 0.55, t0 + fall)
        b1 = land + 0.06
        b2 = land + 0.12
        b3 = land + 0.18
        b4 = land + 0.24
        b5 = land + 0.30
        st = land + 0.40
        dy = rest_y - py
        # 自由落体：位移按 (t/t1)^2
        f1 = t0 + (land - t0) * 0.42
        f2 = t0 + (land - t0) * 0.72
        f3 = t0 + (land - t0) * 0.90
        drop1 = dy * 0.18 ** 2 * 0.0 + dy * (0.42 ** 2)
        drop2 = dy * (0.72 ** 2)
        drop3 = dy * (0.90 ** 2)
        dch.append((ids[cm["bone"]], "translation", [
            (0.0, (0, 0, 0)),
            (round(t0, 3), (0, 0, 0)),
            (round(f1, 3), (dx * 0.15, drop1, dz * 0.15)),
            (round(f2, 3), (dx * 0.55, drop2, dz * 0.55)),
            (round(f3, 3), (dx * 0.85, drop3, dz * 0.85)),
            (round(land, 3), (dx, dy, dz)),
            (round(b1, 3), (dx * 1.02, dy + 0.35, dz * 1.02)),
            (round(b2, 3), (dx * 1.01, dy + 0.02, dz * 1.01)),
            (round(b3, 3), (dx * 1.03, dy + 0.12, dz * 1.03)),
            (round(b4, 3), (dx * 1.02, dy + 0.01, dz * 1.02)),
            (round(b5, 3), (dx * 1.02, dy + 0.04, dz * 1.02)),
            (round(st, 3), (dx * 1.02, dy, dz * 1.02)),
            (DUR_DESTROY, (dx * 1.02, dy, dz * 1.02)),
        ]))

        final_top = max(final_top, rest_y + top_rel)
        dch.append((ids[cm["bone"]], "rotation", [
            (0.0, quat_from_euler(0, 0, 0)),
            (round(t0, 3), quat_from_euler(0, 0, 0)),
            (round(f2, 3), quat_from_euler(ang * 0.18, yaw * 0.2, angz * 0.3)),
            (round(land, 3), quat_from_euler(ang, yaw, angz)),
            (round(b1, 3), quat_from_euler(ang * 1.14, yaw * 1.1, angz * 1.2)),
            (round(b2, 3), quat_from_euler(ang * 0.96, yaw * 0.98, angz * 0.94)),
            (round(st, 3), quat_from_euler(ang * 1.02, yaw * 1.0, angz * 1.0)),
            (DUR_DESTROY, quat_from_euler(ang * 1.02, yaw * 1.0, angz * 1.0)),
        ]))
    # 扬尘：随各阶段块落地炸开
    for s, sm in sorted(stage_meta.items()):
        if s == S_RUB:
            continue
        bidx = [c for c in chunk_meta if c["stage"] == s]
        if bidx:
            tl = min(0.025 + order.index(c) * 0.0055 + min(0.52, 0.30 + c["pivot"][1] * 0.014)
                     for c in bidx)
        else:
            tl = 0.5
        db = next(b for b in bones if b["name"] == f"dust_{s:02d}")
        di = bones.index(db)
        dch.append((ids[di], "scale", [
            (0.0, (0.001,) * 3),
            (round(max(0.0, tl - 0.02), 3), (0.001,) * 3),
            (round(tl + 0.10, 3), (1.6, 1.6, 1.6)),
            (round(tl + 0.30, 3), (2.2, 2.2, 2.2)),
            (round(tl + 0.55, 3), (0.001,) * 3),
            (DUR_DESTROY, (0.001,) * 3),
        ]))
    if S_RUB in stage_ids:
        dch.append((stage_ids[S_RUB], "scale", [
            (0.0, (0.001,) * 3),
            (round(0.20 * DUR_DESTROY, 3), (0.001,) * 3),
            (round(0.66 * DUR_DESTROY, 3), (1.0, 1.0, 1.0)),
            (DUR_DESTROY, (1.0, 1.0, 1.0)),
        ]))
    m.add_animation("destroy", dch, DUR_DESTROY, rest, extras={"kind": "destruction"})

    # ---------------- 静止：把所有可动骨复位
    ich = []
    for s, sid in stage_ids.items():
        ich.append((sid, "translation", [(0.0, (0, 0, 0)), (1.0, (0, 0, 0))]))
        ich.append((sid, "scale", [(0.0, (0.02,) * 3 if s == S_SCAF else
                                    ((0.001,) * 3 if s == S_RUB else (1.0,) * 3)),
                                   (1.0, (0.02,) * 3 if s == S_SCAF else
                                    ((0.001,) * 3 if s == S_RUB else (1.0,) * 3))]))
    for cm in chunk_meta:
        ich.append((ids[cm["bone"]], "translation", [(0.0, (0, 0, 0)), (1.0, (0, 0, 0))]))
        ich.append((ids[cm["bone"]], "rotation", [(0.0, quat_from_euler(0, 0, 0)),
                                                  (1.0, quat_from_euler(0, 0, 0))]))
    for b in bones:
        if b["name"].startswith("dust_"):
            di = bones.index(b)
            ich.append((ids[di], "scale", [(0.0, (0.001,) * 3), (1.0, (0.001,) * 3)]))
    m.add_animation("static", ich, 1.0, rest, extras={"kind": "idle"})

    m.save(os.path.join(OUT, f"{bid}.glb"))

    boxes = sum(len(v) for v in bone_parts.values())
    rep = {
        "cn": meta["cn"], "boxes": boxes, "boxes_raw": n0,
        "stages": len(stage_meta), "chunks": len(chunk_meta),
        "nodes": len(m.nodes), "bones": len(bones),
        "height": round(total_h, 2),
        "materials": len(m.materials),
        "draw_calls": 2,          # 1 个蒙皮网格 + 1 次阴影
        "triangles": _tri_count(m),
        "stage_times": stage_info,
        "team_zones": meta["team_zones"],
        "merlons": meta.get("merlons", 0),
        "rubble_height": round(max(final_top, 0.0), 2),
        "volumes": meta.get("volumes", []),
        "roof": meta.get("roof", ""),
    }
    if verbose:
        print(f"  [{bid}] {meta['cn']} boxes={boxes} chunks={len(chunk_meta)} "
              f"nodes={len(m.nodes)} bones={len(bones)} h={total_h:.2f} "
              f"tris={rep['triangles']} "
              f"bytes={os.path.getsize(os.path.join(OUT, bid + '.glb'))}")
    return rep


def _tri_count(m):
    tot = 0
    for mesh in m.meshes:
        for pr in mesh["primitives"]:
            tot += m.accessors[pr["indices"]]["count"] // 3
    return tot


def build_all():
    os.makedirs(OUT, exist_ok=True)
    out = {}
    for bid in BUILD_INDEX:
        out[bid] = build_building(bid)
    with open(os.path.join(OUT, "_buildings_report.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        for a in args:
            r = build_building(a)
    else:
        build_all()
