"""
chunks.py —— 把构件切成"施工阶段骨 + 碎片骨"两级结构

为什么要切：
  · 建造动画只动阶段骨 → 一整个阶段一起升起，符合施工逻辑。
  · 摧毁动画只动 chunk 骨 → 一块块碎落，而不是把整片墙 scale.y 压成纸片。
  · 所有几何合进 1 个蒙皮网格 → 不论多少块碎片，都只有 1 个 draw call。

chunk 的切法：
  1. 先把超过 max_len 的长条盒沿 X/Z 切开（否则一块 9 m 的墙板无法碎成 2–3 m）。
  2. 按空间桶（2.2 × 2.2 × 2.0 m）聚类，再用 k-means 细化，保证每块紧凑。
  3. 每座总块数控制在 60–120，节点数（阶段 + chunk + 扬尘）≤ 140。
"""
import math
import numpy as np


def _cuts(a0, a1, step):
    out = [a0]
    k = math.floor(a0 / step) + 1
    while k * step < a1 - 1e-6:
        if k * step > a0 + 1e-6:
            out.append(k * step)
        k += 1
    out.append(a1)
    return out


def subdivide(parts, max_len=2.4):
    """按全局网格切开长条盒：切完每个盒子都落在 2.4 m 网格单元内，
    后续按单元聚块时，块的包围盒天然受控。"""
    out = []
    for p in parts:
        if p.get("verts") is not None:
            # 多面体不按盒网切：楔形/斜撑被切开就不再是平面围合体了
            out.append(p)
            continue
        cx, cy, cz, sx, sy, sz = p["box"]
        xs = _cuts(cx - sx / 2, cx + sx / 2, max_len)
        ys = _cuts(cy - sy / 2, cy + sy / 2, max_len)
        zs = _cuts(cz - sz / 2, cz + sz / 2, max_len)
        if len(xs) == 2 and len(ys) == 2 and len(zs) == 2:
            out.append(p)
            continue
        for i in range(len(xs) - 1):
            for k in range(len(ys) - 1):
                for j in range(len(zs) - 1):
                    w = xs[i + 1] - xs[i]
                    h = ys[k + 1] - ys[k]
                    d = zs[j + 1] - zs[j]
                    if w < 1e-5 or h < 1e-5 or d < 1e-5:
                        continue
                    q = dict(p)
                    q["box"] = (round((xs[i] + xs[i + 1]) / 2, 5),
                                round((ys[k] + ys[k + 1]) / 2, 5),
                                round((zs[j] + zs[j + 1]) / 2, 5),
                                round(w, 5), round(h, 5), round(d, 5))
                    out.append(q)
    return out


def bbox(parts):
    C = np.array([p["box"][:3] for p in parts], np.float64)
    S = np.array([p["box"][3:] for p in parts], np.float64)
    lo = (C - S / 2).min(0)
    hi = (C + S / 2).max(0)
    return lo, hi


