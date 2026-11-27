"""
buildings.py —— 六座建筑（v3：阵营染色 / 平顶要塞 / 外露炉膛 / 田垄 / 龙门吊）

几何纪律
--------
* 只有轴对齐长方体。坡度 = 阶梯体块；圆 = 阶梯八/十二边形；斜撑 = 阶梯段。
* 每个构件都带 stage，施工时序由 STAGES 统一驱动。
* 所有贴片类构件（厚 < 0.05）用 surf()/plate() 放置，强制 8 mm 离面，
  不允许再出现 0.026 / 0.030 这种手写魔法偏移。

本轮结构性改动
--------------
* 旗帜改为三种西幻制式（燕尾垂旗 / 长条三角旗 / 垂挂帷幔），宽高比 1:2.4 与 1:3.6。
* 阵营色沿结构线布置：檐口、腰线、垛口压顶、柱箍、栏板、盾面、门楣 —— 每座 ≥6 处。
* 兵营改为平顶 + 雉堞 + 三座角楼，彻底退出"坡屋顶民房"家族。
* 铁匠铺炉膛凸出正立面、烟囱独立砌到 13.6 m；伐木场加 8.6 m 龙门吊；
  农场筒仓 9.5 m + 三条田垄 + 三种作物。
"""
import math

import numpy as np

import detail
import hs
import roofs_hs as roofs
from hs import box as H
from matlib import MATERIALS
from roofs_hs import _prism_x

S_SITE, S_FOUND, S_SCAF = 0, 1, 2
S_WL, S_WM, S_WH, S_WT = 3, 4, 5, 6
S_BEAM, S_RL, S_RH, S_TRIM, S_FLAG, S_RUB = 7, 8, 9, 10, 11, 12

STAGES = [
    (S_SITE,  "放线",   0.000, 0.055),
    (S_FOUND, "台基",   0.045, 0.165),
    (S_SCAF,  "脚手架", 0.152, 0.245),
    (S_WL,    "墙体下", 0.228, 0.372),
    (S_WM,    "墙体中", 0.352, 0.496),
    (S_WH,    "墙体上", 0.478, 0.606),
    (S_WT,    "阁楼",   0.588, 0.700),
    (S_BEAM,  "梁架",   0.682, 0.782),
    (S_RL,    "屋面下", 0.762, 0.862),
    (S_RH,    "屋面上", 0.848, 0.930),
    (S_TRIM,  "饰件",   0.906, 0.972),
    (S_FLAG,  "旗帜",   0.950, 1.000),
]

STAGE_NAME = {s: n for s, n, a, b in STAGES}
STAGE_NAME[S_RUB] = "瓦砾"

PLATE_GAP = 0.008          # 贴片背面离基面的最小距离（8 mm，硬约束）
TC_THICK = 0.022           # 阵营色饰条厚度


def T(m):
    return MATERIALS[m][1]


def B(parts, stage, mat, cx, cy, cz, sx, sy, sz):
    parts.append({
        "stage": stage, "mat": mat, "tile": T(mat),
        "box": (round(cx, 3), round(cy, 3), round(cz, 3),
                round(sx, 3), round(sy, 3), round(sz, 3)),
    })


def surf(base, sign, thick, gap=PLATE_GAP):
    """贴片中心：基面 + 8 mm 空隙 + 半厚。"""
    return base + sign * (gap + thick / 2)


def plate(p, st, mat, cx, cy, cz, w, h, axis, base, sign, thick=0.024):
    """贴在轴对齐基面上的薄片。axis = 'x' 面法线沿 X，'z' 沿 Z。"""
    if axis == "z":
        B(p, st, mat, cx, cy, surf(base, sign, thick), w, h, thick)
    else:
        B(p, st, mat, surf(base, sign, thick), cy, cz, thick, h, w)





def _tag_duty(p, pred, role="duty"):
    """给已生成的构件打职责标签（旧代码用 B() 批量产出，不便逐句加参数）。"""
    n = 0
    for q in p:
        if q.get("role") is None and pred(q):
            q["role"] = role
            n += 1
    return n


# ================================================================== v5 硬边构件
def _mono_roof(p, eave, ridge, w, d, fz, over=0.35, mat="shingle", board=True):
    """单坡薄壳：椽 + 望板 + 瓦 + 封檐 + 阁楼体块。厚度恒 0.18。"""
    pl = roofs.Plane((-w / 2 - over, eave, fz - over), (w / 2 + over, eave, fz - over),
                     (-w / 2 - over, ridge, d / 2), (w / 2 + over, ridge, d / 2))
    nu = 2 if detail.LOW else max(2, int(round(pl.width() / 1.15)))
    nv = 2 if detail.LOW else max(3, int(round(pl.slope_len() / 1.0)))
    hs.grid_slab(p, S_RL, mat, pl, roofs.BOARD_T, nu=nu, nv=nv, offset=0.0,
                 tile=0.9, role="roof")
    n_raf = max(3, int(round(pl.width() / 0.55)))
    hs.rafters(p, S_RL, "wood_dark", pl, n_raf, w=roofs.RAFTER_W, h=roofs.RAFTER_H,
               drop=0.0, v0=-0.02, v1=0.995, tile=0.9, role="rafter")
    hs.courses(p, S_RH, mat, pl, course=0.22, thick=roofs.SHINGLE_T, lip=0.03,
               tile=0.9, role="roof")
    e0, e1 = pl.pt(0.0, 0.0), pl.pt(1.0, 0.0)
    n = pl.normal()
    hs.bar(p, S_RL, "wood_dark", e0 + n * (-0.03), e1 + n * (-0.03), 0.22, 0.12,
           up=n, tile=0.9, role="fascia")
    b0, b1 = pl.pt(0.0, 1.0), pl.pt(1.0, 1.0)
    hs.bar(p, S_RH, "wood_dark", b0, b1, 0.20, 0.16, up=(0, 1, 0), tile=0.9, role="ridge")
    hs.bar(p, S_RH, "cloth_team", b0 + np.array([0, 0.12, 0]), b1 + np.array([0, 0.12, 0]),
           0.26, 0.05, up=(0, 1, 0), tile=1.0, role="team")
    # 阁楼体块：内缩 0.10 的封闭三角体，挡住薄壳底下的空腔
    prof = [(fz + 0.10, eave), (d / 2 - 0.10, eave), (d / 2 - 0.10, ridge - 0.12)]
    roofs._prism_x(p, S_RH, "plaster", prof, -w / 2 + 0.12, w / 2 - 0.12)
    return roofs.RAFTER_H + roofs.BOARD_T + roofs.SHINGLE_T


def _small_roof(p, cx, z_back, z_front, y_back, y_front, width, mat="shingle"):
    """雨棚：同样走薄壳 + 椽 + 瓦，只是没有阁楼。"""
    pl = roofs.Plane((cx - width / 2, y_front, z_front), (cx + width / 2, y_front, z_front),
                     (cx - width / 2, y_back, z_back), (cx + width / 2, y_back, z_back))
    hs.grid_slab(p, S_TRIM, mat, pl, roofs.BOARD_T, nu=3, nv=2, offset=0.0, tile=0.8, role="roof")
    hs.rafters(p, S_TRIM, "wood_dark", pl, max(3, int(width / 0.5)),
               w=roofs.RAFTER_W, h=roofs.RAFTER_H, drop=0.0, tile=0.8, role="rafter")
    hs.courses(p, S_TRIM, mat, pl, course=0.20, thick=roofs.SHINGLE_T, lip=0.025,
               tile=0.8, role="roof")
    e0, e1 = pl.pt(0.0, 0.0), pl.pt(1.0, 0.0)
    n = pl.normal()
    hs.bar(p, S_TRIM, "wood_dark", e0 + n * (-0.02), e1 + n * (-0.02), 0.16, 0.08,
           up=n, tile=0.8, role="fascia")


def _anvil(p, st, x, z, duty=False):
    """铁砧：墩座 0.5 + 腰 0.34 + 砧面 0.62 × 0.20 × 0.28 + 前端三棱台角。"""
    hs.box(p, st, "wood_dark", x, 0.25, z, 0.50, 0.50, 0.50, tile=0.9)
    hs.box(p, st, "steel_dark", x, 0.67, z, 0.34, 0.34, 0.34, tile=0.7)
    hs.box(p, st, "steel", x, 0.94, z, 0.62, 0.20, 0.28, tile=0.7, role="duty" if duty else None)
    # 角：三棱台（锥形收分）
    hs.hexa(p, st, "steel",
            [(x - 0.31, 0.84, z - 0.14), (x - 0.31, 0.84, z + 0.14),
             (x - 0.62, 0.92, z + 0.05), (x - 0.62, 0.92, z - 0.05)],
            [(x - 0.31, 1.04, z - 0.14), (x - 0.31, 1.04, z + 0.14),
             (x - 0.62, 0.96, z + 0.05), (x - 0.62, 0.96, z - 0.05)],
            tile=0.7, role="duty" if duty else None)


def _quench(p, st, x, z):
    """淬火桶：12 边形 φ0.62 × 0.72，两道铁箍，水面用 window 材质。"""
    r = 0.31
    for i, (h, y) in enumerate(((0.72, 0.36),)):
        hs.prism_y(p, st, "wood_dark", hs.ngon(x, z, r, 12), 0.0, h, tile=0.9)
    for y in (0.16, 0.56):
        hs.prism_y(p, st, "cloth_team", hs.ngon(x, z, r + 0.012, 12), y - 0.05, y + 0.05,
                   tile=1.0, role="team")
    hs.prism_y(p, st, "window", hs.ngon(x, z, r - 0.03, 12), 0.66, 0.685, tile=0.7)


def _grind(p, st, x, z):
    """磨石：φ0.9 立轮 + 木架 + 脚踏。"""
    hs.box(p, st, "wood_dark", x, 0.22, z, 1.02, 0.14, 0.46, tile=0.9)
    for sx in (-1, 1):
        hs.box(p, st, "wood_dark", x + sx * 0.46, 0.62, z, 0.12, 0.86, 0.16, tile=0.9)
    hs.prism_y(p, st, "stone", hs.ngon(x, z, 0.45, 16), 0.40, 0.42, tile=1.0)  # 侧板
    # 立轮：绕 X 轴（用 XZ 面内的 16 边形沿 Z 挤出会立不起来，这里用 X 向棱柱）
    poly = [(x + 0.45 * math.cos(i * math.tau / 16), 0.98 + 0.45 * math.sin(i * math.tau / 16))
            for i in range(16)]
    hs.add(p, st, "stone", [(px, py, z - 0.09) for px, py in poly] + [(px, py, z + 0.09) for px, py in poly],
           [tuple(range(16)), tuple(range(16, 32))] +
           [(i, (i + 1) % 16, 16 + (i + 1) % 16, 16 + i) for i in range(16)], tile=1.0)
    hs.box(p, st, "steel_dark", x, 0.98, z, 0.10, 0.10, 0.30, tile=0.7)
    hs.box(p, st, "wood_dark", x + 0.05, 0.14, z - 0.50, 0.30, 0.08, 0.62, tile=0.9)


def _tools(p, st, x, z):
    """工具墙：锤 / 钳 / 锉 / 凿 / 铁条，全部挂住（不留浮空）。"""
    ys = (2.10, 1.86, 1.62, 2.14, 1.70)
    for i in range(5):
        y = ys[i]
        hs.box(p, st, "wood_dark", x, y, z - 0.55 + i * 0.28, 0.10, 0.22, 0.10, tile=0.8)
    # 锤
    hs.box(p, st, "wood_dark", x - 0.06, 1.98, z - 0.55, 0.06, 0.62, 0.06, tile=0.8)
    hs.box(p, st, "steel_dark", x - 0.06, 2.30, z - 0.55, 0.16, 0.14, 0.16, tile=0.7)
    # 钳
    for sz in (-0.04, 0.04):
        hs.bar(p, st, "steel_dark", (x - 0.05, 1.55, z - 0.27 + sz),
               (x - 0.05, 2.16, z - 0.29 + sz), 0.035, 0.035, up=(1, 0, 0), tile=0.7)
    # 锉
    hs.box(p, st, "steel_dark", x - 0.05, 1.86, z + 0.01, 0.04, 0.54, 0.06, tile=0.7)
    # 凿
    hs.box(p, st, "wood_dark", x - 0.05, 1.94, z + 0.29, 0.06, 0.42, 0.06, tile=0.8)
    hs.hexa(p, st, "steel", [(x - 0.08, 1.70, z + 0.27), (x - 0.02, 1.70, z + 0.27),
                             (x - 0.02, 1.70, z + 0.31), (x - 0.08, 1.70, z + 0.31)],
            [(x - 0.05, 1.58, z + 0.29), (x - 0.05, 1.58, z + 0.29),
             (x - 0.05, 1.58, z + 0.31), (x - 0.05, 1.58, z + 0.31)], tile=0.7)
    # 铁条
    hs.box(p, st, "steel", x - 0.05, 1.72, z + 0.57, 0.05, 0.70, 0.05, tile=0.7)


# ================================================================== 构件库
def brace_xy(p, st, mat, x0, y0, x1, y1, z, t=0.12, n=5):
    dx, dy = (x1 - x0) / n, (y1 - y0) / n
    for i in range(n):
        B(p, st, mat, x0 + dx * (i + 0.5), y0 + dy * (i + 0.5), z,
          abs(dx) * 1.18, abs(dy) * 1.18, t)


def brace_zy(p, st, mat, z0, y0, z1, y1, x, t=0.12, n=5):
    dz, dy = (z1 - z0) / n, (y1 - y0) / n
    for i in range(n):
        B(p, st, mat, x, y0 + dy * (i + 0.5), z0 + dz * (i + 0.5),
          t, abs(dy) * 1.18, abs(dz) * 1.18)


def wall(p, st, mat, cx, cz, w, d, y0, y1, t=0.30, gaps=()):
    """四面墙，可开洞。gaps: (side, a0, a1, hole_y0, hole_y1)"""
    def seg(side, a0, a1, yy0, yy1):
        if a1 - a0 < 0.03 or yy1 - yy0 < 0.03:
            return
        if side in ("-z", "+z"):
            zz = cz + (-d / 2 if side == "-z" else d / 2)
            B(p, st, mat, (a0 + a1) / 2, (yy0 + yy1) / 2, zz, a1 - a0, yy1 - yy0, t)
        else:
            xx = cx + (-w / 2 if side == "-x" else w / 2)
            B(p, st, mat, xx, (yy0 + yy1) / 2, (a0 + a1) / 2, t, yy1 - yy0, a1 - a0)

    for side, lo, hi in (("-z", cx - w / 2, cx + w / 2), ("+z", cx - w / 2, cx + w / 2)):
        holes = sorted([g for g in gaps if g[0] == side and g[3] < y1 and g[4] > y0],
                       key=lambda g: g[1])
        cur = lo
        for _s, a0, a1, hy0, hy1 in holes:
            seg(side, cur, a0, y0, y1)
            if hy0 > y0:
                seg(side, a0, a1, y0, hy0)
            if hy1 < y1:
                seg(side, a0, a1, hy1, y1)
            cur = a1
        seg(side, cur, hi, y0, y1)
    for side, lo, hi in (("-x", cz - d / 2, cz + d / 2), ("+x", cz - d / 2, cz + d / 2)):
        holes = sorted([g for g in gaps if g[0] == side and g[3] < y1 and g[4] > y0],
                       key=lambda g: g[1])
        cur = lo
        for _s, a0, a1, hy0, hy1 in holes:
            seg(side, cur, a0, y0, y1)
            if hy0 > y0:
                seg(side, a0, a1, y0, hy0)
            if hy1 < y1:
                seg(side, a0, a1, hy1, y1)
            cur = a1
        seg(side, cur, hi, y0, y1)


def roof_gable(p, st_lo, st_hi, mat, cx, cz, length, span, y0, steps=6, rise=2.4,
               over=0.42, ridge="x", split=0.5, cap=True, shingle=True, duty=False):
    """双坡薄壳屋面（v5）：椽 + 望板 + 瓦 + 封檐 + 脊 + 阁楼体块。总厚 0.18。

    steps / split 参数保留只为兼容旧调用点 —— 阶梯屋面本身已被淘汰。
    """
    if mat == "thatch":
        return roofs.thatch_gable(p, st_lo, st_hi, cx, cz,
                                     length if ridge == "x" else span,
                                     span if ridge == "x" else length,
                                     y0, y0 + rise, over=over, ridge_axis=ridge)
    run = (span / 2 if ridge == "x" else length / 2)
    ridge_y = y0 + max(rise, 0.4)
    if ridge == "x":
        a0 = (cx - length / 2 - over, y0, cz - span / 2 - over)
        a1 = (cx + length / 2 + over, y0, cz - span / 2 - over)
        b0 = (cx - length / 2 - over, ridge_y, cz)
        b1 = (cx + length / 2 + over, ridge_y, cz)
        pls = [roofs.Plane(a0, a1, b0, b1)]
        a2 = (cx - length / 2 - over, y0, cz + span / 2 + over)
        a3 = (cx + length / 2 + over, y0, cz + span / 2 + over)
        pls.append(roofs.Plane(a2, a3, b0, b1))
    else:
        a0 = (cx - span / 2 - over, y0, cz - length / 2 - over)
        a1 = (cx - span / 2 - over, y0, cz + length / 2 + over)
        b0 = (cx, ridge_y, cz - length / 2 - over)
        b1 = (cx, ridge_y, cz + length / 2 + over)
        pls = [roofs.Plane(a0, a1, b0, b1)]
        a2 = (cx + span / 2 + over, y0, cz - length / 2 - over)
        a3 = (cx + span / 2 + over, y0, cz + length / 2 + over)
        pls.append(roofs.Plane(a2, a3, b0, b1))
    for pl, st in ((pls[0], st_lo), (pls[1], st_hi)):
        nu = max(2, int(round(pl.width() / 1.15)))
        nv = max(2, int(round(pl.slope_len() / 1.0)))
        hs.grid_slab(p, st, mat, pl, roofs.BOARD_T, nu=nu, nv=nv, offset=0.0,
                     tile=0.9, role="roof")
        hs.rafters(p, st, "wood_dark", pl, max(2, int(round(pl.width() / 0.55))),
                   w=roofs.RAFTER_W, h=roofs.RAFTER_H, drop=0.0, v0=-0.02, v1=0.995,
                   tile=0.9, role="rafter")
        hs.courses(p, st, mat, pl, course=0.22, thick=roofs.SHINGLE_T, lip=0.03,
                   tile=0.9, role="roof")
        e0, e1 = pl.pt(0.0, 0.0), pl.pt(1.0, 0.0)
        n = pl.normal()
        hs.bar(p, st, "wood_dark", e0 + n * (-0.03), e1 + n * (-0.03), 0.22, 0.12,
               up=n, tile=0.9, role="fascia")
    if cap:
        if ridge == "x":
            hs.ridge_cap(p, st_hi, "wood_dark", "cloth_team",
                         (cx - length / 2 - over, ridge_y, cz),
                         (cx + length / 2 + over, ridge_y, cz), ridge_y + 0.02, team=True)
        else:
            hs.ridge_cap(p, st_hi, "wood_dark", "cloth_team",
                         (cx, ridge_y, cz - length / 2 - over),
                         (cx, ridge_y, cz + length / 2 - -over), ridge_y + 0.02, team=True)
    # 阁楼体块：内缩 0.10，把薄壳下面的空腔挡住
    inset = 0.10
    if ridge == "x":
        prof = [(cz - span / 2 + inset, y0), (cz + span / 2 - inset, y0), (cz, ridge_y - 0.14)]
        roofs._prism_x(p, st_hi, "plaster", prof, cx - length / 2 + inset, cx + length / 2 - inset)
    else:
        prof = [(cx - span / 2 + inset, y0), (cx + span / 2 - inset, y0), (cx, ridge_y - 0.14)]
        roofs._prism_z(p, st_hi, "plaster", prof, cz - length / 2 + inset, cz + length / 2 - inset)
    return roofs.RAFTER_H + roofs.BOARD_T + roofs.SHINGLE_T


