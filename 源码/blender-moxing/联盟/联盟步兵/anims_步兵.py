"""anims_步兵.py —— 联盟步兵 v4：动作组 + 举盾族（12 条）

## 这一版改了什么

v3 的十二条动作骨架是对的（举盾做成"姿态函数 + 每个状态各烤一版"），但**姿态本身**
立不住：盾立在胸前正中、盾面几乎平行于画面，剑竖在脸前 —— 正面看是一面门板加一根杆子。
用户的原话是"举盾不要僵"。

v4 换了举盾的构图：

    盾   盾心压到身体**左前方** (−0.18, 0.31, 1.01)，盾面向外偏 17°、上仰 11°
         → 正面看到的是**斜的盾面**（有透视、有厚度），侧面看得到盾的边和倾角
    剑   右手垂到腰线、剑尖朝**前上方**从盾的右缘挑出去
         → 一条细竖线配盾的大色块，剪影一左一右，不再是"两根杆子叠在脸前"
    身   左肩带盾前顶 11°、右肩后收，膝盖都弯、重心平均落在两脚之间，头从盾沿上方探出

## 为什么还是十二条

引擎只有 idle/walk/attack/hurt/death 五个槽，glTF 不支持分层。要让"举着盾"能同时
叠加在移动/攻击/待机/受击/阵亡上，只能把举盾做成**参数化姿态**、再给每个状态各烤一版：

    guard_raise → [guard_idle | guard_walk | guard_attack | guard_hurt] → guard_lower
                                    └→ guard_death

十二条共用同一份 `GS*/GBODY/GFOOT`，所以"举着盾走"和"举着盾被打"的盾牌位姿逐帧一致，
引擎随便切状态盾都不会跳。

## 手和盾还是焊死的

盾骨挂在 chest 下、手骨挂在 forearm 下，两条独立链。`unit_步兵.weld_shield()` 由盾
反推手腕与手掌朝向，盾是主动的、手是从动的 —— 物理上就是人抓着盾。

## 帧长（与 v3 一致，引擎可能依赖节奏）
idle 108 / walk 26 / attack 22 / hurt 9 / death 32；guard_* 按 30 fps 手感给。
"""
import math

import bpy
from mathutils import Matrix, Vector

import anims_human as AH
import poselib2 as PL
import unit_步兵 as U

S = U.S
FPS = 30
LOC_BONES = ("weapon_R", "weapon_L", "shield")

# ══ 静置（不举盾）════════════════════════════════════════════════════════════
RSP, RSN, RSU = U.SH_C0, U.SH_N0, U.SH_U0
RSPOLE = (-0.56, 0.10, -0.82)
RW0 = Vector((0.313, 0.081, 0.687))          # 右手腕静止点
RD0 = Vector((0.30, 0.22, 0.93)).normalized()  # 剑尖朝上略前（立姿持剑）
RPOLE = (0.62, 0.16, -0.77)

# ══ 举盾（十二条共用）════════════════════════════════════════════════════════
GS = Vector((-0.256, 0.322, 0.986))          # 盾心（身体左前方，护住左半身）
GN = Vector((-0.24, 0.95, 0.22)).normalized()  # 盾面法线：朝前、外偏 20°、上仰 11°
GU = Vector((0.12, 0.09, 0.99)).normalized()  # 盾面竖轴：顶端略外倾
GPOLE = (-0.62, 0.40, -0.68)
GRIP = (-0.020, -0.112, -0.100)              # 握点在盾局部系：盾背中部偏下

GW = Vector((0.324, 0.162, 0.888))           # 右手腕（剑）
GD = Vector((0.14, 0.50, 0.85)).normalized()   # 剑尖朝前上方，从盾右缘挑出去
GPOLE_R = (0.60, 0.24, -0.76)

GBODY = dict(dz=-0.074, dx=0.0, dy=0.0,
             hips_yaw=-10.0, hips_pitch=-1.0, hips_roll=0.0,
             spine_pitch=-1.5,
             chest_pitch=-3.0, chest_yaw=-12.0, chest_roll=-2.0,
             head_pitch=4.0, head_yaw=7.0, head_roll=-1.0)
GFOOT_R = (S.ANK.x + 0.044, -0.104, -2.0, 12.0)
GFOOT_L = (-S.ANK.x - 0.030, 0.118, 2.0, -8.0)


def _kd(f, **kw):
    d = dict(f=f, dz=0.0, dx=0.0, dy=0.0,
             hips_yaw=0.0, hips_pitch=0.0, hips_roll=0.0,
             spine_pitch=0.0, chest_pitch=0.0, chest_yaw=0.0, chest_roll=0.0,
             head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
             rfoot=(S.ANK.x, 0.0, 0.0, 4.0), lfoot=(-S.ANK.x, 0.0, 0.0, -4.0),
             sp=RSP.copy(), sn=RSN.copy(), su=RSU.copy(), spole=RSPOLE,
             rw=RW0.copy(), sd=RD0.copy(), sr=0.0, rpole=RPOLE,
             grip=None)
    d.update(kw)
    return f, d


