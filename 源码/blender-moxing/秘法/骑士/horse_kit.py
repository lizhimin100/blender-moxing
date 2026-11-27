"""horse_kit.py —— 联盟战马（精模 / 硬边支线）的几何组件

给 `unit_骑士.py` 用，也可以单独复用成"无骑手的战马"坐骑。

口径与手册一致：1 unit = 1 m，+Y 正面，+X = 角色右侧，四蹄落地 z = 0。
造型语言：**马是"几块体积 + 一条脊线 + 四段硬腿"拼出来的**，不是一根管子弯出来 ——
  * 躯干 `yloft` 沿 Y 放样，八边切角截面，背线一条硬棱；
  * 颈是**竖起的楔形**（不是平伸的管子）：肩隆出颈、喉线前倾、鬃毛一排薄片；
  * 腿四段（上/下/球节/蹄），段间一条深色缝，蹄上一圈深色"袜口"；
  * 装备四层：鞍（皮革）/ 马衣（team 蓝 + 金边，下摆带弧度）/ 胸甲（甲色）/ 面甲（甲色 + 蓝翎）。

比例（withers ≈ 1.64 m，肩隆到臀 1.30 m，胸深 0.74 m）按真马量出来再把腿压短 6%：
真马偏高瘦，游戏里要"矮壮 + 短腿"才不显瘦长（v1 是长颈鹿）。
"""
import math

from mathutils import Vector

import unitkit as KU
import unitkit2 as K

# ── 尺寸（m）────────────────────────────────────────────────────────────────
Z_BACK = 1.640          # 背线（鞍位）
Z_BELLY = 0.880
Y_CHEST = 0.560
Y_CROUP = -0.780
W_BODY = 0.630

NECK_BASE = Vector((0.0, 0.300, 1.598))
NECK_POLL = Vector((0.0, 0.585, 1.862))
HEAD_TIP = Vector((0.0, 0.905, 1.440))
SADDLE_C = Vector((0.0, -0.060, 1.660))

# 四肢关节（右前 / 右后；左腿按 x 取反）
FRONT_SH = Vector((0.200, 0.330, 1.250))
FRONT_KNEE = Vector((0.208, 0.392, 0.620))
FRONT_FET = Vector((0.212, 0.368, 0.205))
FRONT_TOE = Vector((0.212, 0.466, 0.105))

HIND_HIP = Vector((0.210, -0.560, 1.290))
HIND_HOCK = Vector((0.228, -0.700, 0.545))
HIND_FET = Vector((0.232, -0.616, 0.205))
HIND_TOE = Vector((0.232, -0.520, 0.105))

TAIL_A = Vector((0.0, -0.815, 1.560))
TAIL_B = Vector((0.0, -0.945, 1.320))
TAIL_C = Vector((0.0, -0.965, 1.045))

# 头部坐标系（所有五官按这条轴参数化，改比例时一起走）
HA = NECK_POLL + Vector((0, -0.030, 0.005))
HB = HEAD_TIP
HZ = (HB - HA).normalized()
HX, HY = KU.frame(HA, HB, (0, 0, 1))[1:3]
HL = (HB - HA).length


def hp(t, w=0.0, d=0.0):
    """头部局部坐标：t 沿头轴 0→1，w 横向（±X），d 沿"头背/头腹"。"""
    return HA + HZ * (HL * t) + HX * w + HY * d


# ── 小工具 ──────────────────────────────────────────────────────────────────
def yloft(name, stations, cw=0.06, cd=None):
    """沿 Y 放样。stations = [(y, cx, cz, w, h)] 或 [+cw, +cd]。截面在 XZ 平面。"""
    rows = []
    for st in stations:
        y, cx, cz, w, h = st[:5]
        a = st[5] if len(st) > 5 else cw
        b = st[6] if len(st) > 6 else (a if cd is None else cd)
        rows.append([(cx + x, y, cz + z) for (x, z) in K.octs(w, h, a, b)])
    return K.loft(name, rows)


def ring(name, center, normal, r_in, r_out, thick, n=10):
    """扁环（马镫 / 衔铁）。"""
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


def sec6(w, d, tr=0.62):
    """6 点楔形截面：底边宽、顶边窄（颈和头的横截面都不是矩形）。"""
    hw, hd = w * 0.5, d * 0.5
    tw = hw * tr
    return [(-hw, -hd), (0.0, -hd * 0.92), (hw, -hd),
            (hw * 1.02, -hd * 0.10), (tw, hd), (-tw, hd), (-hw * 1.02, -hd * 0.10)]


