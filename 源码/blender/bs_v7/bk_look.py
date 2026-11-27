# -*- coding: utf-8 -*-
"""bk_look.py —— 兵营造型迭代快出图（560 px / 24 采样）

    blender -b --factory-startup -P bk_look.py            # 三档 × 两个机位
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import mkit      # noqa: E402
import mshot     # noqa: E402
import bk_model  # noqa: E402

OUT = os.path.join(ROOT, "docs", "_tmp", "v7", "look")


def go(star=3, views=((28, 22),), res=560, samp=24, tag="", ground=True,
       exposure=0.30):
    os.makedirs(OUT, exist_ok=True)
    mshot.clear()
    ob, B = bk_model.build(star)
    mshot.scene(res=(res, res), samp=samp, transparent=False, exposure=exposure)
    mshot.world(top=(0.84, 0.82, 0.77), bottom=(0.58, 0.56, 0.51), strength=0.46)
    if ground:
        mshot.ground(8.0, (0.36, 0.35, 0.32))
    mshot.sun(34, 44, 2.5, 0.20)
    mshot.area("补", -74, 18, 45, 3.0, 3.2, (0.74, 0.82, 1.0))
    mshot.area("轮", 205, 34, 38, 2.6, 3.2, (1.0, 0.92, 0.80))
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    for k, (az, el) in enumerate(views):
        cam = mshot.cam(az, el, target=tuple(c), dist=4.0, ortho=1.0)
        span = mshot.fit(cam, pts, az, el, 1.08, True, center=tuple(c))
        cam.data.ortho_scale = span
        mshot.render(os.path.join(OUT, "look_%d%s_%d.png" % (star, tag, k)))
        print("SHOT", star, k, "span", round(span, 3), "tris",
              len(ob.data.loop_triangles))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stars = [int(a) for a in args if a.isdigit()] or [1, 2, 3]
    for s in stars:
        go(s, views=((28, 20), (118, 24), (0, 34)))
