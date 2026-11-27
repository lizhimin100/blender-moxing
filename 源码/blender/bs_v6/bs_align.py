"""
bs_align.py —— 铁匠铺 v10 的构件级"错位 / 穿模 / 共面 / 悬空"体检

    python build/bl_act.py act blender/bs_v6/bs_align.py

口径与兵营 v4 的 br_align.py **完全一致**（改口径必须同步改两处，否则两份报告不可比）：

  ① CLIP   两个构件的三角形真的相交（BVH.overlap）。
           分两类打印：
             cross  —— 跨"系统"（屋面 / 墙 / 坡棚 / 烟囱 / 门廊 / 纹章 / 道具…），
                       这一类才是"错位"嫌疑，必须逐条修或写进白名单；
             inner  —— 同一系统内部（瓦垄压屋面、铁箍套筒身、纹章贴在布上），
                       属于设计叠压，只统计不逐条报。
  ② CONTAIN  A 的世界包围盒整个落在 B 的包围盒内（八向都留 5 mm 余量）。
             BVH 查不出"完全埋进去"（面不相交），这一类专门抓"旗杆埋进梁里"这种。
  ③ COPLANAR 两个构件的**轴向面**共面（法线同为 ±X/±Y/±Z，平面距 < 4 mm），
             且投影重叠 > 0.02 m²。这类不一定有体积重叠，但会在视口/引擎里闪（z-fighting）。
             投影用**真实顶点**算，不用 sqrt(area) 估 —— 旧口径的假阳性一半来自这里。
  ④ FLOAT    构件的包围盒与其它所有构件都不相交（5 mm 容差），也不是落地件。
             抓"悬在半空的构件"。

白名单（LINK / VIA / SLAB）写在下面，每条都要有物理理由：
  LINK —— 连接件：铁件钉进木梁、挂钩包住杆、箍套住筒身（≤ 30 mm 嵌入）
  VIA  —— 必须穿过：烟管穿屋面、椽条入梁、锚栓入墙
  SLAB —— 贴附装饰：纹章/金边/铁箍压在布或石面上（≤ 25 mm 嵌入）
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "bs_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import bs_model  # noqa: E402

# ── 系统划分（按名字前缀，长前缀优先）────────────────────────────────────────
SYSTEM = [
    ("base", ("plinth", "yard", "pave", "threshold", "coal_spill", "coal_bin",
              "coal_bin_lump", "tuft", "rubble", "plank_loose")),
    ("wall", ("mass", "quoin", "dado", "string", "buttress")),
    ("forge", ("forge", "bay_", "hearth", "hood", "flame", "flametip", "coal_bed",
               "coal_lump", "grate", "fire_wash")),
    ("canopy", ("canopy", "vent_", "flue_")),
    ("chimney", ("ch_", "vane")),
    ("roof", ("roof_", "course", "ridge", "fascia", "eave_", "barge", "rafter",
              "cupola", "cup_", "std_", "gable_", "collar", "stud", "brace", "king_")),
    ("wing", ("wing_", "door_")),
    ("porch", ("porch_",)),
    ("window", ("winL", "winR")),
    ("herald", ("shield", "wbanner", "banner", "kite", "crest", "emblem")),
    ("detail", ("sign_", "lan_", "corbel")),
    ("prop", ("anvil", "tool", "weapon", "sword", "axe", "bellows", "quench",
              "bucket", "coal_a", "coal_b", "ingots", "grindstone", "gs_", "log",
              "pot_", "rack_")),
]

# 允许的叠压（(a 前缀, b 前缀) 双向匹配）
LINK = [
    # 地面 / 基座：所有落地件都"埋"进石台或夯土 5–15 cm（防悬空、防漏光）
    ("plinth", "mass"), ("plinth", "quoin"), ("plinth", "dado"), ("plinth", "string"),
    ("plinth", "buttress"), ("plinth", "wing_"), ("plinth", "ch_"), ("plinth", "bay_"),
    ("plinth", "door_"), ("plinth", "porch_"),
    ("yard", "pave"), ("yard", "yard_kerb"), ("yard", "threshold"), ("yard", "coal_spill"),
    ("yard", "tuft"), ("yard", "rubble"), ("yard", "plank_loose"), ("yard", "coal_bin"),
    ("yard", "mass"), ("yard", "wing_"), ("yard", "bay_"), ("yard", "porch_"),
    ("pave", "coal_bin"), ("pave", "coal_spill"), ("pave", "rubble"), ("pave", "plank_loose"),
    ("pave", "threshold"), ("pave", "yard_kerb"),
    # 道具站在铺石上（脚埋 3–10 cm）
    ("pave", "anvil"), ("pave", "tool"), ("pave", "weapon"), ("pave", "sword"),
    ("pave", "axe"), ("pave", "quench"), ("pave", "bucket"), ("pave", "coal_a"),
    ("pave", "coal_b"), ("pave", "ingots"), ("pave", "grindstone"), ("pave", "gs_"),
    ("pave", "pot_"), ("pave", "bellows"), ("pave", "rack_"),
    # 地面让建筑"坐"进去：门洞、门框、门扇、门廊翼都从院子边缘穿过
    ("yard", "door_"), ("pave", "door_"), ("threshold", "door_"),
    ("yard", "wing_"), ("pave", "wing_"),
    # 转角石柱与门框是同一圈石套（门框埋在石柱角上）
    ("bay_", "door_"), ("threshold", "bay_"),
    # 墙体：半木构、窗、龛、扶壁都必须嵌进石墙
    ("mass", "quoin"), ("mass", "dado"), ("mass", "string"), ("mass", "buttress"),
    ("mass", "winL"), ("mass", "winR"), ("mass", "stud"), ("mass", "brace"),
    ("mass", "collar"), ("mass", "king_"), ("mass", "gable_"), ("mass", "vent_"),
    ("mass", "wing_"), ("mass", "bay_"), ("mass", "door_"), ("mass", "roof_"),
    ("mass", "ridge"), ("mass", "cup_"), ("mass", "std_"), ("mass", "ch_"),
    ("dado", "quoin"), ("string", "quoin"), ("string", "buttress"), ("dado", "buttress"),
    # 炉膛龛：侧墙 / 拱券 / 拱上墙体 / 龛内地面互为结构
    ("bay_", "arch"), ("bay_", "keystone"), ("bay_", "hood"), ("bay_", "hearth"),
    ("bay_", "canopy_"), ("bay_", "wing_"), ("bay_", "forge"),
    # 坡棚：檩条压板、斜撑顶梁、封檐板包梁
    ("canopy_", "canopy_"), ("canopy_", "vent_"), ("canopy_", "flue_"),
    ("canopy_", "banner_"), ("canopy_", "bay_"),
    # 烟囱：箍套筒身、压顶盖胸墙、盾贴胸墙
    ("ch_", "ch_"), ("ch_", "roof_"), ("ch_", "shield"), ("ch_", "vane"),
    ("ch_", "wing_"),
    # 屋面：瓦垄压板、脊压条、封檐板包椽、楼阁底座埋入屋面、旗杆底座骑脊
    ("roof_", "course"), ("roof_", "ridge"), ("roof_", "fascia"), ("roof_", "barge"),
    ("roof_", "rafter"), ("roof_", "cup_"), ("roof_", "std_"), ("roof_", "ch_"),
    ("roof_", "wing_"), ("roof_", "canopy_"), ("roof_", "gable_"), ("roof_", "stud"),
    ("roof_", "collar"), ("roof_", "king_"), ("roof_", "brace"), ("roof_", "vent_"),
    ("ridge", "std_"), ("ridge", "cup_"), ("ridge", "course"), ("ridge", "roof_"),
    ("cup_", "cup_"), ("std_", "std_"),
    # 门廊 / 门廊翼：屋面压墙、斜撑顶梁、门扇在门洞里
    ("wing_", "wing_"), ("wing_", "door_"), ("wing_", "porch_"), ("wing_", "canopy_"),
    ("wing_", "roof_"), ("wing_", "mass"),
    ("porch_", "porch_"), ("porch_", "wing_"), ("porch_", "door_"),
    ("door_", "door_"), ("door_", "wing_"), ("door_", "mass"),
    # 纹章：盾/旗压在墙面、布面上
    ("shield", "ch_"), ("shield", "mass"), ("shield", "wing_"), ("shield", "kite"),
    ("wbanner", "mass"), ("banner_", "canopy_"), ("kite", "ch_"), ("kite", "mass"),
    ("kite", "wing_"),
    # 细部：招牌挑臂入墙、提灯挂在门侧
    ("sign_", "wing_"), ("sign_", "porch_"), ("lan_", "wing_"), ("corbel", "mass"),
    ("corbel", "roof_"), ("corbel", "fascia"),
    # 道具内部：砧坐树桩、锤压砧面、工具挂架、剑靠墙
    ("anvil", "anvil"), ("anvil", "stump"), ("anvil_", "tool"),
    ("tool", "tool"), ("weapon", "weapon"), ("sword", "sword"), ("axe", "axe"),
    ("quench", "quench"), ("bucket", "bucket"), ("ingots", "ingots"),
    ("grindstone", "grindstone"), ("gs_", "gs_"), ("log", "log"), ("pot_", "pot_"),
    ("bellows", "bellows"), ("bellows", "bay_"), ("bellows", "hearth"),
    ("coal_bin", "coal_lump"), ("coal_bin", "coal_bin"),
    # ── v10 补充：石构件之间的"必须咬合" ────────────────────────────────────
    # 墙裙 / 腰线 / 隅石是围着墙身转的一圈石带，炉膛龛 / 烟囱胸墙都从它内部穿出
    ("dado", "bay_"), ("string", "bay_"), ("dado", "ch_"), ("string", "ch_"),
    ("quoin", "wing_"),
    # 龛壁与龛正面是同一个石体量的两个方向（拱券墙扣在侧墙上）
    ("bay_", "bay_"), ("bay_", "ch_"),
    # 主屋面与门廊翼屋面在 y 3.34/3.40 处交接，封边板压在这条缝上
    ("barge", "wing_"), ("roof_", "wing_"), ("rafter", "wing_"), ("mass", "wing_"),
    # 坡棚的右端插进烟囱胸墙 4 cm（烟囱从棚边"长"出来）
    ("canopy", "ch_"),
    # 罩子的喉管插进棚面（排烟口是穿孔）
    ("hood", "flue_"), ("hood_throat", "flue_"),
    # 檐口石从转角石柱上穿过（压顶石盖住柱顶）
    ("bay_cornice", "bay_pier"), ("bay_frieze", "bay_cornice"),
    # 山墙百叶盒 / 立柱把斜撑盖在里面（斜撑在木构层，百叶盒比它外凸 5 cm）
    ("vent_", "brace"), ("vent_", "stud"),
    # 烟囱胸墙从前檐挑出：屋面封边板从它侧面 1 cm 处穿过
    ("ch_", "barge"), ("coal_bin", "coal_bin_lump"),
    # 腰线 / 墙裙围着主体转一圈，门廊翼与炉膛龛都从它内部穿出（石带被体量"穿过"）
    ("string", "wing_"), ("dado", "wing_"), ("string", "bay_"),
    # 椽条尾端必须坐在墙顶（墙里埋 0.26 m，外面只露 0.20）
    ("mass", "rafter"), ("mass", "course"),
    # 檐下托牙是插在墙里的牛腿，腰线从它下面过
    ("corbel", "string"), ("corbel", "wing_"), ("corbel", "ch_"),
    ("course", "wing_"), ("course", "ch_"), ("roof_", "wing_gutter"),
    # 山墙托梁的左端被门廊翼的体量包住（翼是 cross gable，扣在主山墙前面）
    ("collar", "wing_"), ("gable_", "wing_"),
    # 门廊屋面右端与炉膛龛转角石柱相切（两块石活在一个角上收口）
    ("porch_", "bay_"), ("pave", "porch_"), ("pave", "bay_"),
    ("threshold", "wing_"), ("threshold", "door_"),
]
VIA = [
    ("flue_", "canopy_"), ("vent_", "canopy_"), ("canopy_rafter", "canopy_beam"),
    ("canopy_strut", "canopy_beam"), ("canopy_strut", "bay_"),
    ("rafter", "fascia"), ("corbel", "mass"), ("std_pole", "ridge"),
    ("stud", "mass"), ("brace", "mass"), ("string", "mass"), ("dado", "mass"),
    ("door_", "mass"), ("wing_", "mass"), ("ch_", "mass"), ("ch_", "roof_"),
    ("bay_", "mass"), ("sign_", "wing_"),
]
SLAB = [
    ("_trim", "_cloth"), ("_trimT", "_cloth"), ("tass", "_cloth"), ("ring", "_pole"),
    ("fin", "_pole"), ("_rim", "shield"), ("_field", "shield"), ("emblem", "shield"),
    ("emblem", "wbanner"), ("emblem", "banner"), ("_hoop", "quench"), ("_hoop", "pot_"),
    ("_hoop", "bucket"),
]

# 同一枚徽记的多层贴片（金边 / 盾面 / 冠带 / 冠尖 / 宝石）互为包含是设计本身
CREST_SUF = ("_edge", "_rim", "_field", "_band",
             "_spike0", "_spike1", "_spike2", "_gem0", "_gem1", "_gem2")


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


BIG = ("roof_", "canopy", "mass", "plinth", "yard", "dado", "ch_breast", "wing_mass",
       "bay_floor", "bay_back", "bay_cheek", "bay_wall", "brace", "stud")


def is_big(n):
    """大结构件的包围盒（尤其是旋转的屋面板）会把贴附件整个包住 —— 那不是"埋进去"。"""
    return n.startswith(BIG)


def allowed(a, b):
    for pa, pb in LINK + VIA + SLAB:
        if (a.startswith(pa) and b.startswith(pb)) or (b.startswith(pa) and a.startswith(pb)):
            return True
    return False


def axial_faces(ob, q=0.02):
    """返回 [((axis, sgn), d, (lo_u, hi_u, lo_v, hi_v))]，只取法线在 6 个主轴上的面。

    投影范围用**真实顶点**算：旧版拿 sqrt(area) 当半边长，斜撑 / 多边形的投影
    被放大，天天报"共面"其实不相交。
    """
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
    OUT = r"D:/测试一/docs/铁匠铺/v10/探针/align.txt"
    buf = []

    def P(*a):
        buf.append(" ".join(str(x) for x in a))

    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    m = bs_model.Model(False).build()
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
                if allowed(na, nb):
                    clip_inner.append(rec)
                elif sys_of(na) == sys_of(nb):
                    clip_inner.append(rec)
                else:
                    clip_cross.append(rec)
            if not crest_pair(na, nb):
                if bb_inside(bbs[na], bbs[nb]) and not is_big(nb):
                    contain.append((na, nb))
                elif bb_inside(bbs[nb], bbs[na]) and not is_big(na):
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
    P("=== CLIP_INNER %d (前 20) ===" % len(clip_inner))
    for c, a, b, sa, sb in clip_inner[:20]:
        P("%4d  %-24s <-> %s" % (c, a, b))
    P("=== CONTAIN %d ===" % len(contain))
    for a, b in contain[:60]:
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
        if n.startswith(("plinth", "yard", "ground")):
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
    for n, lo, hi in floaters[:60]:
        P("   %-24s bb %s .. %s" % (n, lo, hi))
    P("DONE")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(buf))
    print("wrote", OUT, len(buf), "lines")


main()
