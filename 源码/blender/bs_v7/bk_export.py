# -*- coding: utf-8 -*-
"""bk_export.py —— 兵营三档 GLB（两槽制 / 顶点色 / 原点在底座底面中心）

和 th_export 的差别只有两条：
  1. 只有 Mat_TeamColor 一个队色槽，回写它的 baseColorFactor 就够；
  2. 队色件的顶点色必须是纯白 —— 导出后要逐个 primitive 验，防止
     "蓝 × 灰" 把阵营色乘脏。

导出参数：export_vertex_color='ACTIVE'。用 MATERIAL 的话，队色材质没有
Color Attribute 节点，那一批 primitive 就不会带 COLOR_0，引擎里同一栋楼
会出现"有的面吃顶点色、有的不吃"的分裂。
"""
import json
import os
import struct
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import mkit      # noqa: E402
import bk_model  # noqa: E402

OUTDIR = os.path.join(ROOT, "assets", "建筑", "联盟", "兵营_微缩")


def read_glb(path):
    raw = open(path, "rb").read()
    magic, ver, total = struct.unpack("<III", raw[:12])
    assert magic == 0x46546C67, "not a GLB"
    off, chunks = 12, []
    while off < total:
        ln, ctype = struct.unpack("<II", raw[off:off + 8])
        chunks.append((ctype, raw[off + 8:off + 8 + ln]))
        off += 8 + ln + (4 - ln % 4) % 4
    return chunks


def write_glb(path, chunks):
    body = b""
    for ctype, data in chunks:
        pad = (4 - len(data) % 4) % 4
        data = data + (b" " if ctype == 0x4E4F534A else b"\x00") * pad
        body += struct.pack("<II", len(data), ctype) + data
    head = struct.pack("<III", 0x46546C67, 2, 12 + len(body))
    open(path, "wb").write(head + body)


def patch_team(path, pal):
    """Mat_TeamColor 的 baseColorFactor 写成阵营色（线性）。"""
    chunks = read_glb(path)
    js = json.loads(chunks[0][1].decode("utf-8"))
    lin = mkit.srgb(pal["team"])[:3]
    hit = []
    for m in js.get("materials", []):
        if m.get("name") == "Mat_TeamColor":
            pbr = m.setdefault("pbrMetallicRoughness", {})
            pbr["baseColorFactor"] = [round(c, 6) for c in lin] + [1.0]
            hit.append(m["name"])
    new = json.dumps(js, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chunks[0] = (0x4E4F534A, new)
    write_glb(path, chunks)
    return hit


def verify(path):
    chunks = read_glb(path)
    js = json.loads(chunks[0][1].decode("utf-8"))
    prims = [(p.get("material"), sorted(p["attributes"].keys()))
             for m in js.get("meshes", []) for p in m["primitives"]]
    tris = sum(js["accessors"][p["indices"]]["count"] // 3
               for m in js.get("meshes", []) for p in m["primitives"] if "indices" in p)
    mats = {}
    for m in js.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        mats[m.get("name")] = {
            "base": [round(v, 4) for v in pbr.get("baseColorFactor", [1, 1, 1, 1])],
            "metal": pbr.get("metallicFactor"),
            "rough": pbr.get("roughnessFactor"),
        }
    matnames = [m.get("name") for m in js.get("materials", [])]
    prim_mats = [js["materials"][p[0]]["name"] for p in prims if p[0] is not None]
    return {
        "size": os.path.getsize(path),
        "materials": mats, "mat_names": matnames,
        "prims": prim_mats,
        "attrs": [p[1] for p in prims],
        "tris": tris,
        "color0": all("COLOR_0" in a for a in (p[1] for p in prims)),
        "nodes": [n.get("name") for n in js.get("nodes", [])],
    }


def export(star, pal_name="联盟"):
    pal = mkit.palette(pal_name)
    mkit.clear()
    ob, B = bk_model.build(star, pal=pal_name)
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, "兵营_%d星.glb" % star)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_normals=True,
        export_tangents=False,
        export_texcoords=False,
        export_vertex_color='ACTIVE',
        export_all_vertex_colors=True,
        export_materials='EXPORT',
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_animations=False,
    )
    patched = patch_team(path, pal)
    info = verify(path)
    print("★%d -> %s  [%s]" % (star, os.path.basename(path), "/".join(patched)))
    print("   ", json.dumps(info, ensure_ascii=False))
    return {"star": star, "file": os.path.basename(path), **info}


if __name__ == "__main__":
    tmp = os.path.join(ROOT, "docs", "_tmp", "v7")
    os.makedirs(tmp, exist_ok=True)
    rows = [export(s) for s in (1, 2, 3)]
    bad = [r for r in rows
           if r["mat_names"] != ["Mat_Neutral", "Mat_TeamColor"]
           or not r["color0"] or len(r["mat_names"]) != 2]
    with open(os.path.join(tmp, "bk_export.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTDIR, "阵营色.json"), "w", encoding="utf-8") as f:
        json.dump({"说明": "两槽制：只改 Mat_TeamColor 的 baseColor 即可换阵营；"
                          "Mat_Neutral 的顶点色是固定本色，不要动。",
                   "默认": mkit.DEFAULT_PALETTE,
                   "阵营": {k: {"team": v["team"]} for k, v in mkit.PALETTES.items()}},
                  f, ensure_ascii=False, indent=2)
    print("check ->", "PASS" if not bad else "FAIL %s" % [b["star"] for b in bad])
