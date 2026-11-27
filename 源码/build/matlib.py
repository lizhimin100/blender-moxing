"""
matlib.py —— 程序化 PBR 材质库（纯 numpy / PIL，无外部素材）

每套材质输出：
  <name>_BC.png    BaseColor  (RGB)           —— 染色区为近白灰阶，便于玩家色相乘
  <name>_N.png     Normal     (RGB, +Y up)    —— 由高度场求导
  <name>_ORM.png   Occlusion(R) / Roughness(G) / Metallic(B) / TeamMask-TC1(A)
  <name>_E.png     Emissive   (RGB)           —— TC2 副色 / 描边 / 自发光遮罩

全部纹理严格无缝平铺（周期噪声 + 整数分割的砌筑/木板栅格）。
"""
import os
import numpy as np
from PIL import Image

S = 512
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "warband", "textures")


# ---------------------------------------------------------------- 基础工具
def rng(seed):
    return np.random.default_rng(seed)


def pnoise(h, w, cells, r):
    """周期 value noise：cells 必须整除边界，保证无缝。"""
    g = r.random((cells, cells)).astype(np.float32)
    ys = np.arange(h) * cells / h
    xs = np.arange(w) * cells / w
    y0 = np.floor(ys).astype(int) % cells
    x0 = np.floor(xs).astype(int) % cells
    y1 = (y0 + 1) % cells
    x1 = (x0 + 1) % cells
    fy = (ys - np.floor(ys))[:, None].astype(np.float32)
    fx = (xs - np.floor(xs))[None, :].astype(np.float32)
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = g[np.ix_(y0, x0)]
    b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]
    d = g[np.ix_(y1, x1)]
    return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy


def fbm(h, w, base, octaves, r, gain=0.5):
    out = np.zeros((h, w), np.float32)
    amp, tot, c = 1.0, 0.0, base
    for _ in range(octaves):
        out += amp * pnoise(h, w, c, r)
        tot += amp
        amp *= gain
        c = min(c * 2, min(h, w))
    return out / tot


def smooth(x):
    return x * x * (3 - 2 * x)


def normal_from_height(hm, strength=2.0):
    dx = (np.roll(hm, -1, 1) - np.roll(hm, 1, 1)) * strength
    dy = (np.roll(hm, -1, 0) - np.roll(hm, 1, 0)) * strength
    n = np.stack([-dx, -dy, np.ones_like(hm)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-8
    return n * 0.5 + 0.5


def ao_from_height(hm, radius=12, strength=1.6):
    k = np.ones(radius, np.float32) / radius
    blur = hm.copy()
    for _ in range(3):
        blur = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, blur)
        blur = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, blur)
    ao = 1.0 - np.clip((blur - hm) * strength, 0.0, 1.0)
    return np.clip(ao, 0.35, 1.0)


def srgb(hexstr):
    h = hexstr.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


# v2 色卡：贴图均值必须落在这些值附近，否则整包会偏灰（见 docs/prompt-spec-v2.md §1.3）
PALETTE = {
    "stone": "#8D949B",
    "stone_dark": "#4B5057",
    "plaster": "#CEC3AE",
    "wood": "#6A4A33",
    "wood_dark": "#4B3627",
    "shingle": "#5F5446",
    "thatch": "#A98A52",
    "steel": "#9AA0A0",
    "steel_dark": "#5F666B",
    "gold": "#C8A02C",
}


def calibrate(name, bc, iters=2):
    """把 BaseColor 的均值拉到色卡，保留原有的明暗对比。

    只做整体增益，不改图案；两轮处理可以吃掉高光截断带来的残差。
    """
    target = PALETTE.get(name)
    if target is None:
        return bc
    tgt = srgb(target)
    out = np.array(bc, np.float32)
    for _ in range(iters):
        cur = out.reshape(-1, 3).mean(0)
        gain = np.clip(tgt / np.maximum(cur, 1e-4), 0.55, 2.2)
        out = np.clip(out * gain, 0.0, 1.0)
    return out


def save(name, bc, nrm, orm, ems=None):
    os.makedirs(OUT, exist_ok=True)
    bc = calibrate(name, bc)
    Image.fromarray((np.clip(bc, 0, 1) * 255).astype(np.uint8), "RGB").save(f"{OUT}/{name}_BC.png")
    Image.fromarray((np.clip(nrm, 0, 1) * 255).astype(np.uint8), "RGB").save(f"{OUT}/{name}_N.png")
    Image.fromarray((np.clip(orm, 0, 1) * 255).astype(np.uint8), "RGBA").save(f"{OUT}/{name}_ORM.png")
    if ems is not None:
        Image.fromarray((np.clip(ems, 0, 1) * 255).astype(np.uint8), "RGB").save(f"{OUT}/{name}_E.png")


