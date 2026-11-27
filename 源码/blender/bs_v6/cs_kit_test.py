"""cs_kit_test.py —— 工地套件形体/配色对照（带真建筑）。"""
import importlib
import os
import sys

import bpy

HERE = "D:/测试一/blender/bs_v6"
sys.path.insert(0, HERE)

import cs_kit
import shotlib as S

importlib.reload(cs_kit)
importlib.reload(S)

OUT = "D:/测试一/docs/建造系统/_look"
SRC = "D:/测试一/assets/箭塔/箭塔_手游_近.glb"


def pct(vals, q):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(len(vals) * q))]


def main():
    S.clear_scene()
    S.OUTSHOT = OUT
    bpy.ops.import_scene.gltf(filepath=SRC)
    H = 17.46
    xs, ys = [], []
    lo, hi = [1e9] * 3, [-1e9] * 3
    for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        mw = o.matrix_world
        for v in o.data.vertices:
            p = mw @ v.co
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
            if 1.8 <= p.z <= 0.72 * H:
                xs.append(abs(p.x))
                ys.append(abs(p.y))
    body = (2 * pct(xs, 0.985), 2 * pct(ys, 0.985))
    print("bbox", [round(x, 2) for x in lo], [round(x, 2) for x in hi],
          "body", [round(x, 2) for x in body])

    W, D = hi[0] - lo[0], hi[1] - lo[1]
    edges = [0, 0.55, 2.6, 4.6, 6.6, 8.6, 10.6, 12.6, 14.6, 17.46]
    detail = os.environ.get("CS_DETAIL", "low")
    k = cs_kit.Kit(W, D, H, edges, body=body).build()
    ob = k.to_object("SiteKit", detail=detail)
    ob.data.calc_loop_triangles()
    print("detail", detail, "kit tris", len(ob.data.loop_triangles),
          "verts", len(ob.data.vertices), "bones", len(k.bones), "lifts", k.meta["lifts"])

    S.setup_world()
    S.ground_plane()
    S.RES, S.SAMP = 1000, 48
    os.makedirs(OUT, exist_ok=True)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "ground"]
    S.shot(f"kit_{detail}_3q.png", objs, -34, 26, 1.06)
    S.shot(f"kit_{detail}_top.png", objs, -34, 58, 1.06)
    S.shot(f"kit_{detail}_front.png", objs, 0, 8, 1.10)


main()
