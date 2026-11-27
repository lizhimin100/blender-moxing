"""anims_豺狼人斥候.py —— 别名模块（只有一行 re-export）。

`库/anim_sheet.py` 用 `importlib.import_module("anims_" + U.NAME)` 找动作模块，
而本单位的动作文件按交付口径叫 `anims_斥候.py`。这里只做转出。
"""
from anims_斥候 import *  # noqa: F401,F403
from anims_斥候 import build_all  # noqa: F401
