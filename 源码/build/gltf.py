"""
gltf.py —— glTF 2.0 / GLB 导出内核（仅依赖 numpy + struct/json）

本轮重写要点
------------
1. 面级输出：box_geometry 支持 faces 掩码（dedup_faces 的结果），被完全遮住的
   面不再生成三角形，三角面数直接降 30–50%。
2. 顶点 AO：支持 p["vcol"]（24 个顶点色，顺序跟随 FACE_DEF），输出 COLOR_0。
3. 图集 UV：支持 atlas 映射，把世界平铺 UV 按整数瓦片切开，逐瓦片重映射到
   2048 图集内的材质格；同时保留原 TEXCOORD_0（回退用），图集写在 TEXCOORD_1。
4. 骨骼装配：整栋建筑 = 1 个蒙皮网格（1 个材质 → 1 个 draw call），
   骨骼层级 = 阶段 → chunk。build 动阶段骨，destroy 动 chunk 骨，互不干扰。
"""
import json
import os
import struct
import math

F32 = 5126
U16 = 5123
U32 = 5125
U8 = 5121
ARRAY_BUFFER = 34962
ELEMENT_ARRAY_BUFFER = 34963

FACE_DEF = [
    # (normal, corner order as (sx,sy,sz) signs) —— 逆时针，法线朝外
    ((1, 0, 0),  [(1, 0, 1), (1, 0, 0), (1, 1, 0), (1, 1, 1)]),
    ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
    ((0, 1, 0),  [(0, 1, 1), (1, 1, 1), (1, 1, 0), (0, 1, 0)]),
    ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
    ((0, 0, 1),  [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]),
    ((0, 0, -1), [(1, 0, 0), (0, 0, 0), (0, 1, 0), (1, 1, 0)]),
]

FACE_AXIS = [(0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)]


# ------------------------------------------------------------------ 数学
def quat_from_euler(rx, ry, rz):
    """度数；顺序 Z*Y*X（先绕 X，再 Y，再 Z）。返回 (x,y,z,w)。"""
    hx, hy, hz = math.radians(rx) / 2, math.radians(ry) / 2, math.radians(rz) / 2
    cx, sx = math.cos(hx), math.sin(hx)
    cy, sy = math.cos(hy), math.sin(hy)
    cz, sz = math.cos(hz), math.sin(hz)
    qx = (sx, 0.0, 0.0, cx)
    qy = (0.0, sy, 0.0, cy)
    qz = (0.0, 0.0, sz, cz)

    def mul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return (
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        )

    return mul(qz, mul(qy, qx))


# ------------------------------------------------------------------ 盒体
def box_face_quads(box, tile=1.0, offset=(0.0, 0.0, 0.0)):
    """返回 6 个面的 [(face_index, [4 pos], [4 uv])]，法线顺序见 FACE_DEF。"""
    cx, cy, cz, sx, sy, sz = box
    ox, oy, oz = offset
    cx, cy, cz = cx - ox, cy - oy, cz - oz
    X = (cx - sx / 2, cx + sx / 2)
    Y = (cy - sy / 2, cy + sy / 2)
    Z = (cz - sz / 2, cz + sz / 2)
    out = []
    for fi, (n, corners) in enumerate(FACE_DEF):
        pos, uvs = [], []
        for c in corners:
            px, py, pz = X[c[0]], Y[c[1]], Z[c[2]]
            pos.append((px, py, pz))
            if n[0] != 0:
                u, v = (-pz if n[0] > 0 else pz), py
            elif n[1] != 0:
                u, v = px, (pz if n[1] > 0 else -pz)
            else:
                u, v = (px if n[2] > 0 else -px), py
            uvs.append((u / tile, v / tile))
        out.append((fi, n, pos, uvs))
    return out


def box_geometry(box, tile=1.0, offset=(0.0, 0.0, 0.0)):
    """兼容旧接口：整盒 24 顶点。"""
    pos, nrm, uvs, idx = [], [], [], []
    for _fi, n, P, U in box_face_quads(box, tile, offset):
        base = len(pos)
        pos += P
        nrm += [n] * 4
        uvs += U
        idx += [base, base + 1, base + 2, base, base + 2, base + 3]
    return pos, nrm, uvs, idx


