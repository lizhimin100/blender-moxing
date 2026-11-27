"""
roofs_hs.py —— v5 §3.1 / §3.2 的屋面构造（六座共用）

一条硬指标：檐口处屋面法向总厚 = 椽 0.10 + 望板 0.03 + 瓦 0.05 = 0.18 m。
所以屋面必须"薄壳 + 密椽"，不能再用实心楔形；空腔由内缩 0.10 的阁楼体块挡住。

层级（从下往上）：
    椽     0.14 宽 × 0.10 高，间距 0.55，檐口出挑 0.35，椽头端面可见
    望板   0.03 厚，贴椽上，不外露
    瓦     每皮高 0.22 / 露明 0.16 / 厚 0.05，每皮外挑 0.03，每 3 皮错缝
    脊     脊木 0.16 × 0.20 + 脊瓦 0.24 宽，高出两侧 0.04
    封檐   0.12 × 0.22，沿檐口通长，与椽头平齐
"""
import math

import numpy as np

import detail
import hs
from hs import Plane

RAFTER_W = 0.14
RAFTER_H = 0.10
BOARD_T = 0.03
SHINGLE_T = 0.05
EAVE_OVER = 0.35


def _plane(a0, a1, b0, b1):
    return Plane(a0, a1, b0, b1)


def _barge(p, st, mat, a, b, y_eave, y_ridge, sign_z, thick=0.12):
    """山墙封边板：沿坡度通长，两端出头 0.10。"""
    n = 0.10
    A = np.array([a, y_eave - n, 0.0])
    Bp = np.array([b, y_ridge + 0.06, 0.0])
    hs.bar(p, st, mat, A + np.array([0, 0, sign_z * 0.02]),
           Bp + np.array([0, 0, sign_z * 0.02]), thick, 0.22,
           up=(0, 1, 0), tile=0.9, role="barge")


def gable(p, st_lo, st_hi, cx, cz, w, d, eave_y, ridge_y,
          over=0.35, ridge_axis="x", mat="shingle", team=True,
          rafter_mat="wood_dark", attic_mat="plaster", attic=True,
          duty=False, gable_wall_mat=None, barge=True):
    """双坡薄壳屋面（脊沿 X 或 Z）。返回 (檐口厚, 脊高)。"""
    run = (d / 2 if ridge_axis == "x" else w / 2)
    ridge_y = max(ridge_y, eave_y + 0.35)
    pitch = math.atan2(ridge_y - eave_y, run)
    over_x = over if ridge_axis == "x" else 0.0
    over_z = over if ridge_axis == "z" else 0.0
    ox = over if ridge_axis == "z" else over          # 山墙出挑
    # 檐口线（± 法向一侧）与脊线
    if ridge_axis == "x":
        a_lo = (cx - w / 2 - ox, eave_y, cz - d / 2 - over_z)
        a_hi = (cx + w / 2 + ox, eave_y, cz - d / 2 - over_z)
        b_lo = (cx - w / 2 - ox, ridge_y, cz)
        b_hi = (cx + w / 2 + ox, ridge_y, cz)
        p1 = _plane(a_lo, a_hi, b_lo, b_hi)
        a2 = (cx - w / 2 - ox, eave_y, cz + d / 2 + over_z)
        a3 = (cx + w / 2 + ox, eave_y, cz + d / 2 + over_z)
        p2 = _plane(a2, a3, b_lo, b_hi)
    else:
        a_lo = (cx - w / 2 - over_z, eave_y, cz - d / 2 - ox)
        a_hi = (cx - w / 2 - over_z, eave_y, cz + d / 2 + ox)
        b_lo = (cx, ridge_y, cz - d / 2 - ox)
        b_hi = (cx, ridge_y, cz + d / 2 + ox)
        p1 = _plane(a_lo, a_hi, b_lo, b_hi)
        a2 = (cx + w / 2 + over_z, eave_y, cz - d / 2 - ox)
        a3 = (cx + w / 2 + over_z, eave_y, cz + d / 2 + ox)
        p2 = _plane(a2, a3, b_lo, b_hi)

    for pl, st in ((p1, st_lo), (p2, st_hi)):
        width = pl.width()
        nu = max(2, int(round(width / 1.15)))
        nv = max(2, int(round(pl.slope_len() / 1.0)))
        # 望板
        hs.grid_slab(p, st, mat, pl, BOARD_T, nu=nu, nv=nv, offset=0.0,
                     tile=0.9, role="roof")
        # 椽（间距 0.55，出挑 0.35 已在 plane 里）
        n_raf = max(2, int(round(width / 0.55)))
        hs.rafters(p, st, rafter_mat, pl, n_raf, w=RAFTER_W, h=RAFTER_H,
                   drop=0.0, v0=-0.02, v1=0.995, tile=0.9, role="rafter")
        # 瓦
        hs.courses(p, st, mat, pl, course=0.22, thick=SHINGLE_T, lip=0.03,
                   tile=0.9, role="roof")
        # 封檐板（与椽头平齐）
        e0 = pl.pt(0.0, 0.0)
        e1 = pl.pt(1.0, 0.0)
        n = pl.normal()
        mid = (e0 + e1) / 2 + n * (-0.02)
        along = e1 - e0
        L = float(np.linalg.norm(along))
        ang = math.atan2(along[2], along[0])
        # 用 bar 做通长板
        hs.bar(p, st, rafter_mat, e0 + n * (-0.02) + np.array([0, -0.05, 0]),
               e1 + n * (-0.02) + np.array([0, -0.05, 0]), 0.22, 0.12,
               up=n, tile=0.9, role="fascia")

    # 脊
    if ridge_axis == "x":
        hs.ridge_cap(p, st_hi, "wood_dark", "cloth_team" if team else "wood_dark",
                     (cx - w / 2 - ox, ridge_y, cz), (cx + w / 2 + ox, ridge_y, cz),
                     ridge_y + 0.02, team=team)
    else:
        hs.ridge_cap(p, st_hi, "wood_dark", "cloth_team" if team else "wood_dark",
                     (cx, ridge_y, cz - d / 2 - ox), (cx, ridge_y, cz + d / 2 + ox),
                     ridge_y + 0.02, team=team)

    # 山墙封边
    if barge and ridge_axis == "x":
        for sz in (-1, 1):
            for xx in (cx - w / 2 - ox, cx + w / 2 + ox):
                pass
    if attic:
        _attic_gable(p, st_hi, cx, cz, w, d, eave_y, ridge_y, ridge_axis, attic_mat)

    return RAFTER_H + BOARD_T + SHINGLE_T, ridge_y