def loft6(name, p0, p1, secs, up=(0, 0, 1)):
    """6 点楔形截面放样。secs = [(t, w, d, tr)]，t 沿 p0→p1。"""
    p0v, ex, ey, ez = KU.frame(p0, p1, up)
    L = (Vector(p1) - p0v).length
    rows = []
    for st in secs:
        t, w, d = st[:3]
        tr = st[3] if len(st) > 3 else 0.62
        c = p0v + ez * (L * t)
        rows.append([tuple(c + ex * x + ey * y) for (x, y) in sec6(w, d, tr)])
    return K.loft(name, rows)


def fm(name, p0, p1, r0, r1, a0, a1, nv=2, nu=5, thick=0.024, out=(0, 1, 0)):
    return K.arc_band(name, p0, p1, r0, r1, a0, a1, nv, nu, thick, out)


def drape(name, cy, a0, a1, levels, nu, thick, inside, hem_z=None):
    """绕竖轴的布料（马衣 / 鞍垫）。levels = [(z, rx, ry)]，hem_z(u) 覆写最后一排的高度。"""
    grid = []
    nrow = len(levels)
    for j, (z, rx, ry) in enumerate(levels):
        row = []
        for i in range(nu + 1):
            a = math.radians(a0 + (a1 - a0) * i / nu)
            zz = hem_z(i / float(nu)) if (hem_z and j == nrow - 1) else z
            row.append((rx * math.sin(a), cy + ry * math.cos(a), zz))
        grid.append(row)
    return K.grid_shell(name, grid, thick, inside=inside)


# ── 1. 躯干 ─────────────────────────────────────────────────────────────────
def body(u):
    # 桶身：胸窄 → 肚带最宽 → 臀收；背线平，腹线略上提
    u.add(yloft("hs_barrel", [
        (Y_CHEST, 0, 1.300, 0.290, 0.380, 0.070),
        (0.440, 0, 1.272, 0.470, 0.580, 0.095),
        (0.280, 0, 1.258, 0.580, 0.700, 0.105),
        (0.040, 0, 1.252, 0.630, 0.760, 0.115),
        (-0.240, 0, 1.262, 0.610, 0.745, 0.112),
        (-0.470, 0, 1.280, 0.570, 0.720, 0.104),
        (-0.660, 0, 1.302, 0.480, 0.640, 0.092),
        (Y_CROUP, 0, 1.322, 0.310, 0.440, 0.072),
    ]), "horse_spine", "马体", "chunk2", "horse", "barrel")
    # 背脊：一条凸起的硬棱
    u.add(yloft("hs_spine_ridge", [
        (0.460, 0, 1.566, 0.088, 0.070, 0.022),
        (0.040, 0, 1.648, 0.100, 0.064, 0.024),
        (-0.320, 0, 1.634, 0.092, 0.058, 0.022),
        (-0.700, 0, 1.548, 0.082, 0.052, 0.020),
    ], cw=0.02), "horse_spine", "马体", "chunk", "horse", "barrel")
    # 胸（两块，撑住颈根；前胸要"鼓"，不然侧面是直板）
    for s in (1, -1):
        u.add(K.olimb("hs_pec_%d" % s, (s * 0.075, 0.540, 1.420),
                      (s * 0.150, 0.430, 1.190),
                      [(0.0, 0.200, 0.220, 0.052), (1.0, 0.230, 0.260, 0.058)]),
              "horse_chest", "马体", "chunk2", "horse", "chest")
    # 臀（两侧各一块，把后腿接上）
    for s in (1, -1):
        u.add(K.olimb("hs_haunch_%d" % s, (s * 0.100, -0.560, 1.440),
                      (s * 0.180, -0.480, 1.140),
                      [(0.0, 0.290, 0.300, 0.070), (1.0, 0.230, 0.250, 0.055)]),
              "horse_hips", "马体", "chunk2", "horse", "hip")
    # 腹线：一条深色带，把浅桶身和深腿分开
    u.add(fm("hs_belly", (0, 0.010, 1.010), (0, 0.010, 1.135),
             0.316, 0.322, 84, 276, 2, 10, 0.030, (0, 0, -1)),
          "horse_spine", "皮革暗", "chunk", "horse", "belly")


