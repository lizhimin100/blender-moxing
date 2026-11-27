# -*- coding: utf-8 -*-
"""a_export.py —— 联盟七建筑 × 三档 GLB（两槽制 / 顶点色 / 原点在底座底面中心）

    blender -b --factory-startup -P a_export.py                # 全部
    blender -b --factory-startup -P a_export.py -- a_barracks   # 单座

只认两条：
  1. `Mat_TeamColor` 一个槽承担全部阵营色 —— 导出后回写 baseColorFactor；
  2. 队色件顶点色必须是纯白，否则引擎里"蓝 × 灰"会把阵营色乘脏。
导出后**直接解 GLB 的 JSON 块**核对：槽数、COLOR_0、三角面数、阵营色。
"""
import importlib
import json
import os
import struct
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import akit  # noqa: E402

BOOKS = [
    ("a_townhall", "城镇大厅"),
    ("a_barracks", "兵营"),
    ("a_farm",     "农场"),
    ("a_smith",    "铁匠铺"),
    ("a_lumber",   "伐木场"),
    ("a_watch",    "哨塔"),
    ("a_arrow",    "箭塔"),
]
ASSETS = os.path.join(ROOT, "assets", "建筑", "联盟")
TMP = os.path.join(ROOT, "docs", "_tmp", "v8")


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
    chunks = read_glb(path)
    js = json.loads(chunks[0][1].decode("utf-8"))
    lin = akit.mkit.srgb(pal["team"])[:3]
    hit = []
    for m in js.get("materials", []):
        if m.get("name") == "Mat_TeamColor":
            pbr = m.setdefault("pbrMetallicRoughness", {})
            pbr["baseColorFactor"] = [round(c, 6) for c in lin] + [1.0]
            pbr["metallicFactor"] = 0.0
            pbr["roughnessFactor"] = 0.62
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
    mats = {m.get("name"): [round(v, 4) for v in
                            m.get("pbrMetallicRoughness", {}).get(
                                "baseColorFactor", [1, 1, 1, 1])]
            for m in js.get("materials", [])}
    return {"size": os.path.getsize(path),
            "mats": mats,
            "names": [m.get("name") for m in js.get("materials", [])],
            "tris": tris,
            "color0": all("COLOR_0" in a for a in (p[1] for p in prims)),
            "nodes": [n.get("name") for n in js.get("nodes", [])]}


def export_one(modname, name, star, pal_name="联盟"):
    pal = akit.mkit.palette(pal_name)
    akit.mkit.clear()
    mod = importlib.import_module(modname)
    ob, B = mod.build(star, pal=pal_name)
    outdir = os.path.join(ASSETS, "%s_微缩" % name)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "%s_%d星.glb" % (name, star))
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True,
        export_apply=True, export_yup=True, export_normals=True,
        export_tangents=False, export_texcoords=False,
        export_vertex_color='ACTIVE', export_all_vertex_colors=True,
        export_materials='EXPORT', export_cameras=False, export_lights=False,
        export_extras=True, export_animations=False,
    )
    hit = patch_team(path, pal)
    info = verify(path)
    ok = (info["names"] == ["Mat_Neutral", "Mat_TeamColor"]
          and info["color0"] and len(hit) == 1
          and info["tris"] == len(ob.data.loop_triangles))
    print("%-6s ★%d  tris=%-5d  %6.1f KB  COLOR_0=%s  %s"
          % (name, star, info["tris"], info["size"] / 1024.0, info["color0"],
             "OK" if ok else "!! %s" % info["names"]))
    if not ok:
        print("        mats=%s  glb_tris=%d  blender_tris=%d"
              % (info["names"], info["tris"], len(ob.data.loop_triangles)))
    return {"building": name, "star": star, "file": os.path.basename(path),
            "ok": ok, **info}


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = set(argv) if argv else None
    os.makedirs(TMP, exist_ok=True)
    rows = []
    for modname, name in BOOKS:
        if only and modname not in only:
            continue
        for s in (1, 2, 3):
            rows.append(export_one(modname, name, s))
    if only:
        print("部分导出完成：%d 档" % len(rows))
        sys.exit(0)
    bad = [r for r in rows if not r["ok"]]
    with open(os.path.join(TMP, "export.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    # 阵营色白皮书：每座一份，值一样 —— 但引擎按目录加载，分开放最省事
    for _, name in BOOKS:
        outdir = os.path.join(ASSETS, "%s_微缩" % name)
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "阵营色.json"), "w", encoding="utf-8") as f:
            json.dump({"说明": "两槽制：运行时只替换 Mat_TeamColor 的 baseColor 即可"
                              "整体换阵营；Mat_Neutral 的顶点色是固定本色，不要动。",
                       "默认": akit.mkit.DEFAULT_PALETTE,
                       "阵营": {k: {"team": v["team"]} for k, v in
                              akit.mkit.PALETTES.items()}},
                      f, ensure_ascii=False, indent=2)
    print("\n总计 %d 档，失败 %d" % (len(rows), len(bad)))
    for b in bad:
        print("  ✗ %s ★%d" % (b["building"], b["star"]))
