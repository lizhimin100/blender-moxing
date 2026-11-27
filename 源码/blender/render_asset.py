"""
render_asset.py —— 在 Blender 里出图 + 存工程（v5 §7）

用法（Blender 进程内）：
    blender --background --python blender/render_asset.py -- <id> [<id> ...]

每座输出：
    docs/renders/<id>.png            2048²  正交 45°/38°，主体占 62–70%
    docs/renders/<id>_front.png      1024²  正立面白模
    docs/renders/<id>_side.png       1024²  侧立面白模
    docs/renders/<id>_top.png        1024²  俯视白模
    blend/<id>.blend                 Blender 工程（源文件）

为什么白模单独出：验收要看"剪影与构造"，材质会把两者都糊住。
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = r"D:/测试一"
GLB = os.path.join(ROOT, "assets", "warband", "buildings")
OUT = os.environ.get("RENDER_OUT") or os.path.join(ROOT, "docs", "renders")
# 阵营色：游戏里由 team_tint.gdshader 按 ORM.a 染色；Blender 里没有这个着色器，
# 出图时把布料/徽记的 Base Color 直接换成阵营主色，否则渲染永远是一片灰白。
TEAM = {"blue": (0.16, 0.32, 0.62), "red": (0.62, 0.16, 0.16), "green": (0.18, 0.44, 0.24)}.get(
    os.environ.get("TEAM", ""), None)
BLEND = os.path.join(ROOT, "blend")

IDS = ["townhall", "barracks", "blacksmith", "farm", "watchtower", "lumbermill"]


def clear():
    """清场景但不动 factory settings —— 在 GUI 里跑时不能把宿主文件重置掉。"""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.armatures, bpy.data.actions, bpy.data.cameras,
                bpy.data.lights):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def bounds():
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return lo, hi


def setup_world(strength=0.9, top=(0.62, 0.66, 0.72), bottom=(0.16, 0.17, 0.19)):
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    tex = nt.nodes.new("ShaderNodeTexGradient")
    tex.gradient_type = "LINEAR"
    mapn = nt.nodes.new("ShaderNodeMapping")
    texc = nt.nodes.new("ShaderNodeTexCoord")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (*top, 1)
    mapn.inputs["Rotation"].default_value = (math.radians(90), 0, 0)
    nt.links.new(texc.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_light(name, loc, energy, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.size = size
    d.color = color
    ob = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    direction = Vector((0, 0, 0)) - Vector(loc)
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return ob


def make_camera(target, span, ortho=True, az=45.0, el=38.0, offset=0.0):
    cam = bpy.data.cameras.new("Cam")
    cam.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cam.ortho_scale = span
    ob = bpy.data.objects.new("Cam", cam)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    r = max(span * 3.0, 40.0)
    # glTF→Blender 会把 −Z（正面）映射到 +Y，所以 yaw=0 的相机必须站在 +Y 一侧。
    ob.location = target + Vector((math.sin(a) * math.cos(e) * r,
                                   math.cos(a) * math.cos(e) * r,
                                   math.sin(e) * r))
    d = target - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def set_render(res, engine="EEVEE", samples=64, transparent=False):
    sc = bpy.context.scene
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = 0.55
    want = ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"] if engine == "EEVEE" else ["CYCLES"]
    for name in want:
        try:
            sc.render.engine = name
            break
        except TypeError:
            continue
    if sc.render.engine.startswith("BLENDER_EEVEE"):
        ee = sc.eevee
        for attr, val in (("taa_render_samples", samples), ("use_gtao", True),
                          ("use_shadows", True), ("use_raytracing", True)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:
                    pass
    else:
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True


def tint_team():
    if TEAM is None:
        return
    for name, col in (("cloth_team", TEAM), ("emblem", (0.92, 0.88, 0.62))):
        m = bpy.data.materials.get(name)
        if not m or not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                n.inputs["Base Color"].default_value = (*col, 1)
                for lk in list(m.node_tree.links):
                    if lk.to_node == n and lk.to_socket.name == "Base Color":
                        m.node_tree.links.remove(lk)


def clay(on=True):
    for m in bpy.data.materials:
        m.use_nodes = True
        nt = m.node_tree
        if on:
            for n in nt.nodes:
                if n.type == "BSDF_PRINCIPLED":
                    n.inputs["Base Color"].default_value = (0.82, 0.82, 0.82, 1)
                    n.inputs["Roughness"].default_value = 0.62
                    n.inputs["Metallic"].default_value = 0.0
                    for inp in ("Normal", "Base Color"):
                        for lk in list(nt.links):
                            if lk.to_node == n and lk.to_socket.name == inp:
                                nt.links.remove(lk)


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render]", path)


def one(bid):
    clear()
    path = os.path.join(GLB, bid + ".glb")
    bpy.ops.import_scene.gltf(filepath=path)
    # 用 static clip 的第 1 帧定格：它把脚手架/瓦砾缩到 0，其他骨复位。
    # 直接用 REST 会把脚手架渲染出来 —— 那是施工态，不是交付态。
    for ob in bpy.context.scene.objects:
        if ob.type != "ARMATURE":
            continue
        act = bpy.data.actions.get("static")
        if act:
            if ob.animation_data is None:
                ob.animation_data_create()
            ob.animation_data.action = act
        ob.data.pose_position = "POSE"
    bpy.context.scene.frame_set(30)
    bpy.context.view_layer.update()
    lo, hi = bounds()
    ctr = (lo + hi) / 2
    size = hi - lo
    span = max(size.y, size.x) * 1.46            # 主体占 68% 画面

    setup_world()
    add_light("key", ctr + Vector((-span * 0.9, span * 1.05, span * 1.15)),
              energy=span * span * 26, size=span * 0.8)
    add_light("fill", ctr + Vector((span * 1.2, span * 0.35, span * 0.35)),
              energy=span * span * 6, size=span * 1.1, color=(0.72, 0.82, 1.0))

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(BLEND, exist_ok=True)
    tint_team()

    cam = make_camera(Vector((ctr.x, ctr.y * 0.98, ctr.z)), span, ortho=True, az=-45, el=38)
    set_render(2048, "EEVEE", 96)
    render_to(os.path.join(OUT, bid + ".png"))

    # 三张白模正交图
    clay(True)
    set_render(1024, "EEVEE", 64)
    for tag, az, el in (("front", 0, 0), ("side", 90, 0), ("top", 0, 89)):
        for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
            bpy.data.objects.remove(ob, do_unlink=True)
        make_camera(Vector((ctr.x, ctr.y, ctr.z)), span * 1.06, ortho=True, az=az, el=el)
        render_to(os.path.join(OUT, f"{bid}_{tag}.png"))
    clay(False)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, bid + ".blend"))
    print("[blend]", bid)


def main():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    ids = [a for a in args if not a.startswith("-")] or IDS
    for bid in ids:
        one(bid)


if __name__ == "__main__":
    main()
