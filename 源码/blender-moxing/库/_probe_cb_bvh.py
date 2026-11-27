"""_probe_cb_bvh.py —— 定位"握弩的手穿模"：手 vs 弩身/弩矢 的 BVH 互查。

用法：
  blender -b --factory-startup --python 库/_probe_cb_bvh.py -- [ref|build] [detail]

ref   = 读 _ref/联盟/方块人_弩兵.glb 的原网格（修之前）
build = 用 unit_弩兵.build() 现场建的网格（修之后）
"""
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (HERE, os.path.join(ROOT, "联盟", "弩兵")):
    if p not in sys.path:
        sys.path.insert(0, p)

import unit_弩兵 as UU  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE = argv[0] if argv else "build"
DETAIL = int(argv[1]) if len(argv) > 1 else 1

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = 30

SRC = os.path.join(HERE, "_ref", "联盟", "方块人_弩兵.glb")
bpy.ops.import_scene.gltf(filepath=SRC)
arm = next(o for o in sc.objects if o.type == "ARMATURE")
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()

if MODE == "build":
    import unit_弩兵 as U
    import unitkit as K
    for o in [o for o in sc.objects if o.type == "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)
    u = U.build(DETAIL)
    objs = u.finish(prefix="unit")
    u.bind(arm, objs)
    bpy.context.view_layer.update()
    print("[mode] build detail=%d tris=%d" % (DETAIL, K.stats(objs)))
else:
    print("[mode] ref")

meshes = [o for o in sc.objects if o.type == "MESH" and not o.name.startswith("Icosphere")]

# ── 收集每根骨的顶点（世界坐标）+ 三角面 ────────────────────────────────────
groups = {}
polys = {}
for ob in meshes:
    gi = {g.index: g.name for g in ob.vertex_groups}
    mw = ob.matrix_world
    ob.data.calc_loop_triangles()
    local = {}       # 本对象的顶点 → (骨名, 全局索引)
    for v in ob.data.vertices:
        if not v.groups:
            continue
        g = max(v.groups, key=lambda x: x.weight)
        name = gi.get(g.group, "?")
        bucket = groups.setdefault(name, [])
        local[v.index] = (name, len(bucket))
        bucket.append(mw @ v.co)
    for t in ob.data.loop_triangles:
        if t.vertices[0] not in local:
            continue
        name = local[t.vertices[0]][0]
        polys.setdefault(name, []).append(tuple(local[i][1] for i in t.vertices))

for nm in sorted(groups):
    vs = groups[nm]
    lo = Vector((min(p.x for p in vs), min(p.y for p in vs), min(p.z for p in vs)))
    hi = Vector((max(p.x for p in vs), max(p.y for p in vs), max(p.z for p in vs)))
    print("[bone] %-12s n=%4d tris=%4d  x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]"
          % (nm, len(vs), len(polys.get(nm, [])), lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))

# ── BVH ─────────────────────────────────────────────────────────────────────
def tree(nm):
    return BVHTree.FromPolygons(groups[nm], polys[nm], all_triangles=True)


def inside(bvh, co, d=Vector((0.31, 0.53, 0.79)).normalized()):
    """法线判内外：最近点的法线与 (p-最近点) 相反 → 在壳内（比奇偶射线稳）。"""
    hit = bvh.find_nearest(co)
    if hit[0] is None:
        return False
    return (Vector(co) - hit[0]).dot(hit[1]) < 0.0


def pen(name_a, name_b):
    """A 的顶点扎进 B 的最大深度 + 有多少个 -- 以及面片相交对数。"""
    A, B = tree(name_a), tree(name_b)
    pairs = A.overlap(B)
    vs = groups[name_a]
    worst = 0.0
    wpos = None
    ninside = 0
    for p in vs:
        if inside(B, p):
            ninside += 1
            hit = B.find_nearest(p)
            if hit[0] is not None and hit[3] > worst:
                worst = hit[3]
                wpos = p.copy()
    # 相交面片的中心（局部 fwd/sv/up），用来定位是哪一块
    h, t = UU.WEAPON_H, UU.WEAPON_T
    ax = (t - h).normalized()
    sv = Vector((0, 0, 1)).cross(ax).normalized()
    up = ax.cross(sv)

    def loc(p):
        d = p - h
        return "(f%+.3f s%+.3f u%+.3f)" % (d.dot(ax), d.dot(sv), d.dot(up))

    seen = {}
    for ia, ib in pairs[:200]:
        tri = polys[name_a][ia]
        c = (groups[name_a][tri[0]] + groups[name_a][tri[1]] + groups[name_a][tri[2]]) / 3.0
        k = loc(c)
        seen[k] = seen.get(k, 0) + 1
    if seen:
        top = sorted(seen.items(), key=lambda kv: -kv[1])[:8]
        print("     hit-centres:", "  ".join("%s×%d" % (k, v) for k, v in top))
    return len(pairs), ninside, worst, wpos


for hand in ("hand_R", "hand_L"):
    if hand not in groups:
        continue
    for target in ("weapon", "prop_bolt"):
        if target not in groups:
            continue
        a, b, c, d = pen(hand, target)
        print("[pen] %s -> %-9s  face_pairs=%3d  verts_inside=%3d  max_depth=%.4f  %s"
              % (hand, target, a, b, c,
                 "at (%.3f,%.3f,%.3f)" % (d.x, d.y, d.z) if d else ""))

# ── 弩身横截面（在两只手附近）────────────────────────────────────────────────
h, t = UU.WEAPON_H, UU.WEAPON_T
ax = (t - h).normalized()
sv = Vector((0, 0, 1)).cross(ax).normalized()
up = ax.cross(sv)
print("[frame] ax", tuple(round(v, 4) for v in ax), "sv", tuple(round(v, 4) for v in sv),
      "up", tuple(round(v, 4) for v in up))
wv = groups["weapon"]
for label, wp in (("hand_R", Vector(UU.WRIST["R"])), ("hand_L", Vector(UU.WRIST["L"]))):
    f0 = (wp - h).dot(ax)
    near = [p for p in wv if abs((p - h).dot(ax) - f0) < 0.032]
    if not near:
        print("[sect]", label, "no verts")
        continue
    ss = [(p - h).dot(sv) for p in near]
    uu = [(p - h).dot(up) for p in near]
    # 只看弩身（排除弩臂/踏环等远端：|sv|<0.06）
    ss2 = [(p - h).dot(sv) for p in near if abs((p - h).dot(sv)) < 0.06]
    uu2 = [(p - h).dot(up) for p in near if abs((p - h).dot(sv)) < 0.06]
    print("[sect] %-7s fwd=%.3f  sv[%.4f,%.4f]  up[%.4f,%.4f]  (near verts %d)"
          % (label, f0, min(ss2), max(ss2), min(uu2), max(uu2), len(ss2)))
# 手在 (sv, up, fwd) 里的范围
for hand in ("hand_R", "hand_L"):
    wp = Vector(UU.WRIST[hand[-1]])
    vs = groups[hand]
    f = [(p - h).dot(ax) for p in vs]
    s = [(p - h).dot(sv) for p in vs]
    u2 = [(p - h).dot(up) for p in vs]
    print("[hand] %-7s fwd[%.3f,%.3f] sv[%.3f,%.3f] up[%.3f,%.3f]  wrist(fwd=%.3f sv=%.3f up=%.3f)"
          % (hand, min(f), max(f), min(s), max(s), min(u2), max(u2),
             (wp - h).dot(ax), (wp - h).dot(sv), (wp - h).dot(up)))
print("[bones]", len(arm.data.bones), [b.name for b in arm.data.bones])
