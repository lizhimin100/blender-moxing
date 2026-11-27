"""human_kit2.py —— 联盟人类（步兵 / 弩兵 / 农民）参数化组件库

与 `gnoll_kit2.py` 同一套思路：**一张尺寸表 + 一张材质表 = 一个兵种**。
三个联盟人类共用这里的腿 / 胯 / 躯干 / 臂 / 拳 / 裸头 / 骨架，各自只加
"头饰 + 装备 + 武器"（大盔 / 大檐盔 / 草帽，鸢盾 / 重弩 / 锄头与金袋）。

口径（不许改）：
  * 1 unit = 1 m；+Y 正面；+X = 角色右侧；脚底 z = 0；原点在双足中间。
  * 一块 = 一根骨、权重 1.0（刚性蒙皮）；关节留缝，缝里是暗档内胆。
  * 材质名走**语义名**（甲/甲暗/钢/钢暗/皮革/皮革暗/布/皮肤/皮肤暗 + team/team_trim）。
    换阵营只改 `team` / `team_trim` 两个色 —— 与 骑士 / 破法者 一致。
  * 笔触：体积件 `chunk` / 甲片 `chunk2` / 内胆与缝 `facet` / 大件 `chunk3` / 小五金 `hard`。
    **`soft` 只留给必须真的圆的件**（布袋、绳结），一件里不超过 8%。
  * 明度阶梯（俯视角下唯一能读出来的东西）：
        皮革暗 0.10 < 钢暗 0.22 < 皮革 0.26 < 甲暗 0.36 < 布 0.44 < 甲 0.56 < 钢 0.60 < team_trim 0.66
    队色蓝**只落在 3 处**（胸兜 / 盾面 / 帽箍），金只做线（1~2 mm 的边）。
  * 比例走"英雄化"：**头大、肩宽、腿短**（头高 ≈ 1/6 身高、肩宽 ≈ 1.9 头宽），
    这样 96 px 下才认得出兵种。按写实比例做出来一律读成"细长骑士"。

尺寸表全部由 `H`（身高，到颅顶，不含盔）与 `BULK`（体宽系数）推出来，所以三个兵种
只需要给两个数就能保持"同一家人"的比例手感。

用法（unit_xxx.py）：

    import human_kit2 as HK
    S = HK.Human(H=1.60, BULK=1.10).setup()
    u = unitkit2.Unit2(PREFIX, S.MATS, low=low)
    HK.legs(u, S); HK.pelvis(u, S); HK.torso(u, S); HK.neck(u, S)
    HK.arms(u, S); HK.skull(u, S)
    BONES = HK.bones(S, extra=[("weapon_R", ...), ("shield", ...)])
"""
import math

from mathutils import Vector

import unitkit as KU
import unitkit2 as K

# ══ 材质预设 ════════════════════════════════════════════════════════════════
# 暖象牙甲 + 蓝队色 + 金线 + 皮革棕 —— 与《骑士》的骑手同一支语言。
MATS = {
    "甲":        dict(hexcol="#CFC3AC", metal=0.10, rough=0.46),
    "甲暗":      dict(hexcol="#93856E", metal=0.16, rough=0.52),
    "钢":        dict(hexcol="#8F97A1", metal=0.62, rough=0.30),
    "钢暗":      dict(hexcol="#4E555F", metal=0.52, rough=0.42),
    "皮革":      dict(hexcol="#6B4A31", metal=0.00, rough=0.74),
    "皮革暗":    dict(hexcol="#241A12", metal=0.00, rough=0.82),
    "布":        dict(hexcol="#AEA48C", metal=0.00, rough=0.88),
    "布暗":      dict(hexcol="#615A4C", metal=0.00, rough=0.90),
    "皮肤":      dict(hexcol="#D2A87C", metal=0.00, rough=0.64),
    "皮肤暗":    dict(hexcol="#9C7048", metal=0.00, rough=0.68),
    "刃":        dict(hexcol="#AAB2BA", metal=0.72, rough=0.22),
    "team":      dict(hexcol="#2E5FB4", metal=0.00, rough=0.58),
    "team_trim": dict(hexcol="#F1CD79", metal=0.14, rough=0.42),
}

# 农民用"亚麻 + 土黄"，但队色两格不许动（换阵营的唯一开关）。
MATS_FARM = dict(MATS)
MATS_FARM.update({
    "布":        dict(hexcol="#8E9668", metal=0.00, rough=0.88),   # 亚麻绿
    "布暗":      dict(hexcol="#565C3C", metal=0.00, rough=0.92),
    "麻布":      dict(hexcol="#B7AB8E", metal=0.00, rough=0.90),
    "麻布暗":    dict(hexcol="#867C64", metal=0.00, rough=0.92),
})


# ══ 小件 ════════════════════════════════════════════════════════════════════
def ring(name, center, normal, r_in, r_out, thick, n=8):
    """开口环 / 箍（护腕口、盔箍、腰带环）。平面着色下是一条硬边。"""
    c = Vector(center)
    ez = Vector(normal).normalized()
    up = Vector((0, 0, 1))
    if abs(ez.dot(up)) > 0.95:
        up = Vector((0, 1, 0))
    ex = up.cross(ez).normalized()
    ey = ez.cross(ex).normalized()
    rows = []
    for (o, rr) in ((-thick * 0.5, r_in), (-thick * 0.5, r_out),
                    (thick * 0.5, r_out), (thick * 0.5, r_in)):
        rows.append([tuple(c + ez * o + ex * (rr * math.cos(math.tau * k / n))
                           + ey * (rr * math.sin(math.tau * k / n))) for k in range(n)])
    verts = [p for r in rows for p in r]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((i * n + k, i * n + k2, j * n + k2, j * n + k))
    return KU._obj(name, verts, faces)


