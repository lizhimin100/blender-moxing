# -*- coding: utf-8 -*-
"""一次性补丁：给 st_fx.py 加铁匠铺科研（跑完可删）"""
p = r"D:/测试一/blender/bs_v6/st_fx.py"
s = open(p, encoding="utf-8").read()

s = s.replace(
    'bones = [(b[0], (-b[1][0], b[1][1], b[1][2])) + tuple(b[2:]) for b in cfg["bones"]()]',
    'bones = [(b[0], (-b[1][0], b[1][1], b[1][2])) + tuple(b[2:]) for b in cfg["bones"](items)]')
s = s.replace('def lm_bones():', 'def lm_bones(_items=None):')
s = s.replace('"bones": [b[0] for b in cfg["bones"]()],',
              '"bones": [b[0] for b in cfg["bones"]([])],')

anchor = "\nRUN = ("
new = '''
# ── 铁匠铺：炉火 / 烟 / 锤 ──────────────────────────────────────────────────
HEARTH = (0.29, 4.40, 0.30)      # bs_model.forge_fire 的火塘中心


def bs_bones(items):
    """锤子的枢轴从 `anvil_hammer` 的包围盒算（手柄尾端），不写死常量 ——
    铁砧一旦挪位置，硬编码的枢轴就会让锤子绕着空气转。"""
    bpy.context.view_layer.update()
    hx, hy, hz = -0.52, 6.63, 1.90
    for it in items:
        ob = it[0]
        if ob.name == "anvil_hammer":
            pts = [ob.matrix_world @ v.co for v in ob.data.vertices]
            hx = min(p.x for p in pts)
            hy = sum(p.y for p in pts) / len(pts)
            hz = sum(p.z for p in pts) / len(pts)
            break
    return [("flame", HEARTH),
            ("smoke0", (HEARTH[0], HEARTH[1] + 0.62, 1.62)),
            ("smoke1", (HEARTH[0] + 0.16, HEARTH[1] + 0.70, 1.62)),
            ("smoke2", (HEARTH[0] - 0.14, HEARTH[1] + 0.58, 1.62)),
            ("hammer", (hx, hy, hz))]


def bs_groups():
    return {"flame": ("flame_", "flametip"),
            "hammer": ("anvil_hammer",)}


def bs_smoke():
    out = []
    for i in range(3):
        ob = box("smoke_%d" % i, (HEARTH[0] + 0.16 * (i - 1), HEARTH[1] + 0.64, 1.62),
                 (0.30, 0.30, 0.30), M("ash"))
        out.append((ob, 0.0, 0, 1, "smoke%d" % i))
    return out


def bs_clip(arm, act):
    """60 帧 / 2 s：火焰呼吸（0.55→1.06）+ 三团烟错相位上升 + 锤子两次敲击。"""
    pb = arm.pose.bones
    n = 60
    f = pb["flame"]
    for (t, sv) in ((0.0, 0.55), (0.22, 0.98), (0.38, 1.06), (0.62, 0.86),
                    (0.80, 1.02), (1.0, 0.55)):
        _key_scale(f, n * t, (sv, sv * (0.96 + 0.10 * t), sv))
    for i in range(3):
        p = pb["smoke%d" % i]
        ph = i * 0.30
        seq = ((0.00, 0.0, 0.0), (0.10, 0.9, 0.30), (0.55, 0.55, 1.25),
               (0.95, 0.0, 1.75), (1.00, 0.0, 0.0))
        for (ft, sv, dz) in seq:
            t = n if ft >= 1.0 else n * min(1.0, ph + ft)
            _key_scale(p, t, sv)
            _key_loc(p, t, (0, 0, dz))
    h = pb["hammer"]
    for k in range(3):
        base = 0.10 + 0.28 * k
        _key_rot(h, n * base, 0.0, "Y")
        _key_rot(h, n * (base + 0.09), -34.0, "Y")
        _key_rot(h, n * (base + 0.17), 2.0, "Y")
        _key_rot(h, n * (base + 0.23), 0.0, "Y")
    _key_rot(h, n, 0.0, "Y")

'''
s = s.replace(anchor, new + anchor, 1)
s = s.replace(
    '    "伐木场_科研": dict(asset="伐木场", mod="lm_model", kind="research", prefix="LM",',
    '''    "铁匠铺_科研": dict(asset="铁匠铺", mod="bs_model", kind="research", prefix="BS",
                   bones=bs_bones, groups=lambda: bs_groups(),
                   clip=lambda arm, act: bs_clip(arm, act),
                   fx=lambda: bs_smoke(), front=0.95,
                   note="炉火呼吸 / 三团烟上升 / 锤子敲砧"),
    "伐木场_科研": dict(asset="伐木场", mod="lm_model", kind="research", prefix="LM",''')
open(p, "w", encoding="utf-8").write(s)
print("patched", len(s))
