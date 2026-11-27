"""vox_studio.py —— 格网单位的影棚（建 / 摆姿势 / 出图 / 体检），一份代码两处跑

为什么要这个文件：`prev_vox.py` / `icon_vox.py` 都调 `bpy.ops.wm.read_factory_settings`，
在 Blender **图形界面**里会把 DSH 桥接插件一起重置掉（端口立刻断）。这里改成
"手动清场"（删对象 / 清动作 / 清材质），同一份代码既能被桥接 `execute_code` 直接调，
也能 `blender -b --python` 跑。

对外接口（全部返回纯数据，方便桥接里 print）：

    import vox_studio as ST
    S = ST.open(UNIT_DIR, "unit_长枪兵")      # 建 + 绑 + 六动作（可选）
    ST.studio(res=760)                        # 灯光 / 世界 / 地面 / 相机
    ST.shoot("front", OUT, azim=180, elev=2)  # 单张
    ST.still(S, OUT, "walk", 8, azim=218)     # 摆到某动作某帧再拍
    ST.close()                                # 收尾（删对象，不删材质缓存）

约定：镜头全部正交、目标点 = 模型包围盒中心，scale 默认按包围盒高度 ×1.16。
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

RES = 760


# ══ 清场 ════════════════════════════════════════════════════════════════════
def purge():
    """删掉场景里的一切（对象 → 网格 → 骨架 → 动作），**不动**插件与偏好。"""
    for ob in list(bpy.data.objects):
        try:
            bpy.data.objects.remove(ob, do_unlink=True)
        except Exception:
            pass
    for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions,
                  bpy.data.lights, bpy.data.cameras):
        for it in list(block):
            try:
                block.remove(it)
            except Exception:
                pass
    for col in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(col)
        except Exception:
            pass
    # 材质一起清：`vox_outline` 这种"建到一半炸掉"的空壳材料会一直缓存下去，
    # 表现是整件单位渲染成纯白（外壳包住本体）。重建比复用便宜。
    for m in list(bpy.data.materials):
        try:
            bpy.data.materials.remove(m)
        except Exception:
            pass


def paths(unit_dir):
    root = os.path.abspath(unit_dir)
    while not os.path.isdir(os.path.join(root, "库")):
        up = os.path.dirname(root)
        if up == root:
            break
        root = up
    return root, [os.path.join(root, "库"), os.path.join(root, "联盟", "基准"),
                  os.path.abspath(unit_dir)]


def load(unit_dir, module):
    """按目录找模块（先清缓存再 import，反复迭代同一进程也不会拿到旧代码）。"""
    root, ps = paths(unit_dir)
    for p in ps:
        if p not in sys.path:
            sys.path.insert(0, p)
    for name in ("voxbase", "poselib2", "anims_lib", "props_vox", "clip_lib",
                 "unit_基准", module, "anims_" + module.split("unit_")[-1]):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    U = importlib.import_module(module)
    A = importlib.import_module("anims_" + U.NAME)
    return U, A


def open_unit(unit_dir, module, act=True, outline=0.0, team=None):
    """建一件单位，返回 dict(g, U, A, ob, arm, root)。act=False 时只建几何。"""
    import voxbase as V
    U, A = load(unit_dir, module)
    g = U.build()
    ob = g.build(prefix=getattr(U, "PREFIX", "vox"))
    arm = g.build_rig("RIG_" + U.NAME)
    g.bind(arm, ob)
    g.bake_preview(ob, team_hex=team)
    root = bpy.data.objects.new(U.NAME, None)
    root.empty_display_size = 0.2
    bpy.context.scene.collection.objects.link(root)
    arm.parent = root
    bpy.context.scene.render.fps = 30
    if act:
        import poselib2 as PL
        import anims_lib as ALIB
        ALIB.set_sole(PL.Sole(arm, [ob]))
        A.build_all(arm)
    if outline:
        V.outline(ob, outline, arm=arm)
    bpy.context.view_layer.update()
    return dict(g=g, U=U, A=A, ob=ob, arm=arm, root=root)


def close(S=None):
    purge()


# ══ 影棚 ════════════════════════════════════════════════════════════════════
def studio(res=760, ground=True, bg="grad", transparent=True, samples=24,
           key=700.0, fill=240.0, rim=520.0):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    try:
        sc.eevee.taa_render_samples = samples
    except Exception:
        pass

    w = bpy.data.worlds.get("STUDIO") or bpy.data.worlds.new("STUDIO")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bgn = nt.nodes.new("ShaderNodeBackground")
    if bg == "grad":
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
    else:
        bgn.inputs["Color"].default_value = (0.30, 0.34, 0.40, 1)
    bgn.inputs["Strength"].default_value = 0.9
    nt.links.new(bgn.outputs["Background"], out.inputs["Surface"])

    def light(name, loc, energy, size, color, aim=(0, 0, 0.95)):
        d = bpy.data.lights.new(name, "AREA")
        d.energy, d.size, d.color = energy, size, color
        o = bpy.data.objects.new(name, d)
        sc.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    light("key", (-2.6, 3.2, 3.6), key, 3.0, (1.0, 0.96, 0.90))
    light("fill", (3.4, 1.8, 1.9), fill, 3.6, (0.80, 0.88, 1.0))
    light("rim", (0.8, -3.6, 2.6), rim, 2.4, (1.0, 0.90, 0.80))

    if ground:
        bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, -0.004))
        gm = bpy.data.materials.get("ground") or bpy.data.materials.new("ground")
        gm.use_nodes = True
        bsdf = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = (0.12, 0.13, 0.12, 1)
        bsdf.inputs["Roughness"].default_value = 0.94
        bpy.context.object.data.materials.append(gm)

    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def bbox(ob):
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def shoot(name, outdir, azim=218, elev=18, scale=None, center=None, res=None,
          fit=None, cam=None):
    sc = bpy.context.scene
    cam = cam or sc.camera
    ob = next(o for o in bpy.data.objects if o.type == "MESH" and "oline" not in o.name)
    mn, mx = bbox(ob)
    H = fit or (mx.z - mn.z)
    t = Vector(center) if center else Vector(((mn.x + mx.x) * 0.5, (mn.y + mx.y) * 0.5,
                                              (mn.z + mx.z) * 0.5))
    a, e = math.radians(azim), math.radians(elev)
    cam.location = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                               math.sin(e))) * 9.0
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = scale or max(H, 1.2) * 1.16
    if res:
        sc.render.resolution_x = sc.render.resolution_y = res
    os.makedirs(outdir, exist_ok=True)
    sc.render.filepath = os.path.join(outdir, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[shot]", sc.render.filepath)
    return sc.render.filepath


def pose(S, act, frame):
    A = S["A"]
    A.pose_at(S["arm"], act, int(frame))
    bpy.context.view_layer.update()


def still(S, outdir, act, frame, name=None, **kw):
    pose(S, act, frame)
    return shoot(name or ("%s_%03d" % (act, frame)), outdir, **kw)


# ══ 量测（摆好姿势之后问"够不够得着 / 有没有穿"）════════════════════════════
def watch(S):
    import clip_lib as CL
    return CL.Watch([S["ob"]])


def point_line_dist(p, o, d):
    v = Vector(p) - Vector(o)
    return (v - Vector(d) * v.dot(d)).length


def metrics(S, W=None, extra_pairs=()):
    """一只手够不够得着、掌心离武器轴多远、最低点在哪。

    `reach` = 肩→掌心距离 − 0.50（负值 = 够得着，正值 = 差多少米）。
    掌心按"手骨原点 + 0.10 × 手骨 +Y"算，和 `anims_lib.PALM_D` 一个口径。
    """
    arm = S["arm"]
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    palms = {}
    for s in ("R", "L"):
        pb = arm.pose.bones.get("hand_" + s)
        ub = arm.pose.bones.get("upperarm_" + s)
        if not pb or not ub:
            continue
        palm = pb.matrix.translation + (pb.matrix.to_3x3() @ Vector((0, 0.10, 0)))
        sh = ub.matrix.translation
        palms[s] = palm
        out["reach_" + s] = round((palm - sh).length - 0.50, 3)
        out["palm_" + s] = tuple(round(v, 3) for v in palm)
    # 双掌到武器的两条轴
    for w, s in (("weapon_R", "R"), ("weapon_L", "L")):
        pb = arm.pose.bones.get(w)
        if not pb:
            continue
        o = pb.matrix.translation
        d = (pb.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
        for s2, p in palms.items():
            out["%s_%s" % (w, s2)] = round(point_line_dist(p, o, d), 3)
        out[w + "_head"] = tuple(round(v, 3) for v in o)
    # 身体最低点 / 全身最低点
    out["zbody"] = round(V_body(S), 4)
    geo = W.geo(dg) if W else None
    if geo:
        zs = [v.z for vs, _ in geo.values() for v in vs]
        out["zmin"] = round(min(zs), 4) if zs else None
        out["z_bone"] = {k: round(min((v.z for v in vs), default=0), 3)
                         for k, (vs, _t) in geo.items() if vs}
    return out


def V_body(S):
    import voxbase as V
    return V.body_min_z(S["ob"])
