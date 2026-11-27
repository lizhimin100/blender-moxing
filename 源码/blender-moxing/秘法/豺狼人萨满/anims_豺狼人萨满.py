"""anims_豺狼人萨满.py —— 别名模块（只有一行 re-export）。

`库/anim_sheet.py` 用 `importlib.import_module("anims_" + U.NAME)` 找动作模块，
而本单位的 NAME 是"豺狼人萨满"、动作文件按交付口径叫 `anims_萨满.py`。
这里只做转出，逻辑全在 `anims_萨满.py`，不要往这个文件里写东西。
"""
from anims_萨满 import *  # noqa: F401,F403
from anims_萨满 import build_all  # noqa: F401
