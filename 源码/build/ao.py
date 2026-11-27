"""
ao.py —— 顶点环境光遮蔽烘焙（烘焙进 COLOR_0）

为什么必须做：
  体素模型没有斜面，缺少"面与面之间的接触暗部"就会读成一堆积木。
  贴图上的 AO 只在单个盒子内部起伏，跨盒子的接缝（墙与地、檐与墙、梁与柱）
  完全没有暗部 —— 这正是"玩具感"的来源。

做法：
  1. 把所有长方体光栅化成 0.07 m 的占据栅格（y<0 视为地面，让底部有接触暗部）。
  2. 每个面的每个顶点，沿法线半球取 9 个方向 × 4 个距离，命中即计权（近处权重大）。
  3. occl → ao = 1 - strength * occl，再叠一点每盒的亮度/色温扰动，
     打散"整栋一个色"的塑料感。

输出直接写进 glTF 的 COLOR_0（VEC3），着色器里 ALBEDO *= COLOR.rgb。
"""
import numpy as np

from gltf import FACE_DEF

RES = 0.07          # 栅格边长（米）
STRENGTH = 0.34     # AO 最大压暗比例（v2：接缝 AO 必须明显）
PAD = 0.5           # 栅格外扩

_AB = [(0.0, 0.0), (0.78, 0.0), (-0.78, 0.0), (0.0, 0.78), (0.0, -0.78),
       (0.62, 0.62), (-0.62, 0.62), (0.62, -0.62), (-0.62, -0.62)]
_DIST = (0.07, 0.17, 0.30, 0.44)
_FALLOFF = 0.52


def _grid(boxes, res=RES, pad=PAD):
    lo = (boxes[:, :3] - boxes[:, 3:] / 2).min(0) - pad
    hi = (boxes[:, :3] + boxes[:, 3:] / 2).max(0) + pad
    dims = np.maximum(np.ceil((hi - lo) / res).astype(int) + 1, 2)
    g = np.zeros(dims, dtype=bool)

    for b in boxes:
        cx, cy, cz, sx, sy, sz = b
        # 以"格心是否落在盒内"为准，避免把盒子外扩一格造成自遮蔽
        c0 = np.array([cx - sx / 2, cy - sy / 2, cz - sz / 2])
        c1 = np.array([cx + sx / 2, cy + sy / 2, cz + sz / 2])
        i0 = np.ceil((c0 - lo) / res - 0.5).astype(int)
        i1 = np.floor((c1 - lo) / res - 0.5).astype(int)
        i0 = np.clip(i0, 0, dims - 1)
        i1 = np.clip(i1, 0, dims - 1)
        if np.any(i1 < i0):
            continue
        g[i0[0]:i1[0] + 1, i0[1]:i1[1] + 1, i0[2]:i1[2] + 1] = True

    # 地面：y<0 全部占据，给墙脚一圈接触暗部
    gy = int(np.floor((0.0 - lo[1]) / res))
    if gy > 0:
        g[:, :gy, :] = True
    return g, lo, res


def _hash01(cx, cy, cz):
    """确定性的伪随机，避免每次重建色彩乱跳。"""
    h = np.sin(cx * 127.1 + cy * 311.7 + cz * 74.7) * 43758.5453
    h = h - np.floor(h)
    h2 = np.sin(cx * 269.5 + cy * 183.3 + cz * 246.1) * 43758.5453
    h2 = h2 - np.floor(h2)
    return h, h2