def crown_emblem(u, center, size, bone, mat_field="team", mat_gold="team_trim",
                 module="body", tag="sigil", axis="Y", depth=0.0):
    """三尖金冠（联盟徽记，只许出现在胸兜 / 盾面 / 围裙这三处之一）。"""
    cx, cy, cz = center
    s = size
    h = s * 0.80
    u.add(K.plate("sig_field", [(cx - s * 0.60, cz - h * 0.58), (cx + s * 0.60, cz - h * 0.58),
                                (cx + s * 0.60, cz + h * 0.44), (cx - s * 0.60, cz + h * 0.44)],
                  thickness=0.016, offset=cy, axis=axis),
          bone, mat_field, "chunk", module, tag)
    for i, (a, b, top) in enumerate(((-0.54, -0.08, 0.30), (-0.20, 0.20, 0.98),
                                    (0.08, 0.54, 0.30))):
        pts = [(cx + a * s, cz - h * 0.06), (cx + b * s, cz - h * 0.06),
               (cx + (a + b) * 0.5 * s, cz + h * top)]
        u.add(K.plate("sig_p%d" % i, pts, thickness=0.020,
                      offset=cy + (0.005 + depth if axis == "Y" else 0.0), axis=axis),
              bone, mat_gold, "hard", module, tag)
    u.add(K.plate("sig_band", [(cx - s * 0.56, cz - h * 0.20), (cx + s * 0.56, cz - h * 0.20),
                               (cx + s * 0.56, cz - h * 0.04), (cx - s * 0.56, cz - h * 0.04)],
                  thickness=0.022, offset=cy + (0.007 + depth if axis == "Y" else 0.0),
                  axis=axis),
          bone, mat_gold, "hard", module, tag)


def strap(u, p0, p1, w, thick, bone, mat, module="body", tag="strap", style="chunk"):
    """一条压扁的皮带（过肩带 / 胸带 / 袋绳）。"""
    a, b = Vector(p0), Vector(p1)
    ex, ey, ez = KU.frame(a, b, up=(0, 1, 0))
    rows = []
    for t in (0.0, 0.5, 1.0):
        c = a + (b - a) * t
        k = 1.0 if t < 0.5 else 0.94
        rows.append([tuple(c + ex * (w * 0.5 * k) + ey * (thick * 0.5)),
                     tuple(c + ex * (w * 0.5 * k) - ey * (thick * 0.5)),
                     tuple(c - ex * (w * 0.5 * k) - ey * (thick * 0.5)),
                     tuple(c - ex * (w * 0.5 * k) + ey * (thick * 0.5))])
    return u.add(K.loft(name, rows, True), bone, mat, style, module, tag)


def dome_patch(name, center, rx, ry, rz, a0, a1, p0, p1, nu, nv, thick):
    """球面片（护肩顶盖 / 护膝鼓面）。theta 从 +X 起算。"""
    grid = []
    for j in range(nv + 1):
        phi = math.radians(p0 + (p1 - p0) * j / nv)
        row = []
        for i in range(nu + 1):
            th = math.radians(a0 + (a1 - a0) * i / nu)
            row.append((center[0] + rx * math.sin(phi) * math.cos(th),
                        center[1] + ry * math.sin(phi) * math.sin(th),
                        center[2] + rz * math.cos(phi)))
        grid.append(row)
    return K.grid_shell(name, grid, thick, inside=center)


def _frame_tube(name, rows, C, A, P, Q, cw):
    out = []
    for (t, pcen, w, d) in rows:
        base = C + A * t + P * pcen
        pts = K.octs(w, d, cw, cw)
        out.append([tuple(base + P * x + Q * y) for (x, y) in pts])
    return K.loft(name, out)


