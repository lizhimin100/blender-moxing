"""
dl_kit.py —— 失落帝国 / 酒馆 / 火 三套新资产的共用构件库（第十、十一、十二座）

只放"至少两座会用到"的东西。一座独有的形体写在各自的 *_model.py 里，
避免这里长成一个什么都塞的大杂烩（那正是九座后期最难维护的部分）。

三条与九座一致的约定：
  * 1 unit = 1 m；原点在占地中心，z = 0 地面；建模期 +Y 是正面。
  * 所有构件名 = "前缀_" 开头，体检按前缀分组（dl_align）。
  * 任何"叠在某个面上"的件都要么沉进去 3 mm、要么抬起来 6 mm，
    绝不允许两个朝上的面同高（COPLANAR_UP 会闪）。

风格边界（很重要）：
  失落帝国 = **冷**（ancient 冷灰蓝 + bronze 铜绿 + depth_glow 幽绿），
             墙面用"大块砌体 + 少量凸出的牙石"，不做人族那种通长腰线；
  酒馆室内 = **暖**（plaster 石灰白 + wood 三档 + copper），
             靠家具的密集小体量分层，不靠线脚；
  火       = 三 tongue 结构（外焰暗橙 / 中焰橙 / 芯焰亮黄），绝不做单层色板。
"""
import math
import random

from mathutils import Vector

import bslib as L
from bslib import (beam, box, cone, extrude, frustum, lathe, mesh_obj, revolve,
                   ring_y, tube_band)
from wt_model import frame_ring

TAU = math.tau


# ── 小工具 ──────────────────────────────────────────────────────────────────
def rot_box(name, center, size, mat, rot=(0, 0, 0)):
    return box(name, center, size, mat, rot=rot)


def stones(name, cx, cy, z0, n, spread, base, mats, seed=1, flat=True):
    """碎石堆：n 块带随机旋转的方石（俯视是一圈有棱的小块，不是圆点）。

    base = 单块基准尺寸；每块在 0.6–1.25 倍之间，落点按 2D 环分布，
    z 依次抬高 —— 堆的样子来自"叠"，不是来自"多"。
    """
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        a = TAU * rnd.random()
        r = spread * math.sqrt(rnd.random())
        s = base * (0.6 + 0.65 * rnd.random())
        z = z0 + s * 0.17 + (0.045 * (n - i) / max(n, 1))
        mat = mats[i % len(mats)]
        ob = box(name, (cx + r * math.cos(a), cy + r * math.sin(a), z),
                 (s, s * (0.72 + 0.4 * rnd.random()), s * (0.5 + 0.35 * rnd.random())),
                 mat, rot=(rnd.uniform(-0.30, 0.30), rnd.uniform(-0.26, 0.26),
                           rnd.uniform(0, TAU)))
        # 旋转会把底角转下去 / 转上来：按真实最低点重新落位，保证"沉进地面 1 cm"
        mn = min(v.co.z for v in ob.data.vertices)
        ob.location.z += (z0 - 0.01) - mn
        out.append(ob)
    return out


def grass(name, x, y, z, h=0.26, n=5, seed=1, mat=None):
    """草簇：n 片带锥度的窄叶（不是圆点、不是噪声斑）。"""
    rnd = random.Random(seed)
    mat = mat or L.make_material("moss_dark")
    out = []
    for i in range(n):
        a = TAU * i / n + rnd.uniform(-0.4, 0.4)
        lean = rnd.uniform(0.10, 0.34)
        w = 0.026 + rnd.random() * 0.012
        hh = h * (0.7 + 0.5 * rnd.random())
        ob = beam(name, (x + 0.04 * math.cos(a), y + 0.04 * math.sin(a), z),
                  (x + lean * math.cos(a), y + lean * math.sin(a), z + hh),
                  w, 0.010, mat, up="Z")
        if ob is not None:
            ob.rotation_euler.rotate_axis("Y", rnd.uniform(-0.2, 0.2))
            out.append(ob)
    return out