def roof_mono(p, st_lo, st_hi, mat, cx, cz, length, span, y0, steps=5, rise=1.8,
              over=0.34, axis="z", direction=1, split=0.5, thick=0.30,
              fill=None, fill_mat="stone", shingle=True, duty=False):
    """单坡薄壳（v5）。高侧在 cz - direction*span/2（axis=z）或 cx - direction*length/2。"""
    if mat == "thatch":
        return roofs.thatch_gable(p, st_lo, st_hi, cx, cz,
                                     length, span, y0, y0 + rise, over=over,
                                     ridge_axis="x" if axis == "z" else "z")
    ridge_y = y0 + max(rise, 0.3)
    if axis == "z":
        z_lo = cz + direction * (span / 2 + over)
        z_hi = cz - direction * (span / 2)
        pl = roofs.Plane((cx - length / 2 - over, y0, z_lo), (cx + length / 2 + over, y0, z_lo),
                         (cx - length / 2 - over, ridge_y, z_hi), (cx + length / 2 + over, ridge_y, z_hi))
    else:
        x_lo = cx + direction * (length / 2 + over)
        x_hi = cx - direction * (length / 2)
        pl = roofs.Plane((x_lo, y0, cz - span / 2 - over), (x_lo, y0, cz + span / 2 + over),
                         (x_hi, ridge_y, cz - span / 2 - over), (x_hi, ridge_y, cz + span / 2 + over))
    st = st_lo
    hs.grid_slab(p, st, mat, pl, roofs.BOARD_T,
                 nu=max(2, int(round(pl.width() / 1.15))),
                 nv=max(2, int(round(pl.slope_len() / 1.0))), tile=0.9, role="roof")
    hs.rafters(p, st, "wood_dark", pl, max(2, int(round(pl.width() / 0.55))),
               w=roofs.RAFTER_W, h=roofs.RAFTER_H, drop=0.0, v0=-0.02, v1=0.995,
               tile=0.9, role="rafter")
    hs.courses(p, st, mat, pl, course=0.22, thick=roofs.SHINGLE_T, lip=0.03,
               tile=0.9, role="roof")
    e0, e1 = pl.pt(0.0, 0.0), pl.pt(1.0, 0.0)
    n = pl.normal()
    hs.bar(p, st, "wood_dark", e0 + n * (-0.03), e1 + n * (-0.03), 0.22, 0.12,
           up=n, tile=0.9, role="fascia")
    # 高侧压顶
    b0, b1 = pl.pt(0.0, 1.0), pl.pt(1.0, 1.0)
    hs.bar(p, st_hi, "wood_dark", b0, b1, 0.20, 0.16, up=(0, 1, 0), tile=0.9, role="ridge")
    hs.bar(p, st_hi, "cloth_team", b0 + np.array([0, 0.12, 0]), b1 + np.array([0, 0.12, 0]),
           0.26, 0.05, up=(0, 1, 0), tile=1.0, role="team")
    return roofs.RAFTER_H + roofs.BOARD_T + roofs.SHINGLE_T


def roof_pyramid(p, st, mat, cx, cz, size, y0, steps=3, rise=1.0, over=0.4,
                 finial="gold", cap_mat="wood_dark"):
    """阶梯锥顶：用锥台（而不是叠盒子）收分，棱线是直的。"""
    th = rise / steps
    s0 = size + over * 2
    for k in range(steps):
        s_at0 = s0 - k * (s0 * 0.42 / steps)
        s_at1 = s0 - (k + 1) * (s0 * 0.42 / steps)
        hs.frustum(p, st, mat, cx, cz, s_at0, s_at1, y0 + k * th, y0 + (k + 1) * th,
                   tile=0.9, role="cap")
    hs.box(p, st, cap_mat, cx, y0 + rise + 0.05, cz, 0.22, 0.12, 0.22, tile=0.9)
    if finial:
        hs.frustum(p, st, finial, cx, cz, 0.16, 0.16, y0 + rise + 0.11, y0 + rise + 0.35,
                   tile=0.8, role="finial")


def quoins(p, st, mat, cx, cz, w, d, y0, y1, step=0.30, proj=0.03):
    """交错角石：每皮 0.30 高，块 0.45 × 0.36，长短交替但**不往外凸成台阶**。

    v5 修正：旧版每块尺寸在 0.50/0.36 之间跳，转角在剪影上变成一段楼梯；
    现在尺寸恒定，只让奇偶皮的出挑差 15 mm —— 读作砌筑，不读作楼梯。
    """
    L = 0.45
    i = 0
    y = y0
    while y < y1 - 0.02:
        hh = min(step, y1 - y)
        off = proj if i % 2 == 0 else proj * 0.45
        for sx in (-1, 1):
            for sz in (-1, 1):
                cx2 = cx + sx * (w / 2 - L / 2 + off)
                cz2 = cz + sz * (d / 2 - L / 2 + off)
                hs.box(p, st, mat, cx2, y + hh / 2, cz2, L, hh * 0.92, L,
                       tile=1.0)
                if i % 2 == 0:
                    # 长皮：沿墙再压半块，读作交错咬合
                    hs.box(p, st, mat, cx2 + sx * L * 0.5 * 0, y + hh / 2,
                           cz2 + sz * L * 0.5, L * 0.72, hh * 0.92, L * 0.5, tile=1.0)
        y += hh
        i += 1


def window_unit(p, st, x, y, z, w, h, facing, shutters=True, glass="window", team_pelmet=False):
    if facing in ("-x", "+x"):
        sgnx = -1 if facing == "-x" else 1
        B(p, st, "wood_dark", x, y + h / 2 + 0.07, z, 0.12, 0.14, w + 0.18)
        B(p, st, "wood_dark", x + sgnx * 0.03, y - h / 2 - 0.06, z, 0.26, 0.11, w + 0.28)
        B(p, st, "wood_dark", x, y, z - w / 2 - 0.07, 0.12, h, 0.14)
        B(p, st, "wood_dark", x, y, z + w / 2 + 0.07, 0.12, h, 0.14)
        B(p, st, glass, x + sgnx * 0.02, y, z, 0.07, h, w)
        B(p, st, "wood_dark", x + sgnx * 0.05, y, z, 0.06, h, 0.06)
        if shutters:
            B(p, st, "wood_dark", x + sgnx * 0.08, y, z - w / 2 - 0.30, 0.10, h * 0.96, 0.34)
            B(p, st, "wood_dark", x + sgnx * 0.08, y, z + w / 2 + 0.30, 0.10, h * 0.96, 0.34)
        if team_pelmet:
            plate(p, st, "cloth_team", x, y + h / 2 + 0.19, z, w + 0.26, 0.14,
                  "x", x, sgnx)
        return
    sgn = -1 if facing == "-z" else 1
    B(p, st, "wood_dark", x, y + h / 2 + 0.07, z + sgn * 0.04, w + 0.18, 0.14, 0.14)
    B(p, st, "wood_dark", x, y - h / 2 - 0.06, z + sgn * 0.05, w + 0.28, 0.11, 0.26)
    B(p, st, "wood_dark", x - w / 2 - 0.07, y, z + sgn * 0.02, 0.14, h, 0.12)
    B(p, st, "wood_dark", x + w / 2 + 0.07, y, z + sgn * 0.02, 0.14, h, 0.12)
    B(p, st, glass, x, y, z + sgn * 0.03, w, h, 0.07)
    B(p, st, "wood_dark", x, y, z + sgn * 0.06, 0.06, h, 0.06)
    if shutters:
        B(p, st, "wood_dark", x - w / 2 - 0.30, y, z + sgn * 0.07, 0.34, h * 0.96, 0.10)
        B(p, st, "wood_dark", x + w / 2 + 0.30, y, z + sgn * 0.07, 0.34, h * 0.96, 0.10)
    if team_pelmet:
        plate(p, st, "cloth_team", x, y + h / 2 + 0.19, z, w + 0.26, 0.14,
              "z", z, sgn)


def chimney(p, st, mat, x, z, y0, y1, w=1.0, cap=True, team_hoops=()):
    B(p, st, mat, x, (y0 + y1) / 2, z, w, y1 - y0, w)
    for y in team_hoops:
        hoop(p, S_TRIM, x, z, w / 2 * 1.02, y, 0.38, 0.08, "cloth_team")
    if cap:
        B(p, S_TRIM, "stone_dark", x, y1 + 0.10, z, w + 0.26, 0.20, w + 0.26)
        B(p, S_TRIM, "stone_dark", x, y1 + 0.26, z, w * 0.55, 0.16, w * 0.55)


def ladder(p, st, x, z, y0, y1, facing="-z", w=0.72, cage=False):
    B(p, st, "wood", x - w / 2, (y0 + y1) / 2, z, 0.10, y1 - y0, 0.10)
    B(p, st, "wood", x + w / 2, (y0 + y1) / 2, z, 0.10, y1 - y0, 0.10)
    n = max(2, int((y1 - y0) / 0.42))
    for i in range(n):
        B(p, st, "wood", x, y0 + 0.24 + i * (y1 - y0 - 0.3) / (n - 1), z, w, 0.07, 0.09)
    if cage:
        for i in range(6):
            yy = y0 + 1.4 + i * max(0.7, (y1 - y0 - 2.0) / 6)
            B(p, st, "wood_dark", x + facingx(facing) * 0.42, yy, z, 0.07, 0.07, 0.9)
            B(p, st, "wood_dark", x, yy, z + facingz(facing) * 0.42, 0.9, 0.07, 0.07)


def facingx(f):
    return -1 if f == "-x" else (1 if f == "+x" else 0)


def facingz(f):
    return -1 if f == "-z" else (1 if f == "+z" else 0)


def oct_column(p, st, mat, cx, cz, r, y0, y1, layer=1.15, team_ring=()):
    """阶梯八边形柱：每层 6 个盒（十字 + 四角），远看是八边形。"""
    y = y0
    while y < y1 - 0.02:
        h = min(layer, y1 - y)
        cy = y + h / 2
        B(p, st, mat, cx, cy, cz, 2 * r, h, 1.15 * r)
        B(p, st, mat, cx, cy, cz, 1.15 * r, h, 2 * r)
        for sx in (-1, 1):
            for sz in (-1, 1):
                B(p, st, mat, cx + sx * 0.60 * r, cy, cz + sz * 0.60 * r,
                  0.86 * r, h, 0.86 * r)
        y += h
    for yy in team_ring:
        # 1.03 时箍带正好埋进八边形的角块里，只剩断续的红点；拉到 1.10 才读作一圈
        hoop(p, S_TRIM, cx, cz, r * 1.10, yy, 0.20, 0.08, "cloth_team")


def oct_slab(p, st, mat, cx, cz, r, y0, h, shrink=1.0):
    rr = r * shrink
    B(p, st, mat, cx, y0 + h / 2, cz, 2 * rr, h, 1.15 * rr)
    B(p, st, mat, cx, y0 + h / 2, cz, 1.15 * rr, h, 2 * rr)
    for sx in (-1, 1):
        for sz in (-1, 1):
            B(p, st, mat, cx + sx * 0.60 * rr, y0 + h / 2, cz + sz * 0.60 * rr,
              0.86 * rr, h, 0.86 * rr)


def hoop(p, st, cx, cz, r, y, h, t, mat):
    """方形环箍（套在阶梯八边形柱外，读作铁箍）。"""
    B(p, st, mat, cx, y, cz - r + t / 2, 2 * r, h, t)
    B(p, st, mat, cx, y, cz + r - t / 2, 2 * r, h, t)
    B(p, st, mat, cx - r + t / 2, y, cz, t, h, 2 * r)
    B(p, st, mat, cx + r - t / 2, y, cz, t, h, 2 * r)


def disc_vert(p, st, mat, cx, cy, cz, r, thick=0.14, axis="x", teeth=0):
    """竖直阶梯圆盘：用 3 个盒拼出八边形轮廓，可选周向齿。axis=法线方向。"""
    if axis == "x":
        B(p, st, mat, cx, cy, cz, thick, r * 1.5, r * 1.5)
        B(p, st, mat, cx, cy, cz, thick, r * 2.0, r * 1.1)
        B(p, st, mat, cx, cy, cz, thick, r * 1.1, r * 2.0)
        if teeth:
            for i in range(teeth):
                a = i * math.tau / teeth
                B(p, st, mat, cx, cy + math.sin(a) * r * 1.03,
                  cz + math.cos(a) * r * 1.03, thick, 0.10, 0.10)
    else:
        B(p, st, mat, cx, cy, cz, r * 1.5, r * 1.5, thick)
        B(p, st, mat, cx, cy, cz, r * 2.0, r * 1.1, thick)
        B(p, st, mat, cx, cy, cz, r * 1.1, r * 2.0, thick)


def stepped_steps(p, st, mat, cx, z_front, w, n, rise, run, sign=-1):
    """台阶：从 z_front 向 sign 方向逐级下降/上升。"""
    for i in range(n):
        z = z_front + sign * (i * run + run / 2)
        B(p, st, mat, cx, (i + 1) * rise / 2, z, w, (i + 1) * rise, run + 0.01)


# ---------------------------------------------------------------- 旗帜三制式
def _emblem(p, st, cx, cy, cz, size, axis, sign):
    if axis == "z":
        plate(p, st, "emblem", cx, cy, cz, size, size, "z", cz, sign, 0.014)
    else:
        plate(p, st, "emblem", cx, cy, cz, size, size, "x", cx, sign, 0.014)


def flag_a(p, st, x, y, z, w=0.55, h=1.45, axis="x", sign=-1, pole=True):
    """A 燕尾垂旗：3 段布 + 5 条竖向布条做 V 形缺口，上沿横杆 + 球头，徽记在上 1/3。
    (x,y,z) = 旗面顶边中点；axis = 横杆方向。"""
    if pole:
        if axis == "x":
            B(p, st, "wood_dark", x, y + 0.03, z, w + 0.26, 0.05, 0.05)
            for s in (-1, 1):
                B(p, st, "gold", x + s * (w / 2 + 0.15), y + 0.03, z, 0.08, 0.08, 0.08)
        else:
            B(p, st, "wood_dark", x, y + 0.03, z, 0.05, 0.05, w + 0.26)
            for s in (-1, 1):
                B(p, st, "gold", x, y + 0.03, z + s * (w / 2 + 0.15), 0.08, 0.08, 0.08)
    ns = 5
    sw = w / ns
    for i in range(ns):
        # V 形缺口：中间两条短，向两侧递增
        k = abs(i - (ns - 1) / 2) / ((ns - 1) / 2)
        hh = h * (0.80 + 0.20 * k)
        off = (0.015 if i % 2 else -0.015)
        cx = x + (i - (ns - 1) / 2) * sw
        if axis == "x":
            B(p, st, "cloth_team", cx, y - hh / 2 - 0.03, z + off,
              sw + 0.006, hh, 0.028)
        else:
            B(p, st, "cloth_team", x + off, y - hh / 2 - 0.03, cx,
              0.028, hh, sw + 0.006)
    # 徽记：上 1/3，不居中
    if axis == "x":
        _emblem(p, st, x, y - h * 0.28, z - 0.03, w * 0.45, "z", -1)
    else:
        _emblem(p, st, x - 0.03, y - h * 0.28, z, w * 0.45, "x", -1)


def flag_b(p, st, x, y, z, w=0.30, ln=1.10, direction=1, pole_top=False):
    """B 长条三角旗：3 段递减宽度 + 每段错 1 cm；杆顶阶梯四棱锥矛尖。"""
    widths = (w, w * 0.66, w * 0.33)
    lens = (ln * 0.46, ln * 0.32, ln * 0.22)
    cur = x
    for i, (ww, ll) in enumerate(zip(widths, lens)):
        B(p, st, "cloth_team", cur + direction * ll / 2, y - 0.02 + i * 0.01, z,
          ll, 0.03, ww)
        cur += direction * ll
    if pole_top:
        B(p, st, "steel", x, y + 0.14, z, 0.09, 0.26, 0.09)
        B(p, st, "steel", x, y + 0.31, z, 0.06, 0.14, 0.06)
        B(p, st, "steel", x, y + 0.42, z, 0.03, 0.10, 0.03)