# ══ 尺寸表 ══════════════════════════════════════════════════════════════════
class Human:
    """一个站立人类的全部关键点。只吃 H（到颅顶）与 BULK（体宽），比例全部锁死。"""

    # 高度比例（乘 H）——英雄化：腿短、躯干厚、头大
    R_ANKLE, R_KNEE, R_HIP = 0.063, 0.268, 0.505
    R_WAIST, R_CHEST, R_SHLD = 0.572, 0.700, 0.822
    R_NECK, R_HEAD, R_TOP = 0.856, 0.902, 1.000

    def __init__(self, H=1.60, BULK=1.10, ARM=1.00, LEG=1.00,
                 HIP_X=None, SH_X=None, HEAD_W=None, MATS=None, M=None,
                 FOOT_Y=0.205, HEEL_Y=-0.086):
        self.H = H
        self.BULK = BULK
        self.ARM = ARM
        self.LEG = LEG
        self.MATS = MATS or globals()["MATS"]
        self._M = M or dict(plate="甲", plate_d="甲暗", steel="钢", steel_d="钢暗",
                            leather="皮革", leather_d="皮革暗", cloth="布",
                            cloth_d="布暗", skin="皮肤", skin_d="皮肤暗",
                            team="team", trim="team_trim", blade="刃")

        self.Z_ANKLE = self.R_ANKLE * H * LEG
        self.Z_KNEE = self.R_KNEE * H * LEG
        self.Z_HIP = self.R_HIP * H * LEG
        self.Z_WAIST = self.R_WAIST * H * LEG
        self.Z_CHEST = self.R_CHEST * H * LEG
        self.Z_SHLD = self.R_SHLD * H * LEG
        self.Z_NECK = self.R_NECK * H * LEG
        self.Z_HEAD = self.R_HEAD * H * LEG
        self.Z_TOP = self.R_TOP * H * LEG

        self.HIP_X = HIP_X if HIP_X is not None else 0.0705 * H * BULK
        self.SH_X = SH_X if SH_X is not None else 0.1320 * H * BULK
        self.HEAD_W = HEAD_W if HEAD_W is not None else 0.1620 * H
        self.FOOT_Y = FOOT_Y * BULK
        self.HEEL_Y = HEEL_Y * BULK
        self.FOOT_W = 0.0620 * H * BULK

    def setup(self):
        H, B, A = self.H, self.BULK, self.ARM
        x = self.HIP_X
        self.HIP = Vector((x, -0.004, self.Z_HIP))
        self.KNE = Vector((x * 1.030, 0.014 * B, self.Z_KNEE))
        self.ANK = Vector((x * 1.030, 0.000, self.Z_ANKLE))
        self.BAL = Vector((x * 1.030, 0.098 * B, 0.030))
        self.TOE = Vector((x * 1.030, self.FOOT_Y, 0.020))
        self.HEEL = Vector((x * 1.030, self.HEEL_Y, 0.0))

        self.SH = Vector((self.SH_X, 0.006 * B, self.Z_SHLD - 0.004))
        self.ELB = Vector((self.SH_X * 1.040, 0.032 * B, self.Z_SHLD - 0.133 * H * A))
        self.WRI = Vector((self.SH_X * 1.050, 0.054 * B, self.Z_SHLD - 0.246 * H * A))
        self.HDIR = Vector((0.14, 0.30, -0.94)).normalized()
        self.NECK0 = Vector((0.0, 0.030 * B, self.Z_NECK))
        self.HEAD0 = Vector((0.0, 0.040 * B, self.Z_HEAD))
        return self

    # ── 取点 ────────────────────────────────────────────────────────────────
    def side(self, s):
        return "R" if s > 0 else "L"

    def hip(self, s):
        return Vector((s * self.HIP.x, self.HIP.y, self.HIP.z))

    def kne(self, s):
        return Vector((s * self.KNE.x, self.KNE.y, self.KNE.z))

    def ank(self, s):
        return Vector((s * self.ANK.x, self.ANK.y, self.ANK.z))

    def bal(self, s):
        return Vector((s * self.BAL.x, self.BAL.y, self.BAL.z))

    def toe(self, s):
        return Vector((s * self.TOE.x, self.TOE.y, self.TOE.z))

    def sh(self, s):
        return Vector((s * self.SH.x, self.SH.y, self.SH.z))

    def elb(self, s):
        return Vector((s * self.ELB.x, self.ELB.y, self.ELB.z))

    def wri(self, s):
        return Vector((s * self.WRI.x, self.WRI.y, self.WRI.z))

    def hdir(self, s):
        d = self.HDIR.copy()
        d.x *= s
        return d

    def m(self, key):
        return self._M[key]

    def foot_clear(self, pitch_deg):
        """脚绕踝转 pitch 度后，踝要高到多少脚底才不切地（脚底四角取最深的那个）。"""
        p = math.radians(pitch_deg)
        sp, cp = math.sin(p), math.cos(p)
        lo = 0.0
        for y in (self.HEEL_Y, self.FOOT_Y):
            lo = max(lo, -(-self.Z_ANKLE * cp + y * sp))
        return lo


