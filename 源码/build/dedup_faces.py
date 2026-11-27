"""
dedup_faces.py —— 共面/埋入面剔除 + 共面冲突兜底偏移

为什么需要：
  体素建筑是几百个轴对齐盒子拼出来的。相邻盒子的接触面、贴在墙面上的贴片背面
  都是"两个同法线、同一平面"的面 —— 只要两个都送进 GPU，就必然 z-fighting。
  这一步在几何阶段把它们删掉：既不参与渲染，也不参与 AO 采样，顺便省 30–50% 三角面。

规则（与工单 3.1 对应）：
  A. 某个面被另一个盒子的共面面完全覆盖 → 该面不生成。
  B. 某个面的中心点落在另一个盒子内部 → 该面不生成（埋进实体里）。
  C. 剔除后仍然共面且部分重叠的两块 → 按盒心 hash 给其中一块沿法线外移 2 mm。
  D. 所有材质 alphaMode 恒为 OPAQUE（在 gltf.add_material 里写死）。
"""
import numpy as np

EPS = 1e-4
COPLANAR_SHIFT = 0.0025     # 2.5 mm，任何观察距离都不可见，但足以脱离深度冲突


def _rect(box, axis):
    c = box[:3]
    s = box[3:]
    o1, o2 = [a for a in (0, 1, 2) if a != axis]
    return (c[o1] - s[o1] / 2, c[o1] + s[o1] / 2,
            c[o2] - s[o2] / 2, c[o2] + s[o2] / 2)


def _covers(outer, inner, eps=EPS):
    return (outer[0] <= inner[0] + eps and outer[1] >= inner[1] - eps and
            outer[2] <= inner[2] + eps and outer[3] >= inner[3] - eps)


def _overlaps(a, b, eps=EPS):
    return not (a[1] <= b[0] + eps or b[1] <= a[0] + eps or
                a[3] <= b[2] + eps or b[3] <= a[2] + eps)