def awning(p, st, x, y, z, w, depth, sign=-1, drop=0.45, posts=True):
    """木构雨棚（v5 §10.8：布篷全部取消 —— 布是软的，和硬边冲突）。

    两根 0.14 方柱落在石墩上，柱顶横梁、斜椽、小瓦顶；出挑深度即 depth。
    """
    z_out = z + sign * depth
    y_out = y - drop
    if posts:
        for sx in (-1, 1):
            px = x + sx * (w / 2 - 0.14)
            hs.box(p, st, "wood_dark", px, (y_out - 0.30) / 2 + 0.15, z_out - sign * 0.06,
                   0.14, max(0.4, y_out - 0.30), 0.14, tile=0.9)
            hs.box(p, S_FOUND, "stone_dark", px, 0.20, z_out - sign * 0.06,
                   0.34, 0.40, 0.34, tile=1.0)
        hs.box(p, st, "wood_dark", x, y_out - 0.10, z_out - sign * 0.06,
               w, 0.14, 0.16, tile=0.9)
    # 斜椽：从墙面挑到外沿
    n = max(3, int(w / 0.55))
    for i in range(n):
        xx = x - w / 2 + (i + 0.5) * w / n
        # 斜椽的里端要插进墙里 0.18，不能只在墙皮上点一下（会留 15 cm 缝）
        hs.bar(p, st, "wood_dark", (xx, y + 0.10, z + sign * 0.18),
               (xx, y_out + 0.02, z_out), 0.12, 0.10, up=(0, 1, 0), tile=0.9)
    _small_roof(p, x, z + sign * 0.02, z_out, y + 0.10, y_out + 0.06, w)


def banner_v(p, st, x, y_top, z, w=0.75, h=2.8, facing="-z"):
    """竖向垂幅（挂在墙面的长布），上 1/4 处放 TC2 徽记。"""
    sgn = -1 if facing == "-z" else 1
    B(p, st, "wood_dark", x, y_top, z + sgn * 0.05, w + 0.18, 0.07, 0.09)
    for s in (-1, 1):
        B(p, st, "gold", x + s * (w / 2 + 0.10), y_top, z + sgn * 0.05, 0.08, 0.08, 0.08)
    ns = 5
    for i in range(ns):
        sw = w / ns
        hh = h - (0.05 if i % 2 else 0.0)
        B(p, st, "cloth_team", x - w / 2 + sw * (i + 0.5), y_top - hh / 2 - 0.04,
          z + sgn * 0.02, sw - 0.004, hh, 0.028)
    _emblem(p, st, x, y_top - h * 0.28, z - sgn * 0.01, w * 0.45, "z", sgn)


def flag_c(p, st, cx, y, cz, w, h=0.60, axis="x", sign=-1):
    """C 垂挂帷幔：5 条竖布，长度交替差 4 cm，上沿一道横档。"""
    if axis == "x":
        B(p, st, "wood_dark", cx, y, cz - sign * 0.03, w + 0.10, 0.07, 0.09)
        ns = 5
        for i in range(ns):
            sw = w / ns
            hh = h - (0.04 if i % 2 else 0.0)
            B(p, st, "cloth_team", cx - w / 2 + sw * (i + 0.5), y - hh / 2 - 0.02,
              cz - sign * 0.02, sw - 0.004, hh, 0.026)
    else:
        B(p, st, "wood_dark", cx - sign * 0.03, y, cz, 0.09, 0.07, w + 0.10)
        ns = 5
        for i in range(ns):
            sw = w / ns
            hh = h - (0.04 if i % 2 else 0.0)
            B(p, st, "cloth_team", cx - sign * 0.02, y - hh / 2 - 0.02,
              cz - w / 2 + sw * (i + 0.5), 0.026, hh, sw - 0.004)


def battlement(p, st, cx, cz, w, d, y, ph=0.95, pt=0.34, mw=0.50, mh=0.55,
               spacing=0.92):
    """沿矩形周长的女儿墙 + 垛口，返回垛数。垛顶压顶为 TC1。"""
    B(p, st, "stone_dark", cx, y + ph / 2, cz - d / 2 + pt / 2, w, ph, pt)
    B(p, st, "stone_dark", cx, y + ph / 2, cz + d / 2 - pt / 2, w, ph, pt)
    B(p, st, "stone_dark", cx - w / 2 + pt / 2, y + ph / 2, cz, pt, ph, d - 2 * pt)
    B(p, st, "stone_dark", cx + w / 2 - pt / 2, y + ph / 2, cz, pt, ph, d - 2 * pt)
    n = 0
    # 前后两面
    for sz in (-1, 1):
        cnt = max(2, int((w - mw) / spacing) + 1)
        for i in range(cnt):
            xx = cx - w / 2 + pt + mw / 2 + i * spacing
            if xx + mw / 2 > cx + w / 2 - pt + 1e-6:
                break
            B(p, st, "stone_dark", xx, y + ph + mh / 2, cz + sz * (d / 2 - pt / 2),
              mw, mh, pt)
            B(p, S_TRIM, "cloth_team", xx, y + ph + mh + 0.045, cz + sz * (d / 2 - pt / 2),
              mw + 0.08, 0.09, pt + 0.06)
            n += 1
    # 左右两面
    for sx in (-1, 1):
        cnt = max(2, int((d - mw) / spacing) + 1)
        for i in range(cnt):
            zz = cz - d / 2 + pt + mw / 2 + i * spacing
            if zz + mw / 2 > cz + d / 2 - pt + 1e-6:
                break
            B(p, st, "stone_dark", cx + sx * (w / 2 - pt / 2),
              y + ph + mh / 2, zz, pt, mh, mw)
            B(p, S_TRIM, "cloth_team", cx + sx * (w / 2 - pt / 2),
              y + ph + mh + 0.045, zz, pt + 0.06, 0.09, mw + 0.08)
            n += 1
    return n


def scaffold(p, cx, cz, w, d, h, levels=3):
    st = S_SCAF
    for sx in (-1, 1):
        for sz in (-1, 1):
            B(p, st, "wood", cx + sx * (w / 2 + 0.34), h / 2, cz + sz * (d / 2 + 0.34),
              0.12, h, 0.12)
    for i in range(levels):
        yy = h * (i + 0.9) / (levels + 0.9)
        B(p, st, "wood", cx, yy, cz - d / 2 - 0.34, w + 0.80, 0.085, 0.085)
        B(p, st, "wood", cx, yy, cz + d / 2 + 0.34, w + 0.80, 0.085, 0.085)
        B(p, st, "wood", cx - w / 2 - 0.34, yy, cz, 0.085, 0.085, d + 0.80)
        B(p, st, "wood", cx + w / 2 + 0.34, yy, cz, 0.085, 0.085, d + 0.80)
    for i in range(levels):
        y0 = h * i / (levels + 0.9)
        y1 = h * (i + 0.9) / (levels + 0.9)
        brace_xy(p, st, "wood_dark", cx - w / 2 - 0.34, y0 + 0.14,
                 cx + w / 2 + 0.34, y1 - 0.14, cz - d / 2 - 0.34, 0.07, 6)
        brace_zy(p, st, "wood_dark", cz - d / 2 - 0.34, y0 + 0.14,
                 cz + d / 2 + 0.34, y1 - 0.14, cx + w / 2 + 0.34, 0.07, 6)
    B(p, st, "wood_dark", cx, h - 0.06, cz - d / 2 - 0.30, w + 0.6, 0.09, 0.72)
    B(p, st, "wood_dark", cx, h - 0.06, cz + d / 2 + 0.30, w + 0.6, 0.09, 0.72)


def rubble(p, cx, cz, w, d, n=24):
    import random
    r = random.Random(11)
    for i in range(n):
        x = cx + (r.random() - 0.5) * w * 0.92
        z = cz + (r.random() - 0.5) * d * 0.92
        s = 0.20 + r.random() * 0.46
        B(p, S_RUB, "stone_dark" if i % 3 else "wood_dark",
          x, s * 0.46, z, s, s * (0.55 + r.random() * 0.7), s)


# ---------------------------------------------------------------- 场院道具
def brazier(p, st, x, z, y0=0.0):
    B(p, st, "stone_dark", x, y0 + 0.26, z, 0.52, 0.52, 0.52)
    B(p, st, "steel_dark", x, y0 + 0.60, z, 0.62, 0.18, 0.62)
    B(p, st, "steel_dark", x, y0 + 0.72, z, 0.50, 0.10, 0.50)
    B(p, st, "ember", x, y0 + 0.70, z, 0.40, 0.07, 0.40)
    for sx in (-1, 1):
        B(p, st, "steel_dark", x + sx * 0.22, y0 + 0.47, z, 0.07, 0.34, 0.07)
    B(p, st, "cloth_team", x, y0 + 0.52, z, 0.56, 0.08, 0.10)


def barrel(p, st, x, z, y0=0.0, r=0.31, h=0.72):
    oct_slab(p, st, "wood", x, z, r, y0, h * 0.5)
    oct_slab(p, st, "wood", x, z, r * 0.94, y0 + h * 0.5, h * 0.5)
    hoop(p, st, x, z, r * 1.03, y0 + h * 0.22, 0.07, 0.05, "steel_dark")
    hoop(p, st, x, z, r * 1.03, y0 + h * 0.72, 0.07, 0.05, "steel_dark")


def anvil(p, st, x, z, y0=0.0):
    B(p, st, "wood_dark", x, y0 + 0.24, z, 0.50, 0.48, 0.50)
    B(p, st, "steel_dark", x, y0 + 0.56, z, 0.32, 0.18, 0.32)
    B(p, st, "steel_dark", x, y0 + 0.72, z, 0.64, 0.18, 0.28)
    for i in range(3):
        B(p, st, "steel_dark", x + 0.34 + i * 0.085, y0 + 0.72 - i * 0.02,
          z, 0.16 - i * 0.04, 0.12, 0.20 - i * 0.05)


def haystack(p, st, x, z, r=0.8, h=1.2, mat="thatch"):
    layers = 3
    for i in range(layers):
        oct_slab(p, st, mat, x, z, r * (1 - i * 0.16), i * h / layers,
                 h / layers * 1.02)
    B(p, st, "wood_dark", x, h + 0.04, z, 0.10, 0.34, 0.10)
    B(p, st, "cloth_team", x, h * 0.62, z, r * 1.9, 0.10, 0.10)


def shield(p, st, x, y, z, w=0.58, h=0.82, facing="-z"):
    """筝形盾：4 级递减 + 铁边 + TC1 盾面 + TC2 徽记。"""
    sgn = -1 if facing == "-z" else 1
    lv = ((0.00, 1.00), (0.22, 0.90), (0.46, 0.68), (0.70, 0.40))
    for dy, k in lv:
        B(p, st, "steel", x, y + h / 2 - h * (dy + 0.10), z, w * k, h * 0.20, 0.05)
        B(p, st, "cloth_team", x, y + h / 2 - h * (dy + 0.10), z + sgn * 0.035,
          w * k * 0.86, h * 0.16, 0.03)
    _emblem(p, st, x, y + 0.10, z + sgn * 0.05, w * 0.34, "z", sgn)


def pell(p, st, x, z, y0=0.0):
    B(p, st, "stone_dark", x, y0 + 0.28, z, 0.62, 0.56, 0.62)
    oct_column(p, st, "wood", x, z, 0.13, y0 + 0.56, y0 + 2.05, 0.75)
    B(p, st, "wood", x, y0 + 1.72, z, 1.12, 0.14, 0.14)
    for s in (-1, 1):
        B(p, st, "wood", x + s * 0.58, y0 + 1.72, z, 0.16, 0.20, 0.20)
    B(p, st, "thatch", x, y0 + 2.26, z, 0.42, 0.42, 0.42)
    B(p, st, "leather", x, y0 + 1.35, z, 0.56, 0.62, 0.40)
    B(p, st, "cloth_team", x, y0 + 1.42, z - 0.21, 0.50, 0.48, 0.03)
    _emblem(p, st, x, y0 + 1.44, z - 0.24, 0.26, "z", -1)


def weapon_rack(p, st, x, z, y0=0.0, n_spear=6):
    for s in (-1, 1):
        B(p, st, "wood_dark", x + s * 1.15, y0 + 0.95, z, 0.16, 1.90, 0.16)
    for yy in (y0 + 0.55, y0 + 1.55):
        B(p, st, "wood", x, yy, z, 2.40, 0.11, 0.11)
    for i in range(n_spear):
        xx = x - 0.72 + i * 0.29
        hh = 2.35 + (i % 3) * 0.05
        B(p, st, "wood", xx, y0 + hh / 2, z - 0.08, 0.055, hh, 0.055)
        B(p, st, "steel", xx, y0 + hh + 0.08, z - 0.08, 0.07, 0.24, 0.07)
    for i in range(3):
        B(p, st, "steel", x - 0.20 + i * 0.22, y0 + 1.20, z + 0.06, 0.10, 1.05, 0.05)
        B(p, st, "wood_dark", x - 0.20 + i * 0.22, y0 + 0.62, z + 0.06, 0.14, 0.16, 0.10)
    B(p, st, "cloth_team", x, y0 + 1.10, z + 0.13, 2.20, 0.10, 0.04)


def notice_board(p, st, x, z, y0=0.0):
    for s in (-1, 1):
        B(p, st, "wood_dark", x + s * 0.95, y0 + 1.05, z, 0.16, 2.10, 0.16)
    B(p, st, "wood", x, y0 + 1.62, z, 2.10, 0.92, 0.10)
    B(p, st, "cloth_team", x, y0 + 2.18, z - 0.06, 2.24, 0.14, 0.05)
    for i in range(3):
        plate(p, st, "plaster", x - 0.62 + i * 0.62, y0 + 1.68, z, 0.42, 0.56, "z", z, -1, 0.012)
    B(p, st, "cloth_team", x, y0 + 1.10, z - 0.06, 2.24, 0.10, 0.05)


def trough(p, st, x, z, y0=0.0):
    B(p, st, "stone", x, y0 + 0.20, z, 2.24, 0.40, 0.72)
    B(p, st, "window", x, y0 + 0.42, z, 2.02, 0.03, 0.54)
    B(p, st, "cloth_team", x, y0 + 0.50, z - 0.38, 2.28, 0.10, 0.06)
    for s in (-1, 1):
        B(p, st, "wood_dark", x + s * 1.05, y0 + 0.62, z, 0.14, 0.60, 0.14)


def scarecrow(p, st, x, z, y0=0.0):
    B(p, st, "wood_dark", x, y0 + 1.30, z, 0.12, 2.60, 0.12)
    B(p, st, "wood_dark", x, y0 + 1.85, z, 1.40, 0.10, 0.10)
    B(p, st, "thatch", x, y0 + 1.50, z, 0.56, 0.74, 0.34)
    B(p, st, "cloth_team", x, y0 + 1.20, z, 0.60, 0.10, 0.38)
    B(p, st, "thatch", x, y0 + 2.36, z, 0.40, 0.40, 0.40)
    B(p, st, "thatch", x, y0 + 2.66, z, 0.66, 0.08, 0.66)
    B(p, st, "thatch", x, y0 + 2.78, z, 0.40, 0.18, 0.40)


def cart(p, st, x, z, y0=0.0):
    B(p, st, "wood", x, y0 + 0.62, z, 1.80, 0.44, 0.90)
    for s in (-1, 1):
        B(p, st, "wood_dark", x + s * 0.55, y0 + 0.30, z - 0.52, 0.10, 0.14, 1.05)
    # 立式车轮（触地）
    for s in (-1, 1):
        disc_vert(p, st, "wood_dark", x + s * 0.94, y0 + 0.38, z + 0.10, 0.36, 0.14, "x")
        B(p, st, "steel_dark", x + s * 0.94, y0 + 0.38, z + 0.10, 0.16, 0.10, 0.10)
    B(p, st, "wood_dark", x, y0 + 0.38, z + 0.10, 1.90, 0.10, 0.10)
    B(p, st, "wood_dark", x - 1.10, y0 + 0.52, z, 0.60, 0.10, 0.10)
    # 篷架：四根柱把布面撑在车斗上
    for sx in (-1, 1):
        for sz in (-1, 1):
            B(p, st, "wood_dark", x + sx * 0.82, y0 + 0.92, z + sz * 0.48,
              0.09, 0.62, 0.09)
    B(p, st, "cloth_team", x, y0 + 1.28, z, 1.86, 0.08, 1.30)
    for i in range(3):
        B(p, st, "cloth_team", x - 0.62 + i * 0.62, y0 + 1.14, z, 0.10, 0.30, 1.30)
    for i in range(3):
        B(p, st, "cloth_team", x, y0 + 1.30 + i * 0.05, z - 0.50 + i * 0.22,
          1.90, 0.06, 0.20)


