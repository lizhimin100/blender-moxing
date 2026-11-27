"""gnoll_kit.py —— 豺狼人共用体（战士 / 斥候）。

设计目标（对应《建模交接手册》§6）：
  * 种族特征：**大圆耳 + 长吻 + 下颌獠牙 + 颈鬃 + 驼背 + 趾行腿 + 粗尾**。
  * 两兵种差异化不靠整体缩放，靠**比例 + 三个高度带的识别点**：
      战士：鬃冠 / 巨型左肩骨刺 / 拖链流星锤；
      斥候：双羽 / 斜背标枪 + 短披 / 宽刃猎刀。
  * 硬表面只用倒角，有机体只用 Catmull-Clark。
"""
import math

import bpy
from mathutils import Vector

import unitkit as K


def V(B, name):
    return Vector(B[name])


def zline(B, name):
    return B[name][2]


def box_limb(name, p0, p1, w0, d0, w1, d1, mid=0.5):
    """沿骨轴的**方块肢体**（4 点截面，不是圆管）—— 方块人风格。"""
    p0v, x, y, z = K.frame(p0, p1)
    L = (Vector(p1) - p0v).length
    rows = []
    for (t, ww, dd) in ((0.0, w0, d0), (mid, (w0 + w1) * 0.5 * 1.04, (d0 + d1) * 0.5 * 1.04),
                        (1.0, w1, d1)):
        c = p0v + z * (L * t)
        rows.append([c - x * ww * 0.5 - y * dd * 0.5, c + x * ww * 0.5 - y * dd * 0.5,
                     c + x * ww * 0.5 + y * dd * 0.5, c - x * ww * 0.5 + y * dd * 0.5])
    return K.loft(name, rows, True)


def box_ear(name, root, tip, w0, w1, t0, t1, bend=0.0):
    """方块兽耳：根宽 → 中宽 → 圆钝尖，4 点截面。"""
    p0v, x, y, z = K.frame(root, tip)
    L = (Vector(tip) - p0v).length
    rows = []
    for (t, ww, tt) in ((0.0, w0, t0), (0.55, w1, t1), (0.88, w1 * 0.62, t1 * 0.62),
                        (1.0, w1 * 0.34, t1 * 0.34)):
        c = p0v + z * (L * t) + x * (bend * math.sin(math.pi * t))
        rows.append([c - x * ww * 0.5 - y * tt * 0.5, c + x * ww * 0.5 - y * tt * 0.5,
                     c + x * ww * 0.5 + y * tt * 0.5, c - x * ww * 0.5 + y * tt * 0.5])
    return K.loft(name, rows, True)