def pack(height, color, rough, metal, mask, ems=None, ao_str=1.6):
    h, w = height.shape
    h_w = (h, w)
    c = np.asarray(color, np.float32)
    if c.ndim == 1:
        c = c.reshape(1, 1, 3)
    ao = ao_from_height(height, strength=ao_str)
    bc = c * (0.55 + 0.45 * height)[:, :, None]
    bc = bc * (0.7 + 0.3 * ao)[:, :, None]
    nrm = normal_from_height(height)
    rough = np.broadcast_to(np.asarray(rough, np.float32), h_w)
    metal = np.broadcast_to(np.asarray(metal, np.float32), h_w)
    mask = np.broadcast_to(np.asarray(mask, np.float32), h_w)
    orm = np.stack([
        ao,
        np.clip(rough, 0, 1),
        np.clip(metal, 0, 1),
        np.clip(mask, 0, 1),
    ], -1)
    return bc, nrm, orm, ems


# ---------------------------------------------------------------- 材质定义
def m_steel(seed=11):
    r = rng(seed)
    streak = fbm(S, S, 2, 4, r)
    brush = np.sin(np.arange(S, dtype=np.float32)[:, None] * 2.9 + streak * 9.0) * 0.5 + 0.5
    h = 0.55 + 0.22 * streak + 0.14 * brush
    # 划痕：稀疏细长条
    scr = np.zeros((S, S), np.float32)
    for _ in range(90):
        y = r.integers(0, S)
        x = r.integers(0, S)
        ln = r.integers(20, 160)
        xx = (np.arange(ln) + x) % S
        s = 0.6 + 0.4 * np.sin(np.arange(ln) / ln * np.pi)
        scr[y, xx] = np.maximum(scr[y, xx], s)
        scr[(y + 1) % S, xx] = np.maximum(scr[(y + 1) % S, xx], s * 0.5)
    h = h + scr * 0.18 - scr * 0.05
    color = srgb("#8d949b")
    # 划痕与凹处轻微氧化（偏暖、粗糙）
    ox = np.clip(scr * 0.9 + (1 - streak) * 0.25, 0, 1)
    color = color * (1 - ox[:, :, None] * 0.25) + srgb("#6b5a49") * (ox[:, :, None] * 0.25)
    rough = 0.30 + 0.22 * (1 - streak) + ox * 0.18
    return pack(h, color, rough, np.full((S, S), 0.92), np.zeros((S, S)))


def m_steel_dark(seed=12):
    r = rng(seed)
    dent = fbm(S, S, 4, 4, r)
    h = 0.5 + 0.35 * dent
    color = srgb("#4b5057") * (0.8 + 0.4 * dent)[:, :, None]
    rough = 0.42 + 0.28 * (1 - dent)
    return pack(h, color, rough, np.full((S, S), 0.88), np.zeros((S, S)))


def m_gold(seed=13):
    r = rng(seed)
    n = fbm(S, S, 3, 4, r)
    h = 0.6 + 0.3 * n
    color = srgb("#c8a02c") * (0.82 + 0.3 * n)[:, :, None]
    rough = 0.22 + 0.16 * (1 - n)
    return pack(h, color, rough, np.full((S, S), 1.0), np.zeros((S, S)))


def _weave(r, period=6, jitter=0.0):
    ys = np.arange(S)[:, None]
    xs = np.arange(S)[None, :]
    warp = np.sin(xs * np.pi * 2 / period) * 0.5 + 0.5
    weft = np.sin(ys * np.pi * 2 / period) * 0.5 + 0.5
    checker = ((xs // period + ys // period) % 2).astype(np.float32)
    base = warp * checker + weft * (1 - checker)
    return base


def m_cloth_team(seed=14):
    r = rng(seed)
    w = _weave(r)
    fuzz = fbm(S, S, 24, 3, r)
    h = 0.45 + 0.35 * w + 0.2 * fuzz
    # 近白灰阶（让玩家色相乘后仍保有编织明暗）
    color = np.stack([1, 1, 1], -1) * (0.80 + 0.20 * (0.6 * w + 0.4 * fuzz))[:, :, None]
    rough = 0.80 + 0.12 * (1 - w)
    mask = np.ones((S, S), np.float32)
    return pack(h, color.astype(np.float32), rough, np.zeros((S, S)), mask, ao_str=1.0)


def m_cloth_linen(seed=15):
    r = rng(seed)
    w = _weave(r, 7)
    fuzz = fbm(S, S, 20, 3, r)
    h = 0.42 + 0.38 * w + 0.2 * fuzz
    color = srgb("#b3a487") * (0.82 + 0.24 * (0.5 * w + 0.5 * fuzz))[:, :, None]
    # 污渍
    dirt = np.clip(fbm(S, S, 6, 3, r) - 0.45, 0, 1) * 0.6
    color = color * (1 - dirt[:, :, None] * 0.35)
    rough = 0.82 + 0.12 * (1 - w)
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=1.0)


def m_cloth_wool(seed=16):
    r = rng(seed)
    w = _weave(r, 9)
    fuzz = fbm(S, S, 30, 4, r)
    h = 0.4 + 0.35 * w + 0.25 * fuzz
    color = srgb("#6f5f4c") * (0.78 + 0.3 * (0.5 * w + 0.5 * fuzz))[:, :, None]
    rough = 0.86 + 0.1 * (1 - w)
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=1.0)