# ================================================================== 城镇大厅
def b_townhall():
    p = []
    W, D = 9.0, 7.0
    FZ = -D / 2
    B(p, S_SITE, "wood_dark", 0, 0.04, 0, W + 1.6, 0.09, D + 1.6)
    for i, ins in enumerate((0.55, 0.32)):
        B(p, S_FOUND, "stone_dark", 0, 0.17 + i * 0.34, 0, W + ins, 0.34, D + ins)
    # 门前 5 级石阶
    stepped_steps(p, S_FOUND, "stone", 0, -4.62, 4.2, 5, 0.136, 0.34, sign=-1)
    # 台阶两侧矮墙 + TC1 压顶（低区第一眼识别）
    for sx in (-1, 1):
        B(p, S_FOUND, "stone", sx * 2.24, 0.30, -5.30, 0.22, 0.60, 1.55)
        B(p, S_TRIM, "cloth_team", sx * 2.24, 0.64, -5.30, 0.30, 0.12, 1.60)
        B(p, S_TRIM, "stone_dark", sx * 2.24, 0.72, -5.30, 0.26, 0.06, 1.64)

    # ---- 前凸门廊塔
    Y0 = 0.68
    BAYZ = -4.62
    BAYW = 4.60
    wall(p, S_WL, "stone", 0, (FZ + BAYZ) / 2, BAYW, abs(BAYZ - FZ), Y0, 2.30, 0.38,
         gaps=[("-z", -1.20, 1.20, Y0, 2.30)])
    wall(p, S_WM, "stone", 0, (FZ + BAYZ) / 2, BAYW, abs(BAYZ - FZ), 2.30, 3.55, 0.38,
         gaps=[("-z", -1.20, 1.20, 2.30, 3.12)])
    wall(p, S_WH, "stone", 0, (FZ + BAYZ) / 2, BAYW, abs(BAYZ - FZ), 3.55, 4.42, 0.38)
    quoins(p, S_WM, "stone_dark", 0, (FZ + BAYZ) / 2, BAYW, abs(BAYZ - FZ), Y0, 4.42, 0.60, 0.06)
    B(p, S_TRIM, "stone_dark", 0, 3.34, BAYZ - 0.06, 2.70, 0.24, 0.34)
    B(p, S_TRIM, "wood_dark", -1.28, 1.96, BAYZ - 0.06, 0.22, 2.46, 0.32)
    B(p, S_TRIM, "wood_dark", 1.28, 1.96, BAYZ - 0.06, 0.22, 2.46, 0.32)
    B(p, S_TRIM, "wood", 0, 1.94, BAYZ - 0.04, 2.38, 2.36, 0.16)
    for xx in (-0.60, 0.60):
        B(p, S_TRIM, "steel_dark", xx, 1.94, BAYZ - 0.15, 1.12, 2.12, 0.05)
        B(p, S_TRIM, "gold", xx, 1.66, BAYZ - 0.19, 0.09, 0.09, 0.09)
    # 门框内嵌 TC1 条 + 门楣横匾
    for xx in (-1.09, 1.09):
        plate(p, S_TRIM, "cloth_team", xx, 2.02, BAYZ - 0.06, 0.10, 2.30, "z", BAYZ - 0.06, -1, TC_THICK)
    B(p, S_TRIM, "cloth_team", 0, 3.20, BAYZ - 0.28, 2.60, 0.42, 0.05)
    _emblem(p, S_TRIM, 0, 3.20, BAYZ - 0.31, 1.30, "z", -1)

    # 门廊二层凸窗
    wall(p, S_WH, "plaster", 0, (FZ + BAYZ) / 2 - 0.10, BAYW + 0.30, abs(BAYZ - FZ) + 0.20,
         4.84, 6.30, 0.32, gaps=[("-z", -1.55, 0.10, 5.45, 6.25)])
    for zz in (-2.10, -0.30):
        for xx in (-2.46, 2.46):
            B(p, S_WH, "wood_dark", xx, 5.57, zz, 0.18, 1.46, 0.13)
    B(p, S_BEAM, "wood_dark", 0, 5.06, BAYZ - 0.16, BAYW + 0.30, 0.16, 0.14)
    B(p, S_BEAM, "wood_dark", 0, 6.24, BAYZ - 0.16, BAYW + 0.30, 0.16, 0.14)
    window_unit(p, S_TRIM, -1.05, 5.86, BAYZ - 0.20, 1.10, 0.86, "-z", team_pelmet=True)
    window_unit(p, S_TRIM, 1.05, 5.86, BAYZ - 0.20, 1.10, 0.86, "-z", team_pelmet=True)
    B(p, S_TRIM, "wood_dark", 0, 7.10, BAYZ - 0.22, 3.20, 0.86, 0.14)
    B(p, S_TRIM, "window", 0, 7.10, BAYZ - 0.30, 2.96, 0.68, 0.06)
    B(p, S_TRIM, "gold", 0, 7.66, BAYZ - 0.20, BAYW + 0.34, 0.06, 0.05)
    # 门廊塔凸窗上沿 TC1
    B(p, S_TRIM, "cloth_team", 0, 6.42, BAYZ - 0.34, 1.90, 0.10, 0.05)

    # ---- 一层石墙
    wall(p, S_WL, "stone", 0, 0, W, D, Y0, 2.30, 0.40,
         gaps=[("-z", -1.25, 1.25, 0.0, 4.20)])
    wall(p, S_WM, "stone", 0, 0, W, D, 2.30, 3.55, 0.40,
         gaps=[("-z", -1.25, 1.25, 0.0, 4.20),
               ("-z", -3.55, -2.45, 2.42, 3.30), ("-z", 2.45, 3.55, 2.42, 3.30),
               ("-x", -1.75, -0.65, 2.42, 3.30), ("-x", 0.65, 1.75, 2.42, 3.30),
               ("+x", -1.75, -0.65, 2.42, 3.30), ("+x", 0.65, 1.75, 2.42, 3.30),
               ("+z", -1.55, -0.45, 2.42, 3.30), ("+z", 0.45, 1.55, 2.42, 3.30)])
    wall(p, S_WH, "stone", 0, 0, W, D, 3.55, 4.42, 0.40)
    quoins(p, S_WM, "stone_dark", 0, 0, W, D, Y0, 4.42)
    window_unit(p, S_TRIM, -3.00, 2.86, FZ - 0.04, 1.00, 0.86, "-z", team_pelmet=True)
    window_unit(p, S_TRIM, 3.00, 2.86, FZ - 0.04, 1.00, 0.86, "-z", team_pelmet=True)
    for zz in (-1.20, 1.20):
        window_unit(p, S_TRIM, -W / 2 + 0.04, 2.86, zz, 1.00, 0.86, "-x", team_pelmet=True)
        window_unit(p, S_TRIM, W / 2 - 0.04, 2.86, zz, 1.00, 0.86, "+x", team_pelmet=True)
    for xx in (-1.0, 1.0):
        window_unit(p, S_TRIM, xx, 2.86, D / 2 - 0.04, 1.00, 0.86, "+z", team_pelmet=True)

    # ---- 腰线 + 出挑楼板
    B(p, S_BEAM, "stone_dark", 0, 4.48, 0, W + 0.30, 0.20, D + 0.30)
    for i in range(9):
        xx = -3.6 + i * 0.9
        B(p, S_BEAM, "wood_dark", xx, 4.62, FZ - 0.18, 0.16, 0.22, 0.55)
        B(p, S_BEAM, "wood_dark", xx, 4.62, D / 2 + 0.18, 0.16, 0.22, 0.55)
    B(p, S_BEAM, "wood_dark", 0, 4.72, 0, W + 0.72, 0.22, D + 0.72)
    # 二层腰线断续 TC1 饰条（12 段 × 0.7，贴石腰带外侧）
    seg12 = [(-3.55, -2.85), (-2.35, -1.65), (-1.15, -0.45), (0.45, 1.15),
             (1.65, 2.35), (2.85, 3.55)]
    for (a, b) in seg12:
        B(p, S_TRIM, "cloth_team", (a + b) / 2, 4.48, FZ - 0.19, b - a, 0.20, 0.05)
        B(p, S_TRIM, "cloth_team", (a + b) / 2, 4.48, D / 2 + 0.19, b - a, 0.20, 0.05)
    for (a, b) in ((-1.85, -1.15), (-0.35, 0.35), (1.15, 1.85)):
        B(p, S_TRIM, "cloth_team", -W / 2 - 0.19, 4.48, (a + b) / 2, 0.05, 0.20, b - a)
        B(p, S_TRIM, "cloth_team", W / 2 + 0.19, 4.48, (a + b) / 2, 0.05, 0.20, b - a)

    # ---- 二层（出挑半木构）
    W2, D2 = W + 0.60, D + 0.60
    Y2 = 4.84
    wall(p, S_WH, "plaster", 0, 0, W2, D2, Y2, 6.30, 0.34,
         gaps=[("-z", -3.30, -2.30, 5.55, 6.35), ("-z", 2.30, 3.30, 5.55, 6.35),
               ("-x", -1.30, -0.30, 5.55, 6.35), ("+x", -1.30, -0.30, 5.55, 6.35)])
    wall(p, S_WT, "plaster", 0, 0, W2, D2, 6.30, 7.86, 0.34,
         gaps=[("-z", -1.30, 1.30, 6.62, 7.60)])
    for xx in (-4.35, -2.85, -1.35, 1.35, 2.85, 4.35):
        B(p, S_WH, "wood_dark", xx, 5.57, -D2 / 2 - 0.04, 0.19, 1.46, 0.13)
        B(p, S_WH, "wood_dark", xx, 5.57, D2 / 2 + 0.04, 0.19, 1.46, 0.13)
    for zz in (-2.55, -0.95, 0.95, 2.55):
        B(p, S_WH, "wood_dark", -W2 / 2 - 0.04, 5.57, zz, 0.13, 1.46, 0.19)
        B(p, S_WH, "wood_dark", W2 / 2 + 0.04, 5.57, zz, 0.13, 1.46, 0.19)
    for yy in (5.06, 6.24):
        B(p, S_BEAM, "wood_dark", 0, yy, -D2 / 2 - 0.04, W2, 0.16, 0.14)
        B(p, S_BEAM, "wood_dark", 0, yy, D2 / 2 + 0.04, W2, 0.16, 0.14)
        B(p, S_BEAM, "wood_dark", -W2 / 2 - 0.04, yy, 0, 0.14, 0.16, D2)
        B(p, S_BEAM, "wood_dark", W2 / 2 + 0.04, yy, 0, 0.14, 0.16, D2)
    brace_xy(p, S_WH, "wood_dark", -1.35, 5.14, -2.85, 6.16, -D2 / 2 - 0.04, 0.115, 4)
    brace_xy(p, S_WH, "wood_dark", 1.35, 5.14, 2.85, 6.16, -D2 / 2 - 0.04, 0.115, 4)
    brace_xy(p, S_WH, "wood_dark", 2.85, 5.14, 1.35, 6.16, -D2 / 2 - 0.04, 0.115, 4)
    window_unit(p, S_TRIM, -2.80, 5.95, -D2 / 2 - 0.05, 1.00, 0.80, "-z")
    window_unit(p, S_TRIM, 2.80, 5.95, -D2 / 2 - 0.05, 1.00, 0.80, "-z")
    for zz in (0.80, -1.60):
        window_unit(p, S_TRIM, -W2 / 2 - 0.05, 5.95, zz, 0.86, 0.80, "-x")
        window_unit(p, S_TRIM, W2 / 2 + 0.05, 5.95, zz, 0.86, 0.80, "+x")
    B(p, S_TRIM, "wood_dark", 0, 7.10, -D2 / 2 - 0.06, 2.00, 0.86, 0.14)
    B(p, S_TRIM, "window", 0, 7.10, -D2 / 2 - 0.14, 1.76, 0.68, 0.06)
    B(p, S_TRIM, "wood_dark", 0, 7.10, -D2 / 2 - 0.16, 0.07, 0.68, 0.05)
    # 二层檐下厚饰带（阵营色，结构性的"制服"）
    B(p, S_TRIM, "cloth_team", 0, 7.66, -D2 / 2 - 0.19, W2, 0.44, 0.05)
    B(p, S_TRIM, "cloth_team", 0, 7.66, D2 / 2 + 0.19, W2, 0.44, 0.05)
    B(p, S_TRIM, "cloth_team", -W2 / 2 - 0.19, 7.66, 0, 0.05, 0.44, D2)
    B(p, S_TRIM, "cloth_team", W2 / 2 + 0.19, 7.66, 0, 0.05, 0.44, D2)
    B(p, S_TRIM, "gold", 0, 7.66, -D2 / 2 - 0.09, W2 * 0.98, 0.06, 0.05)

    # ---- 主屋顶
    RY = 7.94
    # 封檐板（阵营色，沿屋面四边通长）
    FY0, FX0 = W2 / 2 + 0.46, D2 / 2 + 0.46
    B(p, S_TRIM, "cloth_team", 0, RY - 0.02, -FX0, FY0 * 2, 0.34, 0.07)
    B(p, S_TRIM, "cloth_team", 0, RY - 0.02, FX0, FY0 * 2, 0.34, 0.07)
    B(p, S_TRIM, "cloth_team", -FY0, RY - 0.02, 0, 0.07, 0.34, FX0 * 2)
    B(p, S_TRIM, "cloth_team", FY0, RY - 0.02, 0, 0.07, 0.34, FX0 * 2)
    roof_gable(p, S_RL, S_RH, "shingle", 0, 0, W2, D2, RY, steps=10, rise=3.55,
               over=0.46, ridge="x", split=0.5)
    gz = (FZ + BAYZ) / 2 - 0.55
    roof_gable(p, S_RL, S_RH, "shingle", 0, gz, 2.5, 5.30, RY, steps=8, rise=3.10,
               over=0.30, ridge="z", split=0.5)
    for w, dy in ((5.30, 0.00), (4.30, 0.52), (3.20, 1.04), (2.10, 1.56), (1.00, 2.08)):
        B(p, S_WT, "plaster", 0, RY + dy + 0.26, gz - 1.55, w, 0.52, 0.22)
    B(p, S_BEAM, "wood_dark", 0, RY + 0.06, gz - 1.66, 5.70, 0.20, 0.16)
    for xx in (-2.55, 2.55):
        B(p, S_BEAM, "wood_dark", xx, RY + 1.30, gz - 1.60, 0.18, 2.60, 0.16)
    # 交叉山墙横带 + TC2 徽记
    B(p, S_TRIM, "cloth_team", 0, RY + 0.52, gz - 1.70, 3.20, 0.14, 0.05)
    _emblem(p, S_TRIM, 0, RY + 1.44, gz - 1.76, 0.92, "z", -1)
    for sx in (-1, 1):
        B(p, S_WT, "plaster", sx * (W2 / 2 + 0.06), 8.66, 0.55, 0.18, 1.40, 2.30)

    # ---- 主脊钟楼
    TY = RY + 3.55
    B(p, S_TRIM, "stone_dark", 0, TY + 0.10, 0, 2.05, 0.20, 2.05)
    for sx in (-1, 1):
        for sz in (-1, 1):
            B(p, S_TRIM, "wood", sx * 0.80, TY + 1.10, sz * 0.80, 0.20, 1.80, 0.20)
            # 钟楼四角立柱箍（4 处 × 0.16）
            B(p, S_TRIM, "cloth_team", sx * 0.80, TY + 0.62, sz * 0.80, 0.26, 0.16, 0.26)
    # 下槛压在石板上（原来悬空 7 cm）
    B(p, S_TRIM, "wood_dark", 0, TY + 0.27, 0, 1.90, 0.14, 1.90)
    B(p, S_TRIM, "wood_dark", 0, TY + 1.94, 0, 2.10, 0.18, 2.10)
    # 百叶横档夹在立柱之间（原来浮在柱子外侧 6 cm），两端顶到柱内侧面
    for sz in (-1, 1):
        for i in range(4):
            B(p, S_TRIM, "wood_dark", 0, TY + 0.52 + i * 0.30, sz * 0.70,
              1.40, 0.10, 0.10)
    for sx in (-1, 1):
        for i in range(4):
            B(p, S_TRIM, "wood_dark", sx * 0.70, TY + 0.52 + i * 0.30, 0,
              0.10, 0.10, 1.40)
    # 钟的吊梁：从上槛挂下来，钟不再悬在半空
    B(p, S_TRIM, "wood_dark", 0, TY + 1.62, 0, 0.10, 0.54, 0.10)
    B(p, S_TRIM, "steel_dark", 0, TY + 1.84, 0, 0.18, 0.06, 0.18)
    B(p, S_TRIM, "gold", 0, TY + 1.32, 0, 0.30, 0.40, 0.30)
    roof_pyramid(p, S_TRIM, "shingle", 0, 0, 1.90, TY + 2.03, steps=3, rise=1.05,
                 over=0.30, finial=None)
    MB = TY + 3.04
    B(p, S_FLAG, "wood_dark", 0, MB + 1.43, 0, 0.10, 2.86, 0.10)
    B(p, S_TRIM, "gold", 0, MB + 2.90, 0, 0.17, 0.17, 0.17)
    flag_a(p, S_FLAG, 0, MB + 2.80, 0.02, w=0.55, h=1.45, axis="x", sign=-1, pole=False)

    _tag_duty(p, lambda q: (q["box"][1] > 11.40 and abs(q["box"][0]) < 1.45 and abs(q["box"][2]) < 1.45)
              or (q["box"][1] < 5.3 and abs(q["box"][0]) < 2.42 and q["box"][2] < -4.2))
    chimney(p, S_WT, "stone", -3.30, 2.05, 0.68, 10.60, 1.05, team_hoops=(9.3, 10.2))
    # 正门布篷（低区大面积识别）
    awning(p, S_TRIM, 0, 3.18, BAYZ - 0.30, 2.95, 1.05, sign=-1, drop=0.42, posts=False)
    # 门廊双垂幅（大面积、跨低中高三个带）
    for xx in (-1.78, 1.78):
        banner_v(p, S_FLAG, xx, 6.65, BAYZ - 0.30, w=0.78, h=2.95, facing="-z")
    # 二层角部壁柱（TC1，纵向节奏）
    for sx in (-1, 1):
        for zz in (-2.85, 2.85):
            B(p, S_TRIM, "cloth_team", sx * (W2 / 2 + 0.21), 5.58, zz, 0.05, 1.42, 0.22)

    # 东侧小门廊（第二处附加体量，带小雨檐）
    PX, PZ = 5.15, -1.10
    B(p, S_FOUND, "stone_dark", PX, 0.25, PZ, 1.40, 0.50, 2.40)
    B(p, S_WM, "stone", PX, 1.35, PZ, 1.24, 1.70, 2.20)
    B(p, S_TRIM, "wood_dark", PX, 2.28, PZ, 1.60, 0.16, 2.50)
    roof_mono(p, S_RL, S_RH, "shingle", PX, PZ, 1.40, 2.40, 2.36, steps=2, rise=0.32,
              over=0.18, axis="x", direction=1, split=0.5, thick=0.18, shingle=False)
    B(p, S_TRIM, "cloth_team", PX + 0.68, 2.18, PZ, 0.05, 0.18, 2.30)
    # ---- 场院细节：火盆 / 公告板 / 雨落管
    for xx in (-2.75, 2.75):
        brazier(p, S_TRIM, xx, -5.55)
    notice_board(p, S_TRIM, 6.35, -4.60)
    for sx in (-1, 1):
        for sz in (-1, 1):
            x = sx * (W / 2 + 0.10)
            z = sz * (D / 2 + 0.10)
            B(p, S_TRIM, "steel_dark", x, 4.30, z, 0.12, 7.20, 0.12)
            B(p, S_TRIM, "steel_dark", x - sx * 0.14, 7.86, z, 0.30, 0.12, 0.12)
            B(p, S_TRIM, "steel_dark", x, 0.80, z - sz * 0.16, 0.12, 0.12, 0.34)

    scaffold(p, 0, 0, W2, D2, 8.6, levels=4)
    rubble(p, 0, 0, W + 1, D + 1, 24)
    return p, {"name": "townhall", "cn": "城镇大厅", "roof": "gable_cross",
               "volumes": [(-2.4, 2.4, -4.9, -3.3), (4.4, 5.9, -2.4, 0.2)],
               "team_zones": ["门廊台阶矮墙压顶", "门框内嵌条+门楣横匾", "二层腰线 12 段",
                              "凸窗上沿", "交叉山墙横带", "钟楼四角柱箍", "主脊旗+门廊双旗",
                              "檐下饰带", "窗楣 TC1"]}


