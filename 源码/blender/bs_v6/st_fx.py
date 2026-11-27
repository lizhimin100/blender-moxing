"""st_fx.py —— 训练态 / 科研态（完整主体 + 门开着 + 识别效果 / 一条 research clip）

训练态（工单 2.4，静态、零骨骼零动画）
    门扇固定在打开角度（`open_doors`：按左右扇各自的铰链轴转，不做"换一扇新门"），
    门内自发光（走 自发光 材质槽，引擎侧配 bloom），
    各配**一个**识别效果：兵营武器架点亮 / 圣地晶体辉光 / 车坊机械件张开 / 大厅门口光束。

科研态（工单 2.5，有动画）
    铁匠铺：炉火由小到大（scale 0→1 循环）、烟团上升（transform 循环）、锤子敲砧（rotation 往复）
    伐木场：锯片匀速 rotation、原木 translation 往复推进、锯末掉落
    GLB 里是一条名为 `research` 的 clip，**首末一致**（旋转通道按"同一朝向"判：
    q 与 −q 等价，所以判据是 |dot| ≥ 1−1e-3，其余通道按数值相等）。

为什么科研态用一根骨而不是"节点动画"
------------------------------------
一台机器三个部件各挂一个 Action，导出后就是三条同名 clip（Blender 会自动改名
research.001），引擎侧得自己拼；一根骨架 + 一条 Action 才是"一个 clip"。
骨架只挂运动件（火焰 / 烟 / 锤 / 锯 / 原木 / 锯末），其余顶点不进任何骨。
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bslib as L  # noqa: E402
import st_kit as st  # noqa: E402
from bslib import box, cone, extrude  # noqa: E402
from assets_path import asset_path  # noqa: E402

ROOT = r"D:/测试一"
DOC = os.path.join(ROOT, "docs", "状态资产")


def M(name):
    return L.make_material(name)


# ── 门 ──────────────────────────────────────────────────────────────────────
def open_doors(items, prefixes, deg=105.0):
    """把双开门开到 deg（按左右扇**各自的铰链轴**转）。

    左右扇以 x 的正负分（双开门的中缝在 x=0）；铰链取该扇包围盒的**外侧**竖边。
    这样门扇与门框的接触关系（销子那一条边）天然保留，也不会把两扇门当成
    一整块绕外角转 105°（那样两扇会一起甩到墙外）。
    """
    pre = tuple(prefixes)
    sel = [it for it in items if it[0].name.startswith(pre)]
    if not sel:
        return 0
    bpy.context.view_layer.update()
    groups = {-1: [], 1: []}
    for it in sel:
        ob = it[0]
        xs = [(ob.matrix_world @ v.co).x for v in ob.data.vertices]
        if not xs:
            continue
        groups[-1 if sum(xs) / len(xs) < 0 else 1].append(it)
    n = 0
    for sgn, grp in groups.items():
        if not grp:
            continue
        pts = [(ob.matrix_world @ v.co) for it in grp for v in it[0].data.vertices]
        hx = min(p.x for p in pts) if sgn < 0 else max(p.x for p in pts)
        hy = sum(p.y for p in pts) / len(pts)
        pivot = Vector((hx, hy, 0.0))
        rot = Matrix.Rotation(math.radians(deg) * (1 if sgn < 0 else -1), 3, "Z")
        for it in grp:
            ob = it[0]
            ob.data.transform(ob.matrix_world)
            ob.matrix_world = Matrix.Identity(4)
            for v in ob.data.vertices:
                v.co = pivot + rot @ (Vector(v.co) - pivot)
            ob.data.update()
            n += 1
    return n


def light_pool(name, cx, cy, z, w, d, mat="door_light"):
    """门口 / 灯下的光斑：一块 2 cm 厚的自发光薄板，压在门槛石上。

    只做"贴地的一层光"，不做体积光 —— 透明的体积光在 glTF 里要么靠材质混合
    （引擎侧不定）、要么烘成几何（面数爆炸），两种都不该进资产。
    """
    return [(box(name, (cx, cy, z + 0.011), (w, d, 0.022), M(mat)), 0.0, 0, 1)]


def lantern(name, cx, cy, z, size=0.16, mat="door_light"):
    """铁架小灯笼：四根铁柱 + 自发光芯 + 铁顶盖。"""
    out = []
    s = size
    out.append((box(name + "_core", (cx, cy, z + s * 0.55), (s, s, s * 0.8), M(mat)), 0.0, 0, 1))
    for i, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        out.append((box("%s_bar%d" % (name, i),
                        (cx + dx * s * 0.55, cy + dy * s * 0.55, z + s * 0.55),
                        (0.026, 0.026, s * 1.02), M("iron")), 0.0, 0, 1))
    out.append((box(name + "_cap", (cx, cy, z + s * 1.10), (s * 1.32, s * 1.32, 0.05),
                    M("iron")), 0.002, 0, 1))
    out.append((box(name + "_base", (cx, cy, z + 0.02), (s * 1.32, s * 1.32, 0.045),
                    M("iron")), 0.002, 0, 1))
    return out


def door_light(key, cx, y, z0, z1, w, d=0.05):
    """门洞里的一整片门内灯（贴在门洞内的背板上）。"""
    return [(box(key, (cx, y, (z0 + z1) * 0.5), (w, d, z1 - z0), M("door_light")),
             0.0, 0, 1)]


# ── 训练态：兵营（门开 + 武器架点亮）────────────────────────────────────────
def fx_barracks():
    """武器架 (3.95, 8.45)、场地顶面 0.40：架顶两道灯 + 长矛尖的冷光点 + 地面光斑。

    为什么给"矛尖发光"而不是"整架发光"：RTS 距离上整架发光读成"一块橙板"，
    只有尖上那 8 cm 的一点亮才读成"铁在反光 / 有人在磨枪"。
    """
    out = []
    yz = 0.40
    for sgn in (-1, 1):
        out += lantern("train_lamp_%d" % (sgn + 1), 3.95 + sgn * 0.76, 8.45 - 0.10,
                       yz + 1.62, 0.15)
    out += light_pool("train_pool", 3.95, 8.15, yz + 0.005, 2.30, 1.30)
    for k in range(4):
        ox = -0.52 + k * 0.35
        out.append((box("train_tip%d" % k, (3.95 + ox, 8.45 - 0.43, yz + 2.70),
                        (0.085, 0.085, 0.12), M("door_light")), 0.0, 0, 1))
    # 门内：一整片门内灯（贴在原 gate_glow 前面 8 cm）+ 门槛外的地面光斑
    out += door_light("train_door_light", 0.0, 3.80 - 0.68, 0.62, 3.18, 1.62, 0.05)
    # 光斑落在门槛石上（0.50），不是落进夯土里：4.30 那一带是 gate_step 的踏面
    out += light_pool("train_gate_pool", 0.0, 4.30, 0.505, 2.20, 0.48)
    return out


# ── 驱动（训练态）──────────────────────────────────────────────────────────
def assemble(key, do_export=True):
    cfg = CONFIG[key]
    mod = __import__(cfg["mod"])
    st.clear_scene()
    m = mod.Model(False, unwrap=False).build()
    items = list(m.items)
    st.bake_transforms(items)
    if cfg.get("doors"):
        n = open_doors(items, cfg["doors"], cfg.get("door_deg", 105.0))
        print("[%s] 门扇打开 %d 件 @ %.0f°" % (key, n, cfg.get("door_deg", 105.0)))
    fx = cfg["fx"]() if cfg.get("fx") else []
    fx = [(f[0], f[1], f[2], f[3]) if len(f) >= 4 else (f[0], 0.0, 0, 1) for f in fx]
    m.items = items + fx
    print("[%s] 主体 %d 件 + 效果 %d 件" % (key, len(items), len(fx)))
    if cfg["kind"] == "research":
        return assemble_research(key, cfg, m, do_export)
    objs = m.finalize(bevel=True)
    if not do_export:
        return objs
    path, rec = st.finish(objs, key, cfg["prefix"], asset_path(cfg["asset"]),
                          anim=False, front_ratio=cfg["front"])
    rec.update({"asset_name": key, "kind": "训练态", "note": cfg.get("note", ""),
                "parts": len(items), "fx_parts": len(fx)})
    rec["ok"] = bool(rec["ok"] and rec["mat_count"] <= 4 and rec["skins"] == 0)
    _write(key, rec)
    print("[%s] %s tris=%d mats=%d %s" %
          (key, rec["file"], rec["tris"], rec["mat_count"], "OK" if rec["ok"] else "FAIL"))
    return rec


def _write(key, rec):
    d = os.path.join(DOC, key)
    os.makedirs(d, exist_ok=True)
    import json
    with open(os.path.join(d, "receipt.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)


# ── 训练态：城镇大厅（门开 + 门口光束）──────────────────────────────────────
def fx_townhall():
    """大厅的门洞 2.0 宽、内凹 0.14；打开后门内一片暖光 + 门槛上一道光斑。

    "光束"不做体积光：glTF 里没有可靠的体积散射，做出来要么引擎侧不认，
    要么烘成几何（面数翻倍）。RTS 尺度上"门洞很亮 + 地上有光斑"就够读了。
    """
    out = []
    out += door_light("train_door_light", 0.0, 3.02, 0.62, 2.98, 1.86, 0.06)
    out += light_pool("train_pool", 0.0, 3.62, 0.556, 2.10, 0.96)
    # 门两侧一对灯笼（挂在门套上），把"里面有人"这条信息补足
    for sgn in (-1, 1):
        out += lantern("train_lamp_%d" % (sgn + 1), sgn * 1.30, 3.30, 2.35, 0.16)
    return out


# ── 训练态：神秘圣地（符文环 + 门内辉光）────────────────────────────────────
def fx_sanctuary():
    """圣地的"门"不是门扇，是一整块发光的门（`portal_glass`），所以不转门板。

    训练态做在**门前台阶**上（不是内殿门口）：量体显示场地前沿 y 7.50、
    台阶 5.62–6.98、踏面顶 0.90，所以光斑铺在 (0, 6.05, 0.895)、灯笼立在
    台阶两侧。早期版本把符文环铺在 1.72 半径的台面上 —— 整圈落进台基投影，
    45° 下一颗都看不见（教训：先量"这件东西落在哪个标高上"，再谈造型）。
    """
    out = []
    z, y = 0.895, 6.05
    out += light_pool("train_pool", 0.0, y, z, 2.60, 1.10)
    for sgn in (-1, 1):
        out += lantern("train_lamp_%d" % (sgn + 1), sgn * 1.92, y + 0.12, z, 0.18)
    # 台阶两侧各一道队色灯柱（把"圣地正在用"这条线拉到剪影边缘）
    for sgn in (-1, 1):
        out.append((box("train_post%d" % (sgn + 1), (sgn * 2.44, y + 0.10, z + 0.55),
                        (0.16, 0.16, 1.10), M("site_timber_dark")), 0.006, 0, 1))
        out.append((box("train_post_cap%d" % (sgn + 1), (sgn * 2.44, y + 0.10, z + 1.14),
                        (0.22, 0.22, 0.10), M("team_trim")), 0.0, 0, 1))
    return out


# ── 训练态：蒸汽车坊（门开 + 阀轮转过 90° + 炉口透光）──────────────────────
def fx_workshop():
    out = []
    out += door_light("train_door_light", 0.0, 5.30, 0.70, 3.30, 2.20, 0.06)
    out += light_pool("train_pool", 0.0, 4.86, 0.415, 2.60, 1.10)
    # 阀轮转 90°：`pipe_valve_spoke` 是六根辐条，转过来就是"刚开过阀"。
    # **必须绕阀轮中心转**：按世界原点转 90°，辐条会被甩到 z −3.8（地下），
    # 整件资产的 grounded 直接判失败（这一条踩过）。
    obs = [o for o in bpy.data.objects if o.name.startswith("pipe_valve_spoke")]
    if obs:
        pts = [v.co for o in obs for v in o.data.vertices]
        cx = sum(p.x for p in pts) / len(pts)
        cz = sum(p.z for p in pts) / len(pts)
        rot = Matrix.Rotation(math.radians(90), 3, "Y")
        for o in obs:
            for v in o.data.vertices:
                d = rot @ Vector((v.co.x - cx, 0.0, v.co.z - cz))
                v.co = Vector((cx + d.x, v.co.y, cz + d.z))
            o.data.update()
    return out


# ── 铁匠铺：炉火 / 烟 / 锤 ──────────────────────────────────────────────────
HEARTH = (0.29, 4.40, 0.30)      # bs_model.forge_fire 的火塘中心


def bs_bones(items):
    """锤子的枢轴从 `anvil_hammer` 的包围盒算（手柄尾端），不写死常量 ——
    铁砧一旦挪位置，硬编码的枢轴就会让锤子绕着空气转。"""
    bpy.context.view_layer.update()
    hx, hy, hz = -0.52, 6.63, 1.90
    for it in items:
        ob = it[0]
        if ob.name == "anvil_hammer":
            pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
            hx = min(p.x for p in pts)
            hy = sum(p.y for p in pts) / len(pts)
            hz = sum(p.z for p in pts) / len(pts)
            break
    # 烟从**坡棚顶之上**起（z 3.35）：棚顶 2.5–3.2 那一层是木屋面，
    # 烟团放在 1.62 会被整片棚顶挡死，引擎里等于没有烟。
    return [("flame", HEARTH),
            ("smoke0", (HEARTH[0], HEARTH[1] + 0.90, 3.35)),
            ("smoke1", (HEARTH[0] + 0.18, HEARTH[1] + 0.98, 3.35)),
            ("smoke2", (HEARTH[0] - 0.16, HEARTH[1] + 0.84, 3.35)),
            ("hammer", (hx, hy, hz))]


def bs_groups():
    return {"flame": ("flame_", "flametip"),
            "hammer": ("anvil_hammer",)}


def bs_smoke():
    out = []
    for i in range(3):
        ob = box("smoke_%d" % i, (HEARTH[0] + 0.16 * (i - 1), HEARTH[1] + 0.92, 3.35),
                 (0.34, 0.34, 0.34), M("ash"))
        out.append((ob, 0.0, 0, 1, "smoke%d" % i))
    return out


def bs_clip(arm, act):
    """60 帧 / 2 s：火焰呼吸（0.55→1.06）+ 三团烟错相位上升 + 锤子两次敲击。"""
    pb = arm.pose.bones
    n = 60
    f = pb["flame"]
    for (t, sv) in ((0.0, 0.55), (0.22, 0.98), (0.38, 1.06), (0.62, 0.86),
                    (0.80, 1.02), (1.0, 0.55)):
        _key_scale(f, n * t, (sv, sv * 1.03, sv))  # 竖向略高：火舌往上窜；首末必须同值
    for i in range(3):
        p = pb["smoke%d" % i]
        ph = i * 0.30
        seq = ((0.00, 0.0, 0.0), (0.10, 0.9, 0.30), (0.55, 0.55, 1.25),
               (0.95, 0.0, 1.75), (1.00, 0.0, 0.0))
        for (ft, sv, dz) in seq:
            t = n if ft >= 1.0 else n * min(1.0, ph + ft)
            _key_scale(p, t, sv)
            _key_loc(p, t, (0, 0, dz))
    h = pb["hammer"]
    for k in range(3):
        base = 0.10 + 0.28 * k
        _key_rot(h, n * base, 0.0, "Y")
        _key_rot(h, n * (base + 0.09), -34.0, "Y")
        _key_rot(h, n * (base + 0.17), 2.0, "Y")
        _key_rot(h, n * (base + 0.23), 0.0, "Y")
    _key_rot(h, n, 0.0, "Y")


CONFIG = {
    "兵营_训练": dict(asset="兵营", mod="br_model", kind="train", prefix="BR",
                   doors=("gate_leaf", "gate_seam", "gate_iron"), door_deg=118.0,
                   fx=fx_barracks, front=0.95,
                   note="门开 118°、武器架点亮；队色与旗由引擎侧切换"),
    "城镇大厅_训练": dict(asset="城镇大厅", mod="th_model", kind="train", prefix="TH",
                    doors=("gate_leaf", "gate_stile", "gate_rail", "gate_strap",
                           "gate_stud", "gate_ring"), door_deg=112.0,
                    fx=fx_townhall, front=0.95,
                    note="门开 112°、门口光束；队色与旗由引擎侧切换"),
    "神秘圣地_训练": dict(asset="神秘圣地", mod="ms_model", kind="train", prefix="MS",
                    fx=fx_sanctuary, front=0.95,
                    note="符文环 + 门内辉光（圣地没有门扇，不转门板）"),
    "蒸汽车坊_训练": dict(asset="蒸汽车坊", mod="sw_model", kind="train", prefix="SW",
                    doors=("door_leaf",), door_deg=108.0,
                    fx=fx_workshop, front=0.95,
                    note="门开 108°、阀轮转 90°、门内透光"),
    "铁匠铺_科研": dict(asset="铁匠铺", mod="bs_model", kind="research", prefix="BS",
                   bones=bs_bones, groups=lambda: bs_groups(),
                   clip=lambda arm, act: bs_clip(arm, act),
                   fx=lambda: bs_smoke(), front=0.95,
                   note="炉火呼吸 / 三团烟上升 / 锤子敲砧"),
    "伐木场_科研": dict(asset="伐木场", mod="lm_model", kind="research", prefix="LM",
                    bones=lambda: lm_bones(), groups=lambda: lm_groups(),
                    clip=lambda arm, act: lm_clip(arm, act),
                    fx=lambda: lm_dust(), front=0.95,
                    note="锯轮匀速转 / 锯条上下往复 / 原木往复进给 / 锯末掉落"),
}


# ── 科研态：骨架 + 一条 clip ────────────────────────────────────────────────
def _mk_armature(bones, name="Rig"):
    """bones: [(name, head_world, parent|None)]，head 已经是**成品坐标**（X 已镜像）。"""
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for item in bones:
        nm, head = item[0], item[1]
        parent = item[2] if len(item) > 2 else None
        eb = arm.edit_bones.new(nm)
        eb.head = Vector(head)
        eb.tail = Vector(head) + Vector((0, 0, 0.40))
        eb.roll = 0.0
        eb.use_deform = True
        if parent:
            eb.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def _bind(mesh, arm):
    mesh.parent = arm
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    md = mesh.modifiers.new("arm", "ARMATURE")
    md.object = arm
    md.use_vertex_groups = True


def _assign_group(ob, bone):
    """把整件刚性绑到一根骨（权重 1.0）。科研态的运动件都是刚体。"""
    vg = ob.vertex_groups.get(bone) or ob.vertex_groups.new(name=bone)
    vg.add([v.index for v in ob.data.vertices], 1.0, "REPLACE")


def _prep_groups(items, groups):
    """按前缀把构件挂到骨上。返回挂上的件数。"""
    n = 0
    for it in items:
        ob = it[0]
        for bone, prefixes in groups.items():
            if ob.name.startswith(tuple(prefixes)):
                _assign_group(ob, bone)
                n += 1
                break
    return n


def _key_rot(p, frame, deg, axis="Y"):
    m3 = p.bone.matrix_local.to_3x3()
    r = Matrix.Rotation(math.radians(deg), 3, axis)
    p.rotation_mode = "QUATERNION"
    p.rotation_quaternion = (m3.inverted() @ r @ m3).to_quaternion()
    p.keyframe_insert("rotation_quaternion", frame=frame)


def _key_loc(p, frame, d):
    m3 = p.bone.matrix_local.to_3x3()
    p.location = m3.inverted() @ Vector(d)
    p.keyframe_insert("location", frame=frame)


def _key_scale(p, frame, s):
    p.scale = s if hasattr(s, "__len__") else (s, s, s)
    p.keyframe_insert("scale", frame=frame)


def _action_slot(arm, action):
    ad = arm.animation_data
    try:
        if hasattr(ad, "action_slot") and action.slots:
            ad.action_slot = action.slots[0]
    except Exception:
        pass


def assemble_research(key, cfg, m, do_export):
    items = m.items
    grp = cfg["groups"]() if callable(cfg["groups"]) else cfg["groups"]
    ng = _prep_groups(items, grp)
    fx = cfg["fx"]() if cfg.get("fx") else []
    # fx 是 (ob, bevel, sub, seg, bone) 五元组：锯末这类"只在动画里出现"的件
    fx_items = [(f[0], 0.0, 0, 1) for f in fx]
    for f in fx:
        if len(f) > 4 and f[4]:
            _assign_group(f[0], f[4])
    m.items = items + fx_items
    # 骨位必须在 finalize **之前**算：finalize 会把 items 里的对象合并掉，
    # 之后再去读它们的包围盒就是 StructRNA removed（这一条踩过）。
    bones_pre = cfg["bones"](items)
    print("[%s] 绑骨 %d 件  动效件 %d 件" % (key, ng, len(fx_items)))
    objs = m.finalize(bevel=True)

    if not do_export:
        return objs

    def post(packed):
        # 镜像发生在 finalize 里：骨的 x 要取反（建模期 +X 在成品里是 −X）
        bones = [(b[0], (-b[1][0], b[1][1], b[1][2])) + tuple(b[2:]) for b in bones_pre]
        arm = _mk_armature(bones)
        for ob in packed:
            _bind(ob, arm)
        ad = arm.animation_data_create()
        act = bpy.data.actions.new("research")
        act.use_fake_user = True
        ad.action = act
        _action_slot(arm, act)
        cfg["clip"](arm, act)
        sc = bpy.context.scene
        sc.render.fps = st.FPS
        sc.frame_start = 0
        sc.frame_end = cfg.get("frames", 60)
        sc.frame_set(0)
        return [arm]

    path, rec = st.finish(objs, key, cfg["prefix"], asset_path(cfg["asset"]),
                          anim=True, front_ratio=cfg["front"],
                          expect_clip="research", post=post)
    rec.update({"asset_name": key, "kind": "科研态", "note": cfg.get("note", ""),
                "bones": [b[0] for b in bones_pre],
                "frames": cfg.get("frames", 60), "fps": st.FPS})
    rec["ok"] = bool(rec["ok"] and rec["mat_count"] <= 4)
    _write(key, rec)
    print("[%s] %s tris=%d mats=%d clip=%s %s" %
          (key, rec["file"], rec["tris"], rec["mat_count"],
           rec.get("clips"), "OK" if rec["ok"] else "FAIL"))
    return rec


# ── 伐木场：锯轮 / 锯条 / 原木 / 锯末 ───────────────────────────────────────
RX, RY = 1.30, 5.62          # 锯架中心（lm_model 的常量，抄一份当骨位）
WHEEL = (6.42, 3.92, 0.94)   # 飞轮中心（φ1.76）


def lm_bones(_items=None):
    return [("saw_wheel", WHEEL),
            ("saw_blade", (RX, RY, 3.42)),
            ("beam", (RX, RY, 0.50)),
            ("dust0", (RX, RY + 0.30, 0.62)),
            ("dust1", (RX, RY + 0.30, 0.62)),
            ("dust2", (RX, RY + 0.30, 0.62)),
            ("dust3", (RX, RY + 0.30, 0.62))]


def lm_groups():
    return {
        "saw_wheel": ("wheel_rim", "wheel_rim_in", "wheel_hub", "wheel_spoke"),
        "saw_blade": ("saw_blade", "saw_tooth", "saw_grip", "saw_tie"),
        "beam": ("saw_beam",),
    }


def lm_dust():
    """锯末：四粒 5 cm 的小方块（分相位落下）。它们只在动画里出现。"""
    out = []
    for i in range(4):
        ob = box("dust_%d" % i, (RX + 0.06 - 0.04 * i, RY + 0.30, 0.62),
                 (0.055, 0.05, 0.055), M("sand"))
        out.append((ob, 0.0, 0, 1, "dust%d" % i))
    return out


def lm_clip(arm, act):
    """60 帧 / 2 s 一条 loop：
       锯轮 2 圈（每 45° 一个键，四元数才不会被插值走近路）
       锯条 2 个往复（下切 → 回）
       原木推进 0.24 m 再退回
       锯末 4 粒错相位落下，起落两端 scale 0（不可见时归位，不会被看出"瞬移"）
    """
    pb = arm.pose.bones
    n = 60
    wheel = pb["saw_wheel"]
    for k in range(17):
        _key_rot(wheel, n * k / 16.0, -45.0 * k)
    blade = pb["saw_blade"]
    for k in range(5):
        _key_loc(blade, n * k / 4.0, (0, 0, -0.17 if k % 2 else 0.0))
    beam = pb["beam"]
    _key_loc(beam, 0, (0, 0, 0))
    _key_loc(beam, n * 0.46, (0, 0.24, 0))
    _key_loc(beam, n * 0.56, (0, 0.24, 0))
    _key_loc(beam, n, (0, 0, 0))
    # 锯末：两班（0–0.5 / 0.5–1.0）各两粒。**关键帧必须落在各自那半段里**，
    # 一旦用 (ph+f)%1 折回，曲线会在时间轴上折成锯齿，首末永远对不上（踩过）。
    for i in range(4):
        p = pb["dust%d" % i]
        ph = 0.0 if i < 2 else 0.5
        sep = 0.04 * (i % 2)
        seq = ((0.00, 0.0, 0.00), (0.06, 1.0, -0.02), (0.20, 1.0, -0.30),
               (0.30, 0.0, -0.42), (0.50, 0.0, 0.00))
        for (f, sv, dz) in seq:
            t = n * min(1.0, ph + f + sep)
            _key_scale(p, t, sv)
            _key_loc(p, t, (0, 0, dz))
    for fc in _fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.update()


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



RUN = ("铁匠铺_科研",)


def main():
    out = {}
    for key in RUN:
        out[key] = assemble(key)
    print("ST_FX_RECEIPT " + str({k: (v["tris"], v["mat_count"], v["ok"])
                                  for k, v in out.items()}))


main()
