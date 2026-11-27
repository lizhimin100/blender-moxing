"""tr_scene.py —— 地形底材的"进场景"验收图：把建筑放到铺了贴图的地面上

    blender.exe -b --factory-startup --python blender/bs_v6/tr_scene.py

三张：
    地形_草地_兵营.png   草地铺 40 m，兵营站中间（和 docs/兵营/v4 的机位一致）
    地形_泥土_兵营.png   同上，换土路
    地形_拼接_兵营.png   草地 + 中间一条土路（看两种底材能不能拼在一起）

判据只有一条：**地面不能抢建筑**。所以机位、布光全部复用 shotlib，
和 docs 里已有的图直接可比。
"""
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shotlib as S

TEX = "D:/测试一/assets/地形/%s.png"
GLB = "D:/测试一/assets/兵营/兵营_手游_近.glb"
OUT = "D:/测试一/docs/地形"
GROUND = 60.0            # 地面边长（米）
TILE = 8.0               # 一个 tile 的世界尺寸


def ground_mat(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(TEX % name, check_existing=True)
    tex.extension = "REPEAT"
    tex.interpolation = "Linear"
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def ground(name, sx=GROUND, sy=None, z=0.0):
    """铺一块地面：UV 按尺寸/TILE 平铺，保证 1 个 tile = 6 m。"""
    sy = sx if sy is None else sy
    me = bpy.data.meshes.new("ground_" + name)
    me.from_pydata([(-sx * 0.5, -sy * 0.5, z), (sx * 0.5, -sy * 0.5, z),
                    (sx * 0.5, sy * 0.5, z), (-sx * 0.5, sy * 0.5, z)],
                   [], [(0, 1, 2, 3)])
    me.update()
    nx, ny = sx / TILE, sy / TILE
    lay = me.uv_layers.new(name="UVMap")
    for i, uv in enumerate(((0, 0), (nx, 0), (nx, ny), (0, ny))):
        lay.data[i].uv = uv
    ob = bpy.data.objects.new("ground_" + name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(ground_mat(name))
    return ob


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in ("草地", "泥土"):
        S.clear_scene()
        S.setup_world()
        g = ground(name)
        bpy.ops.import_scene.gltf(filepath=GLB)
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH"
                and o is not g]
        S.shot("地形_%s_兵营.png" % name, objs, -34, 26, res=1000, samples=64,
               out=OUT)

    # 拼接：草地 + 中间一条 8 m 宽的土路
    S.clear_scene()
    S.setup_world()
    ground("草地")
    road = ground("泥土", sx=9.0, sy=GROUND, z=0.012)  # 抬高 12 mm 防 z-fight
    bpy.ops.import_scene.gltf(filepath=GLB)
    objs = [o for o in bpy.context.scene.objects
            if o.type == "MESH" and "ground" not in o.name]
    S.shot("地形_拼接_兵营.png", objs, -34, 26, res=1000, samples=64, out=OUT)
    print("[SCENE DONE]")


main()