# ================================================================== 兵营
def b_barracks():
    p = []
    W, D = 9.0, 6.5
    FZ = -D / 2
    B(p, S_SITE, "wood_dark", 0, 0.04, 0, W + 1.8, 0.09, D + 1.8)
    for i, ins in enumerate((0.62, 0.34)):
        B(p, S_FOUND, "stone_dark", 0, 0.18 + i * 0.34, 0, W + ins, 0.36, D + ins)

    Y0 = 0.60
    # 下段石墙 / 上段石墙
    wall(p, S_WL, "stone_dark", 0, 0, W, D, Y0, 2.10, 0.36,
         gaps=[("-z", -1.25, 1.25, Y0, 2.10)])
    wall(p, S_WM, "stone", 0, 0, W, D, 2.10, 4.70, 0.34,
         gaps=[("-z", -1.25, 1.25, 2.10, 3.30),
               ("-z", -3.55, -2.55, 3.30, 4.20), ("-z", 2.55, 3.55, 3.30, 4.20),
               ("-x", -1.55, -0.55, 2.60, 3.50), ("+x", -1.55, -0.55, 2.60, 3.50)])
    wall(p, S_WH, "stone", 0, 0, W, D, 4.70, 7.20, 0.34,
         gaps=[("-x", -1.55, -0.55, 5.30, 6.20), ("+x", -1.55, -0.55, 5.30, 6.20),
               ("+z", -1.20, -0.20, 5.30, 6.20)])
    quoins(p, S_WM, "stone_dark", 0, 0, W, D, Y0, 7.20, 0.72, 0.08)
    # 箭窗（内凹，读作军事建筑）
    for xx, zz, side in ((-3.55, FZ - 0.02, "z"), (3.55, FZ - 0.02, "z"),
                         (-1.05, -W / 2 - 0.02, "x"), (1.05, W / 2 + 0.02, "x")):
        if side == "z":
            B(p, S_TRIM, "stone_dark", xx, 5.75, zz, 0.34, 1.10, 0.10)
            B(p, S_TRIM, "window", xx, 5.75, zz - 0.06, 0.16, 0.86, 0.04)
            B(p, S_TRIM, "cloth_team", xx, 6.35, zz - 0.09, 0.44, 0.10, 0.04)
        else:
            B(p, S_TRIM, "stone_dark", zz, 5.75, 0.0, 0.10, 1.10, 0.34)
            B(p, S_TRIM, "window", zz - 0.06, 5.75, 0.0, 0.04, 0.86, 0.16)
            B(p, S_TRIM, "cloth_team", zz - 0.09, 6.35, 0.0, 0.04, 0.10, 0.44)

    # ---- 营门：3 级石阶 + 闸门槽 + 门楣横匾 + 双旗
    stepped_steps(p, S_FOUND, "stone", 0, FZ, 3.40, 3, 0.18, 0.34, sign=-1)
    for xx in (-1.30, 1.30):
        B(p, S_TRIM, "stone_dark", xx, 2.10, FZ - 0.10, 0.30, 2.70, 0.34)
        B(p, S_TRIM, "cloth_team", xx, 2.40, FZ - 0.30, 0.50, 0.50, 0.05)
        B(p, S_TRIM, "steel_dark", xx - 0.20, 1.90, FZ - 0.28, 0.12, 2.50, 0.10)
        B(p, S_TRIM, "steel_dark", xx + 0.20, 1.90, FZ - 0.28, 0.12, 2.50, 0.10)
    B(p, S_TRIM, "stone_dark", 0, 3.45, FZ - 0.08, 3.20, 0.36, 0.36)
    B(p, S_TRIM, "cloth_team", 0, 3.72, FZ - 0.22, 2.60, 0.42, 0.05)
    _emblem(p, S_TRIM, 0, 3.72, FZ - 0.25, 1.28, "z", -1)
    awning(p, S_TRIM, 0, 3.06, FZ - 0.30, 3.30, 1.05, sign=-1, drop=0.40, posts=False)
    # 木门 + 铁箍
    B(p, S_TRIM, "wood_dark", 0, 1.62, FZ - 0.05, 2.32, 3.00, 0.14)
    for yy in (0.55, 1.20, 1.90, 2.55):
        B(p, S_TRIM, "steel_dark", 0, yy, FZ - 0.14, 2.36, 0.10, 0.05)
    B(p, S_TRIM, "steel_dark", 0, 1.60, FZ - 0.15, 0.08, 3.00, 0.05)
    for xx in (-0.62, 0.62):
        B(p, S_TRIM, "steel", xx, 1.62, FZ - 0.17, 0.10, 0.10, 0.04)
    for xx in (-1.55, 1.55):
        B(p, S_FLAG, "wood_dark", xx, 1.85, FZ - 1.30, 0.09, 3.70, 0.09)
        B(p, S_FLAG, "gold", xx, 3.74, FZ - 1.30, 0.13, 0.13, 0.13)
        flag_a(p, S_FLAG, xx, 3.52, FZ - 1.34, w=0.55, h=1.45, axis="x", pole=False)

    # ---- 平屋顶 + 女儿墙 + 雉堞
    RY = 7.20
    B(p, S_RL, "stone_dark", 0, RY - 0.11, 0, W - 0.50, 0.22, D - 0.50)
    # 内院下沉 0.35（四周走道 + 中央下凹平台）
    B(p, S_RL, "stone", 0, RY - 0.28, 0, W - 2.90, 0.12, D - 2.30)
    for xx in (-1.65, 1.65):
        B(p, S_TRIM, "wood_dark", xx, RY - 0.18, 1.35, 0.90, 0.10, 0.90)
        for i in range(4):
            B(p, S_TRIM, "wood", xx, RY - 0.45 + i * 0.24, 1.60 - i * 0.12, 0.72, 0.07, 0.08)
    for yy in (7.05, 7.55):
        B(p, S_WT, "stone_dark", 0, yy, FZ - 0.02, W + 0.03, 0.10, 0.30)
    # 托石
    for i in range(10):
        xx = -4.05 + i * 0.90
        for zz in (FZ + 0.02, D / 2 - 0.02):
            B(p, S_BEAM, "stone_dark", xx, 6.98, zz, 0.24, 0.20, 0.34)
    for i in range(7):
        zz = -2.70 + i * 0.90
        for xx in (-W / 2 + 0.02, W / 2 - 0.02):
            B(p, S_BEAM, "stone_dark", xx, 6.98, zz, 0.34, 0.20, 0.24)
    merlons = battlement(p, S_WT, 0, 0, W - 0.50, D - 0.50, RY, ph=0.95, pt=0.34,
                         mw=0.50, mh=0.55, spacing=0.92)
    # 女儿墙外沿连续 TC1 檐带（俯视角最稳的一条）
    pw, pd = W - 0.50, D - 0.50
    B(p, S_TRIM, "cloth_team", 0, RY + 0.76, -pd / 2 - 0.008, pw, 0.30, 0.03)
    B(p, S_TRIM, "cloth_team", 0, RY + 0.76, pd / 2 + 0.008, pw, 0.30, 0.03)
    B(p, S_TRIM, "cloth_team", -pw / 2 - 0.008, RY + 0.76, 0, 0.03, 0.30, pd)
    B(p, S_TRIM, "cloth_team", pw / 2 + 0.008, RY + 0.76, 0, 0.03, 0.30, pd)

    # ---- 主塔（前右角，阶梯八角）
    TX, TZ = 4.55, -3.15
    oct_column(p, S_WM, "stone", TX, TZ, 0.98, 0.0, 10.50, 1.28,
               team_ring=(2.60, 5.20, 8.10))
    B(p, S_TRIM, "cloth_team", TX, 6.55, TZ - 1.02, 2.10, 0.22, 0.05)
    B(p, S_TRIM, "cloth_team", TX, 6.55, TZ + 1.02, 2.10, 0.22, 0.05)
    B(p, S_WT, "stone_dark", TX, 10.62, TZ, 2.20, 0.24, 2.20)
    for i in range(4):
        a = math.pi * 0.5 * i + math.pi * 0.25
        dx, dz = math.cos(a) * 1.00, math.sin(a) * 1.00
        B(p, S_TRIM, "stone_dark", TX + dx, 9.55, TZ + dz, 0.36, 0.90, 0.36)
        B(p, S_WT, "window", TX + dx * 1.10, 9.55, TZ + dz * 1.10, 0.16, 0.70, 0.16)
    oct_slab(p, S_WT, "stone_dark", TX, TZ, 1.15, 10.72, 0.32)
    for i in range(4):
        r = 1.05 * (1 - i * 0.19)
        oct_slab(p, S_RH, "shingle", TX, TZ, r, 11.04 + i * 0.30, 0.32)
    B(p, S_RH, "gold", TX, 12.34, TZ, 0.14, 0.28, 0.14)
    B(p, S_FLAG, "wood_dark", TX, 12.28, TZ, 0.07, 0.70, 0.07)
    flag_a(p, S_FLAG, TX, 12.40, TZ + 0.02, w=0.50, h=1.10, axis="x", pole=False)
    # 副角楼 ×2（后两角）
    for TX2, TZ2 in ((-4.55, 3.15), (4.55, 3.15)):
        oct_column(p, S_WM, "stone", TX2, TZ2, 0.78, 0.0, 9.40, 1.18,
                   team_ring=(2.80, 5.40, 8.00))
        B(p, S_WT, "stone_dark", TX2, 9.50, TZ2, 1.80, 0.22, 1.80)
        oct_slab(p, S_WT, "stone_dark", TX2, TZ2, 0.92, 9.56, 0.26)
        for i in range(3):
            oct_slab(p, S_RH, "shingle", TX2, TZ2, 0.88 * (1 - i * 0.22),
                     9.82 + i * 0.22, 0.24)
        B(p, S_RH, "gold", TX2, 10.72, TZ2, 0.12, 0.24, 0.12)

    # ---- 东侧披屋（厨房/储藏，带烟囱）
    AX, AZ = 6.55, 1.15
    B(p, S_FOUND, "stone_dark", AX, 0.20, AZ, 4.10, 0.40, 4.40)
    wall(p, S_WL, "stone", AX, AZ, 3.60, 4.20, 0.40, 3.20, 0.28,
         gaps=[("-z", -0.60, 0.60, 0.40, 2.50), ("+x", -1.10, -0.20, 1.40, 2.30)])
    wall(p, S_WM, "wood", AX, AZ, 3.60, 4.20, 3.20, 5.40, 0.26)
    roof_mono(p, S_RL, S_RH, "shingle", AX, AZ, 3.60, 4.20, 5.40, steps=4,
              rise=0.90, over=0.30, axis="x", direction=1, split=0.5,
              thick=0.24, fill="both", fill_mat="wood")
    chimney(p, S_TRIM, "stone", 7.85, 2.55, 0.40, 6.90, 0.72, team_hoops=(6.2,))
    # 披屋檐口条（阵营色）
    B(p, S_TRIM, "cloth_team", AX, 5.62, AZ, 3.80, 0.10, 0.06)
    B(p, S_TRIM, "cloth_team", AX + 1.94, 5.66, AZ, 0.06, 0.10, 4.30)
    # 西侧外挂楼梯（与墙留 9 mm 结构缝）
    sx = -W / 2 - 0.95
    for i in range(12):
        B(p, S_TRIM, "wood_dark", sx, 0.30 + i * 0.60, 3.15 - i * 0.36,
          0.95, 0.60, 0.36)
        B(p, S_TRIM, "cloth_team", sx - 0.36, 0.30 + i * 0.60, 3.15 - i * 0.36,
          0.05, 0.10, 0.36)
    for i in range(6):
        yy = 0.60 + i * 1.10
        B(p, S_TRIM, "wood", sx - 0.48, yy + 0.45, 2.95 - i * 0.72, 0.10, 1.10, 0.10)
    B(p, S_TRIM, "wood", sx - 0.48, 6.70, 0.55, 0.10, 0.10, 3.90)
    B(p, S_TRIM, "wood_dark", sx, 7.28, -0.55, 1.10, 0.10, 0.90)

    # ---- 前院 L 形木栅（14 m + 9 m，留 4 m 缺口）
    FY = FZ - 4.60
    for xx in (-7.0, -5.25, -3.5, -2.6, 2.6, 3.5, 5.25, 7.0):
        B(p, S_TRIM, "wood_dark", xx, 0.78, FY, 0.22, 1.56, 0.22)
        B(p, S_TRIM, "wood_dark", xx, 1.66, FY, 0.28, 0.16, 0.28)
        B(p, S_TRIM, "cloth_team", xx, 1.80, FY, 0.22, 0.14, 0.22)
    for yy in (0.45, 1.18):
        B(p, S_TRIM, "wood", -5.05, yy, FY, 3.90, 0.12, 0.10)
        B(p, S_TRIM, "wood", 5.05, yy, FY, 3.90, 0.12, 0.10)
    for zz in (-3.25, -1.45, 0.35):
        B(p, S_TRIM, "wood_dark", -7.0, 0.78, zz, 0.26, 1.56, 0.26)
        B(p, S_TRIM, "cloth_team", -7.0, 1.62, zz, 0.30, 0.14, 0.30)
    for yy in (0.45, 1.18):
        B(p, S_TRIM, "wood", -7.0, yy, -1.45, 0.10, 0.12, 3.80)

    # ---- 训练场：靶人 ×3 / 盾架 / 兵器架 ×2 / 火盆 / 草垛
    for i, (px, pz) in enumerate(((5.9, -5.0), (7.4, -5.9), (6.6, -7.3))):
        pell(p, S_TRIM, px, pz)
    # 盾架 3 面
    RX, RZ = 7.2, -2.8
    for zz in (-0.60, 0.60):
        B(p, S_TRIM, "wood_dark", RX, 0.95, RZ + zz, 0.18, 1.90, 0.18)
    for yy in (0.62, 1.55):
        B(p, S_TRIM, "wood", RX, yy, RZ, 0.14, 0.14, 1.50)
    for zz in (-0.48, 0.0, 0.48):
        for i, (dy, k) in enumerate(((0.00, 1.0), (0.22, 0.82), (0.44, 0.58), (0.66, 0.32))):
            B(p, S_TRIM, "steel", RX - 0.12, 1.75 - 0.90 * (dy + 0.10), RZ + zz,
              0.05, 0.18, 0.52 * k)
            B(p, S_TRIM, "cloth_team", RX - 0.16, 1.75 - 0.90 * (dy + 0.10), RZ + zz,
              0.03, 0.14, 0.46 * k)
        _emblem(p, S_TRIM, RX - 0.18, 1.20, RZ + zz, 0.22, "x", -1)
    weapon_rack(p, S_TRIM, -6.2, -5.6)
    weapon_rack(p, S_TRIM, -6.2, -2.9)
    brazier(p, S_TRIM, -3.55, -6.4)
    brazier(p, S_TRIM, 3.55, -6.4)
    for hx, hz in ((8.0, -0.2), (-6.4, -7.2)):
        haystack(p, S_TRIM, hx, hz, r=0.72, h=1.05)
    # 草靶（箭靶）
    for tx, tz in ((8.2, -6.6),):
        B(p, S_TRIM, "wood_dark", tx, 0.80, tz, 0.18, 1.60, 0.18)
        B(p, S_TRIM, "thatch", tx, 1.55, tz, 1.10, 1.10, 0.22)
        B(p, S_TRIM, "cloth_team", tx - 0.13, 1.55, tz, 0.04, 0.90, 0.90)
        _emblem(p, S_TRIM, tx - 0.16, 1.55, tz, 0.36, "x", -1)

    scaffold(p, 0, 0, W, D, 8.2, levels=4)
    # 兵营的职责构件是"垛口天际线"：整条女儿墙 + 垛口 + 三座角楼的冠部，
    # 只有把它当一个整体量，剪影占比才有意义（单个数垛口是线，不是面）。
    _tag_duty(p, lambda q: q["box"][1] > 10.55)
    rubble(p, 0, 0, W + 1.2, D + 1.2, 26)
    return p, {"name": "barracks", "cn": "兵营", "merlons": merlons, "roof": "flat_crenel",
               "volumes": [(4.4, 8.5, -1.3, 3.3), (-5.6, -4.4, -1.4, 3.4),
                           (-1.9, 1.9, -5.6, -3.2), (3.5, 5.6, -4.2, -2.1)],
               "team_zones": ["垛口压顶 30 处", "女儿墙檐带", "营门双柱箍+门楣横匾",
                              "盾墙 6 面", "盾架 3 面", "靶人胸甲+靶心", "披屋檐口条",
                              "角楼柱箍", "兵器架绑带", "外挂楼梯踢面"]}


