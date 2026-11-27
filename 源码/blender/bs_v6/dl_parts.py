"""
dl_parts.py —— 失落帝国（Lost Empire）**共享零件库** v1

设计意图（2026-11-05 重做地牢入口时抽出来的）：

  这座包的每一座建筑都是"几何即代码"，但以前零件是**长在建筑脚本里**的 ——
  换一座要复制粘贴一遍，改一个尺寸要满文件找数字。这个文件把"能复用的东西"
  收到一处，只做三件事：

    1. **截面/体量原语**：loft2 / u_body / notch_band / step_run —— 失落帝国
       最常出现的"被掏空的实心块"，一次写好，四座都能用。
    2. **带语义的整件**：门扇 / 锁杠 / 断柱 / 骨 / 断链 / 翻倒的火盆。
       每件都吃参数、都能被 `spin()` 绕铰链整体转开（门要能开合）。
    3. **记号**：抓痕 / 拖痕 / 苔线 —— 只做"看得见的几何"，不做贴图。

约定：
  * 全部函数返回 **object 或 list[object]**，顶点已在世界坐标（bslib 的
    box/extrude 都是这样），所以 `spin()` 直接改顶点就能整体旋转。
  * 不碰材质表 —— 材质由调用方传进来（`M = bslib.all_materials()`）。
  * 不改任何全局状态、不建 collection。
  * 1 unit = 1 m；+Y 正面；z 向上。

坑（写代码前先读）：
  * `extrude()` 的 cap 面是一个 n-gon：**凹多边形（U 形）能不用就别用**，
    Blender 的三角化在极凹的角上会翻面；本文件用 `u_body()` 逐块拼 U 形，
    每块都是矩形，顶面共面但**互不重叠**，不会触发 COPLANAR_UP。
  * 任何"贴"上去的面都要离开母面 6 mm 以上（4 mm 是体检阈值）；
    要做凹槽就用"凸出来的一条暗色"，不要真的往里挖 —— 挖需要开洞。
  * `taper_box()` 的 p0 是**起点**（不是中心），`beam()` 的中点才是中心。
"""
import math
import random

import bpy
from mathutils import Matrix, Vector

import bslib as L
from bslib import beam, box, extrude, mesh_obj, revolve, taper_box

TAU = math.tau

# ── 通用小工具 ────────────────────────────────────────────────────────────────


# ── 失落帝国通用阵营色覆盖 ──────────────────────────────────────────────────
# 三座（地牢入口 / 地下城入口 / 折壳入口）共用这一份。
# team / team_trim 是引擎换阵营用的两个材质，**名字不能改**；但失落帝国是中立
# 废墟，套联盟的 #2E5FB4 会一眼读成"人族据点"。换成氧化铁红 + 灰骨粉笔 ——
# 读作"远征队刷在石头上的记号"，不是阵营旗色。
# bronze / iron 的金属度必须压：EEVEE 没有环境贴图时 metallic 0.7–0.9 会渲染成纯黑
# （氧化金属本来就是电介质，压到 0.15–0.45 才是对的）。
LE_TEAM_STYLE = {
    "team":        ("#743A2E", 0.78, 0.0),
    "team_trim":   ("#A99578", 0.84, 0.0),
    "bronze":      ("#6B8A75", 0.62, 0.18),
    "bronze_dark": ("#3C5347", 0.68, 0.15),
    "iron":        ("#3A3F47", 0.52, 0.45),
}


def _paint(mat, hexcol, rough=None, metal=None):
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return mat
    col = L.srgb(hexcol)
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    if rough is not None:
        bsdf.inputs["Roughness"].default_value = rough
    if metal is not None:
        bsdf.inputs["Metallic"].default_value = metal
    mat.diffuse_color = (*col, 1.0)
    return mat


def apply_team_style(style):
    """把一套"本阵营的色彩覆盖"套到场景里同名的材质上。

    桌面档（`restyle(M, ...)`）和手游图集档（`bs_atlas.pack` 会**按 PALETTE
    重新建** team / team_trim）必须走同一个来源，否则两个 GLB 的阵营色不一样
    —— 桌面是锈红、手游是联盟蓝，这种不一致比配色本身更糟。
    """
    if not style:
        return
    for name, spec in style.items():
        mat = bpy.data.materials.get(name)
        if mat is not None:
            _paint(mat, *spec)
        else:
            print("[team-style] 找不到材质：%s" % name)


