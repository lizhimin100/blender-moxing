"""
fr_model.py —— 火载体四件套：营火 / 火把 / 火炬 / 火堆

用户要的是"分开摆放或建模，方便直接套用或利用不同的火载体模型"：
所以这不是四堆火，是**四个载体 + 同一套火**。四件的火焰都由 `dl_kit.flame()`
生成（三条外焰 + 两条中焰 + 一条芯焰），换载体不换火，比例按载体高度给：

    营火 cf   1.9 × 1.7 × 1.05   地炉（石圈 + 交叉柴 + 三脚架吊锅）
    火把 tr   0.5 × 0.5 × 2.25   木杆火把（石座 + 木杆 + 布头）
    火炬 bz   1.0 × 1.0 × 2.25   立式火盆（石座 + 三铁腿 + 盆 + 三链）
    火堆 bf   2.9 × 2.9 × 2.05   篝火（大石 + 两层原木 + 队色小旗）

明度：木三档 + 石两档 + **近黑炭** + 三段暖火；火把布头用 cloth_cream 提亮，
让"火在哪里"在 30 m 外也能一眼看到。

这四件是**道具**，不带建造动画（建造系统只服务建筑）；但它们的几何/材质/命名
与前十二座完全一致，可以直接挂在场景里，也可以拆出 `flame_*` 单独复用。

坐标：X 右、Y 前、Z 上；原点在占地中心，z = 0 地面。
"""
import math
import random

import bpy
from mathutils import Vector

import bslib as L
import dl_kit as K
from bslib import beam, box, extrude, mesh_obj, revolve, tube_band
from br_model import mirror_x


class Fire:
    """四件共用：材质表 / items / 收尾（合并 + 镜像 + UV）。"""

    PREFIX = "FR"
    flat_pref = ("flame_", "cf_ash", "bf_ash")
    # 火舌不做 CC：7 边回转体 + 倒角已经是"软"的，CC 只会把面数翻四倍
    cc_ok = ("cf_pot", "tr_head", "bz_bowl", "bz_base")

    def __init__(self, smooth, unwrap=True):
        self.smooth = smooth
        self.unwrap = unwrap
        self.items = []
        self.M = L.all_materials()

    def add(self, ob, bevel=0.006, sub=0, seg=1):
        self.items.append((ob, bevel, sub, seg))
        return ob

    def put(self, obs, bevel=0.003):
        for ob in obs:
            self.add(ob, bevel)
        return obs

    # 共用：一圈石头
    def stone_ring(self, name, r, n, s, seed, mat_a=None, mat_b=None, z=0.0):
        M = self.M
        mat_a = mat_a or M["stone_mid"]
        mat_b = mat_b or M["stone_dark"]
        rnd = random.Random(seed)
        for i in range(n):
            a = math.tau * i / n + rnd.uniform(-0.10, 0.10)
            rr = r * (0.96 + 0.08 * rnd.random())
            ss = s * (0.70 + 0.40 * rnd.random())
            self.add(box(name, (rr * math.cos(a), rr * math.sin(a),
                                z + ss * 0.34),
                         (ss, ss * 0.78, ss * 0.66),
                         mat_a if i % 2 else mat_b,
                         rot=(rnd.uniform(-0.14, 0.14), rnd.uniform(-0.14, 0.14),
                              a + rnd.uniform(-0.4, 0.4))), 0.005)

    def finalize(self, bevel=True):
        for (ob, bev, sub, seg) in self.items:
            co = ob.data.vertices
            if not len(co):
                continue
            dims = [max(v.co[i] for v in co) - min(v.co[i] for v in co) for i in range(3)]
            n = ob.name
            is_flat = n.startswith(self.flat_pref)
            if self.smooth:
                chunky = min(dims) >= 0.06 and dims[0] * dims[1] * dims[2] >= 0.004
                cc = 1 if (chunky and n.startswith(self.cc_ok)) else 0
                L.finalize(ob, bevel=min(max(bev, 0.002), 0.012), seg=1, sub=cc,
                           flat=is_flat)
            else:
                b = 0.0 if (not bevel or max(dims) < 0.35 or bev < 0.005) else bev
                L.finalize(ob, bevel=b, seg=1, sub=0, flat=True)
        objs = [it[0] for it in self.items]
        bpy.ops.object.select_all(action="DESELECT")
        for ob in objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action="DESELECT")
        out = L.join_by_material(objs, prefix=self.PREFIX)
        mirror_x(out)
        if self.unwrap:
            L.smart_uv(out)
        return out


