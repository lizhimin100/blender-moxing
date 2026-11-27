"""run_vox.py —— 格网单位的构建 / 自检 / 导出（一条龙）

用法：
  blender -b --factory-startup --python 库/run_vox.py -- <unit_dir> <module>

产物（assets/单位/<阵营>/<名>/）：
  <名>.glb              全量：1 mesh（3 材质槽）+ 1 骨架 + 六条动作
  <名>_手游_近.glb       近档（= 全量几何，独立可跑）
  <名>_手游_中.glb       中档：半格并整格（lod 1）
  <名>_手游_远.glb       远档：2×2×2 多数色（lod 2）
  <名>_组件清单.json     部件/骨/材质/自查表
"""
import importlib
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR = os.path.abspath(argv[0])
MOD = argv[1]

ROOT = UNIT_DIR
while not os.path.isdir(os.path.join(ROOT, "库")):
    _up = os.path.dirname(ROOT)
    if _up == ROOT:
        break
    ROOT = _up
for _p in (os.path.join(ROOT, "库"), os.path.join(ROOT, "联盟", "基准"), UNIT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import voxbase as V  # noqa: E402
import poselib2 as PL  # noqa: E402
import anims_lib as ALIB  # noqa: E402

for _m in (V.__name__, MOD, "anims_" + MOD.split("unit_")[-1]):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
U = importlib.import_module(MOD)
A = importlib.import_module("anims_" + U.NAME)

KEY = U.NAME
REL = os.path.relpath(UNIT_DIR, ROOT).replace(os.sep, "/")
OUT = os.path.join(os.path.dirname(ROOT), "assets", "单位", *REL.split("/"))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.unit_settings.system = "METRIC"


def fresh():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def assemble(g):
    ob = g.build(prefix=U.PREFIX)
    root = bpy.data.objects.new(KEY, None)
    root.empty_display_size = 0.2
    scene.collection.objects.link(root)
    arm = g.build_rig("RIG_" + KEY)
    arm.parent = root
    g.bind(arm, ob)
    bpy.context.view_layer.update()
    ALIB.set_sole(PL.Sole(arm, [ob]))
    return ob, arm, root


def lift_fix(arm, ob, acts, VB=None):
    """整段兜底：逐帧量最低点，低于地面的把 hips 抬上去（局部 Y = 世界 +Z）。

    脚有 `PL.ground()` 管，但死倒是整个人躺下去，只能整段抬。
    """
    arm.animation_data_create()
    for act in acts:
        arm.animation_data.action = act
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        f0, f1 = (int(v) for v in act.frame_range)
        dz = {}
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            z = V.body_min_z(ob, VB)
            dz[f] = max(0.0, -z)
        if max(dz.values()) < 1e-4:
            continue
        for fc in PL.fcurves(act):
            if not fc.data_path.endswith('pose.bones["hips"].location'):
                continue
            if fc.array_index != 1:
                continue
            for kp in fc.keyframe_points:
                f = int(round(kp.co[0]))
                d = dz.get(f)
                if not d:
                    continue
                kp.co[1] += d
                kp.handle_left[1] += d
                kp.handle_right[1] += d
            fc.update()
        print("[lift] %-7s max %.4f" % (act.name, max(dz.values())))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    scene.frame_set(0)


def audit_anims(arm, ob):
    """逐帧过一遍：脚底最低点 / 循环首末差 / 骨缩放。"""
    arm.animation_data_create()
    rows = []
    for act in sorted(bpy.data.actions, key=lambda a: a.name):
        arm.animation_data.action = act
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        f0, f1 = (int(v) for v in act.frame_range)
        zmin, scl_max = 1e9, 1.0
        d = 0.0
        p0 = None
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            oe = ob.evaluated_get(dg)
            me = oe.to_mesh()
            for v in me.vertices:
                zmin = min(zmin, (oe.matrix_world @ v.co).z)
            oe.to_mesh_clear()
            for pb in arm.pose.bones:
                scl_max = max(scl_max, max(pb.scale))
            if f == f0:
                p0 = [pb.matrix.copy() for pb in arm.pose.bones]
            if f == f1 and act.name in ("idle", "walk"):
                p1 = [pb.matrix.copy() for pb in arm.pose.bones]
                for a, b in zip(p0, p1):
                    for r in range(4):
                        for c in range(4):
                            d = max(d, abs(a[r][c] - b[r][c]))
        rows.append(dict(name=act.name, f0=f0, f1=f1, sec=round((f1 - f0) / 30.0, 2),
                         zmin=round(zmin, 4), scl=round(scl_max, 2),
                         loop_d=round(d, 6) if act.name in ("idle", "walk") else None))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    scene.frame_set(0)
    return rows


# ── ① 全量 ──────────────────────────────────────────────────────────────────
fresh()
g = U.build()
g.report()
ob, arm, root = assemble(g)
anims = A.build_all(arm)
VB = V.vert_bone(ob)
lift_fix(arm, ob, [bpy.data.actions[n] for n in anims], VB)
rows = audit_anims(arm, ob)

ob.data.calc_loop_triangles()
tris = len(ob.data.loop_triangles)
zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
print("[tris]", tris, " zmin %.4f  zmax %.4f" % (min(zs), max(zs)))
print("[materials]", [m.name for m in ob.data.materials])
print("[bones]", len(arm.data.bones))
for r in rows:
    print("[anim] %-7s %4.2fs f%3d..%-3d zmin=%+.4f scl=%.2f loop_d=%s"
          % (r["name"], r["sec"], r["f0"], r["f1"], r["zmin"], r["scl"],
             r["loop_d"] if r["loop_d"] is not None else "-"))

man = dict(asset=KEY, base=getattr(U, "BASE", ""), diff=list(getattr(U, "DIFF", ())),
           tris=tris, bones=[b.name for b in arm.data.bones],
           materials=[m.name for m in ob.data.materials],
           audit=g.audit(), anims=rows, team_ratio=round(g.team_ratio(), 4),
           parts=[dict(name=p, bone=g.parts[p].bone, cells=len(g.parts[p].cells),
                       extras=len(g.parts[p].extras), soft=g.parts[p].soft,
                       big=g.parts[p].big) for p in g.order])
os.makedirs(os.path.join(UNIT_DIR), exist_ok=True)
with open(os.path.join(UNIT_DIR, "组件清单.json"), "w", encoding="utf-8") as f:
    json.dump(man, f, ensure_ascii=False, indent=1)

V.export_glb(os.path.join(OUT, KEY + ".glb"), [ob], extra=[root, arm])

# ── ② 三档 LOD（从格子降采样重建绑定，绝不 decimate）────────────────────────
for lv, tag in ((1, "近"), (2, "中"), (3, "远")):
    fresh()
    gl = g.lod(level=min(lv - 1, 2)) if lv > 1 else g
    ob2, arm2, root2 = assemble(gl)
    A.build_all(arm2)
    VB2 = V.vert_bone(ob2)
    lift_fix(arm2, ob2, [bpy.data.actions[n] for n in anims], VB2)
    ob2.data.calc_loop_triangles()
    t2 = len(ob2.data.loop_triangles)
    V.export_glb(os.path.join(OUT, "%s_手游_%s.glb" % (KEY, tag)), [ob2],
                 extra=[root2, arm2])
    print("[lod %s] tris %d" % (tag, t2))

print("[done]", KEY, "->", OUT)
