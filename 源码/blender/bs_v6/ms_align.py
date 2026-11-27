"""
ms_align.py —— 神秘圣地的构件级"错位 / 穿模 / 共面 / 悬空"体检

    python build/bl_act.py act blender/bs_v6/ms_align.py

口径与 bs_align / br_align / th_align / wt_align / fm_align / lm_align 一致
（改口径必须同步改这里）：
  ① CLIP   两个构件的三角形真的相交（BVH.overlap）。分 cross（跨系统，必须修或白名单）
           与 inner（同系统内部，设计叠压）。
  ② CONTAIN  一个构件的包围盒整个落在另一个里。
  ③ COPLANAR 同向轴向面共面（距 < 4 mm、投影重叠 > 2 cm 见方）—— 会 z-fighting。
  ④ FLOAT   与所有构件都不相交、也不落地的构件。

白名单每一条都要有物理理由（这座建筑自己的结构关系）：
  · 三级台基逐级坐在下一级的压顶上；压顶盖住台身；
  · 门廊山门从地面砌起，后沿埋进圣所前墙、侧墙与台基相交（体块咬合）；
  · 台阶逐级压在夯土上、最后一级顶住山门门槛；
  · 圣所 12 面墙板在棱线处 6 cm 交叠（壁柱盖住接缝），墙根坐在天台面上；
  · 壁柱钉在墙面上、檐口压在墙顶与柱头上；
  · 龛框、龛台、拱券贴在墙面上（≤ 12 cm 嵌入）；
  · 发光门板嵌在墙洞里，铁栅压在门板前；
  · 山花压在门廊挑檐上，徽记贴在鼓室里；
  · 鼓座坐在圣所檐口顶上，穹顶坐在鼓座压顶上，采光亭坐在穹顶收分口上；
  · 天台晶体灯坐在檐口顶面、贴着鼓座壁；
  · 晶体长在碎石堆里、碎石堆落在夯土上；
  · 火盆 / 断碑 / 草簇 / 碎石落在场地或台基上；
  · 旗帜挂在山门正面的挑杆上，徽记贴在旗布上。
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
for mod in ("bslib", "br_model", "ms_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import ms_model  # noqa: E402

OUT = r"D:/测试一/docs/神秘圣地/v1/探针/align.txt"

SYSTEM = [
    ("yard", ("yard_", "rune_", "tuft", "rubble")),
    ("crys", ("crys_", "domecrys")),
    ("dais", ("dais_", "deck_")),
    ("bay", ("bay_", "step")),
    ("cella", ("cella_", "pil_", "cornice_", "niche_")),
    ("portal", ("portal_",)),
    ("ped", ("ped_",)),
    ("upper", ("drum", "dome_", "lan_", "spire_", "finial", "lamp_")),
    ("props", ("braz_", "stela")),
    ("herald", ("flag_", "crest_")),
]

LINK = [
    # 场地：一切落地件
    ("yard_", "yard_"), ("rune_", "yard_"), ("tuft", "yard_"), ("rubble", "yard_"),
    ("stela", "yard_"), ("braz_", "yard_"), ("crys_", "yard_"), ("crys_", "crys_"),
    # 台基：逐级叠压 + 压顶
    ("dais_", "dais_"), ("dais_", "yard_"), ("deck_", "dais_"),
    # 山门：从地面砌起、埋进圣所前墙、侧墙与台基相交；台阶顶住门槛
    ("bay_", "yard_"), ("bay_", "dais_"), ("bay_", "cella_"), ("bay_", "bay_"),
    ("step", "yard_"), ("step", "bay_"), ("step", "step"),
    # 圣所：墙板互相交叠、墙根坐台面、壁柱钉在墙上、檐口压在墙顶
    ("cella_", "cella_"), ("cella_", "dais_"), ("cella_", "deck_"), ("cella_", "bay_"),
    ("pil_", "cella_"), ("pil_", "dais_"),
    ("cornice_", "cella_"), ("cornice_", "pil_"),
    ("niche_", "cella_"),
    # 发光门：门板嵌在墙洞里，铁栅压在门板前
    ("portal_", "cella_"), ("portal_", "portal_"), ("portal_", "bay_"),
    # 山花压在门廊挑檐上
    ("ped_", "bay_"), ("ped_", "ped_"),
    # 鼓座 / 穹顶 / 采光亭
    ("drum", "cornice_"), ("drum", "drum"), ("dome_", "drum"), ("dome_", "dome_"),
    ("domecrys", "dome_"), ("domecrys", "drum"),
    ("lan_", "dome_"), ("lan_", "lan_"), ("spire_", "lan_"), ("spire_", "spire_"),
    ("finial", "spire_"), ("finial", "finial"),
    ("lamp_", "cornice_"), ("lamp_", "drum"),
    # 旗 / 徽记
    ("flag_", "bay_"), ("crest_", "flag_"), ("crest_", "ped_"),
]

VIA = [
    ("bay_pil", "bay_"), ("step", "dais_"), ("rune_head", "rune_bar"),
    ("lamp_", "dome_"),
]

SLAB = [
    ("niche_glow", "cella_"), ("drumwin_glass", "drum"), ("drumwin_back", "drum"),
    ("cella_stud", "cella_"), ("portal_glass", "cella_"),
    ("dome_boss", "dome_"), ("braz_flame", "braz_bowl"),
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
    m = ms_model.Model(False, unwrap=False).build()
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
        if n.startswith(("yard_soil", "yard_core", "dais_shaft", "dais_cap", "step")):
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
