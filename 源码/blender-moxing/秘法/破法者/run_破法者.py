"""run_破法者.py —— 建秘法·破法者：几何 → 骨架 → 蒙皮 → 动作 → 多形态导出

用法：
  blender -b --factory-startup --python 秘法/破法者/run_破法者.py -- [low] [noanim]

产物（assets/单位/联盟/破法者/）：
  破法者.glb            全量（身体+裙甲+盾+刃+特效+骨架+动作）
  破法者_低模.glb        低模档（关细分，cage 原样）
  破法者_身体.glb        只身体（换装/换武器）
  破法者_十字利刃.glb    只武器（自带 weapon_R）
  破法者_长面盾.glb      只盾（自带 shield 骨）
  qc/组件清单.json       每个零件的模块 / 骨 / 材质 / 面数
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

import unitkit2 as K  # noqa: E402
import unit_破法者 as U  # noqa: E402

for _m in ("unitkit2", "unit_破法者", "anims_破法者"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import unitkit2 as K  # noqa: E402
import unit_破法者 as U  # noqa: E402

HAS_ANIM = True
try:
    import anims_破法者 as A  # noqa: E402
except Exception as _e:
    print("[warn] no anims:", _e)
    A = None
    HAS_ANIM = False

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LOW_ARG = "low" in argv
NOANIM = "noanim" in argv or not HAS_ANIM
KEY = "破法者"
OUT = os.path.join(os.path.dirname(ROOT), "assets", "单位", "联盟", "破法者")
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
    return K.stats(objs)


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
        export_apply=False, export_yup=True, export_texcoords=False,
        export_normals=True, export_materials="EXPORT",
        export_image_format="AUTO", export_skins=True,
        export_animations=not NOANIM, export_animation_mode="ACTIONS",
        export_nla_strips=False, export_bake_animation=False,
        export_force_sampling=True, export_anim_slide_to_zero=True,
        export_optimize_animation_size=False, export_anim_single_armature=True,
        export_def_bones=False, export_morph=False,
    )
    bpy.ops.object.select_all(action="DESELECT")
    print("[out]", os.path.basename(path), os.path.getsize(path) // 1024, "KB")
    return os.path.getsize(path)


MANIFEST = []


def build_unit(low=False, modules=None, anim=True):
    clear()
    u = U.build(low=low, modules=modules)
    objs = u.finish(prefix=U.PREFIX, join_by="module")
    global MANIFEST
    MANIFEST = u.meta
    root = bpy.data.objects.new(KEY, None)
    root.empty_display_size = 0.2
    scene.collection.objects.link(root)
    arm = U.build_rig()
    arm.parent = root
    u.bind(arm, objs)
    u.root = root
    if anim and not NOANIM:
        names = A.build_all(arm)
        print("[anim count]", len(names), names)
    return u, arm, objs


# ── ① 全量 ──────────────────────────────────────────────────────────────────
u, arm, objs = build_unit(low=False)
tris, mn, mx = stats(objs)
print("[tris]", tris, "bbox", tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx))
print("[size] %.3f x %.3f x %.3f" % tuple(mx[i] - mn[i] for i in range(3)))
print("[objects]", [(o.name, len(o.data.polygons)) for o in objs])
print("[materials]", sorted({m.name for o in objs for m in o.data.materials if m}))
print("[bones]", len(arm.data.bones))
print(U.report())

man = [dict(r) for r in MANIFEST]
with open(os.path.join(QCD, "组件清单.json"), "w", encoding="utf-8") as f:
    json.dump({"asset": KEY, "modules": list(U.MODULES),
               "bones": [b[0] for b in U.BONES], "parts": man},
              f, ensure_ascii=False, indent=1)
print("[parts]", len(man), {m: sum(1 for p in man if p["module"] == m) for m in U.MODULES})


def audit_anims():
    if NOANIM:
        return
    arm.animation_data_create()
    for act in sorted(bpy.data.actions, key=lambda a: a.name):
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
            for ob in objs:
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
              % (act.name, (f1 - f0) / 30.0, zmin, d))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    scene.frame_set(0)


audit_anims()
export(os.path.join(OUT, KEY + ".glb"), objs, extra=[u.root, arm])

# ── ② 低模档 ────────────────────────────────────────────────────────────────
u2, arm2, objs2 = build_unit(low=True)
t2, mn2, mx2 = stats(objs2)
print("[low tris]", t2, "bbox", tuple(round(v, 3) for v in mn2), tuple(round(v, 3) for v in mx2))
export(os.path.join(OUT, KEY + "_低模.glb"), objs2, extra=[u2.root, arm2])

# ── ③ 只身体（无盾无刃无特效）───────────────────────────────────────────────
u3, arm3, objs3 = build_unit(modules=["body", "head", "pauldron", "skirt"])
t3, _, _ = stats(objs3)
print("[body tris]", t3)
export(os.path.join(OUT, KEY + "_身体.glb"), objs3, extra=[u3.root, arm3])

# ── ④ 只武器 / 只盾 ─────────────────────────────────────────────────────────
clear()
u4 = U.build(modules=["weapon"])
wobjs = u4.finish(prefix=U.PREFIX + "w")
wroot = bpy.data.objects.new(KEY + "_武器", None)
scene.collection.objects.link(wroot)
warm = K.build_rig([("weapon_R", tuple(U.FIST_R),
                     tuple(U.FIST_R + Vector((0, 0.30, 0))), None)], "RIG_破法者_weapon")
warm.parent = wroot
u4.bind(warm, wobjs)
t4, _, _ = stats(wobjs)
print("[weapon tris]", t4)
export(os.path.join(OUT, KEY + "_十字利刃.glb"), wobjs, extra=[wroot, warm])

clear()
u5 = U.build(modules=["shield"])
sobjs = u5.finish(prefix=U.PREFIX + "s")
sroot = bpy.data.objects.new(KEY + "_盾", None)
scene.collection.objects.link(sroot)
sarm = K.build_rig([("shield", tuple(U.WRI_L), tuple(U.WRI_L + Vector((0, 0, 0.30))), None)],
                   "RIG_破法者_shield")
sarm.parent = sroot
u5.bind(sarm, sobjs)
t5, _, _ = stats(sobjs)
print("[shield tris]", t5)
export(os.path.join(OUT, KEY + "_长面盾.glb"), sobjs, extra=[sroot, sarm])

print("[done]", KEY)
