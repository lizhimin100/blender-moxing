"""
th_align.py —— 城镇大厅的构件级"错位 / 穿模 / 共面 / 悬空"体检

    python build/bl_act.py act blender/bs_v6/th_align.py

口径与 bs_align / br_align 一致（改口径必须同步改这里，否则报告没有可比性）：
  ① CLIP   两个构件的三角形真的相交（BVH.overlap）。分 cross（跨系统，必须修或白名单）
           与 inner（同系统内部，设计叠压）。
  ② CONTAIN  一个构件的包围盒整个落在另一个里。
  ③ COPLANAR 同向轴向面共面（距 < 4 mm、投影重叠 > 2 cm 见方）—— 会 z-fighting。
  ④ FLOAT   与所有构件都不相交、也不落地的构件。

白名单每一条都要有物理理由（这套建筑自己的结构关系）：
  · v3 的钟塔是"骑在屋脊上的石座"—— 塔座必然穿过主屋面（前坡 + 后坡）；
  · 钟亭坐在塔身顶、穹顶坐在钟座上、采光亭坐在穹顶顶；
  · 山花是"穿屋面的三角墙"—— 与主屋面 / 檐口 / 墙顶必然相交；
  · 拱门套 / 钟面 / 色带 / 盾徽 / 壁柱 / 隅石 都是"钉"在石面上的贴附件（≤ 30 mm 嵌入）；
  · 翼楼屋面内侧贴在主楼外墙上（这一侧不做封檐）。
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
for mod in ("bslib", "br_model", "th_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import th_model  # noqa: E402

OUT = r"D:/测试一/docs/城镇大厅/v3/探针/align.txt"

SYSTEM = [
    ("base", ("plinth", "apron", "step", "cheek", "newel", "threshold")),
    ("roof", ("roof_", "tile_", "eave_", "ridge_", "hip", "chimney")),
    ("tower", ("tw_", "bf_", "dm_", "lantern_", "sp_", "flag", "clock_")),
    ("window", ("win", "oculus")),
    ("gate", ("gate_", "sconce_")),
    ("gable", ("gable_",)),
    ("herald", ("band_", "crest_", "wing_band", "wing_trim")),
    ("prop", ("tuft", "pebble")),
    ("wing", ("wing_",)),
    ("wall", ("mass", "dado", "string", "corn_", "quoin", "dentil", "pil_",
              "modil")),
]

LINK = [
    # 塔座骑在屋脊上：与主屋面、正脊、瓦垄、檐口必然相交
    ("tw_", "roof_"), ("tw_", "tile_"), ("tw_", "ridge_"), ("tw_", "hip"),
    ("tw_", "eave_"), ("tw_", "mass"), ("tw_", "corn_"), ("tw_", "band_"),
    ("tw_", "dentil"), ("tw_", "pil_"), ("tw_", "chimney"),
    # 塔座上的色带 / 壁柱 / 小尖塔 / 塔身 / 钟亭 / 穹顶 / 采光亭 是一组
    ("tw_", "tw_"), ("tw_", "bf_"), ("tw_", "dm_"), ("tw_", "lantern_"),
    ("tw_", "sp_"), ("tw_", "flag"), ("tw_", "clock_"),
    ("bf_", "dm_"), ("bf_", "lantern_"), ("bf_", "sp_"), ("bf_", "clock_"),
    ("bf_", "flag"), ("dm_", "lantern_"), ("dm_", "sp_"), ("lantern_", "sp_"),
    ("sp_", "flag"), ("flag", "crest_"),
    # 主屋面 / 封檐 / 压条 / 戗脊 / 瓦垄 / 烟囱
    ("roof_", "mass"), ("roof_", "corn_"), ("roof_", "eave_"), ("roof_", "tile_"),
    ("roof_", "hip"), ("roof_", "ridge_"), ("roof_", "chimney"),
    ("eave_", "corn_"), ("eave_", "mass"), ("eave_", "dentil"),
    ("ridge_", "tile_"), ("hip", "tile_"), ("chimney", "roof_"),
    # 山花：三角墙穿过主屋面、压在檐口上
    ("gable_", "mass"), ("gable_", "roof_"), ("gable_", "tile_"),
    ("gable_", "corn_lip"), ("gable_", "corn_"), ("gable_", "modil"),
    # 山花穿屋面，嵌在山花里的盾徽必然同时碰到瓦面
    ("crest_", "roof_"), ("crest_", "tile_"),
    ("gable_", "corn_"), ("gable_", "eave_"), ("gable_", "crest_"),
    ("gable_", "band_"), ("gable_", "pil_"),
    # 翼楼：屋面内侧贴主楼外墙；翼檐口压在翼墙上
    ("wing_roof", "mass"), ("wing_roof", "corn_"), ("wing_roof", "wing_mass"),
    ("wing_roof", "roof_"), ("wing_roof", "eave_"),
    ("wing_eave", "wing_mass"), ("wing_eave", "mass"), ("wing_eave", "roof_"),
    ("wing_ridge", "wing_roof"), ("wing_hip", "wing_roof"),
    ("wing_tile", "wing_roof"), ("wing_pil", "wing_mass"),
    ("wing_band", "wing_mass"), ("wing_band", "mass"), ("wing_trim", "wing_mass"),
    ("wing_dado", "wing_mass"), ("wing_dado", "mass"),
    ("wing_mass", "mass"), ("wing_mass", "plinth"), ("wing_mass", "dado"),
    ("wing_mass", "band_"), ("wing_mass", "string"),
    # 转角砌体咬合：翼的墙裙 / 色带与主楼的对应线脚必须叠在一起，
    # 否则转角处会露出一道缺口（这是砌体关系，不是错位）
    ("dado_cap", "wing_dado"), ("plinth_cap", "wing_dado"),
    ("plinth_mid", "wing_dado"), ("string", "wing_band"), ("band_m", "wing_band"),
    ("band_t", "wing_trim"), ("corn_", "hip"), ("crest_", "eave_"),
    # 窗：嵌进主楼 / 翼楼外墙
    ("win", "mass"), ("win", "wing_mass"), ("win", "corn_"), ("win", "string"),
    ("win", "band_"), ("win", "quoin"), ("win_slit", "mass"),
    ("oculus", "mass"),
    # 门套 / 门扇 / 扇窗 / 壁灯
    ("gate_", "mass"), ("gate_", "dado"), ("gate_", "band_"), ("gate_", "step"),
    ("gate_", "plinth"), ("gate_", "threshold"), ("gate_", "pil_"),
    ("gate_", "sconce_"), ("sconce_", "mass"), ("sconce_", "pil_"),
    # 线脚 / 隅石 / 齿饰 / 壁柱 钉在墙上
    ("band_", "mass"), ("band_", "quoin"), ("band_", "pil_"), ("band_", "dentil"),
    ("dado", "mass"), ("dado_cap", "mass"), ("string", "mass"), ("string2", "mass"),
    ("corn_", "mass"), ("corn_", "dentil"), ("dentil", "mass"),
    ("quoin", "mass"), ("pil_", "mass"), ("pil_", "corn_"), ("pil_", "string"),
    ("pil_", "band_"), ("pil_", "pil_"), ("crest_", "mass"),
    # 石台 / 台阶 / 散水 / 端柱
    ("plinth_cap", "mass"), ("plinth_cap", "wing_mass"), ("plinth", "mass"),
    ("plinth", "wing_mass"), ("plinth", "dado"), ("plinth", "apron"),
    ("apron", "plinth"), ("step", "plinth"), ("step", "cheek"), ("step", "gate_"),
    ("cheek", "step"), ("cheek", "plinth"), ("cheek_cap", "cheek"),
    ("newel", "step"), ("newel", "cheek"), ("newel", "plinth"),
    ("threshold", "mass"), ("threshold", "gate_"), ("threshold", "step"),
    ("tuft", "apron"), ("tuft", "step"), ("pebble", "apron"), ("pebble", "step"),
]
VIA = [
    ("tw_", "mass"), ("tw_", "roof_"), ("gable_", "roof_"), ("wing_roof", "mass"),
    ("win", "mass"), ("oculus", "mass"), ("gate_", "mass"),
    ("wing_band", "wing_mass"), ("band_", "mass"),
]
SLAB = [
    ("crest_", "gable_"), ("crest_", "flag"), ("band_", "mass"),
    ("gate_", "mass"), ("eave_", "roof_"),
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
    m = th_model.Model(False, unwrap=False).build()
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
        if n.startswith(("plinth", "step", "pave", "curb", "land")):
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
    print("\n".join(buf[:20]))


main()