def chain(name, x, y, z0, z1, w, mat, links=None):
    """吊链：一根方杆 + 一串扁环。RTS 距离上链条只有 2–3 px 宽，
    做 40 个真链环是浪费面数；"杆 + 环"在剪影上一样读作链。"""
    h = z1 - z0
    out = [box(name + "_rod", (x, y, (z0 + z1) * 0.5), (w * 0.55, w * 0.55, h), mat)]
    n = links or max(3, int(h / 0.20))
    for i in range(n):
        zz = z0 + h * (i + 0.5) / n
        if i % 2 == 0:
            out.append(box(name + "_link", (x, y, zz), (w, w * 0.42, w * 0.62), mat))
        else:
            out.append(box(name + "_link", (x, y, zz), (w * 0.42, w, w * 0.62), mat))
    return out


def grate(name, cx, cy, z, w, d, bars=5, mat=None, frame_mat=None):
    """铁栅：一圈边框 + n 根竖条 + 2 根横条。"""
    M = L.all_materials()
    mat = mat or M["bronze_dark"]
    frame_mat = frame_mat or M["bronze"]
    out = [box(name + "_frame0", (cx, cy - d * 0.5 + 0.04, z), (w, 0.08, 0.10), frame_mat),
           box(name + "_frame1", (cx, cy + d * 0.5 - 0.04, z), (w, 0.08, 0.10), frame_mat)]
    for s in (-1, 1):
        out.append(box(name + "_frame2", (cx + s * (w * 0.5 - 0.04), cy, z),
                       (0.08, d - 0.16, 0.10), frame_mat))
    for i in range(bars):
        xx = cx - w * 0.5 + 0.16 + (w - 0.32) * i / max(bars - 1, 1)
        out.append(box(name + "_bar", (xx, cy, z + 0.02), (0.045, d - 0.16, 0.055), mat))
    for yy in (cy - d * 0.24, cy + d * 0.24):
        out.append(box(name + "_bar_h", (cx, yy, z + 0.055), (w - 0.22, 0.05, 0.045), mat))
    return out


def banner(name, x, y, z_top, w, h, mat_cloth, mat_trim, mat_pole,
           yaw=0.0, tilt=0.0, swallow=True):
    """挂旗：横杆（埋进母件）+ 旗布 + 下摆金边。

    旗布用四边形轮廓拉伸 0.035 —— 燕尾缺口是真的轮廓，不是画上去的。
    """
    prof = [(-w * 0.5, 0.0), (w * 0.5, 0.0), (w * 0.5, -h * 0.78)]
    if swallow:
        prof += [(w * 0.26, -h), (0.0, -h * 0.80), (-w * 0.26, -h)]
    else:
        prof += [(w * 0.5, -h)]
    prof += [(-w * 0.5, -h * 0.78)]
    bar = box(name + "_bar", (x, y, z_top), (w + 0.16, 0.07, 0.07), mat_pole)
    bar.rotation_euler = (tilt, 0.0, yaw)
    cloth = extrude(name + "_cloth", prof, "Y", 0.035, (0, 0), mat_cloth)
    cloth.location = (x, y, z_top - 0.02)
    cloth.rotation_euler = (0.0, 0.0, yaw)
    trim = box(name + "_trim", (x, y, z_top - 0.10), (w * 0.98, 0.06, 0.05), mat_trim)
    trim.rotation_euler = (0.0, 0.0, yaw)
    return bar, cloth, trim


def log(name, p0, p1, r, mat, mat_end=None, segs=7, phase=0.0):
    """圆木：7 边形柱 + 两端亮色年轮面（端面是原木堆唯一的"识读面"）。"""
    a, b = Vector(p0), Vector(p1)
    d = b - a
    ln = d.length
    if ln < 1e-6:
        return []
    prof = [(r * math.cos(phase + TAU * i / segs),
             r * math.sin(phase + TAU * i / segs)) for i in range(segs)]
    ob = extrude(name, prof, "Y", ln, (0, 0), mat)
    ob.rotation_euler = d.normalized().to_track_quat("Y", "Z").to_euler()
    ob.location = (a + b) * 0.5
    out = [ob]
    if mat_end is not None:
        for s in (-1, 1):
            cap = extrude(name + "_end", prof, "Y", 0.014, (0, 0), mat_end)
            cap.rotation_euler = ob.rotation_euler
            cap.location = (a + b) * 0.5 + d.normalized() * (s * (ln * 0.5 - 0.004))
            out.append(cap)
    return out