# ══ 1. 腿 ═══════════════════════════════════════════════════════════════════
def legs(u, S, boot_mat=None, greave_mat=None, cuisse_mat=None, team_boot=True,
         knee_mat=None):
    """大腿（内胆 + 两片弧甲 + team 上沿） / 膝（方护膝 + 浮凸） / 小腿（内胆 + 胫甲） / 靴。"""
    k = S.BULK
    boot_mat = boot_mat or S.m("leather_d")
    greave_mat = greave_mat or S.m("steel_d")
    cuisse_mat = cuisse_mat or S.m("plate")
    knee_mat = knee_mat or S.m("steel")
    for s in (1, -1):
        side = S.side(s)
        hip, kne, ank = S.hip(s), S.kne(s), S.ank(s)
        th, sn, ft = "thigh_" + side, "shin_" + side, "foot_" + side
        out = (s * 0.94, 0.06, 0.34)
        toe = S.toe(s)

        # 大腿内胆
        u.olimb("lg_thigh_" + side, hip + (kne - hip) * -0.02, kne + (hip - kne) * 0.10,
                [(0.00, 0.168 * k, 0.180 * k, 0.042), (0.55, 0.156 * k, 0.168 * k, 0.038),
                 (1.00, 0.140 * k, 0.152 * k, 0.034)],
                th, S.m("steel_d"), "facet", "body", "thigh")
        # 大腿甲：外 / 内两片（中缝一条暗线），比内胆外扩 1.6 cm
        for (a0, a1, nm) in ((-106, 6, "out"), (6, 106, "in")):
            u.add(K.arc_band("lg_cuisse_%s_%s" % (nm, side),
                             hip + (kne - hip) * 0.08, kne + (hip - kne) * 0.14,
                             0.112 * k, 0.100 * k, a0, a1, 3, 5, 0.026, out),
                  th, cuisse_mat, "chunk2", "body", "thigh")
        u.add(K.arc_band("lg_cuisse_band_" + side, hip + (kne - hip) * 0.04,
                         hip + (kne - hip) * 0.12, 0.116 * k, 0.114 * k, -110, 110,
                         1, 6, 0.020, out),
              th, S.m("trim"), "chunk", "body", "thigh")

        # 膝
        u.otube("lg_poleyn_" + side,
                [(kne.z + 0.056, kne.x, kne.y - 0.004, 0.166 * k, 0.176 * k, 0.044),
                 (kne.z + 0.004, kne.x, kne.y + 0.006, 0.180 * k, 0.192 * k, 0.048),
                 (kne.z - 0.052, kne.x, kne.y - 0.002, 0.152 * k, 0.164 * k, 0.040)],
                sn, knee_mat, "chunk2", "body", "knee", cw=0.042)
        u.add(dome_patch("lg_knee_cap_" + side, (kne.x, kne.y + 0.030, kne.z),
                         0.070 * k, 0.066 * k, 0.074 * k,
                         -42 if s > 0 else 138, 42 if s > 0 else 222, 24, 92, 2, 2, 0.018),
              sn, S.m("steel_d"), "chunk", "body", "knee")

        # 小腿
        u.olimb("lg_shin_" + side, kne + (ank - kne) * 0.18, ank + (kne - ank) * 0.04,
                [(0.00, 0.140 * k, 0.150 * k, 0.034), (0.55, 0.124 * k, 0.134 * k, 0.030),
                 (1.00, 0.110 * k, 0.118 * k, 0.026)],
                sn, S.m("steel_d"), "facet", "body", "shin")
        u.add(K.arc_band("lg_greave_" + side, kne + (ank - kne) * 0.24,
                         ank + (kne - ank) * 0.06, 0.098 * k, 0.082 * k, -104, 104,
                         3, 6, 0.028, out),
              sn, greave_mat, "chunk2", "body", "shin")
        u.add(K.arc_band("lg_greave_top_" + side, kne + (ank - kne) * 0.20,
                         kne + (ank - kne) * 0.28, 0.102 * k, 0.104 * k, -108, 108,
                         1, 6, 0.018, out),
              sn, S.m("trim"), "chunk", "body", "shin")

        # 靴
        u.otube("lg_sabaton_" + side,
                [(ank.z + 0.046, ank.x, ank.y - 0.006, 0.126 * k, 0.138 * k, 0.030),
                 (ank.z - 0.004, ank.x, ank.y + 0.024, 0.136 * k, 0.196 * k, 0.032),
                 (ank.z - 0.030, ank.x, ank.y + 0.048, 0.138 * k, 0.226 * k, 0.032)],
                ft, boot_mat, "chunk2", "body", "boot", cw=0.032)
        u.box("lg_sole_" + side, (ank.x, (S.HEEL_Y + S.FOOT_Y) * 0.5, 0.013),
              (0.148 * k, (S.FOOT_Y - S.HEEL_Y) * 0.98, 0.026),
              ft, S.m("leather_d"), style="hard", module="body", tag="boot")
        u.otube("lg_toe_" + side,
                [(ank.z - 0.004, toe.x, toe.y - 0.070, 0.132 * k, 0.096 * k, 0.028),
                 (ank.z - 0.038, toe.x, toe.y - 0.022, 0.138 * k, 0.112 * k, 0.030)],
                ft, S.m("steel_d"), "chunk", "body", "boot", cw=0.028)
        if team_boot:
            u.box("lg_toe_rim_" + side, (toe.x, toe.y + 0.010, ank.z - 0.044),
                  (0.120 * k, 0.022, 0.012), ft, S.m("trim"),
                  style="hard", module="body", tag="boot")


# ══ 2. 胯 / 腰 ══════════════════════════════════════════════════════════════
def pelvis(u, S, fauld=True, belt_team=True, kilt_mat=None):
    k = S.BULK
    kilt_mat = kilt_mat or S.m("plate_d")
    u.otube("pv_hip",
            [(S.Z_HIP - 0.070, 0, -0.010, 0.262 * k, 0.214 * k, 0.044),
             (S.Z_HIP + 0.004, 0, -0.010, 0.280 * k, 0.226 * k, 0.048),
             (S.Z_WAIST - 0.006, 0, -0.008, 0.266 * k, 0.216 * k, 0.044)],
            "hips", S.m("steel_d"), "facet", "body", "pelvis", cw=0.042)
    u.otube("pv_belt",
            [(S.Z_WAIST - 0.046, 0, -0.008, 0.282 * k, 0.230 * k, 0.048),
             (S.Z_WAIST + 0.002, 0, -0.008, 0.292 * k, 0.238 * k, 0.050),
             (S.Z_WAIST + 0.036, 0, -0.008, 0.282 * k, 0.232 * k, 0.048)],
            "hips", S.m("leather"), "chunk2", "body", "belt", cw=0.044)
    if belt_team:
        u.box("pv_buckle", (0, 0.118 * k, S.Z_WAIST - 0.004),
              (0.082 * k, 0.026, 0.058), "hips", S.m("trim"),
              style="chunk", module="body", tag="belt")
        u.box("pv_buckle_in", (0, 0.132 * k, S.Z_WAIST - 0.004),
              (0.034 * k, 0.012, 0.026), "hips", S.m("team"),
              style="hard", module="body", tag="belt")
    if not fauld:
        return
    # 腰甲四片（片间 8° 缝）—— 只到膝上两拳，别做成钟罩
    zt, zb = S.Z_HIP + 0.004, S.Z_KNEE + 0.150
    h = zt - zb
    for (nm, a0, a1) in (("f", -44, 44), ("b", 136, 224)):
        u.add(K.arc_panel("pv_fauld_" + nm,
                          [(zt, a0, a1, 0.134 * k, 0.122 * k),
                           (zt - h * 0.55, a0 - 2, a1 if nm == "b" else a1 + 2,
                            0.146 * k, 0.132 * k),
                           (zb, a0 - 5, a1 if nm == "b" else a1 + 5,
                            0.152 * k, 0.136 * k)],
                          0.026, 5, inside=(0, 0, zt - h * 0.5), center=(0, -0.006)),
              "hips", kilt_mat, "chunk2", "body", "fauld")
    for s in (1, -1):
        u.add(K.arc_panel("pv_fauld_s_%d" % s,
                          [(zt, 44, 136, 0.134 * k, 0.122 * k),
                           (zt - h * 0.55, 46, 134, 0.146 * k, 0.132 * k),
                           (zb, 48, 132, 0.152 * k, 0.136 * k)],
                          0.024, 5, inside=(0, 0, zt - h * 0.5), center=(0, -0.006)),
              "hips", kilt_mat, "chunk2", "body", "fauld")


