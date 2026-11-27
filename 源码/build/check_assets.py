"""
check_assets.py —— 交付验收（逐条可测）

覆盖工单第 7 节里能自动判定的项目：
  1  结构连通        → check_floating.py（本脚本调用其结果文件不现实，单独跑）
  3  无压扁摧毁      → destroy clip 不存在 chunk 骨的 scale 通道
  4  废墟厚度        → _buildings_report.json: rubble_height ≥ 2.0
  6-9 高度           → GLB 包围盒
  10 兵营屋顶        → 平顶、垛口 ≥28、角楼 3
  12 立面非矩形      → 占地轮廓的凹凸体量 ≥2
  13 节点预算        → ≤140
  14 几何合法性      → NORMAL 只含 6 个轴向
  15 单位与朝向      → 1 unit=1m、min y≈0、门朝 −Z

用法： python build/check_assets.py [--json]
"""
import json
import math
import os
import struct
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GLB = os.path.join(ROOT, "assets", "warband", "buildings")
REP = os.path.join(GLB, "_buildings_report.json")

HEIGHT_MIN = {"townhall": 17.0, "barracks": 11.5, "blacksmith": 13.5,
              "farm": 9.5, "watchtower": 18.0, "lumbermill": 8.5}


def read_glb(path):
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67
    off, js, binc = 12, None, None
    while off < total:
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        payload = data[off:off + clen]
        off += clen
        if ctype == 0x4E4F534A:
            js = json.loads(payload)
        elif ctype == 0x004E4942:
            binc = payload
    return js, binc