# ── 2. 四条腿 ───────────────────────────────────────────────────────────────
def _leg(u, tag, b_up, b_lo, b_hoof, p_sh, p_knee, p_fet, p_toe, w_up, w_lo, plate_mat):
    u.olimb("hs_%s_up" % tag, p_sh, p_knee,
            [(0.00, w_up, w_up * 1.10, 0.046), (0.55, w_up * 0.78, w_up * 0.84, 0.038),
             (1.00, w_up * 0.60, w_up * 0.64, 0.030)],
            b_up, "马体", "facet", "horse", tag + "_up")
    # 上段外侧一块"肌肉板"（同色，只靠折面读结构；不是甲）
    u.add(fm("hs_%s_up_plate" % tag, p_sh + (p_knee - p_sh) * 0.08,
             p_knee + (p_sh - p_knee) * 0.10,
             w_up * 0.60, w_up * 0.34, -84, 84, 3, 5, 0.024, (0, 1, 0)),
          b_up, plate_mat, "chunk2", "horse", tag + "_up")
    u.olimb("hs_%s_lo" % tag, p_knee, p_fet,
            [(0.00, w_lo, w_lo * 1.14, 0.030), (0.45, w_lo * 0.74, w_lo * 0.82, 0.024),
             (1.00, w_lo * 0.80, w_lo * 0.86, 0.026)],
            b_lo, "马体", "facet", "horse", tag + "_lo")
    # 关节：深色套筒
    u.add(K.olimb("hs_%s_joint" % tag, p_knee + (p_sh - p_knee) * 0.060,
                  p_knee + (p_fet - p_knee) * 0.060,
                  [(0.0, w_up * 0.64, w_up * 0.68, 0.030),
                   (1.0, w_lo * 0.86, w_lo * 0.90, 0.028)]),
          b_lo, "皮革暗", "facet", "horse", tag + "_joint")
    # 球节（"袜口"）+ 蹄：蹄底正好落在 z=0
    u.olimb("hs_%s_fet" % tag, p_fet + (p_knee - p_fet) * 0.16,
            p_fet + Vector((0, 0.010, -0.030)),
            [(0.0, w_lo * 0.58, w_lo * 0.62, 0.022), (1.0, w_lo * 0.70, w_lo * 0.76, 0.026)],
            b_hoof, "皮革暗", "chunk", "horse", tag + "_fet")
    cy = (p_fet.y + p_toe.y) * 0.5
    u.otube("hs_%s_hoof" % tag,
            [(0.000, p_toe.x, cy + 0.024, 0.148, 0.186, 0.042),
             (0.044, p_toe.x, cy + 0.020, 0.152, 0.192, 0.044),
             (0.096, p_toe.x, cy + 0.006, 0.134, 0.166, 0.038),
             (0.150, p_toe.x, cy - 0.010, 0.114, 0.140, 0.032)],
            b_hoof, "蹄", "chunk2", "horse", tag + "_hoof", cw=0.045)


