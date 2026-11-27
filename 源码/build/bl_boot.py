"""bl_boot.py —— 启动 Blender 图形界面时把 DSH 桥接（TCP 9876）拉起来，并做自愈。

用法：
    "D:/360安全浏览器下载/blender.exe" --python build/bl_boot.py

为什么要自愈：任何 `bpy.ops.wm.read_factory_settings()` / 偏好重置都会把插件的
server 对象一起清掉，端口就再也连不上（会话里踩过两次）。这里每 2 秒检查一次，
掉了就重新注册 + 重新 start，不碰场景内容。

配套：`build/bl_act.py act <script>` 往桥接里发脚本；`blender-moxing/库/vox_studio.py`
是桥接里唯一安全的建/拍入口（它用"手动清场"代替 `read_factory_settings`）。
"""
import os

import addon_utils
import bpy

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bl_boot.log")


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


def ensure():
    try:
        if not hasattr(bpy.types, "dshbb_server") or bpy.types.dshbb_server is None:
            addon_utils.enable("dsh_blender_bridge", default_set=True, persistent=True)
            bpy.ops.dshbb.start_server()
            log("[heal] restarted")
        elif not getattr(bpy.types.dshbb_server, "running", False):
            bpy.ops.dshbb.start_server()
            log("[heal] resumed")
    except Exception as exc:
        log("[heal] fail %r" % (exc,))
    return 2.0


open(LOG, "w", encoding="utf-8").close()
addon_utils.enable("dsh_blender_bridge", default_set=True, persistent=True)
bpy.ops.dshbb.start_server()
log("boot ok: %r" % (getattr(bpy.types, "dshbb_server", None),))
bpy.app.timers.register(ensure, first_interval=2.0, persistent=True)
