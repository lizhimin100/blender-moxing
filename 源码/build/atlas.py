"""
atlas.py —— 每座建筑 1 张 2048 图集（BC / N / ORM(RGBA) / E）

布局：4×4 格，每格 512，其中美术区 504 + 四周 4 px 边缘复制。
UV 在导出时按"整数瓦片"切分后重映射到格内，所以图集不会出现平铺断裂；
原 TEXCOORD_0 保留，便于回退到逐材质贴图。
"""
import os
import numpy as np
from PIL import Image

SIZE = 2048
CELL = 512
PAD = 4
ART = CELL - PAD * 2
COLS = SIZE // CELL


def _fit(img, size=ART):
    """RGBA 必须把 RGB 与 A 分开缩放：PIL 直接缩放 RGBA 会把 alpha=0 的 RGB 清空，
    而 ORM 的 A 通道是 TC1 遮罩，绝大多数材质 alpha=0 —— 直接缩放会毁掉整张 ORM。"""
    if img.mode == "RGBA":
        a = np.asarray(img)
        rgb = Image.fromarray(a[:, :, :3], "RGB").resize((size, size), Image.LANCZOS)
        al = Image.fromarray(a[:, :, 3], "L").resize((size, size), Image.LANCZOS)
        out = np.dstack([np.asarray(rgb), np.asarray(al)])
        return Image.fromarray(out, "RGBA")
    return img.resize((size, size), Image.LANCZOS)


def _place(canvas, img, col, row, channels):
    im = np.asarray(_fit(img), np.float32) / 255.0
    if im.ndim == 2:
        im = np.repeat(im[:, :, None], channels, 2)
    if im.shape[2] < channels:
        im = np.concatenate([im, np.ones(im.shape[:2] + (channels - im.shape[2],), np.float32)], -1)
    padded = np.pad(im[:, :, :channels], ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
    x, y = col * CELL, row * CELL
    canvas[y:y + CELL, x:x + CELL, :channels] = padded


def build(bid, mats, tex_dir, out_dir=None, verbose=True, name="atlas_warband"):
    """返回 {mat: (u0, v0, u1, v1)} 与写出的 4 个文件名。"""
    out_dir = out_dir or tex_dir
    mats = sorted(mats)
    assert len(mats) <= COLS * COLS, f"{bid}: 材质 {len(mats)} > 16，需要第二张图集"
    chan = {"BC": 3, "N": 3, "ORM": 4, "E": 3}
    fill = {
        "BC": np.array([0.55, 0.53, 0.50], np.float32),
        "N": np.array([0.5, 0.5, 1.0], np.float32),
        "ORM": np.array([1.0, 0.8, 0.0, 0.0], np.float32),
        "E": np.array([0.0, 0.0, 0.0], np.float32),
    }
    canv = {}
    for k, c in chan.items():
        a = np.zeros((SIZE, SIZE, c), np.float32)
        a[:] = fill[k][:c]
        canv[k] = a

    region = {}
    for i, m in enumerate(mats):
        col, row = i % COLS, i // COLS
        for k in chan:
            fp = os.path.join(tex_dir, f"{m}_{k}.png")
            if k == "E" and not os.path.exists(fp):
                img = Image.new("RGB", (CELL, CELL), (0, 0, 0))
            else:
                img = Image.open(fp).convert("RGBA" if k == "ORM" else "RGB")
            _place(canv[k], img, col, row, chan[k])
        x = col * CELL + PAD
        y = row * CELL + PAD
        region[m] = (x / SIZE, y / SIZE, (x + ART) / SIZE, (y + ART) / SIZE)

    files = {}
    for k in chan:
        fn = f"{name}_{k}.png"
        arr = np.clip(canv[k], 0, 1)
        if k == "ORM":
            Image.fromarray((arr * 255).astype(np.uint8), "RGBA").save(os.path.join(out_dir, fn))
        else:
            Image.fromarray((arr * 255).astype(np.uint8), "RGB").save(os.path.join(out_dir, fn))
        files[k] = fn
    if verbose:
        print(f"    atlas: {len(mats)} 材质 → 2048² × 4  ({', '.join(mats)})")
    return region, files
