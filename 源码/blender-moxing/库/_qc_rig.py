"""_qc_rig.py —— 刚性蒙皮单位的逐帧体检（zmin / 手↔弩穿透），不走 to_mesh。

每根骨一组顶点（世界静止坐标），一帧的变形矩阵就是
    M = (arm.matrix_world @ pose_bone.matrix) @ (arm.matrix_world @ bone.matrix_local)^-1
刚性蒙皮（每顶点权重 1.0）下这跟 to_mesh 完全等价，但快两个数量级。
"""
from mathutils import Vector
from mathutils.bvhtree import BVHTree


class RigMesh:
    def __init__(self, arm, objs):
        self.arm = arm
        self.groups = {}
        self.polys = {}
        self.rest = {}
        self.cross = 0
        for b in arm.data.bones:
            self.rest[b.name] = (arm.matrix_world @ b.matrix_local).copy()
        for ob in objs:
            gi = {g.index: g.name for g in ob.vertex_groups}
            mw = ob.matrix_world
            ob.data.calc_loop_triangles()
            local = {}
            for v in ob.data.vertices:
                if not v.groups:
                    continue
                g = max(v.groups, key=lambda x: x.weight)
                nm = gi.get(g.group, "?")
                bucket = self.groups.setdefault(nm, [])
                local[v.index] = (nm, len(bucket))
                bucket.append(mw @ v.co)
            for t in ob.data.loop_triangles:
                tri = [local.get(i) for i in t.vertices]
                if any(x is None for x in tri):
                    continue
                nm = tri[0][0]
                if any(x[0] != nm for x in tri):
                    # 跨骨的三角：刚性蒙皮里不该有（多半是导出时把重合顶点焊在一起了）。
                    # 早先这里直接用下标拼面，会把别的骨的顶点号混进来 → 假穿透。
                    self.cross += 1
                    continue
                self.polys.setdefault(nm, []).append(tuple(x[1] for x in tri))

    def _M(self, bone):
        return ((self.arm.matrix_world @ self.arm.pose.bones[bone].matrix)
                @ self.rest[bone].inverted())

    def world(self, bone):
        M = self._M(bone)
        return [M @ v for v in self.groups.get(bone, ())]

    def tree(self, bone):
        return BVHTree.FromPolygons(self.world(bone), self.polys[bone], all_triangles=True)

    def zmin(self):
        lo, nb = 1e9, ""
        for nm in self.groups:
            M = self._M(nm)
            for v in self.groups[nm]:
                z = (M @ v).z
                if z < lo:
                    lo, nb = z, nm
        return lo, nb

    def hits(self, a, b):
        """a / b 两组面片的真实相交对数（0 = 无穿模）。"""
        if a not in self.groups or b not in self.groups:
            return 0
        return len(self.tree(a).overlap(self.tree(b)))
