"""st_kit.py —— **状态资产共用机械层**（升级态 / 训练态 / 科研态）

三类状态资产共用的是"机械"，不是"造型"：

  · 升级态 = 旧等级主体在某个标高**截断** + 生料截面 + 静态工地套件 + 新等级暗示件
  · 训练态 = 完整主体 + 门扇固定在打开角度 + 门内自发光 + 一件识别效果
  · 科研态 = 完整主体 + 工作机具（火焰 / 烟 / 锤 / 锯 / 原木 / 锯末）+ 一条 research clip

这里只放"截断 / 生料 / 套件摆场 / 合材质 / 导出 / 回查"，造型在各 st_*.py 里。
验收口径与九座一致：CLIP_CROSS 0 / COPLANAR_UP 0 / FLOAT 0 + grounded + front_ok，
另外状态档多三条：静态档零骨骼零动画、材质 ≤4、面数 ≤23k tri（科研档要求 research clip）。

坐标与九座一致：1 unit = 1 m，原点占地中心，z=0 地面，建模期 +Y 正面；
`finalize()` 最后沿 X 镜像 → 建模期 +X 在成品里是 −X。
"""
import hashlib
import json
import math
import os
import struct

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import convex_hull_2d

import bslib as L
import cs_kit
import st_atlas

FPS = 30
MAX_TRIS = 23000
MAX_MATS = 4


# ── 基础 ────────────────────────────────────────────────────────────────────
def jitter(name, amp):
    """按构件名取一个确定性的 ±amp 偏移 —— 不能每次跑出不同结果，否则报告对不上。"""
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16)
    return (h % 2000) / 1000.0 * amp - amp


def bake_transforms(items):
    """把 beam / taper_box 设过的 location+rotation 烘进网格。

    截断要在世界 z 上做平面切割，而 `beam()` 造出来的构件是"原点在物体原点、
    靠 transform 摆到位"的 —— 不先烘进去，切出来是斜的。
    """
    ident = Matrix.Identity(4)
    # 必须先求值一次：`beam()` / `taper_box()` 是"网格在原点、靠 transform 摆位"，
    # 而 matrix_world 是**上次 depsgraph 求值**的缓存 —— 刚建完的构件读到的还是单位矩阵。
    # 不 update 就烘，等于把斜撑按原点烘平（踩过：4 根山墙斜撑原封不动穿过截断面）。
    bpy.context.view_layer.update()
    for it in items:
        ob = it[0]
        mw = ob.matrix_world
        diff = max(abs(mw[i][j] - ident[i][j]) for i in range(4) for j in range(4))
        if diff > 1e-9:
            ob.data.transform(mw)
            ob.matrix_world = Matrix.Identity(4)


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                bpy.data.armatures, bpy.data.actions, bpy.data.cameras,
                bpy.data.lights, bpy.data.collections):
        for it in list(blk):
            try:
                blk.remove(it)
            except Exception:
                pass


# ── 截断 + 生料截面 ──────────────────────────────────────────────────────────
def _cap_face(ob, zc, mat_name):
    """在切口处把断口封成一张 n 边形（生料材质）。

    为什么是"补一张面"而不是"补一块板"：断口就是母材的横截面，补板会在板底
    和断口之间留一圈共面（COPLANAR_UP）。补面直接把开口封死，边缘与墙的竖面
    只共边、不共面。
    """
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    # 注意：顶点坐标必须在 bm.free() **之前**取样，free 之后 v.co 是野指针
    pts = [(v.co.x, v.co.y) for v in bm.verts if abs(v.co.z - zc) < 3e-3]
    bm.free()
    if len(pts) < 3:
        return None
    try:
        idx = convex_hull_2d(pts)
    except Exception:
        return None
    if len(idx) < 3:
        return None
    ztop = zc + 0.002
    verts = [(pts[i][0], pts[i][1], ztop) for i in idx]
    me = bpy.data.meshes.new("raw_cap")
    me.from_pydata(verts, [], [tuple(range(len(verts)))])
    me.validate(verbose=False)
    me.update()
    ob2 = bpy.data.objects.new("raw_cap", me)
    bpy.context.scene.collection.objects.link(ob2)
    ob2.data.materials.append(L.make_material(mat_name))
    # 单面片：法线朝上（凸包是 CCW，from_pydata 之后要确认一次）
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.faces and bm.faces[0].normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    return ob2