def bake_vertex_ao(parts, res=RES, strength=STRENGTH, verbose=True):
    """就地给每个盒体 part 写入 vcol（24 个顶点色，顺序与 box_geometry 一致）。

    多面体（part["verts"] 存在）不在这里处理 —— 它们的面数与顶点数都不固定，
    由 bake_poly_vcol() 按 poly_face_frames 的顺序单独烘焙。
    """
    if not parts:
        return parts
    box_parts = [p for p in parts if p.get("verts") is None]
    if not box_parts:
        return parts
    boxes = np.array([p["box"] for p in box_parts], dtype=np.float64)
    g, lo, res = _grid(boxes, res)

    # ---- 展开所有顶点（每个盒 6 面 × 4 角，顺序严格跟随 FACE_DEF）
    verts, norms, owner = [], [], []
    for bi, b in enumerate(boxes):
        cx, cy, cz, sx, sy, sz = b
        X = (cx - sx / 2, cx + sx / 2)
        Y = (cy - sy / 2, cy + sy / 2)
        Z = (cz - sz / 2, cz + sz / 2)
        for n, corners in FACE_DEF:
            for c in corners:
                verts.append((X[c[0]], Y[c[1]], Z[c[2]]))
                norms.append(n)
                owner.append(bi)

    P = np.array(verts, dtype=np.float64)
    N = np.array(norms, dtype=np.float64)
    owner = np.array(owner, dtype=np.int64)

    # ---- 每个顶点的切空间
    up = np.where(np.abs(N[:, 1:2]) < 0.9,
                  np.array([[0.0, 1.0, 0.0]]),
                  np.array([[1.0, 0.0, 0.0]]))
    t1 = np.cross(up, N)
    t1 /= np.maximum(np.linalg.norm(t1, axis=1, keepdims=True), 1e-6)
    t2 = np.cross(N, t1)

    occ = np.zeros(len(P))
    wsum = 0.0
    for d in _DIST:
        wsum += (1.0 - d / _FALLOFF) if d < _FALLOFF else 0.0
    for a, b in _AB:
        d3 = N + a * t1 + b * t2
        d3 /= np.maximum(np.linalg.norm(d3, axis=1, keepdims=True), 1e-6)
        for dist in _DIST:
            q = P + N * 0.03 + d3 * dist
            idx = np.floor((q - lo) / res).astype(int)
            ok = np.all((idx >= 0) & (idx < g.shape), axis=1)
            hit = np.zeros(len(q), dtype=bool)
            hit[ok] = g[idx[ok, 0], idx[ok, 1], idx[ok, 2]]
            occ += hit * (1.0 - dist / _FALLOFF)

    ao = 1.0 - strength * np.clip(occ / max(wsum, 1e-6), 0.0, 1.0)

    # ---- 每盒的亮度/色温扰动：打散"整栋一个色"
    h1, h2 = _hash01(boxes[:, 0], boxes[:, 1], boxes[:, 2])
    jit = (0.965 + 0.055 * h1)[owner]             # 0.965 – 1.02
    warm = ((h2 - 0.5) * 0.055)[owner]            # ±2.7% 冷/暖偏移

    r = ao * jit * (1.0 + warm)
    gr = ao * jit
    bl = ao * jit * (1.0 - warm)
    col = np.clip(np.stack([r, gr, bl], axis=1), 0.0, 1.0)

    # ---- 写回
    per = 24
    for i, p in enumerate(box_parts):
        sl = col[owner == i]
        p["vcol"] = [tuple(float(v) for v in c) for c in sl]

    if verbose:
        print(f"    ao: 盒体顶点 {len(P)}  平均 {ao.mean():.3f}  最暗 {ao.min():.3f}")
    return parts


def bake_poly_vcol(parts, res=RES, strength=STRENGTH, verbose=True):
    """多面体的顶点 AO：逐面逐角算遮蔽，写入 part["vcol"]（顺序 = poly_face_frames）。"""
    from gltf import poly_face_frames
    polys = [p for p in parts if p.get("verts") is not None]
    if not polys:
        return parts
    all_boxes = np.array([p["box"] for p in parts], dtype=np.float64)
    g, lo, res = _grid(all_boxes, res)

    wsum = 0.0
    for d in _DIST:
        wsum += (1.0 - d / _FALLOFF) if d < _FALLOFF else 0.0

    tot, acc = 0, 0.0
    for p in polys:
        frames = poly_face_frames(p)
        P, N = [], []
        for n, pts in frames:
            for q in pts:
                P.append(q)
                N.append(n)
        P = np.array(P, dtype=np.float64)
        N = np.array(N, dtype=np.float64)
        up = np.where(np.abs(N[:, 1:2]) < 0.9,
                      np.array([[0.0, 1.0, 0.0]]),
                      np.array([[1.0, 0.0, 0.0]]))
        t1 = np.cross(up, N)
        t1 /= np.maximum(np.linalg.norm(t1, axis=1, keepdims=True), 1e-6)
        t2 = np.cross(N, t1)

        occ = np.zeros(len(P))
        for a, b in _AB:
            d3 = N + a * t1 + b * t2
            d3 /= np.maximum(np.linalg.norm(d3, axis=1, keepdims=True), 1e-6)
            for dist in _DIST:
                q = P + N * 0.03 + d3 * dist
                idx = np.floor((q - lo) / res).astype(int)
                ok = np.all((idx >= 0) & (idx < g.shape), axis=1)
                hit = np.zeros(len(q), dtype=bool)
                hit[ok] = g[idx[ok, 0], idx[ok, 1], idx[ok, 2]]
                occ += hit * (1.0 - dist / _FALLOFF)

        ao = 1.0 - strength * np.clip(occ / max(wsum, 1e-6), 0.0, 1.0)
        h1, h2 = _hash01(np.array([p["box"][0]]), np.array([p["box"][1]]),
                         np.array([p["box"][2]]))
        jit = float(0.965 + 0.055 * h1[0])
        warm = float((h2[0] - 0.5) * 0.055)
        r = np.clip(ao * jit * (1.0 + warm), 0.0, 1.0)
        gr = np.clip(ao * jit, 0.0, 1.0)
        bl = np.clip(ao * jit * (1.0 - warm), 0.0, 1.0)
        p["vcol"] = [(float(a), float(b), float(c)) for a, b, c in zip(r, gr, bl)]
        tot += len(P)
        acc += float(ao.mean())

    if verbose:
        print(f"    ao: 多面体顶点 {tot}  平均 {acc / max(len(polys), 1):.3f}")
    return parts
