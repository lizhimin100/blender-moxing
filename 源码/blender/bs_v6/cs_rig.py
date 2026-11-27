"""cs_rig.py —— 建造骨架 v2：**建筑本体一根骨都不加，只有工地套件动。**

v2 与 v1 的根本差别
-------------------
v1 把建筑按高度切成 9 层、绑到 `band_root` 上，靠根骨等比缩放 0.10→1.0 "拔地而起"。
后果是施工中看到的是**完整建筑的缩小版**（大脚手架 + 小建筑），不是半成品。

v2 的做法：
  * 建筑本体 **不切层、不绑骨、不加动画**，几何与源资产逐三角一致，原始尺寸导出。
  * "从下往上显现"由**世界 Z 遮罩**完成 —— 引擎侧一个 uniform（显影高度）
    就能把建筑裁到任意高度；0% 只露地基、50% 露到墙身、100% 完整。
  * 脚手架 / 场件 / 队色旗仍然由骨驱动，但**只做组装动作**：
    逐层 Z 向立起（不是整体缩放）、从地表顶出、撤架时 Z 向收拢。
  * 时间轴与高度**线性绑定**：`高度 = lerp(z0, H, (t - t0) / (t1 - t0))`。
    这条映射同时写进 `建造参数.json`，引擎与预览台用同一个公式，不会走形。

为什么遮罩放在引擎侧而不是烘进 GLB
----------------------------------
glTF 的动画只能驱动 transform / morph / 材质贴图，驱动不了 shader uniform。
把"裁剪高度"烘成几何（每帧一个切面网格）会让资产体积翻几十倍。
所以 GLB 只负责"实体 + 套件动作"，**一条 uniform 就是全部契约**：

    reveal_height ∈ [z0, H]    世界 Z（米），超过它的片元丢弃

`godot/build_reveal.gdshader` 是同一套逻辑的 Godot 实现；预览台用 three.js 实现。
"""
import math

import bpy
from mathutils import Matrix, Vector

from cs_kit import LIFT_H

FPS = 30.0

# ── 时间轴（秒）────────────────────────────────────────────────────────────
T_REV0 = 0.46                 # 建筑开始"长"的时刻
REV_BASE, REV_K = 2.05, 0.075  # 显影时长 = clamp(BASE + K*H, MIN, MAX)
REV_MIN, REV_MAX = 2.20, 3.55
SCAF_LEAD = 0.20              # 脚手架比施工作业面**先**立好 0.2 s
T_GAP_DIS = 0.26              # 显影结束 → 开始撤架
LIFT_DIS_DT = 0.09            # 撤架逐层间隔
T_CLEAN_DT = 0.06
T_TAIL = 0.95

# 场地件顶出时刻（从地表往上冒）
RISE_T = {
    "site_plot": 0.02, "site_stake": 0.07, "site_rope": 0.11,
    "site_pile_a": 0.15, "site_pile_b": 0.18,
    "site_barrel": 0.21, "site_tub": 0.24, "site_hoist": 0.28,
}
# 收尾退回地里的次序
SINK_T = {
    "site_dust": 0.00, "site_hook": -0.04, "site_hoist": 0.03,
    "site_pile_a": 0.12, "site_pile_b": 0.16,
    "site_barrel": 0.20, "site_tub": 0.24,
    "site_rope": 0.30, "site_stake": 0.34, "site_plot": 0.38,
}


# ── 量体 ──────────────────────────────────────────────────────────────────
def measure(objs):
    """返回 (bbox_lo, bbox_hi, body)：body = (x0, x1, y0, y1) 四边外沿（满量）。

    不用百分位：脚手架要包住"门廊台阶、院墙、场地围栏"这些低处外扩件，
    少包 1 cm 就是穿模。四边独立，带院子的建筑才不会把整圈撑成鸟笼。
    """
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    body = (round(lo.x, 3), round(hi.x, 3), round(lo.y, 3), round(hi.y, 3))
    return lo, hi, body


# ── 显影区间 ──────────────────────────────────────────────────────────────
def reveal_z0(H):
    """0% 时露到的高度 = 地基顶。夹在 0.45–1.00 m（只露台基，不露一层窗）。"""
    return round(min(max(H * 0.10, 0.45), 1.00), 3)


