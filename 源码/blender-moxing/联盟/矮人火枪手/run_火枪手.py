"""run_火枪手.py —— 建联盟·矮人火枪手：几何 → 骨架 → 蒙皮 → 7 条动作 → 多形态导出

用法：
  blender -b --factory-startup --python 联盟/run_火枪手.py -- [detail]

产物（产出/联盟/）：
  方块人_矮人火枪手.glb          全量（身体 + 武器 + 骨架 + 动作）
  方块人_矮人火枪手_低模.glb      低模档（关 Catmull-Clark、倒角 1 段）
  方块人_矮人火枪手_身体.glb      只身体（换装 / 换武器用）
  方块人_矮人火枪手_武器.glb      只武器（自带 weapon_R 插槽骨）
  qc/组件清单.json               每个零件的模块 / 骨 / 材质 / 面数
"""
import importlib
import json
import os
import sys

import bpy
from mathutils import Vector

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

import unitkit as K  # noqa: E402
import unit_火枪手 as U  # noqa: E402
import anims_火枪手 as A  # noqa: E402

for _m in ("unitkit", "unit_火枪手", "anims_火枪手"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import unitkit as K  # noqa: E402
import unit_火枪手 as U  # noqa: E402
import anims_火枪手 as A  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DETAIL = int(argv[0]) if argv else 1
KEY = "方块人_矮人火枪手"
OUT = os.path.join(os.path.dirname(ROOT), "assets", "单位", "联盟", "矮人火枪手")
QCD = HERE
os.makedirs(QCD, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.frame_start = 0
scene.frame_end = 120


def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def stats(objs):
    tris = 0
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in objs:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            for i in range(3):
                mn[i] = min(mn[i], p[i])
                mx[i] = max(mx[i], p[i])
    return tris, mn, mx


def export(path, objs, extra=()):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keep = {o.name for o in list(objs) + list(extra)}
    for ob in list(bpy.data.objects):
        if ob.name not in keep:
            bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in list(objs) + list(extra):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = list(objs)[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True,
        export_apply=False, export_yup=True, export_texcoords=True,
        export_normals=True, export_materials="EXPORT",
        export_image_format="AUTO", export_skins=True,
        export_animations=True, export_animation_mode="ACTIONS",
        export_nla_strips=False, export_bake_animation=False,
        export_force_sampling=True, export_anim_slide_to_zero=True,
        export_optimize_animation_size=False, export_anim_single_armature=True,
        export_def_bones=False,
    )
    bpy.ops.object.select_all(action="DESELECT")
    print("[out]", os.path.basename(path), os.path.getsize(path) // 1024, "KB")
    return os.path.getsize(path)


def join_weapon(wobjs):
    """武器三桶（body/team/trim）合并成一个多材质物体 unit_weapon。"""
    bpy.ops.object.select_all(action="DESELECT")
    for o in wobjs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = wobjs[0]
    if len(wobjs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = "unit_weapon"
    ob.data.name = "unit_weapon"
    bpy.ops.object.select_all(action="DESELECT")
    return ob


MANIFEST = []


def collect_manifest(u):
    """finish() 之后源物体已被 join 掉，清单必须在 finish 前抓。"""
    out = []
    for (ob, bone, mat, bev, seg, sub, sm) in u.parts:
        ob.data.calc_loop_triangles()
        n = len(ob.data.vertices)
        c = (sum((Vector(v.co) for v in ob.data.vertices), Vector()) / n) if n else Vector()
        out.append({"part": ob.name, "module": U.module_of(ob.name), "bone": bone,
                    "material": mat, "tris": len(ob.data.loop_triangles),
                    "center": [round(v, 3) for v in c]})
    return out


def build_unit(with_weapon=True, low=False):
    """身体与武器分别成件：武器永远是一个独立物体 unit_weapon（可拆可换）。"""
    clear()
    u = U.build(DETAIL, ["body", "head", "shoulder", "gear"])
    if low:
        U.low_poly_parts(u)
    collect = collect_manifest(u)
    objs = u.finish(prefix="unit", verbose=False)
    root = bpy.data.objects.new(KEY, None)
    root.empty_display_size = 0.2
    bpy.context.scene.collection.objects.link(root)
    arm = U.build_rig()
    arm.parent = root
    weapon = None
    if with_weapon:
        uw = U.build_weapon_only(DETAIL)
        if low:
            U.low_poly_parts(uw)
        collect += collect_manifest(uw)
        wobjs = uw.finish(prefix="unit_weapon", verbose=False)
        weapon = join_weapon(wobjs)
    global MANIFEST
    MANIFEST = collect
    u.bind(arm, objs)
    if weapon is not None:
        u.bind(arm, [weapon])
    u.root = root
    return u, arm, objs, weapon


# ── ① 全量：几何 + 骨架 + 动作 ──────────────────────────────────────────────
u, arm, objs, weapon = build_unit(with_weapon=True)
allobjs = objs + [weapon]
tris, mn, mx = stats(allobjs)
print("[tris]", tris, "bbox", tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx))
print("[objects]", [(o.name, len(o.data.polygons)) for o in allobjs])
print("[materials]", sorted({m.name for o in allobjs for m in o.data.materials if m}))
print("[bones]", len(arm.data.bones))
print(U.report())

anims = A.build_all(arm)
print("[anim count]", len(anims))

# 组件清单
man = []
for row in MANIFEST:
    man.append(row)
with open(os.path.join(QCD, "组件清单.json"), "w", encoding="utf-8") as f:
    json.dump({"asset": KEY, "modules": list(U.MODULES),
               "bones": [b[0] for b in U.BONES], "parts": man},
              f, ensure_ascii=False, indent=1)
print("[parts]", len(man), "modules",
      {m: sum(1 for p in man if p["module"] == m) for m in U.MODULES})

# 各动作最低点（防穿地）+ 循环检查
def audit_anims():
    arm.animation_data_create()
    for name in anims:
        act = bpy.data.actions[name]
        arm.animation_data.action = act
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        f0, f1 = (int(v) for v in act.frame_range)
        zmin = 1e9
        p0 = p1 = None
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            for ob in allobjs:
                oe = ob.evaluated_get(dg)
                me = oe.to_mesh()
                for v in me.vertices:
                    zmin = min(zmin, (oe.matrix_world @ v.co).z)
                oe.to_mesh_clear()
            if f == f0:
                p0 = [pb.matrix.copy() for pb in arm.pose.bones]
            if f == f1:
                p1 = [pb.matrix.copy() for pb in arm.pose.bones]
        d = 0.0
        for a, b in zip(p0, p1):
            for r in range(4):
                for c in range(4):
                    d = max(d, abs(a[r][c] - b[r][c]))
        print("[anim] %-10s %5.2fs zmin=%.4f loop_d=%.2e"
              % (name, (f1 - f0) / 30.0, zmin, d))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    scene.frame_set(0)


audit_anims()

# 导出全量
export(os.path.join(OUT, KEY + ".glb"), allobjs, extra=[u.root, arm])

# ── ② 低模档 ───────────────────────────────────────────────────────────────
u2, arm2, objs2, weapon2 = build_unit(with_weapon=True, low=True)
all2 = objs2 + [weapon2]
t2, mn2, mx2 = stats(all2)
print("[low tris]", t2, "bbox", tuple(round(v, 3) for v in mn2), tuple(round(v, 3) for v in mx2))
A.build_all(arm2)
export(os.path.join(OUT, KEY + "_低模.glb"), all2, extra=[u2.root, arm2])

# ── ③ 只身体（不带枪）──────────────────────────────────────────────────────
u3, arm3, objs3, _w = build_unit(with_weapon=False)
t3, mn3, mx3 = stats(objs3)
print("[body tris]", t3)
A.build_all(arm3)
export(os.path.join(OUT, KEY + "_身体.glb"), objs3, extra=[u3.root, arm3])

# ── ④ 只武器（自带 weapon_R / prop_ramrod 两根骨）───────────────────────────
clear()
uw = U.build_weapon_only(DETAIL)
wobjs = uw.finish(prefix="unit_weapon", verbose=False)
wobj = join_weapon(wobjs)
warm = bpy.data.armatures.new("RIG_" + KEY + "_weapon")
warm_ob = bpy.data.objects.new("RIG_" + KEY + "_weapon", warm)
scene.collection.objects.link(warm_ob)
wroot = bpy.data.objects.new(KEY + "_武器", None)
wroot.empty_display_size = 0.15
scene.collection.objects.link(wroot)
warm_ob.parent = wroot
bpy.context.view_layer.objects.active = warm_ob
warm_ob.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
for (bn, head, tail) in (("weapon_R", tuple(U.GUN_G), tuple(U.GUN_G + U.GUN_A * 0.30)),
                         ("prop_ramrod", tuple(U.ROD0), tuple(U.ROD1))):
    eb = warm.edit_bones.new(bn)
    eb.head = Vector(head)
    eb.tail = Vector(tail)
    eb.use_connect = False
    if bn == "prop_ramrod":
        eb.parent = warm.edit_bones["weapon_R"]
bpy.ops.object.mode_set(mode="OBJECT")
uw.bind(warm_ob, [wobj])
t4, _, _ = stats([wobj])
print("[weapon tris]", t4)
export(os.path.join(OUT, KEY + "_武器.glb"), [wobj], extra=[wroot, warm_ob])

# ── ⑤ .blend（已停用：本库只交付 glb + 源脚本）──────────────────────────────
u5, arm5, objs5, weapon5 = build_unit(with_weapon=True)
A.build_all(arm5)
txt = bpy.data.texts.new("读我")
txt.write(
    "联盟·矮人火枪手（组件化方块人）\n"
    "1 unit = 1 m；原点在双足中间，z=0 地面；正面 +Y（导出 glTF 后 −Z）。\n"
    "骨架 25 根：root→hips→spine→chest→neck→head；四肢 _R/_L；\n"
    "weapon_R（枪插座，hand_R 的子骨）· prop_ramrod（通条）· weapon_L（副手插座，预留）。\n"
    "材质三个：主体 / team / team_trim。换阵营只改后两个。\n"
    "组件：body（腿胯躯干臂手）· head（颅/盔/胡）· shoulder（护肩）· gear（火药角/弹囊）·\n"
    "      weapon（枪，独立物体 unit_weapon，可直接删掉换别的枪）。\n"
    "动作：idle / idle_alt / walk / attack / reload / hurt / death（30fps）。\n"
    "改色：产出/图集/单位色板.png 的格心，键名见 库/palette.py。\n")
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.file.pack_all()

print("[done]", KEY)