def restyle(M, key, hexcol, rough=None, metal=None):
    """**换掉一个已有材质的基色**（只作用于当前资产）。

    为什么需要它：`team` / `team_trim` 是引擎换阵营用的两个材质，**名字不能改**
    （换色脚本按名字找）。但失落帝国是中立废墟，套上联盟的阵营蓝会一眼读成
    "人族据点" —— 这正是地牢 v1 被判"太像联盟"的第一条。
    所以在本资产里把这两个名字的基色换成**氧化铁红 / 灰骨粉笔**：
    仍然叫 team，仍然能被引擎换色，但预览图里读作"远征队刷在石头上的记号"。

    只改 Base Color / Roughness / Metallic 三个输入，不碰名字、不碰发光。
    """
    return _paint(M[key], hexcol, rough, metal)


def bake(obs):
    """把物体的 transform 烘进网格。

    `beam()/taper_box()` 返回的对象是**局部顶点 + 物体变换**（为了省一次矩阵乘），
    而 `box()/extrude()/revolve()` 是**世界顶点 + 单位变换**。两种混在一起时，
    任何直接改顶点的操作（spin / nudge / settle）都会算错 —— 先烘一次，后面统一。
    """
    for ob in obs:
        if ob is None:
            continue
        mw = ob.matrix_world.copy()
        if mw != Matrix.Identity(4):
            ob.data.transform(mw)
            ob.matrix_world = Matrix.Identity(4)
        ob.data.update()
    return obs


def spin(obs, pivot, ang, axis="Z"):
    """把一组构件绕 pivot 整体旋转（门扇铰链 / 翻倒的器物）。

    顶点是世界坐标，所以直接改顶点；物体自身的 transform 保持单位矩阵
    （`finalize()` 最后会 transform_apply，先烘掉更省事）。
    """
    obs = [o for o in obs if o is not None]
    if not ang:
        return bake(obs)
    bake(obs)
    piv = Vector(pivot)
    R = Matrix.Rotation(ang, 3, axis)
    for ob in obs:
        for v in ob.data.vertices:
            v.co = piv + R @ (v.co - piv)
        ob.data.update()
    return obs


def nudge(ob, dz=0.0, dx=0.0, dy=0.0):
    """整体平移（bbox 对齐用）。"""
    bake([ob])
    for v in ob.data.vertices:
        v.co.x += dx
        v.co.y += dy
        v.co.z += dz
    ob.data.update()
    return ob


def settle(obs, cx=0.0, cy=0.0, z=0.0, gap=0.004):
    """把一组构件按**最低点**落到 z，再平移到 (cx, cy)。

    器物件必须这样落位：`revolve()` 的碗翻倒以后最低点会跑到圆心的另一边，
    手写偏移一定会差几厘米（v1 的吊笼就是这么浮起来的）。
    """
    obs = [o for o in obs if o is not None]
    bake(obs)
    mn = min(v.co.z for ob in obs for v in ob.data.vertices)
    for ob in obs:
        for v in ob.data.vertices:
            v.co.x += cx
            v.co.y += cy
            v.co.z += z - mn - gap
        ob.data.update()
    return obs


def loft2(name, bot, top, z0, z1, mat):
    """上下两个同点数多边形之间放样（土丘 / 断柱顶 / 残石）。

    bot/top 是 [(x, y), ...]，同向、同点数。侧面四边形 + 上下 n-gon。
    **顶面是凸的才用它**；凹轮廓请拆块。
    """
    n = len(bot)
    verts = [Vector((x, y, z0)) for (x, y) in bot]
    verts += [Vector((x, y, z1)) for (x, y) in top]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    faces.append(tuple(range(n, 2 * n)))
    faces.append(tuple(range(n - 1, -1, -1)))
    return mesh_obj(name, verts, faces, mat)


def shrink(pts, k, cx=None, cy=None):
    """多边形按 k 收一圈（k<1 收，k>1 放）。"""
    cx = sum(p[0] for p in pts) / len(pts) if cx is None else cx
    cy = sum(p[1] for p in pts) / len(pts) if cy is None else cy
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for (x, y) in pts]


def jitter_pts(pts, amt, seed=0):
    """给轮廓顶点加一点不规则（土丘 / 塌口）。"""
    rnd = random.Random(seed)
    return [(x + rnd.uniform(-amt, amt), y + rnd.uniform(-amt, amt)) for (x, y) in pts]


# ── 1. 体量：U 形台体 / 凹槽压边 / 阶梯 ─────────────────────────────────────