# ══ 3. 躯干 ═════════════════════════════════════════════════════════════════
def torso(u, S, tabard=True, sigil=True, gorget=True, plate_mat=None,
          tabard_mat=None, abs_bands=2):
    """腹甲 → 胸甲（八边、中脊）→ 胸兜（team + 金冠）→ 护喉。

    "胸甲比腹甲宽 12%、胸兜比胸甲窄 44%" 是这套甲能读出层次的全部秘密。
    """
    k = S.BULK
    plate_mat = plate_mat or S.m("plate")
    tabard_mat = tabard_mat or S.m("team")
    zc, zw, zs = S.Z_CHEST, S.Z_WAIST, S.Z_SHLD

    u.otube("tr_ab",
            [(zw - 0.018, 0, -0.008, 0.232 * k, 0.192 * k, 0.042),
             (zw + 0.056, 0, -0.006, 0.244 * k, 0.200 * k, 0.044),
             (zc - 0.010, 0, -0.004, 0.258 * k, 0.208 * k, 0.046)],
            "spine", S.m("steel_d"), "facet", "body", "abdomen", cw=0.042)
    for i in range(abs_bands):
        z = zw + 0.008 + i * 0.058
        u.add(K.arc_panel("tr_abband%d" % i,
                          [(z - 0.019, -112, 112, 0.124 * k, 0.102 * k),
                           (z + 0.019, -112, 112, 0.126 * k, 0.104 * k)],
                          0.018, 6, inside=(0, -0.006, z), center=(0, -0.006)),
              "spine", S.m("plate_d"), "chunk", "body", "abdomen")
    u.add(K.arc_panel("tr_waistband",
                      [(zw - 0.050, -116, 116, 0.130 * k, 0.104 * k),
                       (zw - 0.014, -116, 116, 0.132 * k, 0.106 * k)],
                      0.016, 6, inside=(0, -0.006, zw - 0.03), center=(0, -0.006)),
          "spine", S.m("trim"), "chunk", "body", "abdomen")

    u.otube("tr_chest",
            [(zc - 0.028, 0, -0.004, 0.252 * k, 0.206 * k, 0.044),
             (zc + 0.046, 0, 0.002, 0.302 * k, 0.226 * k, 0.052),
             (zc + 0.100, 0, 0.006, 0.316 * k, 0.224 * k, 0.054),
             (zs - 0.004, 0, 0.010, 0.284 * k, 0.210 * k, 0.048),
             (zs + 0.030, 0, 0.012, 0.240 * k, 0.188 * k, 0.042)],
            "chest", plate_mat, "chunk2", "body", "chest", cw=0.052)
    u.add(K.grid_shell("tr_sternum", [
        [(-0.018, 0.064 * k, zc - 0.022), (0.0, 0.078 * k, zc - 0.022),
         (0.018, 0.064 * k, zc - 0.022)],
        [(-0.020, 0.102 * k, zc + 0.044), (0.0, 0.118 * k, zc + 0.044),
         (0.020, 0.102 * k, zc + 0.044)],
        [(-0.018, 0.088 * k, zc + 0.118), (0.0, 0.104 * k, zc + 0.118),
         (0.018, 0.088 * k, zc + 0.118)],
    ], 0.018, inside=(0, 0, zc + 0.04)),
          "chest", S.m("plate_d"), "chunk", "body", "chest")

    if tabard:
        u.add(K.grid_shell("tr_tabard", [
            [(-0.058 * k, 0.114 * k, zs + 0.008), (0.058 * k, 0.114 * k, zs + 0.008)],
            [(-0.066 * k, 0.126 * k, zc + 0.086), (0.066 * k, 0.126 * k, zc + 0.086)],
            [(-0.060 * k, 0.120 * k, zc - 0.016), (0.060 * k, 0.120 * k, zc - 0.016)],
            [(-0.050 * k, 0.108 * k, zw - 0.016), (0.050 * k, 0.108 * k, zw - 0.016)],
        ], 0.018, inside=(0, 0, zc + 0.02)),
              "chest", tabard_mat, "chunk2", "body", "tabard")
        for s in (1, -1):
            u.add(K.grid_shell("tr_tabard_rim%d" % s, [
                [(s * 0.058 * k, 0.114 * k, zs + 0.008), (s * 0.074 * k, 0.108 * k, zs + 0.012)],
                [(s * 0.066 * k, 0.126 * k, zc + 0.086), (s * 0.082 * k, 0.120 * k, zc + 0.090)],
                [(s * 0.060 * k, 0.120 * k, zc - 0.016), (s * 0.076 * k, 0.114 * k, zc - 0.012)],
            ], 0.012, inside=(0, 0, zc + 0.02)),
                  "chest", S.m("trim"), "chunk", "body", "tabard")
        if sigil:
            crown_emblem(u, (0, 0.138 * k, zc + 0.046), 0.104 * k, "chest",
                         module="body", tag="sigil")

    if gorget:
        u.otube("tr_gorget",
                [(zs - 0.028, 0, 0.012, 0.246 * k, 0.184 * k, 0.042),
                 (zs + 0.020, 0, 0.014, 0.204 * k, 0.162 * k, 0.034),
                 (S.Z_NECK + 0.004, 0, 0.016, 0.164 * k, 0.138 * k, 0.028)],
                "chest", S.m("plate_d"), "chunk2", "body", "gorget", cw=0.036)
        u.otube("tr_gorget_rim",
                [(S.Z_NECK, 0, 0.016, 0.168 * k, 0.142 * k, 0.029),
                 (S.Z_NECK + 0.020, 0, 0.016, 0.156 * k, 0.132 * k, 0.026)],
                "chest", S.m("trim"), "chunk", "body", "gorget", cw=0.032)