def _attic_gable(p, st, cx, cz, w, d, eave_y, ridge_y, ridge_axis, mat):
    """内缩 0.10 的封闭阁楼体块：挡住薄壳下的空腔，本身不参与外观。"""
    inset = 0.10
    if ridge_axis == "x":
        prof = [(cz - d / 2 + inset, eave_y), (cz + d / 2 - inset, eave_y),
                (cz, ridge_y - 0.14)]
        _prism_x(p, st, mat, prof, cx - w / 2 + inset, cx + w / 2 - inset)
    else:
        prof = [(cx - w / 2 + inset, eave_y), (cx + w / 2 - inset, eave_y),
                (cx, ridge_y - 0.14)]
        _prism_z(p, st, mat, prof, cz - d / 2 + inset, cz + d / 2 - inset)


def _prism_x(p, st, mat, prof_zy, x0, x1):
    """把 (z,y) 剖面沿 X 挤出。"""
    V = [(x0, y, z) for z, y in prof_zy] + [(x1, y, z) for z, y in prof_zy]
    n = len(prof_zy)
    F = [tuple(range(n)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, n + j, n + i))
    hs.add(p, st, mat, V, F, tile=1.1, role="attic")


def _prism_z(p, st, mat, prof_xy, z0, z1):
    V = [(x, y, z0) for x, y in prof_xy] + [(x, y, z1) for x, y in prof_xy]
    n = len(prof_xy)
    F = [tuple(range(n)), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        F.append((i, j, n + j, n + i))
    hs.add(p, st, mat, V, F, tile=1.1, role="attic")


def mono(p, st_lo, st_hi, cx, cz, w, d, eave_y, ridge_y, over=0.35,
         high_side="+x", mat="shingle", team=True, attic=True,
         attic_mat="plaster", ridge_axis="x"):
    """单坡薄壳：檐口在低侧，脊（高侧）贴墙。"""
    sign = 1 if high_side == "+x" else -1
    if ridge_axis == "x":
        # 坡向沿 Z：低侧 z = -sign
        z_lo = cz + sign * (d / 2 + over)
        z_hi = cz - sign * (d / 2)
        a0 = (cx - w / 2 - over, eave_y, z_lo)
        a1 = (cx + w / 2 + over, eave_y, z_lo)
        b0 = (cx - w / 2 - over, ridge_y, z_hi)
        b1 = (cx + w / 2 + over, ridge_y, z_hi)
    else:
        x_lo = cx + sign * (w / 2 + over)
        x_hi = cx - sign * (w / 2)
        a0 = (x_lo, eave_y, cz - d / 2 - over)
        a1 = (x_lo, eave_y, cz + d / 2 + over)
        b0 = (x_hi, ridge_y, cz - d / 2 - over)
        b1 = (x_hi, ridge_y, cz + d / 2 + over)
    pl = _plane(a0, a1, b0, b1)
    st = st_lo
    nu = 2 if detail.LOW else max(2, int(round(pl.width() / 1.15)))
    nv = 2 if detail.LOW else max(2, int(round(pl.slope_len() / 1.0)))
    hs.grid_slab(p, st, mat, pl, BOARD_T, nu=nu, nv=nv, offset=0.0, tile=0.9, role="roof")
    n_raf = max(2, int(round(pl.width() / 0.55)))
    hs.rafters(p, st, "wood_dark", pl, n_raf, w=RAFTER_W, h=RAFTER_H,
               drop=0.0, v0=-0.02, v1=0.995, tile=0.9, role="rafter")
    hs.courses(p, st, mat, pl, course=0.22, thick=SHINGLE_T, lip=0.03,
               tile=0.9, role="roof")
    e0, e1 = pl.pt(0.0, 0.0), pl.pt(1.0, 0.0)
    n = pl.normal()
    hs.bar(p, st, "wood_dark", e0 + n * (-0.02) + np.array([0, -0.05, 0]),
           e1 + n * (-0.02) + np.array([0, -0.05, 0]), 0.22, 0.12,
           up=n, tile=0.9, role="fascia")
    # 高侧收头
    hs.bar(p, st_hi, "wood_dark", b0, b1, 0.20, 0.16, up=(0, 1, 0),
           tile=0.9, role="ridge")
    if team:
        hs.bar(p, st_hi, "cloth_team", b0 + np.array([0, 0.13, 0]),
               b1 + np.array([0, 0.13, 0]), 0.24, 0.06, up=(0, 1, 0),
               tile=1.0, role="team")
    if attic:
        _attic_mono(p, st_hi, cx, cz, w, d, eave_y, ridge_y, ridge_axis, sign, attic_mat)
    return RAFTER_H + BOARD_T + SHINGLE_T, ridge_y


def _attic_mono(p, st, cx, cz, w, d, eave_y, ridge_y, ridge_axis, sign, mat):
    inset = 0.10
    if ridge_axis == "x":
        z_lo = cz + sign * (d / 2 - inset)
        z_hi = cz - sign * (d / 2 - inset)
        prof = [(z_lo, eave_y), (z_hi, ridge_y - 0.12), (z_hi, eave_y)]
        _prism_x(p, st, mat, prof, cx - w / 2 + inset, cx + w / 2 - inset)
    else:
        x_lo = cx + sign * (w / 2 - inset)
        x_hi = cx - sign * (w / 2 - inset)
        prof = [(x_lo, eave_y), (x_hi, ridge_y - 0.12), (x_hi, eave_y)]
        _prism_z(p, st, mat, prof, cz - d / 2 + inset, cz + d / 2 - inset)


# ------------------------------------------------------------------ 茅草
def thatch_gable(p, st_lo, st_hi, cx, cz, w, d, eave_y, ridge_y,
                 over=0.55, ridge_axis="x", layers=3, lift=0.08, press=0.06):
    """茅草：总厚 0.42，3 层叠压，檐口切 45° 斜面，脊部 3 级收头 + 压脊木。"""
    run = (d / 2 if ridge_axis == "x" else w / 2)
    ridge_y = max(ridge_y, eave_y + 0.5)
    if ridge_axis == "x":
        a_lo = (cx - w / 2 - over, eave_y, cz - d / 2 - over)
        a_hi = (cx + w / 2 + over, eave_y, cz - d / 2 - over)
        b_lo = (cx - w / 2 - over, ridge_y, cz)
        b_hi = (cx + w / 2 + over, ridge_y, cz)
        p1 = _plane(a_lo, a_hi, b_lo, b_hi)
        a2 = (cx - w / 2 - over, eave_y, cz + d / 2 + over)
        a3 = (cx + w / 2 + over, eave_y, cz + d / 2 + over)
        p2 = _plane(a2, a3, b_lo, b_hi)
    else:
        a_lo = (cx - w / 2 - over, eave_y, cz - d / 2 - over)
        a_hi = (cx - w / 2 - over, eave_y, cz + d / 2 + over)
        b_lo = (cx, ridge_y, cz - d / 2 - over)
        b_hi = (cx, ridge_y, cz + d / 2 + over)
        p1 = _plane(a_lo, a_hi, b_lo, b_hi)
        a2 = (cx + w / 2 + over, eave_y, cz - d / 2 - over)
        a3 = (cx + w / 2 + over, eave_y, cz + d / 2 + over)
        p2 = _plane(a2, a3, b_lo, b_hi)

    th_each = 0.14
    for pl in (p1, p2):
        nu = 2 if detail.LOW else max(2, int(round(pl.width() / 1.2)))
        nv = 2 if detail.LOW else max(2, int(round(pl.slope_len() / 1.1)))
        for k in range(layers):
            hs.grid_slab(p, st_lo, "thatch", pl, th_each, nu=nu, nv=nv,
                         offset=0.005 + k * 0.004, v0=-0.04 + k * 0.0, v1=0.99,
                         tile=1.0, role="roof")
        # 檐口 45° 切口：外沿比内沿低 0.06
        e0, e1 = pl.pt(0.0, 0.0), pl.pt(1.0, 0.0)
        n = pl.normal()
        q = [e0 + n * 0.06 + np.array([0, 0.0, 0]), e1 + n * 0.06 + np.array([0, 0.0, 0]),
             e1 - n * 0.30 + np.array([0, -0.10, 0]), e0 - n * 0.30 + np.array([0, -0.10, 0])]
        hs.slab(p, st_lo, "thatch", q, 0.06, tile=1.0, role="roof")
        # 椽头（茅草压在椽上）
        n_raf = max(2, int(round(pl.width() / 0.55)))
        hs.rafters(p, st_lo, "wood_dark", pl, n_raf, w=RAFTER_W, h=RAFTER_H,
                   drop=0.16, v0=-0.02, v1=0.9, tile=0.9, role="rafter")

    # 脊：3 级阶梯 + 压脊木
    ry = ridge_y
    steps = [(0.62, 0.10), (0.44, 0.10), (0.26, 0.10)]
    for i, (wid, hh) in enumerate(steps):
        if ridge_axis == "x":
            hs.box(p, st_hi, "thatch", cx, ry + 0.06 + i * hh, cz,
                   w + 2 * over - 0.10 * i, hh, wid, tile=1.0, role="roof")
        else:
            hs.box(p, st_hi, "thatch", cx, ry + 0.06 + i * hh, cz,
                   wid, hh, d + 2 * over - 0.10 * i, tile=1.0, role="roof")
    if ridge_axis == "x":
        hs.box(p, st_hi, "wood_dark", cx, ry + 0.44, cz, w + 2 * over - 0.2, 0.16, 0.18,
               tile=0.9, role="ridge")
    else:
        hs.box(p, st_hi, "wood_dark", cx, ry + 0.44, cz, 0.18, 0.16, d + 2 * over - 0.2,
               tile=0.9, role="ridge")

    _attic_gable(p, st_hi, cx, cz, w, d, eave_y, ridge_y, ridge_axis, "plaster")
    return 0.42, ridge_y


# ------------------------------------------------------------------ 阶梯山墙
def crow_step_gable(p, st, cx, cz, w, d, base_y, ridge_y, step_h=0.40,
                    step_d=0.50, mat="stone", cap_mat="stone_dark",
                    ridge_axis="x", duty=False):
    """阶梯山墙（crow-stepped gable）：每级 0.40 高 × 0.50 深，压顶 0.10 厚、两端出头 0.04。"""
    run = d / 2 if ridge_axis == "x" else w / 2
    n = max(1, int(round((ridge_y - base_y) / step_h)))
    for k in range(n):
        y0 = base_y + k * step_h
        y1 = min(ridge_y, y0 + step_h)
        half = run - k * (run / (n + 0.6))
        if half <= 0.18:
            break
        if ridge_axis == "x":
            for sx in (-1, 1):
                x = cx + sx * (w / 2 - 0.12)
                hs.box(p, st, mat, x, (y0 + y1) / 2, cz,
                       0.24, y1 - y0, half * 2, tile=1.0, role="gable_step")
                # 压顶
                hs.box(p, st, cap_mat, x, y1 + 0.05, cz,
                       0.24 + 0.08, 0.10, half * 2 + 0.08, tile=1.0, role="gable_cap")
        else:
            for sz in (-1, 1):
                z = cz + sz * (d / 2 - 0.12)
                hs.box(p, st, mat, cx, (y0 + y1) / 2, z,
                       half * 2, y1 - y0, 0.24, tile=1.0, role="gable_step")
                hs.box(p, st, cap_mat, cx, y1 + 0.05, z,
                       half * 2 + 0.08, 0.10, 0.24 + 0.08, tile=1.0, role="gable_cap")


# ------------------------------------------------------------------ 塔顶
def stepped_pyramid(p, st, cx, cz, size, y0, steps=3, rise=1.1, over=0.24,
                    mat="shingle", finial="gold", duty=False):
    """3 级阶梯锥顶（哨塔方冠 / 钟楼）。"""
    for k in range(steps):
        s = size + over * 2 - k * (size * 0.55 / steps)
        h = rise / steps
        hs.frustum(p, st, mat, cx, cz, s, s * 0.86, y0 + k * h, y0 + (k + 1) * h,
                   tile=0.9, role="roof")
    if finial:
        hs.frustum(p, st, finial, cx, cz, 0.16, 0.16, y0 + rise, y0 + rise + 0.22,
                   tile=0.8, role="finial")