def barrel(name, x, y, z0, r=0.30, h=0.74, mat=None, mat_hoop=None, segs=8):
    """酒桶：8 边形鼓身 + 两道铁箍 + 端面。"""
    M = L.all_materials()
    mat = mat or M["wood_mid"]
    mat_hoop = mat_hoop or M["bronze_dark"]
    out = [revolve(name + "_body",
                   [(0.0, 0.0), (r * 0.86, 0.0), (r * 1.00, h * 0.22),
                    (r * 1.06, h * 0.50), (r * 1.00, h * 0.78), (r * 0.86, h)],
                   segs, (x, y, z0), mat)]
    for zz in (h * 0.22, h * 0.78):
        out.append(tube_band(name + "_hoop", (x, y), r * 0.97, r * 1.08, z0 + zz - 0.035,
                             z0 + zz + 0.035, segs, mat_hoop))
    out.append(revolve(name + "_lid", [(0.0, 0.0), (r * 0.84, 0.0), (r * 0.84, 0.025)],
                       segs, (x, y, z0 + h), mat))
    return out


def crate(name, x, y, z0, s=0.62, h=0.50, mat=None, mat_edge=None):
    M = L.all_materials()
    mat = mat or M["wood_warm"]
    mat_edge = mat_edge or M["wood_dark"]
    out = [box(name + "_body", (x, y, z0 + h * 0.5), (s, s, h), mat)]
    for k, sz in enumerate((0.10, h - 0.10)):
        for sy in (-1, 1):
            out.append(box(name + "_edge", (x, y + sy * (s * 0.5 - 0.01),
                                           z0 + sz + k * 0.0015),
                           (s + 0.03, 0.05, 0.09), mat_edge))
    for sx in (-1, 1):
        out.append(box(name + "_edge", (x + sx * (s * 0.5 - 0.01), y, z0 + h * 0.5),
                       (0.05, s + 0.03, 0.09), mat_edge))
    return out


def mug(name, x, y, z0, r=0.05, h=0.10):
    M = L.all_materials()
    return [revolve(name + "_body", [(0.0, 0.0), (r, 0.0), (r, h * 0.9), (r * 0.86, h)],
                    6, (x, y, z0), M["wood_warm"]),
            ring_y(name + "_handle", (x + r, y, z0 + h * 0.5), r * 0.28, r * 0.52, 0.022,
                   6, M["wood_dark"])]


def pot(name, x, y, z0, r=0.16, h=0.20, mat=None):
    M = L.all_materials()
    mat = mat or M["copper"]
    return [revolve(name + "_body", [(0.0, 0.0), (r * 0.72, 0.0), (r, h * 0.55),
                                     (r * 0.92, h), (0.0, h)], 8, (x, y, z0), mat)]


# ── 火 ──────────────────────────────────────────────────────────────────────
def flame_tongue(name, x, y, z0, h, r, mat, lean=(0.0, 0.0), segs=7, phase=0.0):
    """一条火舌：底 → 鼓 → 收 → 尖。lean 让火舌往一侧卷（火不是一根锥子）。"""
    rings = [(0.0, 0.0, 0.0, 0.0),
             (r, h * 0.04, 0.0, 0.0),
             (r * 0.92, h * 0.30, lean[0] * 0.25, lean[1] * 0.25),
             (r * 0.66, h * 0.62, lean[0] * 0.62, lean[1] * 0.62),
             (r * 0.26, h * 0.86, lean[0] * 0.90, lean[1] * 0.90),
             (0.0, h, lean[0], lean[1])]
    ob = lathe(name, rings, segs, mat, phase=phase)
    ob.location.x += x
    ob.location.y += y
    ob.location.z += z0
    return ob


