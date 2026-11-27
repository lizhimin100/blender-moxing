"""
sw_align.py —— 蒸汽车坊 v2 的构件级"错位 / 穿模 / 共面 / 悬空"体检

    python build/bl_act.py act blender/bs_v6/sw_align.py

口径与 bs_align / br_align / th_align / wt_align / fm_align / lm_align / ms_align 一致
（改口径必须同步改这里）：
  ① CLIP   两个构件的三角形真的相交（BVH.overlap）。分 cross（跨系统，必须修或白名单）
           与 inner（同系统内部，设计叠压）。
  ② CONTAIN  一个构件的包围盒整个落在另一个里。
  ③ COPLANAR 同向轴向面共面（距 < 4 mm、投影重叠 > 2 cm 见方）—— 会 z-fighting。
  ④ FLOAT   与所有构件都不相交、也不落地的构件。

白名单每一条都要有物理理由（这座建筑自己的结构关系）：
  · 台基坐在夯土上；压顶压在台基上；墙体坐在压顶上；门槛压在台阶与墙脚上；
  · 立面木构（压梁 / 封檐板 / 扶壁 / 窗框）钉在石墙上；
  · 屋面坐在两侧墙顶；山墙三角形压进墙顶 4 cm；封檐板包住屋面端头；
  · 门洞两侧墙墩 + 拱上墙板围出洞口；门扇铰在门洞里；门厅内壁藏在墙厚里；
  · 锅炉房贴着车间右墙砌；烟囱从地面砌起、穿过锅炉房屋面；
  · 立式锅炉立在锅炉房地面上、穿过屋面；蒸汽管进车间墙；烟道接烟囱；
  · 保温主管用抱箍挂在锅炉房外墙上；
  · 天窗 / 补丁压在瓦面上；风向标坐在脊上；排气塔（本轮无）—— 脊帽压在屋面上；
  · 吊装梁插进山墙；斜撑顶在墙面；滑轮 / 链 / 钩挂在梁端；
  · 旗帜挂在压梁上、徽记贴在旗面 / 盾面上；
  · 道具（煤堆 / 煤袋 / 水桶 / 木箱 / 煤仓 / 铁锹）落在场地或贴着墙。
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "br_model", "sw_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import sw_model  # noqa: E402

OUT = r"D:/测试一/docs/蒸汽车坊/v3/探针/align.txt"

SYSTEM = [
    ("yard", ("yard_", "step")),
    ("hall", ("hall_", "win_")),
    ("door", ("door_",)),
    ("roof", ("roof_",)),
    ("gab", ("gab_",)),
    ("ann", ("ann_",)),
    ("chim", ("chim_",)),
    ("boil", ("boil_",)),
    ("pipe", ("pipe_",)),
    ("crane", ("crane_",)),
    ("prop", ("prop_", "tuft", "rubble")),
    ("her", ("her_",)),
]

LINK = [
    # 场地
    ("yard_", "yard_"), ("step", "yard_"), ("step", "step"), ("step", "hall_"),
    # 主体：台基 / 墙 / 山墙 / 压梁 / 封檐板 / 扶壁
    ("hall_", "hall_"), ("hall_", "yard_"),
    # 窗
    ("win_", "hall_"),
    # 屋面
    ("roof_", "hall_"), ("roof_", "roof_"),
    # 门洞 / 门厅 / 门扇
    ("door_", "hall_"), ("door_", "door_"), ("door_", "step"), ("door_", "yard_"),
    # 山墙木构
    ("gab_", "hall_"), ("gab_", "roof_"), ("gab_", "gab_"),
    # 徽记压在压梁上
    ("her_", "gab_"),
    # 锅炉房
    ("ann_", "yard_"), ("ann_", "ann_"), ("ann_", "hall_"),
    # 烟囱穿锅炉房
    ("chim_", "yard_"), ("chim_", "ann_"), ("chim_", "hall_"),
    # 锅炉穿锅炉房屋面
    ("boil_", "ann_"), ("boil_", "boil_"),
    # 管道：蒸汽管进车间墙 / 烟道接烟囱 / 主管挂在外墙
    ("pipe_", "ann_"), ("pipe_", "hall_"), ("pipe_", "chim_"), ("pipe_", "boil_"),
    ("pipe_", "pipe_"),
    # 吊装梁插进山墙
    ("crane_", "hall_"), ("crane_", "crane_"),
    # 道具
    ("prop_", "yard_"), ("prop_", "hall_"), ("prop_", "ann_"), ("prop_", "prop_"),
    ("tuft", "yard_"), ("rubble", "yard_"), ("tuft", "prop_"), ("rubble", "prop_"),
    # 旗 / 徽记
    ("her_", "hall_"), ("her_", "her_"),
]

VIA = [("hall_butt", "hall_"), ("win_", "hall_"), ("prop_bunker", "ann_"),
       ("ann_firebox", "ann_")]

SLAB = [
    ("door_glow", "door_"), ("door_forge", "door_"),
    ("ann_fire_glow", "ann_"), ("ann_fire_glow_core", "ann_"),
    ("ann_fire_grate", "ann_"), ("ann_fire_bezel", "ann_"),
    ("ann_ash_slot", "ann_"), ("ann_port_glass", "ann_"), ("ann_port_rim", "ann_"),
    ("win_", "hall_"), ("roof_sky", "roof_"), ("roof_patch", "roof_"),
]

CREST_SUF = ("_edge", "_rim", "_field", "_band", "_spike0", "_spike1", "_spike2",
             "_gem0", "_gem1", "_gem2")


def crest_base(n):
    for suf in CREST_SUF:
        if n.endswith(suf):
            return n[:-len(suf)]
    return None


def crest_pair(a, b):
    ba = crest_base(a)
    return ba is not None and ba == crest_base(b)


def sys_of(name):
    for tag, keys in SYSTEM:
        for k in keys:
            if name.startswith(k):
                return tag
    return "other"


def bvh_of(ob):
    me = ob.data
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys, all_triangles=False)


def bb_of(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def bb_hit(a, b, pad=0.0):
    return all(a[0][i] - pad <= b[1][i] and b[0][i] - pad <= a[1][i] for i in range(3))


def bb_inside(a, b, pad=0.005):
    return all(a[0][i] >= b[0][i] - pad and a[1][i] <= b[1][i] + pad for i in range(3))


def allowed(a, b):
    for pa, pb in LINK + VIA + SLAB:
        if (a.startswith(pa) and b.startswith(pb)) or (b.startswith(pa) and a.startswith(pb)):
            return True
    return False


def axial_faces(ob, q=0.02):
    out = []
    mw = ob.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    me = ob.data
    for p in me.polygons:
        n = (nm @ p.normal).normalized()
        for axis in range(3):
            for sgn in (-1, 1):
                if abs(n[axis] - sgn) < q:
                    pts = [mw @ me.vertices[i].co for i in p.vertices]
                    d = sum(q2[axis] for q2 in pts) / len(pts)
                    others = [i for i in range(3) if i != axis]
                    o0 = (min(q2[others[0]] for q2 in pts), max(q2[others[0]] for q2 in pts))
                    o1 = (min(q2[others[1]] for q2 in pts), max(q2[others[1]] for q2 in pts))
                    out.append(((axis, sgn), d, (o0[0], o0[1], o1[0], o1[1])))
                    break
            else:
                continue
            break
    return out


def main():
    buf = []

    def P(*a):
        buf.append(" ".join(str(x) for x in a))

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    m = sw_model.Model(False, unwrap=False).build()
    bpy.context.view_layer.update()
    items = [it[0] for it in m.items]
    P("ITEMS", len(items))

    bbs = {ob.name: bb_of(ob) for ob in items}
    trees = {}
    for ob in items:
        try:
            trees[ob.name] = bvh_of(ob)
        except Exception:
            pass

    clip_cross, clip_inner, contain, coplanar = [], [], [], []
    for i, a in enumerate(items):
        na = a.name
        for b in items[i + 1:]:
            nb = b.name
            if na in nb or nb in na:
                continue
            if not bb_hit(bbs[na], bbs[nb], 0.001):
                continue
            ov = trees[na].overlap(trees[nb]) if na in trees and nb in trees else []
            if ov:
                rec = (len(ov), na, nb, sys_of(na), sys_of(nb))
                if allowed(na, nb) or sys_of(na) == sys_of(nb):
                    clip_inner.append(rec)
                else:
                    clip_cross.append(rec)
            if not crest_pair(na, nb):
                if bb_inside(bbs[na], bbs[nb]):
                    contain.append((na, nb))
                elif bb_inside(bbs[nb], bbs[na]):
                    contain.append((nb, na))
            fa, fb = axial_faces(a), axial_faces(b)
            for (ka, da, ba) in fa:
                for (kb, db, bb2) in fb:
                    if ka != kb or abs(da - db) > 0.004:
                        continue
                    ow = min(ba[1], bb2[1]) - max(ba[0], bb2[0])
                    oh = min(ba[3], bb2[3]) - max(ba[2], bb2[2])
                    if ow > 0.02 and oh > 0.02 and ow * oh > 0.0004:
                        coplanar.append((na, nb, round(da, 3), ka))

    clip_cross.sort(reverse=True)
    P("=== CLIP_CROSS %d ===" % len(clip_cross))
    for c, a, b, sa, sb in clip_cross[:120]:
        P("%4d  %-26s(%s) <-> %-26s(%s)" % (c, a, sa, b, sb))
    P("=== CLIP_INNER %d (前 24) ===" % len(clip_inner))
    for c, a, b, sa, sb in clip_inner[:24]:
        P("%4d  %-26s <-> %s" % (c, a, b))
    P("=== CONTAIN %d ===" % len(contain))
    for a, b in contain[:40]:
        P("   %-26s  in  %s" % (a, b))
    up = [c for c in coplanar if c[3] == (2, 1)]
    P("=== COPLANAR_UP %d ===" % len(up))
    for a, b, d, k in up[:80]:
        P("   %-26s <-> %-26s  @%s d=%+.3f" % (a, b, k, d))
    P("=== COPLANAR %d ===" % len(coplanar))
    seen = set()
    for a, b, d, k in coplanar:
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        P("   %-26s <-> %-26s  @%s d=%+.3f" % (a, b, k, d))

    floaters = []
    for ob in items:
        n = ob.name
        if n.startswith(("yard_soil", "hall_plinth", "ann_plinth",
                         "chim_base", "step")):
            continue
        lo, hi = bbs[n]
        if lo.z < 0.02:
            continue
        hit = False
        for other in items:
            if other.name == n:
                continue
            if bb_hit(bbs[n], bbs[other.name], 0.005):
                hit = True
                break
        if not hit:
            floaters.append((n, tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi)))
    P("=== FLOAT %d ===" % len(floaters))
    for n, lo, hi in floaters[:40]:
        P("   %-26s bb %s .. %s" % (n, lo, hi))
    P("DONE")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(buf))
    print("wrote", OUT, len(buf), "lines")
    print("\n".join(buf[:70]))


main()
