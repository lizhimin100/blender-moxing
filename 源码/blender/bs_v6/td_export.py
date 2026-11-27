"""td_export.py —— 地形地块导出：GLB（主版本 + 低模）+ .blend + 回查

    blender.exe -b --factory-startup --python blender/bs_v6/td_export.py

主版本 = 低模 + 6 mm 倒角（地表）/ 细分（道具）；低模 = 原始网格，一点不倒角。
两个版本共用同一套材质与贴图，切版本不掉材质。
"""
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import td_model as M

OUT = "D:/测试一/assets/地形/地块"
SRC_DIR = "D:/测试一/blender/_源文件/地形"   # .blend 是源文件，不进 assets


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.cameras, bpy.data.lights):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


def export_glb(objs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_yup=True,
        export_apply=False, export_materials="EXPORT", export_cameras=False,
        export_lights=False, export_extras=True, export_normals=True,
        export_tangents=False, export_texcoords=True)
    bpy.ops.object.select_all(action="DESELECT")
    return os.path.getsize(path)


def stats(objs):
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        me = ob.data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    return tris, (hi - lo)


def verify(path):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris, dim = stats(objs)
    mats = sorted({s.material.name for o in objs for s in o.material_slots if s.material})
    imgs = [i.name for i in bpy.data.images if i.name != "Render Result"]
    return len(objs), tris, dim, mats, imgs


def main():
    os.makedirs(OUT, exist_ok=True)
    results = {}

    for tag, smooth in (("裂纹泥地", True), ("裂纹泥地_低模", False)):
        clear_scene()
        objs, st = M.build(smooth=smooth)
        # 合材质：125 个构件 = 125 次 draw call，引擎侧扛不住。
        # join_by_material 按材质合，合完只剩「板 ×3 + 缝 + 底座 + 石 + 草」7 个物体。
        objs = M.L.join_by_material(objs, prefix="TD")
        tris, dim = stats(objs)
        path = os.path.join(OUT, "%s.glb" % tag)
        size = export_glb(objs, path)
        n, vt, vd, mats, imgs = verify(path)
        results[tag] = dict(objs=n, tris=vt, size_kb=round(size / 1024),
                            dim="%.2f × %.2f × %.2f" % (vd.x, vd.y, vd.z),
                            mats=mats, imgs=imgs)
        print("[TD EXPORT]", tag, results[tag])
        if smooth:
            bpy.context.preferences.filepaths.save_version = 0
            bpy.ops.wm.save_as_mainfile(
                filepath=os.path.join(SRC_DIR, "裂纹泥地.blend"), relative_remap=False)
    print("[TD EXPORT DONE]")


main()
