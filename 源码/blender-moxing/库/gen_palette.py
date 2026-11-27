"""gen_palette.py —— 生成单位色板 PNG（系统 Python + Pillow）。

用法：python 库/gen_palette.py
输出：产出/图集/单位色板.png（256²，最近邻采样，sRGB）
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palette  # noqa: E402

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "产出", "图集", "单位色板.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

img = Image.new("RGB", (palette.SIZE, palette.SIZE), (0, 0, 0))
px = img.load()
for i, (name, hexcol) in enumerate(palette.ENTRIES):
    cx, cy = i % palette.CELLS, i // palette.CELLS
    rgb = tuple(int(hexcol[j:j + 2], 16) for j in (1, 3, 5))
    for y in range(cy * palette.CELL, (cy + 1) * palette.CELL):
        for x in range(cx * palette.CELL, (cx + 1) * palette.CELL):
            px[x, y] = rgb
img.save(OUT, optimize=True)
print("[palette]", OUT, img.size, len(palette.ENTRIES), "cells")