def timeline(H, nl):
    z0 = reveal_z0(H)
    rev = max(REV_MIN, min(REV_MAX, REV_BASE + REV_K * H))
    t_rev0 = T_REV0
    t_rev1 = t_rev0 + rev
    t_dis0 = t_rev1 + T_GAP_DIS
    t_dis1 = t_dis0 + 0.14 + nl * LIFT_DIS_DT
    t_clean = t_dis1 + T_CLEAN_DT
    t_end = t_clean + T_TAIL
    return {"z0": z0, "z_rev1": round(H, 3), "rev": round(rev, 3),
            "t_rev0": round(t_rev0, 3), "t_rev1": round(t_rev1, 3),
            "t_dis0": round(t_dis0, 3), "t_dis1": round(t_dis1, 3),
            "t_clean": round(t_clean, 3), "t_end": round(t_end, 3)}


def lift_times(H, nl, tl):
    """第 k 层脚手架立起的时刻：作业面到达该层顶的前 SCAF_LEAD 秒。"""
    span = max(H - tl["z0"], 1e-3)
    out = []
    for k in range(nl):
        ztop = min((k + 1) * LIFT_H, H)
        f = (ztop - tl["z0"]) / span
        t = tl["t_rev0"] + tl["rev"] * f - SCAF_LEAD
        out.append(round(max(tl["t_rev0"] - 0.06, t), 3))
    return out


def reveal_at(t, tl):
    """时间 → 显影高度（米）。引擎 / 预览台用同一个公式。"""
    if t <= tl["t_rev0"]:
        return tl["z0"]
    f = (t - tl["t_rev0"]) / max(tl["rev"], 1e-6)
    return tl["z0"] + (tl["z_rev1"] - tl["z0"]) * max(0.0, min(1.0, f))


