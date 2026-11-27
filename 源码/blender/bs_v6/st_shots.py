"""st_shots.py —— 状态资产交付图：45° 方位 / 38° 俯角（工单验收口径）

    blender -b --factory-startup --python blender/bs_v6/st_shots.py -- 哨塔_升级

机位固定（45 / 38）：状态档是"同一座建筑的另一时刻"，机位一变就没法和主图对照。
布光 / 取景全部走 shotlib，与九座交付图同一套观感。
"""
import importlib
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "shotlib", "st_kit", "st_atlas", "st_upgrade", "st_fx",
           "st_new"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

import shotlib as S  # noqa: E402

DOC = os.path.join(ROOT, "docs", "状态资产")
AZ, EL = 45, 38
RES, SAMP = 1200, 48


def build(key):
    """按 key 找它的构建入口，返回已完成的对象列表（不导出）。"""
    import st_upgrade
    if key in st_upgrade.CONFIG:
        return st_upgrade.assemble(key, do_export=False)
    for mod_name in ("st_fx", "st_new"):
        try:
            mod = importlib.import_module(mod_name)
        except ImportError:
            continue
        if key in getattr(mod, "CONFIG", {}):
            return mod.assemble(key, do_export=False)
    raise KeyError(key)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    keys = argv or ["哨塔_升级"]
    ok = {}
    for key in keys:
        objs = build(key)
        S.clear_lights()
        S.OUTSHOT = os.path.join(DOC, key)
        S.setup_world()
        S.ground_plane()
        S.shot("%s_45x38.png" % key, objs, AZ, EL, 1.07, res=RES, samples=SAMP)
        ok[key] = os.path.join(DOC, key, "%s_45x38.png" % key)
        print("[shot]", key, ok[key])
    print("ST_SHOTS_OK " + str(len(ok)))


main()
