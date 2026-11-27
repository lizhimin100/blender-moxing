"""run_弩兵_v4.py —— 弩兵：**不动几何**地修掉"握弩的手穿模"，重做 hurt/death

为什么不用 `run_弩兵.py`：那条路会从 `unit_弩兵.py` **重建整张网格**。源码已经比出厂
资产新（出厂 4,508 面，源码 detail=0 是 7,206、detail=1 是 8,966），一跑就等于换了个模型 ——
用户明确要求过"不要重做模型"。所以这里改成**在原网格上做两处顶点平移**（实现在 `unit_弩兵.fix_grip_clearance()`）：

1. 两只手的方块顶点下移 26 mm —— 拳顶落到弩身底面下方 ~7 mm，从"弩身穿拳"变成"托住"；
2. `weapon` / `prop_bolt` 的顶点上移 55 mm —— 弩（含矢）整体上移。

结果：静止姿态与全部七条动作里 `hand_* × weapon` 的面片相交对数都是 0；
三角面数一个都不变（仍是 3 网格 / 4,508 面 / 24 骨）。

用法：
  blender -b --factory-startup --python 联盟/弩兵/run_弩兵_v4.py
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

SRC = os.path.join(LIB, "_ref", "联盟", "方块人_弩兵.glb")
ASSET = os.path.join(os.path.dirname(ROOT), "assets", "单位", "联盟", "弩兵")
OUT = os.path.join(ASSET, "方块人_弩兵.glb")

# 手/弩的位移量不在这里——见 `unit_弩兵.GRIP_HAND_DZ / GRIP_WEAPON_DZ`
# （拳顶落在弩身底面下方 ~7 mm，扫描过程见 docs/_tmp/cb2_tune.py）

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0

# ══ ①② 加载旧 glb + 手/弩顶点各平移一点点 ═══════════════════════════════════
# 位移量和实现都在 `unit_弩兵.fix_grip_clearance()` 里（load() 会调用），
# 这样体检脚本（pose_check / unit_shot）和这条出货脚本量的是同一份几何。
import unit_弩兵 as U_MOD  # noqa: E402

root, arm, meshes = U_MOD.load()
for a in bpy.data.actions:
    a.use_fake_user = True
print("[load]", os.path.basename(SRC), "meshes", [o.name for o in meshes],
      "tris", sum(len(m.data.loop_triangles) for m in meshes))


# ══ ③ 手 ↔ 弩 穿透复测（BVH 互查）══════════════════════════════════════════
def group_faces(ob, names):
    idx = {g.index for g in ob.vertex_groups if g.name in names}
    out = []
    for poly in ob.data.polygons:
        for vi in poly.vertices:
            v = ob.data.vertices[vi]
            if v.groups:
                best = max(v.groups, key=lambda x: x.weight)
                if best.group in idx:
                    out.append(tuple(poly.vertices))
                    break
    return out


from mathutils.bvhtree import BVHTree  # noqa: E402

# 注意：改骨的 rest 只影响"求值后"的网格，`ob.data.vertices` 是绑定姿态坐标，
# 所以互查必须用 evaluated mesh，否则永远量到旧位置。
bpy.context.view_layer.update()
_dg = bpy.context.evaluated_depsgraph_get()
for ob in meshes:
    hf = group_faces(ob, ("hand_L", "hand_R"))
    wf = group_faces(ob, ("weapon", "prop_bolt"))
    if not hf or not wf:
        continue
    oe = ob.evaluated_get(_dg)
    me = oe.to_mesh()
    vs = [oe.matrix_world @ v.co for v in me.vertices]
    oe.to_mesh_clear()
    th = BVHTree.FromPolygons(vs, hf, all_triangles=False, epsilon=0.0)
    tw = BVHTree.FromPolygons(vs, wf, all_triangles=False, epsilon=0.0)
    ov = th.overlap(tw)
    print("[bvh] %-10s 手面 %d / 弩面 %d → 相交 %d 对" % (ob.name, len(hf), len(wf), len(ov)))


# ══ ④ 动作：旧五条微手术 + hurt/death 重做 ═════════════════════════════════
import anims_弩兵 as AN  # noqa: E402

made = AN.build(arm)
print("[anim]", [m[0] for m in made])

# ══ ⑤ 体检 ═════════════════════════════════════════════════════════════════
arm.animation_data_create()
order = ["idle", "idle_b", "walk", "shoot", "reload", "hurt", "death"]
for name in order:
    act = bpy.data.actions.get(name)
    if act is None:
        print("[qc] MISSING", name)
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
    print("[qc] %-7s f%3d..%-3d %5.2fs  zmin=%+.4f  loop_d=%.1e"
          % (name, f0, f1, (f1 - f0) / 30.0, zmin, d))

arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
scene.frame_set(0)
bpy.context.view_layer.update()

# ══ ⑥ 导出（参数与旧版逐字一致）═══════════════════════════════════════════
os.makedirs(ASSET, exist_ok=True)
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