def m_leather(seed=17):
    r = rng(seed)
    grain = fbm(S, S, 26, 4, r)
    cell = fbm(S, S, 8, 3, r)
    h = 0.45 + 0.3 * grain + 0.2 * cell
    color = srgb("#6a4a33") * (0.66 + 0.52 * (0.6 * grain + 0.4 * cell))[:, :, None]
    # 缝线：每隔 64px 一排
    stitch = np.zeros((S, S), np.float32)
    for y in (64, 192, 320, 448):
        stitch[(np.arange(S) % 20) < 10, y] = 1.0
        h[y - 1:y + 2, :] -= 0.18
    color = color * (1 - stitch[:, :, None] * 0.0) + srgb("#d8c9a8") * stitch[:, :, None] * 0.55
    rough = 0.62 + 0.2 * (1 - grain)
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)))


def m_wood(seed=18):
    r = rng(seed)
    planks = 4
    ys = np.arange(S)[:, None].astype(np.float32)
    xs = np.arange(S)[None, :].astype(np.float32)
    grain = fbm(S, S, 3, 5, r)
    # 年轮沿 y 方向拉长
    rings = np.sin((xs * 0.9 + grain * 26.0)) * 0.5 + 0.5
    pw = S / planks
    px = (xs % pw) / pw
    groove = np.clip((1 - np.abs(px - 0.5) * 2) * 6 - 4.2, 0, 1)      # 板缝
    ph = (ys // pw).astype(np.int32)                                   # 每块板偏移
    rings = np.sin((xs / pw * 6.283 + grain * 18.0 + ph * 1.7)) * 0.5 + 0.5
    cracks = np.zeros((S, S), np.float32)
    for _ in range(26):
        cx = int(r.integers(0, S))
        y0 = int(r.integers(0, S))
        ln = int(r.integers(40, 220))
        for i in range(ln):
            yy = (y0 + i) % S
            xx = int(cx + np.sin(i * 0.12) * 3) % S
            cracks[yy, xx] = 1.0
    h = 0.45 + 0.3 * (0.5 * rings + 0.5 * grain) - groove * 0.45 - cracks * 0.3
    color = srgb("#8b6238") * (0.74 + 0.36 * (0.55 * rings + 0.45 * grain))[:, :, None]
    color = color * (1 - groove[:, :, None] * 0.55) * (1 - cracks[:, :, None] * 0.35)
    rough = 0.66 + 0.2 * (1 - rings) + groove * 0.1
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=2.0)


def m_wood_dark(seed=19):
    bc, n, o, e = m_wood(seed)
    bc = bc * srgb("#8a7a68") / srgb("#8b6238") * 0.78
    return bc, n, o, e


