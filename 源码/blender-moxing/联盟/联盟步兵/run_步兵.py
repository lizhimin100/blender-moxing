"""run_步兵.py —— 联盟步兵 v3：给旧模型换 12 条动作，几何不动

用法：
  blender -b --factory-startup --python 联盟/联盟步兵/run_步兵.py

读 `库/_ref/联盟/方块人_联盟步兵.glb`（原封不动的旧资产），把动作全部重写，
覆盖导出到 `assets/单位/联盟/联盟步兵/方块人_联盟步兵.glb`。
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
for _p in (LIB, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0

import unit_步兵 as U          # noqa: E402
import anims_步兵 as AN        # noqa: E402

root, arm, meshes = U.load()
print("[load]", U.SRC, "meshes", [o.name for o in meshes], "bones", len(arm.data.bones))
missing = [b for b in U.BONES_OK if b not in arm.data.bones]
print("[bones] ok" if not missing else "[bones] MISSING %s" % missing)

# ── 动作 ────────────────────────────────────────────────────────────────────
names = AN.build_all(arm)
print("[anim count]", len(names))

# ── 体检 ────────────────────────────────────────────────────────────────────
arm.animation_data_create()
for act in sorted(bpy.data.actions, key=lambda a: a.name):
    if act.name not in names:
        continue
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
        for ob in meshes:
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
    print("[anim] %-13s %5.2fs f%3d..%3d  zmin=%+.4f  loop_d=%.2e"
          % (act.name, (f1 - f0) / 30.0, f0, f1, zmin, d))

arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
scene.frame_set(0)
bpy.context.view_layer.update()

# ── 导出（覆盖旧资产）──────────────────────────────────────────────────────
os.makedirs(U.ASSET, exist_ok=True)
OUT = os.path.join(U.ASSET, "方块人_联盟步兵.glb")
bpy.ops.object.select_all(action="DESELECT")
for o in [root, arm] + meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(
    filepath=OUT, export_format="GLB", use_selection=True,
    export_apply=False, export_yup=True, export_texcoords=True,
    export_normals=True, export_materials="EXPORT",
    export_image_format="AUTO", export_skins=True,
    export_animations=True, export_animation_mode="ACTIONS",
    export_nla_strips=False, export_bake_animation=False,
    export_force_sampling=True, export_anim_slide_to_zero=True,
    export_optimize_animation_size=False, export_anim_single_armature=True,
)
print("[done]", OUT, os.path.getsize(OUT) // 1024, "KB")