def poly_face_frames(part):
    """把多面体 part 展开成 [(normal, [pos...]), ...]（顺序即 faces 顺序）。

    导出与顶点 AO 共用这一份遍历，保证 COLOR_0 的顶点序不错位。
    """
    import numpy as np
    V = part["verts"]
    out = []
    for f in part["faces"]:
        pts = [np.asarray(V[i], np.float64) for i in f]
        n = np.zeros(3)
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            n[0] += (a[1] - b[1]) * (a[2] + b[2])
            n[1] += (a[2] - b[2]) * (a[0] + b[0])
            n[2] += (a[0] - b[0]) * (a[1] + b[1])
        ln = float(np.linalg.norm(n))
        n = n / ln if ln > 1e-12 else np.array([0.0, 1.0, 0.0])
        out.append((tuple(float(x) for x in n), [tuple(float(x) for x in q) for q in pts]))
    return out


def _planar_uv(pos, n):
    """与 box_face_quads 同口径的平面投影：同轴相邻面纹理连续。"""
    x, y, z = pos
    if abs(n[0]) > max(abs(n[1]), abs(n[2])):
        return (-z if n[0] > 0 else z), y
    if abs(n[2]) > max(abs(n[0]), abs(n[1])):
        return (x if n[2] > 0 else -x), y
    return x, (z if n[1] > 0 else -z)


def _emit_poly(p, region, out, tile, bone, has_col, has_joint, offset):
    """把一个多面体 part 摊成"每面独立顶点"的三角形，写入 out 的各列表。

    与盒体路径的差别只在 UV：多面体的每个面按主法线做平面投影，UV 跨度
    超过一格时整格压到 0..1（否则会采样到图集里相邻材质的格子）。
    """
    P, N, U0, U1, I, J, W, C = out
    ox, oy, oz = offset
    ci = 0
    for n, pts in poly_face_frames(p):
        uv = [_planar_uv((x - ox, y - oy, z - oz), n) for (x, y, z) in pts]
        us = [u for u, _ in uv]
        vs = [v for _, v in uv]
        u0, v0 = min(us), min(vs)
        du = max(us) - u0
        dv = max(vs) - v0
        # 一律把这一面的 UV 跨度归一化到格内 [0,1]：
        # 多面体的面不按整数瓦片切开，若保留 (u - floor(u)) 的偏移，
        # 跨格的面会采样到隔壁材质格（木头上出现窗光的青色，就是这么来的）。
        # 用同一个比例缩放两轴：只归一化会让 1.1 × 0.22 的瓦片被拉成一整格
        s = 1.0 / max(du, dv, 1e-6)
        su = s
        sv = s
        fu = u0
        fv = v0
        base = len(P)
        for k, (x, y, z) in enumerate(pts):
            P.append((x - ox, y - oy, z - oz))
            u, v = uv[k]
            U0.append((u, v))
            if region:
                r0, r1, r2, r3 = region
                U1.append((r0 + ((u - fu) * su) * (r2 - r0),
                           r1 + ((v - fv) * sv) * (r3 - r1)))
            N.append(tuple(float(c) for c in n))
            if has_col:
                vc = p.get("vcol")
                C.append(vc[ci] if vc and ci < len(vc) else (1.0, 1.0, 1.0))
            if has_joint:
                J.append((bone or 0, 0, 0, 0))
                W.append((1.0, 0.0, 0.0, 0.0))
            ci += 1
        for k in range(1, len(pts) - 1):
            I += [base, base + k, base + k + 1]
    return ci


def _breakpoints(a, b):
    """把 [a,b] 按整数边界切开，返回 [(lo,hi,tile_floor), ...]。"""
    if abs(b - a) < 1e-9:
        return [(a, b, math.floor((a + b) * 0.5))]
    lo, hi = (a, b) if a < b else (b, a)
    cuts = [lo]
    k = math.floor(lo) + 1
    while k < hi - 1e-6:
        if k > lo + 1e-6:
            cuts.append(float(k))
        k += 1
    cuts.append(hi)
    out = []
    for i in range(len(cuts) - 1):
        l, h = cuts[i], cuts[i + 1]
        if h - l < 1e-7:
            continue
        out.append((l, h, math.floor((l + h) * 0.5)))
    if not out:
        out = [(lo, hi, math.floor(lo))]
    return out


def _bilinear(v, s, t):
    """v = [p00,p10,p11,p01]（与格子四角顺序一致）；支持 2D/3D/4D 向量。"""
    w0 = (1 - s) * (1 - t)
    w1 = s * (1 - t)
    w2 = s * t
    w3 = (1 - s) * t
    return tuple(w0 * a + w1 * b + w2 * c + w3 * d
                 for a, b, c, d in zip(v[0], v[1], v[2], v[3]))