def legs(u):
    for s, side in ((1, "R"), (-1, "L")):
        def sx(v):
            return Vector((s * v.x, v.y, v.z))

        _leg(u, "f" + side, "horse_upper_" + side, "horse_fore_" + side,
             "horse_hoofF_" + side, sx(FRONT_SH), sx(FRONT_KNEE),
             sx(FRONT_FET), sx(FRONT_TOE), 0.208, 0.146, "马体")
        _leg(u, "h" + side, "horse_thigh_" + side, "horse_shin_" + side,
             "horse_hoofH_" + side, sx(HIND_HIP), sx(HIND_HOCK),
             sx(HIND_FET), sx(HIND_TOE), 0.236, 0.148, "马体")
        # 前膝：一枚同色鼓包，腿才有"关节"（不然是一根棍）
        u.add(K.olimb("hs_f%s_knee" % side, sx(FRONT_KNEE) + Vector((0, 0.010, 0.070)),
                      sx(FRONT_KNEE) + Vector((0, -0.004, -0.060)),
                      [(0.0, 0.148, 0.160, 0.034), (1.0, 0.126, 0.138, 0.028)]),
              "horse_fore_" + side, "马体", "chunk2", "horse", "f" + side + "_knee")
        # 前腿肩包
        u.add(K.olimb("hs_f%s_shoulder" % side, sx(FRONT_SH) + Vector((0, 0.030, 0.100)),
                      sx(FRONT_SH) + Vector((0, -0.010, -0.080)),
                      [(0.0, 0.232, 0.250, 0.058), (1.0, 0.196, 0.214, 0.048)]),
              "horse_upper_" + side, "马体", "chunk2", "horse", "f" + side + "_shoulder")
        # 后腿大腿（飞节以上一大块，是马后躯的"发动机"）
        u.add(K.olimb("hs_h%s_thigh" % side, sx(HIND_HIP) + Vector((0, 0.070, 0.070)),
                      sx(HIND_HOCK) + Vector((0, 0.030, 0.140)),
                      [(0.0, 0.320, 0.350, 0.078), (0.45, 0.270, 0.300, 0.064),
                       (1.0, 0.150, 0.170, 0.038)]),
              "horse_thigh_" + side, "马体", "chunk2", "horse", "h" + side + "_thigh")
        # 飞节尖（向后的一枚角块 —— 马后腿的识别点）
        u.add(K.olimb("hs_h%s_hock" % side, sx(HIND_HOCK) + Vector((0, 0.010, 0.075)),
                      sx(HIND_HOCK) + Vector((0, -0.075, -0.030)),
                      [(0.0, 0.132, 0.138, 0.034), (1.0, 0.090, 0.094, 0.024)]),
              "horse_shin_" + side, "皮革暗", "chunk2", "horse", "h" + side + "_hock")


# ── 3. 颈 / 头 / 鬃 / 尾 ────────────────────────────────────────────────────
def neck(u):
    """颈：从肩隆"长"出来的楔形，颈背一条硬棱 + 一排鬃片。
    用 KU.frame 建局部坐标系，改 NECK_BASE/POLL 时鬃毛和颈脊自动跟着走。"""
    nb, npv = NECK_BASE, NECK_POLL
    _p, ex, ey, ez = KU.frame(nb, npv, (0, 0, 1))
    L = (npv - nb).length

    def npt(t, depth):
        return npv * 0 + nb + ez * (L * t) + ey * depth

    u.add(loft6("hs_neck", nb + ez * (L * -0.06), npv + ez * (L * 0.03),
                [(0.00, 0.268, 0.404, 0.52), (0.28, 0.240, 0.352, 0.52),
                 (0.58, 0.202, 0.290, 0.54), (0.82, 0.170, 0.230, 0.56),
                 (1.00, 0.154, 0.198, 0.58)]),
          "horse_neck", "马体", "chunk2", "horse", "neck")
    # 颈脊（鬃毛长在这条硬棱上）
    crest0 = npt(-0.02, 0.190)
    crest1 = npt(1.00, 0.096)
    u.add(K.olimb("hs_crest", crest0, crest1,
                  [(0.0, 0.098, 0.142, 0.030), (0.55, 0.086, 0.120, 0.026),
                   (1.0, 0.070, 0.096, 0.020)]),
          "horse_neck", "马体", "chunk", "horse", "crest")
    # 鬃毛：一排压扁的薄片，贴着颈脊往颈背外侧倒（不是一排尖刺）
    n = 11
    for i in range(n):
        t = i / (n - 1.0)
        p = crest0.lerp(crest1, t)
        pil = 0.145 * (1.0 - 0.26 * abs(t - 0.45))
        back = 0.062 + 0.050 * t
        rows = []
        for (so, dd, w, d) in ((0.020, 0.014, 0.050, 0.026),
                               (-back * 0.5, -pil * 0.45, 0.044, 0.024),
                               (-back, -pil, 0.026, 0.016)):
            c = p + ey * so
            rows.append([(c.x + x, c.y, c.z + z) for (x, z) in K.octs(w, d, 0.010)])
        u.add(K.loft("hs_mane_%d" % i, rows), "horse_neck", "皮革暗",
              "chunk", "horse", "mane")
    # 额毛（从耳间向前盖一小片）
    u.add(K.olimb("hs_forelock", hp(0.02, 0, 0.058), hp(0.20, 0, -0.004),
                  [(0.0, 0.096, 0.066, 0.024), (1.0, 0.052, 0.034, 0.012)]),
          "horse_head", "皮革暗", "chunk", "horse", "mane")


