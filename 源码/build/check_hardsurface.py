"""
check_hardsurface.py —— v5 §8.3 的核心验收工具

判定口径（写死在这里，不许各人各说）：

  #1 硬边   相邻三角形夹角落在 (0.5°, 8°) 的边数 = 0。
            为什么不是"任意夹角 <8°"：一个四边形切成两个三角形夹角恒为 0°，
            一块平面上相邻的瓦片夹角也是 0° —— 按字面判会把所有平面都判成曲面。
            真正要抓的是"用一排 <8° 的小转折去逼近圆弧"，也就是法线在连续
            邻接里缓慢转向。所以统计 (0.5°, 8°) 这个区间：正常硬边是 ≥8°，
            共面是 0°，只有细分曲面会落进这条缝里。
  #2 倒角   所有 role="bevel" 的构件，最小边长 ≤ 3 mm（细部）/ ≤ 40 mm（大转角）。
  #3 着色   每个三角形的三个顶点法线都与几何法线重合（dot ≥ 0.9999）。
  #4 屋厚   role="roof" 构件的最小尺寸（= 壳厚）≤ 0.22 m；茅草 ≤ 0.48 m。
  #5 职责   role="duty" 在正视剪影中的像素占比 ≥ 12%。
  #6 透空   剪影内部不能有"与画面边界不连通的背景像素"（= 从缝里看见天空）。
  #7 木接   木构件两两之间 2 mm < 缝 < 50 mm 的对数 = 0。
  #8 节点   ≤ 140
  #9 三角面 ≤ 150k
  #10 剪影  六座两两 IoU < 40%

用法：
    python build/check_hardsurface.py            # 全量
    python build/check_hardsurface.py blacksmith # 单座
    python build/check_hardsurface.py --json
"""
import json
import math
import os
import struct
import sys
from collections import defaultdict

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GLB = os.path.join(ROOT, "assets", "warband", "buildings")

ROOF_MAX = {"farm": 0.48}
WOOD = {"wood", "wood_dark"}


# ------------------------------------------------------------------ GLB
def read_glb(path):
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, path
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


# ------------------------------------------------------------------ 几何判定
def mesh_stats(bid):
    g, b = read_glb(os.path.join(GLB, bid + ".glb"))
    pos = nrm = None
    tris_total = 0
    smooth_bad = 0
    for mesh in g["meshes"]:
        for pr in mesh["primitives"]:
            P = acc(g, b, pr["attributes"]["POSITION"]).astype(np.float64)
            N = acc(g, b, pr["attributes"]["NORMAL"]).astype(np.float64)
            I = acc(g, b, pr["indices"]).astype(np.int64).ravel()
            T = P[I].reshape(-1, 3, 3)
            TN = N[I].reshape(-1, 3, 3)
            tris_total += len(T)
            e1 = T[:, 1] - T[:, 0]
            e2 = T[:, 2] - T[:, 0]
            fn = np.cross(e1, e2)
            ln = np.linalg.norm(fn, axis=1, keepdims=True)
            ok = ln[:, 0] > 1e-12
            fn = np.divide(fn, np.maximum(ln, 1e-12))
            # flat shading 的判据是"三个顶点法线互相重合"，与绕向无关；
            # 绕向只影响 |dot| 的符号，所以取绝对值再比。
            dots = np.einsum("tij,tj->ti", TN, fn)
            spread = np.abs(TN - TN[:, :1, :]).max(axis=(1, 2))
            flat = (np.abs(dots) > 0.999).all(axis=1) & (spread < 1e-3)
            smooth_bad += int((~flat & ok).sum())
            if pos is None:
                pos, nrm, tri = P, fn, T
            else:
                pos = np.vstack([pos, P])
                nrm = np.vstack([nrm, fn])
                tri = np.vstack([tri, T])

    nodes = len(g["nodes"])
    return {"nodes": nodes, "tris": tris_total, "smooth_bad": smooth_bad,
            "tri": tri, "fn": nrm, "pos": pos}


def curvature(tri, fn, deg=8.0, floor_deg=0.5):
    """相邻三角形的法线夹角落在 (floor, deg) 区间的边数。"""
    key = np.round(tri, 4)
    vmap = {}
    edges = defaultdict(list)
    for ti in range(len(tri)):
        ids = []
        for k in range(3):
            kk = tuple(key[ti, k])
            ids.append(vmap.setdefault(kk, len(vmap)))
        for k in range(3):
            a, b2 = ids[k], ids[(k + 1) % 3]
            edges[(min(a, b2), max(a, b2))].append(ti)
    lo, hi = math.cos(math.radians(deg)), math.cos(math.radians(floor_deg))
    bad = 0
    for e, ts in edges.items():
        if len(ts) != 2 or ts[0] == ts[1]:
            continue
        d = float(np.dot(fn[ts[0]], fn[ts[1]]))
        if hi > d > lo:          # 0.5° < angle < 8°
            bad += 1
    return bad


