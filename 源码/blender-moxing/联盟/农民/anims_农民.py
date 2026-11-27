"""anims_农民.py —— 联盟农民（方块人）v4：6 条重做动作 + 3 条保留

## 只换动作，不换模型
模型是 `库/_ref/联盟/方块人_农民.glb`（25 骨），本文件只写姿态。
新增一根 `sack` 骨（肩上金袋）——不扛袋子的动作每帧 `SCL["sack"]=0.001`（缩小藏进胸腔），
只有 `carry_gold` 是 `1.0`。

## 锄头怎么摆
`prop_tool` 是 `hand_R` 的子骨，锄头刚体跟着手走。所以"挥锄 / 拄锄"都不靠武器骨，
而是给**锄头一个世界指向** `hd`（`unit_农民.HOE.aim()` 把整套刚体转过去）。
锄头握点=腕点，刃底在腕点沿锄轴 0.506 m 处、柄顶在 0.192 m 处 —— 这两个数是量出来的，
不是估的，所以"刃底落地"= `HOE.grip(ax, ay, tip_z)`。

## 帧长
idle 108 / walk 26 / attack 22 / hurt 9 / death 32（与步兵同节奏），carry_gold 36（循环）。
30 fps，逐帧烘焙（`poselib2.bake`），循环动作首末帧参数完全相同 → loop_d 必然 0。
"""
import math

import bpy
from mathutils import Matrix, Vector

import anims_human as AH
import poselib2 as PL
import unit_农民 as U

S = U.S
HOE = U.HOE
FPS = 30
LOC_BONES = ("prop_tool",)
SCL_BONES = ("sack", "prop_sack", "prop_logs", "prop_tool")

# 锄头静止指向（挂机姿态下"柄在前上、刃在后下"）
HD_REST = HOE.axis.copy()
# 拄锄头：刃底落在身前 (0.10, 0.30)，柄竖直
HD_STAFF = Vector((0.02, 0.10, -0.994)).normalized()


def _kd(f, **kw):
    d = dict(f=f, dz=0.0, dx=0.0, dy=0.0,
             hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
             spine_pitch=0.0, chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
             head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
             rfoot=(S.ANK.x, 0.010, 0.0, 4.0), lfoot=(-S.ANK.x, -0.010, 0.0, -4.0),
             rw=S.WRI_R.copy(), hd=HD_REST.copy(), hr=0.0,
             lw=S.WRI_L.copy(), lp=0.0, lr=0.0, ly=0.0,
             lhoe=0.0, lof=Vector((0.0, 0.02, 0.03)),
             sck=0.001, sp=0.0, sr=0.0, sy=0.0, ptool=1.0,
             kp=0.0, kr=0.0, wt=Vector((0.0, 0.0, 0.0)), wr=Matrix.Identity(3))
    d.update(kw)
    return f, d