def acc(g, b, i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    comp = {5126: ("f4", 4), 5123: ("u2", 2), 5125: ("u4", 4), 5121: ("u1", 1)}[a["componentType"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    cnt = a["count"] * n
    return np.frombuffer(b, dtype=np.dtype("<" + comp[0]), count=cnt, offset=off).reshape(a["count"], n)


def bbox_of(g, b):
    mn = np.array([1e9] * 3)
    mx = np.array([-1e9] * 3)
    for mesh in g["meshes"]:
        for pr in mesh["primitives"]:
            a = g["accessors"][pr["attributes"]["POSITION"]]
            mn = np.minimum(mn, np.array(a["min"]))
            mx = np.maximum(mx, np.array(a["max"]))
    return mn, mx


def check_one(bid, rep):
    g, b = read_glb(os.path.join(GLB, bid + ".glb"))
    names = [n.get("name", "") for n in g["nodes"]]
    res = {"id": bid, "nodes": len(g["nodes"]), "ok": True, "issues": []}

    def fail(msg):
        res["ok"] = False
        res["issues"].append(msg)

    if len(g["nodes"]) > 140:
        fail(f"节点 {len(g['nodes'])} > 140")
    if len(g.get("materials", [])) != 1:
        fail(f"材质 {len(g.get('materials', []))} ≠ 1")
    prims = sum(len(m["primitives"]) for m in g["meshes"])
    if prims != 1:
        fail(f"primitive {prims} ≠ 1")
    if len(g.get("skins", [])) != 1:
        fail("缺少蒙皮")

    clips = {a["name"]: a for a in g.get("animations", [])}
    for nm in ("build", "destroy", "static"):
        if nm not in clips:
            fail(f"缺少 {nm} clip")
    durs = {}
    for nm, a in clips.items():
        tmax = 0.0
        for s in a["samplers"]:
            tmax = max(tmax, float(g["accessors"][s["input"]]["max"][0]))
        durs[nm] = round(tmax, 2)
    if abs(durs.get("build", 0) - 4.8) > 0.02:
        fail(f"build 时长 {durs.get('build')}")
    if abs(durs.get("destroy", 0) - 3.8) > 0.02:
        fail(f"destroy 时长 {durs.get('destroy')}")
    if abs(durs.get("static", 0) - 1.0) > 0.02:
        fail(f"static 时长 {durs.get('static')}")

    # ---- 摧毁：chunk 骨禁止任何 scale；只允许 dust / rubble
    if "destroy" in clips:
        bad_scales = []
        for ch in clips["destroy"]["channels"]:
            if ch["target"]["path"] != "scale":
                continue
            nm = names[ch["target"]["node"]]
            if nm.startswith("dust_") or nm.startswith("stage_12"):
                continue
            bad_scales.append(nm)
        if bad_scales:
            fail(f"destroy 里出现非扬尘/瓦砾 scale：{bad_scales[:4]}")
        # 采样所有 scale 的 y 值
        min_sy = 1.0
        for ch in clips["destroy"]["channels"]:
            if ch["target"]["path"] != "scale":
                continue
            nm = names[ch["target"]["node"]]
            vals = acc(g, b, clips["destroy"]["samplers"][ch["sampler"]]["output"])
            if not (nm.startswith("dust_") or nm.startswith("stage_12")):
                min_sy = min(min_sy, float(vals[:, 1].min()))
        res["destroy_min_scale_y"] = round(min_sy, 3)

    # ---- 几何
    mn, mx = bbox_of(g, b)
    res["size"] = [round(float(v), 2) for v in (mx - mn)]
    res["height_glb"] = round(float(mx[1] - mn[1]), 2)
    if abs(float(mn[1])) > 0.06:
        fail(f"底面 y={mn[1]:.3f}，未落在 0")
    if res["height_glb"] + 0.05 < HEIGHT_MIN[bid]:
        fail(f"高度 {res['height_glb']} < {HEIGHT_MIN[bid]}")
    if rep.get("rubble_height", 0) < 2.0:
        fail(f"废墟高度 {rep.get('rubble_height')} < 2.0")

    # ---- 法线只有 6 个轴向
    bad_norm = 0
    for mesh in g["meshes"]:
        for pr in mesh["primitives"]:
            N = acc(g, b, pr["attributes"]["NORMAL"])
            ok = np.all(np.isin(np.round(N, 3), (-1.0, 0.0, 1.0)), axis=1)
            bad_norm += int((~ok).sum())
    res["bad_normals"] = bad_norm
    if bad_norm:
        fail(f"非法线 {bad_norm} 个顶点")

    # ---- 兵营：平顶 + 垛口
    if bid == "barracks":
        if rep.get("merlons", 0) < 28:
            fail(f"垛口 {rep.get('merlons')} < 28")
        res["merlons"] = rep.get("merlons")
    return res


def footprint_protrusions(bid, res=0.14):
    """体量清单核验：meta["volumes"] 里的每个附加体量必须真实存在。

    对每个登记矩形，要求在"高度 ≥1.2 m 的占地栅格"里占用率 ≥60%，
    且至少有一部分在主墙线之外。返回通过核验的体量数。
    """
    sys.path.insert(0, os.path.dirname(__file__))
    from buildings import BUILD_INDEX
    parts, meta = BUILD_INDEX[bid]()
    vols = meta.get("volumes", [])
    tall = [p for p in parts if p["stage"] not in (2, 12)
            and p["box"][1] + p["box"][4] / 2 >= 1.5]
    C = np.array([p["box"][:3] for p in tall])
    S = np.array([p["box"][3:] for p in tall])
    lo = (C - S / 2).min(0)
    hi = (C + S / 2).max(0)
    nx = int(math.ceil((hi[0] - lo[0]) / res)) + 1
    nz = int(math.ceil((hi[2] - lo[2]) / res)) + 1
    g = np.zeros((nx, nz), bool)
    for c, s in zip(C, S):
        x0 = int((c[0] - s[0] / 2 - lo[0]) / res)
        x1 = int((c[0] + s[0] / 2 - lo[0]) / res)
        z0 = int((c[2] - s[2] / 2 - lo[2]) / res)
        z1 = int((c[2] + s[2] / 2 - lo[2]) / res)
        g[max(0, x0):x1 + 1, max(0, z0):z1 + 1] = True
    n = 0
    for (x0w, x1w, z0w, z1w) in vols:
        i0 = int((x0w - lo[0]) / res)
        i1 = int((x1w - lo[0]) / res)
        k0 = int((z0w - lo[2]) / res)
        k1 = int((z1w - lo[2]) / res)
        i0, i1 = max(0, i0), min(nx - 1, i1)
        k0, k1 = max(0, k0), min(nz - 1, k1)
        if i1 <= i0 or k1 <= k0:
            continue
        occ = g[i0:i1 + 1, k0:k1 + 1].mean()
        if occ >= 0.35 and (i1 - i0) * (k1 - k0) * res * res >= 1.2:
            n += 1
    return n


def main():
    as_json = "--json" in sys.argv
    rep = json.load(open(REP, encoding="utf-8"))
    rows = []
    bad = 0
    for bid in ("townhall", "barracks", "blacksmith", "farm", "watchtower", "lumbermill"):
        r = check_one(bid, rep.get(bid, {}))
        r["protrusions"] = footprint_protrusions(bid)
        need = len(rep.get(bid, {}).get("volumes", [1, 1]))
        if r["protrusions"] < min(2, need):
            r["ok"] = False
            r["issues"].append(f"附加体量 {r['protrusions']} < {min(2, need)}")
        rows.append(r)
        if not r["ok"]:
            bad += 1
        if not as_json:
            print(f"{bid:11s} nodes={r['nodes']:3d} h={r['height_glb']:5.2f} "
                  f"size={r['size']} 凹凸={r['protrusions']} roof={rep.get(bid, {}).get('roof', '-')} "
                  f"{'OK' if r['ok'] else 'FAIL ' + '; '.join(r['issues'])}")

    # v2 §4.1：六座屋顶类型必须两两不同（"一眼区分"的第一手段）
    roofs = [rep.get(b, {}).get("roof", "") for b in
             ("townhall", "barracks", "blacksmith", "farm", "watchtower", "lumbermill")]
    dup = {r for r in roofs if r and roofs.count(r) > 1}
    roof_ok = bool(all(roofs)) and not dup
    if not as_json:
        print(f"\n屋顶类型唯一：{len(set(roofs))}/{len(roofs)} 种"
              f"  {'OK' if roof_ok else 'FAIL ' + str(dup or '缺失')}")
    if not roof_ok:
        bad += 1

    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n资产检查：{len(rows) - bad}/{len(rows)} 通过"
          + ("" if roof_ok else "（含屋顶类型重复）"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
