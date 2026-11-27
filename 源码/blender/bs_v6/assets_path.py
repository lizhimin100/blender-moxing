"""assets_path.py —— 资产目录解析（纯标准库：Blender 里能跑，系统 Python 里也能跑）

资产树按「大类 / 族 / 资产名」组织：

    assets/建筑/联盟/铁匠铺/
    assets/建筑/失落帝国/地牢/
    assets/建筑/通用/营火/
    assets/单位/联盟/剑士/
    assets/单位/野怪/豺狼人/豺狼人战士/
    assets/地形/

但**脚本里只写资产名，不写层级**：

    asset_path("箭塔")            -> .../assets/建筑/联盟/箭塔
    asset_path("剑士", "图集")     -> .../assets/单位/联盟/剑士/图集
    asset_path("地形", "地块")     -> .../assets/地形/地块
    asset_path()                  -> .../assets

于是「换分类、换族名、再加一层」都只影响这一个文件；导出、体检、出图、建造动画
的脚本一个字都不用动。这是整个工程里**唯一**知道资产树长什么样子的地方。
"""
import json
import os

# 本文件在 blender/bs_v6/ 下，向上两级就是工程根
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ASSETS = os.path.join(ROOT, "assets")

# 这些名字是「容器」，不是资产本身，解析时要跳过
_SKIP = {"_历史版本", "_bak", "__pycache__", "图集", "地形"}

_INDEX = None


def _build_index():
    """扫一遍 assets/，把「目录名 -> 路径」建起来。

    同名目录（例如 豺狼人 既是族名也是名字的一部分）优先选：
      ① 里面有 .glb / _图标.png 的；
      ② 层级更浅的。
    """
    idx = {}
    for dirpath, dirnames, filenames in os.walk(ASSETS):
        dirnames[:] = [d for d in dirnames if d not in ("_历史版本", "_bak", "__pycache__")]
        name = os.path.basename(dirpath)
        if name in _SKIP or dirpath == ASSETS:
            continue
        has_asset = any(f.endswith(".glb") for f in filenames) or \
            any("图标" in f for f in filenames)
        depth = dirpath.count(os.sep)
        old = idx.get(name)
        if old is None:
            idx[name] = (has_asset, -depth, dirpath)
        else:
            if (has_asset, -depth) > old[:2]:
                idx[name] = (has_asset, -depth, dirpath)
    return {k: v[2] for k, v in idx.items()}


def index():
    global _INDEX
    if _INDEX is None:
        _INDEX = _build_index()
    return _INDEX


def refresh():
    """资产树变动后（新建/改名）调一次。"""
    global _INDEX
    _INDEX = None
    return index()


def asset_path(*parts):
    """按资产名拿目录；后面的参数当作子路径。

    解析不到就退回老的 `assets/<第一段>`，这样历史脚本（warband 那批）不会炸。
    """
    if not parts:
        return ASSETS
    name = parts[0]
    base = index().get(name) or os.path.join(ASSETS, name)
    return os.path.join(base, *parts[1:]) if len(parts) > 1 else base


def all_assets():
    """{资产名: 相对 assets 的路径}，给索引文件和 Godot 导入脚本用。"""
    out = {}
    for name, path in sorted(index().items()):
        if os.path.isdir(path):
            out[name] = os.path.relpath(path, ASSETS).replace("\\", "/")
    return out


def write_index(path=None):
    path = path or os.path.join(ASSETS, "资产索引.json")
    data = {"root": "assets", "assets": all_assets()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path, len(data["assets"])


if __name__ == "__main__":
    for n in ("铁匠铺", "地牢", "地下城入口", "酒馆内部", "营火", "剑士", "豺狼人战士",
              "地形"):
        print("%-8s %s" % (n, asset_path(n)))
    print("索引 ->", write_index())
