"""_dbg_zfight.py —— 共面闪烁体检（v3 的 0 对判据，出货前必须跑）

  blender -b --factory-startup --python 库/_dbg_zfight.py -- <unit_dir> <module>
"""
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UNIT_DIR, MOD = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "库"))
import vox_studio as ST  # noqa: E402

U, A = ST.load(UNIT_DIR, MOD)
for lv in (0, 1, 2):
    g = U.build()
    g = g if lv == 0 else g.lod(level=lv)
    ob = g.build(prefix="qc")
    n, rows = g.zfight()
    print("[zfight L%d] pairs=%d" % (lv, n))
    for r in rows[:8]:
        print("   ", r)
    for r in g.zf_detail[:8]:
        print("    at", r)
    bpy.data.objects.remove(ob, do_unlink=True)
print("[zfight done]")
