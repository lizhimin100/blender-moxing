"""audit_anim.py —— 动作客观验收（穿模 / 离地 / 打滑 / 循环闭合）

对着**出货 glb**跑，不依赖源脚本，所以测的就是引擎里拿到的那一份。

    blender -b --factory-startup --python 库/audit_anim.py -- <unit.glb> [--step 1]
            [--only idle,walk] [--pairs hands]

口径：
  * 蒙皮网格按**顶点组**拆回每根骨（unitkit2 的每件几何都是 100% 单骨权重），
    逐帧对 deform 后的坐标建 BVH，只在"绝不允许相交"的骨对之间做 overlap。
    返回的是**相交三角形对数**，0 = 真的没穿。
  * zmin：全网格最低点（世界 z）。<0 就是切地。
  * 打滑：脚掌最低点贴地（z<0.02）的帧里，foot 骨世界 XY 的逐帧位移累计。
    支撑相应该接近 0（脚钉在地上）。
  * loop：首末帧全骨矩阵最大差。

配对表（--pairs）：
  hands 手/匕首/道具 vs 躯干与腿（默认，最常用）
  all   再加上 前臂 vs 头 / 盾 vs 头 / 麻袋 vs 头 / 上臂 vs 胸
"""
import json
import math
import os
import struct
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def flag(name, default=None):
    if name in argv:
        i = argv.index(name) + 1
        return argv[i] if i < len(argv) else True
    return default


GLB = os.path.abspath(argv[0])
STEP = int(flag("--step", 1))
ONLY = [s for s in str(flag("--only", "")).split(",") if s]
PAIRS = flag("--pairs", "hands")
MAXF = int(flag("--max", 26))          # 长动作最多采样这么多帧

# ── 骨分组：哪根骨属于"身体"（不可被手/武器穿）──────────────────────────────
BODY = ("hips", "spine", "chest", "neck", "head",
        "thigh_R", "shin_R", "foot_R", "toe_R",
        "thigh_L", "shin_L", "foot_L", "toe_L", "cape")
PROP = ("hand_R", "hand_L", "weapon_R", "weapon_L", "weapon", "prop_tool",
        "prop_bolt", "shield", "sack", "prop_sack", "prop_logs")


def pairs_for(mode):
    out = []
    for p in PROP:
        for b in BODY:
            out.append((p, b))
    if mode == "all":
        for p in ("forearm_R", "forearm_L"):
            out.append((p, "head"))
            out.append((p, "chest"))
        out.append(("shield", "head"))
        out.append(("sack", "head"))
        out.append(("upperarm_R", "chest"))
        out.append(("upperarm_L", "chest"))
        out.append(("upperarm_R", "head"))
        out.append(("upperarm_L", "head"))
    return out


P = pairs_for(PAIRS)


# ══ 载入 ════════════════════════════════════════════════════════════════════
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=GLB)

for o in list(scene.objects):
    if o.type == "MESH" and o.name.startswith("Icosphere"):
        bpy.data.objects.remove(o, do_unlink=True)
objs = [o for o in scene.objects if o.type == "MESH"]
arms = [o for o in scene.objects if o.type == "ARMATURE"]
arm = arms[0]

# 顶点 → 骨名（取权重最大的组）
V2B = {}
for ob in objs:
    gi = {g.index: g.name for g in ob.vertex_groups}
    m = []
    for v in ob.data.vertices:
        if not v.groups:
            m.append(None)
            continue
        g = max(v.groups, key=lambda x: x.weight)
        m.append(gi.get(g.group))
    V2B[ob.name] = m

TRIS = {ob.name: [tuple(t.vertices) for t in ob.data.loop_triangles] for ob in objs}
for ob in objs:
    ob.data.calc_loop_triangles()
TRIS = {ob.name: [tuple(t.vertices) for t in ob.data.loop_triangles] for ob in objs}