def cut_items(items, zcut, amp=0.10):
    """把构件列表按世界 z=zcut 截断（逐件带微小抖动，断口才不是一条水平线）。

    返回 (kept_items, caps, removed)。`kept_items` 里的构件网格已被改过；
    `caps` 是断口的生料封面（(ob, bevel, sub, seg) 三元组格式，可直接进 items）。
    """
    kept, caps, removed = [], [], []
    for it in items:
        ob = it[0]
        if not ob.data.vertices:
            continue
        zs = [v.co.z for v in ob.data.vertices]
        zc = zcut + jitter(ob.name, amp)
        if min(zs) >= zc:
            removed.append(ob.name)
            bpy.data.objects.remove(ob, do_unlink=True)
            continue
        kept.append(it)
        if max(zs) <= zc:
            continue
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        try:
            bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6,
                                   plane_co=(0.0, 0.0, zc), plane_no=(0.0, 0.0, 1.0),
                                   clear_outer=True, clear_inner=False)
        except Exception:
            bm.free()
            continue
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
        if not ob.data.vertices:
            removed.append(ob.name)
            bpy.data.objects.remove(ob, do_unlink=True)
            kept.pop()
            continue
        mat = ob.data.materials[0].name if ob.data.materials else "stone_mid"
        cap = _cap_face(ob, zc, st_atlas.raw_mat(mat))
        if cap is not None:
            caps.append((cap, 0.0, 0, 1))
    return kept, caps, removed


def raw_chunks(caps, per=2, seed=7, top=9):
    """断口上的碎料：小方块斜插在生料面上，把水平的断口线打碎。

    只给**断口面积最大的几处**加（默认 9 处、每处 1–2 块）：每个断口都加，
    俯视就是一地碎石；只在最大的截面加，读作"这面墙是从这儿断的"。
    """
    out = []
    rows = []
    for (cap, _b, _s, _g) in caps:
        vs = cap.data.vertices
        if len(vs) < 3:
            continue
        xs = [v.co.x for v in vs]
        ys = [v.co.y for v in vs]
        z = max(v.co.z for v in vs)
        w, d = max(xs) - min(xs), max(ys) - min(ys)
        rows.append((w * d, (max(xs) + min(xs)) * 0.5, (max(ys) + min(ys)) * 0.5,
                     w, d, z))
    rows.sort(reverse=True)
    rng = seed
    for (area, cx, cy, w, d, z) in rows[:top]:
        n = max(1, min(per, int(round(area / 1.6)) + 1))
        for _i in range(n):
            rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
            f1 = ((rng >> 8) % 1000) / 1000.0
            rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
            f2 = ((rng >> 8) % 1000) / 1000.0
            rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
            f3 = ((rng >> 8) % 1000) / 1000.0
            s = 0.15 + 0.11 * f1
            px = cx + (f1 - 0.5) * max(w - s, 0.0) * 0.9
            py = cy + (f2 - 0.5) * max(d - s, 0.0) * 0.9
            ob = L.box("raw_chunk", (px, py, z - s * 0.24),
                       (s, s * 0.84, s * 0.6),
                       L.make_material("raw_stone"),
                       rot=(0.26 * (f2 - 0.5), 0.24 * (f1 - 0.5), 2.6 * f3))
            out.append((ob, 0.006, 0, 1))
    return out