def cull_faces(parts, verbose=True):
    """就地写入 p["faces"]（6 个 bool）。返回剔除的面数。

    多面体（part["verts"] 存在）不参与：它的 faces 是索引表，不是 6 个开关。
    """
    n = len(parts)
    C = np.array([p["box"][:3] for p in parts], np.float64)
    S = np.array([p["box"][3:] for p in parts], np.float64)
    culled = 0

    for i, p in enumerate(parts):
        if p.get("verts") is not None:
            continue
        box = p["box"]
        masks = []
        for fi, (axis, sign) in enumerate([(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]):
            plane = C[i, axis] + sign * S[i, axis] / 2
            rect = _rect(box, axis)
            # ---- A: 被共面面完全覆盖
            same = (np.abs((C[:, axis] + sign * S[:, axis] / 2) - plane) < EPS)
            same[i] = False
            hidden = False
            for j in np.nonzero(same)[0]:
                if S[j, axis] <= EPS:
                    continue
                oj = _rect(parts[j]["box"], axis)
                if not _covers(oj, rect):
                    continue
                # 两个完全相同的面会互相"完全覆盖"，若都剔除就会破洞 ——
                # 只剔除索引较大的那个，保留一块。
                if _covers(rect, oj) and int(j) < i:
                    continue
                hidden = True
                break
            if hidden:
                masks.append(False)
                culled += 1
                continue
            # ---- B: 整面埋进别的实体（注意：必须是"整面被覆盖"，
            #         不能只看中心点 —— 一根箍带穿过墙面中心会把整面墙误删）
            o1, o2 = [a for a in (0, 1, 2) if a != axis]
            ctr = np.array([0.0, 0.0, 0.0])
            ctr[axis] = plane - sign * 0.0006          # 往实体内侧探 0.6 mm
            inside = ((np.abs(ctr[0] - C[:, 0]) < S[:, 0] / 2 - EPS) &
                      (np.abs(ctr[1] - C[:, 1]) < S[:, 1] / 2 - EPS) &
                      (np.abs(ctr[2] - C[:, 2]) < S[:, 2] / 2 - EPS))
            inside[i] = False
            # B 规则只保留"整面完全被另一个盒子盖住"的情形。
            # 体素建筑里大量贴片会穿过墙面中心，按中心点/覆盖率裁剪会误杀整面墙。
            buried = False
            for j in np.nonzero(inside)[0]:
                oj = _rect(parts[j]["box"], axis)
                if _covers(oj, rect):
                    buried = True
                    break
            if buried:
                masks.append(False)
                culled += 1
                continue
            masks.append(True)
        p["faces"] = masks

    if verbose:
        print(f"    dedup: 剔除 {culled}/{n * 6} 个面 ({culled / max(n * 6, 1) * 100:.1f}%)")
    return culled


def _stable_hash(c):
    h = np.sin(c[0] * 127.1 + c[1] * 311.7 + c[2] * 74.7) * 43758.5453
    return int(abs(h - np.floor(h)) * 100000) % 997


def resolve_coplanar(parts, verbose=True, passes=12):
    """对仍然共面且互相部分覆盖的可见面，给其中一块 2.5 mm 外移。

    单次外移可能因为"同一块被多对冲突反复引用"而留下残余，因此做多轮；
    每轮每块最多外移一次，累计不超过 7.5 mm（视觉上仍不可见）。
    """
    moved = 0
    for _pass in range(passes):
        by_plane = {}
        for i, p in enumerate(parts):
            if p.get("verts") is not None:
                continue
            box = p["box"]
            for fi, (axis, sign) in enumerate([(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]):
                if not p["faces"][fi]:
                    continue
                plane = round(box[axis] + sign * box[3 + axis] / 2, 4)
                by_plane.setdefault((axis, sign, plane), []).append((i, fi))

        touched = set()
        n_pass = 0
        for (_axis, sign, _plane), lst in by_plane.items():
            if len(lst) < 2:
                continue
            for a in range(len(lst)):
                for b in range(a + 1, len(lst)):
                    ia, fa = lst[a]
                    ib, fb = lst[b]
                    ra = _rect(parts[ia]["box"], _axis)
                    rb = _rect(parts[ib]["box"], _axis)
                    if not _overlaps(ra, rb):
                        continue
                    if _covers(ra, rb) or _covers(rb, ra):
                        continue
                    tgt = ia if _stable_hash(parts[ia]["box"][:3]) > _stable_hash(parts[ib]["box"][:3]) else ib
                    if tgt in touched:
                        tgt = ib if tgt == ia else ia
                        if tgt in touched:
                            continue
                    touched.add(tgt)
                    # 只把这个面往外推 2.5 mm（长高/长厚），不平移整盒 ——
                    # 平移会把对面的面也带走，制造新的共面冲突
                    bb = list(parts[tgt]["box"])
                    bb[_axis] += sign * COPLANAR_SHIFT / 2
                    bb[3 + _axis] += COPLANAR_SHIFT
                    parts[tgt]["box"] = tuple(round(v, 5) for v in bb)
                    n_pass += 1
        moved += n_pass
        if n_pass == 0:
            break
    if verbose and moved:
        print(f"    coplanar: 外移 {moved} 处 2.5mm")
    return moved


def trim_overlaps(parts, verbose=True, tol=0.0004):
    """最后一道：相邻墙段在平面内搭接 1–3 mm 时，把较小的一块沿搭接方向收 1 mm。

    只收 ≤8 mm，且只动薄件/小面，不会改变立面观感；换来的是共面像素对归零。
    """
    groups = {}
    for i, p in enumerate(parts):
        if p.get("verts") is not None:
            continue
        b = p["box"]
        for fi, (ax, sg) in enumerate([(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]):
            if not p["faces"][fi]:
                continue
            plane = round(b[ax] + sg * b[3 + ax] / 2, 5)
            groups.setdefault((ax, sg, plane), []).append((i, fi))
    trimmed = 0
    for (ax, sg, _pl), lst in groups.items():
        if len(lst) < 2:
            continue
        o1, o2 = [a for a in (0, 1, 2) if a != ax]
        for a in range(len(lst)):
            for b2 in range(a + 1, len(lst)):
                i, _ = lst[a]
                j, _ = lst[b2]
                A, Bb = parts[i]["box"], parts[j]["box"]
                dx = min(A[o1] + A[3 + o1] / 2, Bb[o1] + Bb[3 + o1] / 2) -                     max(A[o1] - A[3 + o1] / 2, Bb[o1] - Bb[3 + o1] / 2)
                dz = min(A[o2] + A[3 + o2] / 2, Bb[o2] + Bb[3 + o2] / 2) -                     max(A[o2] - A[3 + o2] / 2, Bb[o2] - Bb[3 + o2] / 2)
                if dx <= 0 or dz <= 0 or dx * dz < 1e-4:
                    continue
                tgt = i if A[3 + o1] * A[3 + o2] < Bb[3 + o1] * Bb[3 + o2] else j
                bb = list(parts[tgt]["box"])
                # 沿重叠较窄的方向收 1.2 mm（只收不动中心以外的面）
                k = o1 if dx < dz else o2
                cut = min(dx, dz) + 0.0012
                if cut > 0.008:
                    continue
                bb[3 + k] = max(0.004, bb[3 + k] - cut)
                parts[tgt]["box"] = tuple(round(v, 5) for v in bb)
                trimmed += 1
    if verbose and trimmed:
        print(f"    trim: 收边 {trimmed} 处")
    return trimmed


def dedup(parts, verbose=True):
    cull_faces(parts, verbose)
    resolve_coplanar(parts, verbose)
    trim_overlaps(parts, verbose)
    # 收边会对称缩盒子，可能把两个面重新推到同一平面，最后再消解一次
    resolve_coplanar(parts, verbose)
    return parts
