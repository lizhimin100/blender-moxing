"""comp_sack.py —— 金袋（麻袋）组件：几何 + 骨 + 权重，任何单位都能挂一袋

为什么单独成组件：袋子本身跟"农民"没有关系 —— 运金子的农民、扛粮的苦工、
商队的骡车，都用同一袋。所以按 `unitkit2` 的组件口径做：

    import comp_sack as CS
    SACK = CS.Sack(ROWS, MATERIALS)          # 站表 + 材质
    SACK.add_bone(arm, head, tail)           # 在胸前加一根 sack 骨（父 chest）
    mesh = SACK.build(arm)                   # 建网格，100% 权重给 sack
    mouth = SACK.mouth(P, MOUTH_REST)        # 任意姿态下的袋口世界点

站表一行 = `(y, z, cx, 宽, 厚, 倒角)`：袋子沿"前→后"六站放样，
所以"袋口在身前、袋身压肩、袋尾垂到背后"这件事只由站表决定。

**判据**：整袋 ≤ 500 tri、四种材质（麻布 / 麻布暗 / 金 / team），
束带比袋身只大 7 mm（大了会读成"套在肩上的一圈浮环"）。
"""
import math

import bpy
from mathutils import Matrix, Vector

import unitkit as K

DEFAULT_MATS = {
    "麻布": ("#A6956F", 0.94, 0.0),
    "麻布暗": ("#6F6450", 0.96, 0.0),
    "金": ("#E0B34C", 0.26, 0.86),
    "team": ("#2E5FB4", 0.56, 0.0),
}


def _flat_mat(name, mats):
    hexcol, rough, metal = mats[name]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*K.srgb(hexcol), 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*K.srgb(hexcol), 1.0)
    return m


def _band(name, center, axis, w, h, thick, n=8, ch=None):
    """沿 axis 挤一段环（扎口绳用八边、束带用带倒角的方环）。"""
    d = Vector(axis).normalized()
    X = Vector((1.0, 0.0, 0.0))
    if abs(d.dot(X)) > 0.95:
        X = Vector((0.0, 1.0, 0.0))
    U = d.cross(X).normalized()
    X = U.cross(d).normalized()
    rows = []
    for k in (-0.5, 0.5):
        c = Vector(center) + d * (thick * k)
        pts = K.poly_n(w, h, n) if ch is None else K.poly_rect(w, h, ch)
        rows.append([c + X * u + U * v for (u, v) in pts])
    return K.loft(name, rows, True)


