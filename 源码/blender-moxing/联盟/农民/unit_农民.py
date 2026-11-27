"""unit_农民.py —— 联盟农民（方块人）v4：换一套动作 + 肩上金袋

## 只换动作，不重建模型
模型来自 `库/_ref/联盟/方块人_农民.glb`（5,076 面 / 3 网格 / 25 骨），
`load()` 只做 `bpy.ops.import_scene.gltf()`，**几何一个顶点都不改**。
唯一新增：一根 `sack` 骨 + 一个 `unit_sack` 金袋网格（用户点名要的组件）。

## 这个骨架和步兵那套的两个差别
1. **有三根道具骨**：`prop_tool`（锄头，挂 `hand_R`）、`prop_sack`（旧腰袋）、
   `prop_logs`（柴禾，后两根挂 `chest`）。旧资产靠 `scale=0.002` 把不用的道具缩成一点，
   本文件沿用同一套做法：`anims_农民` 每帧写 `SCL["prop_sack"]=SCL["prop_logs"]=0.002`。
2. **锄头是 0.73 m 的短柄锄**（从腕点到刃底 0.525 m）。所以"拄锄头"必须
   **微微弓腰**才够得着地 —— `S.HOE_*` 里量好了，别按长柄锄的直觉摆。

## 金袋为什么单独一根骨
袋子挂在 `chest` 下（`sack`），扛袋子的动作把它 `SCL=1.0`；其余动作一律 `SCL=0.001`
把一个 1 mm 的小点缩进胸腔内部（`SACK_HEAD` 实测在 chest 蒙皮内部），看不见。

## 尺寸（从 glb 量出来的，改模型才会变）
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
LIB = os.path.join(ROOT, "库")
for _p in (LIB, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import comp_sack as CS  # noqa: E402
import poselib2 as PL  # noqa: E402
import unitkit as K    # noqa: E402

NAME = "方块人_农民"
KEY = "农民"
SRC = os.path.join(LIB, "_ref", "联盟", "方块人_农民.glb")
ASSET = os.path.join(os.path.dirname(ROOT), "assets", "单位", "联盟", "农民")

# ── 骨架关键点（probe 实测）────────────────────────────────────────────────
Z_HIP = 0.667
Z_WAIST = 0.787
Z_CHEST = 0.967
Z_NECK = 1.120
Z_HEAD = 1.194
Z_TOP = 1.267
HIP_X = 0.120
SH_X = 0.218           # upperarm_L/R 的 head（肩关节）
Z_SHLD = 1.108
Z_ANKLE = 0.071
HEEL_Y = -0.127
TOE_Y = 0.200          # 方块脚（toe 骨没有蒙皮，脚是一整块）

WRI_R = Vector((0.2841, 0.0588, 0.671))
WRI_L = Vector((-0.2841, 0.0588, 0.671))

# ── 新骨：sack ─────────────────────────────────────────────────────────────
# head 落在 chest 蒙皮内部（z 1.09 < chest 顶 1.128、|x| 0.14 < 0.196），
# 不扛袋子时 SCL=0.001 缩成一个点就藏在胸腔里，看不见。
SACK_HEAD = Vector((-0.140, 0.010, 1.090))
SACK_TAIL = SACK_HEAD + Vector((0.0, -0.140, -0.060))
SACK_MOUTH = Vector((-0.302, 0.186, 0.980))     # 袋口中心（静止姿态世界坐标）

BONES_OK = ("root", "hips", "spine", "chest", "neck", "head",
            "shoulder_R", "upperarm_R", "forearm_R", "hand_R", "prop_tool",
            "shoulder_L", "upperarm_L", "forearm_L", "hand_L",
            "prop_sack", "prop_logs",
            "thigh_R", "shin_R", "foot_R", "toe_R",
            "thigh_L", "shin_L", "foot_L", "toe_L", "sack")


class Spec:
    """动作层要用的尺寸量（只读）。"""

    def __init__(self):
        self.ANK = Vector((HIP_X, 0.0, Z_ANKLE))
        self.HIP = Vector((HIP_X, 0.0, Z_HIP))
        self.SH = Vector((SH_X, 0.0, Z_SHLD))
        self.Z_ANKLE = Z_ANKLE
        self.HEEL_Y = HEEL_Y
        self.TOE_Y = TOE_Y
        self.H = 1.62
        self.WRI_R = WRI_R.copy()
        self.WRI_L = WRI_L.copy()

    def foot_clear(self, pitch_deg):
        """方块脚绕踝转 pitch 后，踝要高到多少脚底才不切地。"""
        p = math.radians(pitch_deg)
        sp, cp = math.sin(p), math.cos(p)
        lo = 0.0
        for y in (HEEL_Y, TOE_Y):
            lo = max(lo, -(-Z_ANKLE * cp + y * sp))
        return lo


S = Spec()


# ══ 锄头：静止几何量（load 时从网格算）══════════════════════════════════════
class Hoe:
    """锄头的静止几何：握点（= hand_R 的 head / 腕点）、柄轴、刃底、柄顶。

    动作层只关心三件事：
      * `axis`    握点→刃 的世界方向（静止姿态）
      * `blade`   刃底参考点相对腕点（静止）
      * `top`     柄顶相对腕点（静止）
    把锄头摆到"刃底落在 (ax, ay, tip_z)、柄竖直"时，腕点就是
    `(ax, ay, tip_z) - Q @ blade`，`Q` 由 `axis` 旋到 (0,0,-1) 得到。
    """

    def __init__(self):
        self.axis = Vector((0.062, 0.721, -0.690)).normalized()
        self.blade = Vector((0.0, 0.0, 0.0))
        self.top = Vector((0.0, 0.0, 0.0))
        self.pts = []          # 相对 prop_tool 骨 head 的静止坐标
        self.head = Vector((0.274, -0.082, 0.806))
        self.q_vert = Matrix.Identity(3)
        self.blade_q = Vector((0.0, 0.0, 0.0))
        self.top_q = Vector((0.0, 0.0, 0.0))

    def measure(self, arm, meshes):
        H0 = arm.data.bones["hand_R"].head_local.copy()
        self.head = arm.data.bones["prop_tool"].head_local.copy()
        pts = []
        for ob in meshes:
            gi = {g.index: g.name for g in ob.vertex_groups}
            for v in ob.data.vertices:
                if not v.groups:
                    continue
                g = max(v.groups, key=lambda x: x.weight)
                if gi.get(g.group) == "prop_tool":
                    pts.append(ob.matrix_world @ v.co)
        if not pts:
            return self
        c = sum(pts, Vector()) / len(pts)
        # 主轴：协方差最大特征向量（不引 numpy，用幂迭代）
        ax = Vector((0.062, 0.721, -0.690))
        for _ in range(24):
            acc = Vector((0.0, 0.0, 0.0))
            for p in pts:
                d = p - c
                acc += d * d.dot(ax)
            if acc.length > 1e-9:
                ax = acc.normalized()
        if (H0 - c).dot(ax) > 0.0:
            ax = -ax
        self.axis = ax
        self.pts = [p - self.head for p in pts]

        Q = ax.rotation_difference(Vector((0, 0, -1))).to_matrix()
        self.q_vert = Q
        rel = [Q @ (p - H0) for p in pts]
        zmin = min(p.z for p in rel)
        low = [p for p in rel if p.z < zmin + 0.04]
        self.blade_q = sum(low, Vector()) / len(low)
        zmax = max(p.z for p in rel)
        top = [p for p in rel if p.z > zmax - 0.03]
        self.top_q = sum(top, Vector()) / len(top)
        self.blade = Q.transposed() @ self.blade_q
        self.top = Q.transposed() @ self.top_q
        return self

    # ── 给动作层用 ──────────────────────────────────────────────────────────
    def grip(self, ax, ay, tip_z=0.012):
        """刃底落在 (ax, ay, tip_z)、柄竖直时，右腕该在哪。"""
        return Vector((ax, ay, tip_z)) - self.blade_q

    def aim(self, P, direction, roll=0.0):
        """把锄头指向 direction（世界），返回刚体旋转 M（手/锄头一起转）。"""
        d = Vector(direction).normalized()
        q = self.axis.rotation_difference(d).to_matrix()
        if abs(roll) > 1e-9:
            q = Matrix.Rotation(math.radians(roll), 3, d) @ q
        P.set_world("hand_R", q @ P.rig.rest["hand_R"][1])
        return q

    def tip(self, P, M):
        """当前姿态下刃底的世界点（用实际腕点算，IK 够不到也算得准）。"""
        return P.T["hand_R"] + M @ self.blade_q

    def top_world(self, P, M):
        return P.T["hand_R"] + M @ self.top_q

    def floor_rot(self, restR, hdir=(0.30, -0.94, 0.0)):
        """锄头躺平：柄轴水平 + 绕柄找一个"最扁"的滚转角（刃面朝上，不扎地）。"""
        d = Vector(hdir).normalized()
        q = self.axis.rotation_difference(d).to_matrix()
        best = None
        for k in range(24):
            M = Matrix.Rotation(math.radians(k * 15.0), 3, d) @ q
            zs = [(M @ p).z for p in self.pts]
            h = max(zs) - min(zs)
            if best is None or h < best[0] - 1e-6:
                best = (h, k * 15.0, min(zs))
        M = Matrix.Rotation(math.radians(best[1]), 3, d) @ q
        return M @ restR, best[2]


HOE = Hoe()


# ══ 加载 ════════════════════════════════════════════════════════════════════
def load():
    """导入旧 glb（几何不动）+ 加 sack 骨 + 建金袋。返回 (root, arm, meshes)。"""
    bpy.ops.import_scene.gltf(filepath=SRC)
    sc = bpy.context.scene
    root = next(o for o in sc.objects if o.type == "EMPTY")
    arm = next(o for o in sc.objects if o.type == "ARMATURE")
    for o in [o for o in sc.objects if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in sc.objects if o.type == "MESH"]
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()

    add_sack_bone(arm)
    HOE.measure(arm, meshes)
    sack = build_sack(arm)
    meshes = meshes + [sack]
    bpy.context.view_layer.update()
    return root, arm, meshes


def add_sack_bone(arm):
    """edit mode 加一根 sack 骨（父 chest，不连接）。其余 25 骨一个都不动。"""
    if "sack" in arm.data.bones:
        return arm.data.bones["sack"]
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones.new("sack")
    eb.head = SACK_HEAD
    eb.tail = SACK_TAIL
    eb.roll = 0.0
    eb.parent = arm.data.edit_bones["chest"]
    eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    print("[sack bone] head", tuple(round(v, 3) for v in SACK_HEAD),
          "tail", tuple(round(v, 3) for v in SACK_TAIL), "parent chest")
    return arm.data.bones["sack"]


# ══ 金袋：几何 ═════════════════════════════════════════════════════════════
MATS = {
    "麻布": ("#A6956F", 0.94, 0.0),
    "麻布暗": ("#6F6450", 0.96, 0.0),
    "金": ("#E0B34C", 0.26, 0.86),
    "team": ("#2E5FB4", 0.56, 0.0),
}

# 鼓胀麻袋的 8 站：(y, z, 中心 x, 宽, 厚, 倒角)
#   袋口在左肩**前下方**（胸侧，左手抓得住）→ 细颈过肩 → 袋身压过左肩靠后最鼓
#   → 往后、沿背后垂下 → 袋底收口。
#   内壁全程留在 x <= -0.18（头/帽实测 |x|<=0.13、胸 |x|<=0.196），所以不遮脸、不穿胸。
SACK_ROWS = [
    (0.266, 0.930, -0.306, 0.062, 0.058, 0.012),
    (0.186, 0.980, -0.302, 0.082, 0.074, 0.016),
    (0.152, 1.034, -0.300, 0.092, 0.084, 0.018),
    (0.088, 1.096, -0.296, 0.118, 0.110, 0.024),
    (0.020, 1.142, -0.290, 0.166, 0.142, 0.036),
    (-0.052, 1.158, -0.288, 0.204, 0.174, 0.046),
    (-0.130, 1.086, -0.286, 0.214, 0.188, 0.048),
    (-0.188, 0.994, -0.284, 0.178, 0.164, 0.040),
    (-0.212, 0.920, -0.282, 0.106, 0.100, 0.020),
]


# 金袋做成可复用组件：几何/骨/权重都在 库/comp_sack.py，这里只给站表与材质
SACK = CS.Sack(SACK_ROWS, MATS)


def add_sack_bone(arm):
    """sack 骨：父 chest，head 落在胸腔内部（不扛袋子时缩 0.001 藏起来）。"""
    return SACK.add_bone(arm, SACK_HEAD, SACK_TAIL)


def build_sack(arm):
    """金袋网格（组件实现见 库/comp_sack.py）。"""
    return SACK.build(arm)


# ══ 袋口世界点（任意姿态）══════════════════════════════════════════════════
def sack_mouth(P):
    """当前姿态下袋口的世界点（袋口相对 sack 骨静止几何不变）。"""
    return SACK.mouth(P, SACK_MOUTH)


def sack_bone_rot(P, pitch=0.0, roll=0.0, yaw=0.0):
    """袋子自己的轻晃（绕骨 head 转，幅度小，不会穿肩）。"""
    SACK.rot(P, pitch, roll, yaw)


def build_rig():
    return next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