def flame(name, x, y, z0, h=0.55, r=0.20, seed=3):
    """一簇火：5 条外焰 + 3 条中焰 + 1 根芯焰。

    关键是**外焰要短、要散、要歪**：外焰高度只到芯焰的 1/2–2/3、半径压到 0.3–0.45r，
    火舌之间才留得出暗缝；否则几条同高的外焰会合成一块橙色板（C38 规则的复发）。
    """
    M = L.all_materials()
    rnd = random.Random(seed)
    out = []
    n = 5
    for i in range(n):
        a = TAU * i / n + rnd.uniform(-0.30, 0.30)
        d = r * rnd.uniform(0.48, 0.72)
        hh = h * rnd.uniform(0.34, 0.66)
        rr = r * rnd.uniform(0.26, 0.42)
        out.append(flame_tongue(
            "flame_out", x + d * math.cos(a), y + d * math.sin(a), z0,
            hh, rr, M["flame_out"],
            lean=(0.11 * math.cos(a), 0.11 * math.sin(a)),
            segs=7, phase=rnd.random()))
    for i in range(3):
        a = rnd.uniform(0, TAU)
        out.append(flame_tongue(
            "flame_in", x + 0.05 * math.cos(a), y + 0.05 * math.sin(a), z0,
            h * rnd.uniform(0.62, 0.80), r * 0.26, M["ember"],
            lean=(0.05 * math.cos(a), 0.05 * math.sin(a)), segs=7,
            phase=rnd.random()))
    out.append(flame_tongue("flame_core", x, y, z0, h, r * 0.15,
                            M["flame_in"], lean=(0.015, 0.010), segs=7))
    return out


def embers(name, x, y, z, n=5, spread=0.30, seed=5):
    """炭床：n 块大小不一的炭 + 一层压扁的灰。"""
    M = L.all_materials()
    rnd = random.Random(seed)
    out = [revolve(name + "_ash", [(0.0, 0.0), (spread * 1.25, 0.0),
                                   (spread * 1.10, 0.030), (0.0, 0.040)],
                   8, (x, y, z), M["ash"])]
    for i in range(n):
        a = TAU * rnd.random()
        d = spread * math.sqrt(rnd.random()) * 0.8
        s = 0.07 + 0.09 * rnd.random()
        out.append(box(name + "_coal", (x + d * math.cos(a), y + d * math.sin(a),
                                        z + 0.040 + 0.030 * rnd.random() + i * 0.0045),
                       (s, s * (0.74 + 0.12 * rnd.random()), s * 0.55),
                       M["coal"],
                       rot=(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3),
                            rnd.uniform(0, TAU))))
    return out


def candle(name, x, y, z0, h=0.16):
    """蜡烛：蜡身 + 芯焰（一根很小的亮舌）。"""
    M = L.all_materials()
    return [revolve(name + "_wax", [(0.0, 0.0), (0.026, 0.0), (0.025, h * 0.92),
                                    (0.0, h)], 6, (x, y, z0), M["cloth_cream"]),
            flame_tongue(name + "_flame", x, y, z0 + h, 0.075, 0.020,
                         M["flame_in"], segs=5)]


def arch_wall(name, cx, z_base, half, spring, z_top, thick, y0, mat, segs=9):
    """一段带半圆拱洞的墙（轮廓从拱脚起算，避免拱肩留三角洞）。"""
    prof = [(-half, z_top), (half, z_top), (half, z_base)]
    prof += [(half * math.cos(math.pi * s / segs),
              spring + half * math.sin(math.pi * s / segs)) for s in range(segs + 1)]
    prof += [(-half, z_base)]
    return extrude(name, prof, "Y", thick, (cx, 0), mat, offset=y0)


def arc_plate(name, cx, cz, r_in, r_out, a0, a1, z, mat, segs=10, thick=0.03):
    """水平放置的弧形条（符文环 / 地刻）。a0/a1 是弧度，z 是顶面。"""
    verts, faces = [], []
    for i in range(segs + 1):
        a = a0 + (a1 - a0) * i / segs
        ca, sa = math.cos(a), math.sin(a)
        verts += [(cx + r_in * ca, cz + r_in * sa, z),
                  (cx + r_out * ca, cz + r_out * sa, z),
                  (cx + r_out * ca, cz + r_out * sa, z - thick),
                  (cx + r_in * ca, cz + r_in * sa, z - thick)]
    for i in range(segs):
        b, b2 = i * 4, (i + 1) * 4
        faces += [(b + 1, b2 + 1, b2 + 2, b + 2), (b + 3, b2 + 3, b2 + 2, b + 3),
                  (b + 2, b2 + 2, b2 + 3, b + 3), (b + 0, b2 + 0, b2 + 1, b + 1)]
    faces += [(0, 1, 2, 3), ((segs * 4) + 3, (segs * 4) + 2, (segs * 4) + 1,
                             (segs * 4) + 0)]
    return mesh_obj(name, verts, faces, mat)