def _gkd(f, **kw):
    """举盾族的一帧：身体/脚/盾/剑默认就是举盾位。"""
    d = dict(GBODY)
    d.update(dict(rfoot=GFOOT_R, lfoot=GFOOT_L,
                  sp=GS.copy(), sn=GN.copy(), su=GU.copy(), spole=GPOLE,
                  rw=GW.copy(), sd=GD.copy(), sr=0.0, rpole=GPOLE_R, grip=GRIP))
    d.update(kw)
    return _kd(f, **d)


def _emit(rig, W):
    def emit(f, d):
        P = AH.pose(rig, S, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                    hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                    hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                    chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                    chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                    head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        for side, v in (("R", d["rfoot"]), ("L", d["lfoot"])):
            x, y, pitch, yaw = v[:4]
            lift = v[4] if len(v) > 4 else 0.0
            AH.leg(P, S, side, x, y, pitch, yaw, lift)
        U.weld_shield(P, d["sp"], d["sn"], d["su"], d["spole"], grip=d.get("grip"))
        PL.sword_at(P, "R", d["rw"], d["sd"], d["sr"], d["rpole"])
        AH.ground(P, S)
        W.key(P, f)
    return emit


def _baked(rig, name, keys, D):
    act = PL.new_action(rig.arm, name)
    W = PL.Writer(rig, loc_bones=LOC_BONES)
    PL.bake(keys, D, _emit(rig, W))
    PL.finish_action(act)
    return act


# ══ 1. idle（108f）：剑拄在体前，盾挂在左臂 ═════════════════════════════════
def a_idle(rig, D=108):
    keys = [
        _kd(0, dz=-0.006, chest_pitch=-1.5, chest_yaw=1.0, head_pitch=1.0,
            rw=RW0 + Vector((0.0, 0.004, 0.0)), sd=RD0),
        _kd(22, dz=-0.012, dx=-0.008, hips_yaw=-2.0, chest_yaw=-4.0,
            chest_pitch=-2.5, head_yaw=-11.0, head_pitch=2.0, head_roll=-2.0,
            rw=RW0 + Vector((-0.004, 0.0, 0.002)), sd=RD0 + Vector((0.0, 0.04, -0.02)),
            sp=RSP + Vector((-0.004, 0.002, 0.002))),
        _kd(44, dz=-0.008, dx=-0.004, chest_yaw=-1.0, chest_pitch=-1.0,
            head_yaw=-3.0, rw=RW0 + Vector((0.0, 0.006, 0.0)),
            sp=RSP + Vector((0.0, 0.004, 0.002))),
        _kd(64, dz=-0.014, dx=0.010, hips_yaw=2.0, chest_yaw=5.0,
            chest_pitch=-3.0, head_yaw=12.0, head_pitch=2.0, head_roll=2.0,
            rw=RW0 + Vector((0.004, 0.0, 0.002)), sd=RD0 + Vector((0.0, -0.03, 0.02)),
            sp=RSP + Vector((0.006, 0.002, 0.002))),
        _kd(86, dz=-0.006, dx=0.004, chest_pitch=-1.5, head_yaw=2.0,
            rw=RW0 + Vector((0.002, 0.004, 0.0)),
            sp=RSP + Vector((0.002, 0.002, 0.0))),
        _kd(96, dz=-0.016, chest_pitch=-3.0, head_pitch=3.0,
            rw=RW0 + Vector((0.0, 0.0, -0.004))),
        _kd(108, dz=-0.006, chest_pitch=-1.5, chest_yaw=1.0, head_pitch=1.0,
            rw=RW0 + Vector((0.0, 0.004, 0.0)), sd=RD0),
    ]
    return _baked(rig, "idle", keys, D)


# ══ 2. walk（26f）══════════════════════════════════════════════════════════
def a_walk(rig, D=26):
    act = PL.new_action(rig.arm, "walk")
    W = PL.Writer(rig, loc_bones=LOC_BONES)
    for i in range(D + 1):
        t = (i % D) / float(D)
        P = AH.pose(rig, S)
        AH.walk(P, S, t, step=0.150, lift=0.072, base_dz=-0.030,
                base_pitch=-3.0, hips_yaw=7.0, chest_yaw=-7.0,
                head_yaw=3.0, sink=0.014, side_sway=0.022)
        cy = math.cos(2.0 * math.pi * t)
        U.weld_shield(P, RSP + Vector((0.0, 0.010 * cy, 0.006 * abs(cy))),
                      RSN, RSU, RSPOLE)
        PL.sword_at(P, "R", RW0 + Vector((0.006 * cy, 0.048 * cy, 0.004)),
                    RD0 + Vector((0.0, -0.05 * cy, 0.0)), 0.0, RPOLE)
        AH.ground(P, S)
        W.key(P, i)
    PL.finish_action(act)
    return act


# ══ 3. attack（22f）：斜劈 ═════════════════════════════════════════════════════
def a_attack(rig, D=22):
    keys = [
        _kd(0, dz=-0.006, chest_pitch=-1.5, rw=RW0, sd=RD0),
        # 前摇：剑举到右后上，身体拧过去，盾自然往前压
        _kd(6, dz=-0.032, dy=-0.016, hips_yaw=9.0, chest_yaw=17.0,
            chest_pitch=1.0, head_yaw=-10.0, head_pitch=2.0,
            rw=Vector((0.362, -0.020, 1.046)),
            sd=Vector((0.30, -0.34, 0.89)), sr=0.0,
            rfoot=(S.ANK.x + 0.010, -0.048, -2.0, 6.0),
            lfoot=(-S.ANK.x - 0.010, 0.032, 2.0, -6.0),
            sp=RSP + Vector((0.004, 0.012, 0.026)),
            sn=RSN + Vector((0.05, -0.02, 0.0))),
        # 命中 f9：剑落到身前下方，盾顺势回收
        _kd(9, dz=-0.072, dy=0.048, hips_yaw=-8.0, chest_yaw=-14.0,
            chest_pitch=-16.0, chest_roll=-4.0, head_yaw=3.0, head_pitch=8.0,
            rw=Vector((0.276, 0.322, 0.850)),
            sd=Vector((0.10, 0.72, -0.68)),
            rfoot=(S.ANK.x + 0.014, 0.066, 3.0, 8.0),
            lfoot=(-S.ANK.x - 0.012, 0.118, 1.0, -6.0),
            sp=RSP + Vector((-0.008, 0.024, 0.004)),
            sn=RSN + Vector((0.06, -0.04, 0.0))),
        _kd(12, dz=-0.074, dy=0.050, hips_yaw=-9.0, chest_yaw=-15.0,
            chest_pitch=-17.0, chest_roll=-4.0, head_yaw=3.0, head_pitch=8.0,
            rw=Vector((0.274, 0.328, 0.842)),
            sd=Vector((0.10, 0.73, -0.67)),
            rfoot=(S.ANK.x + 0.014, 0.068, 3.0, 8.0),
            lfoot=(-S.ANK.x - 0.012, 0.120, 1.0, -6.0),
            sp=RSP + Vector((-0.008, 0.022, 0.002))),
        _kd(17, dz=-0.026, dy=0.012, hips_yaw=-3.0, chest_yaw=-4.0,
            chest_pitch=-6.0, head_pitch=3.0,
            rw=Vector((0.330, 0.140, 0.760)), sd=Vector((0.24, 0.44, 0.86)),
            rfoot=(S.ANK.x + 0.008, 0.026, 1.0, 5.0),
            lfoot=(-S.ANK.x - 0.008, 0.050, 0.0, -5.0),
            sp=RSP + Vector((0.0, 0.008, 0.004))),
        _kd(22, dz=-0.006, chest_pitch=-1.5, rw=RW0, sd=RD0),
    ]
    return _baked(rig, "attack", keys, D)


# ══ 4. hurt（9f）═══════════════════════════════════════════════════════════
def a_hurt(rig, D=9):
    keys = [
        _kd(0, dz=-0.006, chest_pitch=-1.5, rw=RW0, sd=RD0),
        _kd(3, dz=-0.036, dx=0.020, hips_pitch=4.0, chest_pitch=5.0,
            chest_roll=-7.0, chest_yaw=6.0, head_pitch=10.0, head_yaw=-7.0,
            head_roll=-7.0,
            rw=Vector((0.352, 0.040, 0.720)), sd=Vector((0.34, 0.24, 0.91)),
            lfoot=(-S.ANK.x - 0.026, -0.036, -3.0, -8.0),
            sp=RSP + Vector((0.026, -0.026, 0.012)),
            sn=RSN + Vector((0.04, -0.08, 0.0))),
        _kd(6, dz=-0.022, dx=0.010, chest_pitch=0.0, chest_roll=-3.0,
            chest_yaw=2.0, head_pitch=5.0,
            rw=Vector((0.332, 0.070, 0.706)), sd=RD0,
            lfoot=(-S.ANK.x - 0.012, -0.012, -1.0, -6.0),
            sp=RSP + Vector((0.010, -0.006, 0.006))),
        _kd(9, dz=-0.006, chest_pitch=-1.5, rw=RW0, sd=RD0),
    ]
    return _baked(rig, "hurt", keys, D)


# ══ 5. death（32f）：后仰 → 膝盖失力 → 仰面倒下 ═══════════════════════════════
def a_death(rig, D=32):
    act = PL.new_action(rig.arm, "death")
    W = PL.Writer(rig, loc_bones=LOC_BONES)
    R_FLOOR = U.sword_floor_rot(rig.rest["weapon_R"][1])
    W_FLOOR = Vector((0.404, 0.120, 0.086))
    SH_FLOOR = Vector((-0.470, 0.120, 0.340))
    SH_N_FLOOR = Vector((-0.86, 0.42, 0.28))
    SH_U_FLOOR = Vector((0.043, 0.135, 0.990))
    SH_GRIP = None

    def emit(f, d):
        P = AH.pose(rig, S, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                    hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                    hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                    chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                    chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                    head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        for side, v in (("R", d["rfoot"]), ("L", d["lfoot"])):
            x, y, pitch, yaw = v[:4]
            lift = v[4] if len(v) > 4 else 0.0
            AH.leg(P, S, side, x, y, pitch, yaw, lift)
        U.weld_shield(P, d["sp"], d["sn"], d["su"], d["spole"], grip=d.get("grip"))
        PL.sword_at(P, "R", d["rw"], d["sd"], d["sr"], d["rpole"])
        if d["wloc"] > 0.0 or d["wrot"] > 0.0:
            AH.drop_layered(P, "weapon_R", W_FLOOR, R_FLOOR, d["wloc"], d["wrot"])
        W.key(P, f)

    def kd(f, **kw):
        d = dict(dz=0.0, dx=0.0, dy=0.0, hips_yaw=0.0, hips_pitch=0.0,
                 hips_roll=0.0, spine_pitch=0.0, chest_pitch=0.0, chest_yaw=0.0,
                 chest_roll=0.0, head_pitch=0.0, head_yaw=0.0, head_roll=0.0,
                 rfoot=(S.ANK.x, 0.0, 0.0, 3.0), lfoot=(-S.ANK.x, 0.0, 0.0, -3.0),
                 sp=RSP.copy(), sn=RSN.copy(), su=RSU.copy(), spole=RSPOLE,
                 rw=RW0.copy(), sd=RD0.copy(), sr=0.0, rpole=RPOLE,
                 wloc=0.0, wrot=0.0)
        d.update(kw)
        d["f"] = f
        return f, d

    keys = [
        kd(0, dz=-0.006, chest_pitch=-1.5),
        kd(3, dz=-0.032, dy=-0.026, hips_pitch=3.0, chest_pitch=9.0,
           head_pitch=-12.0, head_yaw=-6.0,
           rw=Vector((0.348, 0.030, 0.740)), sd=Vector((0.40, 0.12, 0.91)),
           lfoot=(-S.ANK.x - 0.022, -0.040, -3.0, -8.0),
           sp=RSP + Vector((0.024, -0.022, 0.016)),
           sn=RSN + Vector((0.05, -0.08, 0.0))),
        kd(7, dz=-0.120, dy=-0.010, hips_pitch=12.0, chest_pitch=4.0,
           head_pitch=-8.0, rw=Vector((0.336, 0.070, 0.660)),
           sd=Vector((0.40, 0.36, 0.84)), wrot=0.5,
           rfoot=(S.ANK.x + 0.006, 0.030, -2.0, 4.0),
           lfoot=(-S.ANK.x - 0.006, 0.026, -2.0, -5.0),
           sp=Vector((-0.360, 0.250, 0.860)), sn=Vector((-0.70, 0.66, 0.26)),
           spole=(-0.66, 0.10, -0.74)),
        kd(13, dz=-0.250, dy=-0.030, hips_pitch=34.0, chest_pitch=0.0,
           head_pitch=-4.0, wloc=0.55, wrot=1.0,
           rfoot=(S.ANK.x + 0.014, 0.110, -4.0, 6.0),
           lfoot=(-S.ANK.x - 0.014, 0.104, -4.0, -7.0),
           sp=SH_FLOOR + Vector((0.040, 0.020, 0.255)), sn=SH_N_FLOOR,
           spole=(-0.64, 0.10, -0.76)),
        kd(19, dz=-0.372, dy=-0.046, hips_pitch=60.0, chest_pitch=-2.0,
           head_pitch=-2.0, wloc=0.85, wrot=1.0,
           rfoot=(S.ANK.x + 0.020, 0.220, -6.0, 8.0),
           lfoot=(-S.ANK.x - 0.020, 0.212, -6.0, -9.0),
           sp=SH_FLOOR + Vector((0.030, 0.0, 0.125)), sn=SH_N_FLOOR,
           spole=(-0.62, 0.06, -0.78)),
        kd(25, dz=-0.470, dy=-0.052, hips_pitch=82.0, chest_pitch=-3.0,
           head_pitch=0.0, wloc=1.0, wrot=1.0,
           rfoot=(S.ANK.x + 0.026, 0.420, -8.0, 7.0),
           lfoot=(-S.ANK.x - 0.026, 0.412, -8.0, -8.0),
           sp=SH_FLOOR, sn=SH_N_FLOOR, su=SH_U_FLOOR, grip=SH_GRIP,
           spole=(-0.62, 0.04, -0.78)),
        kd(29, dz=-0.484, dy=-0.054, hips_pitch=88.0, chest_pitch=-3.0,
           head_pitch=1.0, wloc=1.0, wrot=1.0,
           rfoot=(S.ANK.x + 0.028, 0.436, -9.0, 7.0),
           lfoot=(-S.ANK.x - 0.028, 0.428, -9.0, -8.0),
           sp=SH_FLOOR - Vector((0.004, 0.004, 0.004)), sn=SH_N_FLOOR,
           su=SH_U_FLOOR, grip=SH_GRIP),
        kd(32, dz=-0.486, dy=-0.054, hips_pitch=89.0, chest_pitch=-3.0,
           head_pitch=1.0, wloc=1.0, wrot=1.0,
           rfoot=(S.ANK.x + 0.028, 0.438, -9.0, 7.0),
           lfoot=(-S.ANK.x - 0.028, 0.430, -9.0, -8.0),
           sp=SH_FLOOR - Vector((0.004, 0.004, 0.004)), sn=SH_N_FLOOR,
           su=SH_U_FLOOR, grip=SH_GRIP),
    ]
    PL.bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ══ 6. guard_raise（14f）：盾先向右外翻再压到胸前，别直上直下 ═══════════════
def a_guard_raise(rig, D=14):
    keys = [
        _kd(0, dz=-0.006, chest_pitch=-1.5, rw=RW0, sd=RD0),
        _kd(4, dz=-0.030, hips_yaw=-5.0, chest_yaw=-4.0, chest_pitch=-3.0,
            rw=Vector((0.318, 0.040, 0.760)), sd=Vector((0.30, 0.40, 0.87)),
            sp=Vector((-0.380, 0.190, 0.940)), sn=Vector((-0.76, 0.62, 0.20)),
            spole=(-0.66, 0.22, -0.72),
            rfoot=(S.ANK.x + 0.010, -0.034, -1.0, 6.0),
            lfoot=(-S.ANK.x - 0.014, 0.052, 2.0, -7.0)),
        _kd(9, dz=-0.052, hips_yaw=-9.0, chest_yaw=-9.0, chest_pitch=-2.0,
            chest_roll=-2.0, head_pitch=3.0, head_yaw=5.0,
            rw=GW + Vector((0.0, -0.030, -0.020)), sd=GD + Vector((0.0, -0.20, -0.20)),
            sp=GS + Vector((-0.030, -0.020, -0.040)), sn=GN + Vector((-0.10, -0.06, 0.06)),
            spole=(-0.66, 0.28, -0.70),
            rfoot=GFOOT_R, lfoot=GFOOT_L),
        _gkd(12, dz=-0.060, sp=GS + Vector((0.0, 0.008, 0.008)),
             sn=GN + Vector((0.0, 0.0, 0.03))),
        _gkd(14),
    ]
    return _baked(rig, "guard_raise", keys, D)


# ══ 7. guard_idle（108f）：举着盾呼吸 + 从盾沿上方扫视 ═══════════════════════
def a_guard_idle(rig, D=108):
    """举盾待机最怕"端着"：这里给三件活 —— 盾沿 8 mm 起伏、头从盾沿上方看出去、
    重心在前后脚之间换一次。盾始终朝前，只有 1~2° 的漂移。"""
    keys = [
        _gkd(0),
        _gkd(18, dz=-0.062, chest_pitch=-4.5, head_pitch=5.0,
             sp=GS + Vector((0.0, 0.006, 0.005)),
             sn=GN + Vector((0.0, 0.0, 0.02))),
        _gkd(34, dz=-0.064, chest_pitch=-5.0, head_yaw=15.0, head_pitch=5.0,
             head_roll=-2.0,
             sp=GS + Vector((0.0, 0.008, 0.003)),
             sn=GN + Vector((-0.05, 0.0, 0.02))),
        _gkd(52, dz=-0.050, chest_pitch=-2.5, head_yaw=5.0, head_pitch=3.0,
             sp=GS + Vector((0.0, 0.002, -0.004))),
        _gkd(70, dz=-0.068, dx=0.010, hips_roll=1.5, chest_pitch=-5.0,
             chest_yaw=-15.0, chest_roll=-3.0, head_pitch=4.0, head_yaw=2.0,
             sp=GS + Vector((-0.008, 0.010, 0.006)),
             sn=GN + Vector((0.03, -0.02, 0.02)),
             rw=GW + Vector((0.0, -0.006, 0.004))),
        _gkd(88, dz=-0.058, chest_pitch=-4.0, head_yaw=9.0,
             sp=GS + Vector((0.0, 0.004, 0.002))),
        _gkd(98, dz=-0.054, chest_pitch=-3.5, sp=GS + Vector((0.0, 0.002, 0.0))),
        _gkd(108),
    ]
    return _baked(rig, "guard_idle", keys, D)


# ══ 8. guard_walk（26f）：举着盾走，盾不跟着身体左右摇 ═══════════════════════
def a_guard_walk(rig, D=26):
    act = PL.new_action(rig.arm, "guard_walk")
    W = PL.Writer(rig, loc_bones=LOC_BONES)
    for i in range(D + 1):
        t = (i % D) / float(D)
        P = AH.pose(rig, S)
        AH.walk(P, S, t, step=0.118, lift=0.058, base_dz=-0.062,
                base_pitch=-3.0, hips_yaw=-9.0, chest_yaw=-9.0,
                chest_roll=-2.0, head_yaw=6.0, sink=0.012,
                side_sway=0.014, y_off=0.010)
        cy = math.cos(2.0 * math.pi * t)
        c2 = math.cos(4.0 * math.pi * t)
        # 盾：只做 4 mm 起伏 + 1° 上仰，横向不摇（摇起来像在晃门板）
        U.weld_shield(P, GS + Vector((0.0, 0.004 * cy, 0.005 * abs(cy))),
                      GN + Vector((0.0, 0.0, 0.018 * cy)), GU, GPOLE, grip=GRIP)
        PL.sword_at(P, "R", GW + Vector((0.0, -0.012 * cy, 0.008 * abs(cy))),
                    GD + Vector((0.0, 0.0, 0.10 * c2)), 0.0, GPOLE_R)
        AH.ground(P, S)
        W.key(P, i)
    PL.finish_action(act)
    return act


# ══ 9. guard_attack（24f）：盾击 → 从盾右下刺出 → 收 ═════════════════════════
def a_guard_attack(rig, D=24):
    keys = [
        _gkd(0),
        # 蓄：盾回收 4 cm，重心压后腿
        _gkd(5, dz=-0.070, hips_yaw=-16.0, chest_yaw=-15.0, chest_pitch=-6.0,
             sp=GS + Vector((0.020, -0.012, -0.010)),
             sn=GN + Vector((0.12, -0.10, -0.10)),
             rfoot=(S.ANK.x + 0.014, -0.112, -3.0, 12.0),
             lfoot=(-S.ANK.x - 0.014, 0.116, 3.0, -8.0)),
        # 盾击命中 f8：盾整体前顶 0.13 m、盾面转向正前
        _gkd(8, dz=-0.046, hips_yaw=-4.0, chest_yaw=-4.0, chest_pitch=-1.0,
             chest_roll=0.0, head_pitch=2.0, head_yaw=2.0,
             sp=GS + Vector((-0.010, 0.130, -0.042)),
             sn=Vector((-0.14, 0.98, 0.12)), spole=(-0.66, 0.44, -0.60),
             rfoot=(S.ANK.x + 0.018, -0.056, 1.0, 11.0),
             lfoot=(-S.ANK.x - 0.014, 0.148, 2.0, -8.0),
             rw=GW + Vector((0.0, -0.024, 0.012))),
        # 剑从盾右下刺出 f15
        _gkd(15, dz=-0.064, hips_yaw=4.0, chest_yaw=6.0, chest_pitch=-8.0,
             chest_roll=2.0, head_pitch=4.0, head_yaw=-6.0,
             sp=GS + Vector((0.004, 0.050, -0.010)),
             sn=Vector((-0.22, 0.96, 0.14)),
             rw=Vector((0.238, 0.492, 0.928)),
             sd=Vector((0.02, 0.97, 0.24)),
             rfoot=(S.ANK.x + 0.018, -0.036, 2.0, 11.0),
             lfoot=(-S.ANK.x - 0.014, 0.160, 2.0, -8.0)),
        _gkd(18, dz=-0.066, hips_yaw=4.0, chest_yaw=6.0, chest_pitch=-8.0,
             chest_roll=2.0, head_pitch=4.0, head_yaw=-6.0,
             sp=GS + Vector((0.004, 0.042, 0.0)),
             sn=Vector((-0.22, 0.96, 0.14)),
             rw=Vector((0.240, 0.486, 0.926)),
             sd=Vector((0.02, 0.97, 0.24)),
             rfoot=(S.ANK.x + 0.018, -0.036, 2.0, 11.0),
             lfoot=(-S.ANK.x - 0.014, 0.160, 2.0, -8.0)),
        _gkd(21, dz=-0.060, hips_yaw=-6.0, chest_yaw=-8.0, chest_pitch=-4.0,
             sp=GS + Vector((0.0, 0.012, 0.0))),
        _gkd(24),
    ]
    return _baked(rig, "guard_attack", keys, D)


# ══ 10. guard_hurt（9f）：盾被顶偏又弹回 ═════════════════════════════════════
def a_guard_hurt(rig, D=9):
    keys = [
        _gkd(0),
        _gkd(3, dz=-0.084, dx=0.012, hips_pitch=1.0, chest_pitch=1.0,
             chest_roll=-9.0, chest_yaw=-4.0, head_pitch=12.0, head_yaw=2.0,
             head_roll=-6.0,
             sp=GS + Vector((0.030, -0.030, -0.016)),
             sn=Vector((-0.34, 0.86, 0.40)), spole=(-0.58, 0.22, -0.74),
             rw=GW + Vector((0.020, -0.030, -0.014)),
             rfoot=(S.ANK.x + 0.030, -0.126, -4.0, 12.0),
             lfoot=(-S.ANK.x - 0.026, 0.078, 3.0, -10.0)),
        _gkd(6, dz=-0.066, dx=0.006, chest_pitch=-2.0, chest_roll=-4.0,
             head_pitch=7.0, head_yaw=6.0,
             sp=GS + Vector((0.010, -0.016, -0.004)),
             sn=GN + Vector((0.04, -0.02, 0.06)),
             rfoot=(S.ANK.x + 0.024, -0.104, -3.0, 12.0),
             lfoot=(-S.ANK.x - 0.022, 0.090, 4.0, -9.0)),
        _gkd(8, dz=-0.060, dx=0.002, chest_pitch=-4.0,
             sp=GS + Vector((0.002, -0.004, 0.0))),
        _gkd(9),
    ]
    return _baked(rig, "guard_hurt", keys, D)


# ══ 11. guard_death（40f）：盾被劈开落地 → 往后坐 → 仰面 ═════════════════════
def a_guard_death(rig, D=40):
    act = PL.new_action(rig.arm, "guard_death")
    W = PL.Writer(rig, loc_bones=LOC_BONES)
    R_FLOOR = U.sword_floor_rot(rig.rest["weapon_R"][1])
    W_FLOOR = Vector((0.410, 0.060, 0.086))
    SH_FLOOR = Vector((-0.700, -0.080, 0.140))
    SH_N_FLOOR = Vector((0.04, 0.22, 0.97))
    SH_U_FLOOR = Vector((-0.98, 0.18, 0.06))
    SH_GRIP = (0.0, 0.05, 0.02)

    def emit(f, d):
        P = AH.pose(rig, S, dz=d["dz"], dx=d["dx"], dy=d["dy"],
                    hips_yaw=d["hips_yaw"], hips_pitch=d["hips_pitch"],
                    hips_roll=d["hips_roll"], spine_pitch=d["spine_pitch"],
                    chest_pitch=d["chest_pitch"], chest_yaw=d["chest_yaw"],
                    chest_roll=d["chest_roll"], head_pitch=d["head_pitch"],
                    head_yaw=d["head_yaw"], head_roll=d["head_roll"])
        for side, v in (("R", d["rfoot"]), ("L", d["lfoot"])):
            x, y, pitch, yaw = v[:4]
            lift = v[4] if len(v) > 4 else 0.0
            AH.leg(P, S, side, x, y, pitch, yaw, lift)
        U.weld_shield(P, d["sp"], d["sn"], d["su"], d["spole"], grip=d.get("grip"))
        PL.sword_at(P, "R", d["rw"], d["sd"], d["sr"], d["rpole"])
        if d["wloc"] > 0.0 or d["wrot"] > 0.0:
            AH.drop_layered(P, "weapon_R", W_FLOOR, R_FLOOR, d["wloc"], d["wrot"])
        W.key(P, f)

    def kd(f, **kw):
        d = dict(GBODY)
        d.update(dict(rw=GW.copy(), sd=GD.copy(), sr=0.0, rpole=GPOLE_R,
                      rfoot=GFOOT_R, lfoot=GFOOT_L,
                      sp=GS.copy(), sn=GN.copy(), su=GU.copy(), spole=GPOLE,
                      wloc=0.0, wrot=0.0, dx=0.0, dy=0.0,
                      hips_roll=0.0, head_roll=0.0))
        d.update(kw)
        d["f"] = f
        return f, d

    keys = [
        kd(0),
        # 重击：盾被劈开、人往后仰
        kd(5, dz=-0.092, dx=0.014, hips_yaw=-20.0, chest_yaw=-20.0,
           chest_pitch=5.0, chest_roll=-9.0, head_pitch=-10.0, head_yaw=-4.0,
           sp=GS + Vector((0.036, 0.072, 0.014)),
           sn=Vector((-0.26, 0.70, 0.66)), spole=(-0.46, 0.06, -0.88),
           rw=GW + Vector((0.020, -0.040, 0.020)),
           rfoot=(S.ANK.x + 0.034, -0.146, -4.0, 12.0),
           lfoot=(-S.ANK.x - 0.020, 0.048, 4.0, -10.0)),
        kd(10, dz=-0.150, dx=0.016, hips_yaw=-10.0, hips_pitch=10.0,
           chest_pitch=4.0, chest_roll=-7.0, head_pitch=-8.0, wrot=0.5,
           rw=Vector((0.320, 0.010, 0.720)), sd=Vector((0.42, 0.30, 0.86)),
           rfoot=(S.ANK.x + 0.024, -0.086, -2.0, 11.0),
           lfoot=(-S.ANK.x - 0.016, 0.070, 3.0, -9.0),
           sp=SH_FLOOR + Vector((0.050, 0.290, 0.300)), sn=SH_N_FLOOR,
           spole=(-0.50, 0.10, -0.86)),
        # 盾先横甩到体侧（这一帧是关键：不加它，0.55 m 的盾面会从胸口扫过去）
        kd(13, dz=-0.196, dx=0.010, dy=-0.010, hips_yaw=-14.0, hips_pitch=20.0,
           chest_pitch=2.0, chest_roll=-6.0, head_pitch=-4.0,
           rw=Vector((0.330, 0.010, 0.760)), sd=Vector((0.42, 0.22, 0.88)), wrot=0.35,
           rfoot=(S.ANK.x + 0.028, -0.020, -3.0, 11.0),
           lfoot=(-S.ANK.x - 0.018, 0.084, 4.0, -9.0),
           sp=Vector((-0.560, 0.180, 0.760)), sn=Vector((-0.86, 0.44, 0.26)),
           spole=(-0.52, 0.10, -0.85)),
        kd(16, dz=-0.290, dy=-0.030, hips_yaw=-4.0, hips_pitch=34.0,
           chest_pitch=0.0, head_pitch=-4.0, wloc=0.6, wrot=1.0,
           rfoot=(S.ANK.x + 0.018, 0.130, -4.0, 9.0),
           lfoot=(-S.ANK.x - 0.022, 0.120, -4.0, -10.0),
           sp=Vector((-0.610, 0.010, 0.300)), sn=SH_N_FLOOR, su=SH_U_FLOOR,
           grip=(0.0, 0.05, 0.02),
           spole=(-0.56, 0.08, -0.82)),
        kd(24, dz=-0.396, dy=-0.048, hips_pitch=62.0, chest_pitch=-2.0,
           head_pitch=-2.0, wloc=0.9, wrot=1.0,
           rfoot=(S.ANK.x + 0.026, 0.240, -6.0, 10.0),
           lfoot=(-S.ANK.x - 0.030, 0.230, -6.0, -11.0),
           sp=Vector((-0.640, -0.060, 0.180)), sn=SH_N_FLOOR, su=SH_U_FLOOR,
           grip=(0.0, 0.05, 0.02),
           spole=(-0.60, 0.06, -0.80)),
        kd(31, dz=-0.452, dy=-0.056, hips_pitch=84.0, chest_pitch=-3.0,
           head_pitch=0.0, wloc=1.0, wrot=1.0,
           rfoot=(S.ANK.x + 0.032, 0.320, -8.0, 11.0),
           lfoot=(-S.ANK.x - 0.036, 0.310, -8.0, -12.0),
           sp=SH_FLOOR, sn=SH_N_FLOOR, su=SH_U_FLOOR, grip=SH_GRIP,
           spole=(-0.62, 0.04, -0.78)),
        kd(37, dz=-0.466, dy=-0.058, hips_pitch=88.0, chest_pitch=-3.0,
           head_pitch=1.0, wloc=1.0, wrot=1.0,
           rfoot=(S.ANK.x + 0.034, 0.334, -9.0, 11.0),
           lfoot=(-S.ANK.x - 0.038, 0.324, -9.0, -12.0),
           sp=SH_FLOOR - Vector((0.004, 0.0, 0.004)), sn=SH_N_FLOOR,
           su=SH_U_FLOOR, grip=SH_GRIP),
        kd(40, dz=-0.468, dy=-0.058, hips_pitch=89.0, chest_pitch=-3.0,
           head_pitch=1.0, wloc=1.0, wrot=1.0,
           rfoot=(S.ANK.x + 0.034, 0.336, -9.0, 11.0),
           lfoot=(-S.ANK.x - 0.038, 0.326, -9.0, -12.0),
           sp=SH_FLOOR - Vector((0.004, 0.0, 0.004)), sn=SH_N_FLOOR,
           su=SH_U_FLOOR, grip=SH_GRIP),
    ]
    PL.bake(keys, D, emit)
    PL.finish_action(act)
    return act


# ══ 12. guard_lower（14f）：盾先向外侧翻出去再落回体侧 ═══════════════════════
def a_guard_lower(rig, D=14):
    keys = [
        _gkd(0),
        _gkd(5, dz=-0.060, hips_yaw=-8.0, chest_yaw=-10.0, chest_pitch=-4.0,
             sp=Vector((-0.280, 0.294, 1.000)), sn=Vector((-0.52, 0.80, 0.28)),
             spole=(-0.70, 0.26, -0.66),
             rw=GW + Vector((0.0, -0.010, 0.004)),
             sd=GD + Vector((0.0, -0.10, -0.10))),
        _kd(10, dz=-0.034, hips_yaw=-4.0, chest_yaw=-4.0, chest_pitch=-3.0,
            rw=Vector((0.318, 0.060, 0.716)), sd=Vector((0.30, 0.34, 0.89)),
            sp=Vector((-0.386, 0.226, 0.906)), sn=Vector((-0.74, 0.64, 0.20)),
            spole=(-0.62, 0.18, -0.76),
            rfoot=(S.ANK.x + 0.008, -0.030, -1.0, 5.0),
            lfoot=(-S.ANK.x - 0.012, 0.046, 2.0, -6.0)),
        _kd(14, dz=-0.006, chest_pitch=-1.5, chest_yaw=1.0, head_pitch=1.0,
            rw=RW0, sd=RD0),
    ]
    return _baked(rig, "guard_lower", keys, D)


# ══ 汇总 ════════════════════════════════════════════════════════════════════
TABLE = [
    ("idle", a_idle), ("walk", a_walk), ("attack", a_attack),
    ("hurt", a_hurt), ("death", a_death),
    ("guard_raise", a_guard_raise), ("guard_idle", a_guard_idle),
    ("guard_walk", a_guard_walk), ("guard_attack", a_guard_attack),
    ("guard_hurt", a_guard_hurt), ("guard_death", a_guard_death),
    ("guard_lower", a_guard_lower),
]


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
    # 旧资产里的 cast 是原模型的遗留动作，手与剑都没焊过 —— 直接删掉
    for junk in ("cast",):
        a = bpy.data.actions.get(junk)
        if a:
            bpy.data.actions.remove(a)
            print("[anim] drop legacy", junk)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    return out