def interior_deck(body, zcut, slab_mat="stone_dark", joist_mat="wood_mid"):
    """断口下面的"楼下那层楼板" + 断口上的露明梁。

    空心建筑（墙是四块独立的盒子）截断之后，从 38° 俯角能**一直看到地面**——
    8 m 的进深在画面上没有深度线索，读成"这栋楼只有一层楼板"（二本升级态第一版）。
    补一块比墙内缩 0.35 的暗色楼板放在断口下方 0.30，视线就被截住了；
    梁再压在上面，俯视是"结构外露"，不是"平屋顶"。

    body = (x0, x1, y0, y1)。太窄（<2.4 m）就不做 —— 哨塔那种小进深补了反而糊。
    """
    out = []
    x0, x1, y0, y1 = body
    if (x1 - x0) < 2.4 or (y1 - y0) < 2.4:
        return out
    cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    w, d = (x1 - x0) - 0.70, (y1 - y0) - 0.70
    out.append((L.box("cap_floor", (cx, cy, zcut - 0.38), (w, d, 0.16),
                      L.make_material(slab_mat)), 0.0, 0, 1))
    # 露明梁：沿长边铺，间距 0.92
    if w >= d:
        n = max(3, int(round(d / 0.92)))
        for i in range(n):
            y = y0 + 0.55 + (d - 0.40) * i / max(1, n - 1)
            out.append((L.box("cap_joist", (cx, y, zcut - 0.06), (w - 0.10, 0.15, 0.20),
                              L.make_material(joist_mat)), 0.006, 0, 1))
    else:
        n = max(3, int(round(w / 0.92)))
        for i in range(n):
            x = x0 + 0.55 + (w - 0.40) * i / max(1, n - 1)
            out.append((L.box("cap_joist", (x, cy, zcut - 0.06), (0.15, d - 0.10, 0.20),
                              L.make_material(joist_mat)), 0.006, 0, 1))
    return out


def cap_joists(caps, min_area=2.6, spacing=0.92):
    """大断口上的**露明梁**：一排平行方木，读作"上一层的地板梁正在铺"。

    为什么必须有这一层：截断一栋楼时，凸包封面会盖出一整块 8~10 m 的平面，
    颜色再对也读成"这栋楼是平顶的"（大厅升级态第一版就是这样）。压一排梁上去，
    平面就被切成一条条缝 —— 俯视立刻变成"结构外露"，而且完全不增加悬空件
    （梁两端都压在断口边上）。
    """
    out = []
    rows = []
    for (cap, _b, _s, _g) in caps:
        vs = cap.data.vertices
        if len(vs) < 3:
            continue
        xs = [v.co.x for v in vs]
        ys = [v.co.y for v in vs]
        z = max(v.co.z for v in vs)
        w, d = max(xs) - min(xs), max(ys) - min(ys)
        if w * d < min_area:
            continue
        rows.append((w * d, min(xs), max(xs), min(ys), max(ys), z))
    for (area, x0, x1, y0, y1, z) in rows:
        w, d = x1 - x0, y1 - y0
        if w >= d:
            n = max(2, int(round(d / spacing)))
            for i in range(n):
                y = y0 + 0.28 + (d - 0.56) * i / max(1, n - 1)
                out.append((L.box("cap_joist", ((x0 + x1) * 0.5, y, z + 0.10),
                                (w - 0.34, 0.15, 0.19), L.make_material("wood_mid")),
                            0.006, 0, 1))
        else:
            n = max(2, int(round(w / spacing)))
            for i in range(n):
                x = x0 + 0.28 + (w - 0.56) * i / max(1, n - 1)
                out.append((L.box("cap_joist", (x, (y0 + y1) * 0.5, z + 0.10),
                                (0.15, d - 0.34, 0.19), L.make_material("wood_mid")),
                            0.006, 0, 1))
    return out


# ── 工地套件（静态摆场）───────────────────────────────────────────────────────
def _single_mat_obj(parts, name, mat_name):
    """一个构件组 → 只带一个材质槽的对象。

    套件原本是"一个 mesh 八个材质槽"（建造档靠顶点组驱动，一个对象最省事）；
    状态档要按材质合图集，多槽对象在 `join_by_material` 里会被按第 0 槽归组，
    其余槽的面就串色了。所以这里按 (骨, 材质) 拆开，每件只有一个槽。
    """
    verts, faces = [], []
    for (vs, fs, _mat, _bone, _cc) in parts:
        off = len(verts)
        verts.extend([tuple(v) for v in vs])
        for f in fs:
            faces.append(tuple(i + off for i in f))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(cs_kit.mat_site(mat_name))
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return ob


