"""td_model.py —— 地形地块：干裂泥地（低模 → 曲面细分）

思路
----
不是"在一个平面上贴裂纹贴图"，而是**把裂板真的做成几何**：
周期 Voronoi 切出 ~36 块板，每块向内缩 2.2 cm（缝宽 4.4 cm）、整块抬到自己的高度，
板与板之间就自然形成沟槽；板顶再贴一张"更细一档裂纹"的贴图（裂纹泥地.png），
于是近看有细裂纹、中看有板缝、远看是一整块干裂的土。

无缝
----
站点用 6×6 抖动格，距离按**周期**算（把邻域的 9 个平移副本一起参与切分），
所以每一块拼图边界上的板形与对面完全一致；板先内缩、再按 tile 方框裁切，
裁出来的直边在拼合时会与邻块的直边严丝合缝，不会在接缝处出现"沟"。

为什么低模之后再细分
--------------------
低模给的是**硬边**：板顶是平面多边形、侧壁是直上直下的四边形，读起来像干裂的
土块；Catmull-Clark 把板顶的边缘磨圆一圈，光打上去就有一道柔和的高光，
"晒干的泥板"这个质感全靠这一圈。倒角只做 1.5 cm，防止细分把棱磨得太糊。

坐标：X 右、Y 前、Z 上；原点在 tile 中心，z = 0 ≈ 板顶平均高度。
"""
import math
import random

import bpy
from mathutils import Vector

import bslib as L

# ── 尺寸 ────────────────────────────────────────────────────────────────────
W = 8.0                 # tile 边长（米）
GRID = 9                # 9×9 抖动格 → 81 块板（板宽 ≈ 0.89 m）
JITTER = 0.42           # 站点抖动（占格宽比例）
INSET = 0.006           # 板内缩 → 缝宽 = 2×INSET（细缝）
FLOOR_Z = -0.026        # 缝底（板顶只比它高 1.8–3.6 cm）
SLAB_Z = -0.130         # 底座底面
TOP_LO, TOP_HI = -0.017, 0.017   # 板顶高度区间（平均 ≈ 0）
SEED = 20261029

# 贴图：1 张 = 8 m（与 assets/地形/裂纹泥地.png 的约定一致）
TEX = "D:/测试一/assets/地形/裂纹泥地.png"


# ── 多边形工具（凸多边形，Sutherland–Hodgman） ──────────────────────────────
def clip_half(poly, nx, ny, d):
    """保留 nx·x + ny·y ≤ d 的一侧。"""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp = nx * p[0] + ny * p[1] - d
        dq = nx * q[0] + ny * q[1] - d
        if dp <= 0:
            out.append(p)
        if (dp < 0 < dq) or (dq < 0 < dp):
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def clip_rect(poly, x0, y0, x1, y1):
    poly = clip_half(poly, 1, 0, x1)
    poly = clip_half(poly, -1, 0, -x0)
    poly = clip_half(poly, 0, 1, y1)
    poly = clip_half(poly, 0, -1, -y0)
    return poly


def area(poly):
    s = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s * 0.5


def ccw(poly):
    return poly if area(poly) > 0 else list(reversed(poly))


def dedupe(poly, eps=0.02):
    """合并挨得太近的点。Voronoi 胞元里常出现 1 cm 级的退化边，
    直接拿去做内缩会因为它俩的偏移线几乎重合而算出**自交**多边形。"""
    out = []
    for p in poly:
        if not out or math.dist(p, out[-1]) > eps:
            out.append(p)
    if len(out) > 2 and math.dist(out[0], out[-1]) <= eps:
        out.pop()
    return out


def inset_poly(poly, t):
    """凸多边形等距内缩 —— 用**半平面裁剪**而不是"相邻偏移边求交"。

    求交法在退化边处会自交（踩过：整块地出现两个大洞）；半平面裁剪每一步都还是
    凸多边形，退化边只是让那一步白做一次，永远不会翻出去。
    """
    poly = ccw(dedupe(poly))
    n = len(poly)
    if n < 3:
        return []
    edges = [(poly[i], poly[(i + 1) % n]) for i in range(n)]   # 先定边：裁剪会让 poly 变短
    for a, b in edges:
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey)
        if ln < 1e-9:
            continue
        nx, ny = -ey / ln, ex / ln              # CCW：内法线 = 左法线
        # 内部满足 n·p ≥ n·a；内缩 t 后要保留 n·p ≥ n·a + t，写成 clip_half 的 ≤ 形式
        poly = clip_half(poly, -nx, -ny, -(nx * a[0] + ny * a[1] + t))
        if len(poly) < 3:
            return []
    return poly