class GnollBody:
    def __init__(self, u, B, cfg):
        self.u = u
        self.B = B
        self.cfg = cfg

    def blimb(self, name, p0, p1, r0, r1, bone, mat, key, depth=0.94):
        return self.u.add(box_limb(name, p0, p1, r0 * 2.0, r0 * 2.0 * depth,
                                   r1 * 2.0, r1 * 2.0 * depth),
                          bone, mat, bevel=0.0, seg=1, sub=0, smooth=False, key=key)


    # ── 躯干 ────────────────────────────────────────────────────────────────
    def torso(self):
        u, c = self.u, self.cfg
        segs = (("torso_low", "spine.02", c["torso_low"], "fur"),
                ("torso_high", "chest", c["torso_high"], "fur"),
                ("belly", "spine.01", c["belly"], "fur_dark"),
                ("pelvis_b", "pelvis", c["pelvis"], "fur_dark"))
        for nm, bone, stations, key in segs:
            rows = []
            for (z, w, d, y) in stations:
                rows.append([(x, yy + y, z) for (x, yy) in K.poly_rect(w, d, 0.040)])
            u.loft(c["name"] + "_" + nm, rows, bone, "fur", bevel=0.0, seg=1, sub=0,
                   key=key, smooth=False)

    # ── 腿 ──────────────────────────────────────────────────────────────────
    def legs(self):
        u, B, c = self.u, self.B, self.cfg
        for s, side in ((1, "R"), (-1, "L")):
            th = V(B, "thigh." + side)
            kn = V(B, "shin." + side)
            ho = V(B, "foot." + side)
            ba = V(B, "toe." + side)
            tip = ba + Vector((0.0, 0.289, -0.071)).normalized() * c["toe_len"]
            # 大腿（粗，根部埋进胯）
            self.blimb("thigh_" + side, th + Vector((0, 0, 0.04)), kn,
                       c["thigh_r"], c["thigh_r"] * 0.80, "thigh." + side, "fur", "fur")
            # 小腿：膝 → 跗关节（向后收）
            self.blimb("shin_" + side, kn, ho, c["shin_r"], c["shin_r"] * 0.74,
                       "shin." + side, "fur", "fur_dark")
            # 跖骨：跗关节 → 脚掌
            self.blimb("pastern_" + side, ho, ba, c["shin_r"] * 0.78, c["shin_r"] * 0.64,
                       "foot." + side, "fur", "fur_dark")
            # 脚掌：平底（不能是圆管 —— 圆管会把脚压到地下）
            rows = []
            for (yy, z0, z1, ww) in (
                    (ba.y - 0.015, 0.008, 0.105, c["paw_w"]),
                    (ba.y + 0.10, 0.002, 0.090, c["paw_w"] * 1.02),
                    (tip.y - 0.03, 0.000, 0.060, c["paw_w"] * 0.86),
                    (tip.y + 0.02, 0.000, 0.038, c["paw_w"] * 0.62)):
                rows.append([(ba.x - ww * 0.5, yy, z0), (ba.x + ww * 0.5, yy, z0),
                             (ba.x + ww * 0.5, yy, z1), (ba.x - ww * 0.5, yy, z1)])
            u.loft("paw_" + side, rows, "toe." + side, "fur", bevel=0.004, sub=0,
                   key="fur_dark", smooth=False)
            # 爪：三前一后
            fwd = (tip - ba).normalized()
            sidev = Vector((1, 0, 0))
            for i, (dx, dz, ln) in enumerate(((-0.055, 0.0, 0.075), (0.0, 0.0, 0.085), (0.055, 0.0, 0.075))):
                base = tip + sidev * dx + Vector((0, 0, 0.014 + dz))
                claw_tip = base + fwd * ln + Vector((0, 0, -0.008))
                if claw_tip.z < 0.005:
                    claw_tip.z = 0.005
                u.claw("claw_%s%d" % (side, i), base, claw_tip,
                       0.030, 0.026, "toe." + side, "bone", key="bone")
            if c["detail"]:
                # 后爪
                u.claw("claw_%s_b" % side, ho + Vector((0, 0.02, 0.01)),
                       ho + Vector((0, -0.055, -0.02)), 0.024, 0.020, "foot." + side, "bone",
                       key="bone")
                # 膝毛簇
                u.plate("tuft_knee_" + side,
                        [(-0.035, 0.0), (0.035, 0.0), (0.020, 0.09), (-0.015, 0.10)],
                        "thigh." + side, "fur_pale", axis="X", thickness=0.020,
                        offset=kn.x + s * 0.02, bevel=0.002, key="fur_pale",
                        uv_origin=(kn.y, kn.z - 0.06))

    # ── 臂 ──────────────────────────────────────────────────────────────────
    def arms(self):
        u, B, c = self.u, self.B, self.cfg
        for s, side in ((1, "R"), (-1, "L")):
            sh = V(B, "upperarm." + side)
            el = V(B, "forearm." + side)
            wr = V(B, "hand." + side)
            self.blimb("upperarm_" + side, sh, el, c["arm_r"], c["arm_r"] * 0.84,
                       "upperarm." + side, "fur", "fur")
            self.blimb("forearm_" + side, el, wr, c["arm_r"] * 0.88, c["arm_r"] * 0.70,
                       "forearm." + side, "fur", "fur_dark")
            # 肘毛簇
            if c["detail"]:
                u.plate("tuft_elbow_" + side,
                        [(-0.030, 0.0), (0.030, 0.0), (0.016, 0.085), (-0.012, 0.095)],
                        "forearm." + side, "fur_pale", axis="X", thickness=0.018,
                        offset=el.x + s * 0.01, bevel=0.002, key="fur_pale",
                        uv_origin=(el.y, el.z - 0.04))
            # 手：拳 + 三爪
            hand_len = c["hand_len"]
            fwd = (wr - el).normalized()
            palm = wr + fwd * hand_len * 0.35
            u.box("palm_" + side, palm, (c["hand_w"], hand_len, c["hand_h"]),
                  "hand." + side, "fur_dark", bevel=0.010, rot=(0, 0, 0))
            if c["detail"]:
                for i in range(3):
                    dx = (i - 1) * 0.038
                    base = palm + Vector((dx, hand_len * 0.42, 0.0))
                    u.claw("hclaw_%s%d" % (side, i), base, base + fwd * 0.060 + Vector((0, 0, -0.02)),
                           0.024, 0.020, "hand." + side, "bone", key="bone")

    # ── 尾 ──────────────────────────────────────────────────────────────────
    def tail(self):
        u, B, c = self.u, self.B, self.cfg
        pts = [V(B, "tail.01"), V(B, "tail.02"), V(B, "tail.03")]
        tip = pts[-1] + (pts[-1] - pts[-2]).normalized() * c["tail_tip"]
        segs = [(pts[0], pts[1], "tail.01"), (pts[1], pts[2], "tail.02"), (pts[2], tip, "tail.03")]
        for i, (a, b, bone) in enumerate(segs):
            r0 = c["tail_r"] * (1.0 - i * 0.22)
            r1 = c["tail_r"] * (0.78 - i * 0.22)
            self.blimb("tail_%d" % i, a, b, r0, r1, bone, "fur",
                       "fur" if i < 2 else "fur_dark", depth=0.90)
        if c["detail"]:
            # 尾尖白毛
            self.blimb("tail_tip", pts[2] + (tip - pts[2]) * 0.55, tip,
                       c["tail_r"] * 0.42, c["tail_r"] * 0.20, "tail.03", "fur_pale", "fur_pale")

    # ── 头 ──────────────────────────────────────────────────────────────────
    def head(self):
        u, B, c = self.u, self.B, self.cfg
        hb = V(B, "head")
        nb = V(B, "neck.01")
        # 颈：从胸口斜上前，粗
        self.blimb("neck", nb + Vector((0, -0.02, -0.04)), hb + Vector((0, -0.01, 0.04)),
                   c["neck_r"], c["neck_r"] * 0.92, "neck.01", "fur", "fur")
        # 颅 + 吻：一条连续的 Y 向放样（不是"方头 + 方管"）
        rows = []
        for (y, z, w, h) in c["head_sections"]:
            rows.append([(x, y, z + zz) for (x, zz) in K.poly_rect(w, h, 0.030)])
        u.loft("skull_muzzle", rows, "head", "fur", bevel=0.0, seg=1, sub=0,
               key=c["skull_key"], smooth=False)
        # 下颌：一条薄放样，挂 jaw 骨
        rows = []
        for (y, z, w, h) in c["jaw_sections"]:
            rows.append([(x, y, z + zz) for (x, zz) in K.poly_rect(w, h, 0.022)])
        u.loft("jaw", rows, "jaw", "fur_light", bevel=0.0, seg=1, sub=0, smooth=False)
        jb = V(B, "jaw")
        # 口线
        for s in (1, -1):
            u.box("mouth_line_%d" % s, (s * 0.074, jb.y + 0.090, jb.z + 0.012),
                  (0.014, 0.200, 0.010), "head", "dark", bevel=0.001)
        # 鼻头 + 鼻梁皱纹
        nose = c["nose"]
        u.box("nose", nose[0], nose[1], "head", "dark", bevel=0.006)
        nc = c["nose"][0]
        for i, yy in enumerate((nc[1] - 0.065, nc[1] - 0.035)):
            u.box("nose_wrinkle_%d" % i, (0, yy, nc[2] - 0.002), (0.080, 0.018, 0.010),
                  "head", "fur_shadow", bevel=0.001)
        # 眼：斜切的暗眶 + 琥珀点（不是一条墨镜）
        for s in (1, -1):
            e = c["eye"]
            u.box("eye_socket_%d" % s, (s * e[0], e[1], e[2]), (0.068, 0.026, 0.050),
                  "head", "fur_shadow", bevel=0.003, rot=(0, 0, -s * 0.18))
            u.box("eye_%d" % s, (s * e[0], e[1] + 0.014, e[2] + 0.002), (0.036, 0.010, 0.020),
                  "head", "M_eye", bevel=0.001, rot=(0, 0, -s * 0.18))
            u.box("brow_%d" % s, (s * (e[0] + 0.008), e[1] + 0.012, e[2] + 0.038),
                  (0.082, 0.030, 0.020), "head", "fur_dark", bevel=0.003,
                  rot=(0, 0, -s * 0.12))
        # 上/下獠牙：大口角，正面能看到
        for s in (1, -1):
            ub = Vector((s * 0.080, jb.y + 0.150, jb.z + 0.028))
            u.claw("fang_up_%d" % s, ub, ub + Vector((0, 0.004, -0.058)), 0.026, 0.022,
                   "head", "bone", key="bone")
            lb = Vector((s * 0.060, jb.y + 0.140, jb.z - 0.002))
            u.claw("fang_lo_%d" % s, lb, lb + Vector((0, 0.004, 0.056)), 0.024, 0.020,
                   "jaw", "bone", key="bone")
        # 大圆耳：根埋在颅里，往外上方斜出（不是兔耳）
        for s, side in ((1, "R"), (-1, "L")):
            er = V(B, "ear." + side)
            # 耳根埋进颅骨里，让耳朵从毛里长出来（不要在外面留方块）
            root = Vector((er.x, er.y - 0.015, er.z - 0.080))
            tip = root + Vector((s * c["ear_out"], -0.045, c["ear_up"]))
            u.add(box_ear("ear_" + side, root, tip, c["ear_w"] * 0.55, c["ear_w"],
                          c["ear_t"], c["ear_t"] * 0.72, bend=s * 0.015),
                  "ear." + side, "fur", 0.0, 1, 0, False, key="fur_light")
            # 耳内暗面
            u.plate("ear_in_" + side,
                    [(-0.030, 0.0), (0.030, 0.0), (0.020, 0.080), (-0.018, 0.080)],
                    "ear." + side, "fur_shadow", axis="Y", thickness=0.012,
                    offset=0.030, bevel=0.002, key="fur_shadow",
                    uv_origin=(0.0, root.z + 0.045))
        # 下巴毛
        self.blimb("chin_tuft", (0, jb.y + 0.156, jb.z - 0.020),
                   (0, jb.y + 0.196, jb.z - 0.072), 0.045, 0.018,
                   "jaw", "fur_light", "fur_light")

    # ── 鬃 / 颈毛 ───────────────────────────────────────────────────────────
    def mane(self):
        u, c = self.u, self.cfg
        if not c["mane"]:
            return
        for i, (bone, y0, z0, y1, z1, w0, w1, d0, d1) in enumerate(c["mane"]):
            rows = []
            for (t, yy, zz, ww, dd) in ((0.0, y0, z0, w0, d0),
                                        (0.55, y0 + (y1 - y0) * 0.55, z0 + (z1 - z0) * 0.65,
                                         w1 * 1.7, d1 * 1.5),
                                        (1.0, y1, z1, w1, d1)):
                rows.append([(-ww * 0.5, yy - dd * 0.5, zz), (ww * 0.5, yy - dd * 0.5, zz),
                             (ww * 0.5, yy + dd * 0.5, zz), (-ww * 0.5, yy + dd * 0.5, zz)])
            u.loft("mane_%d" % i, rows, bone, "fur",
                   bevel=0.0, seg=1, sub=0, smooth=False,
                   key="fur_light" if i % 2 == 0 else "fur")

    def ruff(self):
        u, B, c = self.u, self.B, self.cfg
        if not c["ruff"]:
            return
        z0 = B["chest"][2] + 0.020
        z1 = z0 + 0.130
        seg = 10
        r0o, r0i = c["ruff_r"] + 0.075, c["ruff_r"] - 0.040
        r1o, r1i = c["ruff_r"] + 0.010, c["ruff_r"] - 0.060
        verts, faces = [], []
        for (zz, ro, ri) in ((z0, r0o, r0i), (z1, r1o, r1i)):
            for (rr, aa) in ((ro, 0), (ri, 0)):
                for k in range(seg):
                    a = math.tau * k / seg
                    verts.append((math.sin(a) * rr, math.cos(a) * rr * 0.78 + 0.02, zz))
        # rings: 0 outer0, seg inner0, 2seg outer1, 3seg inner1
        for k in range(seg):
            k2 = (k + 1) % seg
            faces.append((k, k2, seg + k2, seg + k))                       # bottom
            faces.append((2 * seg + k, 2 * seg + k2, 3 * seg + k2, 3 * seg + k))  # top
            faces.append((k, 2 * seg + k, 2 * seg + k2, k2))               # outer wall
            faces.append((seg + k, 3 * seg + k, 3 * seg + k2, seg + k2))   # inner wall
        u.add(K._obj("collar", verts, faces), "chest", "fur_light", 0.0, 1, 0, False,
              key="fur_light")
        # 一圈垂毛
        for k in range(seg):
            a = math.tau * k / seg
            x = math.sin(a) * (r0o - 0.020)
            y = math.cos(a) * (r0o - 0.020) * 0.78 + 0.02
            self.blimb("collar_tuft_%d" % k, (x, y, z0 + 0.010),
                       (x * 1.04, y * 1.04, z0 - 0.090), 0.036, 0.016, "chest", "fur",
                       "fur_pale" if k % 2 else "fur_dark")
