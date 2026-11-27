"""
lm_align.py —— 伐木场的构件级"错位 / 穿模 / 共面 / 悬空"体检

    python build/bl_act.py act blender/bs_v6/lm_align.py

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
for mod in ("bslib", "br_model", "lm_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import lm_model  # noqa: E402

OUT = r"D:/测试一/docs/伐木场/v1/探针/align.txt"

SYSTEM = [
    ("base", ("yard_", "plinth", "rail_")),
    ("frame", ("post_", "beam_", "wall_", "bench_", "tool_")),
    ("roof", ("roof_", "rafter_")),
    ("hut", ("hut_", "win_hut")),
    ("saw", ("saw_",)),
    ("timber", ("timber_",)),
    ("cart", ("cart_", "barrow_")),
    ("wheel", ("wheel_",)),
    ("props", ("sawdust", "plank_", "tuft", "rubble", "barrel_")),
    ("herald", ("flag_", "banner_", "crest_")),
]

LINK = [
    # 场地：柱脚 / 石基 / 轨道都压在夯土上
    ("post_", "yard_"), ("post_", "post_foot"), ("rail_", "yard_"),
    ("wall_", "yard_"), ("wall_", "wall_"), ("bench_", "yard_"),
    ("beam_", "post_"), ("beam_mid", "post_"), ("beam_eave", "post_"),
    ("post_brace", "post_"), ("post_brace", "beam_eave"),
    ("post_", "beam_"), ("post_band", "post_"), ("post_band_t", "post"),
    ("post_corner", "post_"), ("post_corner_band", "post_corner"),
    # 屋面压在檐梁 / 墙顶 / 椽条上
    ("roof_", "beam_"), ("roof_", "wall_"), ("roof_", "post_"),
    ("roof_", "roof_"), ("roof_rafter", "roof_"), ("rafter_end", "roof_"),
    ("roof_seam_end", "roof_"), ("roof_light", "roof_"),
    # 小屋：墙 / 石基 / 门窗 / 腰线互咬
    ("hut_", "hut_"), ("hut_", "yard_"), ("hut_", "wall_"), ("hut_", "roof_"),
    ("hut_", "beam_eave"), ("hut_stud", "hut_side"), ("hut_rail", "hut_side"),
    ("hut_stone", "hut_"), ("win_hut", "hut_"), ("win_hut", "hut_side"),
    ("hut_jamb", "hut_front"), ("hut_head", "hut_front"), ("hut_door", "hut_"),
    # 锯架：柱脚 / 柱身 / 横梁 / 雨棚 / 锯条 / 方木
    ("saw_", "saw_"), ("saw_", "yard_"), ("saw_", "rail_"),
    ("saw_post", "saw_foot"), ("saw_head", "saw_post"), ("saw_band", "saw_post"),
    ("saw_roof", "saw_head"), ("saw_ridge", "saw_roof"),
    ("saw_blade", "saw_head"), ("saw_grip", "saw_blade"), ("saw_tie", "saw_grip"),
    ("saw_tooth", "saw_blade"), ("saw_hook", "saw_head"),
    ("saw_rag", "saw_hook"), ("saw_beam", "rail_"), ("saw_plank", "saw_beam"),
    # 原木堆：原木压垫木、端面盘与年轮贴在原木上
    ("timber_", "timber_"), ("timber_", "yard_"), ("timber_", "timber_sleeper"),
    ("timber_face", "timber_bark"), ("timber_ring", "timber_face"),
    ("timber_pith", "timber_face"), ("timber_bark", "timber_sleeper"),
    # 台车 / 飞轮 / 手推车
    ("cart_", "rail_"), ("cart_", "cart_"), ("barrow_", "yard_"),
    ("barrow_", "barrow_"), ("wheel_", "yard_"), ("wheel_", "wheel_"),
    ("wheel_spoke", "wheel_hub"), ("wheel_leg", "wheel_"), ("wheel_base", "yard_"),
    # 杂物 / 旗
    ("sawdust", "yard_"), ("plank_", "yard_"), ("tool_", "yard_"),
    ("tool_", "hut_"), ("tuft", "yard_"), ("rubble", "yard_"),
    ("barrel_", "yard_"), ("flag_", "post_"), ("banner_", "wall_"),
    ("crest_", "wall_"), ("crest_", "hut_"), ("crest_", "banner_"),
]

VIA = [
    ("roof_", "beam_eave"), ("hut_", "beam_eave"), ("wall_", "yard_"),
    ("saw_", "yard_"), ("timber_", "yard_"),
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
    m = lm_model.Model(False, unwrap=False).build()
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