def u_body(name, x, y0, y1, z0, z1, nx, ny0, mat):
    """**U 形实心台体**：正面（+Y）开一道槽，槽从 y1 一直切到 ny0。

    等价于"一块石头被挖掉一个方槽"。用三块矩形拼，不产生凹 n-gon：
        left   x0..-nx
        right  +nx..x1
        back   -nx..+nx, y0..ny0
    三块的顶面同高、互不重叠（只共边），体检不会报 COPLANAR_UP。

    返回 [left, right, back]。
    """
    out = []
    out.append(box(name + "_l", (-(x + nx) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5),
                   (x - nx, y1 - y0, z1 - z0), mat))
    out.append(box(name + "_r", ((x + nx) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5),
                   (x - nx, y1 - y0, z1 - z0), mat))
    if ny0 > y0:
        out.append(box(name + "_b", (0.0, (y0 + ny0) * 0.5, (z0 + z1) * 0.5),
                       (nx * 2, ny0 - y0, z1 - z0), mat))
    return out


def notch_band(name, nx, ny0, y1, z0, z1, w, mat, side_inset=0.0):
    """沿 U 形槽两侧的**压边**（顶面一圈亮边，俯视全靠它定形）。

    两条长条，从槽口 y1 一直退到 ny0；`side_inset` >0 时向外让开，
    用来制造"压边悬出墙面 4 cm"的阴影线。
    """
    x0 = nx - side_inset
    x1 = nx + w
    out = []
    for s in (-1, 1):
        cx = s * (x0 + x1) * 0.5
        out.append(box(name + ("_l" if s < 0 else "_r"),
                       (cx, (ny0 + y1) * 0.5, (z0 + z1) * 0.5),
                       (x1 - x0, y1 - ny0, z1 - z0), mat))
    return out


def step_run(name, x, y_front, z_top, n, rise, tread, mat, mat_nose=None,
             nose=(0.10, 0.075), mat_riser=None):
    """**台阶**：n 级，从 y_front 往 -Y 方向往上退。

    每级是一块落到 z=0 的实心块（不做薄片，RTS 下薄片会闪）。
    **踢面与踏面必须分两个材质**：低模无贴图、又没有 AO，同一材质时整跑台阶
    在 26° 机位下会糊成一块斜坡（v2 第二版就是这么翻车的）。踏面亮、踢面暗，
    三条横向明暗带就是"这里在往下走"的全部信息。
    `mat_nose` 是踏面前缘的一条窄亮条（磨亮的边）。
    返回 [step..., nose...]。
    """
    out = []
    for i in range(n):
        zt = z_top - i * rise
        cy = y_front - (i + 0.5) * tread
        body = mat_riser or mat
        # 踢面体：落到 z=0
        out.append(box(name + "_s%d" % i, (0.0, cy, (zt - 0.115) * 0.5),
                       (x * 2, tread, zt - 0.115), body))
        # 踏面：一块 55 mm 的亮板，前缘出挑 30 mm（自阴影线）
        out.append(box(name + "_t%d" % i, (0.0, cy + 0.015, zt - 0.0575),
                       (x * 2, tread + 0.03, 0.115), mat))
        if mat_nose is not None:
            ny, nz = nose
            out.append(box(name + "_n%d" % i,
                           (0.0, y_front - i * tread - ny * 0.5 + 0.006,
                            zt - nz * 0.5 + 0.010),
                           (x * 2 - 0.02, ny, nz), mat_nose))
    return out


# ── 2. 门：门扇 / 锁杠 / 门环 / 门槛 ────────────────────────────────────────


