"""dl_align.py —— 新资产（地牢 / 地下城入口 / 酒馆内部 / 四件火）的构件级体检

    blender -b --python blender/bs_v6/dl_align.py

口径与 bs_align / br_align / ... / at_align 一致：
  ① CLIP_CROSS  两个不同系统的构件三角形真的相交（同系统内允许，白名单要写物理理由）
  ② COPLANAR_UP 朝上的面共面（距 < 4 mm、投影重叠 > 2 cm 见方）—— 会 z-fighting
  ③ FLOAT       与所有构件都不相交、也不落地的构件
  ④ grounded / front_ok

报告写到 docs/<资产>/v1/align.txt，汇总写到 docs/新资产体检.txt。
"""
import importlib
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "br_model", "wt_model", "dl_kit", "dl_parts", "dg_layout",
          "dg_model", "uc_model",
          "tv_model", "fr_model"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import dg_model  # noqa: E402
import uc_model  # noqa: E402
import tv_model  # noqa: E402
import fr_model  # noqa: E402

# ── 每件资产的系统分组 + 允许相交的"结构接触" ──────────────────────────────
ASSETS = {
    "地牢": {
        "mod": dg_model, "kw": {},
        "sys": [("pad", ("pd_",)), ("shelf", ("sh_",)), ("court", ("pt_", "st_")),
                ("gate", ("gw_",)), ("door", ("dr_",)), ("back", ("bq_",)),
                ("prop", ("pr_",)), ("trace", ("tr_",)), ("team", ("tm_",)),
                ("fire", ("fl_",))],
        # 允许相交 = 结构接触，每条都有物理理由（写在这里，报告直接引用）：
        #   shelf-court  压边坐在槽口上、台阶落在槽里
        #   shelf-gate   门墙两翼故意嵌进石壳 6 mm（不然接缝漏发丝黑线）
        #   shelf-back   土丘压在石壳顶面
        #   court-gate   门墙面就是槽底的后壁
        #   gate-door    门扇压进门框的掩口（关死时必然重叠）
        #   *-team       漆面刷在别的构件表面上
        "link": [("shelf", "court"), ("shelf", "gate"), ("shelf", "back"),
                 ("shelf", "prop"), ("shelf", "pad"), ("pad", "prop"),
                 ("court", "gate"), ("court", "door"), ("court", "prop"),
                 ("court", "trace"), ("gate", "door"), ("gate", "prop"),
                 ("back", "prop"), ("back", "gate"), ("door", "trace"),
                 ("door", "prop"), ("door", "fire")],
        # 覆盖层：漆面 / 苔痕 / 拖痕本来就是"刷在别人表面上"的，
        # 它们与任何构件重叠都不算穿模（这条对所有资产成立，不是本座的特例）
        "overlay": ("team", "trace"),
        "dir": "v2",
        "front": 0.85,
    },
    "地下城入口": {
        "mod": uc_model, "kw": {},
        "sys": [("pad", ("pad_", "tuft")), ("cliff", ("clf_",)), ("ter", ("ter_",)),
                ("stair", ("st_",)), ("statue", ("stat_",)), ("rune", ("rune_",)),
                ("par", ("par_",)), ("flag", ("bnr_",)), ("torch", ("torch_",)),
                ("prop", ("pro_",)), ("fire", ("flame_",))],
        "link": [("pad", "cliff"), ("pad", "ter"), ("pad", "stair"), ("pad", "prop"),
                 ("cliff", "ter"), ("cliff", "statue"), ("cliff", "torch"),
                 ("cliff", "flag"), ("ter", "stair"), ("ter", "statue"),
                 ("ter", "rune"), ("ter", "flag"), ("ter", "prop"),
                 ("ter", "torch"), ("statue", "flag"), ("prop", "ter"),
                 ("prop", "pad"), ("stair", "ter"), ("fire", "prop"),
                 ("par", "ter"), ("par", "stair"), ("par", "cliff"), ("par", "prop"),
                 ("par", "flag"),
                 ("fire", "torch")],
        "front": 1.0,
    },
    "酒馆内部": {
        "mod": tv_model, "kw": {},
        "sys": [("base", ("base_", "flr_")), ("wall", ("wall_",)), ("frame", ("beam_", "post_")),
                ("bar", ("bar_", "stl_")), ("hearth", ("hth_",)), ("table", ("tbl_",)),
                ("stair", ("stair_",)), ("lamp", ("chn_",)), ("flag", ("bnr_",)),
                ("lantern", ("lan_",)), ("prop", ("prop_",)),
                ("fire", ("flame_",))],
        "link": [("base", s) for s in ("wall", "frame", "bar", "hearth", "table",
                                       "stair", "lamp", "flag", "lantern", "prop")] +
                [("wall", "frame"), ("wall", "bar"), ("wall", "hearth"), ("wall", "lantern"),
                 ("wall", "flag"), ("wall", "prop"), ("frame", "bar"), ("frame", "lamp"),
                 ("frame", "wall"), ("bar", "table"), ("bar", "prop"), ("bar", "hearth"),
                 ("hearth", "prop"), ("hearth", "wall"), ("table", "prop"),
                 ("stair", "prop"), ("stair", "wall"), ("lamp", "frame"),
                 ("flag", "wall"), ("lantern", "wall"), ("prop", "wall"),
                 ("prop", "stair"), ("prop", "bar"), ("fire", "hearth"),
                 ("fire", "prop")],
        "front": 1.0,
    },
}
for cn in ("营火", "火把", "火炬", "火堆"):
    ASSETS[cn] = {"mod": fr_model.module_for(cn), "kw": {"name": cn},
                  "sys": [("root", ("",))], "link": [], "front": 1.0}


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


