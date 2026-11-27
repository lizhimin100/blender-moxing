"""ch_probe.py —— 盾面用纯自发光分色，看看到底是哪一块在发黑"""
import importlib
import math
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
if HERE not in sys.path:
    sys.path.insert(0, HERE)
for m in ("bslib", "ch_model", "shotlib"):
    if m in sys.modules:
        importlib.reload(sys.modules[m])
import ch_model  # noqa: E402
import shotlib as S  # noqa: E402

S.OUTSHOT = r"D:/测试一/docs/剑士/_look"
S.RES, S.SAMP = 700, 24
S.clear_scene()
objs, st = ch_model.build(smooth=True, bevel=True)

COL = {"team": (1, 0, 0), "steel": (0, 1, 0), "steel_dark": (0, 0.4, 1),
       "iron": (1, 1, 1), "wood_warm": (1, 1, 0), "team_trim": (1, 0, 1)}
for ob in objs:
    nm = ob.data.materials[0].name
    m = bpy.data.materials.new("dbg_" + nm)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    c = COL.get(nm, (0.15, 0.15, 0.15))
    em.inputs["Color"].default_value = (*c, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ob.data.materials.clear()
    ob.data.materials.append(m)

S.setup_world(strength=0.0)
S.ground_plane()
S.shot("dbg_front.png", objs, 0, 4, fixed=(Vector((0, 0, 1.28)), 2.8))
S.shot("dbg_shield.png", objs, -40, 10, fixed=(Vector((-0.36, 0.10, 1.24)), 1.0))
print("PROBE_DONE")
