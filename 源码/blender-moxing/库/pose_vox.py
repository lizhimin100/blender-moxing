"""pose_vox.py —— 格网单位的动作体检 + 接触表出图（格网档专用）

和精模档的 `pose_check.py` 分工相同，但走的是 `voxbase.Grid` 这条路
（`Grid.build()` / `bind()` / `PL.Sole`），并且多三样格网档才需要的量：

  ① **按骨分组的最低点** —— 死倒时"最低点"几乎总是掉在地上的武器；
     要先把它和身体分开看，否则永远发现不了"人还悬在半空"。
  ② **双手握杆 / 箭贴弓** —— 长枪兵左掌到枪轴的距离、弓箭手的箭轴与弓腹夹角。
     这两个是"动作像不像"的硬指标，靠眼睛只能说"有点怪"。
  ③ **接触表** —— 一条动作抽 N 帧、按固定机位渲成小图，再拼成一张。
     看节奏和重心，比看单帧准；看穿模，比看单帧差（所以两样都留着）。

用法：

    blender -b --factory-startup --python 库/pose_vox.py -- \
        联盟/弓箭手 unit_弓箭手 [--only attack] [--step 2] \
        [--sheet attack:0,6,12,18,24,30,36,42,48,54] [--cams iso,side] \
        [--res 420] [--out docs/_tmp/sheet] [--nolift]

口径：
  * `--nolift` 关掉 `run_vox.lift_fix` 那道兜底，看"原始姿态"；
    默认开启 = 看出货那一份（和 glb 一致）。
  * `zmin` 是全身最低点；`zbody` 是**去掉武器/箭筒/披风**之后的最低点。
    死倒判定看 `zbody`，不看 `zmin`。
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def flag(name, default=None):
    if name in argv:
        i = argv.index(name) + 1
        return argv[i] if i < len(argv) else True
    return default


UNIT_DIR = os.path.abspath(argv[0])
UMOD = argv[1]
ONLY = [s for s in str(flag("--only", "")).split(",") if s]
STEP = int(flag("--step", 2))
SHEET = flag("--sheet", "")
CAMS = [s for s in str(flag("--cams", "iso,side")).split(",") if s]
OUT = os.path.abspath(flag("--out", os.path.join(os.path.dirname(UNIT_DIR), "..", "docs", "_tmp", "sheet")))
RES = int(flag("--res", 420))
NOLIFT = "--nolift" in argv
MAXF = int(flag("--max", 40))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, UNIT_DIR, os.path.join(ROOT, "联盟", "基准")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30

for _m in ("voxbase", "poselib2", "anims_lib", "clip_lib", UMOD, "unit_基准"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

import voxbase as V          # noqa: E402
import poselib2 as PL        # noqa: E402
import anims_lib as ALIB     # noqa: E402
import unit_基准 as BASE     # noqa: E402
import clip_lib as CL        # noqa: E402

U = importlib.import_module(UMOD)
A = importlib.import_module("anims_" + U.NAME)

# ── 建单位 ──────────────────────────────────────────────────────────────────
g = U.build()
g.report()
ob = g.build(prefix=U.PREFIX)
arm = g.build_rig("RIG_" + U.NAME)
g.bind(arm, ob)
bpy.context.view_layer.update()
ALIB.set_sole(PL.Sole(arm, [ob]))
names = A.build_all(arm)
print("[unit]", U.NAME, "tris", sum(p.tri_est() for p in g.parts.values()),
      "bones", len(arm.data.bones), "actions", names)


# ── lift_fix（和 run_vox 同一份逻辑，只在体检时可选）────────────────────────
def lift_fix(acts, VB=None):
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


VB = V.vert_bone(ob)
acts = [bpy.data.actions[n] for n in names]
if not NOLIFT:
    lift_fix(acts, VB)

# ── 体检 ────────────────────────────────────────────────────────────────────
PAIRS = CL.pairs_for("all")
WATCH = CL.Watch([ob])
BODY_ONLY = set(CL.BODY)


def per_bone_zmin(geo):
    out = {}
    for k, (vs, _t) in geo.items():
        if vs:
            out[k] = min(v.z for v in vs)
    return out


def bone_axis(bone):
    """骨的世界点 + 世界 +Y 轴（armature 在原点、无旋转，所以 matrix 就是世界）。"""
    pb = arm.pose.bones.get(bone)
    if pb is None:
        return None, None
    M = pb.matrix
    return M.translation.copy(), Vector(M.col[1].xyz).normalized()


def point_line_dist(p, o, d):
    v = Vector(p) - Vector(o)
    return (v - Vector(d) * v.dot(d)).length


def geom_metrics(geo):
    """几组"动作像不像"的量。缺骨就跳过。"""
    m = {}
    # ① 左掌心到枪轴（weapon_R 的 +Y 直线）的距离 —— 双手持枪的硬指标
    hv = geo.get("hand_L", ([], []))[0]
    o, d = bone_axis("weapon_R")
    if hv and o is not None:
        c = sum(hv, Vector()) / len(hv)
        m["hand_shaft"] = point_line_dist(c, o, d)
    # ② 箭轴与"箭尾→弓握把"的夹角：撒放前应当 < 8°
    o2, a2 = bone_axis("weapon_R")
    o3, _ = bone_axis("weapon_L")
    if o2 is not None and o3 is not None:
        line = (o3 - o2)
        if line.length > 1e-4 and a2 is not None:
            m["wr_wl"] = math.degrees(a2.angle(line.normalized()))
    return m


def bone_world(b):
    pb = arm.pose.bones.get(b)
    return pb.matrix.translation.copy() if pb else None


rows = []
for nm in names:
    if ONLY and nm not in ONLY:
        continue
    act = bpy.data.actions[nm]
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(round(v)) for v in act.frame_range)
    n = max(f1 - f0, 1)
    idx = list(range(f0, f1 + 1, STEP))
    if len(idx) > MAXF:
        idx = sorted({int(f0 + round(n * i / (MAXF - 1.0))) for i in range(MAXF)})
    worst, zlo, zbody = {}, 1e9, 1e9
    zbody_at = (0, "")
    boot = {"R": [], "L": []}
    hips_z = []
    prev, slide = {}, 0.0
    p0 = p1 = None
    ms = {"hand_shaft": 0.0, "wr_wl": 0.0}
    for f in idx:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        geo = WATCH.geo(bpy.context.evaluated_depsgraph_get())
        bz = per_bone_zmin(geo)
        zz, bb = WATCH.zmin_tag(geo)
        if zz < zlo:
            zlo = zz
        zb = V.body_min_z(ob, VB)
        if zb < zbody:
            zbody, zbody_at = zb, (f, "body@%d" % f)
        for s in ("R", "L"):
            ft = WATCH.foot(geo, s)
            if ft:
                boot[s].append((ft[1].y, ft[0], ft[1].x))
        hz = bone_world("hips")
        if hz:
            hips_z.append(hz.z)
        for k, v in WATCH.clip(geo, PAIRS).items():
            worst[k] = max(worst.get(k, 0), v)
        for s in ("R", "L"):
            ft = WATCH.foot(geo, s)
            if ft is None:
                continue
            z, c = ft
            if z < 0.022 and s in prev and prev[s][0] < 0.022:
                slide += (Vector((c.x, c.y)) - Vector((prev[s][1], prev[s][2]))).length
            prev[s] = (z, c.x, c.y)
        for k, v in geom_metrics(geo).items():
            if k in ms:
                ms[k] = max(ms[k], v)
        if f == f0:
            p0 = [pb.matrix.copy() for pb in arm.pose.bones]
        if f == f1:
            p1 = [pb.matrix.copy() for pb in arm.pose.bones]
    soft = {k: v for k, v in worst.items() if tuple(k.split("×")) in CL.SOFT}
    worst = {k: v for k, v in worst.items() if tuple(k.split("×")) not in CL.SOFT}
    if soft:
        worst.update({"(" + k + ")": v for k, v in soft.items() if v > 150})
    loop = 0.0
    if p0 and p1:
        for a, b in zip(p0, p1):
            for r in range(4):
                for c in range(4):
                    loop = max(loop, abs(a[r][c] - b[r][c]))
    stride = max((b[0] for b in boot["R"]), default=0) - min((b[0] for b in boot["R"]), default=0)
    lift = max((b[1] for b in boot["R"] + boot["L"]), default=0) - min(
        (b[1] for b in boot["R"] + boot["L"]), default=0)
    bounce = (max(hips_z) - min(hips_z)) if hips_z else 0.0
    r = dict(name=nm, f=(f0, f1), worst=worst, zmin=zlo, zbody=zbody,
             zbody_at=zbody_at, slide=slide, loop=loop, stride=stride, lift=lift,
             bounce=bounce, **ms)
    rows.append(r)
    ok = (not worst) and zlo > -0.002
    print("%s%-8s f%3d..%-3d zmin=%+.4f zbody=%+.4f@f%d(%s) stride=%.2f lift=%.2f "
          "bounce=%.3f slide=%.2f loop=%.1e shafts=%s %s"
          % ("OK " if ok else "!! ", nm, f0, f1, zlo, zbody, zbody_at[0], zbody_at[1],
             stride, lift, bounce, slide, loop,
             ("%.3f/%.0f°" % (ms["hand_shaft"], ms["wr_wl"]))
             if (ms["hand_shaft"] or ms["wr_wl"]) else "-",
             ("CLIP " + str(worst)) if worst else ""))

print("[pose_vox] %d actions" % len(rows))
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis.identity()
scene.frame_set(0)


PROBE = flag("--probe", "")
if PROBE:
    act = bpy.data.actions[PROBE]
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    f0, f1 = (int(round(v)) for v in act.frame_range)
    for f in range(f0, f1 + 1, 2):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        geo = WATCH.geo(bpy.context.evaluated_depsgraph_get())
        bz = per_bone_zmin(geo)
        m = geom_metrics(geo)
        w = WATCH.clip(geo, [("weapon_R", "chest"), ("weapon_R", "head"), ("weapon_R", "hips"),
                            ("hand_L", "chest"), ("hand_L", "head"), ("weapon_L", "chest")])
        print("[f%03d] zmin=%+.3f(%s) shaft=%s wr-chest=%s"
              % (f, min(bz.values()) if bz else 0, min(bz, key=bz.get) if bz else "-",
                 ("%.3f" % m.get("hand_shaft", -1)) if "hand_shaft" in m else "-",
                 w or "-"))
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()


# ── 接触表出图 ──────────────────────────────────────────────────────────────
if SHEET:
    act_name, fr = SHEET.split(":")
    frames = [int(x) for x in fr.split(",") if x.strip() != ""]
    os.makedirs(OUT, exist_ok=True)

    g.bake_preview(ob)
    V.outline(ob, 0.010, arm=arm)
    bpy.context.view_layer.update()

    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = scene.render.resolution_y = RES
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.eevee.taa_render_samples = 16
    except Exception:
        pass

    world = bpy.data.worlds.new("W")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    bgn = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    tex = nt.nodes.new("ShaderNodeTexGradient")
    mp = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.085, 0.095, 0.110, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.42, 0.47, 0.54, 1)
    mp.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bgn.inputs["Color"])
    bgn.inputs["Strength"].default_value = 0.9
    nt.links.new(bgn.outputs["Background"], wout.inputs["Surface"])

    def add_light(name, loc, energy, size, color, aim=(0, 0, 0.95)):
        d = bpy.data.lights.new(name, "AREA")
        d.energy = energy
        d.size = size
        d.color = color
        o = bpy.data.objects.new(name, d)
        scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    add_light("key", (-2.6, 3.2, 3.6), 700, 3.0, (1.0, 0.96, 0.90))
    add_light("fill", (3.4, 1.8, 1.9), 240, 3.6, (0.80, 0.88, 1.0))
    add_light("rim", (0.8, -3.6, 2.6), 520, 2.4, (1.0, 0.90, 0.80))

    bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, -0.004))
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.13, 0.12, 1)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.94
    bpy.context.object.data.materials.append(gm)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    H = 2.35 if g.parts and any(p.big for p in g.parts.values()) else 1.85

    def shoot(tag, azim, elev, scale):
        t = Vector((0, 0.06, H * 0.46))
        a, e = math.radians(azim), math.radians(elev)
        cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                                   math.sin(e))) * 9.0
        cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam_data.ortho_scale = scale
        scene.render.filepath = os.path.join(OUT, tag + ".png")
        bpy.ops.render.render(write_still=True)

    view = {"iso": (218, 18, H * 1.10), "side": (90, 4, H * 1.05),
            "front": (180, 3, H * 1.05), "rts": (218, 38, H * 1.30),
            "back": (0, 6, H * 1.05)}
    A.pose_at(arm, act_name, frames[0] if frames else 0)
    for fr_ in frames:
        A.pose_at(arm, act_name, fr_)
        bpy.context.view_layer.update()
        for c in CAMS:
            az, el, sc = view.get(c, view["iso"])
            shoot("%s_%s_f%03d_%s" % (U.KEY if hasattr(U, "KEY") else U.NAME, act_name, fr_, c),
                  az, el, sc)
    print("[sheet]", OUT, len(frames), "frames")
print("[pose_vox done]")
