"""
br_align.py —— 兵营的构件级"错位 / 穿模 / 共面 / 悬空"体检

    python build/bl_rt.py act blender/bs_v6/bs_align.py

口径（改口径必须同步改这里，否则报告没有可比性）：

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
  ④ FLOAT    构件的包围盒与其它所有构件都不相交（5 mm 容差），也不是落地件 / 前场道具。
             抓"悬在半空的构件"。

白名单（LINK / VIA / SLAB）写在下面，每条都要有物理理由：
  LINK —— 连接件：铁件钉进木梁、挂钩包住杆、箍套住筒身（≤ 30 mm 嵌入）
  VIA  —— 必须穿过：烟管穿屋面、椽条入梁、锚栓入墙
  SLAB —— 贴附装饰：纹章/金边/铁箍压在布或石面上（≤ 25 mm 嵌入）
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for mod in ("bslib", "br_model"):
    if mod in sys.modules:
        importlib.reload(sys.modules[mod])
import br_model as bs_model  # noqa: E402

# ── 系统划分（按名字前缀）──────────────────────────────────────────────────
SYSTEM = [
    ("base", ("plinth", "yard", "apron", "step", "threshold", "seam", "sill", "edge", "lip",
              "rule", "path", "joint",
              # v4 地面：铺石 / 训练圈 / 草簇 / 碎石 全是"地面系统"
              "pave", "drill", "tuft", "rubble", "curb", "patch", "plank_loose")),
    ("wall", ("mass", "quoin", "dado", "string", "buttress", "arrow")),
    ("parapet", ("para", "ml_", "tw_para", "tw_merlon")),
    ("gate", ("gate_",)),
    ("tower", ("tw_",)),
    ("timber", ("post", "rail", "stud", "brace")),
    ("window", ("win_f", "win_s", "win_b", "win2")),
    ("herald", ("shield", "wbanner", "banner", "kite", "emblem", "band_")),
    ("roofdeck", ("deck", "pole", "ph_")),
    ("prop", ("fence", "gate_post", "dummy", "wrack", "barrel", "crate", "armor",
              "target", "hay", "pell", "pikes", "shields", "sandbag")),
]

# 允许的叠压（(a 前缀, b 前缀) 双向匹配）
LINK = [("shield", "gate_"), ("shield", "tower"), ("shield", "mass"), ("shield", "deck"),
        ("wbanner", "mass"), ("banner", "mass"), ("band_", "mass"), ("gate_pilaster", "mass"),
        ("gate_band", "mass"), ("quoin", "mass"), ("para", "mass"), ("ml_", "para"),
        ("tw_", "mass"), ("deck", "mass"), ("pole", "deck"), ("ph_", "deck"),
        # 角楼是贴墙的长方体量：整圈腰线/墙裙从它内部穿过，外面看不见
        ("string", "tw_"), ("plinth_band", "tw_"), ("mass", "tw_"), ("dado", "tw_"),
        # 门框 / 门扇 / 门洞暖光落在腰线高度上，被门框挡住
        ("gate_", "plinth_band"),
        # 场地铺到角楼基座底下（建筑坐在场地里）
        ("yard", "tw_"), ("apron", "tw_"), ("seam", "tw_"), ("edge", "tw_"),
        # 门柱包住围栏端头、假人站台压在石铺上
        ("gate_post", "fence"), ("dummy_", "apron"),
        # 基座是一圈"包住墙脚"的台：墙体 / 墙裙 / 扶壁都插进它 0.48
        ("plinth", "mass"), ("plinth", "dado"), ("plinth", "tw_"), ("plinth", "quoin"),
        ("plinth", "buttress"), ("string", "buttress"),
        # 门槛是一块凸出门前的石踏步，门框 / 墙根盾都踩在它上面
        ("threshold", "gate_"), ("threshold", "shields"), ("threshold", "dado"),
        # 门楼是从前女儿墙上"长"出来的：墙体与垛口都从它内部穿过
        ("para", "gh_"), ("ml_", "gh_"),
        # 饰带钉在木构立柱外面（10 mm 嵌入）
        ("band_", "stud"), ("band_", "post"), ("band_", "rail"),
        # 角楼包住主墙的转角：那一角的隅石在角楼内部
        ("quoin", "tw_"),
        # 门套壁柱是竖向贴在墙上的，横过墙裙和二层腰线（建筑做法本身如此）
        ("gate_pilaster", "string"), ("gate_pilaster", "dado"), ("gate_pilaster", "plinth"),
        ("gate_band", "string"), ("gate_jamb", "dado"), ("gate_jamb", "string"),
        # 角楼平台板插在角楼女儿墙之间（板压墙）
        ("tw_floor", "tw_para"),
        # 门扇/门缝合页在门洞里穿过基座与门槛
        ("plinth", "gate_"), ("threshold", "plinth"),
        # 屋顶物件坐在平台板上（顶面同为 7.40，只有边线接触）
        ("mass", "ph_"), ("mass", "pole"), ("mass", "brazier"), ("mass", "deck"),
        ("deck", "brazier"), ("dado", "gate_"),
        # 窗玻璃贴住立柱、纹章矛尖画到横幅外 1 cm（都在墙面上，看不见）
        ("stud", "win2s"), ("stud", "wbanner"), ("post_b", "wbanner"),
        # ── v4 地面：铺石 / 沙圈是"站在"夯土台上的实体件（埋 3–6 cm），
        #    道具站在铺石 / 沙面上，围栏柱穿过铺石外沿 —— 都是设计叠压
        ("yard", "gate_step"), ("pave", "gate_step"), ("patch", "dummy"),
        ("pave", "fence"), ("pave", "barrel"), ("pave", "armor"), ("pave", "pikes"),
        ("pave", "shields"), ("pave", "crate"), ("pave", "dummy"),
        ("drill", "pell"), ("drill_ring", "dummy"), ("drill", "wrack")]
VIA = [("gate_", "mass"), ("win_", "mass"), ("win2", "mass"), ("post", "mass"),
       ("rail", "mass"), ("stud", "mass"), ("brace", "mass"), ("string", "mass"),
       ("dado", "mass"), ("buttress", "mass"), ("threshold", "mass"),
       ("yard", "plinth"), ("fence", "yard"), ("fence", "plinth"), ("gate_post", "yard"),
       ("dummy", "yard"), ("wrack", "yard"), ("armor", "yard"), ("target", "yard"),
       ("hay", "yard"), ("pell", "yard"), ("pikes", "yard"), ("barrel", "yard"),
       ("crate", "yard"), ("shields", "yard"), ("sandbag", "yard"),
       ("gate_flag", "gate_post"), ("fence_flag", "fence")]
SLAB = [("_trim", "_cloth"), ("fringe", "_cloth"), ("emblem", "shield"),
        ("emblem", "wbanner"), ("_cap", "ml_"), ("_cap", "tw_merlon"), ("apron", "yard"),
        ("seam", "yard"), ("_rope", "hay"), ("_hoop", "barrel"), ("_band", "crate")]


CREST_SUF = ("_edge", "_rim", "_field", "_band",
             "_spike0", "_spike1", "_spike2", "_gem0", "_gem1", "_gem2")


def crest_base(n):
    for suf in CREST_SUF:
        if n.endswith(suf):
            return n[:-len(suf)]
    return None


def crest_pair(a, b):
    """同一枚徽记的两块贴片（金边/盾面/冠带/冠尖/宝石）互为包含是设计本身。"""
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
    """返回 [(axis_vec_key, d, (lo0, hi0, lo1, hi1))]，只取法线在 6 个主轴上的面。

    v4 起用**真实顶点**算投影范围：旧版拿 sqrt(area) 当半边长，斜撑 / 多边形的
    投影被放大，天天报"共面"其实不相交（mass_front 与 mass_back 就是这种假阳性）。
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
    OUT = r"D:/测试一/docs/兵营/v4/探针/align.txt"
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
                if bb_inside(bbs[na], bbs[nb]):
                    contain.append((na, nb))
                elif bb_inside(bbs[nb], bbs[na]):
                    contain.append((nb, na))
            # 共面
            fa, fb = axial_faces(a), axial_faces(b)
            for (ka, da, ba) in fa:
                for (kb, db, bb2) in fb:
                    if ka != kb or abs(da - db) > 0.004:
                        continue
                    # 两个方向的投影都必须真的重叠（面积 > 0.0004 m² = 2 cm 见方）
                    ow = min(ba[1], bb2[1]) - max(ba[0], bb2[0])
                    oh = min(ba[3], bb2[3]) - max(ba[2], bb2[2])
                    if ow > 0.02 and oh > 0.02 and ow * oh > 0.0004:
                        coplanar.append((na, nb, round(da, 3), ka))

    clip_cross.sort(reverse=True)
    P("=== CLIP_CROSS %d ===" % len(clip_cross))
    for c, a, b, sa, sb in clip_cross[:80]:
        P("%4d  %-24s(%s) <-> %-24s(%s)" % (c, a, sa, b, sb))
    P("=== CLIP_INNER %d (前 20) ===" % len(clip_inner))
    for c, a, b, sa, sb in clip_inner[:20]:
        P("%4d  %-24s <-> %s" % (c, a, b))
    P("=== CONTAIN %d ===" % len(contain))
    for a, b in contain[:40]:
        P("   %-24s  in  %s" % (a, b))
    # 真正会"闪"的只有**朝上**的共面（俯视时看得见）。朝下的底面全部贴在 z=0，
    # 被地面挡住，不进这一条统计口径。
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

    # 悬空：bb 与所有其它构件都不相交
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
    for n, lo, hi in floaters[:40]:
        P("   %-24s bb %s .. %s" % (n, lo, hi))
    P("DONE")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(buf))
    print("wrote", OUT, len(buf), "lines")


main()
