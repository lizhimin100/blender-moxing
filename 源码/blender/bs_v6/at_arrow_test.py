"""at_arrow_test.py —— 箭饰三方案对照（同一塔顶 / 同一机位 / 并排一张图）

    python build/bl_act.py act blender/bs_v6/at_arrow_test.py

A 四片薄羽（当前）
B 三片薄羽（1.25 高 / 0.42 出）
C 双面剪影箭（两片互相垂直的箭头形板）
"""
import importlib
import math
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("bslib", "br_model", "wt_model", "at_model", "shotlib"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import at_model as A  # noqa: E402
import bslib as L  # noqa: E402
import shotlib as S  # noqa: E402
from bslib import box, cone, mesh_obj, revolve  # noqa: E402


class VarA(A.Model):
    pass


class VarB(A.Model):
    def arrow(self):
        M = self.M
        self.add(revolve("arw_shaft", [(0.090, 0.0), (0.078, 1.55)], 8,
                         (0, 0, 14.44), M["wood_dark"]), 0.0, 1)
        prof = [(0.02, 14.80), (0.16, 15.02), (0.42, 15.46), (0.26, 16.02),
                (0.02, 16.12)]
        for a in (0, 120, 240):
            self.add(A.vane("fl_vane", a, prof, 0.052, M["team"], swirl=0.55), 0.004)
        self.add(revolve("arw_head", [(0.052, 0.0), (0.250, 0.26), (0.190, 0.42),
                                      (0.0, 1.10)], 4,
                         (0, 0, 16.10), M["iron"], phase=math.pi / 4), 0.0, 1)


class VarC(A.Model):
    """双面剪影箭：两片互相垂直的板，板本身就是完整的箭形轮廓。"""

    @staticmethod
    def plate(name, prof, thick, mat, yaw):
        a = yaw
        ux, uy = math.cos(a), math.sin(a)
        tx, ty = -math.sin(a), math.cos(a)
        n = len(prof)
        verts = []
        for s in (-0.5, 0.5):
            for (u, z) in prof:
                verts.append((ux * u + tx * thick * s, uy * u + ty * thick * s, z))
        faces = [tuple(range(n)), tuple(range(n, 2 * n))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        return mesh_obj(name, verts, faces, mat)

    def arrow(self):
        M = self.M
        prof = [(0.000, 17.46),
                (0.300, 16.70), (0.300, 16.52), (0.085, 16.44),
                (0.085, 15.56), (0.330, 15.20), (0.330, 15.00),
                (0.085, 14.94), (0.085, 14.62), (-0.085, 14.62),
                (-0.085, 14.94), (-0.330, 15.00), (-0.330, 15.20),
                (-0.085, 15.56), (-0.085, 16.44), (-0.300, 16.52),
                (-0.300, 16.70)]
        for yaw in (0.0, math.pi * 0.5):
            self.add(self.plate("arw_flat", prof, 0.055, M["iron"], yaw), 0.004)
        # 板在中心线上是薄的：加一根竖杆把两片板"绑"成一体
        self.add(revolve("arw_core", [(0.070, 0.0), (0.062, 2.60)], 6,
                         (0, 0, 14.80), M["iron"]), 0.0, 1)
        self.add(box("arw_sleeve", (0, 0, 14.86), (0.20, 0.20, 0.16),
                     M["roof_edge"]), 0.006)


def main():
    S.OUTSHOT = os.path.join(ROOT, "docs", "箭塔", "_look")
    S.RES, S.SAMP = 1100, 32
    S.clear_scene()

    objs = []
    for i, cls in enumerate((VarA, VarB, VarC)):
        m = cls(True, unwrap=False)
        m.roof()
        m.arrow()
        part = m.finalize(bevel=True)
        for ob in part:
            ob.location.x += i * 3.4
            objs.append(ob)

    S.setup_world()
    S.shot("_箭饰对照.png", objs, -34, 20, 1.06)
    S.shot("_箭饰正面.png", objs, 0, 4, 1.06)
    print("DONE")


main()
