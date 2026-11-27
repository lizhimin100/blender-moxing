"""clip_lib.py —— 动作客观体检的公共部分（穿模 / 离地 / 打滑 / 循环闭合）

被两个脚本共用：
  * `audit_anim.py`  对着出货 glb 跑（最终验收）
  * `pose_check.py`  内存里建单位 + 只建要看的动作（迭代时用，比导出快）

为什么按顶点组拆网格：`unitkit2` 每一件几何都是 100% 单骨权重，所以"这块三角面
属于哪根骨"是确定的。拆开之后就能直接问"左手有没有插进胯里"这种问题，
不用靠眼睛数像素 —— 之前的"手撑腰"就是这么找出来的（hand_L×hips 576 对）。

判定只做**三角形互交**（BVHTree.overlap）。相邻骨（上臂↔前臂、大腿↔小腿）
天然在关节处互相含着，所以配对表里只放**绝不允许相交**的组合。
"""
import json

from mathutils import Vector
from mathutils.bvhtree import BVHTree

BODY = ("hips", "spine", "chest", "neck", "head",
        "thigh_R", "shin_R", "foot_R", "toe_R",
        "thigh_L", "shin_L", "foot_L", "toe_L", "cape")
PROP = ("hand_R", "hand_L", "weapon_R", "weapon_L", "weapon", "prop_tool",
        "prop_bolt", "shield", "sack", "prop_sack", "prop_logs")

# 只在 --pairs all 里加的"结构性"配对：它们允许在关节处轻微相交，
# 但超过阈值就说明手臂整条压进躯干了。
SOFT = (("upperarm_R", "chest"), ("upperarm_L", "chest"),
        ("upperarm_R", "head"), ("upperarm_L", "head"),
        ("forearm_R", "chest"), ("forearm_L", "chest"),
        ("forearm_R", "head"), ("forearm_L", "head"))


def pairs_for(mode="hands"):
    out = []
    for p in PROP:
        for b in BODY:
            out.append((p, b))
    if mode == "all":
        out.extend(SOFT)
    return out


class Watch:
    """一组蒙皮网格的逐帧体检器。"""

    def __init__(self, objs):
        self.objs = objs
        self.v2b = {}
        self.tris = {}
        for ob in objs:
            gi = {g.index: g.name for g in ob.vertex_groups}
            m = []
            for v in ob.data.vertices:
                if not v.groups:
                    m.append(None)
                    continue
                g = max(v.groups, key=lambda x: x.weight)
                m.append(gi.get(g.group))
            self.v2b[ob.name] = m
            ob.data.calc_loop_triangles()
            self.tris[ob.name] = [tuple(t.vertices) for t in ob.data.loop_triangles]
        self.soft_limit = 40      # 上臂/前臂 vs 胸 的"结构性"相交容忍对数

    # ── 当前帧几何 ──────────────────────────────────────────────────────────
    def geo(self, dg):
        out = {}
        for ob in self.objs:
            oe = ob.evaluated_get(dg)
            me = oe.to_mesh()
            mw = oe.matrix_world
            co = [mw @ v.co for v in me.vertices]
            v2b = self.v2b[ob.name]
            for tri in self.tris[ob.name]:
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

    @staticmethod
    def bvh(geo, bone):
        if bone not in geo:
            return None
        vs, ts = geo[bone]
        if not ts:
            return None
        return BVHTree.FromPolygons(vs, ts, all_triangles=True, epsilon=0.0)

    @staticmethod
    def zmin_tag(geo):
        z, b = 1e9, ""
        for k, (vs, _ts) in geo.items():
            for v in vs:
                if v.z < z:
                    z, b = v.z, k
        return z, b

    @staticmethod
    def zmin(geo):
        z = 1e9
        for vs, _ts in geo.values():
            for v in vs:
                if v.z < z:
                    z = v.z
        return z

    @staticmethod
    def foot(geo, s):
        b = "foot_" + s
        if b not in geo:
            return None
        vs, _ts = geo[b]
        return (min(v.z for v in vs), sum(vs, Vector()) / max(len(vs), 1))

    def clip(self, geo, pairs):
        bv = {}
        worst = {}
        for (a, b) in pairs:
            for k in (a, b):
                if k not in bv:
                    bv[k] = self.bvh(geo, k)
            if bv[a] is None or bv[b] is None:
                continue
            ov = bv[a].overlap(bv[b])
            if not ov:
                continue
            lim = self.soft_limit if (a, b) in SOFT else 0
            if len(ov) > lim:
                worst[a + "×" + b] = max(worst.get(a + "×" + b, 0), len(ov))
        return worst


def audit_action(scene, arm, act, pairs, watch, step=1, maxf=26, quiet=False):
    """跑一条动作：返回 dict(worst, zmin, slide, loop, frames)。"""
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(round(v)) for v in act.frame_range)
    n = max(f1 - f0, 1)
    idx = list(range(f0, f1 + 1, step))
    if len(idx) > maxf:
        idx = sorted({int(f0 + round(n * i / (maxf - 1.0))) for i in range(maxf)})
    worst = {}
    zlo = 1e9
    zlo_at = (0, "")
    prev = {}
    slide = 0.0
    p0 = p1 = None
    for f in idx:
        scene.frame_set(f)
        geo = watch.geo(__import__("bpy").context.evaluated_depsgraph_get())
        zz, bb = watch.zmin_tag(geo)
        if zz < zlo:
            zlo, zlo_at = zz, (f, bb)
        w = watch.clip(geo, pairs)
        for k, v in w.items():
            worst[k] = max(worst.get(k, 0), v)
        for s in ("R", "L"):
            ft = watch.foot(geo, s)
            if ft is None:
                continue
            z, c = ft
            if z < 0.022 and s in prev and prev[s][0] < 0.022:
                slide += (Vector((c.x, c.y)) - Vector((prev[s][1], prev[s][2]))).length
            prev[s] = (z, c.x, c.y)
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
    res = dict(name=act.name, worst=worst, zmin=zlo, slide=slide, loop=d,
               frames=(f0, f1), zmin_at=zlo_at)
    if not quiet:
        ok = (not worst) and zlo > -0.002
        print("%s%-13s %5.2fs f%3d..%-3d zmin=%+.4f@f%d(%s) stride=%.3f loop=%.1e %s"
              % ("OK " if ok else "!! ", act.name, (f1 - f0) / 30.0, f0, f1, zlo,
                 zlo_at[0], zlo_at[1], slide, d,
                 "" if not worst else "CLIP " + json.dumps(worst, ensure_ascii=False)))
    return res