# ── 1. 营火 ─────────────────────────────────────────────────────────────────
class Campfire(Fire):
    PREFIX = "CF"

    def build(self):
        M = self.M
        self.stone_ring("cf_stone", 0.62, 9, 0.26, seed=301)
        self.put(K.embers("cf_ember", 0.0, 0.0, 0.02, 8, 0.46, seed=302), 0.002)
        # 交叉柴：四根，两两交叉
        for i in range(4):
            a = math.tau * i / 4 + 0.30
            self.put(K.log("cf_log",
                           (0.52 * math.cos(a), 0.52 * math.sin(a), 0.20),
                           (-0.52 * math.cos(a), -0.52 * math.sin(a), 0.16),
                           0.085, M["wood_dark"], M["wood_warm"]), 0.002)
        self.put(K.flame("cf_flame", 0.0, 0.0, 0.20, 0.52, 0.24, seed=303), 0.002)
        # 三脚架 + 吊锅：营火与火堆的区别就在这一副架子
        hub = (0.02, 0.02, 1.02)
        for i in range(3):
            a = math.tau * i / 3 + 0.5
            self.add(beam("cf_tripod", (0.74 * math.cos(a), 0.74 * math.sin(a), 0.06),
                          hub, 0.055, 0.055, M["wood_dark"]), 0.002)
        self.add(revolve("cf_hub", [(0.0, 0.0), (0.075, 0.0), (0.075, 0.06)], 6,
                         (hub[0], hub[1], hub[2] - 0.03), M["iron"]), 0.002)
        self.put(K.chain("cf_chain", 0.02, 0.02, 0.86, 1.00, 0.045, M["iron"], links=3),
                 0.001)
        self.put(K.pot("cf_pot", 0.02, 0.02, 0.66, 0.16, 0.20, M["copper"]), 0.002)
        self.add(box("cf_pot_lid", (0.02, 0.02, 0.87), (0.20, 0.20, 0.035),
                     M["iron"]), 0.002)
        # 旁边一小捆备柴
        for i in range(2):
            self.put(K.log("cf_spare", (0.80, -0.35 + i * 0.14, 0.09),
                           (1.30, -0.35 + i * 0.14, 0.09),
                           0.075, M["wood_mid"], M["wood_warm"]), 0.002)
        return self


# ── 2. 火把 ─────────────────────────────────────────────────────────────────
class Torch(Fire):
    PREFIX = "TR"

    def build(self):
        M = self.M
        self.add(revolve("tr_base", [(0.0, 0.0), (0.24, 0.0), (0.24, 0.10),
                                     (0.19, 0.16), (0.0, 0.16)], 8,
                         (0, 0, 0), M["stone_mid"]), 0.006)
        self.add(box("tr_post", (0, 0, 0.98), (0.105, 0.105, 1.64), M["wood_dark"]), 0.004)
        # 铁箍两道
        for zz in (0.34, 1.42):
            self.add(box("tr_ferrule", (0, 0, zz), (0.135, 0.135, 0.06), M["iron"]), 0.002)
        # 承托盘 + 布头
        self.add(revolve("tr_pan", [(0.0, 0.0), (0.20, 0.0), (0.20, 0.04),
                                    (0.10, 0.08)], 8, (0, 0, 1.80), M["iron"]), 0.003)
        self.add(revolve("tr_head", [(0.0, 0.0), (0.11, 0.0), (0.13, 0.09),
                                     (0.11, 0.22), (0.07, 0.28)], 7,
                         (0, 0, 1.86), M["wood_mid"]), 0.004)
        self.add(tube_band("tr_head_band", (0, 0), 0.09, 0.145, 1.93, 1.97, 7,
                           M["cloth_cream"]), 0.002)
        self.add(tube_band("tr_head_band2", (0, 0), 0.08, 0.135, 2.03, 2.055, 7,
                           M["iron"]), 0.002)
        self.put(K.embers("tr_ember", 0, 0, 2.13, 4, 0.10, seed=311), 0.001)
        self.put(K.flame("tr_flame", 0, 0, 2.12, 0.40, 0.12, seed=312), 0.002)
        # 杆头一个小铁环，挂得住墙钩
        self.add(revolve("tr_ring", [(0.09, 0.0), (0.13, 0.02), (0.13, 0.07),
                                     (0.09, 0.09)], 8, (0, -0.10, 1.30), M["iron"]), 0.0)
        return self