# ------------------------------------------------------------------ 构建器
class Model:
    def __init__(self, name):
        self.name = name
        self.bin = bytearray()
        self.buffers_views = []
        self.accessors = []
        self.images = []
        self.samplers = []
        self.textures = []
        self.materials = []
        self.mat_index = {}
        self.meshes = []
        self.nodes = []
        self.animations = []
        self.skins = []
        self.scene_roots = []
        self._tex_dir = None
        self._tex_uri = None
        self.atlas = None            # {mat: (u0,v0,u1,v1)} 使用图集时设置

    # ---------------- 二进制
    def _align(self):
        while len(self.bin) % 4:
            self.bin.append(0)

    def _view(self, payload, target=None):
        self._align()
        off = len(self.bin)
        self.bin += payload
        bv = {"buffer": 0, "byteOffset": off, "byteLength": len(payload)}
        if target:
            bv["target"] = target
        self.buffers_views.append(bv)
        return len(self.buffers_views) - 1

    def _acc(self, arr, ctype, atype, target=None, minmax=False):
        import numpy as np
        a = np.ascontiguousarray(arr)
        bv = self._view(a.tobytes(), target)
        acc = {"bufferView": bv, "componentType": ctype, "count": int(a.shape[0]), "type": atype}
        if minmax:
            acc["min"] = [float(x) for x in np.atleast_1d(a.min(axis=0)).ravel()]
            acc["max"] = [float(x) for x in np.atleast_1d(a.max(axis=0)).ravel()]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    # ---------------- 纹理 / 材质
    def set_texture_dir(self, d, uri_prefix=None):
        self._tex_dir = d
        self._tex_uri = uri_prefix

    def _image(self, path, name=None):
        name = name or os.path.basename(path)
        if not self._tex_uri:
            with open(path, "rb") as f:
                data = f.read()
            bv = self._view(data)
            self.images.append({"bufferView": bv, "mimeType": "image/png", "name": name})
        else:
            self.images.append({"uri": f"{self._tex_uri}/{name}", "name": name})
        if not self.samplers:
            self.samplers.append({"magFilter": 9729, "minFilter": 9987,
                                  "wrapS": 10497, "wrapT": 10497})
        self.textures.append({"sampler": 0, "source": len(self.images) - 1})
        return len(self.textures) - 1

    def add_material(self, mat_name, emissive=False):
        if mat_name in self.mat_index:
            return self.mat_index[mat_name]
        d = self._tex_dir
        bc = self._image(os.path.join(d, f"{mat_name}_BC.png"))
        nr = self._image(os.path.join(d, f"{mat_name}_N.png"))
        orm = self._image(os.path.join(d, f"{mat_name}_ORM.png"))
        m = {
            "name": mat_name,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": bc},
                "metallicRoughnessTexture": {"index": orm},
                "baseColorFactor": [1, 1, 1, 1],
                "metallicFactor": 1.0,
                "roughnessFactor": 1.0,
            },
            "normalTexture": {"index": nr, "scale": 1.0},
            "occlusionTexture": {"index": orm, "strength": 1.0},
            "doubleSided": False,
            "alphaMode": "OPAQUE",
            "extras": {"tile": 1.0},
        }
        efile = os.path.join(d, f"{mat_name}_E.png")
        if os.path.exists(efile):
            em = self._image(efile)
            m["emissiveTexture"] = {"index": em}
            m["emissiveFactor"] = [1.0, 1.0, 1.0]
        else:
            m["emissiveFactor"] = [0.0, 0.0, 0.0]
        self.materials.append(m)
        self.mat_index[mat_name] = len(self.materials) - 1
        return self.mat_index[mat_name]

    def add_atlas_material(self, bid, atlas_files, name="atlas"):
        """整栋建筑 1 个材质：BC/N/ORM/E 四张 2048 图集，采样 TEXCOORD_1。"""
        if self.mat_index:
            return 0
        idx = {}
        for key, fn in atlas_files.items():
            idx[key] = self._image(os.path.join(self._tex_dir, fn), fn)
        base = idx["BC"]
        m = {
            "name": "atlas_" + bid,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": base, "texCoord": 1},
                "metallicRoughnessTexture": {"index": idx["ORM"], "texCoord": 1},
                "baseColorFactor": [1, 1, 1, 1],
                "metallicFactor": 1.0,
                "roughnessFactor": 1.0,
            },
            "normalTexture": {"index": idx["N"], "scale": 1.0, "texCoord": 1},
            "occlusionTexture": {"index": idx["ORM"], "strength": 1.0, "texCoord": 1},
            "emissiveTexture": {"index": idx["E"], "texCoord": 1},
            "emissiveFactor": [1.0, 1.0, 1.0],
            "doubleSided": False,
            "alphaMode": "OPAQUE",
            "extras": {"atlas": True},
        }
        self.materials.append(m)
        self.mat_index["__atlas__"] = 0
        return 0

    # ---------------- 网格
    def add_parts(self, parts, offset=(0, 0, 0), atlas=None):
        """生成 1 个 mesh。图集模式 → 全部构件塞进 1 个 primitive。"""
        import numpy as np
        by_mat = {}
        for p in parts:
            key = "__atlas__" if atlas else p["mat"]
            by_mat.setdefault(key, []).append(p)

        prims = []
        for mname, plist in by_mat.items():
            P, N, U0, U1, I, J, W, C = [], [], [], [], [], [], [], []
            has_joint = any(p.get("bone") is not None for p in plist)
            has_col = any(p.get("vcol") is not None for p in plist)
            for p in plist:
                tile = p["tile"]
                faces = p.get("faces")
                vcol = p.get("vcol")
                bone = p.get("bone")
                region = atlas.get(p["mat"]) if atlas else None
                if p.get("verts") is not None:
                    _emit_poly(p, region, (P, N, U0, U1, I, J, W, C), tile, bone,
                               has_col, has_joint, offset)
                    continue
                for fi, n, pos, uvs in box_face_quads(p["box"], tile, offset):
                    if faces is not None and not faces[fi]:
                        continue

                    cells = []
                    if region:
                        bu = _breakpoints(min(u for u, _ in uvs), max(u for u, _ in uvs))
                        bv = _breakpoints(min(v for _, v in uvs), max(v for _, v in uvs))
                        for (ul, uh, uf) in bu:
                            for (vl, vh, vf) in bv:
                                su0 = (ul - uvs[0][0]) / ((uvs[1][0] - uvs[0][0]) or 1e-9)
                                su1 = (uh - uvs[0][0]) / ((uvs[1][0] - uvs[0][0]) or 1e-9)
                                tv0 = (vl - uvs[0][1]) / ((uvs[3][1] - uvs[0][1]) or 1e-9)
                                tv1 = (vh - uvs[0][1]) / ((uvs[3][1] - uvs[0][1]) or 1e-9)
                                cells.append((su0, su1, tv0, tv1, uf, vf))
                    else:
                        cells = [(0.0, 1.0, 0.0, 1.0, 0, 0)]

                    for (s0, s1, t0, t1, uf, vf) in cells:
                        corners = [(s0, t0), (s1, t0), (s1, t1), (s0, t1)]
                        base = len(P)
                        for (s, t) in corners:
                            P.append(_bilinear(pos, s, t))
                            uv = _bilinear(uvs, s, t)
                            U0.append(uv)
                            if region:
                                u0, v0, u1, v1 = region
                                U1.append((u0 + (uv[0] - uf) * (u1 - u0),
                                           v0 + (uv[1] - vf) * (v1 - v0)))
                            N.append(n)
                            if has_col:
                                C.append(_bilinear(vcol[fi * 4:fi * 4 + 4], s, t))
                            if has_joint:
                                J.append((bone or 0, 0, 0, 0))
                                W.append((1.0, 0.0, 0.0, 0.0))
                        I += [base, base + 1, base + 2, base, base + 2, base + 3]

            attrs = {
                "POSITION": self._acc(np.array(P, np.float32), F32, "VEC3", ARRAY_BUFFER, minmax=True),
                "NORMAL": self._acc(np.array(N, np.float32), F32, "VEC3", ARRAY_BUFFER),
                "TEXCOORD_0": self._acc(np.array(U0, np.float32), F32, "VEC2", ARRAY_BUFFER),
            }
            if region:
                attrs["TEXCOORD_1"] = self._acc(np.array(U1, np.float32), F32, "VEC2", ARRAY_BUFFER)
            if has_col:
                attrs["COLOR_0"] = self._acc(np.array(C, np.float32), F32, "VEC3", ARRAY_BUFFER)
            if has_joint:
                attrs["JOINTS_0"] = self._acc(np.array(J, np.uint8), U8, "VEC4", ARRAY_BUFFER)
                attrs["WEIGHTS_0"] = self._acc(np.array(W, np.float32), F32, "VEC4", ARRAY_BUFFER)
            ctype = U16 if len(P) < 65535 else U32
            ind = np.array(I, np.uint16 if ctype == U16 else np.uint32)
            attrs_idx = self._acc(ind, ctype, "SCALAR", ELEMENT_ARRAY_BUFFER)
            prims.append({
                "attributes": attrs,
                "indices": attrs_idx,
                "material": 0 if atlas else self.add_material(mname),
                "mode": 4,
            })
        mesh = {"name": self.name + "_mesh", "primitives": prims}
        self.meshes.append(mesh)
        return len(self.meshes) - 1

    # ---------------- 节点
    def add_node(self, name, children=None, mesh=None, skin=None, translation=None,
                 rotation=None, scale=None):
        n = {"name": name}
        if children:
            n["children"] = children
        if mesh is not None:
            n["mesh"] = mesh
        if skin is not None:
            n["skin"] = skin
        if translation:
            n["translation"] = list(translation)
        if rotation:
            n["rotation"] = list(rotation)
        if scale:
            n["scale"] = list(scale)
        self.nodes.append(n)
        return len(self.nodes) - 1

    # ---------------- 蒙皮骨架
    def add_skinned_building(self, parts, bones, mesh_name=None):
        """bones: [{name, parent(索引|None), pivot(x,y,z), scale(可选)}]
        返回 (bone_node_ids, mesh_node_id, skin_index)。"""
        import numpy as np
        mesh = self.add_parts(parts, atlas=self.atlas)

        ids = []
        for b in bones:
            par = b.get("parent")
            p = b["pivot"]
            if par is None:
                local = list(p)
            else:
                pp = bones[par]["pivot"]
                local = [p[0] - pp[0], p[1] - pp[1], p[2] - pp[2]]
            sc = b.get("scale")
            ids.append(self.add_node(b["name"], translation=local,
                                     scale=(sc, sc, sc) if sc else None))
        for i, b in enumerate(bones):
            par = b.get("parent")
            if par is not None:
                self.nodes[ids[par]].setdefault("children", []).append(ids[i])

        ibm = []
        for b in bones:
            px, py, pz = b["pivot"]
            ibm.append([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -px, -py, -pz, 1])
        ibm_acc = self._acc(np.array(ibm, np.float32), F32, "MAT4")
        roots = [ids[i] for i, b in enumerate(bones) if b.get("parent") is None]
        self.skins.append({
            "joints": ids,
            "inverseBindMatrices": ibm_acc,
            "skeleton": roots[0],
            "name": "Armature",
        })
        arm = self.add_node("Armature", children=roots)
        mnode = self.add_node(mesh_name or (self.name + "_mesh"), mesh=mesh, skin=0)
        self.scene_roots = [arm, mnode]
        return ids, mnode, 0

    # ---------------- 动画
    def add_animation(self, name, channels, dur, rest_translation=None, extras=None):
        import numpy as np
        samplers, chans = [], []
        rest_translation = rest_translation or {}
        for bone, path, keys in channels:
            keys = sorted(keys, key=lambda k: k[0])
            times = np.array([k[0] for k in keys], np.float32)
            vals = []
            for t, v in keys:
                if path == "translation":
                    base = rest_translation.get(bone, (0, 0, 0))
                    vals.append((base[0] + v[0], base[1] + v[1], base[2] + v[2]))
                else:
                    vals.append(v)
            out = np.array(vals, np.float32)
            tin = self._acc(times, F32, "SCALAR", minmax=True)
            tout = self._acc(out, F32, "VEC4" if path == "rotation" else "VEC3")
            samplers.append({"input": tin, "output": tout, "interpolation": "LINEAR"})
            chans.append({"sampler": len(samplers) - 1, "target": {"node": bone, "path": path}})
        anim = {"name": name, "samplers": samplers, "channels": chans}
        if extras:
            anim["extras"] = extras
        self.animations.append(anim)
        return anim

    # ---------------- 输出
    def save(self, path):
        gltf = {
            "asset": {"version": "2.0", "generator": "WorkBuddy Voxel Foundry", "copyright": ""},
            "scene": 0,
            "scenes": [{"nodes": self.scene_roots, "name": self.name}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "accessors": self.accessors,
            "bufferViews": self.buffers_views,
            "buffers": [{"byteLength": 0}],
        }
        if self.textures:
            gltf["textures"] = self.textures
            gltf["images"] = self.images
            gltf["samplers"] = self.samplers
        if self.skins:
            gltf["skins"] = self.skins
        if self.animations:
            gltf["animations"] = self.animations

        bin_chunk = bytes(self.bin)
        if len(bin_chunk) % 4:
            bin_chunk += b"\x00" * (4 - len(bin_chunk) % 4)
        gltf["buffers"][0]["byteLength"] = len(bin_chunk)

        js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        if len(js) % 4:
            js += b" " * (4 - len(js) % 4)
        total = 12 + 8 + len(js) + 8 + len(bin_chunk)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(js), 0x4E4F534A))
            f.write(js)
            f.write(struct.pack("<II", len(bin_chunk), 0x004E4942))
            f.write(bin_chunk)
        return path