def _octa(name, center, r):
    c = Vector(center)
    v = [c + Vector((r, 0, 0)), c + Vector((-r, 0, 0)),
         c + Vector((0, r, 0)), c + Vector((0, -r, 0)),
         c + Vector((0, 0, r * 1.25)), c + Vector((0, 0, -r * 1.25))]
    f = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4),
         (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    return K._obj(name, v, f)


class Sack:
    def __init__(self, rows, mats=None, bone="sack", name="unit_sack"):
        self.rows = [tuple(r) for r in rows]
        self.mats = dict(mats or DEFAULT_MATS)
        self.bone = bone
        self.name = name
        self._off_mouth = None

    # ── 站坐标系 ────────────────────────────────────────────────────────────
    def _frame(self, i):
        y, z, xc, w, h, ch = self.rows[i]
        c = Vector((xc, y, z))
        if i == 0:
            d = Vector(self.rows[1][:3]) - c
        elif i == len(self.rows) - 1:
            d = c - Vector(self.rows[i - 1][:3])
        else:
            d = Vector(self.rows[i + 1][:3]) - Vector(self.rows[i - 1][:3])
        d.normalize()
        X = Vector((1.0, 0.0, 0.0))
        U = d.cross(X)
        U.normalize()
        if U.z < 0.0:
            U = -U
        return c, X, U, w, h, d

    def _bag_rows(self):
        out = []
        for i in range(len(self.rows)):
            c, X, U, w, h, d = self._frame(i)
            ch = self.rows[i][5]
            out.append([c + X * u + U * v for (u, v) in K.poly_rect(w, h, ch)])
        return out

    # ── 骨 ──────────────────────────────────────────────────────────────────
    def add_bone(self, arm, head, tail, parent="chest"):
        """在 edit 模式加一根骨（已存在就复用）。head 要落在父骨的蒙皮内部，
        这样不扛袋子时把这根骨缩到 0.001 就藏进胸腔，看不见。"""
        if self.bone in arm.data.bones:
            return arm.data.bones[self.bone]
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action="DESELECT")
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm.data.edit_bones.new(self.bone)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        eb.roll = 0.0
        eb.parent = arm.data.edit_bones[parent]
        eb.use_connect = False
        bpy.ops.object.mode_set(mode="OBJECT")
        print("[sack bone]", tuple(round(v, 3) for v in head), "parent", parent)
        return arm.data.bones[self.bone]

    # ── 网格 ────────────────────────────────────────────────────────────────
    def build(self, arm):
        parts = []
        rows = self._bag_rows()
        parts.append((K.loft("sack_body", rows[:-1], True), "麻布"))
        parts.append((K.loft("sack_tail", rows[-2:], True), "麻布暗"))

        c0, X0, U0, w0, h0, d0 = self._frame(0)
        for i, off in enumerate((0.008, 0.044)):
            parts.append((_band("sack_tie%d" % i, c0 + d0 * off, d0,
                                w0 + 0.022, h0 + 0.022, 0.020), "麻布暗"))

        mouth_dir = -d0
        for i, (du, dv, dn) in enumerate(((0.000, 0.010, 0.026),
                                          (-0.028, -0.014, 0.004),
                                          (0.026, -0.017, 0.002))):
            p = c0 + X0 * du + U0 * dv + mouth_dir * dn
            parts.append((_octa("sack_nug%d" % i, p, 0.032), "金"))

        c2, _x2, _u2, w2, h2, _d2 = self._frame(2)
        c3, _x3, _u3, w3, h3, _d3 = self._frame(3)
        c23 = (c2 + c3) * 0.5
        w23 = (w2 + w3) * 0.5 + 0.007
        h23 = (h2 + h3) * 0.5 + 0.007
        d23 = (c3 - c2).normalized()
        parts.append((_band("sack_strap", c23, d23, w23, h23, 0.030, ch=0.052), "team"))
        buckle_c = c23 + Vector((-w23 * 0.5 - 0.006, 0.0, -0.010))
        parts.append((K.box("sack_buckle", tuple(buckle_c), (0.026, 0.062, 0.056)), "金"))

        out = []
        mats = {k: (bpy.data.materials.get(k) or _flat_mat(k, self.mats)) for k in self.mats}
        for ob, mat in parts:
            ob.data.materials.clear()
            ob.data.materials.append(mats[mat])
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            m = ob.modifiers.new("bev", "BEVEL")
            m.width = 0.006
            m.segments = 1
            m.limit_method = "ANGLE"
            m.angle_limit = math.radians(32)
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except Exception as e:
                print("[warn bevel]", ob.name, e)
            for p in ob.data.polygons:
                p.use_smooth = False
            out.append(ob)

        bpy.ops.object.select_all(action="DESELECT")
        for o in out:
            o.select_set(True)
        bpy.context.view_layer.objects.active = out[0]
        bpy.ops.object.join()
        sack = bpy.context.view_layer.objects.active
        sack.name = self.name
        sack.data.name = self.name
        vg = sack.vertex_groups.new(name=self.bone)
        vg.add(list(range(len(sack.data.vertices))), 1.0, "REPLACE")
        sack.parent = arm
        sack.matrix_parent_inverse = arm.matrix_world.inverted()
        md = sack.modifiers.new("Armature", "ARMATURE")
        md.object = arm
        md.use_vertex_groups = True
        sack.data.calc_loop_triangles()
        print("[sack] verts %d tris %d" % (len(sack.data.vertices),
                                           len(sack.data.loop_triangles)))
        return sack

    # ── 任意姿态下的袋口 ────────────────────────────────────────────────────
    def mouth(self, P, mouth_rest):
        """袋口世界点：袋口相对骨盆静止几何不变，所以只要由 sack 骨推一次偏移。"""
        if self._off_mouth is None:
            h, R = P.rig.rest[self.bone]
            self._off_mouth = R.inverted() @ (Vector(mouth_rest) - h)
        P.solve_T()
        return P.T[self.bone] + P.R[self.bone] @ self._off_mouth

    def rot(self, P, pitch=0.0, roll=0.0, yaw=0.0):
        """袋子自己的轻晃（绕骨 head 转，幅度 1~2°，不会穿肩）。"""
        P.rot(self.bone, (1, 0, 0), pitch, chain=True)
        P.rot(self.bone, (0, 1, 0), roll, chain=True)
        P.rot(self.bone, (0, 0, 1), yaw, chain=True)
