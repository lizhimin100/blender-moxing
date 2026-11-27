"""把 assets/ 里的交付物同步到公开仓库（默认 D:/测试一/_仓库/blender-moxing）。

**这个脚本就是「什么该进仓库、什么不该进、放哪个目录」的唯一定义。**
改主意只需要改这里，不用去仓库里手动搬文件。

目录规范（对齐本地工作区的习惯，不是老仓库的 产出/ 那一套）：

  单位/
    联盟/<单位>/      glb + 图标 + 组件化的组件（身体 / 武器 / 分档）
    失落/<单位>/      ← 原「野怪」，按阵营改名为「失落」
    失落/武器/        共享挂点件（匕首 / 流星锤）
    文档/            单位规范、对照表、交接手册、经验、自检、修订报告

  建筑/
    联盟|失落帝国|通用/<资产>/    六档 glb + 512² 图标
    文档/            资产规范、建模规则、审美 brief、每座一页设计报告

  地形纹理/
    草泥|草裂纹|泥裂纹/   图集四张 + Godot shader + LUT + 生成说明
    地块/                 8×8 m 可平铺地块
    文档/                 生成说明书 + 参数配置

进仓库的：GLB、图标、可用文档、机器清单。
不进仓库的：渲染迭代图（约 50 MB，是过程不是资产）、_历史版本（git 自己就是）、
.blend / .pyc / _tmp（重跑脚本就有）、生成脚本（本仓库只做交付）。

用法：
  python build/sync_repo.py                     # 同步到默认目录
  python build/sync_repo.py --to <路径>
  python build/sync_repo.py --lite              # 不推细分档与远/中景 LOD（省约 30 MB）
  python build/sync_repo.py --prune             # 删掉源里已不存在的文件
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
DOCS = os.path.join(ROOT, "docs")
UNIT_SRC = os.path.join(ROOT, "blender-moxing")     # 单位脚本工作区（只取文档）
DEFAULT_TO = os.path.join(ROOT, "_仓库", "blender-moxing")

# 建筑：每座一个目录，6 档 glb + 1 张图标
BUILD_EXT = ("", "_低模", "_手游_近", "_手游_中", "_手游_远", "_建造")

# 火四件是纯道具，没有建造动画（设计如此，不是漏导）
NO_BUILD = ("火堆", "火把", "火炬", "营火")

# 阵营改名：源目录 → 仓库目录
FACTION = {"联盟": "联盟", "野怪": "失落", "失落帝国": "失落帝国", "通用": "通用"}

# 每座只收**最新一版**的设计报告；旧版留在 docs/ 里，vN 目录本身就是历史。
REPORT = {
    "伐木场": "v1", "兵营": "v4", "农场": "v2", "哨塔": "v1", "城镇大厅": "v3",
    "神秘圣地": "v1", "箭塔": "v2", "蒸汽车坊": "v3", "酒馆内部": "v1",
    "铁匠铺": "v10", "地牢": "v2", "折壳入口": "v2", "地下城入口": "v1",
    "火": "v1",
}

copied, skipped, missing = [], [], []


def put(src, dst):
    if not os.path.isfile(src):
        missing.append(os.path.relpath(src, ROOT))
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(os.path.relpath(dst, TO))
    return True


# ── 单位 ────────────────────────────────────────────────────────────────────
def sync_units(lite):
    root = os.path.join(ASSETS, "单位")
    for team_src in sorted(os.listdir(root)):
        tdir = os.path.join(root, team_src)
        if not os.path.isdir(tdir):
            continue
        team = FACTION.get(team_src, team_src)
        # 单位目录可能是 联盟/剑士，也可能是 野怪/豺狼人/豺狼人战士 —— 拍平
        for dirpath, _, files in os.walk(tdir):
            glbs = [f for f in files if f.lower().endswith(".glb")]
            if not glbs:
                continue
            asset = os.path.basename(dirpath)              # 文件夹名 = 资产名
            out = os.path.join(TO, "单位", team, asset)
            for fn in sorted(glbs):
                if lite and any(k in fn for k in ("_手游_中", "_手游_远")):
                    continue
                if lite and fn == asset + ".glb":
                    continue                               # --lite 跳过细分档
                put(os.path.join(dirpath, fn), os.path.join(out, fn))
            # 图标：单位现在也有 512² 卡面了（2026-11-05 补的，走 icon_units.py）。
            # 文件名跟 GLB 主干走（方块人_农民_图标.png），不是文件夹名，所以按后缀找。
            for fn in sorted(files):
                if fn.endswith("_图标.png"):
                    put(os.path.join(dirpath, fn), os.path.join(out, fn))
    # 共享武器件：只在仓库里存在过，源工程没有，从旧仓库原样保留由调用方负责
    #（迁移时已手工搬到 单位/失落/武器/，这里不覆盖）


def sync_unit_docs():
    d = os.path.join(UNIT_SRC, "文档")
    if not os.path.isdir(d):
        return
    for fn in sorted(os.listdir(d)):
        if fn.lower().endswith(".md"):
            put(os.path.join(d, fn), os.path.join(TO, "单位", "文档", fn))


# ── 可复用零件 ──────────────────────────────────────────────────────────────
def sync_parts():
    root = os.path.join(ASSETS, "建筑", "零件")
    if not os.path.isdir(root):
        return
    for fn in sorted(os.listdir(root)):
        if fn.lower().endswith(".glb"):
            put(os.path.join(root, fn), os.path.join(TO, "建筑", "零件", fn))
    put(os.path.join(DOCS, "零件", "说明.md"),
        os.path.join(TO, "建筑", "零件", "说明.md"))


# ── 建筑 ────────────────────────────────────────────────────────────────────
def sync_buildings(lite):
    root = os.path.join(ASSETS, "建筑")
    for team_src in sorted(os.listdir(root)):
        tdir = os.path.join(root, team_src)
        if not os.path.isdir(tdir):
            continue
        team = FACTION.get(team_src, team_src)
        for asset in sorted(os.listdir(tdir)):
            adir = os.path.join(tdir, asset)
            if not os.path.isdir(adir):
                continue
            out = os.path.join(TO, "建筑", team, asset)
            for ext in BUILD_EXT:
                if ext == "_建造" and asset in NO_BUILD:
                    continue
                if lite and ext == "":
                    continue                               # --lite 跳过细分档
                put(os.path.join(adir, asset + ext + ".glb"),
                    os.path.join(out, asset + ext + ".glb"))
            put(os.path.join(adir, asset + "_图标.png"),
                os.path.join(out, asset + "_图标.png"))


def sync_build_docs():
    for fn in ("资产规范.md", "建模规则.md"):
        put(os.path.join(DOCS, "10-规范", fn), os.path.join(TO, "建筑", "文档", fn))
    aroot = os.path.join(DOCS, "审美")
    if os.path.isdir(aroot):
        for fn in sorted(os.listdir(aroot)):
            if fn.lower().endswith(".md"):
                put(os.path.join(aroot, fn), os.path.join(TO, "建筑", "文档", "审美", fn))
    for asset, ver in sorted(REPORT.items()):
        put(os.path.join(DOCS, asset, ver, "报告.md"),
            os.path.join(TO, "建筑", "文档", "设计", asset + ".md"))


# ── 地形纹理 ────────────────────────────────────────────────────────────────
def keep_terrain(rel):
    """只要游戏真正采样到的四张图集 + shader + LUT，外加生成说明。
    cell_00..15 / preview_3x3 / noise_256 是生成中间产物，能从工具箱重跑。"""
    return rel.startswith(("atlas_", "godot/")) or rel.lower().endswith(".md")


def sync_terrain(lite):
    root = os.path.join(ASSETS, "地形")
    mroot = os.path.join(root, "材质")
    if os.path.isdir(mroot):
        for mat in sorted(os.listdir(mroot)):
            mdir = os.path.join(mroot, mat)
            if not os.path.isdir(mdir):
                continue
            out = os.path.join(TO, "地形纹理", mat)
            for dirpath, _, files in os.walk(mdir):
                for fn in sorted(files):
                    rel = os.path.relpath(os.path.join(dirpath, fn), mdir).replace("\\", "/")
                    if not keep_terrain(rel):
                        skipped.append("地形/材质/%s/%s" % (mat, rel))
                        continue
                    put(os.path.join(dirpath, fn), os.path.join(out, rel))
    groot = os.path.join(root, "地块")
    if os.path.isdir(groot):
        for fn in sorted(os.listdir(groot)):
            src = os.path.join(groot, fn)
            if fn.lower().endswith(".glb"):
                if lite and fn.endswith("_低模.glb"):
                    continue
                put(src, os.path.join(TO, "地形纹理", "地块", fn))
            elif fn.lower().endswith(".md"):
                put(src, os.path.join(TO, "地形纹理", "地块", fn))
    # 生成说明
    box = os.path.join(ROOT, "地形生成工具箱")
    put(os.path.join(box, "使用说明书.md"),
        os.path.join(TO, "地形纹理", "文档", "地形材质使用说明书.md"))
    put(os.path.join(box, "参数配置.json"),
        os.path.join(TO, "地形纹理", "文档", "地形参数配置.json"))


# ── 清单 ────────────────────────────────────────────────────────────────────
def sync_manifest():
    """资产清单给 agent 读，路径必须相对仓库根、且是新目录。"""
    subprocess.run([sys.executable, os.path.join(ROOT, "build", "mk_manifest.py")],
                   cwd=ROOT, capture_output=True)
    src = os.path.join(ASSETS, "资产清单.json")
    if not os.path.isfile(src):
        missing.append("assets/资产清单.json")
        return
    with open(src, encoding="utf-8") as f:
        doc = json.load(f)

    def fix(p):
        """assets 路径 → 仓库路径。建筑只去掉一层，单位要换阵营名。"""
        if p.startswith("建筑/"):
            return p                                   # 建筑/联盟/兵营/…  与仓库同构
        if p.startswith("单位/"):
            parts = p.split("/")
            if len(parts) >= 4:                        # 单位/野怪/豺狼人/豺狼人战士/x.glb
                parts[1] = FACTION.get(parts[1], parts[1])
            # 拍平：族 那一层去掉（单位/失落/豺狼人/豺狼人战士 → 单位/失落/豺狼人战士）
            if len(parts) == 5:
                parts.pop(2)
            return "/".join(parts)
        if p.startswith("地形/"):
            return p.replace("地形/材质/", "地形纹理/", 1).replace("地形/地块/", "地形纹理/地块/", 1)
        return p

    newassets = {}
    for key, a in doc["资产"].items():
        for rec in a["files"].values():
            rec["path"] = fix(rec["path"])
        # 顶层键也要跟着改：单位/野怪/X → 单位/失落/X，地形/X → 地形纹理/X
        k = key
        if k.startswith("单位/"):
            parts = k.split("/")
            parts[1] = FACTION.get(parts[1], parts[1])
            k = "/".join(parts)
        elif k.startswith("地形/"):
            k = k.replace("地形/", "地形纹理/", 1)
        newassets[k] = a
    doc["资产"] = newassets

    with open(os.path.join(TO, "资产清单.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1, sort_keys=True)
    copied.append("资产清单.json")


def prune():
    """删掉仓库里源已不存在的东西。不碰 单位/失落/武器（仓库独有的挂点件）。"""
    keep = {os.path.normpath(p) for p in copied}
    safe = ("建筑", "地形纹理")
    for sub in safe:
        d = os.path.join(TO, sub)
        if not os.path.isdir(d):
            continue
        for dirpath, _, files in os.walk(d):
            for fn in files:
                full = os.path.normpath(os.path.join(dirpath, fn))
                if full not in keep:
                    os.remove(full)
                    print("  - 删除 %s" % os.path.relpath(full, TO))
        for dirpath, _, _ in os.walk(d, topdown=False):
            if not os.listdir(dirpath):
                os.rmdir(dirpath)


def main():
    global TO
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default=DEFAULT_TO)
    ap.add_argument("--lite", action="store_true", help="不推细分档与中/远景 LOD")
    ap.add_argument("--prune", action="store_true", help="删除源中已不存在的文件")
    args = ap.parse_args()
    TO = os.path.abspath(args.to)

    if not os.path.isdir(TO):
        print("目标目录不存在：%s\n先 clone：git clone https://github.com/lizhimin100/"
              "blender-moxing.git \"%s\"" % (TO, TO))
        return 1

    sync_units(args.lite)
    sync_unit_docs()
    sync_parts()
    sync_buildings(args.lite)
    sync_build_docs()
    sync_terrain(args.lite)
    sync_manifest()
    if args.prune:
        prune()

    total = sum(os.path.getsize(os.path.join(TO, p)) for p in copied
                if os.path.isfile(os.path.join(TO, p)))
    print("同步完成 → %s" % TO)
    print("  拷入 %d 个文件，%.1f MB" % (len(copied), total / 1048576))
    if missing:
        print("  缺失 %d 个源文件：" % len(missing))
        for m in missing[:10]:
            print("    ! %s" % m)
    if skipped:
        print("  跳过 %d 个生成中间产物" % len(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
