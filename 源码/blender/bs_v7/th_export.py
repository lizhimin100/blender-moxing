# -*- coding: utf-8 -*-
"""th_export.py —— 导出 3 档 GLB（顶点色 / 无贴图 / 原点在底座底面中心）

导出参数里必须显式打开顶点色：
    export_vertex_color='MATERIAL' + export_all_vertex_colors=True

队色怎么落地（本轮新增）：
`team` / `team_trim` 的材质 Base Color 是**常量**（阵营色），网格上那层灰阶顶点色
只是明度遮罩。导完再解 GLB 的 JSON 块，把 baseColorFactor 直接写成线性阵营色 ——
"换阵营"于是等于"改材质颜色"，跟引擎里的做法一致，不需要重建模型。
顺带把整套阵营色写成 `阵营色.json` 放在资产目录，运行时照着改。
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
import th_model  # noqa: E402

OUTDIR = os.path.join(ROOT, "assets", "建筑", "联盟", "城镇大厅_微缩")


# ------------------------------------------------------------------ GLB 读写

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
    """把 team / team_trim 的 baseColorFactor 写成阵营色（线性）。"""
    chunks = read_glb(path)
    js = json.loads(chunks[0][1].decode("utf-8"))
    lin = {k: mkit.srgb(pal[k])[:3] for k in ("team", "team_trim")}
    hit = []
    for m in js.get("materials", []):
        name = m.get("name")
        if name in lin:
            pbr = m.setdefault("pbrMetallicRoughness", {})
            pbr["baseColorFactor"] = [round(c, 6) for c in lin[name]] + [1.0]
            hit.append(name)
    new = json.dumps(js, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chunks[0] = (0x4E4F534A, new)
    write_glb(path, chunks)
    return hit


def verify(path):
    """直接读 GLB 的 JSON 块，确认 COLOR_0 / 材质 / 面数 / 阵营色都在。"""
    chunks = read_glb(path)
    js = json.loads(chunks[0][1].decode("utf-8"))
    prims = [sorted(p["attributes"].keys()) for m in js.get("meshes", []) for p in m["primitives"]]
    tris = sum(js["accessors"][p["indices"]]["count"] // 3
               for m in js.get("meshes", []) for p in m["primitives"] if "indices" in p)
    mats = {}
    for m in js.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        mats[m.get("name")] = {
            "base": [round(v, 3) for v in pbr.get("baseColorFactor", [1, 1, 1, 1])],
            "metal": pbr.get("metallicFactor"),
            "rough": pbr.get("roughnessFactor"),
        }
    return {"size": os.path.getsize(path), "materials": mats, "attrs": prims,
            "tris": tris, "color0": all("COLOR_0" in a for a in prims),
            "nodes": [n.get("name") for n in js.get("nodes", [])]}


# ------------------------------------------------------------------ 导出

def export(star, pal_name="联盟"):
    pal = mkit.palette(pal_name)
    mkit.clear()
    ob, B = th_model.build(star, pal=pal_name)
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, "城镇大厅_%d星.glb" % star)
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
        export_vertex_color='MATERIAL',
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
    with open(os.path.join(tmp, "export.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    # 阵营色随资产走：运行时读它改 team / team_trim 的材质颜色即可换阵营
    with open(os.path.join(OUTDIR, "阵营色.json"), "w", encoding="utf-8") as f:
        json.dump({"说明": "改 material['team'] / ['team_trim'] 的 baseColor 即可换阵营；"
                          "顶点色只是明度遮罩，不要动。",
                   "默认": mkit.DEFAULT_PALETTE,
                   "阵营": mkit.PALETTES}, f, ensure_ascii=False, indent=2)
    print("painted ->", os.path.join(OUTDIR, "阵营色.json"))
