"""th_light_test.py -- 试验 2：面积光主光、去背光（看地面光斑是否消失）"""
import importlib, math, os, sys
import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
OUT = r"D:/测试一/docs/城镇大厅/v2/_wip"
sys.path.insert(0, HERE)
for m in ("bslib", "br_model", "th_model"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import bslib, th_model

def clear():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras,
                bpy.data.lights, bpy.data.worlds):
        for it in list(blk):
            try: blk.remove(it)
            except Exception: pass

def bounds(objs):
    lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return lo, hi

def world():
    w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB"); tex = nt.nodes.new("ShaderNodeTexGradient")
    mapn = nt.nodes.new("ShaderNodeMapping"); texc = nt.nodes.new("ShaderNodeTexCoord")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.050,0.058,0.064,1)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (0.30,0.34,0.38,1)
    mapn.inputs["Rotation"].default_value = (math.radians(90),0,0)
    nt.links.new(texc.outputs["Generated"], mapn.inputs["Vector"])
    nt.links.new(mapn.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.45
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

def ground():
    me = bpy.data.meshes.new("ground"); s = 300.0
    me.from_pydata([(-s,-s,0),(s,-s,0),(s,s,0),(-s,s,0)], [], [(0,1,2,3)]); me.update()
    ob = bpy.data.objects.new("ground", me); bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("G"); mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*bslib.srgb("#3F4638"), 1)
    b.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in b.inputs: b.inputs["Specular IOR Level"].default_value = 0.0
    ob.data.materials.append(mat)

def area(name, loc, energy, size, color, aim):
    d = bpy.data.lights.new(name, "AREA"); d.energy = energy; d.size = size; d.color = color
    ob = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(aim)-Vector(loc)).to_track_quat("-Z","Y").to_euler()
    return ob

def basis(az, el):
    a, e = math.radians(az), math.radians(el)
    view = Vector((math.sin(a)*math.cos(e), math.cos(a)*math.cos(e), math.sin(e))).normalized()
    right = view.cross(Vector((0,0,1))).normalized()
    up = right.cross(view).normalized()
    return view, right, up

def fit(objs, az, el):
    lo, hi = bounds(objs); ctr = (lo+hi)*0.5
    view, right, up = basis(az, el)
    mx = my = 0.0
    for ob in objs:
        for c in ob.bound_box:
            p = (ob.matrix_world @ Vector(c)) - ctr
            mx = max(mx, abs(p.dot(right))); my = max(my, abs(p.dot(up)))
    return ctr, max(mx,my)*2.0*1.08

def stage(ctr, span, az, el):
    view, right, up = basis(az, el)
    area("key", ctr + (-0.62*right + 0.92*up + 1.35*view)*span,
         span*span*112, span*0.52, (1.0,0.93,0.82), ctr)
    area("fill", ctr + (1.15*right + 0.10*up + 0.95*view)*span,
         span*span*20, span*1.15, (0.64,0.78,1.0), ctr)
    area("bounce", ctr + (0.05*right - 0.95*up + 0.75*view)*span,
         span*span*9, span*1.25, (0.86,0.90,1.0), ctr)

def shot(name, objs, az, el):
    ctr, span = fit(objs, az, el)
    for ob in [o for o in bpy.context.scene.objects if o.type == "CAMERA"]:
        bpy.data.objects.remove(ob, do_unlink=True)
    cam = bpy.data.cameras.new("C"); cam.type = "ORTHO"; cam.ortho_scale = span
    ob = bpy.data.objects.new("C", cam); bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el); r = 120.0
    ob.location = ctr + Vector((math.sin(a)*math.cos(e)*r, math.cos(a)*math.cos(e)*r, math.sin(e)*r))
    ob.rotation_euler = (ctr-ob.location).to_track_quat("-Z","Y").to_euler()
    bpy.context.scene.camera = ob
    for l in [o for o in bpy.context.scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(l, do_unlink=True)
    stage(ctr, max(span, 16.0), az, el)
    sc = bpy.context.scene
    sc.render.resolution_x = 760; sc.render.resolution_y = 760
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    try: sc.view_settings.look = "AgX - Punchy"
    except Exception: pass
    sc.view_settings.exposure = 0.18
    sc.render.engine = "BLENDER_EEVEE"
    ee = getattr(sc, "eevee", None)
    if ee:
        for k,v in (("taa_render_samples",24),("use_gtao",True),("use_shadows",True),("use_raytracing",True)):
            try: setattr(ee,k,v)
            except Exception: pass
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)

def main():
    clear(); objs, st = th_model.build(smooth=True); print(st)
    world(); ground()
    shot("light_hero.png", objs, -48, 30)
    shot("light_back.png", objs, 148, 26)
    print("DONE")

main()