def m_stone(seed=20, dark=False):
    r = rng(seed)
    rows, cols = 4, 3
    ys = np.arange(S)[:, None].astype(np.float32)
    xs = np.arange(S)[None, :].astype(np.float32)
    ry = ys / (S / rows)
    row = np.floor(ry).astype(np.int32)
    fy = ry - row
    off = (row % 2) * 0.5
    rx = xs / (S / cols) + off
    col = np.floor(rx).astype(np.int32)
    fx = rx - col
    joint_w = 0.035
    jx = np.clip(np.minimum(fx, 1 - fx) / joint_w, 0, 1)
    jy = np.clip(np.minimum(fy, 1 - fy) / (joint_w * 1.5), 0, 1)
    jointmask = 1.0 - np.minimum(jx, jy)          # 1 = 灰缝中心
    n1 = fbm(S, S, 32, 4, r)
    n2 = fbm(S, S, 8, 3, r)
    # 每块石头独立的明度
    bid = (row * 31 + col * 17) % 97
    bvar = ((bid / 97.0) - 0.5) * 0.24
    h = 0.55 + 0.18 * n2 + 0.12 * n1 + bvar - jointmask * 0.55
    base = srgb("#5f666b") if dark else srgb("#9aa0a0")
    color = base * (0.86 + 0.28 * (0.6 * n2 + 0.4 * n1) + bvar)[:, :, None]
    color = color * (1 - jointmask[:, :, None] * 0.68)
    # 大尺度污渍：让整面墙不是均匀一片
    grime = np.clip(fbm(S, S, 3, 4, r) - 0.42, 0, 1) * 1.5
    color = color * (1 - grime[:, :, None] * 0.18)
    # 苔痕 / 风化
    moss = np.clip(fbm(S, S, 5, 4, r) - 0.58, 0, 1) * 2.0
    color = color * (1 - moss[:, :, None] * 0.35) + srgb("#48513a") * moss[:, :, None] * 0.35
    rough = 0.72 + 0.18 * (1 - n1) + jointmask * 0.12
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=2.2)


def m_stone_dark(seed=21):
    return m_stone(seed, dark=True)


def m_thatch(seed=22):
    r = rng(seed)
    ys = np.arange(S)[:, None].astype(np.float32)
    xs = np.arange(S)[None, :].astype(np.float32)
    strand = np.sin(xs * 0.55 + fbm(S, S, 40, 3, r) * 14) * 0.5 + 0.5
    bundles = fbm(S, S, 6, 3, r)
    h = 0.4 + 0.35 * strand + 0.25 * bundles
    color = srgb("#a98a52") * (0.7 + 0.45 * (0.55 * strand + 0.45 * bundles))[:, :, None]
    rough = 0.86 + 0.1 * (1 - strand)
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=2.2)


def m_shingle(seed=27):
    r = rng(seed)
    rows = 8
    ys = np.arange(S)[:, None].astype(np.float32)
    xs = np.arange(S)[None, :].astype(np.float32)
    ry = ys / (S / rows)
    row = np.floor(ry).astype(np.int32)
    fy = ry - row
    off = (row % 2) * 0.5
    rx = xs / (S / 8) + off
    col = np.floor(rx).astype(np.int32)
    fx = rx - col
    edge = np.clip(np.minimum(fx, 1 - fx) * 9, 0, 1) * np.clip(fy * 3.2, 0, 1)
    n1 = fbm(S, S, 26, 4, r)
    n2 = fbm(S, S, 7, 3, r)
    var = (((row * 13 + col * 29) % 71) / 71.0 - 0.5) * 0.22
    h = 0.55 + 0.20 * n1 + 0.12 * n2 + var - (1 - edge) * 0.35
    color = srgb("#5f5446") * (0.80 + 0.34 * (0.6 * n1 + 0.4 * n2) + var)[:, :, None]
    color = color * (1 - (1 - edge)[:, :, None] * 0.45)
    rough = 0.74 + 0.18 * (1 - n1)
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=2.0)


def m_window(seed=28):
    r = rng(seed)
    n = fbm(S, S, 12, 3, r)
    h = 0.5 + 0.25 * n
    color = srgb("#1d2226") * (0.9 + 0.2 * n)[:, :, None]
    rough = 0.35 + 0.2 * (1 - n)
    # 冷色室内光：与炉膛的橙形成冷暖对比（v2 色卡 window = #8FE6FF）
    ems = np.stack([srgb("#8fe6ff")] * (S * S), 0).reshape(S, S, 3) * (0.55 + 0.45 * n)[:, :, None]
    bc, nrm, orm, _ = pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)))
    return bc, nrm, orm, ems


def m_ember(seed=29):
    r = rng(seed)
    n = fbm(S, S, 7, 4, r)
    cracks = np.clip(np.sin(n * 22.0), 0, 1) ** 5
    h = 0.5 + 0.3 * n
    color = srgb("#20140d") * (0.8 + 0.5 * n)[:, :, None] + srgb("#8c3a10") * cracks[:, :, None] * 0.5
    rough = 0.85
    ems = np.stack([srgb("#ff8a2b")] * (S * S), 0).reshape(S, S, 3) * (0.45 + 0.75 * cracks)[:, :, None]
    bc, nrm, orm, _ = pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)))
    return bc, nrm, orm, ems