# ================================================================== 铁匠铺
def b_blacksmith():
    """铁匠铺 v5：11.0 m 的作坊，不是 14 m 的工厂。

    识别顺序 = 设计顺序：炉口橙光 → 炉罩收分 → 烟囱 → 铁砧。
    动作线（火 → 砧 → 水）沿正立面从左到右铺开，雨棚让开炉口 0.8 m。
    """
    p = []
    W, D = 7.6, 5.4
    FZ, BZ = -D / 2, D / 2
    EAVE, RIDGE = 5.6, 7.4
    Y0 = 0.50

    # ---------------- 场地 / 台基（勒脚外放 0.06，高 0.35）
    hs.box(p, S_SITE, "wood_dark", 0, 0.04, 0.3, W + 3.6, 0.09, D + 6.4, tile=1.4)
    hs.box(p, S_FOUND, "stone_dark", 0, 0.14, 0, W + 0.34, 0.28, D + 0.34, tile=1.2)
    hs.box(p, S_FOUND, "stone_dark", 0, 0.375, 0, W + 0.18, 0.35, D + 0.18, tile=1.2)
    hs.box(p, S_FOUND, "stone", 0, 0.545, 0, W - 0.05, 0.06, D - 0.05, tile=1.2)

    # ---------------- 墙体
    wall(p, S_WL, "stone", 0, 0, W, D, Y0, 2.40, 0.34,
         gaps=[("-z", 1.30, 2.50, Y0, 2.66), ("+x", -1.00, 0.20, 2.00, 3.00),
               ("+z", -0.20, 1.40, Y0, 2.30)])
    wall(p, S_WM, "stone", 0, 0, W, D, 2.40, 3.90, 0.34,
         gaps=[("+x", -1.00, 0.20, 2.00, 3.00), ("-z", 2.65, 3.35, 2.95, 3.55),
               ("+z", -0.20, 1.40, Y0, 2.30)])
    wall(p, S_WH, "plaster", 0, 0, W, D, 3.90, EAVE, 0.30)
    # 侧墙山尖（跟着单坡斜上去）
    # 山尖要"咬"进屋面 2 cm：留 2 cm 缝就会在侧视图上看见一道透光的天
    for sx in (-1, 1):
        _prism_x(p, S_WH, "stone",
                 [(FZ - 0.02, EAVE - 0.02), (BZ, EAVE - 0.02),
                  (BZ, RIDGE + 0.035), (FZ - 0.02, EAVE + 0.015)],
                 sx * W / 2 - 0.16, sx * W / 2 + 0.16)
    quoins(p, S_WM, "stone_dark", 0, 0, W, D, Y0, EAVE, 0.60)

    # ---------------- 正立面半木构（立柱 0.14，斜撑 45°，全部顶到梁）
    for x in (-3.34, -2.42, -1.50, -0.58, 0.34, 2.62, 3.34):
        hs.box(p, S_WH, "wood_dark", x, (3.90 + EAVE + 0.06) / 2, FZ - 0.19,
               0.14, EAVE - 3.90 + 0.06, 0.14, tile=0.9)
    hs.box(p, S_WH, "wood_dark", 0, 3.94, FZ - 0.19, W, 0.16, 0.18, tile=0.9)
    hs.box(p, S_WH, "wood_dark", 0, EAVE - 0.10, FZ - 0.19, W + 0.14, 0.20, 0.20, tile=0.9)
    for x in (-2.88, -1.96, -1.04):
        hs.bar(p, S_WH, "wood_dark", (x - 0.42, 3.98, FZ - 0.19),
               (x + 0.42, EAVE - 0.22, FZ - 0.19), 0.12, 0.12, up=(0, 0, 1), tile=0.9)

    # ---------------- 单坡屋面（檐口 5.6 → 脊 7.4）
    roof_h = _mono_roof(p, EAVE, RIDGE, W, D, FZ)

    # ---------------- 炉膛凸出体量 3.2 × 2.4 × 4.6，凸出 1.6
    fx, fz = -1.90, FZ - 0.80          # 体块中心：外脸 -4.30，内脸 -1.90
    bx0, bx1 = fx - 1.60, fx + 1.60
    mz = fz - 1.20                     # 外脸
    # 开口 1.60 × 1.15，下沿 0.95，内凹 0.60
    ox0, ox1 = fx - 0.80, fx + 0.80
    oy0, oy1 = 0.95, 2.10
    d_in = mz + 0.60
    # 体块拆成 5 块围出洞口（硬边，不用布尔）
    hs.box(p, S_WL, "stone", (bx0 + ox0) / 2, 2.30, fz, ox0 - bx0, 4.60, 2.40, tile=1.1)
    hs.box(p, S_WL, "stone", (ox1 + bx1) / 2, 2.30, fz, bx1 - ox1, 4.60, 2.40, tile=1.1)
    hs.box(p, S_WL, "stone", fx, oy0 / 2, fz, ox1 - ox0, oy0, 2.40, tile=1.1)
    hs.box(p, S_WM, "stone", fx, (oy1 + 4.60) / 2, fz, ox1 - ox0, 4.60 - oy1, 2.40, tile=1.1)
    hs.box(p, S_WL, "stone_dark", fx, 2.30, (d_in + fz + 1.20) / 2,
           ox1 - ox0, 4.60, (fz + 1.20) - d_in, tile=1.1)
    # 炭台 + 炉膛内壁 + 炉口橙光（唯一自发光点）
    hs.box(p, S_TRIM, "stone_dark", fx, oy0 - 0.09, mz - 0.22, 1.86, 0.18, 0.44, tile=1.0, role="duty")
    hs.box(p, S_TRIM, "ember", fx, oy0 + 0.02, d_in - 0.03, 1.44, 0.04, 0.10, tile=0.7, role="duty")
    hs.box(p, S_TRIM, "ember", fx, (oy0 + oy1) / 2 - 0.05, d_in - 0.05,
           1.40, (oy1 - oy0) * 0.72, 0.06, tile=0.7, role="duty")
    hs.box(p, S_TRIM, "steel_dark", fx, oy1 + 0.09, mz - 0.06, 1.92, 0.20, 0.16, tile=0.8, role="duty")
    # 炉口石框（硬边，见棱）
    for sx in (-1, 1):
        hs.box(p, S_WM, "stone_dark", fx + sx * 0.92, (oy0 + oy1) / 2, mz + 0.10,
               0.24, oy1 - oy0 + 0.20, 0.22, tile=1.0, role="duty")
    # 熏黑：炉口周围压暗（顶点色由 AO 负责，这里只把石材换成 stone_dark）

    # ---------------- 炉罩：3.2 收分到 1.4，高 1.8，4 级阶梯
    for i in range(4):
        t0, t1 = i / 4, (i + 1) / 4
        w0 = 3.20 - (3.20 - 1.40) * t0
        w1 = 3.20 - (3.20 - 1.40) * t1
        hs.frustum(p, S_WT, "stone_dark", fx, fz, (w0, 2.40 - 0.30 * i),
                   (w1, 2.40 - 0.30 * (i + 1)), 4.60 + 1.8 * t0, 4.60 + 1.8 * t1,
                   tile=1.1, role="duty")
    hs.box(p, S_TRIM, "cloth_team", fx, 6.44, fz - 0.92, 1.52, 0.10, 0.06, tile=1.0, role="team")

    # ---------------- 烟囱 1.40 → 1.15，顶 11.0
    ch_bot = 6.40
    hs.frustum(p, S_WT, "stone", fx, fz, 1.40, 1.15, ch_bot, 10.72, tile=1.2, role="duty")
    for y in (7.30, 9.00):
        hs.box(p, S_TRIM, "cloth_team", fx, y, fz, 1.44, 0.16, 1.44, tile=1.0, role="team")
        hs.box(p, S_TRIM, "steel_dark", fx, y + 0.14, fz, 1.46, 0.05, 1.46, tile=0.8, role="trim")
    # 烟帽：四面出挑 0.18 + 两块叠板
    hs.box(p, S_TRIM, "stone_dark", fx, 10.76, fz, 1.51, 0.12, 1.51, tile=1.0, role="duty")
    hs.box(p, S_TRIM, "stone_dark", fx, 10.86, fz, 1.32, 0.10, 1.32, tile=1.0, role="duty")
    hs.box(p, S_TRIM, "steel_dark", fx, 10.95, fz, 1.18, 0.08, 1.18, tile=0.8, role="duty")

    # ---------------- 正门（偏右）+ 两级石阶
    dx = 1.90
    hs.box(p, S_FOUND, "stone", dx, 0.29, FZ - 0.62, 1.72, 0.20, 0.86, tile=1.0)
    hs.box(p, S_FOUND, "stone", dx, 0.10, FZ - 1.02, 1.28, 0.20, 0.72, tile=1.0)
    for sx in (-1, 1):
        hs.box(p, S_WM, "wood_dark", dx + sx * 0.66, 1.55, FZ - 0.20, 0.14, 2.24, 0.20, tile=0.9)
    hs.box(p, S_WM, "wood_dark", dx, 2.60, FZ - 0.20, 1.52, 0.18, 0.22, tile=0.9)
    hs.box(p, S_TRIM, "cloth_team", dx, 2.72, FZ - 0.30, 1.56, 0.14, 0.05, tile=1.0, role="team")
    # 门扇（半开）+ 铁铰
    hs.box(p, S_TRIM, "wood", dx - 0.34, 1.52, FZ - 0.24, 0.90, 2.06, 0.09, tile=0.9)
    for hy in (1.02, 2.02):
        hs.box(p, S_TRIM, "steel_dark", dx - 0.34, hy, FZ - 0.30, 0.76, 0.08, 0.03, tile=0.7, role="bevel")
    # 招牌
    hs.box(p, S_TRIM, "wood_dark", dx, 3.42, FZ - 0.34, 1.72, 0.42, 0.06, tile=0.9)
    _emblem(p, S_TRIM, dx, 3.42, FZ - 0.38, 0.30, "z", -1)

    # ---------------- 木瓦小雨棚：出挑 2.0，两根 0.14 方柱落在石墩上
    cy0, cy1 = 3.30, 4.06
    for px2 in (dx - 0.95, dx + 0.95):
        hs.box(p, S_BEAM, "wood_dark", px2, 1.72, FZ - 1.92, 0.14, 2.36, 0.14, tile=0.9)
        hs.box(p, S_FOUND, "stone_dark", px2, 0.22, FZ - 1.92, 0.36, 0.44, 0.36, tile=1.0)
    hs.box(p, S_BEAM, "wood_dark", dx, 2.94, FZ - 1.92, 2.24, 0.14, 0.16, tile=0.9)
    _small_roof(p, dx, FZ + 0.10, FZ - 2.24, cy1, cy0, 2.44)
    hs.box(p, S_TRIM, "cloth_team", dx, cy0 - 0.07, FZ - 2.24, 2.48, 0.10, 0.05, tile=1.0, role="team")

    # ---------------- 工作区：火 → 砧 → 水
    _anvil(p, S_TRIM, -3.62, FZ - 1.34, duty=False)
    _anvil(p, S_TRIM, -0.62, FZ - 2.28, duty=False)
    _quench(p, S_TRIM, 0.86, FZ - 2.10)
    _grind(p, S_TRIM, 2.62, FZ - 2.72)
    # 煤堆：两级方堆，靠炉膛侧墙
    hs.box(p, S_TRIM, "stone_dark", bx0 - 0.62, 0.29, fz - 0.60, 1.10, 0.58, 1.36, tile=1.1)
    hs.box(p, S_TRIM, "stone_dark", bx0 - 0.62, 0.74, fz - 0.60, 0.82, 0.34, 1.02, tile=1.1)
    # 工具墙：两道横档 + 5 件工具（挂在炉膛左侧面）
    for yy in (1.55, 2.62):
        hs.box(p, S_TRIM, "wood_dark", bx0 - 0.05, yy, fz + 0.10, 0.08, 0.10, 2.00, tile=0.9)
    _tools(p, S_TRIM, bx0 - 0.10, fz + 0.10)

    # ---------------- 阵营色：只沿结构线
    hs.box(p, S_TRIM, "cloth_team", 0, EAVE - 0.02, FZ - 0.36, W + 0.24, 0.12, 0.05, tile=1.0, role="team")
    hs.box(p, S_TRIM, "cloth_team", 0, 3.90, FZ - 0.36, W + 0.18, 0.12, 0.05, tile=1.0, role="team")
    # 山墙挑旗
    # 山墙挑旗：只留插在墙体里的短杆，旗面挪到正脊那面（单独一片悬空布读作 bug）

    # 正脊小旗
    flag_b(p, S_FLAG, 3.10, RIDGE + 0.14, FZ + 0.30, w=0.28, ln=1.05, direction=1)

    scaffold(p, 0, 0, W, D, 7.0, levels=3)
    rubble(p, 0, 0, W + 2.4, D + 5.2, 22)
    return p, {"name": "blacksmith", "cn": "铁匠铺", "roof": "mono_pitch",
               "height": 11.0,
               "volumes": [(-3.60, -0.20, -4.40, -1.80), (0.90, 2.90, -4.30, -2.60),
                           (-3.90, -2.70, -4.20, -2.10)],
               "team_zones": ["炉罩下沿", "烟囱 2 道箍", "门楣", "雨棚边", "淬火桶 2 道箍", "山墙挑旗"]}