def simplify(poly, tol=0.006):
    """去掉几乎共线的点：低模不要一堆 0.1 mm 的碎点。"""
    out = []
    n = len(poly)
    for i in range(n):
        a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        cross = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        if cross > tol * max(1e-6, math.dist(a, c)):
            out.append(b)
    return out if len(out) >= 3 else poly


# ── 周期 Voronoi ────────────────────────────────────────────────────────────
def sites(rnd):
    """9×9 抖动格站点，按网格索引存：{(gx, gy): (x, y)}，坐标在 [0, W)²。"""
    step = W / GRID
    grid = {}
    for gy in range(GRID):
        for gx in range(GRID):
            grid[(gx, gy)] = ((gx + 0.5) * step + rnd.uniform(-JITTER, JITTER) * step,
                              (gy + 0.5) * step + rnd.uniform(-JITTER, JITTER) * step)
    return grid


def cell_poly(grid, key):
    """第 key 个站点的 Voronoi 胞元（无界空间里算，可能伸出 tile 之外）。

    周期：只跟 ±2 圈邻格比（抖动 0.42 格时，胞元不会超出 1.5 格），
    超出网格的邻格按 ±W 平移进来 —— 这就是"周期 Voronoi"，接缝两侧的板形完全一致。
    """
    big = [(-W, -W), (2 * W, -W), (2 * W, 2 * W), (-W, 2 * W)]
    ax, ay = grid[key]
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx == 0 and dy == 0:
                continue
            lx, ly = key[0] + dx, key[1] + dy
            kx, ky = lx % GRID, ly % GRID
            bx, by = grid[(kx, ky)]
            bx += ((lx - kx) // GRID) * W
            by += ((ly - ky) // GRID) * W
            nx, ny = bx - ax, by - ay
            if abs(nx) < 1e-9 and abs(ny) < 1e-9:
                continue
            d = (bx * bx + by * by - ax * ax - ay * ay) * 0.5
            big = clip_half(big, nx, ny, d)
            if len(big) < 3:
                return []
    return dedupe(big)


def plate_pieces(grid, key):
    """胞元 → 内缩 → 按 tile 方框裁切（含 8 个平移），返回落在 tile 里的所有块。"""
    poly = cell_poly(grid, key)
    if len(poly) < 3:
        return []
    poly = inset_poly(poly, INSET)
    if len(poly) < 3:
        return []
    pieces = []
    for ox in (-W, 0.0, W):
        for oy in (-W, 0.0, W):
            piece = clip_rect(poly, ox, oy, ox + W, oy + W)
            if len(piece) >= 3 and abs(area(piece)) > 1e-4:
                # 平移到以原点为中心：tile 的占地是 [-W/2, W/2]²
                pieces.append([(x - ox - W * 0.5, y - oy - W * 0.5)
                               for x, y in piece])
    return pieces


def inside(poly, x, y, margin=0.0):
    """点是否在凸多边形内（带内缩余量）。"""
    poly = ccw(poly)
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(ex, ey) or 1e-9
        # 左侧为内：点到边的最短距离
        if (x - a[0]) * (-ey / ln) + (y - a[1]) * (ex / ln) < margin:
            return False
    return True


# ── 材质 ────────────────────────────────────────────────────────────────────
def mat_texture(name, path, mult=1.0):
    """贴图材质。mult 是整体明度倍率 —— 用同一张贴图做出"每块板干得不一样"的三档。"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path, check_existing=True)
    tex.extension = "REPEAT"
    tex.interpolation = "Linear"
    col_out = tex.outputs["Color"]
    if abs(mult - 1.0) > 1e-6:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(col_out, mix.inputs[6])
        mix.inputs[7].default_value = (mult, mult, mult, 1.0)
        col_out = mix.outputs[2]
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(col_out, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.96
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    m.diffuse_color = (0.22, 0.17, 0.12, 1)
    return m


def mat_flat(name, hexcol):
    return L.make_material(name) if name in L.PALETTE else _new_flat(name, hexcol)


def _new_flat(name, hexcol):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    col = L.srgb(hexcol)
    bsdf.inputs["Base Color"].default_value = (*col, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    m.diffuse_color = (*col, 1.0)
    return m


def uv_world(ob, tile=W, uv_off=(0.0, 0.0)):
    """UV = 世界 XY / tile（+ 每块板自己的偏移）。

    偏移是故意的：每块板的土干得不一样，颜色本来就该有差异；共用一张贴图时，
    把 UV 挪一挪就等于"每块板取到贴图的不同部位"，缝里又看不出来。
    """
    me = ob.data
    lay = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            lay.data[li].uv = (v.x / tile + uv_off[0], v.y / tile + uv_off[1])


# ── 几何：板 / 底座 ─────────────────────────────────────────────────────────
def offset_ring(poly, t):
    """沿角平分线把每个顶点内移 t（顶点数不变）。

    支撑环必须与顶面**同顶点数**：用内缩多边形的话，裁剪可能少掉几个点，
    环面就会连错顶点、渲染出黑色三角（第一版地板上那些黑箭头就是这么来的）。
    """
    poly = ccw(poly)
    n = len(poly)
    out = []
    for i in range(n):
        a, v, c = poly[i - 1], poly[i], poly[(i + 1) % n]
        ns = []
        for p0, p1 in ((a, v), (v, c)):
            ex, ey = p1[0] - p0[0], p1[1] - p0[1]
            ln = math.hypot(ex, ey) or 1e-9
            ns.append((-ey / ln, ex / ln))          # CCW 内法线
        bx, by = ns[0][0] + ns[1][0], ns[0][1] + ns[1][1]
        bl = math.hypot(bx, by) or 1e-9
        bx, by = bx / bl, by / bl
        k = t / max(0.25, bx * ns[0][0] + by * ns[0][1])
        out.append((v[0] + bx * k, v[1] + by * k))
    return out


def plate(name, poly, z_top, mat_top, mat_wall, ring=0.040, tilt=(0.0, 0.0),
          uv_off=(0.0, 0.0), dome=0.005):
    """一块裂板：顶面 + **一圈支撑环** + 侧壁。

    支撑环是"低模 + 细分"的关键：只有顶面和侧壁时，Catmull-Clark 会把整块板
    揉成一枚圆润的鹅卵石（第一版就是石板路）；顶面边缘多一圈 3 cm 的环，
    细分只会在这 3 cm 里把棱磨圆 —— 板顶保住平面，边缘又有一道柔和的高光。
    """
    poly = ccw(poly)
    inner = offset_ring(poly, ring)          # 顶点数必须与 poly 一致
    n = len(poly)
    m = n
    cx = sum(x for x, _ in poly) / n
    cy = sum(y for _, y in poly) / n
    # 每块板带一点倾斜：相邻板在缝口就会错开一个台阶，缝才像"裂开"而不是"砌缝"
    def z_of(x, y):
        return z_top + tilt[0] * (x - cx) + tilt[1] * (y - cy)
    verts = ([(x, y, z_of(x, y)) for x, y in poly]          # 0..n-1   外圈（顶）
             + [(x, y, z_of(x, y)) for x, y in inner]       # n..n+m-1 内圈（顶）
             + [(x, y, FLOOR_Z - 0.03) for x, y in poly]    # 侧壁底缘
             + [(cx, cy, z_of(cx, cy) + dome)])             # 顶心（微拱）
    base = 2 * n
    apex = 3 * n
    faces = []                                         # 顶面：内圈 → 顶心的扇形
    for i in range(n):
        faces.append((n + i, n + (i + 1) % n, apex))
    for i in range(n):                                 # 支撑环
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    for i in range(n):                                 # 侧壁
        j = (i + 1) % n
        faces.append((base + i, base + j, j, i))
    ob = L.mesh_obj(name, verts, faces, mat_top)       # 不 recalc：绕序已按外向写好
    ob.data.materials.append(mat_wall)
    n_top = len(faces) - n                             # 侧壁 = 最后 n 个面
    for idx in range(n_top, len(faces)):
        ob.data.polygons[idx].material_index = 1
    uv_world(ob, uv_off=uv_off)
    return ob


def slab(name, mat):
    return L.box(name, (0, 0, (SLAB_Z + FLOOR_Z) * 0.5),
                 (W, W, FLOOR_Z - SLAB_Z), mat)


def floor_plane(name, mat):
    me = bpy.data.meshes.new(name)
    h = W * 0.5
    me.from_pydata([(-h, -h, FLOOR_Z), (h, -h, FLOOR_Z), (h, h, FLOOR_Z),
                    (-h, h, FLOOR_Z)], [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    L.recalc_normals(ob)
    return ob


# ── 几何：道具 ──────────────────────────────────────────────────────────────
def rock(name, center, r, h, mat, rnd, sides=7):
    """矮胖的多面卵石：三圈 + 顶点，每圈半径抖一点。"""
    cx, cy, cz = center
    rings = ((0.0, 0.98), (0.42, 1.00), (0.78, 0.62))
    verts = []
    for z, k in rings:
        for i in range(sides):
            a = 2 * math.pi * i / sides + rnd.uniform(-0.12, 0.12)
            rr = r * k * rnd.uniform(0.86, 1.06)
            verts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr, cz + z * h))
    verts.append((cx + rnd.uniform(-0.15, 0.15) * r, cy + rnd.uniform(-0.15, 0.15) * r,
                  cz + h))
    top = len(verts) - 1
    faces = []
    for ri in range(len(rings) - 1):
        for i in range(sides):
            a0 = ri * sides + i
            a1 = ri * sides + (i + 1) % sides
            b0 = (ri + 1) * sides + i
            b1 = (ri + 1) * sides + (i + 1) % sides
            faces.append((a0, a1, b1, b0))
    for i in range(sides):
        faces.append(((len(rings) - 1) * sides + i,
                      (len(rings) - 1) * sides + (i + 1) % sides, top))
    ob = L.mesh_obj(name, verts, faces, mat)
    L.recalc_normals(ob)
    return ob


def tuft(name, center, h, mat, rnd, blades=9):
    """枯草簇：一圈向外倾的窄三角叶（单面片，双面材质可读）。"""
    cx, cy, cz = center
    verts, faces = [], []
    for i in range(blades):
        a = 2 * math.pi * i / blades + rnd.uniform(-0.35, 0.35)
        lean = rnd.uniform(0.28, 0.62)             # 越外侧越平
        hh = h * rnd.uniform(0.65, 1.0)
        ox, oy = math.cos(a), math.sin(a)
        w = 0.020 * rnd.uniform(0.7, 1.3)
        base = len(verts)
        verts.append((cx - oy * w, cy + ox * w, cz))
        verts.append((cx + oy * w, cy - ox * w, cz))
        verts.append((cx + ox * lean * hh, cy + oy * lean * hh, cz + hh))
        faces.append((base, base + 1, base + 2))
    ob = L.mesh_obj(name, verts, faces, mat)
    L.recalc_normals(ob)
    return ob


# ── 组装 ────────────────────────────────────────────────────────────────────
def build(smooth=True):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    rnd = random.Random(SEED)
    grid = sites(rnd)
    tops = {k: rnd.uniform(TOP_LO, TOP_HI) for k in grid}

    m_plate = [mat_texture("td_plate_a", TEX, 0.97),
               mat_texture("td_plate_b", TEX, 1.00),
               mat_texture("td_plate_c", TEX, 1.03)]
    m_crack = _new_flat("td_crack", "#4A3A28")
    m_slab = mat_flat("earth_dark", "#55432F")
    m_rock = _new_flat("td_rock", "#695C49")
    m_rock2 = _new_flat("td_rock_light", "#776956")
    m_dry = _new_flat("td_dry_grass", "#877F4E")

    # 板片先算一遍，几何和"道具落点"共用同一份数据
    pieces = []
    for key in grid:
        for k, piece in enumerate(plate_pieces(grid, key)):
            piece = simplify(piece)
            if len(piece) >= 3:
                tilt = (rnd.uniform(-0.022, 0.022), rnd.uniform(-0.022, 0.022))
                cx = sum(x for x, _ in piece) / len(piece)
                cy = sum(y for _, y in piece) / len(piece)
                pieces.append((piece, tops[key], key, k, tilt, (cx, cy)))

    plates = []
    for piece, ztop, key, k, tilt, _c in pieces:
        uvo = (rnd.uniform(0, 1), rnd.uniform(0, 1))
        mat = m_plate[rnd.randrange(3)]
        ob = plate("plate_%02dx%02d_%d" % (key[0], key[1], k), piece, ztop, mat,
                   m_crack, tilt=tilt, uv_off=uvo)
        plates.append(ob)

    slab_ob = slab("slab", m_slab)
    floor_ob = floor_plane("crack_floor", m_crack)

    # ── 道具：集中在前右一块，留出大片干净的泥板（构图紧凑但不平均） ──
    props = []
    # 候选锚点：前右 1/4 区域
    def pick_spot(rad, tries=800):
        """在一块**完全落在某块板内部**的地方落点（留安全边），返回贴面后的高度。

        构图：只在左前 1/4 的一小块里选点，让另外 3/4 保持干净的泥面 ——
        "装饰品要符合审美"首先是**不要撒满**。
        """
        for _ in range(tries):
            x = rnd.uniform(-W * 0.5 + 1.1, -W * 0.5 + 2.9)
            y = rnd.uniform(-W * 0.5 + 1.1, -W * 0.5 + 2.7)
            for piece, ztop, _key, _k, tilt, (cx, cy) in pieces:
                if inside(piece, x, y, margin=rad + 0.05):
                    if all((x - px) ** 2 + (y - py) ** 2 > (rad + pr + 0.05) ** 2
                           for px, py, pr in placed):
                        z = ztop + tilt[0] * (x - cx) + tilt[1] * (y - cy)
                        return (x, y, z)
        return None

    placed = []
    # 主石
    for idx, (r, h) in enumerate(((0.28, 0.17), (0.19, 0.12), (0.13, 0.08))):
        spot = pick_spot(r)
        if not spot:
            continue
        ob = rock("rock_%d" % idx, (spot[0], spot[1], spot[2] - 0.012), r, h, m_rock, rnd)
        props.append((ob, 0.02, 1))
        placed.append((spot[0], spot[1], r))
    # 碎石子
    for idx in range(9):
        r = rnd.uniform(0.040, 0.075)
        spot = pick_spot(r)
        if not spot:
            continue
        ob = rock("pebble_%d" % idx, (spot[0], spot[1], spot[2] - 0.006), r,
                  r * rnd.uniform(0.7, 1.1), m_rock, rnd, sides=5)
        props.append((ob, 0.006, 1))
        placed.append((spot[0], spot[1], r))
    # 枯草
    for idx in range(5):
        spot = pick_spot(0.12)
        if not spot:
            continue
        ob = tuft("tuft_%d" % idx, (spot[0], spot[1], spot[2] - 0.004),
                  rnd.uniform(0.30, 0.44), m_dry, rnd)
        props.append((ob, 0.0, 0))

    objs = plates + [slab_ob, floor_ob] + [p[0] for p in props]
    if smooth:
        # 地表**不做 Catmull-Clark**：它会把每块板磨成鹅卵石，"干裂"立刻变"石板路"
        # （A/B 见 docs/地形/地块/_cmp_lowpoly.png）。地表只给 6 mm 倒角 ——
        # 边缘有一道极细的高光就够了，板顶必须保住平面。
        for ob in plates:
            L.finalize(ob, bevel=0.006, seg=1, sub=0, angle=30.0)
        # 细分只给道具：卵石要圆，草叶不要。
        for ob, bev, sub in props:
            L.finalize(ob, bevel=bev, seg=1, sub=sub, angle=40.0)
    return objs, {"plates": len(plates), "props": len(props), "sites": len(grid)}