def door_leaf(name, hinge_x, y, z0, w, h, t, side, ang, M,
              bands=2, studs=(3, 3), ring=False, chip=0.0, panel=0.0, face=1):
    """**一扇门**（可开合）。

    参数
      hinge_x  铰链所在的 x（门轴）
      side     +1 门扇向 +x 展开，-1 向 -x
      ang      开合角（弧度，绕门轴）。0 = 关死；正值 = 往 -Y（门里）推开
      bands    横向铁箍条数；studs = (列, 行) 门钉；ring 是否有铜门环
      chip     上沿缺口比例（0 = 完整；0.18 = 右上角崩掉 18% 宽）
      panel    门板线脚的内缩量（0 = 不做；0.2 = 四边各让 20 cm，中间成凹面）
      face     门饰朝哪一侧：+1 = +Y（建模期的正面，默认），-1 = 朝里

    **face 不是可有可无的**：建模式 +Y 是正面，门饰（线脚/门钉/门环）必须朝 +Y。
    早期版本把偏移写死成 `y - t/2 - δ`（朝 -Y），结果整扇门从外面看只有两道铁箍，
    线脚、门钉、门环全在隧道里侧 —— 从外面拍近景是"一块光板"（2026-11-05 修的）。
    返回 list。**所有件都注册在同一个 hinge 上，改 `ang` 一个数就能开门。**
    """
    mat_body = M["door_stone"]
    mat_iron = M["iron"]
    obs = []
    hw = w * 0.5
    cx = hinge_x + side * hw

    # 门板：上沿按 chip 切一刀（用 extrude 做轮廓，缺口是真的轮廓）
    if chip > 0.001:
        prof = [(0.0, h), (w * (1.0 - chip), h), (w, h - chip * w), (w, 0.0), (0.0, 0.0)]
        plate = extrude(name + "_slab", [(side * u, v) for (u, v) in prof],
                        "Y", t, (hinge_x, z0), mat_body, offset=y)
    else:
        plate = box(name + "_slab", (cx, y, z0 + h * 0.5), (w, t, h), mat_body)
    obs.append(plate)

    fh = face * (t * 0.5)          # 门饰所在的"面"到门板中心的距离（带符号）
    if panel > 0.02:
        py0, py1 = z0 + panel, z0 + h - panel
        px0 = hinge_x + side * panel
        px1 = hinge_x + side * (w - panel)
        bw = 0.085
        pm = M["ancient_mid"]
        obs.append(box(name + "_pl", (px0, y + fh + face * 0.018,
                                      (py0 + py1) * 0.5), (bw, 0.036, py1 - py0), pm))
        obs.append(box(name + "_pr", (px1, y + fh + face * 0.018,
                                      (py0 + py1) * 0.5), (bw, 0.036, py1 - py0), pm))
        obs.append(box(name + "_pb", ((px0 + px1) * 0.5, y + fh + face * 0.018, py0),
                       (px1 - px0, 0.036, bw), pm))
        obs.append(box(name + "_pt", ((px0 + px1) * 0.5, y + fh + face * 0.018, py1),
                       (px1 - px0, 0.036, bw), pm))

    for i in range(bands):
        zz = z0 + h * (0.30 + 0.40 * i / max(bands - 1, 1)) if bands > 1 else z0 + h * 0.5
        obs.append(box(name + "_band%d" % i, (cx, y, zz), (w * 0.99, t + 0.06, 0.085),
                       mat_iron))
        # 箍上的铆钉
        for k in range(4):
            xx = hinge_x + side * (0.20 + (w - 0.40) * k / 3.0)
            for sgn in (-1, 1):
                obs.append(box(name + "_rv%d_%d" % (i, k * 2 + (sgn > 0)),
                               (xx, y + sgn * (t * 0.5 + 0.028), zz),
                               (0.048, 0.03, 0.048), mat_iron))

    cols, rows = studs
    for c in range(cols):
        for r in range(rows):
            xx = hinge_x + side * (0.28 + (w - 0.56) * c / max(cols - 1, 1))
            zz = z0 + h * (0.12 + 0.66 * r / max(rows - 1, 1))
            obs.append(box(name + "_stud%d_%d" % (c, r), (xx, y + fh + face * 0.022, zz),
                           (0.058, 0.03, 0.058), mat_iron))

    if ring:
        rx = hinge_x + side * (w * 0.72)      # 往里挪：贴边会读成门框上的挂件
        ring_ob = L.ring_y(name + "_ring", (rx, y + fh + face * 0.052, z0 + h * 0.52),
                           0.115, 0.165, 0.050, 9, M["bronze"])
        obs.append(ring_ob)
        # 门环的挂座：一小块铜板，别让圆环"浮"在门板上
        obs.append(box(name + "_ringseat", (rx, y + fh + face * 0.02, z0 + h * 0.52 + 0.23),
                       (0.18, 0.05, 0.11), M["bronze_dark"]))

    return spin(obs, (hinge_x, y, z0), ang)