def head(u):
    u.add(loft6("hs_head", HA, HB + Vector((0, 0.010, -0.006)),
                [(0.00, 0.166, 0.212, 0.46), (0.24, 0.176, 0.218, 0.46),
                 (0.55, 0.152, 0.180, 0.48), (0.80, 0.126, 0.146, 0.52),
                 (1.00, 0.112, 0.120, 0.56)]),
          "horse_head", "马体", "chunk2", "horse", "head")
    # 下颌（沿头腹的一条硬块，正面看头是"楔 + 方"）
    u.add(K.olimb("hs_jaw", hp(0.04, 0, -0.092), hp(0.92, 0, -0.062),
                  [(0.00, 0.152, 0.092, 0.030), (0.55, 0.126, 0.076, 0.026),
                   (1.00, 0.092, 0.058, 0.020)]),
          "horse_head", "皮革暗", "facet", "horse", "jaw")
    # 口鼻端面（深色）
    u.add(K.olimb("hs_muzzle", hp(0.92, 0, -0.002), hp(1.06, 0, -0.008),
                  [(0.0, 0.106, 0.114, 0.022), (1.0, 0.098, 0.100, 0.020)]),
          "horse_head", "皮革暗", "chunk", "horse", "muzzle")
    for s in (1, -1):
        u.rivet("hs_eye_%d" % s, hp(0.38, s * 0.074, 0.026), (s * 0.94, -0.16, 0.30),
                "horse_head", "皮革暗", "chunk", "horse", "eye", r=0.026, h=0.013, n=8)
        # 耳：从枕部竖起、稍向后外张的扁楔
        eb = hp(0.03, s * 0.072, 0.062)
        et = eb + Vector((s * 0.050, -0.048, 0.228))
        u.add(K.olimb("hs_ear_%d" % s, eb, et,
                      [(0.0, 0.084, 0.056, 0.014), (0.55, 0.070, 0.044, 0.012),
                       (1.0, 0.026, 0.018, 0.006)]),
              "horse_head", "马体", "chunk", "horse", "ear")
    for s_ in (1, -1):
        u.rivet("hs_nostril_%d" % s_, hp(0.94, s_ * 0.050, 0.060), (s_ * 0.55, 0.62, 0.55),
                "horse_head", "皮革暗", "chunk", "horse", "muzzle", r=0.024, h=0.012, n=6)
    # 笼头：鼻革 + 颊革 + 衔铁（低分辨率下最便宜的"这是马"证据）
    for s_ in (1, -1):
        u.add(K.olimb("hs_cheekstrap_%d" % s_, hp(0.16, s_ * 0.070, -0.020),
                      hp(0.78, s_ * 0.058, -0.014),
                      [(0.0, 0.026, 0.020, 0.006), (1.0, 0.024, 0.018, 0.006)]),
              "horse_head", "皮革暗", "chunk", "horse", "bridle")
        u.add(ring("hs_bit_%d" % s_, hp(0.90, s_ * 0.070, -0.030), (s_, 0.0, 0.2),
                   0.020, 0.034, 0.010, 8),
              "horse_head", "钢", "chunk", "horse", "bridle")
    u.add(K.olimb("hs_noseband", hp(0.72, 0, 0.0), hp(0.745, 0, 0.0),
                  [(0.0, 0.150, 0.166, 0.030), (1.0, 0.148, 0.164, 0.030)]),
          "horse_head", "皮革暗", "chunk", "horse", "bridle")
    # 面甲（chamfron）：额 → 鼻梁的一片甲，金脊 + 蓝翎
    rows = []
    for (t, w) in ((0.05, 0.130), (0.34, 0.136), (0.62, 0.116), (0.84, 0.092)):
        c = hp(t, 0, 0.118)
        rows.append([(x, c.y, c.z) for x in (-w * 0.5, -w * 0.20, w * 0.20, w * 0.5)])
    u.add(K.grid_shell("hs_chamfron", rows, 0.024, inside=(0, 0.90, 1.68)),
          "horse_head", "甲", "chunk2", "horse", "chamfron")
    u.add(K.olimb("hs_chamfron_ridge", hp(0.06, 0, 0.150), hp(0.84, 0, 0.158),
                  [(0.0, 0.038, 0.034, 0.009), (1.0, 0.026, 0.024, 0.007)]),
          "horse_head", "team_trim", "chunk", "horse", "chamfron")
    # 翎座 + 三片蓝翎
    base = hp(0.04, 0, 0.128)
    u.add(K.olimb("hs_plume_base", base + Vector((0, 0.006, -0.022)),
                  base + Vector((0, 0.002, 0.024)),
                  [(0.0, 0.070, 0.070, 0.018), (1.0, 0.052, 0.052, 0.014)]),
          "horse_head", "team_trim", "chunk", "horse", "plume")
    for i, dx in enumerate((-0.030, 0.0, 0.030)):
        u.add(K.olimb("hs_plume_%d" % i, base + Vector((dx, 0.004, 0.014)),
                      base + Vector((dx * 2.1, -0.150, 0.196 - abs(dx) * 1.2)),
                      [(0.0, 0.040, 0.054, 0.009), (0.55, 0.048, 0.040, 0.009),
                       (1.0, 0.012, 0.018, 0.004)]),
              "horse_head", "team", "chunk", "horse", "plume")


