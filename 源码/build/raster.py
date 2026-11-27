"""
raster.py —— 极简正交软件光栅器（numpy，无 GPU）

用途（全部是验收项，不是"看起来差不多"）：
  · 阵营染色可见投影占比 + 高度分布（3.3.5）
  · 纯白模剪影两两重合率（验收 #11）
  · 平面投影凹凸体量计数（验收 #12）
  · 职责构件在正视图剪影中的占比（v5 验收 #5）
  · 单帧 PNG 预览（无浏览器时的快速目检）

v5：输入可以是轴对齐盒体（part["box"] + 6 面开关），也可以是任意多面体
（part["verts"] + part["faces"]）。两者都在这里先展开成三角形，再走一条
统一的填充路径 —— 光栅化口径只有一份。
"""
import math

import numpy as np

# 材质近似固有色（从 matlib 的定义抄一份，避免每次读贴图）
MAT_RGB = {
    "steel": (0.55, 0.58, 0.60), "steel_dark": (0.29, 0.31, 0.34),
    "gold": (0.78, 0.63, 0.17), "cloth_team": (0.92, 0.92, 0.90),
    "leather": (0.42, 0.29, 0.20), "wood": (0.55, 0.38, 0.22),
    "wood_dark": (0.34, 0.26, 0.20), "stone": (0.60, 0.63, 0.63),
    "stone_dark": (0.37, 0.40, 0.42), "thatch": (0.66, 0.54, 0.32),
    "plaster": (0.81, 0.76, 0.68), "ember": (0.35, 0.14, 0.05),
    "shingle": (0.29, 0.26, 0.22), "window": (0.16, 0.11, 0.07),
    "emblem": (0.90, 0.90, 0.90), "plaster_dust": (0.72, 0.68, 0.60),
}

_BOX_FACES = [
    # (法线, 四角符号) —— 与 gltf.FACE_DEF 完全同序（+X -X +Y -Y +Z -Z），
    # 这样 dedup 写进 part["faces"] 的 6 个开关才能对上号。
    ((1, 0, 0), [(1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)]),
    ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
    ((0, 1, 0), [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)]),
    ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    ((0, 0, -1), [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)]),
]


def _basis(yaw, elev):
    a, e = math.radians(yaw), math.radians(elev)
    # yaw=0 → 相机在 -Z（正面），与预览台/Godot 的前向一致
    cam = np.array([math.sin(a) * math.cos(e), math.sin(e), -math.cos(a) * math.cos(e)])
    f = -cam
    right = np.cross(f, np.array([0.0, 1.0, 0.0]))
    right /= np.linalg.norm(right) + 1e-9
    up = np.cross(right, f)
    return cam, f, right, up


def part_faces(part):
    """[(normal, [pts], shade)] —— 面级遍历，三角形在填充时再扇形拆分。"""
    out = []
    if part.get("verts") is not None:
        V = [np.asarray(v, np.float64) for v in part["verts"]]
        vcol = part.get("vcol") or []
        ci = 0
        for f in part["faces"]:
            pts = [V[i] for i in f]
            n = np.zeros(3)
            for i in range(len(pts)):
                a, b = pts[i], pts[(i + 1) % len(pts)]
                n[0] += (a[1] - b[1]) * (a[2] + b[2])
                n[1] += (a[2] - b[2]) * (a[0] + b[0])
                n[2] += (a[0] - b[0]) * (a[1] + b[1])
            ln = float(np.linalg.norm(n))
            n = n / ln if ln > 1e-12 else np.array([0.0, 1.0, 0.0])
            shade = 1.0
            if vcol and ci + len(pts) <= len(vcol):
                shade = float(np.mean([c[0] for c in vcol[ci:ci + len(pts)]]))
            ci += len(pts)
            out.append((n, pts, shade))
        return out

    cx, cy, cz, sx, sy, sz = part["box"]
    X = (cx - sx / 2, cx + sx / 2)
    Y = (cy - sy / 2, cy + sy / 2)
    Z = (cz - sz / 2, cz + sz / 2)
    flags = part.get("faces")
    vcol = part.get("vcol") or []
    for fi, (n, corner_signs) in enumerate(_BOX_FACES):
        if flags is not None and not flags[fi]:
            continue
        pts = [np.array([X[c[0]], Y[c[1]], Z[c[2]]], np.float64) for c in corner_signs]
        nv = np.array(n, np.float64)
        shade = 1.0
        if vcol and fi * 4 + 4 <= len(vcol):
            shade = float(np.mean([c[0] for c in vcol[fi * 4:fi * 4 + 4]]))
        out.append((nv, pts, shade))
    return out