def _kmeans(P, K, iters=14):
    """确定性 k-means（按坐标排序初始化），避免每次重建碎片位置乱跳。"""
    n = len(P)
    K = min(K, n)
    order = np.lexsort((P[:, 2], P[:, 0], P[:, 1]))
    seeds = [order[int((i + 0.5) * n / K)] for i in range(K)]
    C = P[seeds].copy()
    lab = np.zeros(n, np.int32)
    for _ in range(iters):
        d = ((P[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        new = np.array([P[lab == k].mean(0) if np.any(lab == k) else C[k] for k in range(K)])
        if np.allclose(new, C, atol=1e-5):
            break
        C = new
    return lab


CELL = 2.4


def make_chunks(parts, max_per_stage=20, total_target=112, verbose=True):
    """按 2.4 m 空间单元聚块，再在阶段内合并相邻单元直到预算。

    返回 (bones, bone_parts, chunk_meta, stage_meta)
    """
    stages = {}
    for p in parts:
        stages.setdefault(p["stage"], []).append(p)

    stage_order = sorted(stages)
    bones = []
    bone_parts = {}
    chunk_meta = []
    stage_meta = {}

    stage_bone = {}
    for s in stage_order:
        lo, hi = bbox(stages[s])
        piv = ((lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2)
        stage_bone[s] = len(bones)
        bones.append({"name": f"stage_{s:02d}", "parent": None, "pivot": piv})
        bone_parts[stage_bone[s]] = []
        stage_meta[s] = {"bone": stage_bone[s], "pivot": piv, "lo": lo, "hi": hi}

    def centroid(group):
        b = np.array([q["box"][:3] for q in group], np.float64)
        return b.mean(0)

    def merge_to(groups, K):
        groups = [list(g) for g in groups]
        while len(groups) > K:
            cents = np.array([centroid(g) for g in groups])
            d = ((cents[:, None, :] - cents[None, :, :]) ** 2).sum(-1)
            np.fill_diagonal(d, 1e18)
            a, b = np.unravel_index(np.argmin(d), d.shape)
            if a > b:
                a, b = b, a
            groups[a] = groups[a] + groups[b]
            groups.pop(b)
        return groups

    stage_groups = {}
    for s in stage_order:
        plist = stages[s]
        if s == 12:
            stage_groups[s] = [plist]
            continue
        cells = {}
        for q in plist:
            cx, cy, cz = q["box"][:3]
            key = (int(math.floor(cx / CELL)), int(math.floor(cy / CELL)),
                   int(math.floor(cz / CELL)))
            cells.setdefault(key, []).append(q)
        groups = list(cells.values())
        K = max(1, min(max_per_stage, int(math.ceil(len(plist) / 20))))
        if len(groups) > K:
            groups = merge_to(groups, K)
        final = []
        for sub in groups:
            # 按绝对 Y 网格再切一次：合并可能跨多层，但切完每块 ≤ 2.4 m 高
            bands = {}
            for q in sub:
                b = int(math.floor(q["box"][1] / CELL))
                bands.setdefault(b, []).append(q)
            final.extend(bands.values())
        stage_groups[s] = final

    # ---- 全局预算：块数超限时，合并同一阶段里"合起来最紧凑"的两块
    total = sum(len(v) for v in stage_groups.values())
    while total > total_target:
        best = None
        for s, groups in stage_groups.items():
            if sort_skip(s) or len(groups) < 2:
                continue
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    lo, hi = bbox(groups[i] + groups[j])
                    d = float(np.linalg.norm(hi - lo))
                    if best is None or d < best[0]:
                        best = (d, s, i, j)
        if best is None:
            break
        _, s, i, j = best
        gs = stage_groups[s]
        gs[i] = gs[i] + gs[j]
        gs.pop(j)
        total -= 1

    for s in stage_order:
        for sub in stage_groups[s]:
            lo, hi = bbox(sub)
            piv = ((lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2)
            bid = len(bones)
            bones.append({"name": f"chunk_{s:02d}_{len(chunk_meta):03d}",
                          "parent": stage_bone[s], "pivot": piv})
            bone_parts[bid] = []
            for p in sub:
                p["bone"] = bid
                bone_parts[bid].append(p)
            chunk_meta.append({
                "bone": bid, "stage": s, "pivot": piv, "lo": lo, "hi": hi,
                "size": hi - lo, "n": len(sub),
                "height": float(hi[1] - lo[1]),
            })

    if verbose:
        print(f"    chunks: {len(chunk_meta)} 块 / {len(bones)} 骨")
    return bones, bone_parts, chunk_meta, stage_meta


def sort_skip(stage):
    return stage == 12


def add_dust(parts, bones, bone_parts, stage_meta, rng=None):
    """每个阶段一圈扬尘：4–6 个小方块，挂在独立 dust 骨上（scale 0→2.2→0）。"""
    r = rng or np.random.default_rng(7)
    for s, sm in sorted(stage_meta.items()):
        if s == 12:
            continue
        lo, hi = sm["lo"], sm["hi"]
        cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
        w = max(1.0, min(hi[0] - lo[0], 3.0))
        d = max(1.0, min(hi[2] - lo[2], 3.0))
        bid = len(bones)
        bones.append({"name": f"dust_{s:02d}", "parent": None,
                      "pivot": (cx, 0.06, cz), "scale": 0.001})
        bone_parts[bid] = []
        k = 5
        for i in range(k):
            a = (i / k) * math.tau + 0.4
            rad = 0.55 + 0.45 * ((i * 37) % 5) / 4
            x = math.cos(a) * w * 0.35 * rad
            z = math.sin(a) * d * 0.35 * rad
            sz = 0.22 + 0.10 * ((i * 53) % 4)
            parts.append({
                "stage": s, "mat": "plaster", "tile": 0.85,
                "box": (round(x, 4), round(0.10 + sz / 2, 4), round(z, 4),
                        round(sz, 4), round(sz * 0.9, 4), round(sz, 4)),
                "bone": bid, "dust": True,
                "faces": [True] * 6, "vcol": [(1.0, 1.0, 1.0)] * 24,
            })
            bone_parts[bid].append(parts[-1])
    return parts


def enforce_budget(chunk_meta, total_min=60, total_max=120):
    return total_min <= len(chunk_meta) <= total_max