def lock_bar(name, x0, x1, y, z, hw, M, w=0.13, brackets=True):
    """横贯两扇门的大铜栓 + 两个座（关死的**证据**，比任何贴图都管用）。"""
    obs = [box(name + "_bar", ((x0 + x1) * 0.5, y, z),
               (abs(x1 - x0), w, hw), M["iron"])]
    if brackets:
        for xx in (x0, x1):
            obs.append(box(name + "_brk", (xx, y + 0.01, z), (0.17, 0.19, hw + 0.10),
                           M["bronze_dark"]))
    # 栓中间的铜锁：一个方块 + 一道环
    obs.append(box(name + "_lock", ((x0 + x1) * 0.5, y - w * 0.55, z - hw * 0.55),
                   (0.17, 0.13, 0.22), M["bronze_dark"]))
    obs.append(L.ring_y(name + "_lockring", ((x0 + x1) * 0.5, y - w * 0.55, z + hw * 0.55),
                        0.035, 0.055, 0.03, 6, M["bronze"]))
    return obs


# ── 3. 遗迹：断柱 / 土丘 / 残墙块 ───────────────────────────────────────────


def column_ruin(name, cx, cy, z0, h, w, M, courses=4, seed=7, cap=True,
                bend=0.0):
    """**断柱**：几段错缝的方石 + 一个被砸断的顶（用 loft2 收一个斜口）。

    `bend` 让每一段沿 x 轻微偏移（柱子被压弯 / 倒了一半），单位 m。
    """
    rnd = random.Random(seed)
    obs = []
    seg = h / courses
    for i in range(courses):
        cw = w * (1.0 - 0.02 * i) + rnd.uniform(-0.012, 0.012)
        off = bend * (i / max(courses - 1, 1))
        z0i = z0 + i * seg
        obs.append(box(name + "_c%d" % i, (cx + off, cy + rnd.uniform(-0.01, 0.01),
                                          z0i + seg * 0.5),
                       (cw, cw * rnd.uniform(0.94, 1.04), seg * 0.985), M["ancient"]))
    top = z0 + h
    tw = w * 0.5
    base = [(cx - w * 0.5, cy - w * 0.5), (cx + w * 0.5, cy - w * 0.5),
            (cx + w * 0.5, cy + w * 0.5), (cx - w * 0.5, cy + w * 0.5)]
    tl = [(cx - tw + 0.06, cy - tw), (cx + tw, cy - tw * 0.7),
          (cx + tw * 0.7, cy + tw), (cx - tw, cy + tw * 0.8)]
    obs.append(loft2(name + "_break", base, tl, top - 0.02, top + 0.14 + 0.10,
                     M["ancient"]))
    if cap:
        obs.append(box(name + "_cap", (cx, cy, z0 + h + 0.02),
                       (w * 1.18, w * 1.18, 0.10), M["ancient_pale"]))
    return obs


def mound(name, pts, z0, z1, M, inset=0.82, seed=3, mat=None):
    """**土丘**：一个不规则多边形往上收（顶比底小），顶面再铺一块深色。

    这是"失序"最省面的写法：不做噪声、不做球，靠轮廓的不规则 + 收分。
    """
    mat = mat or M["earth_dark"]
    bot = jitter_pts(pts, 0.05, seed)
    top = shrink(jitter_pts(pts, 0.09, seed + 1), inset)
    out = [loft2(name + "_b", bot, top, z0, z1, mat)]
    out.append(loft2(name + "_cap", shrink(top, 0.72), shrink(top, 0.52),
                     z1 - 0.02, z1 + 0.09, M["earth_dark"]))
    return out


def rubble_slab(name, cx, cy, z, w, d, t, ang, tilt, M, mat=None):
    """**落石 / 斜靠的石板**：一块带 yaw + tilt 的板，底部按最低点落位。"""
    mat = mat or M["ancient"]
    ob = box(name, (0.0, 0.0, 0.0), (w, d, t), mat)
    R = (Matrix.Rotation(ang, 3, "Z") @ Matrix.Rotation(tilt, 3, "X"))
    for v in ob.data.vertices:
        v.co = R @ v.co
    mn = min(v.co.z for v in ob.data.vertices)
    for v in ob.data.vertices:
        v.co.z += z - mn - 0.004
        v.co.x += cx
        v.co.y += cy
    ob.data.update()
    return ob


# ── 4. 生物：骨 / 根 ────────────────────────────────────────────────────────


def bone_long(name, p0, p1, r, M, dark=False, knuckle=True):
    """**一根长骨**：中间细、两头粗（两个关节块）。骨不能是圆柱 —— 圆柱读成管子。"""
    mat = M["bone_dark"] if dark else M["bone"]
    obs = [taper_box(name + "_shaft", p0, p1, r * 2.0, r * 1.7, r * 1.5, r * 1.3, mat)]
    if knuckle:
        for (p, s) in ((p0, 1.0), (p1, 1.0)):
            obs.append(box(name + "_kn", p, (r * 2.9, r * 2.9, r * 2.6), mat,
                           rot=(0.2, 0.1, 0.0)))
    return obs