# ══ 4. 臂 ═══════════════════════════════════════════════════════════════════
def arms(u, S, rere_mat=None, vamb_mat=None):
    k = S.BULK
    rere_mat = rere_mat or S.m("plate")
    vamb_mat = vamb_mat or S.m("plate")
    for s in (1, -1):
        side = S.side(s)
        sh, el, wr = S.sh(s), S.elb(s), S.wri(s)
        ua, fa = "upperarm_" + side, "forearm_" + side
        out = (s * 1.0, -0.18, -0.12)
        d = (el - sh).normalized()
        df = (wr - el).normalized()

        # 肩窝 / 上臂
        u.olimb("ar_jt_sh_" + side, sh + d * -0.050, sh + d * 0.036,
                [(0.0, 0.168 * k, 0.174 * k, 0.044), (1.0, 0.162 * k, 0.168 * k, 0.042)],
                ua, S.m("steel_d"), "facet", "body", "joint")
        u.olimb("ar_upper_" + side, sh + d * 0.006, el - d * 0.020,
                [(0.00, 0.152 * k, 0.158 * k, 0.040), (0.55, 0.142 * k, 0.148 * k, 0.036),
                 (1.00, 0.130 * k, 0.136 * k, 0.032)],
                ua, S.m("steel_d"), "facet", "body", "upper")
        u.add(K.arc_band("ar_rere_" + side, sh + d * 0.030, el - d * 0.036,
                         0.092 * k, 0.078 * k, -118, 118, 2, 6, 0.024, out),
              ua, rere_mat, "chunk2", "body", "upper")
        u.add(K.arc_band("ar_rere_rim_" + side, el - d * 0.066, el - d * 0.042,
                         0.082 * k, 0.086 * k, -114, 114, 1, 6, 0.018, out),
              ua, S.m("trim"), "chunk", "body", "upper")

        # 肘
        u.olimb("ar_jt_el_" + side, el - d * 0.030, el + df * 0.030,
                [(0.0, 0.126 * k, 0.130 * k, 0.032), (1.0, 0.126 * k, 0.130 * k, 0.032)],
                fa, S.m("steel_d"), "facet", "body", "joint")
        u.add(dome_patch("ar_couter_" + side, tuple(el + Vector((s * 0.008, -0.012, 0.002))),
                         0.078 * k, 0.074 * k, 0.080 * k,
                         -46 if s > 0 else 134, 46 if s > 0 else 226, 22, 92, 2, 2, 0.018),
              fa, S.m("plate_d"), "chunk", "body", "elbow")
        # 前臂
        u.olimb("ar_fore_" + side, el + df * 0.016, wr - df * 0.004,
                [(0.00, 0.132 * k, 0.138 * k, 0.032), (0.55, 0.120 * k, 0.126 * k, 0.030),
                 (1.00, 0.110 * k, 0.116 * k, 0.026)],
                fa, S.m("steel_d"), "facet", "body", "fore")
        u.add(K.arc_band("ar_vamb_" + side, el + df * 0.026, wr - df * 0.008,
                         0.080 * k, 0.070 * k, -132, 132, 2, 6, 0.022, out),
              fa, vamb_mat, "chunk2", "body", "fore")
        u.add(ring("ar_cuff_" + side, tuple(wr - df * 0.008), tuple(df),
                   0.066 * k, 0.078 * k, 0.024, 8),
              fa, S.m("trim"), "chunk", "body", "cuff")