def site_objects(kit):
    """套件 → 按 (骨, 材质) 拆开的对象列表，名字沿用骨名（site_*）。"""
    groups = {}
    for p in kit.parts:
        groups.setdefault((p[3], p[2]), []).append(p)
    out = []
    for (bone, mat), parts in groups.items():
        ob = _single_mat_obj(parts, bone, mat)
        out.append((ob, 0.0, 0, 1))
    return out


def static_site(W, D, H, body=None, lifts=None, attach=None):
    """建一套静态工地件（放线 / 桩绳 / 脚手架 / 料堆 / 吊杆 / 队色 / 扬土）。"""
    kit = cs_kit.Kit(W, D, H, attach=attach, body=body)
    kit.build(lifts=lifts)
    return kit


# ── 训练态的门 ──────────────────────────────────────────────────────────────
def open_door(items, prefix, deg=108.0, hinge="minx"):
    """把门扇绕竖轴开到指定角度（默认 108°，开过 90° 才读得出"门开着"）。

    做法不是"换一扇新门"，而是把原门扇的顶点绕**门框上的铰链轴**转过去 ——
    门扇与门框的接触关系（销子那一条边）因此天然保留，不会凭空多出一条缝。
    hinge：minx / maxx 取包围盒的哪一条竖边当铰链。
    """
    moved = 0
    for it in items:
        ob = it[0]
        if not ob.name.startswith(prefix):
            continue
        vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
        if not vs:
            continue
        x0 = min(v.x for v in vs)
        x1 = max(v.x for v in vs)
        y0 = min(v.y for v in vs)
        y1 = max(v.y for v in vs)
        hx = x0 if hinge == "minx" else x1
        hy = y1 if abs(y1) > abs(y0) else y0
        pivot = Vector((hx, hy, 0.0))
        # 门朝建筑外侧（+Y）开：铰链在左端（minx）时是绕 Z **正**转，
        # 在右端（maxx）时反向 —— 顶点相对铰链的 x 符号变了，符号必须跟着变。
        ang = math.radians(deg) * (1 if hinge == "minx" else -1)
        rot = Matrix.Rotation(ang, 3, "Z")
        # 先烘掉物体级变换，再在世界坐标里转
        ob.data.transform(ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        for v in ob.data.vertices:
            v.co = pivot + rot @ (Vector(v.co) - pivot)
        ob.data.update()
        moved += 1
    return moved


# ── 合材质 / 导出 / 回查 ──────────────────────────────────────────────────────
def pack_state(objs, out_dir, label, prefix, include_emit=True):
    """按图集把 N 个对象压到 ≤4 个材质：主体 / team / team_trim / 自发光。"""
    miss = st_atlas.missing(objs)
    if miss:
        raise KeyError("这些材质不在 STATE_ORDER 里：%s" % ", ".join(miss))
    imgs = st_atlas.build_images(out_dir, label=label, include_emit=include_emit)
    cs = {st_atlas.bs_atlas.TAG_ATLAS: "sRGB", "ORM": "Non-Color",
          st_atlas.bs_atlas.TAG_EMIT: "sRGB"}
    for tag, img in imgs.items():
        img.colorspace_settings.name = cs[tag]
    st_atlas.pin_uv(objs)
    packed = st_atlas.pack(objs, imgs, prefix=prefix)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    return packed


def export_glb(objs, path, anim=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format="GLB", use_selection=True,
              export_yup=True, export_apply=False, export_materials="EXPORT",
              export_cameras=False, export_lights=False, export_extras=True,
              export_normals=True, export_tangents=False, export_texcoords=True,
              export_image_format="AUTO")
    if anim:
        kw.update(export_animations=True, export_animation_mode="ACTIONS",
                  export_nla_strips=False, export_bake_animation=False,
                  export_force_sampling=True, export_anim_slide_to_zero=True,
                  export_optimize_animation_size=False,
                  export_anim_single_armature=True, export_skins=True,
                  export_def_bones=False)
    else:
        kw.update(export_animations=False, export_skins=False)
    bpy.ops.export_scene.gltf(**kw)
    bpy.ops.object.select_all(action="DESELECT")
    return os.path.getsize(path)


def glb_json(path):
    """读 GLB 的 JSON 块（不做 Blender 导入，返回值就是引擎看到的那一份）。"""
    with open(path, "rb") as f:
        head = f.read(12)
        magic, ver, total = struct.unpack("<III", head)
        if magic != 0x46546C67:
            raise ValueError("不是 GLB: %s" % path)
        clen, ctype = struct.unpack("<II", f.read(8))
        js = json.loads(f.read(clen).decode("utf-8"))
        return js, total


def _acc_floats(js, blob, idx):
    acc = js["accessors"][idx]
    bv = js["bufferViews"][acc["bufferView"]]
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    count = acc["count"]
    stride = bv.get("byteStride") or (4 * ncomp)
    out = []
    for i in range(count):
        vals = struct.unpack_from("<" + "f" * ncomp, blob, off + i * stride)
        out.append(vals)
    return out


def glb_clips(path):
    """GLB 里的动画清单 + 每条 clip 的循环一致性（首帧 vs 末帧）。"""
    js, _total = glb_json(path)
    with open(path, "rb") as f:
        f.seek(12)
        clen, ctype = struct.unpack("<II", f.read(8))
        f.seek(12 + 8 + clen)
        blen, btype = struct.unpack("<II", f.read(8))
        blob = f.read(blen)
    out = []
    for anim in js.get("animations", []):
        chans = anim.get("channels", [])
        worst = 0.0
        dur = 0.0
        bad = []
        for ch in chans:
            sm = anim["samplers"][ch["sampler"]]
            t = _acc_floats(js, blob, sm["input"])
            if t:
                dur = max(dur, t[-1][0])
            v = _acc_floats(js, blob, sm["output"])
            if len(v) < 2:
                continue
            a, b = v[0], v[-1]
            if ch["target"]["path"] == "rotation":
                d = abs(sum(x * y for x, y in zip(a, b)))
                err = abs(1.0 - d)
            else:
                err = max(abs(x - y) for x, y in zip(a, b))
            if err > 1e-4:
                bad.append((ch["target"].get("node"), ch["target"]["path"], round(err, 5)))
            worst = max(worst, err)
        out.append({"name": anim.get("name"), "channels": len(chans),
                    "duration": round(dur, 3), "loop_err": round(worst, 6),
                    "loop_ok": worst <= 1e-3, "bad": bad[:6]})
    return out


def verify(path, front_ratio=1.0, anim=False, expect_clip="research"):
    """重新导入 GLB 回查：面数 / 材质 / 包围盒 / 贴地 / 朝向（+ 动画清单）。"""
    js, total = glb_json(path)
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=path)
    # 只算"有材质的网格"：glTF 导入器会给骨架建一个 Icosphere 占位件（不在 GLB 里），
    # 它 z −1..1，会把 grounded 判成失败。引擎看不到它，回查也不该算它。
    objs = [o for o in bpy.context.scene.objects
            if o.type == "MESH" and any(o.data.materials)]
    tris = 0
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objs:
        ob.data.calc_loop_triangles()
        tris += len(ob.data.loop_triangles)
        mw = ob.matrix_world
        for c in ob.bound_box:
            w = mw @ Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    names = sorted({m.name for o in objs for m in o.data.materials if m})
    rec = {
        "file": os.path.basename(path), "bytes": total, "meshes": len(objs),
        "tris": tris, "materials": names, "mat_count": len(names),
        "bbox_min": [round(v, 3) for v in lo],
        "bbox_max": [round(v, 3) for v in hi],
        "size": [round(v, 3) for v in (hi - lo)],
        # 源资产的石台本来就有 8–40 cm 埋进地形的一圈（建模规则 C32），
        # 状态档不动它的 z——所以贴地按"最低点不高于 0、不高于 12 cm"判。
        "grounded": bool(-0.12 <= lo.z <= 0.02),
        "zmin": round(lo.z, 3),
        "front_ok": bool(hi.y >= abs(lo.y) * front_ratio - 0.001),
        "mats_ok": len(names) <= MAX_MATS,
        "tris_ok": tris <= MAX_TRIS,
        "skins": len(js.get("skins", [])),
        "animations": [a.get("name") for a in js.get("animations", [])],
    }
    if anim:
        clips = glb_clips(path)
        rec["clips"] = clips
        rec["clip_ok"] = any(c["name"] == expect_clip and c["channels"] > 0
                             and c["loop_ok"] for c in clips)
    else:
        rec["static_ok"] = (rec["skins"] == 0 and not js.get("animations"))
    rec["ok"] = bool(rec["grounded"] and rec["front_ok"] and rec["mats_ok"]
                     and rec["tris_ok"]
                     and (rec["clip_ok"] if anim else rec["static_ok"]))
    return rec


