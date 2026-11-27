"""
snap_wood.py —— 木构接头补齐（v5 §3.4「木头没粘在一起」的机械修复）

规则只有一条：**端面对端面**的 2–50 mm 缝，沿缝轴把较短的那根延长到位。
为什么不用 weld_parts：weld 是"把飘着的块拉到主体上"，会把一根 6 m 的饰条
拉成 6.5 m；这里只补 ≤50 mm 的施工缝，延长量肉眼不可见。

判定"端面对端面"：沿缝轴分离，另两轴的投影重叠 ≥50%。
（一根立在两根椽之间的柱子，与椽子的水平间隙不是接头，不处理。）
"""
import numpy as np

WOOD = {"wood", "wood_dark"}


def snap(parts, max_gap=0.05, min_gap=0.002, overlap=0.010, rounds=3, verbose=True):
    fixed = 0
    wood = [p for p in parts if p["mat"] in WOOD]
    if len(wood) < 2:
        return 0
    for _ in range(rounds):
        n = 0
        C = np.array([p["box"][:3] for p in wood], np.float64)
        S = np.array([p["box"][3:] for p in wood], np.float64)
        half = S / 2
        for i in range(len(wood)):
            d = np.abs(C[i + 1:] - C[i]) - (half[i + 1:] + half[i])
            sep = d.max(axis=1)
            ax = d.argmax(axis=1)
            for k in np.nonzero((sep > min_gap) & (sep < max_gap))[0]:
                j = i + 1 + int(k)
                a = int(ax[k])
                ok = True
                for q in range(3):
                    if q == a:
                        continue
                    lo = max(C[i][q] - half[i][q], C[j][q] - half[j][q])
                    hi = min(C[i][q] + half[i][q], C[j][q] + half[j][q])
                    if (hi - lo) / max(1e-6, min(S[i][q], S[j][q])) < 0.5:
                        ok = False
                        break
                if not ok:
                    continue
                # 延长较短的那根（体积近似）
                tgt = i if S[i].prod() <= S[j].prod() else j
                grow = float(sep[k]) + overlap
                part = wood[tgt]
                if part.get("verts") is not None:
                    # 多面体（斜撑/椽）：把靠缝那一端的顶点整体推过去
                    other = j if tgt == i else i
                    sign = 1.0 if C[other][a] > C[tgt][a] else -1.0
                    reach = C[tgt][a] + sign * half[tgt][a]
                    V = []
                    for v in part["verts"]:
                        vv = list(v)
                        if abs(vv[a] - reach) <= 0.02:
                            vv[a] += sign * grow
                        V.append(tuple(vv))
                    part["verts"] = V
                    lo = min(v[a] for v in V)
                    hi = max(v[a] for v in V)
                    C[tgt, a] = (lo + hi) / 2
                    half[tgt, a] = (hi - lo) / 2
                    n += 1
                    fixed += 1
                    continue
                bb = list(wood[tgt]["box"])
                sign = 1.0 if C[j][a] > C[tgt][a] else -1.0
                if tgt == i:
                    sign = 1.0 if C[j][a] > C[i][a] else -1.0
                else:
                    sign = 1.0 if C[i][a] > C[j][a] else -1.0
                bb[a] += sign * grow / 2.0
                bb[3 + a] += grow
                wood[tgt]["box"] = tuple(round(float(v), 5) for v in bb)
                C[tgt, a] = bb[a]
                half[tgt, a] = bb[3 + a] / 2
                n += 1
                fixed += 1
        if n == 0:
            break
    if verbose and fixed:
        print(f"    snap: 补齐木接头 {fixed} 处")
    return fixed
