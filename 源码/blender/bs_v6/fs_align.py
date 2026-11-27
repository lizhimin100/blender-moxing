"""fs_align.py —— 折壳入口的构件级体检（口径与 dl_align / at_align 完全一致）

    python build/bl_act.py act blender/bs_v6/fs_align.py

① CLIP_CROSS  两个不同系统的构件三角形真的相交（同系统内允许，白名单要写物理理由）
② COPLANAR_UP 朝上的面共面（距 < 4 mm、投影重叠 > 2 cm 见方）—— 会 z-fighting
③ FLOAT       与所有构件都不相交、也不落地的构件
④ grounded / front_ok

报告写到 docs/折壳入口/v1/align.txt
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
for m in ("bslib", "br_model", "dl_kit", "fs_model"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import fs_model  # noqa: E402

NAME = "折壳入口"
SYS = [("pad", ("gd_", "tuft", "tuft_h")), ("mound", ("md_",)),
       ("shell", ("sh_",)), ("tunnel", ("cv_",)), ("bone", ("bn_",)),
       ("step", ("st_",)), ("portal", ("pt_",)), ("door", ("dr_",)),
       ("prop", ("pro_", "flame_", "ember"))]
# 白名单只写**物理上必须相交**的配对，其余一律要求真的不碰。
LINK = [("pad", "mound"), ("pad", "shell"), ("pad", "bone"), ("pad", "prop"),
        ("pad", "step"), ("pad", "portal"),
        # 土山是"埋住"墙的：土与墙必须相交，否则读成摆上去的
        ("mound", "shell"), ("mound", "tunnel"), ("mound", "bone"),
        ("mound", "step"), ("mound", "prop"),
        # 隧道是从墙身里穿过去的；洞壁与墙的断面必须接上
        ("shell", "tunnel"), ("shell", "portal"), ("shell", "bone"),
        ("shell", "step"), ("shell", "prop"), ("shell", "door"),
        # 门套石嵌在墙面上；门扇落在门槛上；台阶接门槛
        ("portal", "door"), ("portal", "step"), ("portal", "tunnel"),
        ("portal", "bone"), ("door", "tunnel"), ("step", "tunnel"),
        ("step", "prop"), ("step", "bone"), ("tunnel", "bone"),
        ("tunnel", "prop"), ("bone", "prop"), ("bone", "bone"),
        # 隧道是从土台/土山里挖出来的；门楼站在前庭地面上
        ("pad", "tunnel"), ("mound", "portal"), ("mound", "mound"),
        # 门扇落在门槛石/门枕石上
        ("step", "door")]
FRONT = 0.55   # 壳的体量天生在后侧；判"有没有转 180°"够用


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
                    o0 = (min(q2[others[0]] for q2 in pts),
                          max(q2[others[0]] for q2 in pts))
                    o1 = (min(q2[others[1]] for q2 in pts),
                          max(q2[others[1]] for q2 in pts))
                    out.append(((axis, sgn), d, (o0[0], o0[1], o1[0], o1[1])))
                    break
            else:
                continue
            break
    return out


def sys_of(n):
    for tag, keys in SYS:
        for k in keys:
            if n.startswith(k):
                return tag
    return "other"


def main():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    m = fs_model.Model(False, unwrap=False).build()
    bpy.context.view_layer.update()
    items = [it[0] for it in m.items] + [it[0] for it in m.loose]
    allowed = set()
    for a, b in LINK:
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
    lines = ["ITEMS %d" % len(items),
             "BBOX %s .. %s  SIZE %s" % ([round(v, 2) for v in lo],
                                         [round(v, 2) for v in hi],
                                         [round(v, 2) for v in (hi - lo)]),
             "GROUNDED %s  FRONT_OK %s" % (abs(lo.z) <= 0.06,
                                           hi.y > abs(lo.y) * FRONT),
             "=== CLIP_CROSS %d ===" % len(clip)]
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
    lines.append("=== BELOW_GROUND ===")
    for ob in items:
        low = bbs[ob.name][0].z
        if low < -0.02:
            lines.append("   %-26s z=%+.3f" % (ob.name, low))
    txt = "\n".join(lines)
    out = os.path.join(ROOT, "docs", NAME, "v1")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "align.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    print("\n######## %s ########\n%s" % (NAME, txt))


main()