def run(cn, cfg):
    mod = cfg["mod"]
    if "name" in cfg["kw"]:
        m = mod.Model(False, unwrap=False)
        m = m.build()
    else:
        m = mod.Model(False, unwrap=False).build()
    bpy.context.view_layer.update()
    items = [it[0] for it in m.items]
    systems = cfg["sys"]

    overlay = set(cfg.get("overlay", ()))

    def sys_of(n):
        for tag, keys in systems:
            for k in keys:
                if n.startswith(k):
                    return tag
        return "other"

    allowed = set()
    for a, b in cfg["link"]:
        allowed.add((a, b))
        allowed.add((b, a))

    bbs = {ob.name: bb_of(ob) for ob in items}
    trees = {}
    for ob in items:
        try:
            trees[ob.name] = bvh_of(ob)
        except Exception:
            pass

    clip, coplanar = [], []
    for i, a in enumerate(items):
        na = a.name
        sa = sys_of(na)
        for b in items[i + 1:]:
            nb = b.name
            sb = sys_of(nb)
            if na in nb or nb in na:
                continue
            if not bb_hit(bbs[na], bbs[nb], 0.001):
                continue
            if sa in overlay or sb in overlay:
                continue
            if sa != sb and (sa, sb) not in allowed:
                ov = trees[na].overlap(trees[nb]) if na in trees and nb in trees else []
                if ov:
                    clip.append((len(ov), na, nb, sa, sb))
            fa, fb = axial_faces(a), axial_faces(b)
            for (ka, da, ba) in fa:
                for (kb, db, bb2) in fb:
                    if ka != kb or abs(da - db) > 0.004:
                        continue
                    ow = min(ba[1], bb2[1]) - max(ba[0], bb2[0])
                    oh = min(ba[3], bb2[3]) - max(ba[2], bb2[2])
                    if ow > 0.02 and oh > 0.02 and ow * oh > 0.0004:
                        coplanar.append((na, nb, round(da, 3), ka))

    floaters = []
    for ob in items:
        n = ob.name
        lo, hi = bbs[n]
        if lo.z < 0.03:
            continue
        if not any(bb_hit(bbs[n], bbs[o.name], 0.004) for o in items if o.name != n):
            floaters.append((n, tuple(round(v, 2) for v in lo),
                             tuple(round(v, 2) for v in hi)))

    lo = Vector((min(b[0][i] for b in bbs.values()) for i in range(3)))
    hi = Vector((max(b[1][i] for b in bbs.values()) for i in range(3)))
    up = [c for c in coplanar if c[3] == (2, 1)]
    lines = []
    lines.append("ITEMS %d" % len(items))
    lines.append("BBOX %s .. %s  SIZE %s" % (
        [round(v, 2) for v in lo], [round(v, 2) for v in hi],
        [round(v, 2) for v in (hi - lo)]))
    lines.append("GROUNDED %s  FRONT_OK %s" % (
        abs(lo.z) <= 0.06, hi.y > abs(lo.y) * cfg["front"]))
    lines.append("=== CLIP_CROSS %d ===" % len(clip))
    for c, a, b, sa, sb in sorted(clip, reverse=True)[:40]:
        lines.append("%4d  %-26s(%s) <-> %-26s(%s)" % (c, a, sa, b, sb))
    lines.append("=== COPLANAR_UP %d ===" % len(up))
    seen = set()
    for a, b, d, k in up:
        key = (a, b)
        if key in seen:
            continue
        seen.add(key)
        lines.append("   %-26s <-> %-26s @%s d=%+.3f" % (a, b, k, d))
        if len(seen) >= 40:
            break
    lines.append("=== FLOAT %d ===" % len(floaters))
    for n, l, h in floaters[:30]:
        lines.append("   %-26s bb %s .. %s" % (n, l, h))
    txt = "\n".join(lines)
    out = os.path.join(ROOT, "docs", cn, cfg.get("dir", "v1"))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "align.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print("\n######## %s ########\n%s" % (cn, txt))
    return {"name": cn, "items": len(items), "clip": len(clip),
            "coplanar": len(up), "float": len(floaters),
            "grounded": abs(lo.z) <= 0.06, "front": hi.y > abs(lo.y) * cfg["front"],
            "size": [round(v, 2) for v in (hi - lo)]}


def main():
    import json
    res = []
    for cn, cfg in ASSETS.items():
        for ob in list(bpy.data.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
        for m in list(bpy.data.materials):
            if m.users == 0:
                bpy.data.materials.remove(m)
        res.append(run(cn, cfg))
    with open(os.path.join(ROOT, "docs", "新资产体检.txt"), "w", encoding="utf-8") as f:
        f.write("资产\t构件\tCLIP_CROSS\tCOPLANAR_UP\tFLOAT\t贴地\t朝向\t尺寸\n")
        for r in res:
            f.write("%s\t%d\t%d\t%d\t%d\t%s\t%s\t%s\n" % (
                r["name"], r["items"], r["clip"], r["coplanar"], r["float"],
                "OK" if r["grounded"] else "NO", "OK" if r["front"] else "NO",
                r["size"]))
    print("ALIGN_SUMMARY " + json.dumps(res, ensure_ascii=False))


main()