# ── 3. 火炬（立式火盆）───────────────────────────────────────────────────────
class Brazier(Fire):
    PREFIX = "BZ"

    def build(self):
        M = self.M
        # 八角石座（两级）+ 队色箍
        self.add(revolve("bz_base", [(0.0, 0.0), (0.46, 0.0), (0.46, 0.14),
                                     (0.38, 0.24), (0.0, 0.24)], 8,
                         (0, 0, 0), M["stone_mid"]), 0.008)
        self.add(revolve("bz_base2", [(0.0, 0.0), (0.34, 0.0), (0.34, 0.10)], 8,
                         (0, 0, 0.24), M["stone_light"]), 0.004)
        self.add(tube_band("bz_team", (0, 0), 0.40, 0.47, 0.08, 0.13, 8, M["team"]),
                 0.002)
        # 三根铁腿，从座面斜到盆底
        for i in range(3):
            a = math.tau * i / 3 + 0.3
            self.add(beam("bz_leg", (0.26 * math.cos(a), 0.26 * math.sin(a), 0.30),
                          (0.30 * math.cos(a), 0.30 * math.sin(a), 1.12),
                          0.075, 0.075, M["iron"]), 0.003)
        # 盆：底 + 外壁 + 沿；里面是炭
        self.add(revolve("bz_bowl", [(0.12, 0.0), (0.30, 0.05), (0.43, 0.16),
                                     (0.46, 0.30), (0.40, 0.32), (0.34, 0.18),
                                     (0.12, 0.10)], 10, (0, 0, 1.10), M["bronze_dark"]),
                 0.005)
        self.add(tube_band("bz_rim", (0, 0), 0.40, 0.48, 1.39, 1.44, 10,
                           M["bronze"]), 0.003)
        self.put(K.embers("bz_ember", 0, 0, 1.32, 6, 0.30, seed=321), 0.002)
        self.put(K.flame("bz_flame", 0, 0, 1.34, 0.78, 0.34, seed=322), 0.002)
        # 三条吊链 + 三片小盾（队色）
        for i in range(3):
            a = math.tau * i / 3 + 0.3
            self.put(K.chain("bz_chain", 0.44 * math.cos(a), 0.44 * math.sin(a),
                             0.34, 1.36, 0.045, M["iron"], links=4), 0.001)
            self.add(box("bz_hook", (0.46 * math.cos(a), 0.46 * math.sin(a), 1.40),
                         (0.10, 0.06, 0.14), M["bronze"],
                         rot=(0, 0, a + math.pi / 2)), 0.002)
        return self


# ── 4. 火堆 ─────────────────────────────────────────────────────────────────
class Bonfire(Fire):
    PREFIX = "BF"

    def build(self):
        M = self.M
        self.stone_ring("bf_stone", 1.12, 8, 0.44, seed=331)
        self.put(K.embers("bf_ember", 0, 0, 0.03, 10, 0.86, seed=332), 0.002)
        # 两层原木：底层 3 根、上层 2 根、顶 1 根
        rnd = random.Random(333)
        for i in range(3):
            a = math.tau * i / 3 + 0.15
            self.put(K.log("bf_log",
                           (1.02 * math.cos(a), 1.02 * math.sin(a), 0.20),
                           (-1.02 * math.cos(a), -1.02 * math.sin(a), 0.20),
                           0.115, M["wood_dark"], M["wood_warm"]), 0.003)
        for i in range(2):
            a = math.tau * i / 2 + 0.55
            self.put(K.log("bf_log",
                           (0.88 * math.cos(a), 0.88 * math.sin(a), 0.44),
                           (-0.88 * math.cos(a), -0.88 * math.sin(a), 0.44),
                           0.105, M["wood_mid"], M["wood_warm"]), 0.003)
        self.put(K.log("bf_log", (-0.62, 0.12, 0.66), (0.62, -0.10, 0.68),
                       0.095, M["wood_dark"], M["wood_warm"]), 0.002)
        # 两根斜插的支架（烤东西用）
        for (sx, sy) in ((-1.05, 0.55), (1.05, -0.55)):
            self.add(beam("bf_stake", (sx, sy, 0.10), (sx * 0.35, sy * 0.35, 1.45),
                          0.075, 0.075, M["wood_dark"]), 0.003)
        self.add(beam("bf_bar", (-0.42, 0.22, 1.40), (0.42, -0.22, 1.40),
                      0.05, 0.05, M["iron"]), 0.002)
        self.put(K.flame("bf_flame", 0, 0, 0.62, 1.30, 0.52, seed=334), 0.003)
        # 队色小旗：插在火堆边（"这堆火是我们的"）
        self.add(box("bf_pole", (1.62, 1.28, 0.66), (0.05, 0.05, 1.32),
                     M["wood_dark"]), 0.002)
        prof = [(-0.26, 0.0), (0.26, 0.0), (0.08, -0.20), (-0.26, -0.38)]
        fl = extrude("bf_flag", prof, "Y", 0.026, (0, 0), M["team"])
        fl.location = (1.62, 1.31, 1.30)
        self.add(fl, 0.002)
        return self


BUILDERS = {"营火": Campfire, "火把": Torch, "火炬": Brazier, "火堆": Bonfire}


def build(name, smooth=True, unwrap=True, bevel=True):
    m = BUILDERS[name](smooth, unwrap).build()
    objs = m.finalize(bevel=bevel)
    return objs, L.stats(objs)


# ── 兼容既有导出管线（export_mobile 里 `module.Model(False).build()`）──────
import types


def module_for(name):
    """把某一件火载体包成"像 *_model.py 一样"的模块对象。

    export_mobile / dl_export 都是按 `module.Model(smooth, unwrap).build()` 调用的，
    这里给每件火一个只带 Model 的命名空间，不必为四件小道具各写一个文件。
    """
    class _M:
        _target = name

        def __new__(cls, smooth, unwrap=True):
            return BUILDERS[cls._target](smooth, unwrap)

    return types.SimpleNamespace(Model=_M, NAME=name)
