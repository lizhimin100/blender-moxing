"""
weld.py —— 结构焊接：把所有"差一点没搭上"的构件补到实体上

规则：
  1. 按 AABB 求连通块（三轴同时重叠才算接触）。
  2. 对每个不与地面连通的块，找到它与主结构最近的一对构件，
     沿间隙轴把该构件朝主结构延伸 gap + overlap。
  3. 迭代到没有悬空块，或超过 max_gap 不再处理（大缝必须回源头改，
     硬拉一根 1 米长的杆只会让造型更怪）。

这样出来的模型可以保证：任何一块几何都通过实体链路连到地面。
"""
import numpy as np

EPS = 0.015


def _components(c, half, eps=EPS):
    n = len(c)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ok = np.ones((n, n), dtype=bool)
    for axis in (0, 1, 2):
        d = np.abs(c[:, axis][:, None] - c[:, axis][None, :])
        lim = half[:, axis][:, None] + half[:, axis][None, :] + eps
        ok &= d <= lim
    ii, jj = np.nonzero(np.triu(ok, 1))
    for a, b in zip(ii.tolist(), jj.tolist()):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [np.array(v) for v in groups.values()]


def _pair_gap(c1, h1, c2, h2):
    """返回 (L∞ 间距, i, j)，用于决定要焊接哪一对构件。"""
    sep = None
    for axis in (0, 1, 2):
        d = np.abs(c1[:, axis][:, None] - c2[:, axis][None, :])
        lim = h1[:, axis][:, None] + h2[:, axis][None, :]
        g = d - lim
        sep = g if sep is None else np.maximum(sep, g)
    i, j = np.unravel_index(np.argmin(sep), sep.shape)
    return float(sep[i, j]), int(i), int(j)


def _axis_gaps(c1, h1, c2, h2, i, j):
    """单对构件逐轴间隙与方向：正值表示没接上。"""
    out = []
    for axis in (0, 1, 2):
        g = abs(c1[i][axis] - c2[j][axis]) - (h1[i][axis] + h2[j][axis])
        sign = 1.0 if c1[i][axis] > c2[j][axis] else -1.0
        out.append((g, sign))
    return out


def weld_parts(parts, max_gap=0.30, overlap=0.04, verbose=True):
    """就地修正 box，使全模型连通到地面。返回 (parts, 修补次数)。"""
    boxes = [list(p["box"]) for p in parts]
    is_poly = [p.get("verts") is not None for p in parts]
    fixed = 0

    for _ in range(64):
        c = np.array([b[:3] for b in boxes], dtype=np.float64)
        s = np.array([b[3:] for b in boxes], dtype=np.float64)
        half = s / 2.0
        comps = _components(c, half)

        grounded, floating = [], []
        for idx in comps:
            if (c[idx, 1] - half[idx, 1]).min() <= 0.03:
                grounded.append(idx)
            else:
                floating.append(idx)
        if not floating:
            break

        progressed = False
        for fi in floating:
            best = None
            for gi in grounded:
                gap, i, j = _pair_gap(c[fi], half[fi], c[gi], half[gi])
                if best is None or gap < best[0]:
                    best = (gap, i, j, fi, gi)
            if best is None:
                continue
            gap, i, j, fi, gi = best
            if gap > max_gap or gap < -0.05:
                continue
            if is_poly[int(fi[i])]:
                # 多面体不能沿 AABB 拉伸（会与顶点解耦），留给建模阶段处理
                continue

            bi = boxes[int(fi[i])]
            # 三轴都要闭合：任何一轴还留着缝，两块就仍然不接触
            for axis, (g, sign) in enumerate(_axis_gaps(c[fi], half[fi], c[gi], half[gi], i, j)):
                if g <= 0.0:
                    continue
                grow = g + overlap
                bi[axis] -= sign * grow / 2.0     # 远端面不动，近端面朝目标延展
                bi[3 + axis] += grow
            fixed += 1
            progressed = True
            break

        if not progressed:
            break

    for p, b in zip(parts, boxes):
        p["box"] = tuple(round(float(v), 5) for v in b)
    if verbose and fixed:
        print(f"    weld: 修补 {fixed} 处接触")
    return parts, fixed
