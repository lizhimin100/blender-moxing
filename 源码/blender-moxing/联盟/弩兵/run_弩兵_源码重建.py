"""run_弩兵_源码重建.py —— ⚠ 会重建整张网格（4,508 → 8,966 面）

出厂资产 `方块人_弩兵.glb` **不是**这条路径产的：源码比出厂资产新（多了一层细节：
护肩叠片、膝甲、更大的弩身与踏环）。用户要求"不要重做模型"，所以出货走
`run_弩兵_v4.py`（只在原网格上位移手与弩的顶点）。本文件保留，供以后真要整体升级时用。

"""

"""run_弩兵.py —— 联盟弩兵 v3：修握弩穿模 + 重做 hurt/death，覆盖导出。

流程：导入 `库/_ref/联盟/方块人_弩兵.glb` 的骨架 + 旧动作 → 只重建网格
（几何源码在 unit_弩兵.py，v3 只改了 `build_fist()` 的手）→ 旧动作做微手术 →
重做 hurt/death → 全动作体检 → 覆盖导出。

用法：
  blender -b --factory-startup --python 联盟/弩兵/run_弩兵.py -- [detail]
"""
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
for p in (LIB, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import anims_弩兵 as AN  # noqa: E402
import unit_弩兵 as U  # noqa: E402
import unitkit as K  # noqa: E402
from _qc_rig import RigMesh  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DETAIL = int(argv[0]) if argv else 1
SRC = os.path.join(LIB, "_ref", "联盟", U.NAME + ".glb")
ASSET = os.path.join(os.path.dirname(ROOT), "assets", "单位", "联盟", "弩兵")
OUT = os.path.join(ASSET, U.NAME + ".glb")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0

bpy.ops.import_scene.gltf(filepath=SRC)
root_empty = next(o for o in scene.objects if o.type == "EMPTY")
arm = next(o for o in scene.objects if o.type == "ARMATURE")

# 丢旧网格，留骨架 + 旧动作
for o in [o for o in scene.objects if o.type == "MESH"]:
    bpy.data.objects.remove(o, do_unlink=True)
for me in list(bpy.data.meshes):
    if me.users == 0:
        bpy.data.meshes.remove(me)
for a in bpy.data.actions:
    a.use_fake_user = True

for pb in arm.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()

u = U.build(DETAIL)
objs = u.finish(prefix="unit", verbose=True)
u.bind(arm, objs)

# ── 动作：五条旧动作微手术 + hurt/death 重做 ───────────────────────────────
made = AN.build(arm)

# ── 体检 ────────────────────────────────────────────────────────────────────
print("[tris]", K.stats(objs))
mn = Vector((1e9,) * 3)
mx = Vector((-1e9,) * 3)
for o in objs:
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
print("[bbox] min", tuple(round(v, 3) for v in mn), "max", tuple(round(v, 3) for v in mx))
print("[objects]", [(o.name, len(o.data.polygons)) for o in objs])
print("[materials]", sorted(m.name for m in bpy.data.materials if m.users))
print("[bones]", len(arm.data.bones), [b.name for b in arm.data.bones])

rm = RigMesh(arm, objs)
arm.animation_data_create()
order = ["idle", "idle_b", "walk", "shoot", "reload", "hurt", "death"]
for name in order:
    act = bpy.data.actions.get(name)
    if act is None:
        print("[anim] MISSING", name)
        continue
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(v) for v in act.frame_range)
    zmin, zbone = 1e9, ""
    hit = {"R": 0, "L": 0, "Rbolt": 0, "Lbolt": 0}
    worst_f = None
    p0 = p1 = None
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        z, zn = rm.zmin()
        if z < zmin:
            zmin, zbone = z, zn
        for k, (h, t) in (("R", ("hand_R", "weapon")), ("L", ("hand_L", "weapon")),
                          ("Rbolt", ("hand_R", "prop_bolt")),
                          ("Lbolt", ("hand_L", "prop_bolt"))):
            n = rm.hits(h, t)
            if n:
                hit[k] += 1
                if worst_f is None:
                    worst_f = f
        if f == f0:
            p0 = [pb.matrix.copy() for pb in arm.pose.bones]
        if f == f1:
            p1 = [pb.matrix.copy() for pb in arm.pose.bones]
    d = 0.0
    for a, b in zip(p0, p1):
        for r in range(4):
            for c in range(4):
                d = max(d, abs(a[r][c] - b[r][c]))
    print("[qc] %-7s f%3d..%-3d %5.2fs  zmin=%+.4f(%s)  穿透帧 R%d L%d boltR%d boltL%d  loop_d=%.1e"
          % (name, f0, f1, (f1 - f0) / 30.0, zmin, zbone,
             hit["R"], hit["L"], hit["Rbolt"], hit["Lbolt"], d))

arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
scene.frame_set(0)
bpy.context.view_layer.update()

# ── 导出（参数与旧版逐字一致）──────────────────────────────────────────────
os.makedirs(ASSET, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
for o in [root_empty, arm] + objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=False,
    export_yup=True,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_skins=True,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_nla_strips=False,
    export_bake_animation=False,
    export_force_sampling=True,
    export_anim_slide_to_zero=True,
    export_optimize_animation_size=False,
    export_anim_single_armature=True,
)
print("[done]", OUT, os.path.getsize(OUT) // 1024, "KB")
