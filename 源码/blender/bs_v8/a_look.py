# -*- coding: utf-8 -*-
"""a_look.py —— 造型迭代用快出图（4 机位 / 640 px / 单档）

    blender -b --factory-startup -P a_look.py -- a_townhall 3

只为"看体块"服务：不打灯阵、不做后期。判定标准只有一条：
**缩到 96 px 还认不认得出这是哪座建筑**。所以最后一张固定是 96 px 缩略。
"""
import importlib
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import akit      # noqa: E402
import mshot     # noqa: E402

OUT = os.path.join(ROOT, "docs", "_tmp", "v8", "look")


def mesh_points(ob):
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def setup(ground=True, exposure=0.0):
    mshot.scene(res=(640, 640), samp=32, transparent=not ground, exposure=exposure)
    mshot.world(top=(0.86, 0.84, 0.79), bottom=(0.56, 0.54, 0.49), strength=0.40)
    if ground:
        mshot.ground(18.0, (0.300, 0.292, 0.268))
    mshot.sun(34, 46, 1.55, 0.20)
    mshot.area("补", -72, 16, 32, 3.4, 3.2, (0.74, 0.83, 1.0))
    mshot.area("轮", 208, 36, 28, 2.8, 3.2, (1.0, 0.88, 0.72))


def shoot(ob, path, az, el, margin=1.10):
    pts = mesh_points(ob)
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    cam = mshot.cam(az, el, target=(c[0], c[1], c[2] * 0.98), dist=5.0, ortho=1.0)
    span = mshot.fit(cam, pts, az, el, margin, True, center=(c[0], c[1], c[2] * 0.98))
    cam.data.ortho_scale = span
    mshot.render(path)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mod_name = argv[0] if argv else "a_townhall"
    star = int(argv[1]) if len(argv) > 1 else 3
    mod = importlib.import_module(mod_name)

    os.makedirs(OUT, exist_ok=True)
    akit.mkit.clear()
    ob, B = mod.build(star)
    ob.data.calc_loop_triangles()
    print("tris=%d parts=%d" % (len(ob.data.loop_triangles), len(B.info)))
    setup(True)
    for tag, az, el in (("a", 32, 33), ("b", 88, 18), ("c", -40, 40), ("d", 0, 62)):
        shoot(ob, os.path.join(OUT, "%s_%d_%s.png" % (mod_name, star, tag)), az, el, 1.10)
    print("done ->", OUT)
