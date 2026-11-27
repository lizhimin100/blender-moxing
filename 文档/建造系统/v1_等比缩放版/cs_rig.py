"""cs_rig.py —— 通用建造骨架：把任意建筑切成层，加一套骨，写一条 build 动作。

系统契约（建筑只给这几样）：
    footprint (W, D)  占地（场地 bbox）
    height    H       总高
    yaw               朝向（度，正面 +Y）
    attach            挂点表
本体 bbox 由一次离线测量得到（不进运行时契约），用来把脚手架贴到墙边。

为什么用"层 + 骨"而不是逐件动画：
  * 建筑在交付前已按材质合并成 4 个对象，件级信息没了；按高度切层是唯一
    对任何建筑都成立、且不需要重跑建模脚本的分解方式。
  * 刚性权重 1.0 → 层内所有材质的相对位置逐帧不变 → 不可能错位。
  * 一条 action 同时驱动层骨与工地骨 → GLB 里只有一个 clip，引擎只播一次。
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from cs_kit import LIFT_H

FPS = 30.0
BAND_MIN, BAND_MAX = 4, 9
BAND_TARGET = 2.05          # 每层大约多高
T_PLOT = 0.02
T_STAKE = 0.07
T_ROPE = 0.11
T_PILES = 0.13
T_HOIST = 0.19
T_BAND0 = 0.58
BAND_DT = 0.25
BAND_MOVE = 0.20


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


def band_edges(H):
    """层高表：第一层给台基（0.55），其余等分；层数随高度走。"""
    n = int(max(BAND_MIN, min(BAND_MAX, round(H / BAND_TARGET))))
    z0 = min(0.55, H * 0.05)
    step = (H - z0) / (n - 1)
    edges = [0.0, z0] + [z0 + step * i for i in range(1, n)]
    edges[-1] = H
    return [round(e, 4) for e in edges]


# ── 切层 ──────────────────────────────────────────────────────────────────
def _bisect(bm, z, keep_above):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(
        bm, geom=geom, dist=1e-5, plane_co=(0, 0, z), plane_no=(0, 0, 1),
        clear_inner=keep_above, clear_outer=not keep_above,
    )


def slice_bands(ob, edges, names):
    """把 ob 按 edges 切成 len(edges)-1 个对象，每个对象一个顶点组。"""
    out = []
    H = edges[-1]
    src = ob.data
    for i in range(len(edges) - 1):
        z0, z1 = edges[i], edges[i + 1]
        me = src.copy()
        bm = bmesh.new()
        bm.from_mesh(me)
        if z0 > 1e-4:
            _bisect(bm, z0, keep_above=True)
        if z1 < H - 1e-4:
            _bisect(bm, z1, keep_above=False)
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(me)
        bm.free()
        me.update()
        o = bpy.data.objects.new(f"{ob.name}_b{i:02d}", me)
        bpy.context.scene.collection.objects.link(o)
        g = o.vertex_groups.new(name=names[i])
        g.add([v.index for v in me.vertices], 1.0, "REPLACE")
        out.append(o)
    return out


def join(objs, name):
    for o in bpy.data.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    for o in bpy.data.objects:
        o.select_set(False)
    return ob


def weld(ob, dist=0.0002):
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(False)


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
def build(building, kit, edges, yaw=0.0, detail="low", verbose=True):
    """building: 已合并的单个 mesh 对象；kit: cs_kit.Kit。返回 (arm, t_end, marks)。"""
    H = edges[-1]
    nb = len(edges) - 1
    band_names = [f"band_{i:02d}" for i in range(nb)]

    weld(building)
    band_objs = slice_bands(building, edges, band_names)
    bpy.data.objects.remove(building, do_unlink=True)
    body = join(band_objs, "Building")
    site = kit.to_object("SiteKit", detail=detail)
    for o in (body, site):
        if yaw:
            o.rotation_euler = (0, 0, math.radians(yaw))
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    bones = [("band_root", (0, 0, 0), None)]
    bones += [(band_names[i], (0, 0, edges[i]), "band_root") for i in range(nb)]
    kit_bones = sorted(kit.bones.keys(),
                       key=lambda n: (0 if n.startswith("site_scaf") else 1, n))
    for n in kit_bones:
        bones.append((n, kit.bones[n], None))
    arm = make_armature(bones)
    bind(body, arm)
    bind(site, arm)

    # ── 时间表：放线 → 立架 → 整栋拔地 → 收尾微沉 → 撤架 → 清场 ──
    lh = kit.meta["lifts"]
    t_scaf = 0.46
    t_rise0 = 0.86
    rise = max(1.15, min(3.10, 0.85 + H * 0.085))   # 高的慢一点，但不线性
    t_rise1 = t_rise0 + rise
    t_settle = t_rise1 + 0.02
    t_dism = t_settle + 0.36
    t_clean = t_dism + lh * 0.10 + 0.22
    t_end = t_clean + 0.55
    # 脚手架在楼体抬头前立好（0.1 s 一层），随后楼在架子里长
    lift_t = [t_rise0 - 0.30 + k * 0.10 for k in range(lh)]

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

    # 1) 根骨：整栋以地基为原点从地表"冒"出来（等比 → 绝不会出现切片）
    #    曲线前快后慢：0.10 s 到 1/3，末段慢慢落定，像被从地里顶出来
    root = pb("band_root")
    key_scale(root, 0.0, 0.001)
    key_scale(root, t_rise0 - 0.08, 0.001)
    key_scale(root, t_rise0, 0.10)
    key_scale(root, t_rise0 + rise * 0.28, 0.36)
    key_scale(root, t_rise0 + rise * 0.56, 0.63)
    key_scale(root, t_rise0 + rise * 0.82, 0.86)
    key_scale(root, t_rise1, (1.014, 1.0, 1.014))
    key_scale(root, t_settle + 0.14, (0.996, 1.0, 0.996))
    key_scale(root, t_settle + 0.30, 1.0)

    # 3) 场地：从地里顶出来（不是缩放入场）
    for name, t in (("site_plot", 0.02), ("site_stake", 0.06), ("site_rope", 0.09),
                    ("site_pile_a", 0.12), ("site_pile_b", 0.15),
                    ("site_barrel", 0.18), ("site_tub", 0.20)):
        rise_from_ground(name, t)
    hoist = rise_from_ground("site_hoist", 0.22, speed=3.0)
    if hoist and "site_hook" in arm.pose.bones:
        hdz, hdur = hoist
        p = pb("site_hook")
        key_loc(p, 0.0, (0, 0, hdz))
        key_loc(p, 0.22, (0, 0, hdz))
        key_loc(p, 0.22 + hdur, (0, 0, 0))
    if "site_dust" in arm.pose.bones:
        rise_from_ground("site_dust", t_rise0 - 0.04, speed=2.0)

    # 4) 脚手架：一层层立起来，最后从上往下拆
    for k in range(lh):
        n = f"site_scaf_{k}"
        if n not in arm.pose.bones:
            continue
        p = pb(n)
        te = lift_t[k]
        td = t_dism + (lh - 1 - k) * 0.10
        key_scale(p, 0.0, 0.0)
        key_scale(p, te - 0.01, 0.0)
        key_scale(p, te, (1, 0.0, 1))
        key_scale(p, te + 0.08, (1, 1.03, 1))
        key_scale(p, te + 0.14, (1, 1.0, 1))
        key_scale(p, td, (1, 1.0, 1))
        key_scale(p, td + 0.12, 0.0)

    # 5) 旗 / 挂幡：布是"展开"，不是"顶出来"
    for n in ("site_flag", "site_banner"):
        if n not in arm.pose.bones:
            continue
        p = pb(n)
        t_flag = lift_t[-1] + 0.12
        key_scale(p, 0.0, 0.0)
        key_scale(p, t_flag, 0.0)
        key_scale(p, t_flag + 0.12, 1.0)
        key_scale(p, t_dism - 0.06, 1.0)
        key_scale(p, t_dism + 0.03, 0.0)

    # 6) 收尾：退回地里
    for n, d in (("site_dust", 0.00), ("site_hook", -0.06), ("site_hoist", 0.02),
                 ("site_pile_a", 0.10), ("site_pile_b", 0.15),
                 ("site_barrel", 0.19), ("site_tub", 0.23),
                 ("site_rope", 0.29), ("site_stake", 0.33), ("site_plot", 0.37)):
        sink_into_ground(n, t_clean + d)

    ease_all(arm, act)
    sc = bpy.context.scene
    sc.render.fps = int(FPS)
    sc.frame_start = 0
    sc.frame_end = int(t_end * FPS)
    sc.frame_set(0)

    marks = {
        "t_end": round(t_end, 3),
        "scaf": round(t_scaf, 3),
        "rise0": round(t_rise0, 3),
        "rise1": round(t_rise1, 3),
        "bands": [round(t_rise0 + (t_rise1 - t_rise0) * i / nb, 3) for i in range(nb)],
        "lifts": [round(t, 3) for t in lift_t],
        "dismantle": round(t_dism, 3),
        "clean": round(t_clean, 3),
        "n_bands": nb,
        "n_lifts": lh,
    }
    if verbose:
        body.data.calc_loop_triangles()
        site.data.calc_loop_triangles()
        print(f"  bands={nb} lifts={lh} tris={len(body.data.loop_triangles)}+"
              f"{len(site.data.loop_triangles)} bones={len(arm.data.bones)} "
              f"t_end={t_end:.2f}s")
    return arm, t_end, marks
