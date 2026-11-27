"""anims_火枪手.py —— 火枪手的姿态层与 7 条动作

姿态算法与《单位资产规范》一致：**手/脚落在目标点（双骨解析 IK），不手调角度**。
躯干走 FK（hips→spine→chest→neck→head），四肢走 IK；武器直接写世界朝向，
手骨跟着武器转（枪是 hand_R 的子骨，只能这么反解）。

坐标系：骨架空间 = 世界空间（armature 在原点、无旋转）；骨局部 Y 是骨轴。
所有姿态先算"世界朝向 R[骨]"，最后按父链换算成 basis 四元数写入关键帧。

命名（与联盟单位同一套）：idle / walk / attack / hurt / death / cast（引擎状态）
+ idle_alt / reload（剪辑附加，不进状态机）。
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

import unit_火枪手 as U

FPS = 30
L_UA, L_FA = U.L_UPPER, U.L_FORE
L_TH, L_SH = U.L_THIGH, U.L_SHIN

GUN_A_REST = U.GUN_A.copy()
GX_REST, GZ_REST = U.GX.copy(), U.GZ.copy()


def _Y():
    return Vector((0, 1, 0))


class Rig:
    def __init__(self, arm):
        self.arm = arm
        self.rest = {}
        self.parent = {}
        self.kids = {}
        for b in arm.data.bones:
            self.rest[b.name] = (b.head_local.copy(), b.matrix_local.to_3x3().copy())
            self.parent[b.name] = b.parent.name if b.parent else None
            self.kids.setdefault(b.name, [])
        for n, p in self.parent.items():
            if p:
                self.kids.setdefault(p, []).append(n)
        self.order = []
        self._walk("root", set())

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

    def length(self, bone):
        h, _ = self.rest[bone]
        p = self.parent[bone]
        if not p:
            return 0.12
        return (h - self.rest[p][0]).length if bone.startswith("weapon") else \
            (self._tail(bone) - h).length

    def _tail(self, bone):
        for b in self.arm.data.bones:
            if b.name == bone:
                return b.tail_local.copy()
        return Vector((0, 0, 0))


class Frame:
    """一帧姿态：R[骨] = 世界朝向，T[骨] = 世界骨根位置。"""

    def __init__(self, rig):
        self.rig = rig
        self.R = {n: rig.rest[n][1].copy() for n in rig.order}
        self.T = {n: rig.rest[n][0].copy() for n in rig.order}
        self.offset = Vector((0, 0, 0))
        self.rod_slide = 0.0

    # ── 基础操作 ────────────────────────────────────────────────────────────
    def apply(self, bone, M, chain=True):
        for n in ([bone] + self.rig.subtree(bone)[1:] if chain else [bone]):
            self.R[n] = M @ self.R[n]

    def rot(self, bone, axis, deg, chain=True):
        if abs(deg) < 1e-9:
            return
        self.apply(bone, Matrix.Rotation(math.radians(deg), 3, Vector(axis)), chain)

    def rot_l(self, bone, axis, deg, chain=True):
        if abs(deg) < 1e-9:
            return
        M = Matrix.Rotation(math.radians(deg), 3, Vector(axis))
        for n in ([bone] + self.rig.subtree(bone)[1:] if chain else [bone]):
            self.R[n] = self.R[n] @ M

    def set_world(self, bone, R_new, chain=True):
        delta = R_new @ self.R[bone].inverted()
        self.apply(bone, delta, chain)

    def aim(self, bone, direction, chain=True):
        cur = (self.R[bone] @ _Y()).normalized()
        d = Vector(direction).normalized()
        q = cur.rotation_difference(d)
        self.apply(bone, q.to_matrix(), chain)

    def solve_T(self):
        for n in self.rig.order:
            p = self.rig.parent[n]
            if p is None:
                self.T[n] = self.rig.rest[n][0] + self.offset
            else:
                # 偏移先转到父骨的**静止局部系**，再用父骨的姿态旋转摆出去
                off = self.rig.rest[p][1].inverted() @ (self.rig.rest[n][0] - self.rig.rest[p][0])
                self.T[n] = self.T[p] + self.R[p] @ off

    # ── 四肢 IK ────────────────────────────────────────────────────────────
    def arm(self, side, wrist, pole):
        self.solve_T()
        S = self.T["upperarm_" + side]
        W = Vector(wrist)
        E = _ik2(S, W, L_UA, L_FA, pole)
        self.aim("upperarm_" + side, E - S, chain=False)
        self.aim("forearm_" + side, W - E, chain=False)

    def leg(self, side, ankle, pole, foot_pitch=0.0):
        self.solve_T()
        H = self.T["thigh_" + side]
        A = Vector(ankle)
        K = _ik2(H, A, L_TH, L_SH, pole)
        self.aim("thigh_" + side, K - H, chain=False)
        self.aim("shin_" + side, A - K, chain=False)
        rest_f = self.rig.rest["foot_" + side][1]
        self.set_world("foot_" + side,
                       Matrix.Rotation(math.radians(foot_pitch), 3, "X") @ rest_f,
                       chain=True)

    def feet_planted(self, spread=0.0, lift=(0.0, 0.0), pitch=(0.0, 0.0)):
        for i, (side, s) in enumerate((("R", 1), ("L", -1))):
            A = Vector((s * U.LEG_X, 0.015 + spread,
                        U.Z_ANKLE + lift[i]))
            self.leg(side, A, (s * 0.35, 1.0, 0.10), pitch[i])

    # ── 武器 ────────────────────────────────────────────────────────────────
    def gun(self, butt, direction, aim=True):
        """把枪摆到 (butt, direction)：整只右手（含枪）跟着转，再解右臂到握把。"""
        d = Vector(direction).normalized()
        cur = (self.R["weapon_R"] @ _Y()).normalized()
        q = cur.rotation_difference(d)
        M = q.to_matrix()
        self.apply("hand_R", M)
        grip = Vector(butt) + d * U.GUN_L_BACK
        wrist = grip - M @ (U.FIST_R - U.WRI_R)
        self.arm("R", wrist, (0.75, -0.85, -0.35))
        return grip

    def gun_rest(self):
        """不摆枪：枪跟着右手/躯干走（rest 姿态）。"""
        pass


def gun_frame(direction):
    d = Vector(direction).normalized()
    M = GUN_A_REST.rotation_difference(d).to_matrix()
    return M @ GX_REST, M @ GZ_REST, d


def gpt(butt, direction, x, y, z):
    """枪局部点 → 世界（与 Frame.gun 的最短弧旋转一致）。"""
    ex, ez, d = gun_frame(direction)
    return Vector(butt) + ex * x + d * y + ez * z


def _ik2(root, target, l1, l2, pole):
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


# ── 姿态模板 ───────────────────────────────────────────────────────────────
def stance(P, dz=0.0, dx=0.0, dy=0.0,
           hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
           spine_pitch=0.0, spine_yaw=0.0,
           chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
           head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
           feet=None):
    """通用站姿：躯干 FK + 双脚落地。feet = [(lift, pitch), ...] 给走动用。"""
    P.offset = Vector((dx, dy, dz))
    P.rot("hips", (0, 0, 1), hips_yaw)
    P.rot("hips", (1, 0, 0), hips_pitch)
    P.rot("hips", (0, 1, 0), hips_roll)
    P.rot("spine", (1, 0, 0), spine_pitch)
    P.rot("spine", (0, 0, 1), spine_yaw)
    P.rot("chest", (1, 0, 0), chest_pitch)
    P.rot("chest", (0, 0, 1), chest_yaw)
    P.rot("chest", (0, 1, 0), chest_roll)
    # 头：先抵消一点躯干的转向（人看前方），再叠自己的角
    P.rot("head", (0, 0, 1), head_yaw - chest_yaw * 0.55 - hips_yaw * 0.35)
    P.rot("head", (1, 0, 0), head_pitch - chest_pitch * 0.5)
    P.rot("head", (0, 1, 0), head_roll - chest_roll * 0.6)
    if feet is None:
        P.feet_planted()
    elif feet != "free":
        P.feet_planted(lift=[f[0] for f in feet], pitch=[f[1] for f in feet])


def hand_belt(P):
    """左手搭在左胯（rest 姿态，跟着躯干走）。"""
    pass


def hand_to(P, target, pole=(-0.85, -0.55, -0.35)):
    P.arm("L", target, pole)


# ── 关键帧写入 ─────────────────────────────────────────────────────────────
class Writer:
    def __init__(self, rig):
        self.rig = rig
        self.prev = {}

    def key(self, P, frame):
        for n in self.rig.order:
            p = self.rig.parent[n]
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
            elif n == "prop_ramrod":
                pb.location = Vector((0, P.rod_slide, 0))
                pb.keyframe_insert("location", frame=frame)


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


def finish_action(act, arm):
    """曲线收尾：贝塞尔 + 首末帧数值对齐。"""
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"
        fc.update()


def _fcurves(act):
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
    except Exception:
        pass
    return out


# ── 动作 ───────────────────────────────────────────────────────────────────
def a_idle(rig, D=120):
    """待机 4.0s：两次呼吸 + 重心左右 + 一次轻微的看四周。"""
    act = new_action(rig.arm, "idle")
    W = Writer(rig)
    keys = [
        (0,   0.000, 0.000, 0.0, 0.0, 0.0, 0.0, 0.0),
        (18,  0.006, 0.004, -0.8, 1.2, -1.6, 0.0, 2.0),
        (36, -0.004, 0.008, 0.6, -1.0, 0.9, 0.6, 1.0),
        (54,  0.004, 0.004, -0.6, 1.0, -1.2, 0.4, -1.5),
        (72, -0.003, -0.004, 0.5, -0.8, 0.8, -0.4, -3.0),
        (90,  0.005, -0.006, -0.7, 1.1, -1.4, -0.6, -1.0),
        (108, -0.002, -0.002, 0.4, -0.6, 0.6, -0.2, 0.0),
        (120, 0.000, 0.000, 0.0, 0.0, 0.0, 0.0, 0.0),
    ]
    for (f, dz, sway, roll, breath, headyaw, headpitch, hipyaw) in keys:
        P = Frame(rig)
        stance(P, dz=dz, dx=sway, hips_yaw=hipyaw, hips_roll=roll,
               chest_pitch=breath, spine_pitch=breath * 0.5,
               head_yaw=headyaw, head_pitch=headpitch)
        W.key(P, f)
    finish_action(act, rig.arm)
    return act


def a_idle_alt(rig, D=150):
    """悠闲 5.0s：把枪往肩上一沉、抬手捋两下胡子、扭头看一眼。"""
    act = new_action(rig.arm, "idle_alt")
    W = Writer(rig)
    GUT = U.GUN_G.copy()
    AR = GUN_A_REST

    def base(P, dz=0.0, hy=0.0, hp=0.0, cp=0.0, chy=0.0, gun=True):
        stance(P, dz=dz, hips_yaw=hy * 0.3, chest_yaw=chy, chest_pitch=cp,
               head_yaw=hy, head_pitch=hp)

    # 捋胡子的三个阶段：手在胡子前 / 往下 / 回腰带
    def stroke(P, t, head_pitch):
        # t=0 手在胡子中段，t=1 顺到胡子下缘（掌根贴着胡子走）
        target = Vector((-0.030, 0.318 - 0.012 * t, 0.960 - 0.115 * t))
        P.arm("L", target, (-0.9, -0.30, -0.55))

    seq = [
        (0,   dict(dz=0.0, hy=0, hp=0, cp=0)),
        (18,  dict(dz=-0.008, hy=-3, hp=2.5, cp=1.0)),
        (34,  dict(dz=-0.006, hy=-4, hp=3.0, cp=1.2), 0.0),
        (48,  dict(dz=-0.006, hy=-3, hp=1.5, cp=1.0), 0.55),
        (60,  dict(dz=-0.006, hy=-2, hp=0.5, cp=0.8), 1.0),
        (72,  dict(dz=-0.006, hy=0, hp=1.0, cp=0.8), 0.35),
        (86,  dict(dz=-0.006, hy=2, hp=1.5, cp=0.6), 0.0),
        (100, dict(dz=-0.004, hy=0, hp=0.0, cp=0.4)),
        (112, dict(dz=-0.004, hy=13, hp=1.0, cp=0.2)),
        (126, dict(dz=-0.004, hy=6, hp=0.5, cp=0.2)),
        (150, dict(dz=0.0, hy=0, hp=0, cp=0)),
    ]
    for row in seq:
        f, kw = row[0], row[1]
        P = Frame(rig)
        base(P, **kw)
        if len(row) > 2:
            stroke(P, row[2], kw["hp"])
        W.key(P, f)
    finish_action(act, rig.arm)
    return act


def a_walk(rig, D=30):
    """走路 1.0s：矮人重步，两步一循环，脚落地不打滑；枪一直扛在肩上。"""
    act = new_action(rig.arm, "walk")
    W = Writer(rig)
    n = 10
    for i in range(n + 1):
        f = round(D * i / n)
        t = i / n
        P = Frame(rig)
        ph_r = t % 1.0
        ph_l = (t + 0.5) % 1.0

        def leg_y(ph):
            if ph < 0.5:                      # 支撑相：由前到后
                return 0.128 - 0.256 * (ph / 0.5)
            u = (ph - 0.5) / 0.5              # 摆动相：由后到前，抬起
            return -0.128 + 0.256 * (u * u * (3 - 2 * u))

        def leg_z(ph):
            if ph < 0.5:
                return 0.0
            u = (ph - 0.5) / 0.5
            return 0.072 * math.sin(math.pi * u)

        def foot_pitch(ph):
            if ph < 0.5:
                return 0.0                     # 支撑相：整只脚掌贴地
            u = (ph - 0.5) / 0.5
            return 14.0 * math.sin(math.pi * u)  # 摆动相：抬脚尖过障

        bob = -0.020 + 0.016 * math.cos(4 * math.pi * t)
        sway = 0.014 * math.sin(2 * math.pi * t)
        stance(P, dz=bob, dx=sway,
               hips_yaw=-3.2 * math.sin(2 * math.pi * t),
               hips_roll=3.4 * math.sin(2 * math.pi * t),
               chest_yaw=4.2 * math.sin(2 * math.pi * t),
               chest_pitch=3.0, spine_pitch=1.5,
               head_pitch=-2.0,
               feet=[(0, 0), (0, 0)])
        P.solve_T()
        for side, s, ph in (("R", 1, ph_r), ("L", -1, ph_l)):
            A = Vector((s * U.LEG_X, U.Z_ANKLE * 0 + leg_y(ph), U.Z_ANKLE + leg_z(ph)))
            P.leg(side, A, (s * 0.3, 1.0, 0.12), foot_pitch(ph))
        W.key(P, f)
    finish_action(act, rig.arm)
    return act


def a_attack(rig, D=40):
    """攻击 1.33s：扛肩 → 落枪平举 → 击发（40% 命中帧）→ 收回肩上。
    矮人短臂端不了长枪的托底，所以是"夹在右腋下的腰射"。"""
    act = new_action(rig.arm, "attack")
    W = Writer(rig)
    REST_BUTT = gpt(Vector((0, 0, 0)), GUN_A_REST, 0, -U.GUN_L_BACK, 0)
    AIM_BUTT = Vector((0.266, 0.040, 0.778))
    AIM_DIR = Vector((-0.30, 0.905, 0.300)).normalized()
    MUZ = AIM_DIR.copy()

    def key(f, k, dz=0.0, cy=0.0, cp=0.0, hp=0.0, hy=0.0, butt=None, d=None, brace=None):
        P = Frame(rig)
        stance(P, dz=dz, hips_yaw=cy * 0.4, chest_yaw=cy, chest_pitch=cp,
               head_yaw=hy, head_pitch=hp)
        if butt is not None:
            P.gun(butt, d)
        if brace is not None:
            P.arm("L", brace, (-0.8, -0.6, -0.4))
        W.key(P, f)
        return P

    # 0 起手（扛肩）
    key(0, 0)
    # 5 下沉、枪开始前倒
    key(5, 0, dz=-0.010, cy=-6, cp=1.5,
        butt=REST_BUTT.lerp(AIM_BUTT, 0.35), d=GUN_A_REST.lerp(AIM_DIR, 0.35))
    # 10 枪到肩前，左手抬起来扶
    key(10, 0, dz=-0.016, cy=-15, cp=4.0,
        butt=REST_BUTT.lerp(AIM_BUTT, 0.82), d=GUN_A_REST.lerp(AIM_DIR, 0.82),
        brace=Vector((-0.130, 0.262, 0.828)))
    # 14 瞄准到位
    key(14, 0, dz=-0.018, cy=-19, cp=6.0, hp=-2.0,
        butt=AIM_BUTT, d=AIM_DIR, brace=Vector((-0.126, 0.276, 0.822)))
    # 16 击发（40%）：枪后坐 + 枪口上跳 + 躯干后仰
    kick = AIM_BUTT - MUZ * 0.045 + Vector((0, 0, 0.004))
    key(16, 1, dz=-0.012, cy=-15, cp=1.0, hp=3.0,
        butt=kick, d=(AIM_DIR + Vector((0, 0, 0.10))).normalized(),
        brace=Vector((-0.138, 0.246, 0.842)))
    # 19 回落
    key(19, 0, dz=-0.017, cy=-18, cp=5.0, hp=-1.0,
        butt=AIM_BUTT, d=AIM_DIR, brace=Vector((-0.128, 0.272, 0.826)))
    # 25 保持
    key(25, 0, dz=-0.016, cy=-17, cp=4.5, hp=-1.0,
        butt=AIM_BUTT + AIM_DIR * 0.004, d=AIM_DIR,
        brace=Vector((-0.130, 0.270, 0.826)))
    # 31 收枪回肩
    key(31, 0, dz=-0.010, cy=-9, cp=2.5,
        butt=REST_BUTT.lerp(AIM_BUTT, 0.45), d=GUN_A_REST.lerp(AIM_DIR, 0.45))
    # 36 / 40 回 rest
    key(36, 0, dz=-0.002, cy=-2, cp=0.6)
    key(40, 0)
    finish_action(act, rig.arm)
    return act


def a_reload(rig, D=84):
    """装填 2.8s：枪横端在胸前 → 左手去腰带取药 → 点药池 → 抽通条 → 捅两下 → 归位。"""
    act = new_action(rig.arm, "reload")
    W = Writer(rig)
    REST_BUTT = gpt(Vector((0, 0, 0)), GUN_A_REST, 0, -U.GUN_L_BACK, 0)
    PORT_BUTT = Vector((0.345, 0.245, 0.585))
    PORT_DIR = Vector((-0.960, 0.240, 0.140)).normalized()
    HORN = Vector((-0.210, 0.112, 0.556))
    MUZ = gpt(PORT_BUTT, PORT_DIR, 0.0, 0.790, 0.014)
    FORE = gpt(PORT_BUTT, PORT_DIR, 0.0, 0.470, -0.030)
    ROD_TIP = gpt(PORT_BUTT, PORT_DIR, 0.0, 0.556, -0.050)
    ROD_OUT = gpt(PORT_BUTT, PORT_DIR, 0.0, 0.716, -0.050)

    def key(f, dz=0.0, cy=0.0, cp=0.0, hy=0.0, hp=0.0, butt=None, d=None,
            left=None, slide=0.0):
        P = Frame(rig)
        stance(P, dz=dz, hips_yaw=cy * 0.35, chest_yaw=cy, chest_pitch=cp,
               head_yaw=hy, head_pitch=hp)
        if butt is not None:
            P.gun(butt, d)
        if left is not None:
            P.arm("L", left, (-0.85, -0.5, -0.45))
        P.rod_slide = slide
        W.key(P, f)

    key(0)
    key(9, dz=-0.014, cy=-4, cp=1.2, butt=REST_BUTT.lerp(PORT_BUTT, 0.55),
        d=GUN_A_REST.lerp(PORT_DIR, 0.55))
    key(17, dz=-0.020, cy=-8, cp=2.4, butt=PORT_BUTT, d=PORT_DIR,
        left=FORE, hp=3.0)
    key(25, dz=-0.018, cy=-11, cp=2.2, butt=PORT_BUTT, d=PORT_DIR,
        left=HORN, hy=-7)
    key(31, dz=-0.018, cy=-10, cp=2.2, butt=PORT_BUTT, d=PORT_DIR,
        left=HORN + Vector((0.015, 0.02, 0.055)), hy=-5)
    key(39, dz=-0.018, cy=-8, cp=2.8, butt=PORT_BUTT, d=PORT_DIR,
        left=MUZ, hp=4.0)
    key(45, dz=-0.018, cy=-8, cp=2.8, butt=PORT_BUTT, d=PORT_DIR,
        left=MUZ + Vector((0.0, -0.005, 0.03)), hp=4.0)
    key(52, dz=-0.018, cy=-8, cp=2.6, butt=PORT_BUTT, d=PORT_DIR,
        left=ROD_TIP, hp=2.0)
    key(60, dz=-0.018, cy=-8, cp=2.6, butt=PORT_BUTT, d=PORT_DIR,
        left=ROD_OUT, hp=0.0, slide=0.16)
    key(67, dz=-0.020, cy=-8, cp=3.2, butt=PORT_BUTT, d=PORT_DIR,
        left=ROD_TIP, hp=2.0, slide=0.02)
    key(72, dz=-0.018, cy=-7, cp=2.6, butt=PORT_BUTT, d=PORT_DIR,
        left=FORE, slide=0.0)
    key(78, dz=-0.010, cy=-3, cp=1.2, butt=REST_BUTT.lerp(PORT_BUTT, 0.5),
        d=GUN_A_REST.lerp(PORT_DIR, 0.5))
    key(84)
    finish_action(act, rig.arm)
    return act


def a_hurt(rig, D=11):
    """受击 0.33s：上半身被打得一缩，脚不退。"""
    act = new_action(rig.arm, "hurt")
    W = Writer(rig)
    seq = [(0, 0.0, 0.0, 0.0, 0.0),
           (3, -0.014, 7.0, -6.0, 9.0),
           (6, -0.008, 3.0, -2.0, 4.0),
           (11, 0.0, 0.0, 0.0, 0.0)]
    for (f, dz, cp, cy, hp) in seq:
        P = Frame(rig)
        stance(P, dz=dz, chest_pitch=cp, chest_yaw=cy, head_pitch=hp,
               hips_pitch=cp * 0.3)
        W.key(P, f)
    finish_action(act, rig.arm)
    return act


def a_death(rig, D=40):
    """阵亡 1.3s：中弹一顿 → 膝盖一软跪下去 → 上身垮下、头低垂 → 最后 0.4s 绝对静止。
    不做"整体前倒"：绕脚踝翻 78° 会让背/枪穿地，跪倒更安全也更耐看。"""
    act = new_action(rig.arm, "death")
    W = Writer(rig)
    seq = [
        # f,  dz,   chest_pitch, head_pitch, head_yaw, hips_pitch
        (0,   0.000, 0.0, 0.0, 0.0, 0.0),
        (4,  -0.020, -9.0, 7.0, -3.0, -3.0),
        (10, -0.120, 10.0, 4.0, -6.0, 6.0),
        (17, -0.260, 26.0, 8.0, -8.0, 12.0),
        (22, -0.360, 44.0, 12.0, -8.0, 16.0),
        (26, -0.406, 55.0, 14.0, -6.0, 18.0),
        (28, -0.414, 58.0, 14.0, -5.0, 18.0),
        (40, -0.414, 58.0, 14.0, -5.0, 18.0),
    ]
    for (f, dz, cp, hp, hy, hip) in seq:
        P = Frame(rig)
        stance(P, dz=dz, hips_pitch=hip, chest_pitch=cp, head_pitch=hp, head_yaw=hy)
        W.key(P, f)
    finish_action(act, rig.arm)
    return act


def build_all(arm, only=None):
    rig = Rig(arm)
    table = [("idle", a_idle), ("idle_alt", a_idle_alt), ("walk", a_walk),
             ("attack", a_attack), ("reload", a_reload), ("hurt", a_hurt),
             ("death", a_death)]
    out = []
    for name, fn in table:
        if only and name not in only:
            continue
        act = fn(rig)
        act.name = name
        out.append(name)
        print("[anim]", name, "frames", tuple(int(v) for v in act.frame_range))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out
