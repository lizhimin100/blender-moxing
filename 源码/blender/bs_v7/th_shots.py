# -*- coding: utf-8 -*-
"""th_shots.py —— 交付出图：图标底片（带地面）+ 卡牌底片（透明）

图标走"沙盘摆件"机位：方位 26°、俯角 30°、正交 —— 和游戏里 3/4 俯视一致，
上卡牌时建筑不会因为透视变形而认不出来。
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

import mkit      # noqa: E402
import mshot     # noqa: E402
import th_model  # noqa: E402

RAW = os.path.join(ROOT, "docs", "_tmp", "v7", "shots")
boxes = {}


def stage(star, ground=True, exposure=0.30):
    mkit.clear()
    ob, B = th_model.build(star)
    mshot.scene(res=(1024, 1024), samp=96, transparent=not ground, exposure=exposure)
    mshot.world(top=(0.84, 0.82, 0.77), bottom=(0.58, 0.56, 0.51), strength=0.46)
    if ground:
        mshot.ground(18.0, (0.360, 0.350, 0.320))
    mshot.sun(34, 44, 2.5, 0.20)
    mshot.area("补", -72, 16, 56, 3.4, 3.2, (0.74, 0.83, 1.0))
    mshot.area("轮", 208, 36, 48, 2.8, 3.2, (1.0, 0.88, 0.72))
    corners = mesh_points(ob)
    lo = [min(p[i] for p in corners) for i in range(3)]
    hi = [max(p[i] for p in corners) for i in range(3)]
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    return ob, corners, c


def mesh_points(ob):
    """真实顶点，而不是 bound_box 的 8 个角 —— 空角会把取景撑大约 20%。"""
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def proj_bbox(ob, res):
    """模型 8 个包围盒角在画面里的像素框 —— 给 PIL 精确裁切用，别靠肉眼猜。"""
    sc = bpy.context.scene
    cam = sc.camera
    xs, ys = [], []
    for co in mesh_points(ob):
        p = world_to_camera_view(sc, cam, co)
        xs.append(p.x * res[0])
        ys.append((1 - p.y) * res[1])
    return [min(xs), min(ys), max(xs), max(ys)]


def shot(ob, corners, c, path, az=26, el=30, margin=1.05, res=(1024, 1024), samp=96):
    mshot.scene(res=res, samp=samp, transparent=bpy.context.scene.render.film_transparent)
    cam = mshot.cam(az, el, target=(c[0], c[1], c[2] * 0.96), dist=5.0, ortho=1.0)
    span = mshot.fit(cam, corners, az, el, margin, True, center=(c[0], c[1], c[2] * 0.96))
    cam.data.ortho_scale = span
    print("   shot %s span=%.3f" % (os.path.basename(path), span))
    mshot.render(path)
    bb = proj_bbox(ob, res)
    boxes[os.path.basename(path)] = [round(v, 1) for v in bb]
    print("   bbox", boxes[os.path.basename(path)])
    return path


if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    for s in (1, 2, 3):
        ob, corners, c = stage(s, ground=True)
        shot(ob, corners, c, os.path.join(RAW, "icon_%d.png" % s), 30, 33, 1.14, (1024, 1024), 96)
    # 卡牌底片：透明 + 略低俯角，给卡面留出天空
    for s in (3, 2, 1):
        ob, corners, c = stage(s, ground=False, exposure=0.38)
        shot(ob, corners, c, os.path.join(RAW, "sprite_%d.png" % s), 27, 25, 1.05, (1600, 1600), 96)
    import json
    with open(os.path.join(RAW, "bbox.json"), "w", encoding="utf-8") as f:
        json.dump(boxes, f, ensure_ascii=False, indent=2)
