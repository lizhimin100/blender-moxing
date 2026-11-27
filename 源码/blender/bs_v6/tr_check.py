"""tr_check.py —— 地形贴图的体检出图（不参与生产，只出"看图用的图"）

    blender.exe -b --factory-startup --python blender/bs_v6/tr_check.py

出四样：
    _预览_平铺.png    3×3 平铺（缩到 768）—— 看接缝和重复感
    _预览_近景.png    256² 局部放大 2×      —— 看草簇 / 裂纹的笔触
    _预览_远景.png    缩到 128 再放大 3×    —— 模拟 RTS 机位，看会不会抢建筑
    _预览_对照.png    两张并排 + 色阶条
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tr_tex as T


def to_img(arr, path):
    h, w = arr.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    img.colorspace_settings.name = "sRGB"
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def box(px, k):
    h, w, _ = px.shape
    return px.reshape(h // k, k, w // k, k, 3).mean(axis=(1, 3))


def near(px, k):
    return px.repeat(k, axis=0).repeat(k, axis=1)


def tile(px, n):
    return np.tile(px, (n, n, 1))


def main():
    out = T.DOC_DIR
    os.makedirs(out, exist_ok=True)
    for name in ("草地", "泥土"):
        px = T.load_px(os.path.join(T.OUT_DIR, name + ".png"))
        s = name
        # 3×3 平铺 → 768
        to_img(box(tile(px, 3), 2), os.path.join(out, "_预览_平铺_%s.png" % s))
        # 近景：256² 放大 2×
        crop = px[128:384, 128:384]
        to_img(near(crop, 2), os.path.join(out, "_预览_近景_%s.png" % s))
        # 远景：96 → 384（4×）
        to_img(near(box(px, 4), 3), os.path.join(out, "_预览_远景_%s.png" % s))
        print("[CHECK]", name, "ok")


main()