def _emit(rig, W):
    def emit(f, d):
        P = AH.pose(rig, S, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                    hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                    hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                    chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                    chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                    head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        for side, v in (("R", d["rfoot"]), ("L", d["lfoot"])):
            AH.leg(P, S, side, v[0], v[1], v[2], v[3], v[4] if len(v) > 4 else 0.0)
        # 道具显隐（沿用旧资产的做法：没用的缩成一点）
        P.SCL["sack"] = d["sck"]
        P.SCL["prop_sack"] = 0.002
        P.SCL["prop_logs"] = 0.002
        P.SCL["prop_tool"] = d["ptool"]
        U.sack_bone_rot(P, d["sp"], d["sr"], d["sy"])
        P.solve_T()
        # 右手 + 锄头
        M = HOE.aim(P, d["hd"], d["hr"])
        P.arm("R", d["rw"], (0.60, 0.24, -0.76))
        P.solve_T()
        # 左手：lhoe=1 时焊在柄顶（"扶锄头"），否则自己给点
        wl = Vector(d["lw"])
        if d.get("lout"):
            wl = wl + Vector((-0.060, 0.030, 0.0))
        if d["lhoe"] > 1e-4:
            wl = wl.lerp(HOE.top_world(P, M) + Vector(d["lof"]), d["lhoe"])
        P.arm("L", wl, (-0.66, 0.36, -0.66))
        PL.hand_rot(P, "L", d["lp"], d["lr"], d["ly"])
        if d["kp"] > 1e-4 or d["kr"] > 1e-4:
            AH.drop_layered(P, "prop_tool", d["wt"], d["wr"], d["kp"], d["kr"])
        AH.ground(P, S)                     # 铁律：每条动作末句做落地校正（只抬不压）
        W.key(P, f)
    return emit


def _baked(rig, name, keys, D):
    act = PL.new_action(rig.arm, name)
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    PL.bake(keys, D, _emit(rig, W))
    PL.finish_action(act)
    return act


# ══ 1. idle（108f）：双手扶锄头站着，重心换脚 + 左右看 + 呼吸 ══════════════
def a_idle(rig, D=108):
    """农民拄着锄头歇着：上身弓着把重量压在锄柄上，两只手一上一下扶着。"""
    GRIP = HOE.grip(0.262, 0.248, 0.020)
    BASE = dict(dz=-0.062, hips_pitch=-7.0, spine_pitch=-10.0, chest_pitch=-16.0,
                rw=GRIP, hd=HD_STAFF, lhoe=0.0, lof=Vector((0.0, 0.030, 0.028)),
                lw=S.WRI_L + Vector((-0.014, 0.024, 0.026)), lp=-12.0, ly=8.0,
                rfoot=(S.ANK.x + 0.012, 0.030, -2.0, 7.0),
                lfoot=(-S.ANK.x - 0.014, -0.040, 3.0, -6.0))

    def k(f, **kw):
        d = dict(BASE)
        d.update(kw)
        return _kd(f, **d)

    keys = [
        k(0, chest_pitch=-16.0, head_yaw=0.0, head_pitch=9.0),
        # 换到左脚：胯往左压，头往左看
        k(20, dz=-0.070, dx=-0.016, hips_roll=2.0, chest_roll=-2.5,
          chest_pitch=-15.0, head_yaw=-11.0, head_pitch=10.0, ly=9.0),
        k(34, dz=-0.064, dx=-0.012, hips_roll=1.5, chest_roll=-1.5,
          chest_pitch=-16.5, head_yaw=-14.0, head_pitch=10.0, ly=8.0),
        # 一次呼吸（胸口抬起）
        k(48, dz=-0.056, dx=-0.004, chest_pitch=-13.0, spine_pitch=-8.5,
          head_pitch=7.0, head_yaw=-6.0, ly=9.5),
        # 换到右脚
        k(62, dz=-0.068, dx=0.016, hips_roll=-2.0, chest_roll=2.5,
          chest_pitch=-15.0, head_yaw=4.0, head_pitch=10.0, ly=3.0),
        k(76, dz=-0.062, dx=0.012, hips_roll=-1.5, chest_roll=2.0,
          chest_pitch=-16.0, head_yaw=13.0, head_pitch=11.0, ly=2.0),
        k(90, dz=-0.058, dx=0.004, chest_pitch=-14.5, head_yaw=8.0,
          head_pitch=8.0, ly=5.0),
        k(100, dz=-0.066, chest_pitch=-16.5, head_yaw=2.0, head_pitch=10.0),
        k(108, chest_pitch=-16.0, head_yaw=0.0, head_pitch=9.0),
    ]
    return _baked(rig, "idle", keys, D)


# ══ 2. walk（26f）：步幅 0.13，支撑相匀速不打滑，肩一高一低 ════════════════
def a_walk(rig, D=26):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    for i in range(D + 1):
        t = (i % D) / float(D)
        P = AH.pose(rig, S)
        # 腿只有 0.554 长、脚掌 0.33 长 —— 步幅 0.13 已经接近方块人的上限
        AH.walk(P, S, t, step=0.130, lift=0.062, base_dz=-0.026,
                base_pitch=-3.5, hips_yaw=6.0, chest_yaw=-6.5,
                chest_roll=2.4, head_yaw=2.5, sink=0.012,
                side_sway=0.020, spread=0.0)
        cy = math.cos(2.0 * math.pi * t)
        cx = math.sin(2.0 * math.pi * t)
        # 肩一高一低（chest_roll 已带 2.4，这里再给右肩一点主动起伏）
        P.rot("shoulder_R", (0, 1, 0), -3.0 * cy, chain=False)
        P.rot("shoulder_L", (0, 1, 0), 3.0 * cy, chain=False)
        P.SCL["sack"] = 0.001
        P.SCL["prop_sack"] = 0.002
        P.SCL["prop_logs"] = 0.002
        P.SCL["prop_tool"] = 1.0
        P.solve_T()
        # 锄头挂在右手，随步伐前后甩（幅度小，刃底一直在 0.2 以上）
        M = HOE.aim(P, HD_REST + Vector((0.0, -0.10 * cy, 0.04 * cy)), 0.0)
        P.arm("R", S.WRI_R + Vector((0.008, 0.052 * cy, 0.004 * abs(cx))),
              (0.60, 0.24, -0.76))
        P.solve_T()
        P.arm("L", S.WRI_L + Vector((-0.010, -0.062 * cy, 0.010 * abs(cx))),
              (-0.62, 0.30, -0.72))
        PL.hand_rot(P, "L", -6.0 * cy, 0.0, 4.0)
        W.key(P, i)
    PL.finish_action(act)
    return act


# ══ 3. attack（22f）：抡锄头 —— 前摇抬到右后上 → f9 砸到身前下方 → 顿 3 帧 ═══
def a_attack(rig, D=22):
    keys = [
        _kd(0, dz=-0.026, chest_pitch=-3.5, rw=S.WRI_R, hd=HD_REST, lhoe=0.0,
            lw=S.WRI_L),
        # 前摇：锄头抬到右后上，身体拧过去
        _kd(5, dz=-0.040, dy=-0.014, hips_yaw=8.0, chest_yaw=15.0,
            chest_pitch=2.0, head_yaw=-10.0, head_pitch=4.0,
            rw=Vector((0.298, -0.060, 1.075)), hd=Vector((0.06, -0.52, 0.85)), hr=-12.0,
            lw=Vector((-0.170, 0.120, 1.010)), lp=-40.0, ly=16.0,
            rfoot=(S.ANK.x + 0.012, -0.040, -2.0, 7.0),
            lfoot=(-S.ANK.x - 0.010, 0.030, 2.0, -6.0)),
        # f9 = 40%：命中，刃砸到身前下方
        _kd(9, dz=-0.078, dy=0.040, hips_yaw=-7.0, chest_yaw=-12.0,
            chest_pitch=-22.0, chest_roll=-4.0, head_yaw=3.0, head_pitch=10.0,
            rw=Vector((0.176, 0.318, 0.660)), hd=Vector((0.02, 0.60, -0.80)), hr=6.0,
            lw=Vector((-0.120, 0.170, 0.900)), lp=-70.0, ly=4.0,
            rfoot=(S.ANK.x + 0.014, 0.062, 3.0, 9.0),
            lfoot=(-S.ANK.x - 0.014, 0.112, 1.0, -7.0)),
        # 顿帧 3 帧
        _kd(12, dz=-0.080, dy=0.042, hips_yaw=-7.5, chest_yaw=-12.5,
            chest_pitch=-23.0, chest_roll=-4.0, head_yaw=3.0, head_pitch=10.0,
            rw=Vector((0.174, 0.322, 0.654)), hd=Vector((0.02, 0.61, -0.79)), hr=6.0,
            lw=Vector((-0.120, 0.172, 0.898)), lp=-70.0, ly=4.0,
            rfoot=(S.ANK.x + 0.014, 0.064, 3.0, 9.0),
            lfoot=(-S.ANK.x - 0.014, 0.114, 1.0, -7.0)),
        # 收
        _kd(17, dz=-0.040, dy=0.014, hips_yaw=-2.0, chest_yaw=-3.0,
            chest_pitch=-8.0, head_pitch=4.0,
            rw=Vector((0.300, 0.130, 0.700)), hd=HD_REST + Vector((0.0, 0.10, 0.10)),
            lw=Vector((-0.280, 0.110, 0.720)), lp=-20.0, ly=6.0,
            rfoot=(S.ANK.x + 0.008, 0.020, 1.0, 6.0),
            lfoot=(-S.ANK.x - 0.008, 0.046, 0.0, -5.0)),
        _kd(22, dz=-0.026, chest_pitch=-3.5, rw=S.WRI_R, hd=HD_REST, lw=S.WRI_L),
    ]
    return _baked(rig, "attack", keys, D)


# ══ 扛袋姿态的公共层 ══════════════════════════════════════════════════════════
# 袋口在左肩**前下方**（胸侧），左手焊在袋口；袋身压左肩靠后、从背后垂下去。
# 扛袋的动作一律：袋 SCL=1.0、锄头 SCL=0.001（收起来，手里不拿）、右手空着下垂。
MOFF = Vector((-0.012, 0.052, -0.060))     # 腕相对袋口：从正下方托住袋颈
POLE_L = (-0.38, 0.34, -0.86)
POLE_R = (0.76, 0.20, -0.66)

CARRY_BASE = dict(dz=-0.034, dx=0.014, dy=0.0,
                  hips_yaw=4.0, hips_pitch=-3.0, hips_roll=-2.0,
                  spine_pitch=-2.0, chest_pitch=-5.0, chest_yaw=2.0, chest_roll=-2.5,
                  head_pitch=6.0, head_yaw=-2.0, head_roll=0.0,
                  rfoot=(S.ANK.x + 0.014, 0.026, -1.0, 8.0),
                  lfoot=(-S.ANK.x + 0.004, -0.028, 2.0, -5.0),
                  sp=0.0, sr=0.0, sy=0.0, sck=1.0, weld=1.0,
                  rw=None, lw=tuple(S.WRI_L), lp=0.0, lr=0.0, ly=0.0,
                  rp=-3.0, ry=3.0, pole_l=POLE_L, pole_r=POLE_R, rout=0.0)


def _carry_frame(rig, d):
    """一帧"扛袋"姿态：躯干 + 腿 → 落地校正 → 袋口世界点 → 左手焊上去 → 右手空着。"""
    P = AH.pose(rig, S, dz=d["dz"], dx=d["dx"], dy=d.get("dy", 0.0),
                hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                head_yaw=d["head_yaw"], head_roll=d["head_roll"])
    for side, v in (("R", d["rfoot"]), ("L", d["lfoot"])):
        AH.leg(P, S, side, v[0], v[1], v[2], v[3], v[4] if len(v) > 4 else 0.0)
    P.SCL["sack"] = d.get("sck", 1.0)
    P.SCL["prop_sack"] = 0.002
    P.SCL["prop_logs"] = 0.002
    P.SCL["prop_tool"] = 0.001          # 锄头收起来
    U.sack_bone_rot(P, d.get("sp", 0.0), d.get("sr", 0.0), d.get("sy", 0.0))
    AH.ground(P, S)                     # 先落地（只抬不压），再算袋口
    P.solve_T()
    if d.get("weld", 1.0) > 0.5:
        mouth = U.sack_mouth(P)         # 袋口世界点由 sack 骨推出来
        wl = mouth + MOFF
        P.arm("L", wl, d.get("pole_l", POLE_L))
        P.aim("hand_L", mouth - wl)     # 手心对准袋口
    else:
        P.arm("L", Vector(d["lw"]), d.get("pole_l", POLE_L))
        PL.hand_rot(P, "L", d.get("lp", 0.0), d.get("lr", 0.0), d.get("ly", 0.0))
    rw = d.get("rw")
    if rw is None:
        # 默认"右臂自然下垂"：腕相对肩的静止偏移按胸口朝向摆，身体一转手就跟着转，
        # 不会像写死世界坐标那样在跪/倒的过程中扫进胸口。
        off = rig.rest["chest"][1].inverted() @ (S.WRI_R - rig.rest["upperarm_R"][0])
        rw = P.T["upperarm_R"] + P.R["chest"] @ off
    rw = Vector(rw) + Vector((d.get("rout", 0.0), 0.0, 0.0))
    P.arm("R", rw, d.get("pole_r", POLE_R))
    PL.hand_rot(P, "R", d.get("rp", -3.0), 0.0, d.get("ry", 3.0))
    return P


def _baked_carry(rig, name, keys, D):
    act = PL.new_action(rig.arm, name)
    W = PL.Writer(rig, loc_bones=(), scl_bones=SCL_BONES)

    def emit(f, d):
        W.key(_carry_frame(rig, d), f)

    PL.bake(keys, D, emit)
    PL.finish_action(act)
    return act


def _ck(f, **kw):
    """扛袋动作的关键帧：默认 = 站着扛袋那一套，kw 覆盖。"""
    d = dict(CARRY_BASE)
    d.update(kw)
    return f, d


# ══ 4. hurt（9f）：扛着袋子挨打 —— 袋子往一侧甩、人侧闪，最后回位 ═══════════
def a_hurt(rig, D=9):
    """扛袋挨打：上身被打得后仰+右闪，左肩的袋子被带得往外甩（远离头），
    三帧后回位。首末帧参数完全相同 → 可以直接接回 carry_gold / carry_gold_idle。

    * `sr` 是绕骨轴（世界 Y）的滚转：负值 = 袋口往外、袋尾往下，正好甩离脸。
    * 左手焊在袋口上，所以袋子甩出去手会跟着被拽一下 —— 这就是"拎着袋子挨打"。
    """
    keys = [
        _ck(0),
        # f2 命中：后仰 + 往右闪，袋子往左外甩
        _ck(2, dz=-0.058, dx=0.030, dy=-0.018, hips_pitch=4.0, hips_yaw=-7.0,
            chest_pitch=5.0, chest_roll=-8.0, chest_yaw=7.0,
            head_pitch=13.0, head_yaw=-9.0, head_roll=-7.0,
            sp=-4.0, sr=-7.0, sy=5.0,
            rw=Vector((0.334, -0.008, 0.706)),
            rfoot=(S.ANK.x + 0.030, -0.020, -2.0, 9.0),
            lfoot=(-S.ANK.x + 0.022, -0.052, -3.0, -8.0)),
        # f5 回弹
        _ck(5, dz=-0.040, dx=0.020, hips_yaw=-2.0, chest_pitch=-2.0,
            chest_roll=-4.5, chest_yaw=3.0, head_pitch=8.0, head_yaw=-4.0,
            sr=-3.0, sy=2.0,
            lfoot=(-S.ANK.x + 0.010, -0.040, 0.0, -6.0)),
        # f7 收
        _ck(7, dz=-0.035, dx=0.016, chest_pitch=-4.2, chest_roll=-3.0,
            head_pitch=7.0, head_yaw=-3.0, sr=-1.0, sy=1.0),
        _ck(9),
    ]
    return _baked_carry(rig, "hurt", keys, D)


# ══ 5. death（32f）：扛袋中招 → 膝盖一软 → 往左侧倒 → 末 6 帧定格 ═══════════
def a_death(rig, D=32):
    """扛着袋子被打死：后仰 → 膝盖一软跪下去 → 往**左**侧倒（袋子在左肩，
    跟着 chest 一起倒，人压在自己扛的那袋金子上）→ f26..f32 绝对静止。

    * 锄头已经收起（`prop_tool` 缩到 0.001），所以不会出现"锄头插进脚"。
    * 末段左手不再焊袋口（人已经脱手了），左臂顺着地面摊开 —— 否则手会压进胸里。
    """
    keys = [
        _ck(0),
        # 中招后仰（被打得往后一缩，袋子被顶得往外）
        _ck(3, dz=-0.058, dy=-0.022, hips_pitch=6.0, hips_yaw=-8.0, hips_roll=-8.0,
            chest_pitch=8.0, chest_roll=-10.0, chest_yaw=7.0,
            head_pitch=14.0, head_yaw=-10.0, sp=-5.0, sr=-6.0, sy=4.0,
            lp=22.0, ly=-12.0,
            lfoot=(-S.ANK.x + 0.022, -0.050, -3.0, -9.0)),
        # 膝盖一软（跪下去）
        _ck(8, dz=-0.176, dy=0.004, hips_pitch=-10.0, hips_roll=4.0,
            chest_pitch=-7.0, chest_roll=3.0, head_pitch=13.0, head_yaw=-7.0, sr=-4.0,
            lp=8.0, ly=-6.0, pole_l=(-0.90, 0.05, -0.40), rout=0.070,
            rfoot=(S.ANK.x + 0.030, -0.020, 9.0, 8.0),
            lfoot=(-S.ANK.x - 0.020, -0.004, 11.0, -8.0)),
        # 往**右**侧倒（袋子在左肩 → 倒下去时袋子在上面，不会压进地里）
        _ck(13, dz=-0.300, dy=0.020, dx=-0.020, hips_pitch=-8.0, hips_roll=40.0,
            chest_pitch=-4.0, chest_roll=8.0, head_pitch=6.0, head_yaw=4.0,
            sr=-2.0, lp=-4.0,
            rw=Vector((0.420, 0.340, 0.420)), pole_r=(0.50, 0.20, 0.40), rout=0.030,
            lw=(-0.020, 0.300, 0.500), pole_l=(0.0, 0.60, 0.60),
            rfoot=(S.ANK.x + 0.120, 0.020, 20.0, 10.0),
            lfoot=(-S.ANK.x - 0.120, -0.030, 22.0, -12.0)),
        _ck(18, dz=-0.336, dy=0.032, dx=-0.040, hips_pitch=-12.0, hips_roll=70.0,
            chest_pitch=-2.0, chest_roll=5.0, head_pitch=2.0, head_yaw=8.0,
            lp=-14.0,
            rw=Vector((0.410, 0.460, 0.220)), pole_r=(0.40, 0.20, 0.35),
            lw=(0.140, 0.380, 0.360), pole_l=(0.1, 0.70, 0.55),
            rfoot=(S.ANK.x - 0.180, -0.050, 18.0, 10.0),
            lfoot=(-S.ANK.x - 0.280, 0.080, 22.0, -12.0)),
        # 落定（f24..f32 同参数 = 末 6 帧定格）
        _ck(24, dz=-0.344, dy=0.040, dx=-0.050, hips_pitch=-15.0, hips_roll=88.0,
            chest_pitch=-2.0, chest_roll=4.0, head_pitch=2.0, head_yaw=10.0,
            lp=-18.0,
            rw=Vector((0.400, 0.560, 0.100)), pole_r=(0.30, 0.20, 0.30),
            lw=(0.280, 0.420, 0.280), pole_l=(0.1, 0.70, 0.50),
            rfoot=(S.ANK.x - 0.230, -0.050, 18.0, 10.0),
            lfoot=(-S.ANK.x - 0.330, 0.090, 22.0, -12.0)),
        _ck(32, dz=-0.344, dy=0.040, dx=-0.050, hips_pitch=-15.0, hips_roll=88.0,
            chest_pitch=-2.0, chest_roll=4.0, head_pitch=2.0, head_yaw=10.0,
            lp=-18.0,
            rw=Vector((0.400, 0.560, 0.100)), pole_r=(0.30, 0.20, 0.30),
            lw=(0.280, 0.420, 0.280), pole_l=(0.1, 0.70, 0.50),
            rfoot=(S.ANK.x - 0.230, -0.050, 18.0, 10.0),
            lfoot=(-S.ANK.x - 0.330, 0.090, 22.0, -12.0)),
    ]
    return _baked_carry(rig, "death", keys, D)


# ══ 6. carry_gold（36f 循环）：扛着袋子走 ═══════════════════════════════════
def a_carry_gold(rig, D=36):
    """肩上扛一袋金子走路（36 f 循环，30 fps）。

    左手**焊在袋口**（袋口世界点由 sack 骨逐帧推出来），袋子自身只做 1.5° 的小晃，
    手跟着晃 —— 所以看起来是"手抓着袋口、袋子压着肩"，不是"手在袋子旁边摆"。
    步幅收到 0.105（空手是 0.13），上身负重：胸往前 5°、重心往右 1.4 cm 配重。
    锄头收起来（`prop_tool` 0.001）：扛袋时右手空着自然下垂。
    """
    act = PL.new_action(rig.arm, "carry_gold")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    MOFF = Vector((-0.080, 0.034, -0.032))     # 腕相对袋口：外侧前下方抓住袋颈
    POLE = (-0.38, 0.34, -0.86)

    for i in range(D + 1):
        t = 0.0 if i == D else i / float(D)
        a2 = 2.0 * math.pi * t
        cy = math.cos(a2)
        P = AH.pose(rig, S, dz=-0.040, dx=0.014,
                    hips_yaw=5.0 * cy, hips_pitch=-3.0, hips_roll=-2.0,
                    chest_pitch=-5.0 - 1.2 * math.cos(2 * a2), chest_yaw=-4.0 - 4.0 * cy,
                    chest_roll=2.0 * cy, head_yaw=3.0 * cy, head_pitch=6.0)
        AH.walk(P, S, t, step=0.105, lift=0.055, base_dz=0.0,
                base_pitch=0.0, hips_yaw=0.0, chest_yaw=0.0, chest_roll=0.0,
                head_yaw=0.0, sink=0.010, side_sway=0.014, y_off=0.0)
        P.SCL["sack"] = 1.0
        P.SCL["prop_sack"] = 0.002
        P.SCL["prop_logs"] = 0.002
        P.SCL["prop_tool"] = 0.001          # 锄头收起来
        U.sack_bone_rot(P, 1.2 * cy, -1.6 * cy, 1.0 * math.sin(a2))
        P.solve_T()
        # 左手焊袋口
        mouth = U.sack_mouth(P)
        wl = mouth + MOFF
        P.arm("L", wl, POLE)
        P.aim("hand_L", mouth - wl)
        # 右手空着，随步伐小幅前后摆
        P.arm("R", S.WRI_R + Vector((0.030, 0.046 * cy, 0.012 + 0.006 * abs(cy))),
              (0.72, 0.22, -0.68))
        PL.hand_rot(P, "R", -6.0 * cy, 0.0, 4.0)
        AH.ground(P, S)
        W.key(P, i)
    PL.finish_action(act)
    return act


# ══ 7. carry_gold_idle（60f 循环）：扛着袋子站着等 ══════════════════════════
def a_carry_gold_idle(rig, D=60):
    """站着扛袋：袋子压肩、换一次重心、袋子跟着起伏 6 mm。"""
    MOFF = Vector((-0.080, 0.034, -0.032))
    POLE = (-0.38, 0.34, -0.86)
    act = PL.new_action(rig.arm, "carry_gold_idle")
    W = PL.Writer(rig, loc_bones=LOC_BONES, scl_bones=SCL_BONES)
    keys = [
        (0, dict(dz=-0.034, dx=0.014, hips_roll=-2.0, chest_pitch=-5.0,
                 chest_roll=-2.5, chest_yaw=2.0, head_yaw=-2.0, head_pitch=6.0,
                 sp=0.0, sr=0.0, sy=0.0)),
        (14, dict(dz=-0.042, dx=0.010, hips_roll=-2.6, chest_pitch=-6.4,
                  chest_roll=-3.2, chest_yaw=1.0, head_yaw=-7.0, head_pitch=7.0,
                  sp=-1.4, sr=1.0, sy=-0.8)),
        (30, dict(dz=-0.030, dx=0.018, hips_roll=-1.4, chest_pitch=-4.2,
                  chest_roll=-2.0, chest_yaw=3.0, head_yaw=4.0, head_pitch=5.0,
                  sp=1.2, sr=-0.6, sy=0.6)),
        (46, dict(dz=-0.040, dx=0.012, hips_roll=-2.2, chest_pitch=-6.0,
                  chest_roll=-2.8, chest_yaw=1.5, head_yaw=0.0, head_pitch=6.5,
                  sp=-0.8, sr=0.8, sy=-0.4)),
        (60, dict(dz=-0.034, dx=0.014, hips_roll=-2.0, chest_pitch=-5.0,
                  chest_roll=-2.5, chest_yaw=2.0, head_yaw=-2.0, head_pitch=6.0,
                  sp=0.0, sr=0.0, sy=0.0)),
    ]

    def emit(f, d):
        P = AH.pose(rig, S, dz=d["dz"], dx=d["dx"],
                    hips_yaw=4.0, hips_pitch=-3.0, hips_roll=d["hips_roll"],
                    spine_pitch=-2.0, chest_pitch=d["chest_pitch"],
                    chest_yaw=d["chest_yaw"], chest_roll=d["chest_roll"],
                    head_yaw=d["head_yaw"], head_pitch=d["head_pitch"])
        AH.feet(P, S, (S.ANK.x + 0.014, 0.026, -1.0, 8.0),
                (-S.ANK.x + 0.004, -0.028, 2.0, -5.0))
        P.SCL["sack"] = 1.0
        P.SCL["prop_sack"] = 0.002
        P.SCL["prop_logs"] = 0.002
        P.SCL["prop_tool"] = 0.001          # 锄头收起来
        U.sack_bone_rot(P, d["sp"], d["sr"], d["sy"])
        P.solve_T()
        mouth = U.sack_mouth(P)
        wl = mouth + MOFF
        P.arm("L", wl, POLE)
        P.aim("hand_L", mouth - wl)
        P.arm("R", S.WRI_R + Vector((0.030, 0.006, 0.012)), (0.72, 0.22, -0.68))
        PL.hand_rot(P, "R", -3.0, 0.0, 3.0)
        AH.ground(P, S)
        W.key(P, f)

    PL.bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ══ 汇总 ════════════════════════════════════════════════════════════════════
TABLE = [
    ("idle", a_idle), ("walk", a_walk), ("attack", a_attack),
    ("hurt", a_hurt), ("death", a_death),
    ("carry_gold", a_carry_gold), ("carry_gold_idle", a_carry_gold_idle),
]
KEEP = ("carry_wood", "idle_scratch", "idle_stretch")


def build_all(arm, only=None):
    rig = PL.Rig(arm)
    out = []
    for name, fn in TABLE:
        if only and name not in only:
            continue
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)      # 同名覆盖：不许出现两条 idle
        act = fn(rig)
        act.name = name
        act.use_fake_user = True
        out.append(name)
        print("[anim]", name, "frames", tuple(int(v) for v in act.frame_range))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out


def mute_sack(arm, act):
    """保留的 3 条旧动作：给新加的 sack 骨补两个 scale=0.001 的关键帧。

    旧动作里没有这根骨，不补的话引擎播 carry_wood 时袋子会以静止大小挂在肩上。
    """
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    pb = arm.pose.bones["sack"]
    pb.scale = (0.001, 0.001, 0.001)
    f0, f1 = (int(v) for v in act.frame_range)
    pb.keyframe_insert("scale", frame=f0)
    pb.keyframe_insert("scale", frame=f1)
    PL.finish_action(act)
    arm.animation_data.action = None
    pb.matrix_basis.identity()