# ── 骨架 ──────────────────────────────────────────────────────────────────
def make_armature(bones):
    """bones: [(name, head, parent|None)]，全部竖直骨，roll 0。"""
    arm = bpy.data.armatures.new("BuildRig")
    ob = bpy.data.objects.new("BuildRig", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for item in bones:
        name, head = item[0], item[1]
        parent = item[2] if len(item) > 2 else None
        eb = arm.edit_bones.new(name)
        eb.head = Vector(head)
        eb.tail = Vector(head) + Vector((0, 0, 0.42))
        eb.roll = 0.0
        eb.use_deform = True
        if parent:
            eb.parent = arm.edit_bones[parent]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def bind(mesh, arm):
    mesh.parent = arm
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    md = mesh.modifiers.new("arm", "ARMATURE")
    md.object = arm
    md.use_vertex_groups = True


def _fcurves(action):
    out = []
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
    except Exception:
        pass
    if not out:
        out = list(action.fcurves)
    return out


def _action_slot(arm, action):
    ad = arm.animation_data
    try:
        if hasattr(ad, "action_slot") and action.slots:
            ad.action_slot = action.slots[0]
    except Exception:
        pass


def ease_all(arm, action, interp="BEZIER", handle="AUTO_CLAMPED"):
    for fc in _fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            kp.handle_left_type = handle
            kp.handle_right_type = handle
        fc.update()


# ── 主流程 ────────────────────────────────────────────────────────────────
def build(building, kit, H, yaw=0.0, detail="low", verbose=True):
    """building: 已合并的单个 mesh 对象（**保持原样**）；kit: cs_kit.Kit。

    返回 (arm, t_end, marks)。建筑本体进函数是啥样、出函数还是啥样：
    不切层、不绑骨、不规范、不加动画。
    """
    nl = kit.meta["lifts"]
    tl = timeline(H, nl)
    lt = lift_times(H, nl, tl)

    site = kit.to_object("SiteKit", detail=detail)
    if yaw:
        for o in (building, site):
            o.rotation_euler = (0, 0, math.radians(yaw))
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    arm = make_armature([(n, kit.bones[n], None) for n in sorted(kit.bones)])
    bind(site, arm)

    ad = arm.animation_data_create()
    act = bpy.data.actions.new("build")
    act.use_fake_user = True
    ad.action = act
    _action_slot(arm, act)

    def pb(n):
        return arm.pose.bones[n]

    def key_scale(p, t, s):
        p.scale = s if hasattr(s, "__len__") else (s, s, s)
        p.keyframe_insert("scale", frame=t * FPS)

    def key_loc(p, t, d):
        M = p.bone.matrix_local.to_3x3().inverted()
        p.location = M @ Vector(d)
        p.keyframe_insert("location", frame=t * FPS)

    def rise_from_ground(name, t, speed=4.0):
        if name not in arm.pose.bones:
            return None
        p = pb(name)
        z0, z1 = kit.bone_box.get(name, (0.0, 0.6))
        dz = -(z1 + 0.08)
        dur = max(0.18, min(0.95, -dz / speed))
        key_loc(p, 0.0, (0, 0, dz))
        key_loc(p, t, (0, 0, dz))
        key_loc(p, t + dur, (0, 0, 0))
        return dz, dur

    def sink_into_ground(name, t):
        if name not in arm.pose.bones:
            return
        p = pb(name)
        z0, z1 = kit.bone_box.get(name, (0.0, 0.6))
        key_loc(p, t, (0, 0, 0))
        key_loc(p, t + 0.16, (0, 0, -(z1 + 0.08)))

    def z_grow(name, t, dur=0.16):
        """Z 向从底边长起来（脚手架"立架"——不是整体放大）。

        没到时刻的层必须**搬到 500 m 以外**：Z 压扁到 0 之后几何仍在，会变成
        一片悬在半空的黑色平面（踩过）。先搬走再立起来。
        """
        p = pb(name)
        key_loc(p, 0.0, (0, 0, -500.0))
        key_loc(p, max(0.0, t - 0.02), (0, 0, -500.0))
        key_loc(p, t, (0, 0, 0))
        key_scale(p, 0.0, (1, 0.02, 1))
        key_scale(p, max(0.0, t - 0.01), (1, 0.02, 1))
        key_scale(p, t + dur, (1, 1.05, 1))
        key_scale(p, t + dur + 0.07, (1, 1.0, 1))

    def z_collapse(name, t, ztop, dur=0.12):
        """拆架：Z 向收拢 + 抽到地下。收拢后是零厚度，抽走时看不见。"""
        p = pb(name)
        key_scale(p, t, (1, 1.0, 1))
        key_scale(p, t + dur, (1, 0.02, 1))
        key_loc(p, t, (0, 0, 0))
        key_loc(p, t + dur, (0, 0, -(ztop + 0.15)))

    # 1) 场地：放线 → 桩绳 → 料堆 → 吊装（全部"从地表顶出"）
    for name, t in RISE_T.items():
        rise_from_ground(name, t)
    hoist = rise_from_ground("site_hoist", RISE_T["site_hoist"], speed=3.0)
    if hoist and "site_hook" in arm.pose.bones:
        hdz, hdur = hoist
        p = pb("site_hook")
        key_loc(p, 0.0, (0, 0, hdz))
        key_loc(p, RISE_T["site_hoist"], (0, 0, hdz))
        key_loc(p, RISE_T["site_hoist"] + hdur, (0, 0, 0))
    if "site_dust" in arm.pose.bones:
        rise_from_ground("site_dust", tl["t_rev0"] - 0.10, speed=2.0)

    # 2) 脚手架：跟着作业面一层层立（每层从自己的底面 Z 向立起）
    for k in range(nl):
        n = f"site_scaf_{k}"
        if n not in arm.pose.bones:
            continue
        z_grow(n, lt[k])
        z_collapse(n, tl["t_dis0"] + (nl - 1 - k) * LIFT_DIS_DT,
                   min((k + 1) * LIFT_H, H))

    # 3) 队色：顶层立起后张开，撤架前收
    for n in ("site_flag", "site_banner"):
        if n not in arm.pose.bones:
            continue
        p = pb(n)
        t_flag = lt[-1] + 0.16
        key_scale(p, 0.0, 0.0)
        key_scale(p, t_flag, 0.0)
        key_scale(p, t_flag + 0.14, 1.0)
        key_scale(p, tl["t_dis0"] - 0.04, 1.0)
        key_scale(p, tl["t_dis0"] + 0.06, 0.0)

    # 4) 收尾：依次退回地里
    for n, d in SINK_T.items():
        sink_into_ground(n, tl["t_clean"] + d)

    ease_all(arm, act)
    sc = bpy.context.scene
    sc.render.fps = int(FPS)
    sc.frame_start = 0
    sc.frame_end = int(tl["t_end"] * FPS)
    sc.frame_set(0)

    marks = dict(tl)
    marks.update({
        "lifts": [round(t, 3) for t in lt],
        "n_lifts": nl,
        "reveal": {"axis": "z", "z0": tl["z0"], "z1": round(H, 3),
                   "t0": tl["t_rev0"], "t1": tl["t_rev1"]},
        "body_size": [round(building.dimensions.x, 3),
                      round(building.dimensions.y, 3),
                      round(building.dimensions.z, 3)],
        "n_bands": 0,
    })
    if verbose:
        site.data.calc_loop_triangles()
        building.data.calc_loop_triangles()
        print(f"  lifts={nl} tris={len(building.data.loop_triangles)}"
              f"(body, untouched)+{len(site.data.loop_triangles)}  "
              f"bones={len(arm.data.bones)}  reveal {tl['z0']}→{H:.2f}m  "
              f"t {tl['t_rev0']}→{tl['t_rev1']}s  end {tl['t_end']:.2f}s")
    return arm, tl["t_end"], marks