# ── 场景收尾 ────────────────────────────────────────────────────────────────
def finish(objs, key, prefix, asset_dir, anim=False, front_ratio=1.0,
           expect_clip="research", post=None):
    """合图集 → 导 GLB → 回查。返回 (path, receipt)。

    图集落在 `<资产目录>/图集_状态/`，GLB 落在 `<资产目录>/<名>.glb` ——
    与 `<建筑>.glb` / `<建筑>_建造.glb` 各自独立，互不覆盖。

    `post(packed)` 给科研态用：合完材质之后再加骨架 / 绑蒙皮 / 烘 clip，
    返回"额外要一起导出的对象"（骨架）。静态档不传。
    """
    os.makedirs(asset_dir, exist_ok=True)
    atlas_dir = os.path.join(asset_dir, "图集_状态")
    path = os.path.join(asset_dir, key + ".glb")
    packed = pack_state(objs, atlas_dir, key, prefix, include_emit=True)
    extra = post(packed) if post else []
    export_glb(list(packed) + list(extra), path, anim=anim)
    rec = verify(path, front_ratio=front_ratio, anim=anim, expect_clip=expect_clip)
    return path, rec


def measure(objs_items):
    """构件列表 → (bbox_lo, bbox_hi, body=(x0,x1,y0,y1))。"""
    bpy.context.view_layer.update()
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for it in objs_items:
        ob = it[0] if isinstance(it, tuple) else it
        mw = ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    return lo, hi, (lo.x, hi.x, lo.y, hi.y)


def measure_body(items, zmin):
    """围墙的平面外沿：只取 z ≥ zmin 的顶点。
    为什么不直接用总包围盒：总盒把**院子和台阶**也算进去（哨塔 7.16×9.11，
    塔身只有 4.2×4.2）。拿总盒去搭脚手架，架子会围着空院子立一圈，读成鸟笼。
    院子那一圈仍然要包在**放线框**里（那是对的，工地围的是整块地），
    所以 W/D 用总盒、scaffold 的 body 用这一份。
    """
    lo = Vector((1e9, 1e9))
    hi = Vector((-1e9, -1e9))
    n = 0
    bpy.context.view_layer.update()
    for it in items:
        ob = it[0] if isinstance(it, tuple) else it
        mw = ob.matrix_world
        for v in ob.data.vertices:
            p = mw @ v.co
            if p.z < zmin:
                continue
            n += 1
            lo.x, lo.y = min(lo.x, p.x), min(lo.y, p.y)
            hi.x, hi.y = max(hi.x, p.x), max(hi.y, p.y)
    if n < 8:
        return None
    return (lo.x, hi.x, lo.y, hi.y)
