"""run_农民.py —— 联盟农民 v4：换 6 条动作 + 加肩上金袋，几何不动

用法：
  blender -b --factory-startup --python 联盟/农民/run_农民.py

读 `库/_ref/联盟/方块人_农民.glb`（原封不动的旧资产），
覆盖导出 `assets/单位/联盟/农民/方块人_农民.glb`，
另外单独导出 `assets/单位/联盟/农民/农民_金袋.glb`（只有金袋网格 + 一根 sack 骨）。
"""
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

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

import unit_农民 as U          # noqa: E402
import anims_农民 as AN        # noqa: E402

root, arm, meshes = U.load()
body = [o for o in meshes if o.name != "unit_sack"]
sack = next(o for o in meshes if o.name == "unit_sack")
print("[load]", U.SRC)
print("[meshes]", [(o.name, len(o.data.vertices)) for o in meshes])
print("[bones]", len(arm.data.bones), [b.name for b in arm.data.bones])
missing = [b for b in U.BONES_OK if b not in arm.data.bones]
print("[bones] ok" if not missing else "[bones] MISSING %s" % missing)

# ── 动作 ────────────────────────────────────────────────────────────────────
names = AN.build_all(arm)
print("[anim count] rebuilt", len(names))

# 保留的 3 条旧动作：只补 sack 骨的 scale=0.001 两个关键帧
kept = [a for a in bpy.data.actions if a.name in AN.KEEP]
print("[keep]", [(a.name, tuple(int(v) for v in a.frame_range)) for a in kept])
for a in kept:
    AN.mute_sack(arm, a)

# ── 体检 ────────────────────────────────────────────────────────────────────
arm.animation_data_create()


def eval_bvh(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for ob in objs:
        oe = ob.evaluated_get(dg)
        me = oe.to_mesh()
        vs = [oe.matrix_world @ v.co for v in me.vertices]
        ps = [tuple(p.vertices) for p in me.polygons]
        trees.append(BVHTree.FromPolygons(vs, ps, all_triangles=False, epsilon=0.0))
        oe.to_mesh_clear()
    return trees


for act in sorted(bpy.data.actions, key=lambda a: a.name):
    if act.name not in names and act.name not in AN.KEEP:
        continue
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(v) for v in act.frame_range)
    zmin = 1e9
    zmin_which = ""
    p0 = p1 = None
    hit = 0
    hit_frames = []
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        for ob in meshes:
            oe = ob.evaluated_get(dg)
            me = oe.to_mesh()
            for v in me.vertices:
                z = (oe.matrix_world @ v.co).z
                if z < zmin:
                    zmin = z
                    zmin_which = ob.name
            oe.to_mesh_clear()
        if f == f0:
            p0 = [pb.matrix.copy() for pb in arm.pose.bones]
        if f == f1:
            p1 = [pb.matrix.copy() for pb in arm.pose.bones]
        # 袋子 vs 身体：只在袋子看得见的时候查
        if act.name == "carry_gold":
            ts = eval_bvh([sack])
            n = 0
            for ob in body:
                tb = eval_bvh([ob])[0]
                n += len(ts[0].overlap(tb))
            if n:
                hit += n
                hit_frames.append((f, n))
    d = 0.0
    for a, b in zip(p0, p1):
        for r in range(4):
            for c in range(4):
                d = max(d, abs(a[r][c] - b[r][c]))
    extra = ""
    if act.name == "carry_gold":
        extra = "  sackXbody=%d%s" % (hit, hit_frames[:4])
    print("[anim] %-13s %5.2fs f%3d..%3d  zmin=%+.4f (%s)  loop_d=%.2e%s"
          % (act.name, (f1 - f0) / 30.0, f0, f1, zmin, zmin_which, d, extra))

arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
    pb.scale = (1.0, 1.0, 1.0)
    pb.location = (0.0, 0.0, 0.0)
    pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
scene.frame_set(0)
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
    pb.scale = (1.0, 1.0, 1.0)
bpy.context.view_layer.update()
print("[pre-export] sack scale", tuple(round(v, 4) for v in arm.pose.bones["sack"].scale))

# ── 导出（覆盖旧资产）──────────────────────────────────────────────────────
os.makedirs(U.ASSET, exist_ok=True)
OUT = os.path.join(U.ASSET, "方块人_农民.glb")
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

# ── 单独导出金袋（袋子网格 + 一根同名 sack 骨）──────────────────────────────
arm2 = arm.copy()
arm2.data = arm.data.copy()
scene.collection.objects.link(arm2)
for c in list(arm2.children):
    pass
bpy.ops.object.select_all(action="DESELECT")
arm2.select_set(True)
bpy.context.view_layer.objects.active = arm2
bpy.ops.object.mode_set(mode="EDIT")
for b in list(arm2.data.edit_bones):
    if b.name != "sack":
        arm2.data.edit_bones.remove(b)
bpy.ops.object.mode_set(mode="OBJECT")

sack2 = sack.copy()
sack2.data = sack.data.copy()
sack2.name = "农民_金袋"              # 原名 unit_sack 已被主网格占用，这里用组件名
sack2.data.name = "农民_金袋"
arm2.name = "农民_金袋_arm"
arm2.data.name = "农民_金袋_arm"
scene.collection.objects.link(sack2)
sack2.parent = arm2
sack2.matrix_parent_inverse = arm2.matrix_world.inverted()
for m in sack2.modifiers:
    if m.type == "ARMATURE":
        m.object = arm2
for vg in list(sack2.vertex_groups):
    if vg.name != "sack":
        sack2.vertex_groups.remove(vg)

bpy.ops.object.select_all(action="DESELECT")
arm2.select_set(True)
sack2.select_set(True)
bpy.context.view_layer.objects.active = arm2
OUT2 = os.path.join(U.ASSET, "农民_金袋.glb")
bpy.ops.export_scene.gltf(
    filepath=OUT2, export_format="GLB", use_selection=True,
    export_apply=False, export_yup=True, export_texcoords=True,
    export_normals=True, export_materials="EXPORT",
    export_image_format="AUTO", export_skins=True,
    export_animations=False,
)
print("[done]", OUT2, os.path.getsize(OUT2) // 1024, "KB",
      "bones", [b.name for b in arm2.data.bones])