def tail(u):
    u.add(K.olimb("hs_tail_01", TAIL_A, TAIL_B,
                  [(0.0, 0.106, 0.118, 0.028), (1.0, 0.082, 0.092, 0.022)]),
          "horse_tail_01", "马体", "chunk", "horse", "tail")
    u.add(K.olimb("hs_tail_02", TAIL_B, TAIL_C + Vector((0, -0.020, -0.090)),
                  [(0.0, 0.086, 0.096, 0.024), (0.48, 0.128, 0.118, 0.026),
                   (1.0, 0.052, 0.046, 0.014)]),
          "horse_tail_02", "皮革暗", "chunk", "horse", "tail")


# ── 4. 装备：鞍 / 马衣 / 胸甲 ───────────────────────────────────────────────
def tack(u):
    # 鞍垫（team 蓝，压在鞍下，两侧露一条金边）
    u.add(K.arc_panel("hs_blanket", [
        (1.602, 46, 314, 0.318, 0.466),
        (1.520, 46, 314, 0.332, 0.486),
        (1.452, 46, 314, 0.338, 0.494),
    ], 0.022, nu=16, inside=(0, -0.06, 1.50), center=(0, -0.060)),
        "horse_spine", "team", "chunk", "tack", "blanket")
    u.add(K.arc_panel("hs_blanket_hem", [
        (1.462, 46, 314, 0.341, 0.497),
        (1.424, 46, 314, 0.343, 0.500),
    ], 0.024, nu=16, inside=(0, -0.06, 1.46), center=(0, -0.060)),
        "horse_spine", "team_trim", "chunk", "tack", "blanket")
    # 鞍座（皮革）：前鞍桥 / 座 / 后鞍桥
    u.add(yloft("hs_saddle", [
        (0.170, 0, 1.612, 0.300, 0.070, 0.030),
        (0.090, 0, 1.650, 0.378, 0.098, 0.036),
        (-0.070, 0, 1.656, 0.396, 0.102, 0.038),
        (-0.220, 0, 1.644, 0.356, 0.092, 0.034),
        (-0.340, 0, 1.608, 0.276, 0.066, 0.028),
    ], cw=0.035), "horse_spine", "皮革", "chunk2", "tack", "saddle")
    u.add(yloft("hs_pommel", [
        (0.192, 0, 1.640, 0.152, 0.052, 0.020),
        (0.164, 0, 1.706, 0.132, 0.042, 0.018),
        (0.126, 0, 1.720, 0.112, 0.034, 0.014),
    ], cw=0.02), "horse_spine", "皮革", "chunk", "tack", "saddle")
    u.add(yloft("hs_cantle", [
        (-0.312, 0, 1.620, 0.244, 0.058, 0.024),
        (-0.352, 0, 1.682, 0.222, 0.048, 0.020),
        (-0.386, 0, 1.696, 0.192, 0.040, 0.016),
    ], cw=0.02), "horse_spine", "皮革", "chunk", "tack", "saddle")
    # 鞍翼（两侧垂片）+ 金边
    for s in (1, -1):
        u.add(K.plate("hs_flap_%d" % s,
                      [(-0.268, 1.614), (0.062, 1.614), (0.086, 1.474),
                       (-0.026, 1.416), (-0.244, 1.436)],
                      thickness=0.024, offset=s * 0.204, axis="X"),
              "horse_spine", "皮革", "chunk2", "tack", "flap")
        u.add(K.plate("hs_flap_rim_%d" % s,
                      [(-0.026, 1.416), (0.086, 1.474), (0.092, 1.456),
                       (-0.026, 1.398), (-0.250, 1.418), (-0.252, 1.436)],
                      thickness=0.026, offset=s * 0.205, axis="X"),
              "horse_spine", "team_trim", "chunk", "tack", "flap")
        # 马镫带 + 马镫（镫踏在 z=1.12，骑手脚掌正好踩上）
        u.box("hs_stir_up_%d" % s, (s * 0.330, 0.082, 1.404), (0.028, 0.024, 0.320),
              "horse_spine", "皮革暗", style="chunk", module="tack", tag="stirrup")
        u.add(ring("hs_stirrup_%d" % s, (s * 0.368, 0.100, 1.190), (1, 0, 0),
                   0.056, 0.084, 0.024, 10),
              "horse_spine", "钢", "chunk", "tack", "stirrup")
        u.box("hs_stir_tread_%d" % s, (s * 0.368, 0.100, 1.110), (0.106, 0.078, 0.020),
              "horse_spine", "钢", style="chunk", module="tack", tag="stirrup")
    # 肚带（绕桶身一圈）
    u.add(K.arc_panel("hs_girth", [
        (1.560, 42, 318, 0.300, 0.430),
        (1.300, 42, 318, 0.322, 0.452),
        (1.040, 42, 318, 0.310, 0.440),
    ], 0.022, nu=16, inside=(0, -0.02, 1.30), center=(0, -0.020)),
        "horse_spine", "皮革暗", "chunk", "tack", "girth")
    # 胸甲（peytral）：只做一条窄带 + 中央圆芯，不做整片浅色围裙
    u.add(K.arc_panel("hs_peytral", [
        (1.386, 214, 326, 0.262, 0.296),
        (1.300, 210, 330, 0.286, 0.322),
        (1.222, 214, 326, 0.268, 0.302),
    ], 0.026, nu=8, inside=(0, 0.28, 1.30), center=(0, 0.286)),
        "horse_chest", "皮革暗", "chunk2", "tack", "peytral")
    u.rivet("hs_peytral_boss", (0, 0.588, 1.300), (0, 1, 0.02),
            "horse_chest", "team_trim", "chunk", "tack", "peytral",
            r=0.044, h=0.018, n=8)

    # 马衣：从鞍后盖到臀，下摆按角度起伏（后中压到 1.02、两侧收在 1.20），金边
    def hem(i, nu=18):
        # i/nu 0→1 是 66°→294°（经过 180° = 正后）。后中做一个浅 V，两侧收高，露出后腿
        u_ = i / float(nu)
        rear = math.sin(math.pi * u_) ** 2.2
        return 1.180 - 0.120 * rear

    u.add(drape("hs_caparison", -0.300, 66, 294,
                [(1.520, 0.300, 0.402), (1.430, 0.352, 0.464),
                 (1.310, 0.382, 0.500), (1.196, 0.396, 0.516)],
                18, 0.024, (0, -0.30, 1.38), hem_z=hem),
          "horse_spine", "team", "chunk2", "tack", "caparison")
    u.add(drape("hs_caparison_hem", -0.300, 66, 294,
                [(1.208, 0.399, 0.519), (1.156, 0.401, 0.522)],
                18, 0.026, (0, -0.30, 1.34),
                hem_z=lambda i, nu=18: hem(i, nu) - 0.034),
          "horse_spine", "team_trim", "chunk", "tack", "caparison")
    # 马衣上的两枚金徽（左右臀侧）
    for s in (1, -1):
        u.add(K.plate("hs_emb_%d" % s,
                      [(-0.042, 1.352), (0.0, 1.408), (0.042, 1.352), (0.0, 1.296)],
                      thickness=0.016, offset=s * 0.398, axis="X"),
              "horse_spine", "team_trim", "chunk", "tack", "caparison")
    # 缰绳：从衔铁沿颈侧回到鞍桥（短、静态、不跨骨）
    for s in (1, -1):
        u.add(K.olimb("hs_rein_%d" % s, hp(0.86, s * 0.140, -0.010),
                      (s * 0.208, 0.410, 1.735),
                      [(0.0, 0.030, 0.022, 0.006), (1.0, 0.028, 0.020, 0.006)]),
              "horse_neck", "皮革暗", "chunk", "tack", "rein")


def build(u):
    body(u)
    legs(u)
    neck(u)
    head(u)
    tail(u)
    tack(u)
