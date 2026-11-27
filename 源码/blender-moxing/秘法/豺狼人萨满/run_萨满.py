"""run_萨满.py —— 建野怪·豺狼人萨满：几何 → 骨架 → 蒙皮 → 多形态导出

用法：
  blender -b --factory-startup --python 秘法/豺狼人萨满/run_萨满.py

产物（assets/单位/野怪/豺狼人/豺狼人萨满/）：
  豺狼人萨满.glb        全量（身体 + 头 + 巫杖 + 电弧 + 骨架 + 5 条动作）
  豺狼人萨满_低模.glb    低模档（关倒角，cage 原样）
  豺狼人萨满_巫杖.glb    只道具（自带 weapon_R / fx_ball / fx_arc 三根骨）
  组件清单.json         每个零件的模块 / 骨 / 材质 / 面数
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
import unit_萨满 as U  # noqa: E402

for _m in ("unitkit2", "unit_萨满", "anims_萨满"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import unitkit2 as K  # noqa: E402
import unit_萨满 as U  # noqa: E402

HAS_ANIM = True
try:
    import anims_萨满 as A  # noqa: E402
except Exception as _e:
    print("[warn] no anims:", _e)
    A = None
    HAS_ANIM = False

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
KEY = U.NAME
OUT = os.path.join(os.path.dirname(ROOT), "assets", "单位", "野怪", "豺狼人", KEY)
QCD = HERE
os.makedirs(QCD, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.frame_start = 0
scene.frame_end = 140


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


def export(path, objs, extra=(), anim=True):
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
        export_animations=(anim and A is not None), export_animation_mode="ACTIONS",
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
    objs = u.finish(prefix=U.PREFIX, join_by="module", verbose=True)
    global MANIFEST
    MANIFEST = u.meta
    root = bpy.data.objects.new(KEY, None)
    root.empty_display_size = 0.2
    scene.collection.objects.link(root)
    arm = U.build_rig()
    arm.parent = root
    u.bind(arm, objs)
    u.root = root
    if anim and A is not None:
        names = A.build_all(arm)
        print("[anim count]", len(names), names)
    return u, arm, objs


def audit_anims(objs, arm):
    if A is None:
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
        print("[anim] %-8s %5.2fs  f%3d..%3d  zmin=%+.4f  loop_d=%.2e"
              % (act.name, (f1 - f0) / 30.0, f0, f1, zmin, d))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    scene.frame_set(0)


# ── ① 全量 ──────────────────────────────────────────────────────────────────
u, arm, objs = build_unit(low=False)
tris, mn, mx = stats(objs)
print("[tris]", tris, "bbox", tuple(round(v, 3) for v in mn), tuple(round(v, 3) for v in mx))
print("[size] %.3f x %.3f x %.3f" % tuple(mx[i] - mn[i] for i in range(3)))
print("[objects]", [(o.name, len(o.data.polygons)) for o in objs])
print("[materials]", sorted({m.name for o in objs for m in o.data.materials if m}))
print("[bones]", len(arm.data.bones), [b.name for b in arm.data.bones])
print("[zmin] %.4f  [zmax] %.4f" % (mn.z, mx.z))
soft = sum(1 for p in u.parts if p["sub"] > 0)
print("[parts] %d  soft %d (%.1f%%)" % (len(u.parts), soft, 100.0 * soft / len(u.parts)))
print(U.report())
audit_anims(objs, arm)

man = [dict(r) for r in MANIFEST]
with open(os.path.join(QCD, "组件清单.json"), "w", encoding="utf-8") as f:
    json.dump({"asset": KEY, "modules": list(U.MODULES),
               "bones": [b[0] for b in U.BONES], "parts": man},
              f, ensure_ascii=False, indent=1)
print("[parts by module]", {m: sum(1 for p in man if p["module"] == m) for m in U.MODULES})
print("[mat use]", {k: sum(1 for p in man if p["material"] == k) for k in U.MATS})

export(os.path.join(OUT, KEY + ".glb"), objs, extra=[u.root, arm])

# ── ② 低模档 ────────────────────────────────────────────────────────────────
u2, arm2, objs2 = build_unit(low=True)
t2, mn2, mx2 = stats(objs2)
print("[low tris]", t2, "bbox", tuple(round(v, 3) for v in mn2),
      tuple(round(v, 3) for v in mx2))
print("[low zmin] %.4f" % mn2.z)
export(os.path.join(OUT, KEY + "_低模.glb"), objs2, extra=[u2.root, arm2])

# ── ③ 只巫杖（自带 weapon_R / fx_ball / fx_arc）──────────────────────────────
clear()
u4 = U.build(modules=["staff"])
objs4 = u4.finish(prefix=U.PREFIX + "_staff", join_by="module", verbose=False)
PROP_BONES = [("weapon_R", tuple(U.GRIP), tuple(U.GRIP + Vector((0, 0, 0.30))), None),
              ("fx_ball", tuple(U.ORB_C), tuple(U.ORB_C + Vector((0, 0, 0.08))), "weapon_R"),
              ("fx_arc", tuple(U.ORB_C), tuple(U.ORB_C + Vector((0, 0, 0.07))), "weapon_R")]
arm4 = K.build_rig(PROP_BONES, "RIG_%s_weapon" % KEY)
u4.bind(arm4, objs4)
t4, mn4, mx4 = stats(objs4)
print("[staff tris]", t4, "zmin %.4f" % mn4.z, "h %.3f" % (mx4.z - mn4.z))
export(os.path.join(OUT, KEY + "_巫杖.glb"), objs4, extra=[arm4], anim=False)

print("[done]", KEY)
