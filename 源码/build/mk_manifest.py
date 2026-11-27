"""扫 assets/ 下所有 GLB，输出机器可读的资产清单。

为什么要有这个：README 里那些「6,768 tri / 4 材质 / 10.08 × 9.93 × 4.94 m」
如果靠手抄，改一次版就会过期，下一个接手的人会照着错的数字做判断。
这个脚本直接解 GLB 的 JSON 块，一次生成：

  - assets/资产清单.json   给 agent / 脚本读
  - 标准输出一份 markdown 表 给 README 贴

用法：
  python build/mk_manifest.py            # 生成 json + 打印表
  python build/mk_manifest.py --markdown # 只打印表
"""

import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")


def read_glb(path):
    """解 GLB：返回 (gltf_json, 总字节)。只读头两个块，不碰 BIN。"""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("不是 GLB：%s" % path)
    off, js = 12, None
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        if ctype == 0x4E4F534A:            # 'JSON'
            js = json.loads(data[off + 8:off + 8 + clen].decode("utf-8"))
        off += 8 + clen + ((4 - clen % 4) % 4 if clen % 4 else 0)
    if js is None:
        raise ValueError("GLB 里没有 JSON 块：%s" % path)
    return js, len(data)


def glb_meta(path):
    """三角数 / 材质 / 节点 / 包围盒 / 骨骼 / 动作。"""
    js, size = read_glb(path)
    acc = js.get("accessors", [])

    tris = 0
    for mesh in js.get("meshes", []):
        for p in mesh.get("primitives", []):
            if p.get("mode", 4) != 4:       # 只数三角形
                continue
            if "indices" in p:
                tris += acc[p["indices"]]["count"] // 3
            elif "POSITION" in p.get("attributes", {}):
                tris += acc[p["attributes"]["POSITION"]]["count"] // 3

    lo = [1e9] * 3
    hi = [-1e9] * 3
    for mesh in js.get("meshes", []):
        for p in mesh.get("primitives", []):
            i = p.get("attributes", {}).get("POSITION")
            if i is None:
                continue
            a = acc[i]
            if "min" not in a or "max" not in a:
                continue
            for k in range(3):
                lo[k] = min(lo[k], a["min"][k])
                hi[k] = max(hi[k], a["max"][k])
    dims = [round(hi[k] - lo[k], 2) for k in range(3)] if hi[0] > lo[0] else None

    mats = [m.get("name", "?") for m in js.get("materials", [])]
    joints = 0
    for sk in js.get("skins", []):
        joints += len(sk.get("joints", []))

    return {
        "tri": tris,
        "materials": len(mats),
        "material_names": mats,
        "nodes": len(js.get("nodes", [])),
        "meshes": len(js.get("meshes", [])),
        "joints": joints,
        "animations": len(js.get("animations", [])),
        "size_xyz": dims,
        "bytes": size,
    }


# 每个资产的交付档 → 语义。键是文件名后缀，值是给人看的用途。
KIND = (
    ("", "细分（倒角 + 一级细分）"),
    ("_低模", "低模（无倒角、全平面着色）"),
    ("_手游_近", "手游 LOD0 近景"),
    ("_手游_中", "手游 LOD1 中景"),
    ("_手游_远", "手游 LOD2 远景"),
    ("_建造", "建造动画档"),
    ("_身体", "分体·身体"),
    ("_武器", "分体·武器"),
    ("_图标", "图标"),
)


def kind_of(stem, asset):
    """判断这是哪一个交付档。顺序重要：_手游_近 不能先被 "" 命中。"""
    if stem == asset:
        return "hero"
    tail = stem[len(asset):]
    for k, label in KIND:
        if k and tail == k:
            return k.lstrip("_")
    return "other"


def walk():
    """遍历 assets/，产出 (相对路径, 类别, 阵营, 资产名, meta|None)。"""
    out = []
    for base, cats in (("建筑", "建筑"), ("单位", "单位"), ("地形", "地形")):
        root = os.path.join(ASSETS, base)
        if not os.path.isdir(root):
            continue
        for dirpath, _, files in os.walk(root):
            for fn in sorted(files):
                if not fn.lower().endswith(".glb"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ASSETS).replace("\\", "/")
                parts = rel.split("/")
                team = parts[1] if len(parts) > 2 else ""
                asset = os.path.splitext(fn)[0]
                # 「方块人_矮人火枪手_低模」这类名字，资产名要去掉分体后缀
                for suf in ("_低模", "_手游_近", "_手游_中", "_手游_远",
                            "_建造", "_身体", "_武器"):
                    if asset.endswith(suf):
                        asset = asset[:-len(suf)]
                        break
                try:
                    meta = glb_meta(full)
                except Exception as e:                       # noqa: BLE001
                    print("  ! %s: %s" % (rel, e), file=sys.stderr)
                    meta = None
                out.append({"path": rel, "cat": cats, "team": team,
                            "asset": asset, "file": fn, "meta": meta})
    return out


def main():
    only_md = "--markdown" in sys.argv
    items = walk()
    if not items:
        print("assets/ 下没找到 GLB", file=sys.stderr)
        return 1

    # 按资产聚合：一个资产 = 若干交付档
    assets = {}
    for it in items:
        key = "%s/%s/%s" % (it["cat"], it["team"], it["asset"])
        a = assets.setdefault(key, {"cat": it["cat"], "team": it["team"],
                                    "asset": it["asset"], "files": {}})
        k = kind_of(os.path.splitext(it["file"])[0], it["asset"])
        a["files"][k] = {"path": it["path"], **(it["meta"] or {})}

    doc = {
        "生成": "python build/mk_manifest.py",
        "单位": "米（1 unit = 1 m）· 原点 = 占地中心 · 脚底/地面 z = 0 · 正面朝 −Z",
        "口径": {
            "tri": "三角面数，GLB 里索引数 / 3",
            "materials": "材质槽位数 = 每个网格的 draw call 上限",
            "size_xyz": "包围盒 X × Y × Z",
            "joints": "蒙皮骨骼数（仅单位）",
            "animations": "动作数（仅单位）",
        },
        "资产": assets,
    }

    if not only_md:
        dst = os.path.join(ASSETS, "资产清单.json")
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
        print("已写 %s（%d 个资产 / %d 个 GLB）"
              % (os.path.relpath(dst, ROOT), len(assets), len(items)), file=sys.stderr)

    print("| 资产 | 阵营 | 手游近 tri | 材质 | 细分 tri | 尺寸 X×Y×Z (m) |")
    print("|---|---|---:|---:|---:|---|")
    for key in sorted(assets):
        a = assets[key]
        low = a["files"].get("手游_近") or a["files"].get("hero") or {}
        hero = a["files"].get("hero") or {}
        dim = (low.get("size_xyz") if low.get("size_xyz") else hero.get("size_xyz")) or []
        name = a["asset"]
        if a["cat"] != "建筑":
            name = "%s/%s" % (a["cat"], a["asset"])
        print("| %s | %s | %s | %s | %s | %s |" % (
            name, a["team"],
            "{:,}".format(low.get("tri", 0)) if low else "—",
            low.get("materials", "—"),
            "{:,}".format(hero.get("tri", 0)) if hero else "—",
            " × ".join(str(d) for d in dim) if dim else "—"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
