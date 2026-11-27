# -*- coding: utf-8 -*-
"""th_look.py —— 造型迭代用的快出图（560 px / 24 采样）"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mkit      # noqa: E402
import mshot     # noqa: E402
import th_model  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "docs", "_tmp", "v7")


def go(star=3, views=((26, 22),), res=560, samp=24, tag="", ground=True):
    os.makedirs(OUT, exist_ok=True)
    mshot.clear()
    ob, B = th_model.build(star)
    mshot.scene(res=(res, res), samp=samp, transparent=False, exposure=0.30)
    mshot.world(top=(0.84, 0.82, 0.77), bottom=(0.58, 0.56, 0.51), strength=0.46)
    if ground:
        mshot.ground(8.0, (0.36, 0.35, 0.32))
    mshot.sun(34, 44, 2.5, 0.20)
    mshot.area("补", -74, 18, 45, 3.0, 3.2, (0.74, 0.82, 1.0))
    mshot.area("轮", 205, 34, 38, 2.6, 3.2, (1.0, 0.92, 0.80))
    # 用真实顶点，不用 bound_box 的 8 个角（空角会把取景撑大 20%）
    pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    corners = pts
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    for k, (az, el) in enumerate(views):
        cam = mshot.cam(az, el, target=(c[0], c[1], c[2]), dist=4.0, ortho=1.0)
        span = mshot.fit(cam, corners, az, el, 1.10, True, center=(c[0], c[1], c[2]))
        cam.location = mshot.Vector((c[0], c[1], c[2])) + mshot.Vector(
            (mshot.math.sin(mshot.math.radians(az)) * mshot.math.cos(mshot.math.radians(el)),
             mshot.math.cos(mshot.math.radians(az)) * mshot.math.cos(mshot.math.radians(el)),
             mshot.math.sin(mshot.math.radians(el)))) * 4.0
        cam.rotation_euler = (cam.location - mshot.Vector((c[0], c[1], c[2]))).to_track_quat('Z', 'Y').to_euler()
        mshot.render(os.path.join(OUT, "look_%d%s_%d.png" % (star, tag, k)))
        print("SHOT", star, k, "span", round(span, 3))


if __name__ == "__main__":
    for s in (1, 2, 3):
        go(s, views=((28, 20), (118, 24)))
