"""style_bench.py —— 审美对照台：同一座建筑 × 四个造型方向。

**这不是交付物，是"指认工具"。**
用户说"我对造型不满意"但说不出要什么的时候，别再猜词 —— 给他四张同一机位、
只改造型参数的图，让他指"哪个更接近、哪两个各要一半"。

四个方向（只动三件事：Z 比例、XY 比例、构件是否歪/是否删）：
    A 要塞   Z×0.84 XY×1.08   压扁加宽，重心低，"压得住地面"
    B 神殿   Z×1.18 XY×0.93   拉高收窄，"垂直感"
    C 遗迹   逐件 ±1.6° 倾斜   松脱、错位、随时要塌
    D 极简   删掉体积 < 12 L 的构件  只留主体量，装饰密度降到 1/3

    "D:/360安全浏览器下载/blender.exe" -b --python blender/bs_v6/style_bench.py
产物：docs/审美/对照_<资产>_<方向>.png
"""
import importlib
import math
import os
import random
import sys

import bpy
from mathutils import Euler, Matrix, Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from assets_path import asset_path  # noqa: E402,F401

TARGET = "dg_model"          # 想对照哪座就改这里
CN = "地牢"
AZ, EL = -34.0, 27.0

for _m in ("bslib", "br_model", "wt_model", "dl_kit", TARGET):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
mod = importlib.import_module(TARGET)
import shotlib as S  # noqa: E402

OUT = os.path.join(ROOT, "docs", "审美")
os.makedirs(OUT, exist_ok=True)
S.OUTSHOT = OUT


def volume(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    dx = max(p.x for p in pts) - min(p.x for p in pts)
    dy = max(p.y for p in pts) - min(p.y for p in pts)
    dz = max(p.z for p in pts) - min(p.z for p in pts)
    return dx * dy * dz


def morph(objs, sz=1.0, sxy=1.0, tilt=0.0, drop=0.0, seed=7):
    """把整座建筑按"造型方向"整体变形（只动变换，不改几何）。"""
    S_ = Matrix.Diagonal((sxy, sxy, sz, 1.0))
    rnd = random.Random(seed)
    dead = []
    for ob in objs:
        if drop and volume(ob) < drop:
            dead.append(ob)
            continue
        mw = ob.matrix_world.copy()
        T = Matrix.Identity(4)
        if tilt:
            pts = [mw @ Vector(c) for c in ob.bound_box]
            pivot = Vector((sum(p.x for p in pts) / 8.0,
                            sum(p.y for p in pts) / 8.0,
                            min(p.z for p in pts)))
            R = Euler((math.radians(rnd.uniform(-tilt, tilt)),
                       math.radians(rnd.uniform(-tilt, tilt)),
                       math.radians(rnd.uniform(-tilt * 0.5, tilt * 0.5))),
                      "XYZ").to_matrix().to_4x4()
            T = Matrix.Translation(pivot) @ R @ Matrix.Translation(-pivot)
        ob.matrix_world = S_ @ T @ mw
    for ob in dead:
        bpy.data.objects.remove(ob, do_unlink=True)
    return [o for o in objs if o not in dead], len(dead)


VARIANTS = [
    ("A_要塞", dict(sz=0.84, sxy=1.08), 0.00, "压扁加宽 · 重心低"),
    ("B_神殿", dict(sz=1.18, sxy=0.93), 0.00, "拉高收窄 · 垂直感"),
    ("C_遗迹", dict(tilt=1.6), 0.00, "逐件倾斜 · 松脱"),
    ("D_极简", dict(drop=0.012), 0.00, "删小构件 · 只留体量"),
]

# 先量一次，四个方向共用同一机位（否则"变大变小"会污染判断）
S.clear_scene()
base, _ = mod.build(smooth=True)
ctr, span = S.fit_span(base, AZ, EL, 1.08)
span *= 1.17
print("[bench] fixed frame", [round(v, 2) for v in ctr], "span %.2f" % span)

for i, (tag, kw, expo, why) in enumerate(VARIANTS):
    S.clear_scene()
    objs, st = mod.build(smooth=True)
    objs, ndead = morph(objs, seed=11 + i, **kw)
    S.setup_world()
    S.ground_plane()
    bpy.context.scene.view_settings.exposure = 0.20 + expo
    path = "对照_%s_%s.png" % (CN, tag)
    S.shot(path, objs, AZ, EL, fixed=(ctr, span), res=760, samples=64)
    print("[bench] %-8s %s  drop=%d  tris=%s" % (tag, why, ndead, st.get("tris")))
print("BENCH_DONE")