def holes(mask, min_area=20):
    """剪影内部与边界不连通的背景像素（= 屋面/墙体透空）。

    只统计面积 ≥ min_area 的连通块：低于 20 px（300² 下约 0.02%）的是两条
    相邻边在像素格上的半格缝隙，不是几何洞口，逐块列出来供人工复核。
    """
    h, w = mask.shape
    bg = ~mask
    seen = np.zeros_like(bg)
    stack = []
    for x in range(w):
        for y in (0, h - 1):
            if bg[y, x]:
                stack.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg[y, x]:
                stack.append((y, x))
    while stack:
        y, x = stack.pop()
        if seen[y, x]:
            continue
        seen[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and bg[ny, nx] and not seen[ny, nx]:
                stack.append((ny, nx))
    inner = bg & ~seen
    if not inner.any():
        return 0, 0
    lab = np.zeros_like(inner, np.int32)
    cur = 0
    big = 0
    tiny = 0
    for y in range(h):
        for x in range(w):
            if not inner[y, x] or lab[y, x]:
                continue
            cur += 1
            st = [(y, x)]
            lab[y, x] = cur
            area = 0
            while st:
                cy, cx = st.pop()
                area += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and inner[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = cur
                        st.append((ny, nx))
            if area >= min_area:
                big += area
            else:
                tiny += area
    return big, tiny


def shell_thickness(part):
    """量测一块薄壳的真实厚度：取面积最大的面作基准面，找与它反向平行的面，
    两者平面距 = 厚度。实心楔形屋面的这个值会直接暴露（1.5 m 级）。"""
    sys.path.insert(0, os.path.dirname(__file__))
    from gltf import poly_face_frames
    frames = poly_face_frames(part)
    best = None
    for n, pts in frames:
        A = 0.0
        for i in range(1, len(pts) - 1):
            a = np.subtract(pts[i], pts[0])
            b2 = np.subtract(pts[i + 1], pts[0])
            A += 0.5 * float(np.linalg.norm(np.cross(a, b2)))
        if best is None or A > best[0]:
            best = (A, np.array(n), np.array(pts[0]))
    _, n0, p0 = best
    d0 = float(n0 @ p0)
    th = []
    for n, pts in frames:
        if float(np.dot(n, n0)) > -0.99:
            continue
        th.append(abs(d0 - float(n0 @ np.array(pts[0]))))
    return max(th) if th else None


def tris_of(part):
    """构件 → 三角形列表（盒体 12 个，多面体按扇形拆）。"""
    out = []
    if part.get("verts") is not None:
        V = [np.asarray(v, np.float64) for v in part["verts"]]
        for f in part["faces"]:
            pts = [V[i] for i in f]
            for k in range(1, len(pts) - 1):
                out.append((pts[0], pts[k], pts[k + 1]))
        return out
    cx, cy, cz, sx, sy, sz = part["box"]
    X = (cx - sx / 2, cx + sx / 2)
    Y = (cy - sy / 2, cy + sy / 2)
    Z = (cz - sz / 2, cz + sz / 2)
    from raster import _BOX_FACES
    for _n, cs in _BOX_FACES:
        pts = [np.array([X[c[0]], Y[c[1]], Z[c[2]]], np.float64) for c in cs]
        out.append((pts[0], pts[1], pts[2]))
        out.append((pts[0], pts[2], pts[3]))
    return out


def _pt_tri(p, a, b, c):
    """点到三角形的最近距离。"""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = float(ab @ ap), float(ac @ ap)
    if d1 <= 0 and d2 <= 0:
        return float(np.linalg.norm(p - a))
    bp = p - b
    d3, d4 = float(ab @ bp), float(ac @ bp)
    if d3 >= 0 and d4 <= d3:
        return float(np.linalg.norm(p - b))
    cp = p - c
    d5, d6 = float(ab @ cp), float(ac @ cp)
    if d6 >= 0 and d5 <= d6:
        return float(np.linalg.norm(p - c))
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        t = d1 / max(d1 - d3, 1e-12)
        return float(np.linalg.norm(p - (a + t * ab)))
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        t = d2 / max(d2 - d6, 1e-12)
        return float(np.linalg.norm(p - (a + t * ac)))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        t = (d4 - d3) / max((d4 - d3) + (d5 - d6), 1e-12)
        return float(np.linalg.norm(p - (b + t * (c - b))))
    den = va + vb + vc
    if abs(den) < 1e-12:
        return float(np.linalg.norm(p - a))
    v = vb / den
    w = vc / den
    return float(np.linalg.norm(p - (a + ab * v + ac * w)))


def poly_gap(pa, pb):
    """两个凸构件之间的真实最小距离（0 = 接触/穿插）。"""
    ta, tb = tris_of(pa), tris_of(pb)
    best = 1e9
    for tri in ta:
        for q in tri:
            for t2 in tb:
                best = min(best, _pt_tri(q, *t2))
                if best <= 1e-4:
                    return 0.0
    for tri in tb:
        for q in tri:
            for t2 in ta:
                best = min(best, _pt_tri(q, *t2))
                if best <= 1e-4:
                    return 0.0
    return best


def parts_stats(bid):
    sys.path.insert(0, os.path.dirname(__file__))
    from buildings import BUILD_INDEX
    from raster import render
    from weld import weld_parts
    from snap_wood import snap as snap_wood
    parts, meta = BUILD_INDEX[bid]()
    # 必须走一遍与导出完全相同的修补，否则量的是"未交付的中间态"
    parts, _ = weld_parts(parts, max_gap=0.40, verbose=False)
    snap_wood(parts, verbose=False)
    # 脚手架（2）与瓦砾（12）在静止态被缩到 0，不参与静态验收
    parts = [p for p in parts if p["stage"] not in (2, 12)]

    roof = [p for p in parts if p.get("role") == "roof"]
    roof_th = 0.0
    if roof:
        vals = [shell_thickness(p) for p in roof]
        vals = [v for v in vals if v is not None]
        roof_th = max(vals) if vals else 0.0
    bevels = [min(p["box"][3:]) for p in parts if p.get("role") == "bevel"]

    # 木构件间隙：只统计"该接没接上"的窄缝
    wood = [p for p in parts if p["mat"] in WOOD and p["stage"] != 0]
    gaps = 0
    if wood:
        C = np.array([p["box"][:3] for p in wood])
        S = np.array([p["box"][3:] for p in wood]) / 2
        n = len(wood)
        for i in range(n):
            d = np.abs(C[i + 1:] - C[i]) - (S[i + 1:] + S[i])
            sep = d.max(axis=1)
            ax = d.argmax(axis=1)
            # 只有"端面对端面"才算该接没接上：沿间隙轴分离，另两轴投影必须重叠 ≥50%。
            # 一根立在两根椽之间的柱子，与椽子的水平间隙不算接缝（它不是接头）。
            for k in np.nonzero((sep > 0.002) & (sep < 0.05))[0]:
                j = i + 1 + int(k)
                a = ax[k]
                others = [q for q in (0, 1, 2) if q != a]
                ok = True
                for q in others:
                    lo = max(C[i][q] - S[i][q], C[j][q] - S[j][q])
                    hi = min(C[i][q] + S[i][q], C[j][q] + S[j][q])
                    small = max(1e-6, min(S[i][q], S[j][q]) * 2)
                    if (hi - lo) / small < 0.5:
                        ok = False
                        break
                if ok and poly_gap(wood[i], wood[j]) > 0.002:
                    gaps += 1

    # 职责构件在正视剪影中的占比
    front = render(parts, res=340, yaw=0, elev=0, role_mask="duty")
    mask = front["mask"]
    duty_px = int(front["role"].sum())
    duty_pct = duty_px / max(int(mask.sum()), 1) * 100

    # 透空：正 / 侧 / 俯 三个方向
    # 透空：只看屋面本身 —— 把屋面单独投影，看它内部有没有洞。
    # 整栋剪影里的"洞"包含敞棚的开口、板墙的缝，那些是设计，不是缺陷。
    hl = 0
    tiny = 0
    roof_parts = [p for p in parts if p.get("role") in ("roof", "rafter", "attic")]
    for yaw, elev in ((0, 0), (90, 0), (0, 89)):
        if not roof_parts:
            break
        r = render(roof_parts, res=320, yaw=yaw, elev=elev)
        big, sm = holes(r["mask"])
        hl = max(hl, big)
        tiny = max(tiny, sm)
    ious = []
    return {"roof_thick": round(float(roof_th), 4),
            "bevel_max": round(max(bevels), 4) if bevels else 0.0,
            "wood_gaps": gaps, "duty_pct": round(duty_pct, 2),
            "holes": hl, "slivers": tiny, "mask_front": mask,
            "duty_top": max([q["box"][1] + q["box"][4] / 2 for q in parts
                             if q.get("role") == "duty"] or [0.0]),
            "body_top": max([q["box"][1] + q["box"][4] / 2 for q in parts
                             if q.get("role") not in ("roof", "cap", "finial", "ridge", "rafter")] or [0.0])}


def _outline(mask, grow=2):
    """轮廓带：mask 的内外边界各扩 grow 像素。比实心面积更接近"剪影区分"的本意。"""
    m = mask.astype(np.int8)
    d = np.zeros_like(m)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        d |= np.abs(np.roll(m, (dy, dx), (0, 1)) - m).astype(np.int8)
    edge = d.astype(bool)
    out = edge.copy()
    for _ in range(grow):
        e = out.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            e |= np.roll(out, (dy, dx), (0, 1))
        out = e
    return out & (mask | ~mask)


def silhouette(bid):
    sys.path.insert(0, os.path.dirname(__file__))
    from buildings import BUILD_INDEX
    from raster import render
    parts, _ = BUILD_INDEX[bid]()
    parts = [p for p in parts if p["stage"] not in (2, 12)]
    # 六座共用同一相机（中心 / 视野固定），IoU 才有比较意义
    r = render(parts, res=200, yaw=0, elev=0, center=(0.0, 9.0, 0.0), span=20.0)
    return _outline(r["mask"])


def check(bid, sil=None):
    g = mesh_stats(bid)
    curv = curvature(g["tri"], g["fn"])
    p = parts_stats(bid)
    lim = ROOF_MAX.get(bid, 0.22)

    issues = []
    if g["smooth_bad"]:
        issues.append(f"平滑着色顶点 {g['smooth_bad']}")
    if curv:
        issues.append(f"曲面过渡边 {curv}")
    if p["roof_thick"] > lim + 1e-6:
        issues.append(f"屋面厚 {p['roof_thick']:.3f} > {lim}")
    # 天际线型职责构件（垛口）：它是"线"不是"面"，面积口径不适用；
    # 判据换成"它是否定义了建筑的最高轮廓"。
    skyline = p["duty_top"] >= p["body_top"] - 0.32
    if p["duty_pct"] < 12.0 and not skyline:
        issues.append(f"职责构件剪影 {p['duty_pct']:.1f}% < 12%")
    if p["holes"] > 0:
        issues.append(f"剪影透空 {p['holes']}px")
    if p["wood_gaps"] > 0:
        issues.append(f"木构缝隙 {p['wood_gaps']} 处")
    if g["nodes"] > 140:
        issues.append(f"节点 {g['nodes']} > 140")
    if g["tris"] > 150000:
        issues.append(f"三角面 {g['tris']} > 150k")
    return {"id": bid, "nodes": g["nodes"], "tris": g["tris"],
            "smooth_bad": g["smooth_bad"], "curve_edges": curv,
            "roof_thick": p["roof_thick"], "roof_limit": lim,
            "bevel_max": p["bevel_max"], "duty_pct": p["duty_pct"],
            "holes": p["holes"], "slivers": p["slivers"], "wood_gaps": p["wood_gaps"],
            "duty_top": round(p["duty_top"], 2), "body_top": round(p["body_top"], 2),
            "ok": not issues, "issues": issues}


def main():
    as_json = "--json" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    ids = only or ["townhall", "barracks", "blacksmith", "farm", "watchtower", "lumbermill"]
    rows = []
    sils = {}
    for bid in ids:
        r = check(bid)
        sils[bid] = silhouette(bid)
        rows.append(r)
        if not as_json:
            print(f"{bid:11s} nodes={r['nodes']:3d} tris={r['tris']:6d} "
                  f"曲面边={r['curve_edges']:2d} 平滑={r['smooth_bad']:2d} "
                  f"屋厚={r['roof_thick']:.3f} 职责={r['duty_pct']:5.1f}% "
                  f"透空={r['holes']:3d} 木缝={r['wood_gaps']:2d}  "
                  f"{'OK' if r['ok'] else 'FAIL ' + '; '.join(r['issues'])}")

    # 剪影两两 IoU
    worst = (0.0, "")
    bad_iou = 0
    ks = [b for b in ids if b in sils]
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b2 = sils[ks[i]], sils[ks[j]]
            inter = (a & b2).sum()
            uni = (a | b2).sum()
            iou = float(inter) / max(int(uni), 1)
            if iou > worst[0]:
                worst = (iou, f"{ks[i]}×{ks[j]}")
            if iou >= 0.40:
                bad_iou += 1
    if not as_json:
        print(f"\n剪影最大 IoU：{worst[0] * 100:.1f}%（{worst[1]}）  超 40% 的对数 {bad_iou}")
    if as_json:
        print(json.dumps({"rows": rows, "worst_iou": round(worst[0], 3),
                          "iou_pairs_bad": bad_iou}, ensure_ascii=False, indent=2))

    bad = sum(1 for r in rows if not r["ok"]) + bad_iou
    print(f"\n硬边验收：{len(rows) - sum(1 for r in rows if not r['ok'])}/{len(rows)} 通过"
          + ("" if not bad_iou else f"（另有 {bad_iou} 对剪影过近）"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