# ================================================================== 农场
def b_farm():
    p = []
    W, D = 8.0, 6.0
    FZ = -D / 2
    B(p, S_SITE, "wood_dark", 0, 0.04, 0, W + 1.4, 0.09, D + 1.4)
    for i, ins in enumerate((0.50, 0.26)):
        B(p, S_FOUND, "stone_dark", 0, 0.14 + i * 0.28, 0, W + ins, 0.28, D + ins)
    Y0 = 0.52
    wall(p, S_WL, "stone_dark", 0, 0, W, D, Y0, 1.30, 0.30,
         gaps=[("-z", -1.70, 1.70, Y0, 1.30)])
    wall(p, S_WM, "wood", 0, 0, W, D, 1.30, 3.10, 0.26,
         gaps=[("-z", -1.70, 1.70, 1.30, 3.05),
               ("-z", -3.55, -2.55, 1.85, 2.70), ("-z", 2.55, 3.55, 1.85, 2.70),
               ("+x", -1.30, -0.30, 1.85, 2.70), ("-x", -1.30, -0.30, 1.85, 2.70)])
    wall(p, S_WH, "wood", 0, 0, W, D, 3.10, 4.60, 0.26,
         gaps=[("-z", -3.55, -2.55, 3.20, 4.05), ("-z", 2.55, 3.55, 3.20, 4.05)])
    for i in range(15):
        xx = -W / 2 + 0.30 + i * 0.54
        B(p, S_WM, "wood_dark", xx, 2.20, FZ - 0.04, 0.07, 1.80, 0.08)
        B(p, S_WM, "wood_dark", xx, 2.20, D / 2 + 0.04, 0.07, 1.80, 0.08)
    B(p, S_BEAM, "wood_dark", 0, 1.34, FZ - 0.05, W, 0.16, 0.10)
    B(p, S_BEAM, "wood_dark", 0, 3.06, FZ - 0.05, W, 0.16, 0.10)
    B(p, S_TRIM, "wood_dark", 0, 1.76, FZ - 0.05, 3.46, 2.60, 0.16)
    for xx in (-0.86, 0.86):
        B(p, S_TRIM, "wood", xx, 1.76, FZ - 0.14, 1.62, 2.50, 0.09)
    brace_xy(p, S_TRIM, "wood_dark", -1.66, 0.56, 1.66, 2.96, FZ - 0.19, 0.13, 6)
    brace_xy(p, S_TRIM, "wood_dark", 1.66, 0.56, -1.66, 2.96, FZ - 0.19, 0.13, 6)
    B(p, S_TRIM, "stone_dark", 0, 1.70, FZ - 0.22, 0.10, 2.40, 0.06)
    awning(p, S_TRIM, 0, 3.28, FZ - 0.10, 3.70, 1.35, sign=-1, drop=0.40)
    # 谷仓门框 TC1
    for xx in (-1.78, 1.78):
        B(p, S_TRIM, "cloth_team", xx, 1.76, FZ - 0.20, 0.10, 2.60, 0.05)
    for xx in (-3.05, 3.05):
        window_unit(p, S_TRIM, xx, 2.28, FZ - 0.04, 0.92, 0.80, "-z", team_pelmet=True)
        window_unit(p, S_TRIM, xx, 3.62, FZ - 0.04, 0.92, 0.78, "-z", team_pelmet=True)

    RY = 4.66
    roof_gable(p, S_RL, S_RH, "thatch", 0, 0, W, D, RY, steps=10, rise=3.30, over=0.44,
               ridge="x", split=0.5)
    for w, dy in ((W, 0.0), (W * 0.74, 0.58), (W * 0.48, 1.16),
                  (W * 0.24, 1.74), (W * 0.08, 2.32)):
        for zz in (FZ - 0.02, D / 2 + 0.02):
            B(p, S_WT, "wood", 0, RY + dy + 0.31, zz, w, 0.62, 0.20)
    B(p, S_TRIM, "emblem", 0, RY + 0.94, FZ - 0.30, 1.00, 1.00, 0.05)
    B(p, S_TRIM, "cloth_team", 0, RY + 0.24, FZ - 0.30, W * 0.9, 0.14, 0.06)

    # ---- 筒仓（9.5 m，正面左前方）
    sx, sz = -5.95, -4.55
    B(p, S_FOUND, "stone_dark", sx, 0.32, sz, 3.70, 0.64, 3.70)
    oct_column(p, S_WM, "stone_dark", sx, sz, 1.62, 0.64, 2.60, 0.98)
    oct_column(p, S_WH, "wood", sx, sz, 1.58, 2.60, 7.60, 1.15,
               team_ring=(3.10, 4.90, 6.90))
    for i in range(7):
        oct_slab(p, S_RH, "shingle", sx, sz, 1.74 * (1 - i * 0.14),
                 7.60 + i * 0.25, 0.26)
    B(p, S_TRIM, "wood_dark", sx, 9.42, sz, 0.54, 0.30, 0.54)
    B(p, S_TRIM, "cloth_team", sx, 8.10, sz - 1.50, 3.20, 0.14, 0.20)
    B(p, S_TRIM, "cloth_team", sx, 8.10, sz + 1.50, 3.20, 0.14, 0.20)
    B(p, S_TRIM, "cloth_team", sx - 1.50, 8.10, sz, 0.20, 0.14, 3.00)
    B(p, S_TRIM, "cloth_team", sx + 1.50, 8.10, sz, 0.20, 0.14, 3.00)
    banner_v(p, S_FLAG, sx + 0.05, 6.55, sz - 1.78, w=0.72, h=2.30, facing="-z")
    # 出料口
    B(p, S_TRIM, "wood_dark", sx, 1.55, sz - 1.70, 0.90, 0.90, 0.20)
    B(p, S_TRIM, "steel_dark", sx, 1.55, sz - 1.80, 0.70, 0.70, 0.06)
    # 外部爬梯 + 护笼
    ladder(p, S_TRIM, sx + 1.05, sz - 1.72, 0.0, 9.10, "-z", 0.72, cage=True)
    for i in range(6):
        yy = 2.0 + i * 1.2
        B(p, S_TRIM, "wood_dark", sx + 1.05, yy, sz - 1.95, 0.86, 0.08, 0.08)

    # 谷仓西侧奶牛棚（贴墙披屋，第二处体量）
    DX, DZ = -5.05, 1.75
    B(p, S_FOUND, "stone_dark", DX, 0.16, DZ, 2.20, 0.32, 2.80)
    wall(p, S_WM, "wood", DX, DZ, 2.00, 2.60, 0.32, 2.30, 0.22,
         gaps=[("-z", -0.60, 0.60, 0.32, 1.90)])
    roof_mono(p, S_RL, S_RH, "thatch", DX, DZ, 2.00, 2.60, 2.30, steps=3, rise=0.45,
              over=0.22, axis="x", direction=-1, split=0.5, thick=0.22, shingle=False)
    B(p, S_TRIM, "cloth_team", DX - 1.12, 2.02, DZ, 0.05, 0.20, 2.70)
    # ---- L 形围栏（14 + 9 m，转角柱加粗，双开木门）
    FY, FX = -9.0, -9.2
    for i in range(9):
        xx = FX + i * 1.75
        B(p, S_TRIM, "wood_dark", xx, 0.70, FY, 0.16, 1.40, 0.16)
    B(p, S_TRIM, "wood", -4.90, 0.95, FY, 8.60, 0.11, 0.10)
    B(p, S_TRIM, "wood", -4.90, 0.52, FY, 8.60, 0.11, 0.10)
    B(p, S_TRIM, "wood", 2.90, 0.95, FY, 6.50, 0.11, 0.10)
    B(p, S_TRIM, "wood", 2.90, 0.52, FY, 6.50, 0.11, 0.10)
    for i in range(6):
        zz = FY + 1.55 + i * 1.55
        B(p, S_TRIM, "wood_dark", FX, 0.70, zz, 0.16, 1.40, 0.16)
    B(p, S_TRIM, "wood", FX, 0.95, FY + 3.9, 0.10, 0.11, 7.80)
    B(p, S_TRIM, "wood", FX, 0.52, FY + 3.9, 0.10, 0.11, 7.80)
    B(p, S_TRIM, "wood_dark", FX, 0.90, FY, 0.34, 1.80, 0.34)
    B(p, S_TRIM, "cloth_team", FX, 1.72, FY, 0.42, 0.16, 0.42)
    # 双开木门（TC1 整扇）
    for s in (-1, 1):
        gx = s * 0.85
        B(p, S_TRIM, "cloth_team", gx, 0.85, FY, 1.60, 1.62, 0.10)
        B(p, S_TRIM, "wood_dark", gx, 1.66, FY, 1.64, 0.12, 0.14)
        B(p, S_TRIM, "wood_dark", gx, 0.16, FY, 1.64, 0.14, 0.14)
        B(p, S_TRIM, "steel_dark", gx, 0.85, FY - 0.08, 0.10, 1.40, 0.05)
        B(p, S_TRIM, "steel", s * 0.10, 0.95, FY - 0.10, 0.12, 0.12, 0.06)
    for s in (-1, 1):
        B(p, S_TRIM, "wood_dark", s * 1.70, 0.95, FY, 0.22, 1.90, 0.22)

    # ---- 草垛 ×3 / 水槽 + 辘轳 / 板车 / 稻草人
    for hx, hz, hr in ((-4.4, -6.6, 0.80), (-2.9, -6.9, 0.80), (-3.5, -5.4, 0.72)):
        haystack(p, S_TRIM, hx, hz, r=hr, h=1.25)
    trough(p, S_TRIM, 2.6, -5.2)
    B(p, S_TRIM, "wood_dark", 4.0, 0.85, -5.2, 0.16, 1.70, 0.16)
    B(p, S_TRIM, "wood_dark", 4.0, 1.68, -5.2, 0.90, 0.12, 0.12)
    oct_slab(p, S_TRIM, "wood", 4.0, -5.2, 0.30, 1.30, 0.16)
    B(p, S_TRIM, "wood_dark", 4.0, 1.30, -5.2, 0.42, 0.10, 0.10)
    cart(p, S_TRIM, 1.2, -7.0)
    scarecrow(p, S_TRIM, 6.2, 2.6)

    # ---- 田地与作物：3 条垄，麦 / 白菜 / 南瓜
    for r in range(3):
        zc = -0.4 + r * 1.9
        B(p, S_TRIM, "stone_dark", 8.2, 0.06, zc, 6.4, 0.12, 1.0)
        B(p, S_TRIM, "thatch", 8.2, 0.18, zc, 6.2, 0.16, 0.92)
        n = 9
        for i in range(n):
            xx = 5.25 + i * 0.72
            if r == 0:
                for k, hh in ((0, 0.35), (1, 0.55), (2, 0.75)):
                    B(p, S_TRIM, "thatch", xx + (0.03 if k % 2 else -0.03), 0.26 + hh / 2, zc,
                      0.10, hh, 0.10)
            elif r == 1:
                B(p, S_TRIM, "wood", xx, 0.42, zc, 0.30, 0.26, 0.30)
                B(p, S_TRIM, "thatch", xx, 0.58, zc, 0.42, 0.18, 0.42)
            else:
                B(p, S_TRIM, "thatch", xx, 0.36, zc, 0.44, 0.28, 0.42)
                B(p, S_TRIM, "wood_dark", xx + 0.28, 0.28, zc - 0.18, 0.30, 0.05, 0.05)
                B(p, S_TRIM, "wood_dark", xx + 0.40, 0.30, zc - 0.28, 0.18, 0.05, 0.05)
    B(p, S_FLAG, "wood_dark", 5.05, 0.75, -0.4, 0.06, 1.50, 0.06)
    flag_b(p, S_FLAG, 5.05, 1.30, -0.4, w=0.30, ln=1.10, direction=1)
    B(p, S_FLAG, "wood_dark", 11.25, 0.75, 3.4, 0.06, 1.50, 0.06)
    flag_b(p, S_FLAG, 11.25, 1.30, 3.4, w=0.30, ln=1.10, direction=-1)

    scaffold(p, 0, 0, W, D, 5.6, levels=3)
    _tag_duty(p, lambda q: abs(q["box"][0] + 5.95) < 1.95 and abs(q["box"][2] + 4.55) < 1.95 and q["box"][1] > 2.4)
    rubble(p, 0, 0, W + 1, D, 24)
    return p, {"name": "farm", "cn": "农场", "roof": "gable_steep",
               "volumes": [(-7.7, -4.2, -6.3, -2.8), (-6.3, -3.8, 0.3, 3.3)],
               "team_zones": ["围栏双开门", "水槽边沿", "筒仓 3 道铁箍", "板车篷",
                              "谷仓门框", "稻草人腰带", "筒仓通风帽下沿", "田垄端头旗 ×2",
                              "窗楣 TC1"]}


