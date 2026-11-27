"""
at_align.py —— 箭塔的构件级"错位 / 穿模 / 共面 / 悬空"体检（v2 冠部重做后的系统表）

    python build/bl_act.py act blender/bs_v6/at_align.py

口径与 bs_align / br_align / th_align / wt_align / fm_align / lm_align /
ms_align / sw_align 完全一致（改口径必须同步改这里）：
  ① CLIP   两个构件的三角形真的相交（BVH.overlap）。分 cross（跨系统，必须修或白名单）
           与 inner（同系统内部，设计叠压）。
  ② CONTAIN  一个构件的包围盒整个落在另一个里。
  ③ COPLANAR 同向轴向面共面（距 < 4 mm、投影重叠 > 2 cm 见方）—— 会 z-fighting。
  ④ FLOAT   与所有构件都不相交、也不落地的构件。

白名单每一条都要有物理理由（这座塔自己的结构关系）：
  · 台基坐在夯土上、踏步压在台基前脸、石基坐在台基压顶上；
  · 墙裙 / 线脚 / 扶壁 / 箭孔是"钉"在石面上的贴附件（≤ 30 mm 嵌入）；
  · 门扇嵌在门洞里、门楣梁压住门扇顶、拱内填石顶到拱腹；
  · 塔身下段坐石基压顶、隅石咬在上下两段墙的角上、托石顶住挑檐；
  · 石挑檐托住战棚地板、斜撑两端分别顶住塔身与地板底、封檐板包住地板断面；
  · 栏板坐在平台上、亭柱穿过栏板扶手落到地板、檐梁压在柱顶；
  · 檐口封板/压线包住屋面底边、戗脊压在屋面上、箭杆插进宝顶座；
  · 箭靶三脚 / 箭捆架 / 木桶 / 石堆落在地面，火盆 / 箭袋 / 备用箭落在平台。
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
for mod in ("bslib", "br_model", "wt_model", "at_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import at_model  # noqa: E402

OUT = r"D:/测试一/docs/箭塔/v2/探针/align.txt"

SYSTEM = [
    ("base", ("plinth", "step", "yard_soil", "yard_curb", "wall_")),
    ("stone", ("sb_", "bt_")),
    ("shaft", ("s1_", "s2_", "q_", "led_", "corb_")),
    ("gate", ("gate_",)),
    ("slot", ("slot",)),
    ("crown", ("deck_", "bkt_")),
    ("pav", ("rail_", "post_", "head_", "prop_", "quiver_", "banner_")),
    ("roof", ("eave_", "spire_")),
    ("arrow", ("arw_", "fl_")),
    ("yard", ("rack_", "pebble_", "tuft", "barrel_", "targ_")),
]

LINK = [
    # 场地 / 台基 / 石基
    ("sb_", "plinth"), ("sb_", "step"), ("sb_", "yard_"), ("sb_", "sb_"),
    ("bt_", "plinth"), ("bt_", "sb_"), ("bt_", "bt_"), ("bt_", "yard_"),
    ("wall_", "plinth"), ("wall_", "step"), ("wall_", "sb_"), ("wall_", "bt_"),
    ("wall_", "wall_"), ("wall_", "yard_"),
    # 门：门扇 / 门楣 / 拱内填石 / 门槛 / 拱券 / 拱心石
    ("gate_", "sb_"), ("gate_", "plinth"), ("gate_", "step"), ("gate_", "gate_"),
    ("gate_", "wall_"),
    # 箭孔：贴片钉在石墙 / 塔身上
    ("slot", "sb_"), ("slot", "s1_"), ("slot", "s2_"), ("slot", "gate_"),
    # 塔身：下段坐压顶、隅石咬墙、托石顶挑檐
    ("s1_", "sb_"), ("s1_", "sb_cap"), ("s1_", "bt_"), ("s1_", "s1_"),
    ("s2_", "s1_"), ("s2_", "s2_"), ("q_", "s2_"),
    ("led_", "s2_"), ("led_", "q_"), ("corb_", "s2_"), ("corb_", "led_"),
    # 战棚：挑檐 / 地板 / 封檐板 / 斜撑
    ("deck_", "s2_"), ("deck_", "led_"), ("bkt_", "s2_"), ("bkt_", "deck_"),
    ("bkt_", "led_"),
    # 亭：栏板坐平台、柱穿扶手、檐梁压柱
    ("rail_", "deck_"), ("post_", "deck_"), ("post_", "rail_"),
    ("head_", "post_"), ("prop_", "deck_"), ("prop_", "rail_"),
    ("quiver_", "deck_"), ("quiver_", "rail_"),
    # 屋顶：檐口包屋面、戗脊压屋面、箭杆插宝顶座
    ("eave_", "post_"), ("eave_", "head_"), ("eave_", "eave_"),
    ("spire_", "head_"), ("spire_", "spire_"), ("spire_", "eave_"),
    ("arw_", "spire_"), ("arw_", "arw_"), ("fl_", "arw_"), ("fl_", "fl_"),
    # 场地道具
    ("rack_", "yard_"), ("rack_", "rack_"), ("rack_", "wall_"),
    ("pebble_", "yard_"), ("tuft", "yard_"), ("barrel_", "yard_"),
    ("targ_", "yard_"), ("targ_", "targ_"), ("targ_", "wall_"),
]

VIA = []

SLAB = [
    ("slot", "sb_"), ("slot", "s1_"), ("slot", "s2_"),
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
    m = at_model.Model(False, unwrap=False).build()
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
    for c, a, b, sa, sb in clip_cross[:100]:
        P("%4d  %-24s(%s) <-> %-24s(%s)" % (c, a, sa, b, sb))
    P("=== CLIP_INNER %d (前 24) ===" % len(clip_inner))
    for c, a, b, sa, sb in clip_inner[:24]:
        P("%4d  %-24s <-> %s" % (c, a, b))
    P("=== CONTAIN %d ===" % len(contain))
    for a, b in contain[:40]:
        P("   %-24s  in  %s" % (a, b))
    up = [c for c in coplanar if c[3] == (2, 1)]
    P("=== COPLANAR_UP %d ===" % len(up))
    for a, b, d, k in up:
        P("   %-24s <-> %-24s  @%s d=%+.3f" % (a, b, k, d))
    P("=== COPLANAR %d ===" % len(coplanar))
    seen = set()
    for a, b, d, k in coplanar:
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        P("   %-24s <-> %-24s  @%s d=%+.3f" % (a, b, k, d))

    floaters = []
    for ob in items:
        n = ob.name
        if n.startswith(("plinth", "step", "pave", "curb", "land", "yard_soil")):
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
        P("   %-24s bb %s .. %s" % (n, lo, hi))
    P("DONE")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(buf))
    print("wrote", OUT, len(buf), "lines")
    print("\n".join(buf[:60]))


main()
