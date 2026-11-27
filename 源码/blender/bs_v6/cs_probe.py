"""cs_probe.py —— 建造系统：读一座建筑，量出系统需要的四个输入。

在 Blender 进程内跑（build/bl_act.py act）。只读 + 打印，不写盘。
"""
import json
import os

import bpy
from mathutils import Vector

ROOT = "D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402

ASSET = asset_path()

TARGETS = [
    ("箭塔", "箭塔_手游_近.glb"),
    ("兵营", "兵营_手游_近.glb"),
]


def hard_reset():
    bpy.ops.wm.read_homefile(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def mesh_stats(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    tris = 0
    open_edges = 0
    for o in objs:
        if o.type != "MESH":
            continue
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
        open_edges += sum(1 for e in o.data.edges if len(e.link_faces if hasattr(e, "link_faces") else []) == 0) if False else 0
    return lo, hi, tris


def report():
    out = {}
    for cn, fn in TARGETS:
        hard_reset()
        objs = import_glb(os.path.join(asset_path(cn), fn))
        roots = [o for o in objs if o.parent is None]
        lo, hi, tris = mesh_stats(objs)
        mats = sorted({s.material.name for o in objs if o.type == "MESH"
                       for s in o.material_slots if s.material})
        info = {
            "file": fn,
            "objects": len([o for o in objs if o.type == "MESH"]),
            "empties": [{"n": o.name, "loc": [round(x, 3) for x in o.location],
                         "rot": [round(x, 4) for x in o.rotation_euler],
                         "scale": [round(x, 3) for x in o.scale]} for o in objs if o.type != "MESH"],
            "roots": [{"n": o.name, "type": o.type,
                       "loc": [round(x, 3) for x in o.location],
                       "rot": [round(x, 4) for x in o.rotation_euler],
                       "scale": [round(x, 3) for x in o.scale]} for o in roots],
            "bbox_lo": [round(x, 3) for x in lo],
            "bbox_hi": [round(x, 3) for x in hi],
            "size": [round(hi[i] - lo[i], 3) for i in range(3)],
            "tris": tris,
            "mats": mats,
            "obj_detail": [],
        }
        for o in objs:
            if o.type != "MESH":
                continue
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            zlo = min(p.z for p in bb)
            zhi = max(p.z for p in bb)
            # 开放边：判断是不是壳体（切层会露内腔）
            me = o.data
            edge_faces = {}
            for p in me.polygons:
                for ek in p.edge_keys:
                    edge_faces[ek] = edge_faces.get(ek, 0) + 1
            open_e = sum(1 for k, v in edge_faces.items() if v == 1)
            info["obj_detail"].append({
                "n": o.name, "mat": o.material_slots[0].material.name if o.material_slots else None,
                "z": [round(zlo, 3), round(zhi, 3)], "verts": len(me.vertices),
                "open_edges": open_e, "parent": o.parent.name if o.parent else None,
            })
        out[cn] = info
    print("###CS_PROBE###" + json.dumps(out, ensure_ascii=False))


report()