def m_plaster(seed=26):
    r = rng(seed)
    n1 = fbm(S, S, 9, 4, r)
    n2 = fbm(S, S, 40, 3, r)
    h = 0.5 + 0.30 * n1 + 0.12 * n2
    color = srgb("#cec3ae") * (0.86 + 0.20 * n1 + 0.06 * n2)[:, :, None]
    # 雨渍与剥落
    stain = np.clip(fbm(S, S, 5, 4, r) - 0.55, 0, 1) * 2.4
    color = color * (1 - stain[:, :, None] * 0.22)
    rough = 0.86 + 0.10 * (1 - n2)
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=1.4)


def m_skin(seed=23):
    r = rng(seed)
    n = fbm(S, S, 10, 3, r)
    h = 0.5 + 0.35 * n
    color = srgb("#c49a78") * (0.9 + 0.16 * n)[:, :, None]
    rough = 0.58 + 0.16 * (1 - n)
    return pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)), ao_str=0.8)


def m_crystal(seed=24):
    r = rng(seed)
    n = fbm(S, S, 4, 3, r)
    h = 0.5 + 0.4 * n
    color = srgb("#63c8f0") * (0.7 + 0.5 * n)[:, :, None]
    rough = 0.10 + 0.12 * (1 - n)
    ems = np.stack([srgb("#8fe6ff")] * (S * S), 0).reshape(S, S, 3) * (0.4 + 0.60 * n)[:, :, None]
    bc, nrm, orm, _ = pack(h, color, rough, np.zeros((S, S)), np.zeros((S, S)))
    return bc, nrm, orm, ems


def m_emblem(seed=25):
    r = rng(seed)
    n = fbm(S, S, 16, 3, r)
    h = 0.55 + 0.3 * n
    color = np.ones((S, S, 3), np.float32) * (0.85 + 0.15 * n)[:, :, None]
    # 徽记纹样：菱形 + 竖向剑形，作为 TC2 自发光遮罩
    ys = np.arange(S)[:, None].astype(np.float32) / S * 2 - 1
    xs = np.arange(S)[None, :].astype(np.float32) / S * 2 - 1
    diamond = np.clip(1.0 - (np.abs(xs) + np.abs(ys) * 1.0) * 3.0, 0, 1)
    bar = ((np.abs(xs) < 0.12) & (np.abs(ys) < 0.62)).astype(np.float32)
    cross = ((np.abs(ys) < 0.10) & (np.abs(xs) < 0.45)).astype(np.float32)
    em = np.clip(diamond * 0.9 + bar * 0.25 + cross * 0.2, 0, 1)
    ems = np.stack([em, em, em], -1) * 0.9
    rough = 0.6 + 0.2 * (1 - n)
    bc, nrm, orm, _ = pack(h, color, rough, np.zeros((S, S)), np.ones((S, S)), ao_str=0.9)
    return bc, nrm, orm, ems


# name -> (生成函数, 平铺尺度(米/一次重复), 说明)
MATERIALS = {
    "steel":       (m_steel,       0.75),
    "steel_dark":  (m_steel_dark,  0.75),
    "gold":        (m_gold,        0.45),
    "cloth_team":  (m_cloth_team,  0.42),
    "cloth_linen": (m_cloth_linen, 0.45),
    "cloth_wool":  (m_cloth_wool,  0.50),
    "leather":     (m_leather,     0.40),
    "wood":        (m_wood,        1.00),
    "wood_dark":   (m_wood_dark,   1.00),
    "stone":       (m_stone,       1.30),
    "stone_dark":  (m_stone_dark,  1.30),
    "thatch":      (m_thatch,      0.90),
    "skin":        (m_skin,        0.55),
    "plaster":     (m_plaster,     0.85),
    "ember":       (m_ember,       0.70),
    "shingle":     (m_shingle,     0.95),
    "window":      (m_window,      0.60),
    "crystal":     (m_crystal,     0.35),
    "emblem":      (m_emblem,      0.55),
}


def build_all(force=False):
    os.makedirs(OUT, exist_ok=True)
    made = []
    for name, (fn, tile) in MATERIALS.items():
        p = f"{OUT}/{name}_BC.png"
        if os.path.exists(p) and not force:
            made.append(name)
            continue
        res = fn()
        bc, nrm, orm = res[0], res[1], res[2]
        ems = res[3] if len(res) > 3 else None
        save(name, bc, nrm, orm, ems)
        made.append(name)
        print(f"  [tex] {name}")
    return made


if __name__ == "__main__":
    import sys
    build_all(force="--force" in sys.argv)
    print("textures ->", os.path.abspath(OUT))
