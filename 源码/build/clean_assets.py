"""clean_assets.py —— 资产目录瘦身：一座建筑一个文件夹里只留「图标 + GLB」。

    python build/clean_assets.py            # 干跑，只打印计划
    python build/clean_assets.py --apply    # 真删（先打包进 _bak/资产精简.zip）

留：<建筑>_图标.png、<建筑>.glb、<建筑>_低模.glb、<建筑>_手游_{近,中,远}.glb、
    <建筑>_建造.glb
走：*.blend、图集/、建造*.json、<建筑>_建造_细分.glb、说明.md（移到 docs/<建筑>/）
"""
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "blender", "bs_v6"))
from assets_path import asset_path, all_assets  # noqa: E402

ASSET = asset_path()
DOCS = os.path.join(ROOT, "docs")
BACKUP = os.path.join(ROOT, "_bak", "资产精简.zip")

BUILDINGS = list(all_assets())


def keep(name, cn):
    if name.endswith(".png"):
        return True
    if not name.endswith(".glb"):
        return False
    if name.endswith("_建造_细分.glb"):
        return False
    return True


def main(apply=False):
    plan_del, plan_move = [], []
    for cn in BUILDINGS:
        d = asset_path(cn)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if os.path.isdir(p):
                plan_del.append(p)
                continue
            if name == "说明.md":
                plan_move.append((p, os.path.join(DOCS, cn, "说明.md")))
                continue
            if not keep(name, cn) and not name.endswith("_图标.png"):
                plan_del.append(p)
        # 图标从 assets/图标/ 搬进建筑目录
        src = os.path.join(ASSET, "图标", f"{cn}_图标.png")
        if os.path.exists(src):
            plan_move.append((src, os.path.join(d, f"{cn}_图标.png")))

    left = sorted(os.listdir(os.path.join(ASSET, "图标"))) if os.path.isdir(
        os.path.join(ASSET, "图标")) else []
    if left:
        # 各尺寸 / 透明 / 生图变体都由 icon_post.py 从主图生成，随源资产一起清掉
        plan_del.append(os.path.join(ASSET, "图标"))

    for p in plan_del:
        print("DEL ", os.path.relpath(p, ROOT))
    for a, b in plan_move:
        print("MOVE", os.path.relpath(a, ROOT), "→", os.path.relpath(b, ROOT))
    print(f"--- del {len(plan_del)} / move {len(plan_move)} / 图标目录剩余 {len(left)}")

    if not apply:
        return
    os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
    with zipfile.ZipFile(BACKUP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in plan_del:
            if os.path.isdir(p):
                for base, _, fs in os.walk(p):
                    for f in fs:
                        fp = os.path.join(base, f)
                        z.write(fp, os.path.relpath(fp, ROOT))
            else:
                z.write(p, os.path.relpath(p, ROOT))
    print("备份 →", os.path.relpath(BACKUP, ROOT),
          f"{os.path.getsize(BACKUP)/1048576:.1f} MB")

    for a, b in plan_move:
        os.makedirs(os.path.dirname(b), exist_ok=True)
        if os.path.exists(b):
            os.remove(b)
        shutil.move(a, b)
    for p in plan_del:
        if os.path.isdir(p):
            shutil.rmtree(p)
        else:
            os.remove(p)
    ic = os.path.join(ASSET, "图标")
    if os.path.isdir(ic) and not os.listdir(ic):
        os.rmdir(ic)
    print("done")


if __name__ == "__main__":
    main("--apply" in sys.argv)