def fist(u, S, side, center=None, axis=None, palm=None, k=1.0, mat=None,
         cuff=True, bone=None, module="body", tag="hand", knuckle=True):
    """握拳（攥住一根沿 `axis` 的杆）。掌心朝 `palm`，三指从 +Q 绕到 −P。

    与 gnoll_kit2.fist_around 同一套坐标，但换成联盟的甲片语言：
    掌块（甲） + 指节横板（钢） + 三指（甲暗） + 拇指（甲暗） + 腕箍（金线）。
    """
    s = 1 if side == "R" else -1
    bone = bone or ("hand_" + side)
    mat = mat or S.m("plate")
    kk = k * S.BULK
    C = Vector(center) if center is not None else S.wri(s) + S.hdir(s) * 0.062
    A = Vector(axis).normalized() if axis is not None else Vector((0, 0, 1))
    P = Vector(palm) if palm is not None else S.hdir(s)
    P = (P - A * P.dot(A))
    if P.length < 1e-5:
        P = Vector((0, 1, 0))
    P.normalize()
    Q = A.cross(P).normalized()

    # 掌块：整体偏到 +P 一侧，中间留出"握孔"给杆件穿过。
    # 掌块压在轴上就会把剑柄/弩身吞进去 —— 这是"握持穿模"的唯一成因。
    u.add(_frame_tube("hd_palm_" + side,
                      ((-0.070, 0.052, 0.078, 0.112), (-0.030, 0.050, 0.082, 0.120),
                       (0.018, 0.048, 0.078, 0.114), (0.050, 0.046, 0.068, 0.100)),
                      C, A, P, Q, 0.020 * kk),
          bone, mat, "chunk", module, tag)
    # 指缝内胆：掌块内侧的一条暗缝（从指缝里透出来的深度）
    u.add(_frame_tube("hd_gap_" + side, ((-0.046, 0.024, 0.022, 0.094),
                                        (0.038, 0.024, 0.020, 0.092)),
                      C, A, P, Q, 0.006 * kk),
          bone, S.m("leather_d"), "facet", module, "finger")
    # 三指：从掌侧 (+P) 绕过 +Q、指尖落到 −P —— 把杆件围在虎口里
    for i, dz in enumerate((-0.052, -0.008, 0.036)):
        p0 = C + P * (0.040 * kk) + Q * (0.030 * kk) + A * (dz * kk)
        p1 = C + P * (0.008 * kk) + Q * (0.088 * kk) + A * (dz * kk)
        p2 = C - P * (0.046 * kk) + Q * (0.074 * kk) + A * (dz * kk)
        u.olimb("hd_f%d_a_%s" % (i, side), tuple(p0), tuple(p1),
                [(0.00, 0.042 * kk, 0.044 * kk, 0.011), (1.00, 0.038 * kk, 0.040 * kk, 0.010)],
                bone, S.m("plate_d"), "chunk", module, "finger")
        u.olimb("hd_f%d_b_%s" % (i, side), tuple(p1), tuple(p2),
                [(0.00, 0.038 * kk, 0.040 * kk, 0.010), (1.00, 0.032 * kk, 0.034 * kk, 0.009)],
                bone, S.m("plate_d"), "chunk", module, "finger")
    if knuckle:
        # 指节横板：压在指根上（+Q 侧），沿握轴一条
        u.add(_frame_tube("hd_knuckle_" + side,
                          ((-0.058, 0.060, 0.030, 0.104), (0.042, 0.060, 0.030, 0.100)),
                          C, A, P, Q, 0.010 * kk),
              bone, S.m("steel"), "chunk", module, "finger")
    # 拇指：从掌侧斜压到指尖，锁住杆件
    u.olimb("hd_thumb_a_" + side, tuple(C + P * (0.058 * kk) - Q * (0.052 * kk)),
            tuple(C + P * (0.012 * kk) - Q * (0.068 * kk)),
            [(0.00, 0.042 * kk, 0.046 * kk, 0.011), (1.00, 0.036 * kk, 0.040 * kk, 0.010)],
            bone, S.m("plate_d"), "chunk", module, "finger")
    u.olimb("hd_thumb_b_" + side, tuple(C + P * (0.012 * kk) - Q * (0.068 * kk)),
            tuple(C - P * (0.048 * kk) - Q * (0.038 * kk)),
            [(0.00, 0.036 * kk, 0.040 * kk, 0.010), (1.00, 0.030 * kk, 0.032 * kk, 0.009)],
            bone, S.m("plate_d"), "chunk", module, "finger")
    if cuff:
        wr = S.wri(s)
        dd = (C - wr)
        dd = dd.normalized() if dd.length > 1e-6 else S.hdir(s)
        u.olimb("hd_cuff_" + side, tuple(wr + dd * (0.028 * kk)), tuple(wr - dd * (0.002 * kk)),
                [(0.0, 0.102 * kk, 0.108 * kk, 0.024), (1.0, 0.094 * kk, 0.100 * kk, 0.022)],
                bone, S.m("trim"), "chunk", module, "cuff")