def bone_stack(name, cx, cy, z, M, n=4, seed=11, r=0.055):
    """**骨堆**：几根长骨横竖交叉叠着（不是头骨堆 —— 那会变成鬼屋道具）。"""
    rnd = random.Random(seed)
    obs = []
    for i in range(n):
        a = rnd.uniform(0, TAU)
        L0 = rnd.uniform(0.42, 0.78)
        zz = z + 0.055 + i * 0.052
        ox, oy = cx + rnd.uniform(-0.10, 0.10), cy + rnd.uniform(-0.10, 0.10)
        p0 = (ox - math.cos(a) * L0 * 0.5, oy - math.sin(a) * L0 * 0.5, zz)
        p1 = (ox + math.cos(a) * L0 * 0.5, oy + math.sin(a) * L0 * 0.5, zz)
        obs += bone_long(name + "_%d" % i, p0, p1, r * rnd.uniform(0.85, 1.2), M,
                         dark=(i % 3 == 2))
    return obs


def root_strands(name, x, y, z_top, M, n=3, seed=5, length=0.55):
    """**垂根**：从石缝里挂下来的一小束（两根一折，读作"软的东西"）。"""
    rnd = random.Random(seed)
    obs = []
    for i in range(n):
        xx = x + rnd.uniform(-0.10, 0.10)
        yy = y + rnd.uniform(-0.04, 0.04)
        l1 = length * rnd.uniform(0.55, 0.9)
        p0 = (xx, yy, z_top - i * 0.013)
        p1 = (xx + rnd.uniform(-0.06, 0.06), yy + rnd.uniform(-0.03, 0.05), z_top - l1)
        p2 = (p1[0] + rnd.uniform(-0.05, 0.05), p1[1], z_top - l1 * rnd.uniform(1.3, 1.7))
        obs.append(beam(name + "_a%d" % i, p0, p1, 0.035, 0.028, M["wood_dark"], up="Z"))
        obs.append(beam(name + "_b%d" % i, p1, p2, 0.026, 0.022, M["wood_dark"], up="Z"))
    return [o for o in obs if o is not None]


# ── 5. 器物：翻倒的火盆 / 半埋的铁栅 ────────────────────────────────────────


def brazier_tipped(name, cx, cy, z, M, ang=0.0, tilt=1.62,
                   mat_bowl="bronze_dark", mat_rim="bronze_dark"):
    """**翻倒的火盆**：碗倒扣、灰洒出来、两颗冷炭。落位走 `settle()`。"""
    obs = []
    bowl = revolve(name + "_bowl",
                   [(0.10, 0.00), (0.27, 0.06), (0.31, 0.17), (0.27, 0.22), (0.11, 0.22)],
                   8, (0.0, 0.0, 0.0), M[mat_bowl])
    spin([bowl], (0.0, 0.0, 0.05), tilt, "X")
    obs.append(bowl)
    obs.append(box(name + "_base", (0.0, 0.0, 0.0), (0.34, 0.34, 0.10), M[mat_rim]))
    obs.append(box(name + "_ash", (0.0, 0.34, 0.012), (0.42, 0.38, 0.024), M["coal"]))
    for i, (ax, ay) in enumerate(((-0.06, 0.24), (0.09, 0.36), (0.01, 0.50))):
        obs.append(box(name + "_emb%d" % i, (ax, ay, 0.028), (0.07, 0.05, 0.03),
                       M["ember"]))
    spin(obs, (0.0, 0.0, 0.0), ang)
    return settle(obs, cx, cy, z)


def ground_grate(name, cx, cy, z, M, w=1.05, d=0.72, ang=0.0, tilt=0.18):
    """**半埋的铁栅**：斜插在土里，只露出 2/3。"""
    import dl_kit as K
    obs = K.grate(name, 0.0, 0.0, 0.0, w, d, bars=5,
                  mat=M["bronze_dark"], frame_mat=M["bronze"])
    spin(obs, (0.0, 0.0, 0.0), tilt, "X")
    spin(obs, (0.0, 0.0, 0.0), ang, "Z")
    for ob in obs:
        nudge(ob, dz=z, dx=cx, dy=cy)
    return obs