# ================================================================== 哨塔
def b_watchtower():
    p = []
    W = 4.2
    FX = W / 2
    B(p, S_SITE, "wood_dark", 0, 0.04, 0, W + 2.2, 0.09, W + 2.2)
    for i, ins in enumerate((0.85, 0.50, 0.22)):
        B(p, S_FOUND, "stone_dark", 0, 0.15 + i * 0.28, 0, W + ins, 0.28, W + ins)
    Y0 = 0.84
    for sx in (-1, 1):
        for sz in (-1, 1):
            for k in range(4):
                yy = Y0 + 1.42 + k * 2.84
                if yy > 12.6:
                    break
                B(p, S_WL if k < 2 else S_WH, "wood_dark",
                  sx * FX, yy, sz * FX, 0.38, 2.72, 0.38)
    wall(p, S_WL, "wood", 0, 0, W + 0.58, W + 0.58, Y0, 3.30, 0.26, gaps=[
        ("-z", -0.72, 0.72, Y0, 2.62),
        ("-x", -0.62, 0.48, 1.72, 2.46), ("+x", -0.62, 0.48, 1.72, 2.46),
        ("+z", -0.55, 0.55, 1.72, 2.46)])
    for i in range(9):
        xx = -(W + 0.58) / 2 + 0.28 + i * 0.56
        B(p, S_WL, "wood_dark", xx, 2.05, -(W + 0.58) / 2 - 0.04, 0.07, 2.60, 0.08)
        B(p, S_WL, "wood_dark", xx, 2.05, (W + 0.58) / 2 + 0.04, 0.07, 2.60, 0.08)
    B(p, S_TRIM, "wood_dark", 0, 2.62, -(W + 0.58) / 2 - 0.05, 1.66, 0.16, 0.16)
    B(p, S_TRIM, "wood", 0, 1.60, -(W + 0.58) / 2 - 0.02, 1.40, 2.06, 0.13)
    B(p, S_TRIM, "steel_dark", 0, 1.60, -(W + 0.58) / 2 - 0.10, 0.08, 1.90, 0.05)
    # 基座门框 TC1 + 压顶
    for xx in (-0.86, 0.86):
        B(p, S_TRIM, "cloth_team", xx, 1.70, -(W + 0.58) / 2 - 0.16, 0.10, 2.10, 0.05)
    B(p, S_TRIM, "cloth_team", 0, 2.76, -(W + 0.58) / 2 - 0.16, 1.86, 0.14, 0.05)
    bw = W + 0.80
    B(p, S_TRIM, "cloth_team", 0, 3.34, -bw / 2 + 0.09, bw, 0.14, 0.18)
    B(p, S_TRIM, "cloth_team", 0, 3.34, bw / 2 - 0.09, bw, 0.14, 0.18)
    B(p, S_TRIM, "cloth_team", -bw / 2 + 0.09, 3.34, 0, 0.18, 0.14, bw - 0.36)
    B(p, S_TRIM, "cloth_team", bw / 2 - 0.09, 3.34, 0, 0.18, 0.14, bw - 0.36)
    B(p, S_TRIM, "cloth_team", 0, 3.10, -(W + 0.58) / 2 - 0.16, W + 0.60, 0.20, 0.05)
    B(p, S_TRIM, "cloth_team", 0, 9.10, -FX - 0.16, 1.60, 0.18, 0.05)
    window_unit(p, S_TRIM, -1.30, 2.10, -(W + 0.58) / 2 - 0.05, 0.70, 0.62, "-z")
    window_unit(p, S_TRIM, 1.30, 2.10, -(W + 0.58) / 2 - 0.05, 0.70, 0.62, "-z")

    for lvl, yy in enumerate((1.70, 4.70, 7.70, 10.70)):
        st = S_WL if lvl < 2 else S_WH
        for sz in (-1, 1):
            B(p, st, "wood", 0, yy, sz * FX, W + 0.10, 0.22, 0.24)
            B(p, st, "wood", 0, yy + 0.62, sz * FX, W + 0.10, 0.16, 0.20)
        for sx in (-1, 1):
            B(p, st, "wood", sx * FX, yy, 0, 0.24, 0.22, W + 0.10)
            B(p, st, "wood", sx * FX, yy + 0.62, 0, 0.20, 0.16, W + 0.10)
        for sz in (-1, 1):
            brace_xy(p, st, "wood_dark", -FX, yy + 0.12, FX, yy + 1.30, sz * FX, 0.11, 5)
            brace_xy(p, st, "wood_dark", FX, yy + 0.12, -FX, yy + 1.30, sz * FX, 0.11, 5)
        for sx in (-1, 1):
            brace_zy(p, st, "wood_dark", -FX, yy + 0.12, FX, yy + 1.30, sx * FX, 0.11, 5)
            brace_zy(p, st, "wood_dark", FX, yy + 0.12, -FX, yy + 1.30, sx * FX, 0.11, 5)
        # 四柱箍（每 2.5 m 一道，共 8 道）
        if lvl < 3:
            for sx in (-1, 1):
                for sz in (-1, 1):
                    B(p, st, "cloth_team", sx * FX, yy + 0.36, sz * FX, 0.46, 0.28, 0.46)

    HB = 6.20
    B(p, S_WM, "wood_dark", 0, HB - 0.16, 0, W + 1.30, 0.22, W + 1.30)
    # 观景廊：三面 TC1 栏板（背面开敞）
    for sz in (-1, 1):
        for i in range(5):
            xx = -1.72 + i * 0.86
            B(p, S_WM, "cloth_team", xx, HB + 0.55, sz * (FX + 0.62), 0.74, 0.44, 0.16)
            B(p, S_WM, "wood_dark", xx, HB + 1.20, sz * (FX + 0.62), 0.78, 0.12, 0.20)
            B(p, S_WM, "wood_dark", xx, HB + 0.08, sz * (FX + 0.62), 0.78, 0.12, 0.20)
        for xx in (-1.72, -0.86, 0.0, 0.86, 1.72):
            B(p, S_WM, "wood_dark", xx, HB + 0.66, sz * (FX + 0.74), 0.09, 1.24, 0.08)
    # 第三面：+X 侧
    for i in range(3):
        zz = -0.72 + i * 0.86
        B(p, S_WM, "cloth_team", FX + 0.62, HB + 0.55, zz, 0.16, 0.44, 0.78)
        B(p, S_WM, "wood_dark", FX + 0.62, HB + 1.20, zz, 0.20, 0.12, 0.82)
    for zz in (-1.0, 0.0, 1.0):
        B(p, S_WM, "wood_dark", FX + 0.74, HB + 0.66, zz, 0.08, 1.24, 0.09)
    for sz in (-1, 1):
        brace_zy(p, S_WM, "wood_dark", sz * (FX + 0.62), HB - 0.02,
                 sz * FX, HB - 1.05, -FX, 0.10, 4)
        brace_zy(p, S_WM, "wood_dark", sz * (FX + 0.62), HB - 0.02,
                 sz * FX, HB - 1.05, FX, 0.10, 4)
    for sz in (-1, 1):
        for k in range(2):
            B(p, S_RL if k == 0 else S_RH, "shingle", 0, HB + 1.60 + k * 0.20,
              sz * (FX + 0.86 - k * 0.34), W + 1.90, 0.20, 0.72)

    PY = 12.60
    B(p, S_BEAM, "wood_dark", 0, PY, 0, W + 1.80, 0.28, W + 1.80)
    B(p, S_BEAM, "wood", 0, PY + 0.24, 0, W + 1.44, 0.18, W + 1.44)
    for sx in (-1, 1):
        for sz in (-1, 1):
            B(p, S_BEAM, "wood_dark", sx * (FX + 0.82), PY - 0.36, sz * (FX + 0.82),
              0.20, 0.72, 0.20)
            brace_xy(p, S_BEAM, "wood_dark", sx * (FX + 0.82), PY - 1.40,
                     sx * FX, PY - 0.10, sz * (FX + 0.72), 0.10, 4)
            B(p, S_BEAM, "wood_dark", sx * (FX + 0.86), PY + 0.98, sz * (FX + 0.86),
              0.18, 1.46, 0.18)
    for sz in (-1, 1):
        for yy in (PY + 0.44, PY + 0.92, PY + 1.62):
            B(p, S_BEAM, "wood", 0, yy, sz * (FX + 0.86), W + 1.72, 0.13, 0.13)
    for sx in (-1, 1):
        for yy in (PY + 0.44, PY + 0.92, PY + 1.62):
            B(p, S_BEAM, "wood", sx * (FX + 0.86), yy, 0, 0.13, 0.13, W + 1.72)
    for i in range(7):
        xx = -FX - 0.70 + i * 0.60
        for sz in (-1, 1):
            B(p, S_BEAM, "wood_dark", xx, PY + 0.74, sz * (FX + 0.86), 0.07, 0.80, 0.07)
    # 方冠檐口断续 TC1
    for i in range(4):
        for sz in (-1, 1):
            B(p, S_TRIM, "cloth_team", -1.5 + i * 1.0, PY + 1.24, sz * (FX + 0.96),
              0.70, 0.14, 0.05)
        for sx in (-1, 1):
            B(p, S_TRIM, "cloth_team", sx * (FX + 0.96), PY + 1.24, -1.5 + i * 1.0,
              0.05, 0.14, 0.70)

    for sx in (-1, 1):
        for sz in (-1, 1):
            B(p, S_RH, "wood_dark", sx * 1.55, PY + 1.75, sz * 1.55, 0.22, 2.90, 0.22)
    B(p, S_RH, "wood_dark", 0, PY + 3.16, 0, W + 0.30, 0.20, W + 0.30)
    roof_pyramid(p, S_RL, "shingle", 0, 0, W + 0.30, PY + 3.26, steps=3, rise=1.35,
                 over=0.52, finial=None)
    _tag_duty(p, lambda q: q["box"][1] > 12.25)
    roof_pyramid(p, S_RH, "shingle", 0, 0, W * 0.52, PY + 4.50, steps=2, rise=0.72,
                 over=0.30, finial="gold")
    B(p, S_TRIM, "gold", 0, PY + 5.42, 0, 0.16, 0.36, 0.16)

    ladder(p, S_TRIM, -FX - 0.55, 0.0, Y0, PY - 0.20, 0.80)
    ladder(p, S_TRIM, 0.0, FX + 0.55, Y0, HB - 0.30, 0.72)

    # 平台垂旗 ×3（A 型）+ 塔顶旗（B 型）
    for sz in (-1, 1):
        B(p, S_FLAG, "wood_dark", sz * (FX + 0.62), PY + 0.55, -(FX + 0.30),
          0.09, 1.20, 0.09)
        flag_a(p, S_FLAG, sz * (FX + 0.62), PY + 0.48, -(FX + 0.36),
               w=0.50, h=1.20, axis="x", pole=False)
    B(p, S_FLAG, "wood_dark", 0, PY + 0.55, -(FX + 0.30), 0.09, 1.20, 0.09)
    flag_a(p, S_FLAG, 0, PY + 0.48, -(FX + 0.36), w=0.50, h=1.20, axis="x", pole=False)
    # 塔顶 B 型（直接挂在金顶上，总高 18.2）
    flag_b(p, S_FLAG, 0, PY + 5.38, 0, w=0.30, ln=1.05, direction=1, pole_top=False)

    # 塔身正面垂幅（中高区识别）
    banner_v(p, S_FLAG, 0.0, 10.60, -FX - 0.06, w=1.10, h=3.30, facing="-z")
    # 平台火盆 / 箭袋 ×4 / 水桶 ×2 / 绞盘
    brazier(p, S_TRIM, 1.05, 1.05, PY + 0.28)
    for sx in (-1, 1):
        for sz in (-1, 1):
            B(p, S_TRIM, "leather", sx * 1.42, PY + 0.62, sz * 1.42, 0.18, 0.58, 0.18)
            for i in range(4):
                B(p, S_TRIM, "wood", sx * 1.42 + 0.04, PY + 0.80 + i * 0.10,
                  sz * 1.42, 0.05, 0.34, 0.05)
    barrel(p, S_TRIM, -1.10, 0.95, PY + 0.28, 0.25, 0.46)
    barrel(p, S_TRIM, -0.52, 1.05, PY + 0.28, 0.25, 0.46)
    # 底部绞盘
    B(p, S_TRIM, "wood_dark", 0, 0.60, 3.05, 0.60, 1.20, 0.60)
    oct_slab(p, S_TRIM, "wood", 0, 3.05, 0.44, 0.90, 0.18)
    B(p, S_TRIM, "steel_dark", 0.50, 0.95, 3.05, 0.10, 0.10, 0.10)
    B(p, S_TRIM, "cloth_team", 0.50, 0.95, 3.05, 0.28, 0.10, 0.10)

    # 基座西侧守卫披屋
    HX, HZ = -3.30, 0.90
    B(p, S_FOUND, "stone_dark", HX, 0.16, HZ, 2.10, 0.32, 2.80)
    wall(p, S_WL, "wood", HX, HZ, 1.90, 2.60, 0.32, 2.30, 0.20,
         gaps=[("-x", -0.55, 0.55, 0.32, 1.90)])
    for xx in (-1.86, -1.00):
        B(p, S_WM, "wood_dark", HX + xx, 1.15, HZ + 1.20, 0.16, 2.30, 0.16)
    roof_mono(p, S_RL, S_RH, "shingle", HX, HZ, 1.90, 2.60, 2.30, steps=3, rise=0.50,
              over=0.22, axis="z", direction=-1, split=0.5, thick=0.20, shingle=False)
    B(p, S_TRIM, "cloth_team", HX, 2.32, HZ - 1.24, 2.00, 0.24, 0.05)
    B(p, S_TRIM, "cloth_team", HX, 2.32, HZ + 1.24, 2.00, 0.24, 0.05)
    B(p, S_TRIM, "cloth_team", HX - 0.92, 1.20, HZ, 0.05, 1.90, 0.16)
    # 东侧柴垛
    for i in range(4):
        for j in range(5 - (i // 3)):
            B(p, S_TRIM, "wood", 3.10 + i * 0.36, 0.20 + j * 0.34, 2.10,
              0.34, 0.30, 1.50)
            B(p, S_TRIM, "wood_dark", 3.10 + i * 0.36, 0.20 + j * 0.34, 2.86,
              0.30, 0.26, 0.04)
    B(p, S_TRIM, "cloth_team", 3.55, 0.55, 2.10, 0.06, 0.12, 1.55)
    scaffold(p, 0, 0, W, W, 11.0, levels=5)
    rubble(p, 0, 0, W + 1.5, W + 1.5, 22)
    return p, {"name": "watchtower", "cn": "哨塔", "roof": "crown_eave",
               "volumes": [(-4.5, -2.1, -0.6, 2.4), (2.8, 4.7, 1.2, 3.0)],
               "team_zones": ["基座门框+压顶", "四柱箍 8 道", "观景廊三面栏板",
                              "方冠檐口饰条", "三面垂旗+塔顶旗", "平台火盆", "绞盘握把"]}


# ================================================================== 伐木场
def b_lumbermill():
    """伐木场 v5：一座敞棚 + 一台立式锯框 + 一堆原木。

    识别顺序 = 设计顺序：锯框 → 原木端面年轮 → 龙门吊。
    锯框是独立于棚体的第二重剪影，把棚口的黑腔切成三块 —— 这是"一眼认出
    是锯木厂"的唯一办法，所以它必须在正中偏前，正面完全开敞。
    """
    p = []
    W, D = 7.2, 6.0
    FZ, BZ = -D / 2, D / 2
    EAVE, RIDGE = 5.2, 6.6

    hs.box(p, S_SITE, "wood_dark", 0, 0.04, -0.4, W + 5.2, 0.09, D + 8.0, tile=1.5)
    hs.box(p, S_FOUND, "stone_dark", 0, 0.16, 0, W + 0.6, 0.32, D + 0.6, tile=1.2)
    for sx in (-1, 1):
        for zz in (-2.55, 0.0, 2.55):
            hs.box(p, S_FOUND, "stone_dark", sx * 3.36, 0.44, zz, 0.62, 0.30, 0.62, tile=1.0)
            # 六根柱：0.30 方，柱脚落在石墩上
            hs.box(p, S_WL, "wood", sx * 3.36, (0.59 + EAVE) / 2, zz, 0.30, EAVE - 0.59, 0.30, tile=0.9)

    # ---------------- 檐梁 + 檩
    for sx in (-1, 1):
        hs.box(p, S_BEAM, "wood_dark", sx * 3.36, EAVE - 0.10, 0, 0.34, 0.24, D + 0.7, tile=0.9)
    hs.box(p, S_BEAM, "wood_dark", 0, RIDGE - 0.12, 0, W + 0.9, 0.22, 0.26, tile=0.9)
    for sx in (-1, 1):
        hs.bar(p, S_BEAM, "wood_dark", (sx * 3.36, EAVE - 0.22, FZ - 0.30),
               (0, RIDGE - 0.24, FZ - 0.30), 0.14, 0.16, up=(0, 0, 1), tile=0.9)
        hs.bar(p, S_BEAM, "wood_dark", (sx * 3.36, EAVE - 0.22, BZ + 0.30),
               (0, RIDGE - 0.24, BZ + 0.30), 0.14, 0.16, up=(0, 0, 1), tile=0.9)

    # ---------------- 双坡薄壳屋面（脊沿 X）
    pl1 = roofs.Plane((-W / 2 - 0.45, EAVE, FZ - 0.45), (W / 2 + 0.45, EAVE, FZ - 0.45),
                      (-W / 2 - 0.45, RIDGE, 0), (W / 2 + 0.45, RIDGE, 0))
    pl2 = roofs.Plane((-W / 2 - 0.45, EAVE, BZ + 0.45), (W / 2 + 0.45, EAVE, BZ + 0.45),
                      (-W / 2 - 0.45, RIDGE, 0), (W / 2 + 0.45, RIDGE, 0))
    for pl, st in ((pl1, S_RL), (pl2, S_RH)):
        hs.grid_slab(p, st, "shingle", pl, roofs.BOARD_T, nu=6, nv=4, tile=0.9, role="roof")
        hs.rafters(p, st, "wood_dark", pl, 13, w=roofs.RAFTER_W, h=roofs.RAFTER_H,
                   drop=0.0, v0=-0.02, v1=0.99, tile=0.9, role="rafter")
        hs.courses(p, st, "shingle", pl, course=0.22, thick=roofs.SHINGLE_T, lip=0.03,
                   tile=0.9, role="roof")
        e0, e1 = pl.pt(0.0, 0.0), pl.pt(1.0, 0.0)
        n = pl.normal()
        hs.bar(p, st, "wood_dark", e0 + n * (-0.03), e1 + n * (-0.03), 0.24, 0.14,
               up=n, tile=0.9, role="fascia")
    hs.ridge_cap(p, S_RH, "wood_dark", "cloth_team",
                 (-W / 2 - 0.45, RIDGE, 0), (W / 2 + 0.45, RIDGE, 0), RIDGE + 0.02, team=True)
    # 山墙人字架：敞棚不封山墙，用桁架把屋顶的力传到柱子上
    for sx in (-1, 1):
        xx = sx * (W / 2 + 0.10)
        hs.box(p, S_BEAM, "wood_dark", xx, EAVE - 0.10, 0, 0.18, 0.22, D + 0.4, tile=0.9)
        hs.box(p, S_BEAM, "wood_dark", xx, (EAVE + RIDGE) / 2, 0, 0.16, RIDGE - EAVE, 0.18, tile=0.9)
        for sz in (-1, 1):
            hs.bar(p, S_BEAM, "wood_dark", (xx, EAVE - 0.04, sz * 2.10),
                   (xx, RIDGE - 0.26, sz * 0.10), 0.12, 0.14, up=(1, 0, 0), tile=0.9)

    # ---------------- 立式锯框 2.80 高 × 2.20 宽，正中偏前
    sy = 0.95                                  # 框底标高（坐在锯台面上）
    szc = FZ + 0.24                            # 桩位：紧贴棚口，正面完全开敞
    fw, fh = 2.20, 2.80
    y0, y1 = sy, sy + fh
    hs.box(p, S_FOUND, "stone_dark", 0, 0.17, szc + 0.30, fw + 0.30, 0.34, 1.10, tile=1.0)
    # 锯台面：原木从这儿推过去，也是锯框在正视图里的"底座"
    hs.box(p, S_TRIM, "wood_dark", 0, (0.34 + sy) / 2, szc + 0.10,
           fw + 0.24, sy - 0.34, 0.90, tile=0.9, role="duty")
    for sx in (-1, 1):
        hs.box(p, S_WT, "wood_dark", sx * (fw / 2 - 0.12), (y0 + y1) / 2, szc,
               0.24, fh, 0.24, tile=0.9, role="duty")
    hs.box(p, S_WT, "wood_dark", 0, y1 - 0.11, szc, fw, 0.22, 0.26, tile=0.9, role="duty")
    hs.box(p, S_WT, "wood_dark", 0, y0 + 0.11, szc, fw, 0.22, 0.26, tile=0.9, role="duty")
    for yy in (y0 + 1.05, y0 + 2.05):
        hs.box(p, S_WT, "wood_dark", 0, yy, szc, fw - 0.30, 0.12, 0.12, tile=0.9, role="duty")
    # 锯条 1.90 × 0.10 × 0.06，方齿每 0.12 一个、交替左右偏移
    hs.box(p, S_TRIM, "steel", 0, (y0 + 0.22 + y1 - 0.22) / 2, szc + 0.03,
           0.14, fh - 0.50, 0.08, tile=0.7, role="duty")
    for i in range(15):
        ty = y0 + 0.24 + i * 0.12
        if ty > y1 - 0.24:
            break
        dx = 0.075 if i % 2 else -0.075
        hs.box(p, S_TRIM, "steel_dark", dx, ty, szc + 0.03, 0.14, 0.06, 0.08,
               tile=0.7, role="duty")
    # 滑车 2.4 × 0.9 × 0.35 + 4 个阶梯八边形轮
    hs.box(p, S_TRIM, "wood_dark", 0, sy + 0.18, szc - 0.95, 2.40, 0.35, 0.90, tile=0.9, role="duty")
    for sx in (-1, 1):
        for zz in (-1, 1):
            hs.prism_y(p, S_TRIM, "steel_dark",
                       hs.ngon(sx * 1.02, szc - 0.95 + zz * 0.28, 0.17, 8), 0.02, 0.14, tile=0.7)
    # 原木（在锯上）：φ0.46 × 3.4，端面朝外，3 圈年轮
    ly = sy + 0.62
    hs.prism_y(p, S_TRIM, "wood", hs.ngon(0, szc - 0.95, 0.23, 12), ly - 0.23, ly + 0.23, tile=1.0, role="duty")
    for rr, mat in ((0.19, "wood_dark"), (0.12, "wood"), (0.055, "wood_dark")):
        hs.prism_y(p, S_TRIM, mat, hs.ngon(0, szc - 0.95, rr, 12), ly + 0.225, ly + 0.245, tile=1.0, role="duty")

    # ---------------- 后墙：横向板墙（不是整面实墙，棚要透气）
    for i in range(7):
        yy = 0.55 + i * 0.66
        hs.box(p, S_WM, "wood", 0, yy, BZ - 0.12, W, 0.58, 0.16, tile=1.0)
    for i in range(3):
        hs.box(p, S_WM, "wood_dark", 0, 0.55 + i * 2.0, BZ - 0.06, W, 0.16, 0.10, tile=0.9)
    # 两侧半高板墙
    for sx in (-1, 1):
        for i in range(4):
            hs.box(p, S_WM, "wood", sx * (W / 2 - 0.10), 0.55 + i * 0.66, 0,
                   0.16, 0.58, D - 0.4, tile=1.0)

    # ---------------- 龙门吊：移到棚后，跨原木堆
    gy = 8.00
    for sx in (-1, 1):
        hs.box(p, S_WT, "wood_dark", sx * 3.10, gy / 2, BZ + 2.55, 0.34, gy, 0.34, tile=0.9)
        hs.box(p, S_FOUND, "stone_dark", sx * 3.10, 0.22, BZ + 2.55, 0.72, 0.44, 0.72, tile=1.0)
        hs.bar(p, S_WT, "wood_dark", (sx * 3.10, 5.90, BZ + 2.55),
               (sx * 3.10, gy - 0.10, BZ + 2.55 - 0.95), 0.16, 0.18, up=(1, 0, 0), tile=0.9)
    hs.box(p, S_WT, "wood_dark", 0, gy, BZ + 2.55, 6.60, 0.34, 0.40, tile=0.9, role="duty")
    hs.box(p, S_TRIM, "cloth_team", 0, gy + 0.22, BZ + 2.55, 6.62, 0.10, 0.44, tile=1.0, role="team")
    hs.box(p, S_TRIM, "steel_dark", 0, gy - 0.30, BZ + 2.55, 0.24, 0.28, 0.24, tile=0.7)
    hs.box(p, S_TRIM, "steel_dark", 0, gy - 0.90, BZ + 2.55, 0.10, 1.10, 0.10, tile=0.7)
    hs.bar(p, S_TRIM, "steel_dark", (0, gy - 1.44, BZ + 2.55), (0, gy - 1.44, BZ + 2.55), 0.1, 0.1)

    # ---------------- 原木堆：金字塔 3-2-1
    for row, n in enumerate((3, 2, 1)):
        for i in range(n):
            x = (i - (n - 1) / 2) * 0.52
            yy = 0.23 + row * 0.40
            hs.prism_y(p, S_TRIM, "wood", hs.ngon(x, BZ + 2.45, 0.23, 12), yy - 0.23, yy + 0.23, tile=1.0)
            for zz in (-1, 1):
                hs.prism_y(p, S_TRIM, "wood_dark",
                           hs.ngon(x, BZ + 2.45, 0.19, 12), yy + zz * 0.225, yy + zz * 0.245, tile=1.0)
    # 挡木（防止原木滚散）
    for sx in (-1, 1):
        hs.box(p, S_TRIM, "wood_dark", sx * 1.05, 0.22, BZ + 2.45, 0.16, 0.44, 3.0, tile=0.9)
    hs.box(p, S_TRIM, "wood_dark", 0, 0.12, BZ + 2.45, 2.4, 0.16, 3.2, tile=1.0)

    # ---------------- 锯末：3 处方堆 + 6 块散落
    for (dx2, dz2, s2) in ((-1.55, FZ + 1.05, 1.10), (0.35, FZ + 0.75, 0.86), (1.62, FZ + 1.35, 0.72)):
        hs.box(p, S_TRIM, "thatch", dx2, 0.10, dz2, s2, 0.20, s2 * 0.8, tile=0.8)
        hs.box(p, S_TRIM, "thatch", dx2 + 0.12, 0.20, dz2 - 0.06, s2 * 0.62, 0.12, s2 * 0.5, tile=0.8)
    for i in range(6):
        hs.add(p, S_TRIM, "thatch",
               [(x0, -0.01, z0) for x0, z0 in [
                   (-1.0 + i * 0.42, FZ + 2.0 + (i % 3) * 0.4),
                   (-0.78 + i * 0.42, FZ + 2.0 + (i % 3) * 0.4),
                   (-0.70 + i * 0.42, FZ + 2.16 + (i % 3) * 0.4),
                   (-1.08 + i * 0.42, FZ + 2.16 + (i % 3) * 0.4)]] +
               [(x0, 0.03, z0) for x0, z0 in [
                   (-1.0 + i * 0.42, FZ + 2.0 + (i % 3) * 0.4),
                   (-0.78 + i * 0.42, FZ + 2.0 + (i % 3) * 0.4),
                   (-0.70 + i * 0.42, FZ + 2.16 + (i % 3) * 0.4),
                   (-1.08 + i * 0.42, FZ + 2.16 + (i % 3) * 0.4)]],
               [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)],
               tile=0.7)

    # ---------------- 阵营色：檐口 / 柱箍 / 锯框顶梁（只沿结构线）
    for sx in (-1, 1):
        hs.box(p, S_TRIM, "cloth_team", sx * 3.36, EAVE - 0.26, 0, 0.38, 0.10, D + 0.72, tile=1.0, role="team")
        for zz in (-2.55, 0.0, 2.55):
            hs.box(p, S_TRIM, "cloth_team", sx * 3.36, 3.20, zz, 0.36, 0.12, 0.36, tile=1.0, role="team")
    hs.box(p, S_TRIM, "cloth_team", 0, y1 - 0.02, szc, fw + 0.06, 0.10, 0.24, tile=1.0, role="team")
    # 旗
    hs.box(p, S_FLAG, "wood_dark", 3.36, EAVE + 0.55, FZ - 0.10, 0.08, 1.50, 0.08, tile=0.9)
    flag_a(p, S_FLAG, 3.36, EAVE + 0.42, FZ - 0.10, w=0.46, h=1.20, axis="z", pole=False)

    scaffold(p, 0, 0, W, D, 7.0, levels=3)
    rubble(p, 0, 0, W + 3.0, D + 6.0, 22)
    return p, {"name": "lumbermill", "cn": "伐木场", "roof": "open_shed",
               "height": 8.2,
               "volumes": [(-1.10, 1.10, FZ + 0.20, FZ + 1.50),
                           (-3.44, -2.60, BZ + 1.0, BZ + 3.4),
                           (2.60, 3.44, BZ + 1.0, BZ + 3.4)],
               "team_zones": ["檐口条", "柱箍 6 处", "锯框顶梁", "龙门吊横梁", "旗"]}
BUILD_INDEX = {
    "townhall": b_townhall,
    "barracks": b_barracks,
    "blacksmith": b_blacksmith,
    "farm": b_farm,
    "watchtower": b_watchtower,
    "lumbermill": b_lumbermill,
}