# ══ 5. 头（裸头：农民 / 弩兵露脸用；盔另建）═════════════════════════════════
def skull(u, S, jaw=True, beard=False, ears=True, face_mat=None, mat_dark=None,
          bone="head", module="head", brow_hide=False):
    """方块化的头：额头一块正面折面、眉弓、鼻楔、颧面、下颌、下巴。

    判据：**正面只有 ±38° 一块折面** —— 眼、鼻、嘴全压在这块面上，
    否则俯视角下会绕到侧脸变成"面具天线"。
    """
    hw = S.HEAD_W * 0.5
    z0 = S.Z_NECK + 0.008
    zt = S.Z_TOP - 0.006
    h = zt - z0
    cy = S.HEAD0.y
    face_mat = face_mat or S.m("skin")
    mat_dark = mat_dark or S.m("skin_d")

    rows = [
        (z0, 0.70, 0.84, 0.78),
        (z0 + h * 0.16, 0.93, 0.97, 0.94),
        (z0 + h * 0.44, 1.00, 1.00, 1.00),
        (z0 + h * 0.72, 1.00, 0.97, 1.02),
        (z0 + h * 0.89, 0.90, 0.88, 0.92),
        (zt, 0.68, 0.70, 0.72),
    ]
    grid = []
    for (z, wf, df, cf) in rows:
        w, d = 2 * hw * wf, 2 * hw * 0.92 * df
        grid.append([(x, cy + y, z) for (x, y) in K.octs(w, d, w * 0.19 * cf, d * 0.19 * cf)])
    u.add(K.loft("sk_skull", grid), bone, face_mat, "chunk", module, "skull")

    if not brow_hide:
        u.box("sk_brow", (0, cy + hw * 0.60, z0 + h * 0.66),
              (hw * 1.62, 0.026, 0.022), bone, mat_dark, style="chunk",
              module=module, tag="brow")
    for s in (1, -1):
        u.box("sk_eye%d" % s, (s * hw * 0.34, cy + hw * 0.64, z0 + h * 0.60),
              (hw * 0.34, 0.022, 0.026), bone, S.m("leather_d"), style="hard",
              module=module, tag="eye")
        u.box("sk_pup%d" % s, (s * hw * 0.28, cy + hw * 0.665, z0 + h * 0.60),
              (hw * 0.12, 0.010, 0.014), bone, S.m("steel_d"), style="hard",
              module=module, tag="eye")
    u.add(K.plate("sk_nose", [(-hw * 0.15, z0 + h * 0.55), (hw * 0.15, z0 + h * 0.55),
                              (hw * 0.11, z0 + h * 0.38), (-hw * 0.11, z0 + h * 0.38)],
                  thickness=0.030, offset=cy + hw * 0.66, axis="Y"),
          bone, face_mat, "chunk", module, "nose")
    if jaw:
        u.box("sk_mouth", (0, cy + hw * 0.62, z0 + h * 0.23),
              (hw * 0.54, 0.016, 0.012), bone, S.m("leather_d"), style="hard",
              module=module, tag="mouth")
        u.otube("sk_jaw",
                [(z0 - 0.006, 0, cy, hw * 1.28, hw * 1.06, hw * 0.22),
                 (z0 + h * 0.11, 0, cy + hw * 0.02, hw * 1.38, hw * 1.18, hw * 0.24),
                 (z0 + h * 0.25, 0, cy + hw * 0.02, hw * 1.44, hw * 1.24, hw * 0.25)],
                bone, mat_dark, "chunk", module, "jaw", cw=hw * 0.18)
    if beard:
        u.otube("sk_beard",
                [(z0 - 0.014, 0, cy + hw * 0.04, hw * 1.32, hw * 1.12, hw * 0.22),
                 (z0 + h * 0.13, 0, cy + hw * 0.07, hw * 1.22, hw * 1.06, hw * 0.20)],
                bone, S.m("cloth_d"), "chunk", module, "beard", cw=hw * 0.16)
        u.box("sk_moust", (0, cy + hw * 0.66, z0 + h * 0.31),
              (hw * 0.88, 0.024, 0.018), bone, S.m("cloth_d"), style="chunk",
              module=module, tag="beard")
    if ears:
        for s in (1, -1):
            u.add(K.plate("sk_ear%d" % s,
                          [(-0.022, z0 + h * 0.45), (0.024, z0 + h * 0.51),
                           (0.022, z0 + h * 0.60), (-0.024, z0 + h * 0.55)],
                          thickness=0.024, offset=s * (hw * 0.90), axis="X"),
                  bone, mat_dark, "chunk", module, "ear")


def neck(u, S, mat=None):
    k = S.BULK
    mat = mat or S.m("leather_d")
    u.olimb("nk_neck", (0, 0.014 * k, S.Z_NECK - 0.036),
            (0, 0.030 * k, S.Z_HEAD + 0.020),
            [(0.00, 0.128 * k, 0.120 * k, 0.028), (1.00, 0.114 * k, 0.108 * k, 0.024)],
            "neck", mat, "facet", "body", "neck")


# ══ 6. 骨架 ═════════════════════════════════════════════════════════════════
def bones(S, extra=(), hands=True, weapons=True, wdir=None):
    """联盟白名单 24~25 根：root hips spine chest neck head
    shoulder/upperarm/forearm/hand ×2 thigh/shin/foot/toe ×2 (+ weapon_R/L, shield)。

    `extra` 追加道具骨（sack / prop_* / fx_*），数量不限。
    """
    b = [
        ("root", (0, 0, 0), (0, 0, 0.30), None),
        ("hips", (0, 0, S.Z_HIP), (0, 0, S.Z_WAIST), "root"),
        ("spine", (0, 0, S.Z_WAIST), (0, 0.010 * S.BULK, S.Z_CHEST), "hips"),
        ("chest", (0, 0.010 * S.BULK, S.Z_CHEST),
         (0, 0.028 * S.BULK, S.Z_SHLD + 0.014), "spine"),
        ("neck", (0, 0.026 * S.BULK, S.Z_NECK - 0.004),
         (0, 0.038 * S.BULK, S.Z_HEAD), "chest"),
        ("head", (0, 0.038 * S.BULK, S.Z_HEAD), (0, 0.044 * S.BULK, S.Z_TOP), "neck"),
    ]
    for s in (1, -1):
        side = S.side(s)
        sh, el, wr = S.sh(s), S.elb(s), S.wri(s)
        hd = S.hdir(s)
        b += [
            ("shoulder_" + side, (s * 0.042 * S.BULK, 0.006 * S.BULK, S.Z_SHLD - 0.016),
             tuple(sh), "chest"),
            ("upperarm_" + side, tuple(sh), tuple(el), "shoulder_" + side),
            ("forearm_" + side, tuple(el), tuple(wr), "upperarm_" + side),
        ]
        if hands:
            b.append(("hand_" + side, tuple(wr), tuple(wr + hd * (0.108 * S.BULK)),
                      "forearm_" + side))
        hip, kne, ank = S.hip(s), S.kne(s), S.ank(s)
        bal, toe = S.bal(s), S.toe(s)
        b += [
            ("thigh_" + side, tuple(hip), tuple(kne), "hips"),
            ("shin_" + side, tuple(kne), tuple(ank), "thigh_" + side),
            ("foot_" + side, tuple(ank), tuple(bal), "shin_" + side),
            ("toe_" + side, tuple(bal), tuple(toe), "foot_" + side),
        ]
    if weapons:
        # wdir：武器骨的轴向（骨轴 = 武器朝向）。不给就沿手掌方向。
        for s in (1, -1):
            side = S.side(s)
            wr = S.wri(s)
            d = Vector(wdir[side]).normalized() if (wdir and side in wdir) else S.hdir(s)
            b.append(("weapon_" + side, tuple(wr), tuple(wr + d * 0.10),
                      "hand_" + side))
    for e in extra:
        b.append(e)
    return b
