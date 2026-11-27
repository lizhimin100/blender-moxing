"""
fm_align.py —— 农场的构件级"错位 / 穿模 / 共面 / 悬空"体检

    python build/bl_act.py act blender/bs_v6/fm_align.py

口径与 bs_align / br_align / th_align 一致（改口径必须同步改这里）：
  ① CLIP   两个构件的三角形真的相交（BVH.overlap）。分 cross（跨系统，必须修或白名单）
           与 inner（同系统内部，设计叠压）。
  ② CONTAIN  一个构件的包围盒整个落在另一个里。
  ③ COPLANAR 同向轴向面共面（距 < 4 mm、投影重叠 > 2 cm 见方）—— 会 z-fighting。
  ④ FLOAT   与所有构件都不相交、也不落地的构件。

白名单每一条都要有物理理由（这套建筑自己的结构关系）：
  · 石基压顶压在石基上、线脚/隅石/门套"钉"在石面上（≤ 30 mm 嵌入）；
  · 木塔身上下段坐在石基压顶 / 挑台铺板上；
  · 挑台托梁插进塔身、斜撑两端分别顶住墙与平台底；
  · 栏板立柱坐在铺板上，扶手/横档横穿立柱；
  · 瞭望亭柱坐在铺板上、檐梁压在柱顶、屋面板压在檐梁/脊梁上、山墙压在屋面板端头；
  · 外梯斜梁两端分别搭在石台与挑台边缘、踏档钉在斜梁上；
  · 围栏立柱埋进场地的夯土、火盆/木桶/柴堆落在地面；
  · 徽记/旗帜/门楣匾是"贴"在布面或石面上的贴附件。
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
for mod in ("bslib", "br_model", "fm_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import fm_model  # noqa: E402

OUT = r"D:/测试一/docs/农场/v2/探针/align.txt"

SYSTEM = [
    ("base", ("plinth", "yard_", "path", "door_sill")),
    ("barn", ("barn_", "gable_", "front_", "vent_", "rafter_end")),
    ("roof", ("roof_",)),
    ("tower", ("tower_", "twin_", "tloop_")),
    ("shed", ("shed_", "tool_", "plinth_shed", "barrel_shed")),
    ("field", ("field_", "row", "wheat", "cabbage", "pumpkin")),
    ("well", ("well_",)),
    ("props", ("hay_", "trough", "cart_", "barrel_a", "barrel_b",
               "plank_loose", "pebble", "tuft")),
    ("fence", ("fence_", "field_gate", "gate_post")),
    ("gate", ("gate_",)),
    ("window", ("win",)),
    ("herald", ("crest_",)),
]

LINK = [
    # 谷仓：墙 / 山墙 / 石基 / 墙裙 / 腰梁 / 立柱 / 门套 / 门窗 互相咬合
    ("barn_gable", "barn_"), ("barn_gable", "barn_back"), ("barn_gable", "barn_front"),
    ("barn_gable", "barn_dado"), ("barn_back", "barn_dado"), ("barn_front", "barn_dado"),
    ("barn_rail", "barn_"), ("barn_rail", "barn_gable"), ("barn_rail", "barn_col"),
    ("barn_rail", "barn_front"), ("barn_col", "barn_"), ("barn_col", "barn_gable"),
    ("gable_stud", "barn_gable"), ("gable_stud", "barn_dado"),
    ("gable_brace", "barn_gable"), ("gable_brace", "barn_dado"),
    ("front_stud", "barn_front"), ("front_stud", "barn_dado"),
    ("front_brace", "barn_front"), ("front_x", "barn_front"), ("front_x", "front_stud"),
    ("front_mid", "barn_front"), ("front_mid", "front_x"),
    ("gate_", "barn_front"), ("gate_", "gate_"), ("gate_", "front_brace"),
    ("gate_", "barn_floor_in"), ("gate_", "hay_inside"), ("gate_", "path"),
    ("barn_floor_in", "hay_inside"), ("gate_", "yard_"), ("roof_", "crest_"),
    ("gate_", "gate_step"),
    ("gate_", "front_stud"), ("gate_", "barn_dado"),
    ("win", "barn_"), ("win", "barn_gable"), ("win", "barn_rail"),
    ("win_front", "barn_front"), ("win_front", "front_brace"),
    ("side_door", "barn_"), ("crest_", "barn_front"), ("crest_", "gate_"), ("crest_", "front_mid"),
    # 屋面：压在墙顶 / 山墙 / 檐口上，通风百叶与椽头钉在坡面上
    ("roof_", "barn_"), ("roof_patch", "roof_"), ("roof_", "barn_gable"), ("roof_", "barn_front"),
    ("roof_", "barn_back"), ("roof_", "barn_rail"),
    ("vent_", "roof_"), ("rafter_end", "roof_"), ("rafter_end", "barn_front"),
    ("roof_", "vent_"),
    # 筒仓：箍 / 锥顶 / 门 / 窗 / 爬梯 都长在筒身上
    ("tower_", "tower_"), ("tower_", "twin_"), ("tower_", "tloop_"),
    ("tower_", "plinth"), ("tower_", "barn_"), ("tower_", "roof_"),
    ("tower_", "yard_"), ("tower_", "fence_"),
    # 披屋：后墙贴谷仓左墙，屋面压墙与柱
    ("shed_", "plinth_shed"), ("shed_", "barn_"), ("shed_", "barn_gable"),
    ("shed_roof", "shed_"), ("shed_rib", "shed_roof"), ("shed_rib", "shed_post"),
    ("shed_fascia", "shed_roof"), ("shed_post", "plinth_shed"),
    ("shed_post_band", "shed_post"), ("shed_post", "shed_"),
    ("tool_", "plinth_shed"), ("tool_", "shed_"), ("barrel_shed", "plinth_shed"),
    ("shed_hay", "plinth_shed"),
    # 田垄：作物长在垄上、垄压在场地上
    ("row", "field_base"), ("wheat", "row"), ("cabbage", "row"), ("pumpkin", "row"),
    ("row_end", "row"), ("row", "yard_"), ("field_base", "yard_"),
    ("pumpkin_vine", "row"), ("pumpkin_stem", "pumpkin"), ("cabbage_in", "cabbage"),
    ("wheat_tip", "wheat"),
    # 井 / 槽 / 草垛 / 板车
    ("well_", "yard_"), ("well_", "well_"), ("trough", "yard_"),
    ("hay_", "yard_"), ("hay_rope", "hay_"), ("hay_top", "hay_"),
    ("cart_", "yard_"), ("cart_", "cart_"), ("barrel_a", "yard_"),
    ("barrel_b", "yard_"), ("plank_loose", "yard_"), ("pebble", "yard_"),
    ("tuft", "yard_"), ("door_sill", "plinth"), ("door_sill", "barn_"),
    ("path", "yard_"),
    # 围栏：石座埋进场地、柱与横杆互咬、门挂在门柱上
    ("fence_", "yard_"), ("fence_", "fence_"), ("fence_", "plinth"),
    ("field_gate", "fence_"), ("field_gate", "gate_post"), ("field_gate", "field_gate"),
    ("gate_post", "fence_"), ("gate_post", "yard_"), ("gate_post_cap", "gate_post"),
    ("gate_post_band", "gate_post"), ("fence_base", "yard_"), ("fence_base_f", "yard_"),
    ("field_gate_rail", "field_gate_leaf"), ("field_gate_brace", "field_gate_leaf"),
    # 场地自身的分层：披屋地坪与谷仓石台是两块相接的台（不是错位）
    ("plinth", "yard_"), ("plinth_shed", "yard_"), ("yard_curb", "yard_"),
    ("plinth_shed", "plinth"), ("plinth", "plinth_shed"),
    ("plinth", "shed_"), ("plinth", "side_door"), ("plinth", "gate_"),
    ("plinth", "front_"), ("plinth", "cart_"), ("plinth", "tool_"),
    ("plinth", "hay_"),
    ("fence_l", "fence_f"), ("fence_f", "fence_l"),
    ("plinth", "barn_"), ("plinth", "tower_"),
]

VIA = [
    ("barn_", "plinth"), ("tower_", "plinth"), ("roof_", "barn_"),
    ("gate_", "barn_front"), ("win", "barn_"), ("fence_", "yard_"),
]

SLAB = [
    ("crest_", "barn_front"), ("crest_", "gate_"), ("vent_", "roof_"),
    ("win", "barn_gable"), ("roof_", "barn_"),
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
    m = fm_model.Model(False, unwrap=False).build()
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
    print("\n".join(buf[:40]))


main()
