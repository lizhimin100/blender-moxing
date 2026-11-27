"""icon_units.py —— 单位图标（UI 卡面）出图

和 icon_shots.py 的差别只有一处：**不改模型，直接导交付用的 GLB**。
为什么：单位是从脚本装配 + 绑骨 + 打动作出来的，重跑一遍要几十秒且可能和交付件不一致；
图标必须和船上的那个 GLB 是同一个东西，所以直接从 assets/ 里读。

取景 / 布光 / 渲染设置全部走 iconlib，与建筑图标同一套（见 iconlib.py 头部的三条要求）。

用法（在 Blender 里跑，走 build/bl_act.py）：
  ICON_UNIT_STAGE=cand python build/bl_act.py act blender/bs_v6/icon_units.py
  ICON_UNIT_STAGE=final ...

产物：
  docs/_tmp/图标原图/_raw_<单位>.png   512² 透明底，交给 icon_post.py 合成卡面
  docs/图标/试拍/unit_<单位>_az{az}_el{el}.png   候选机位（256²）
"""

import importlib
import json
import os
import sys

import bpy

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
SRC_UNIT = os.path.join(ROOT, "assets", "单位")
OUT_CAND = os.path.join(ROOT, "docs", "图标", "试拍")
OUT_ICON = os.path.join(ROOT, "docs", "_tmp", "图标原图")

if HERE not in sys.path:
    sys.path.insert(0, HERE)
for _m in ("iconlib",):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])
import iconlib  # noqa: E402

STAGE = os.environ.get("ICON_UNIT_STAGE", "final")

# 单位的机位比建筑**低**：建筑要看屋面（24°），人形在 24° 会俯视到头皮，
# 14° 才同时看得到脸、肩线和脚下的落地感。方位 22° 让武器先出剪影。
FINAL = (22, 14)
CANDIDATES = [(18, 10), (22, 14), (26, 18), (30, 22)]

# 单体人形：22°/14° 让武器先出剪影。
# **骑兵要单独给角度**：马的体长是竖直的 2 倍，正面机位会被马头顶掉骑士，
# 34° 侧前方才同时看得到马身、骑士和枪。
ANGLE_OVERRIDE = {"骑士": (-56, 14), "豺狼人萨满": (-12, 12),
                  "豺狼人战士": (16, 12), "豺狼人斥候": (8, 13)}

# 只出指定单位（逗号分隔），空 = 全出
UNIT_FILTER = [v for v in os.environ.get("ICON_UNIT_FILTER", "").split(",") if v]

RES_CAND = 256
RES_FINAL = 512
SAMPLES_CAND = 32
SAMPLES_FINAL = 96

# 分体件不是主力格，跳过（它们不进建造菜单）
# 精模的 _长面盾 / _十字利刃 也是分体件（部件单独出 glb 挂骨），同样不该出图标
SKIP_SUFFIX = ("_低模", "_手游_近", "_手游_中", "_手游_远", "_身体", "_武器",
               "_长面盾", "_十字利刃")


def find_units():
    """返回 [(key, glb 路径)]，key = GLB 文件名去扩展名。"""
    out = []
    for dirpath, _, files in os.walk(SRC_UNIT):
        for fn in sorted(files):
            if not fn.lower().endswith(".glb"):
                continue
            stem = os.path.splitext(fn)[0]
            if any(stem.endswith(s) for s in SKIP_SUFFIX):
                continue
            if UNIT_FILTER and not any(stem.endswith(k) for k in UNIT_FILTER):
                continue
            out.append((stem, os.path.join(dirpath, fn)))
    return sorted(out)


def load(path):
    """导 GLB，返回参与剪影的网格。

    **必须排掉 `glTF_not_exported` 集合里的东西**：Blender 的 glTF 导入器会给每根骨
    造一个显示用的棱角球（半径 1 m，放在原点）。它不在交付的 GLB 里（GLB 只有
    unit_body/unit_team/unit_trim 三个 mesh），但它是真实顶点 —— 混进取景会把
    包围盒撑到 2 m，人物缩在画面左侧一块，取景全废（踩过）。
    """
    bpy.ops.import_scene.gltf(filepath=path)
    bpy.context.view_layer.update()
    out = []
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        if any(c.name == "glTF_not_exported" for c in ob.users_collection):
            continue
        out.append(ob)
    return out


def reset_session():
    """每件单位都在**干净会话**里导。

    以前只用 iconlib.clear_scene()，它清对象/网格/材质，但不清 `bpy.data.actions`。
    连拍时后一件单位会绑上前一件留下的动作（实测弩兵绑到了 `death.001`），
    渲染帧刚好落在塌下去的姿势上，出图是一堆零件堆在地上 —— 而 GLB 本身是好的。
    所以这里直接 read_factory_settings 回空场景，动作库一起清掉。
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)


def main():
    receipt = {"stage": STAGE, "shots": {}, "ok": True}
    units = find_units()
    print("[units]", len(units), [k for k, _ in units])
    for key, path in units:
        reset_session()
        objs = load(path)
        if not objs:
            print("  ! 没有网格：", key)
            continue
        if STAGE == "cand":
            for az, el in CANDIDATES:
                ctr, span, size2d = iconlib.project_fit(objs, az, el)
                iconlib.make_cam(ctr, span, az, el)
                iconlib.studio_world()
                iconlib.studio_lights(ctr, span, az, el)
                p = os.path.join(OUT_CAND, "unit_%s_az%d_el%d.png" % (key, az, el))
                n = iconlib.render_to(p, RES_CAND, SAMPLES_CAND)
                print("[cand]", key, az, el, "span %.2f" % span,
                      "sil %.2fx%.2f" % size2d, n)
        else:
            az, el = ANGLE_OVERRIDE.get(key, FINAL)
            raw = os.path.join(OUT_ICON, "_raw_%s.png" % key)
            n, span, size2d = iconlib.shoot(objs, az, el, raw,
                                            res=RES_FINAL, samples=SAMPLES_FINAL)
            # 兜底：人形剪影高度应当 1.2~2.0 m（傀儡 4.3 m）。低于 1 m 说明绑骨/动作出错，
            # 输出的是一堆零件，不能进图标库。
            tall = max(size2d)
            if tall < 1.0:
                receipt["ok"] = False
                print("  !! 剪影只有 %.2f m，疑似姿势异常：%s" % (tall, key))
            receipt["shots"][key] = {"bytes": n, "span": round(span, 3),
                                     "silhouette": [round(v, 3) for v in size2d],
                                     "angle": [az, el],
                                     "meshes": len(objs)}
            print("[icon]", key, "span %.2f" % span, "sil %.2fx%.2f" % size2d, n)
    print("UNIT_ICON_RECEIPT " + json.dumps(receipt, ensure_ascii=False))


main()