def frame_geo():
    """当前帧：每根骨 → (世界顶点列表, 三角形列表)。"""
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for ob in objs:
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        mw = oe.matrix_world
        co = [mw @ v.co for v in me.vertices]
        v2b = V2B[ob.name]
        for tri in TRIS[ob.name]:
            b = v2b[tri[0]]
            if b is None:
                continue
            vs, ts = out.setdefault(b, ([], []))
            base = len(vs)
            for i in tri:
                vs.append(co[i])
            ts.append((base, base + 1, base + 2))
        oe.to_mesh_clear()
    return out


def bvh_of(geo, bone):
    if bone not in geo:
        return None
    vs, ts = geo[bone]
    if not ts:
        return None
    return BVHTree.FromPolygons(vs, ts, all_triangles=True, epsilon=0.0)


def zmin_of(geo):
    z = 1e9
    for vs, _ts in geo.values():
        for v in vs:
            if v.z < z:
                z = v.z
    return z


def foot_xy(geo):
    out = {}
    for s in ("R", "L"):
        b = "foot_" + s
        if b not in geo:
            out[s] = None
            continue
        vs, _ts = geo[b]
        z = min(v.z for v in vs)
        c = sum(vs, Vector()) / max(len(vs), 1)
        out[s] = (z, c.x, c.y)
    return out


def check(act_name):
    act = bpy.data.actions.get(act_name)
    if act is None:
        return
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(round(v)) for v in act.frame_range)
    n = f1 - f0
    idx = list(range(f0, f1 + 1, STEP))
    if len(idx) > MAXF:
        idx = [f0 + round(n * i / (MAXF - 1.0)) for i in range(MAXF)]
        idx = sorted(set(int(v) for v in idx))
    worst = {}
    zlo = 1e9
    slide = {"R": 0.0, "L": 0.0}
    prev = {}
    p0 = p1 = None
    for f in idx:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        geo = frame_geo()
        zlo = min(zlo, zmin_of(geo))
        bv = {}
        for (a, b) in P:
            for k in (a, b):
                if k not in bv:
                    bv[k] = bvh_of(geo, k)
            if bv[a] is None or bv[b] is None:
                continue
            ov = bv[a].overlap(bv[b])
            if ov:
                key = a + "×" + b
                worst[key] = max(worst.get(key, 0), len(ov))
        fx = foot_xy(geo)
        for s in ("R", "L"):
            if fx[s] is None:
                continue
            z, x, y = fx[s]
            if z < 0.022 and s in prev and prev[s][0] < 0.022:
                slide[s] += math.hypot(x - prev[s][1], y - prev[s][2])
            prev[s] = (z, x, y)
        if f == f0:
            p0 = [pb.matrix.copy() for pb in arm.pose.bones]
        if f == f1:
            p1 = [pb.matrix.copy() for pb in arm.pose.bones]
    d = 0.0
    if p0 and p1:
        for a, b in zip(p0, p1):
            for r in range(4):
                for c in range(4):
                    d = max(d, abs(a[r][c] - b[r][c]))
    tag = "OK " if (not worst and zlo > -0.002) else "!! "
    print("%s%-13s %5.2fs f%3d..%-3d zmin=%+.4f slide R%.3f L%.3f loop=%.1e %s"
          % (tag, act_name, (f1 - f0) / 30.0, f0, f1, zlo, slide["R"], slide["L"], d,
             "" if not worst else "CLIP " + json.dumps(worst, ensure_ascii=False)))
    return worst, zlo


names = sorted(a.name for a in bpy.data.actions)
if ONLY:
    names = [n for n in names if n in ONLY]
print("[audit]", os.path.basename(GLB), "actions", len(names), "pairs", len(P))
bad = 0
for nm in names:
    r = check(nm)
    if r and (r[0] or r[1] < -0.002):
        bad += 1
arm.animation_data.action = None
print("[audit done] bad actions:", bad)
