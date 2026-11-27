"""poselib2.py —— 精模单位的姿态层（与 unitkit2 配套，与 anim_tools 无关）

口径与《单位资产规范》一致：
  * 骨架空间 = 世界空间（armature 在原点、无旋转）；骨局部 Y 是骨轴。
  * 躯干走 FK（hips→spine→chest→neck→head），四肢走**双骨解析 IK**：
    手/脚落在目标点，不手调角度。
  * 所有姿态先算"世界朝向 R[骨] + 世界骨根 T[骨]"，最后按父链换算成 basis 四元数。

比 anims_火枪手 多出来的两件事（精模需要）：
  * `P.LOC[骨] = Vector` —— 骨局部平移（十字利刃飞出去 / 收回来靠这一条）
  * `P.SCL[骨] = f`     —— 骨缩放（傀儡纹路脉冲 / 施法闪电出现靠这一条）
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 30


def ik2(root, target, l1, l2, pole):
    """双骨解析 IK：返回中间关节位置。pole 决定弯曲方向。"""
    root, target = Vector(root), Vector(target)
    d = target - root
    dist = min(d.length, (l1 + l2) * 0.999)
    if dist < 1e-5:
        return root + Vector((0, 0, 1)) * l1
    dn = d.normalized()
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - a * a, 0.0))
    p = Vector(pole) - dn * Vector(pole).dot(dn)
    if p.length < 1e-6:
        p = Vector((0, 0, 1)) - dn * dn.z
    p.normalize()
    return root + dn * a + p * h


class Rig:
    def __init__(self, arm):
        self.arm = arm
        self.rest = {}
        self.parent = {}
        self.kids = {}
        self.length = {}
        for b in arm.data.bones:
            self.rest[b.name] = (b.head_local.copy(), b.matrix_local.to_3x3().copy())
            self.parent[b.name] = b.parent.name if b.parent else None
            self.length[b.name] = b.length
            self.kids.setdefault(b.name, [])
        for n, p in self.parent.items():
            if p:
                self.kids.setdefault(p, []).append(n)
        self.order = []
        self._walk("root", set())
        # 站姿用的默认落脚点（取 foot_R 的静止位置）
        fh = self.rest.get("foot_R", (Vector((0.11, 0.015, 0.10)), None))[0]
        self.foot_x = abs(fh.x)
        self.foot_z = fh.z

    def _walk(self, n, seen):
        if n in seen:
            return
        seen.add(n)
        self.order.append(n)
        for k in self.kids.get(n, []):
            self._walk(k, seen)

    def subtree(self, bone):
        out = []
        self._collect(bone, out)
        return out

    def _collect(self, n, out):
        out.append(n)
        for k in self.kids.get(n, []):
            self._collect(k, out)

    def L(self, bone):
        return self.length.get(bone, 0.1)


class Frame:
    """一帧姿态：R[骨] = 世界朝向，T[骨] = 世界骨根位置。"""

    def __init__(self, rig):
        self.rig = rig
        self.R = {n: rig.rest[n][1].copy() for n in rig.order}
        self.T = {n: rig.rest[n][0].copy() for n in rig.order}
        self.offset = Vector((0, 0, 0))
        self.LOC = {}
        self.SCL = {}
        self.TFIX = {}          # 骨根世界位置覆写（骑手挂鞍点用，见 place()）
        self.legargs = {}       # 每侧最后一次 IK 的入参（落地校正要重解）

    # ── 朝向 ────────────────────────────────────────────────────────────────
    def apply(self, bone, M, chain=True):
        for n in ([bone] + self.rig.subtree(bone)[1:] if chain else [bone]):
            self.R[n] = M @ self.R[n]

    def rot(self, bone, axis, deg, chain=True):
        if abs(deg) < 1e-9:
            return
        self.apply(bone, Matrix.Rotation(math.radians(deg), 3, Vector(axis)), chain)

    def set_world(self, bone, R_new, chain=True):
        delta = R_new @ self.R[bone].inverted()
        self.apply(bone, delta, chain)

    def aim(self, bone, direction, chain=True):
        cur = (self.R[bone] @ Vector((0, 1, 0))).normalized()
        d = Vector(direction).normalized()
        q = cur.rotation_difference(d)
        self.apply(bone, q.to_matrix(), chain)

    def solve_T(self):
        for n in self.rig.order:
            if n in self.TFIX:
                self.T[n] = Vector(self.TFIX[n])
                continue
            p = self.rig.parent.get(n)
            if p is None:
                self.T[n] = self.rig.rest[n][0] + self.offset
            else:
                off = self.rig.rest[p][1].inverted() @ (self.rig.rest[n][0] - self.rig.rest[p][0])
                self.T[n] = self.T[p] + self.R[p] @ off
            # 骨自身的局部平移（`hold` 的换把 / 滑杆、`weapon_loc`）必须算进骨根：
            # 以前这里只把 LOC 交给 Writer 写关键帧，Frame 自己的 T 不含它，于是
            # **挂在武器骨下面的零件**（弓箭手的弓弦）会整体少一个握持半径 ——
            # v3 的弦一直停在该在的位置前 10 cm，就是这么来的。
            loc = self.LOC.get(n)
            if loc is not None:
                self.T[n] = self.T[n] + self.R[n] @ Vector(loc)

    def place(self, bone, world_T, world_R=None, chain=True):
        """把一根骨**整体搬到世界点**（骑手跟随马背鞍点 / 摔下马）。

        与 arm/leg 的分工：那两个只解关节角度、骨根仍挂在父链上；这里连骨根位置一起给，
        同一根骨可以从"跟着马"无缝切到"摔在地上"，不需要第二副骨架。

        位置写进 P.LOC（骨局部平移），所以这根骨必须放进 Writer 的 loc_bones。
        同时记 TFIX，后续再调 solve_T 时它不会掉回父链算出来的位置（子骨跟着走）。
        """
        if world_R is not None:
            self.set_world(bone, world_R, chain)
        p = self.rig.parent.get(bone)
        rb = self.rig.rest[bone]
        if p is None:
            self.TFIX[bone] = Vector(world_T)
            self.T[bone] = Vector(world_T)
            self.offset = Vector(world_T) - rb[0]
            return
        rp = self.rig.rest[p]
        self.T.pop(bone, None)
        self.TFIX.pop(bone, None)
        self.solve_T()
        rel = rp[1].inverted() @ (rb[0] - rp[0])
        base = self.T[p] + self.R[p] @ rel
        M = self.R[p] @ (rp[1].inverted() @ rb[1])
        self.LOC[bone] = M.inverted() @ (Vector(world_T) - base)
        self.TFIX[bone] = Vector(world_T)
        self.T[bone] = Vector(world_T)
        for k in self.rig.subtree(bone)[1:]:
            self.T.pop(k, None)

    # ── 四肢 IK ─────────────────────────────────────────────────────────────
    def arm(self, side, wrist, pole):
        self.solve_T()
        S = self.T["upperarm_" + side]
        W = Vector(wrist)
        l1 = self.rig.L("upperarm_" + side)
        l2 = self.rig.L("forearm_" + side)
        E = ik2(S, W, l1, l2, pole)
        self.aim("upperarm_" + side, E - S, chain=False)
        self.aim("forearm_" + side, W - E, chain=False)

    def leg(self, side, ankle, pole, foot_pitch=0.0, foot_yaw=0.0, foot_roll=0.0):
        self.legargs[side] = (Vector(ankle), pole, foot_pitch, foot_yaw, foot_roll)
        self.solve_T()
        H = self.T["thigh_" + side]
        A = Vector(ankle)
        K = ik2(H, A, self.rig.L("thigh_" + side), self.rig.L("shin_" + side), pole)
        self.aim("thigh_" + side, K - H, chain=False)
        self.aim("shin_" + side, A - K, chain=False)
        rest_f = self.rig.rest["foot_" + side][1]
        R = (Matrix.Rotation(math.radians(foot_yaw), 3, "Z")
             @ Matrix.Rotation(math.radians(foot_pitch), 3, "X")
             @ Matrix.Rotation(math.radians(foot_roll), 3, "Y"))
        self.set_world("foot_" + side, R @ rest_f, chain=True)

    def feet(self, lift=(0.0, 0.0), pitch=(0.0, 0.0), yaw=(0.0, 0.0),
             dx=0.0, dy=0.0, spread=0.0):
        for i, (side, s) in enumerate((("R", 1), ("L", -1))):
            A = Vector((s * (self.rig.foot_x + spread) + dx, 0.015 + dy,
                        self.rig.foot_z + lift[i]))
            self.leg(side, A, (s * 0.35, 1.0, 0.10), pitch[i], yaw[i])

    # ── 武器插座 ────────────────────────────────────────────────────────────
    def weapon_loc(self, bone, y=0.0, x=0.0, z=0.0):
        self.LOC[bone] = Vector((x, y, z))

    def weapon_spin(self, bone, deg):
        self.rot(bone, (0, 1, 0), deg, chain=False)


def new_action(arm, name):
    if arm.animation_data is None:
        arm.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0] if act.slots else \
            act.slots.new("OBJECT", "Slot")
    except Exception:
        pass
    return act


def fcurves(act):
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
    except Exception:
        pass
    return out


def finish_action(act):
    for fc in fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


class Writer:
    """把 Frame 写成关键帧。旋转全骨都写；LOC/SCL 只写用到的骨。"""

    def __init__(self, rig, loc_bones=(), scl_bones=()):
        self.rig = rig
        self.prev = {}
        self.loc_bones = set(loc_bones)
        self.scl_bones = set(scl_bones)

    def key(self, P, frame):
        for n in self.rig.order:
            p = self.rig.parent.get(n)
            rn = P.R[n]
            if p is None:
                basis = self.rig.rest[n][1].inverted() @ rn
            else:
                off = self.rig.rest[p][1].inverted() @ self.rig.rest[n][1]
                basis = off.inverted() @ (P.R[p].inverted() @ rn)
            q = basis.to_quaternion()
            pq = self.prev.get(n)
            if pq is not None and q.dot(pq) < 0:
                q.negate()
            self.prev[n] = q.copy()
            pb = self.rig.arm.pose.bones[n]
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            if n == "root":
                loc = self.rig.rest[n][1].inverted() @ (P.T[n] - self.rig.rest[n][0])
                pb.location = loc
                pb.keyframe_insert("location", frame=frame)
            elif n in P.LOC or n in self.loc_bones:
                pb.location = P.LOC.get(n, Vector((0, 0, 0)))
                pb.keyframe_insert("location", frame=frame)
            if n in P.SCL or n in self.scl_bones:
                s = P.SCL.get(n, 1.0)
                pb.scale = (s, s, s) if not hasattr(s, "__len__") else (s[0], s[1], s[2])
                pb.keyframe_insert("scale", frame=frame)


def stance(P, dz=0.0, dx=0.0, dy=0.0,
           hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
           spine_pitch=0.0, spine_yaw=0.0, spine_roll=0.0,
           chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
           head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
           legs=True):
    P.offset = Vector((dx, dy, dz))
    P.rot("hips", (0, 0, 1), hips_yaw)
    P.rot("hips", (1, 0, 0), hips_pitch)
    P.rot("hips", (0, 1, 0), hips_roll)
    P.rot("spine", (1, 0, 0), spine_pitch)
    P.rot("spine", (0, 0, 1), spine_yaw)
    P.rot("spine", (0, 1, 0), spine_roll)
    P.rot("chest", (1, 0, 0), chest_pitch)
    P.rot("chest", (0, 0, 1), chest_yaw)
    P.rot("chest", (0, 1, 0), chest_roll)
    P.rot("head", (0, 0, 1), head_yaw - chest_yaw * 0.5 - hips_yaw * 0.35 - spine_yaw * 0.5)
    P.rot("head", (1, 0, 0), head_pitch - chest_pitch * 0.5 - spine_pitch * 0.4)
    P.rot("head", (0, 1, 0), head_roll - chest_roll * 0.6)
    if legs:
        P.feet()


def loop_key(P0, P1):
    """把 P0 的姿态抄给 P1（循环首末帧逐骨相等，避免浮点漂移）。"""
    for n in P0.rig.order:
        P1.R[n] = P0.R[n].copy()
        P1.T[n] = P0.T[n].copy()
    P1.offset = P0.offset.copy()
    P1.LOC = dict(P0.LOC)
    P1.SCL = dict(P0.SCL)
    return P1


def drop_to(P, bone, target_T, target_R, k):
    """把一根骨从「跟着父链」平滑过渡到**世界目标位姿**（k = 0…1）。

    阵亡里"武器脱手"专用：k=0 时武器还在手上（完全跟随手掌），k=1 时已经躺在地上。
    中间用四元数 slerp + 位置 lerp，所以不会在脱手那一帧跳一下。
    走 place()，所以骨骼必须放进 Writer 的 loc_bones。target_R 收 Matrix 或 Quaternion。
    """
    P.solve_T()
    T0 = P.T[bone].copy()
    q0 = P.R[bone].to_quaternion()
    q1 = target_R.to_quaternion() if hasattr(target_R, "to_quaternion") else target_R.copy()
    q = q0.slerp(q1, k)
    T = T0.lerp(Vector(target_T), k)
    P.place(bone, T, q.to_matrix(), chain=True)
    return T


# ══ 落地校正 ════════════════════════════════════════════════════════════════
class Sole:
    """脚（爪）底的顶点云 —— 让"脚底真的踩在地上"变成一次测量，而不是一次估算。

    为什么不用解析公式：方块脚是矩形、还算得出来；豺狼人的爪是三趾、精模的靴子
    带倒角，`foot_clear()` 这类式子总有几毫米残差（实测 -11 mm，全动作都在切地）。
    这里取该骨 100% 权重的顶点换算到骨局部坐标，逐帧乘当前骨矩阵取最低点，
    差多少就把踝抬多少、再解一次 IK —— 两轮必收敛，误差 < 0.2 mm。
    """

    def __init__(self, arm, meshes, bones=("foot_R", "toe_R", "foot_L", "toe_L")):
        self.arm = arm
        self.pts = {b: [] for b in bones}
        for ob in meshes:
            names = {g.name: g.index for g in ob.vertex_groups}
            mw = ob.matrix_world
            for b in bones:
                if b not in names:
                    continue
                gi = names[b]
                inv = arm.data.bones[b].matrix_local.inverted()
                for v in ob.data.vertices:
                    for g in v.groups:
                        if g.group == gi and g.weight > 0.5:
                            self.pts[b].append(inv @ (mw @ v.co))
                            break
        for b, ps in list(self.pts.items()):
            if len(ps) > 460:                      # 只要最低那一层，够判高度
                zs = sorted(ps, key=lambda p: p.z)[:460]
                self.pts[b] = zs

    def ok(self):
        """每侧**至少有一根骨**有点云就够 —— 方块人的脚是一整块（toe 骨没有蒙皮），
        严格要求四根骨都有点会让整条落地校正在方块人身上静默失效。"""
        sides = sorted({b.rsplit("_", 1)[-1] for b in self.pts})
        return all(any(self.pts.get(b) for b in self.pts if b.endswith("_" + s))
                   for s in sides)

    def low(self, P, bone):
        ps = self.pts.get(bone) or ()
        if not ps:
            return 1e9
        T, R = P.T[bone], P.R[bone]
        z = 1e9
        for p in ps:
            q = T + R @ p
            if q.z < z:
                z = q.z
        return z

    def side_low(self, P, side):
        """一侧的最低点：脚掌 + 脚趾（爪尖在 toe 骨上，只测 foot 会漏 1 cm）。"""
        P.solve_T()
        z = 1e9
        for b, ps in self.pts.items():
            if b.endswith("_" + side) and ps:
                z = min(z, self.low(P, b))
        return z


def ground(P, sole, target=0.0015, iters=3, sides=("R", "L")):
    """把两只脚**抬到**脚底刚好贴地（只抬不压，所以不会影响抬脚/腾空帧）。

    注意：`aim()` 只改朝向不改 T，所以量高度之前必须 `solve_T()` 一次，
    否则用的是上一帧的骨根位置（实测左脚会差 17 cm，校正直接失效）。
    """
    if sole is None or not sole.ok():
        return P
    for side in sides:
        if side not in P.legargs:          # legargs 用 "R"/"L" 索引，不是骨名
            continue
        for _ in range(iters):
            P.solve_T()
            z = sole.side_low(P, side)
            d = target - z
            if d <= 0.0003:
                break
            ank, pole, fp, fy, fr = P.legargs[side]
            P.leg(side, ank + Vector((0.0, 0.0, d)), pole, fp, fy, fr)
    return P


# ══ 通用姿态小工具（萨满 / 战士 / 斥候 共用）══════════════════════════════════
def mix(a, b, u):
    if a is None or b is None:          # 非数值参数（如 grip=None）原样传
        return a if u < 1.0 else b
    if isinstance(a, (tuple, list)):
        return tuple(mix(x, y, u) for x, y in zip(a, b))
    if isinstance(a, Vector):
        return Vector(a).lerp(Vector(b), u)
    return a + (b - a) * u


def bake(keys, D, emit):
    """keys = [(frame, 参数字典)] —— 段内 smoothstep，逐帧回调。"""
    keys = sorted(keys, key=lambda kv: kv[0])
    for i in range(D + 1):
        j = 0
        while j + 1 < len(keys) and keys[j + 1][0] <= i:
            j += 1
        f0, a = keys[j]
        f1, b = keys[min(j + 1, len(keys) - 1)]
        u = 0.0 if f1 == f0 else (i - f0) / float(f1 - f0)
        u = max(0.0, min(1.0, u))
        u = u * u * (3.0 - 2.0 * u)
        emit(i, {k: mix(a[k], b[k], u) for k in a})


def hand_rot(P, side, pitch=0.0, roll=0.0, yaw=0.0):
    """把手的**世界朝向**定在"静止姿态 + 一个世界旋转"上（手里的东西跟着它走）。"""
    rest = P.rig.rest["hand_" + side][1]
    M = (Matrix.Rotation(math.radians(yaw), 3, "Z")
         @ Matrix.Rotation(math.radians(pitch), 3, "X")
         @ Matrix.Rotation(math.radians(roll), 3, "Y"))
    P.set_world("hand_" + side, M @ rest)
    return M


def grip_pose(P, side, target, off, pitch=0.0, roll=0.0, yaw=0.0,
              pole=(0.55, -0.55, -0.75)):
    """把手心（=武器握点）放到世界点 target，同时把武器转到 (pitch, roll, yaw)。"""
    M = hand_rot(P, side, pitch, roll, yaw)
    wrist = Vector(target) - (M @ Vector(off))
    P.arm(side, wrist, pole)
    return wrist


def aim_hand(P, side, direction, pole):
    P.aim("hand_" + side, Vector(direction).normalized())


def grip_at(P, side, target, blade, roll=0.0, pole=(0.55, -0.55, -0.75)):
    """把**掌心**放到 world target，刃轴指向 blade（roll = 绕刃轴自转）。

    比 `hand_rot(pitch, roll, yaw)` 好用：那三个角是"绕世界 XYZ 转多少度"，
    脑子里要先想清楚刃尖最后朝哪；这里直接给"刃尖朝哪"，转动由最小的那一个
    四元数补出来，roll 只负责刃口翻面。

    前提：该单位的武器轴线 = hand 骨的 +Y（豺狼人双匕、破法者利刃都是这样；
    人类的剑挂在 weapon_R 上，轴线不同，别用这个）。
    """
    bone = "hand_" + side
    rest = P.rig.rest[bone][1]
    d = Vector(blade).normalized()
    d0 = (rest @ Vector((0, 1, 0))).normalized()
    R = d0.rotation_difference(d).to_matrix() @ rest
    if abs(roll) > 1e-9:
        R = Matrix.Rotation(math.radians(roll), 3, d) @ R
    P.set_world(bone, R, chain=True)
    gl = getattr(P.rig, "grip_local", {}).get(side)
    if gl is None:
        gl = Vector((0.0, 0.030, 0.0))
    wrist = Vector(target) - R @ gl
    P.arm(side, wrist, pole)
    return wrist


def aim_weapon(P, side, blade_bone, direction, roll=0.0):
    """把**武器骨**（weapon_R 之类）的 +Y 指向 direction，握它的手跟着一起转。

    人类步兵的剑挂在 weapon_R 上，骨轴是"腕→剑尖"，跟 hand 骨的轴不是一回事，
    所以不能直接 aim hand。这里把手当成一个刚体握把：转手 = 转剑。
    """
    P.solve_T()
    cur = (P.R[blade_bone] @ Vector((0, 1, 0))).normalized()
    d = Vector(direction).normalized()
    M = cur.rotation_difference(d).to_matrix()
    if abs(roll) > 1e-9:
        M = Matrix.Rotation(math.radians(roll), 3, d) @ M
    P.apply("hand_" + side, M, chain=True)
    return M


def sword_at(P, side, wrist, direction, roll=0.0, pole=(0.60, 0.18, -0.78),
             blade_bone="weapon_R"):
    """剑：腕点在 wrist，剑轴指向 direction。先转手（连带剑），再解手臂。"""
    aim_weapon(P, side, blade_bone, direction, roll)
    P.arm(side, wrist, pole)
    return wrist