def render(parts, res=256, yaw=35, elev=38, center=None, span=None,
           team_only=False, background=(0.09, 0.10, 0.12), role_mask=None,
           hide_roles=()):
    """返回 dict(img, mask, mat, wy, role)

    role_mask: 需要单独统计的 role 名（该 role 覆盖的像素记进 role_hit）
    hide_roles: 完全不参与投影的 role（用于"职责构件可见性"剔除遮挡物）
    """
    C = np.array([p["box"][:3] for p in parts], np.float64)
    S = np.array([p["box"][3:] for p in parts], np.float64)
    lo = (C - S / 2).min(0)
    hi = (C + S / 2).max(0)
    if center is None:
        center = (lo + hi) / 2
    if span is None:
        span = max(hi[1] - lo[1], (hi[0] - lo[0]) * 0.9, 1.0)
    cam, f, right, up = _basis(yaw, elev)
    scale = res / span
    ctr = np.array(center, np.float64)

    def project(P):
        d = np.asarray(P, np.float64) - ctr
        x = d @ right
        y = d @ up
        z = d @ f
        return np.stack([res / 2 + x * scale, res / 2 - y * scale], -1), z + 40.0

    img = np.zeros((res, res, 3), np.float32)
    img[:] = background
    matid = np.full((res, res), -1, np.int32)
    wy = np.zeros((res, res), np.float32)
    role = np.zeros((res, res), np.int32)
    zbuf = np.full((res, res), 1e9, np.float32)

    light = np.array([0.42, 0.82, -0.38])
    light /= np.linalg.norm(light)
    names = sorted({p["mat"] for p in parts})
    midx = {m: i for i, m in enumerate(names)}
    cols = np.array([MAT_RGB.get(m, (0.6, 0.6, 0.6)) for m in names], np.float32)

    yy, xx = np.mgrid[0:res, 0:res]
    view = -f
    for p in parts:
        if p.get("role") in hide_roles:
            continue
        m = midx[p["mat"]]
        base = cols[m]
        if team_only:
            base = (np.array([1.0, 0.15, 0.12], np.float32) if p["mat"] in ("cloth_team", "emblem")
                    else np.array([0.2, 0.22, 0.25], np.float32))
        for nrm, pts, shade in part_faces(p):
            if float(nrm @ view) <= 0:
                continue
            for k in range(1, len(pts) - 1):
                p0, p1, p2 = pts[0], pts[k], pts[k + 1]
                scr, dep = project([p0, p1, p2])
                x0 = int(max(0, math.floor(scr[:, 0].min())))
                x1 = int(min(res - 1, math.ceil(scr[:, 0].max())))
                y0 = int(max(0, math.floor(scr[:, 1].min())))
                y1 = int(min(res - 1, math.ceil(scr[:, 1].max())))
                if x1 < x0 or y1 < y0:
                    continue
                px = xx[y0:y1 + 1, x0:x1 + 1] + 0.5
                py = yy[y0:y1 + 1, x0:x1 + 1] + 0.5
                ax, ay = scr[0]
                bx, by = scr[1]
                cx2, cy2 = scr[2]
                den = (by - cy2) * (ax - cx2) + (cx2 - bx) * (ay - cy2)
                if abs(den) < 1e-9:
                    continue
                w0 = ((by - cy2) * (px - cx2) + (cx2 - bx) * (py - cy2)) / den
                w1 = ((cy2 - ay) * (px - cx2) + (ax - cx2) * (py - cy2)) / den
                w2 = 1.0 - w0 - w1
                inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
                if not inside.any():
                    continue
                depth = w0 * dep[0] + w1 * dep[1] + w2 * dep[2]
                zs = zbuf[y0:y1 + 1, x0:x1 + 1]
                hit = inside & (depth < zs - 1e-5)
                if not hit.any():
                    continue
                zs[hit] = depth[hit]
                matid[y0:y1 + 1, x0:x1 + 1][hit] = m
                yv = (w0 * float(p0[1]) + w1 * float(p1[1]) + w2 * float(p2[1]))
                wy[y0:y1 + 1, x0:x1 + 1][hit] = yv[hit]
                if role_mask and p.get("role") == role_mask:
                    role[y0:y1 + 1, x0:x1 + 1][hit] = 1

                lam = max(0.0, float(nrm @ light))
                col = base * shade * (0.42 + 0.72 * lam)
                img[y0:y1 + 1, x0:x1 + 1][hit] = col

    mask = matid >= 0
    return {"img": img, "mask": mask, "matid": matid, "wy": wy, "role": role,
            "names": names, "center": ctr, "span": span, "scale": scale}


def save_png(res, path):
    from PIL import Image
    a = np.clip(res["img"], 0, 1) ** (1 / 1.9)
    Image.fromarray((a * 255).astype(np.uint8)).save(path)


def silhouette(parts, res=128, yaw=35, elev=22):
    r = render(parts, res=res, yaw=yaw, elev=elev,
               center=(np.mean([p["box"][0] for p in parts]),
                       np.mean([p["box"][1] + p["box"][4] / 2 for p in parts]),
                       np.mean([p["box"][2] for p in parts])),
               span=None)
    return r["mask"]
