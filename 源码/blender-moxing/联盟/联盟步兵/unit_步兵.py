"""unit_步兵.py —— 联盟步兵（方块人）的**骨架接入层**（v3 动作重做，模型不动）

v3 只做一件事：给旧模型换一套动作。**几何一个顶点都不改。**

模型来自 `库/_ref/联盟/方块人_联盟步兵.glb`（3,356 面 / 3 网格 / 25 骨），
`build_rig()` 直接返回导入的骨架，没有任何重建流程。

## 这个骨架和精模那套的三个差别（写动作前必须先看）
1. **`shield` 骨挂在 `chest` 下，不挂在 `hand_L` 下**。也就是说盾和左手是两条独立的链：
   你摆手，盾不会跟；你摆盾，手不会跟。旧版就是这里出错 —— 待机时手贴着盾，
   一走起来手甩出去、盾还留在胯上。
   → 本文件用 `shield_frame()` / `weld_shield()` 把两边**焊死**：
     先算盾的目标世界位姿（位置 + 盾面法线 + 盾面竖轴），再反推腕点和手掌朝向，
     IK 上去，最后用 `place()` 把盾骨钉到同一个位姿上。任何一帧手都不会离开盾。
2. **脚是方块脚**：踝在 z=0.115，脚掌连 heel(−0.128) 到 toe(+0.195)。
   `foot_clear(pitch)` 按这个矩形算，别再拿精模那套参数。
3. **武器骨 `weapon_R` 的骨轴朝上**（head 在腕、tail 在 +Z 上方），剑身永远是"柄在下、
   刃在上"的静止朝向 —— 挥砍靠手（`hand_rot` 的 pitch），不是靠 `weapon_R`。

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

import poselib2 as PL  # noqa: E402

NAME = "方块人_联盟步兵"
KEY = "联盟步兵"
SRC = os.path.join(LIB, "_ref", "联盟", "方块人_联盟步兵.glb")
ASSET = os.path.join(os.path.dirname(ROOT), "assets", "单位", "联盟", "联盟步兵")

# ── 骨架关键点（probe 实测）────────────────────────────────────────────────
Z_HIP = 0.674
Z_WAIST = 0.799
Z_CHEST = 0.968
Z_SHLD = 1.043
Z_NECK = 1.106
Z_HEAD = 1.187
Z_TOP = 1.268
HIP_X = 0.124
SH_X = 0.313
Z_ANKLE = 0.115
HEEL_Y = -0.128
TOE_Y = 0.195

WRI_R = Vector((0.313, 0.081, 0.687))
WRI_L = Vector((-0.313, 0.081, 0.687))
ELB_R = Vector((0.313, 0.025, 0.864))
ELB_L = Vector((-0.313, 0.025, 0.864))

# ── 盾：点云主轴（PCA 实测）────────────────────────────────────────────────
SH_C0 = Vector((-0.4232, 0.1933, 0.8646))          # 盾的几何中心
SH_H0 = Vector((-0.366, 0.138, 0.922))             # shield 骨的 head
SH_N0 = Vector((-0.870, 0.492, -0.030)).normalized()   # 盾面法线（朝外侧前方）
SH_U0 = Vector((0.043, 0.135, 0.990)).normalized()     # 盾面竖轴（长轴）
SH_X0 = SH_N0.cross(SH_U0).normalized()                # 盾面横轴（右手系）
M0 = Matrix((
    (SH_X0.x, SH_N0.x, SH_U0.x),
    (SH_X0.y, SH_N0.y, SH_U0.y),
    (SH_X0.z, SH_N0.z, SH_U0.z),
))                                              # 盾网格在静止姿态下的朝向
# 腕点在"盾坐标系"里的偏移（焊接用，算一次）
OFF_WRIST_L = M0.transposed() @ (WRI_L - SH_C0)
OFF_CEN = SH_C0 - SH_H0                          # 盾心相对盾骨 head

BONES_OK = ("root", "hips", "spine", "chest", "neck", "head",
            "shoulder_R", "upperarm_R", "forearm_R", "hand_R", "weapon_R",
            "shoulder_L", "upperarm_L", "forearm_L", "hand_L", "weapon_L",
            "shield", "thigh_R", "shin_R", "foot_R", "toe_R",
            "thigh_L", "shin_L", "foot_L", "toe_L")


# ── 剑：静止时的网格朝向（用于"躺平"时把刀面朝上，别让护手竖着扎地）──────
_SW_D0 = Vector((0.364 - 0.313, 0.100 - 0.081, 0.864 - 0.687)).normalized()
_SW_N0 = (Vector((0, 1, 0)) - _SW_D0 * _SW_D0.y)
_SW_N0.normalize()
_SW_X0 = _SW_N0.cross(_SW_D0).normalized()
M0S = Matrix(((_SW_X0.x, _SW_N0.x, _SW_D0.x),
              (_SW_X0.y, _SW_N0.y, _SW_D0.y),
              (_SW_X0.z, _SW_N0.z, _SW_D0.z)))


def sword_floor_rot(restR, blade_dir=(0.20, -0.955, 0.02), face_up=(0.0, 0.0, 1.0)):
    """剑躺平时骨的世界朝向：刃轴水平 + 刀面朝上（否则护手会竖着切进地里 15 cm）。"""
    d = Vector(blade_dir).normalized()
    n = Vector(face_up)
    n = (n - d * n.dot(d)).normalized()
    x = n.cross(d).normalized()
    Mt = Matrix(((x.x, n.x, d.x), (x.y, n.y, d.y), (x.z, n.z, d.z)))
    return Mt @ M0S.transposed() @ restR


class Spec:
    """动作层要用的尺寸量（只读）。"""

    def __init__(self):
        self.ANK = Vector((HIP_X, 0.0, Z_ANKLE))
        self.HIP = Vector((HIP_X, 0.0, Z_HIP))
        self.SH = Vector((SH_X, 0.0, Z_SHLD))
        self.Z_ANKLE = Z_ANKLE
        self.HEEL_Y = HEEL_Y
        self.TOE_Y = TOE_Y
        self.H = 1.755

    def foot_clear(self, pitch_deg):
        """方块脚绕踝转 pitch 后，踝要高到多少脚底才不切地。"""
        p = math.radians(pitch_deg)
        sp, cp = math.sin(p), math.cos(p)
        lo = 0.0
        for y in (HEEL_Y, TOE_Y):
            lo = max(lo, -(-Z_ANKLE * cp + y * sp))
        return lo


S = Spec()


# ══ 加载 ────────────────────────────────────────────────────────────────────
def load():
    """导入旧 glb，返回 (root_empty, armature, meshes)。不清动作、不动几何。"""
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
    return root, arm, meshes


def build_rig():
    """兼容 run_unit 的入口：返回导入的骨架（需要在 load() 之后调用）。"""
    return next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")


# ══ 盾：位姿 → 手 ═══════════════════════════════════════════════════════════
def frame_of(normal, up=(0.0, 0.0, 1.0)):
    """由"盾面法线 + 大致的竖轴"造一个右手正交基（列 = X,Y,Z）。"""
    n = Vector(normal).normalized()
    u = Vector(up)
    u = (u - n * u.dot(n))
    if u.length < 1e-6:
        u = Vector((0, 0, 1))
    u.normalize()
    x = n.cross(u).normalized()
    return Matrix(((x.x, n.x, u.x), (x.y, n.y, u.y), (x.z, n.z, u.z)))


def shield_target(pos, normal, up=(0.0, 0.0, 1.0)):
    """盾心放在 pos、盾面法线朝 normal 时的 (盾网格世界朝向 M, 盾骨世界位置 T)。"""
    M = frame_of(normal, up)
    T = Vector(pos) - M @ OFF_CEN
    return M, T


def weld_shield(P, pos, normal, up=(0.0, 0.0, 1.0), pole=(-0.70, 0.30, -0.64),
                extra=(0.0, 0.0, 0.0), grip=None):
    """把盾摆到 (pos, normal)，并把左手 IK 上去、手掌朝向一起拧 —— 手和盾从此焊死。

    `grip` 是"握点在盾局部系里的偏移"（x 沿盾面横轴、y 沿盾面法线、z 沿盾面竖轴）。
    不给就用静止姿态量出来的 OFF_WRIST_L —— 那是**盾挂在体侧**时的相对位置
    （腕在盾心内下 18 cm）。举盾时盾要压到胸前，那个位置会把腕推进胯里，
    所以要换成"腕在盾背中部"的 (−0.02, −0.112, −0.10)。

    返回 (腕点, 盾的世界朝向 M)，方便调用方做二次微调。
    """
    M, T = shield_target(Vector(pos) + Vector(extra), normal, up)
    D = M @ M0.transposed()                      # 盾网格相对静止朝向的增量
    gl = Vector(grip) if grip is not None else OFF_WRIST_L
    wrist = Vector(pos) + Vector(extra) + M @ gl
    P.arm("L", wrist, pole)
    P.set_world("hand_L", D @ P.rig.rest["hand_L"][1])
    P.place("shield", T, D @ P.rig.rest["shield"][1])
    return wrist, M


def rest_shield(P):
    """不举盾时：盾回到静止位姿（仍然是焊在手上的）。"""
    return weld_shield(P, SH_C0, SH_N0, SH_U0)


def shield_at_rest_frame(P):
    """按"手在静止位置"直接放盾（用在手完全不动、只做躯干呼吸的动作里，省一次 IK）。"""
    wrist = P.T["hand_L"] if "hand_L" in P.T else WRI_L
    _ = wrist
    P.place("shield", SH_H0, P.rig.rest["shield"][1])
