# -*- coding: utf-8 -*-
"""a_shots.py —— 三阶同框预览 / 图标底片 / 卡牌底片

三套图，机位同一套（方位 32° / 俯角 33° 正交），保证七座建筑摆在一起时
俯视角完全一致 —— 这是"同一套游戏资产"最容易被破坏的地方。

  1. **三阶同框**：1/2/3 星在**同一场景**里横向排开，间距 1.5 m，一张图。
     这是验收"变宽还是变高"的唯一证据，必须真的在一个场景里拍。
  2. **图标底片**：单档 + 地面，1024²，用于 512 图标。
  3. **卡牌底片**：单档 + 透明背景，1500²，用于 1024×1400 卡牌。

    blender -b --factory-startup -P a_shots.py                # 全部
    blender -b --factory-startup -P a_shots.py -- a_farm       # 单座
"""
import importlib
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from bpy_extras.object_utils import world_to_camera_view  # noqa: E402

import akit   # noqa: E402
import mshot  # noqa: E402

RAW = os.path.join(ROOT, "docs", "_tmp", "v8", "shots")
BOOKS = [
    ("a_townhall", "城镇大厅"),
    ("a_barracks", "兵营"),
    ("a_farm",     "农场"),
    ("a_smith",    "铁匠铺"),
    ("a_lumber",   "伐木场"),
    ("a_watch",    "哨塔"),
    ("a_arrow",    "箭塔"),
]
_BST = os.path.join(ROOT, "docs", "_tmp", "v8", "shots", "bbox.json")
BOXES = json.load(open(_BST, encoding="utf-8")) if os.path.exists(_BST) else {}
# 只算投影不渲染：单座重拍时用它刷新裁切框，省 6 分钟
NORENDER = bool(os.environ.get("AV_NO_RENDER"))


def light_setup(ground=True, exposure=0.0):
    mshot.world(top=(0.86, 0.84, 0.79), bottom=(0.56, 0.54, 0.49), strength=0.40)
    if ground:
        mshot.ground(24.0, (0.300, 0.292, 0.268))
    mshot.sun(34, 46, 1.55, 0.20)
    mshot.area("补", -72, 16, 32, 3.4, 3.2, (0.74, 0.83, 1.0))
    mshot.area("轮", 208, 36, 28, 2.8, 3.2, (1.0, 0.88, 0.72))
    _ = exposure


def points(objs):
    out = []
    for ob in objs:
        out += [ob.matrix_world @ v.co for v in ob.data.vertices]
    return out


def centre(pts):
    lo = [min(p[i] for p in pts) for i in range(3)]
    hi = [max(p[i] for p in pts) for i in range(3)]
    return [(lo[i] + hi[i]) / 2 for i in range(3)], lo, hi


def frame(pts, az, el, res, margin=1.06):
    """按**真实顶点**取景，并按画幅比例修正正交跨度。

    mshot.fit 只按 max(width,height) 给跨度，宽画幅（2400×1100）会把
    上下留成两条白边 —— 这里把高度需求乘回宽高比。
    """
    c, lo, hi = centre(pts)
    azr, elr = math.radians(az), math.radians(el)
    v = Vector((math.sin(azr) * math.cos(elr), math.cos(azr) * math.cos(elr),
                math.sin(elr)))
    q = v.to_track_quat('Z', 'Y')
    rot = q.to_matrix()
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    rel = [Vector((p[0] - c[0], p[1] - c[1], p[2] - c[2])) for p in pts]
    mx = max(abs(p.dot(right)) for p in rel)
    my = max(abs(p.dot(up)) for p in rel)
    aspect = res[0] / float(res[1])
    span = max(2 * mx, 2 * my * aspect) * margin
    return c, span


def render(name, mod, star, kind, res, az=32, el=33, margin=1.06, ground=True,
           line_up=False):
    akit.mkit.clear()
    if line_up:
        objs = []
        # 相机在 +X/+Y 侧，**+X 在屏幕左边** —— 所以 1★ 放 +1.5、
        # 3★ 放 −1.5，排出来才是从左到右 1→2→3。
        # 设完 location 必须 view_layer.update()，否则 matrix_world 还是旧的，
        # 取景会按"三座都在原点"算，结果一座被切掉、右边一大片空。
        for i, s in enumerate((1, 2, 3)):
            ob, B = mod.build(s)
            ob.location.x = (1 - i) * 1.5
            objs.append(ob)
        bpy.context.view_layer.update()
        ob = objs
    else:
        ob0, B = mod.build(star)
        ob = [ob0]

    mshot.scene(res=res, samp=96, transparent=not ground, exposure=0.0)
    light_setup(ground)
    pts = points(ob)
    c, span = frame(pts, az, el, res, margin)
    cam = mshot.cam(az, el, target=(c[0], c[1], c[2]), dist=8.0, ortho=1.0)
    cam.data.ortho_scale = span
    # 相机刚改过位置/朝向：不 update 的话 matrix_world 还是旧的，
    # 投影框会按"相机在原点"算 —— 渲染路径被 render() 顺手刷新了，
    # 所以只在 AV_NO_RENDER 模式暴露，图标会被裁错。
    bpy.context.view_layer.update()
    path = os.path.join(RAW, "%s%s.png" % (name, kind))
    if not NORENDER:
        mshot.render(path)
    # 投影框（裁切用）
    sc = bpy.context.scene
    xs, ys = [], []
    for co in pts:
        p = world_to_camera_view(sc, cam, co)
        xs.append(p.x * res[0])
        ys.append((1 - p.y) * res[1])
    BOXES[os.path.basename(path)] = [round(min(xs), 1), round(min(ys), 1),
                                     round(max(xs), 1), round(max(ys), 1)]
    if not NORENDER:
        print("   %-28s span=%.2f  %s" % (os.path.basename(path), span,
                                          BOXES[os.path.basename(path)]))
    return path


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = set(argv) if argv else None
    os.makedirs(RAW, exist_ok=True)
    for modname, cn in BOOKS:
        try:
            mod = importlib.import_module(modname)
        except ModuleNotFoundError:
            print("[skip] %s 缺模块" % modname)
            continue
        if only and modname not in only:
            continue
        print("== %s ==" % cn)
        # 1) 三阶同框：一张图证明"变宽不变高"
        render(cn, mod, 3, "_三阶同框", (2400, 920), 32, 33, 1.05,
               ground=True, line_up=True)
        # 2) 图标底片
        for s in (1, 2, 3):
            render(cn, mod, s, "_icon%d" % s, (1024, 1024), 32, 33, 1.10, True)
        # 3) 卡牌底片（透明）
        for s in (1, 2, 3):
            render(cn, mod, s, "_sprite%d" % s, (1500, 1500), 28, 26, 1.04, False)
    with open(os.path.join(RAW, "bbox.json"), "w", encoding="utf-8") as f:
        json.dump(BOXES, f, ensure_ascii=False, indent=2)
    print("done ->", RAW)
