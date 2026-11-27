"""icon_shots.py —— 建筑图标（UI 用）专用出图

和 bs_shots 的区别：那不是图标，是"展示图"。图标有三条硬要求：

  ① **必须透明底**。图标要贴在按钮 / 建造菜单 / 卡片上，底图颜色由 UI 决定。
     出图时 film_transparent=True，世界光只用来照明、不进画面。
  ② **必须相机相对布光**。所有建筑用同一套"左上主光 + 右补光 + 背后轮廓光"，
     光源按相机基向量摆放，换机位时光位跟着转 —— 否则两座建筑的受光面不一样，
     摆在一排菜单里一眼看出是两批图。
  ③ **必须投影后取景**。用包围盒取景会被斜视角骗（盒子比剪影大一圈），
     图标会显得"飘在小框里"。这里把**顶点逐个投影**到相机平面再取边框，
     保证剪影四边留白相等。

产物：
  docs/图标/试拍/<建筑>_az{az}_el{el}.png   候选机位（256²，透明底）
  assets/图标/<建筑>_图标.png               成品（512²，透明底，带接触阴影）
  assets/图标/<建筑>_图标_{128,64}.png      缩小自检（看 64 px 还认不认得出）
  docs/图标/<建筑>_图标_暗底.png / _亮底.png  UI 上的实际效果（透明底不适合作展示）
"""

import importlib
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = r"D:/测试一/blender/bs_v6"
ROOT = r"D:/测试一"
OUT_CAND = os.path.join(ROOT, "docs", "图标", "试拍")
OUT_ICON = os.path.join(ROOT, "docs", "_tmp", "图标原图")
OUT_DOC = os.path.join(ROOT, "docs", "图标")

if HERE not in sys.path:
    sys.path.insert(0, HERE)
import bslib  # noqa: E402
for _m in ("bslib", "bs_model", "br_model", "th_model", "wt_model", "fm_model",
           "lm_model", "ms_model", "sw_model", "at_model",
           "dl_kit", "dg_model", "uc_model", "tv_model", "fr_model", "fs_model",
           "tent_model", "keep_model"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

# ── 机位候选：(方位角, 仰角) ────────────────────────────────────────────────
# 方位角 0 = 正对建筑正面（模型正面 +Y），正数往 +X 转；仰角 0 = 平视。
# 这批是给 RTS 建造菜单用的"小立体模型"视角：能同时看到正立面、一个侧立面、屋面。
CANDIDATES = [(24, 22), (28, 26), (32, 30), (38, 34)]
STAGE = os.environ.get("ICON_STAGE", "final")  # cand / final
FINAL = (26, 24)

RES_CAND = 256
RES_FINAL = 512
SAMPLES_CAND = 32
SAMPLES_FINAL = 96
MARGIN = 1.06          # 剪影外留 6%
SHADOW = 0.34          # 接触阴影不透明度


# 取景 / 布光 / 渲染设置全部来自 iconlib —— 建筑与单位图标只有这一份实现。
from iconlib import (MARGIN, clear_scene, basis, project_fit, make_cam,   # noqa: E402,F401
                     studio_world, add_area, studio_lights, set_render, render_to)


def build_target(key):
    if key == "铁匠铺":
        import bs_model as mod
    elif key == "城镇大厅":
        import th_model as mod
    elif key == "哨塔":
        import wt_model as mod
    elif key == "农场":
        import fm_model as mod
    elif key == "伐木场":
        import lm_model as mod
    elif key == "神秘圣地":
        import ms_model as mod
    elif key == "蒸汽车坊":
        import sw_model as mod
    elif key == "箭塔":
        import at_model as mod
    elif key == "地牢":
        import dg_model as mod
    elif key == "地下城入口":
        import uc_model as mod
    elif key == "酒馆内部":
        import tv_model as mod
    elif key == "折壳入口":
        import fs_model as mod
    elif key == "城镇大厅二本":
        import keep_model as mod
    elif key in ("营火", "火把", "火炬", "火堆"):
        import fr_model as frmod
        return frmod.build(key, smooth=True, unwrap=False)
    elif key in ("初级帐篷", "中等帐篷", "豪华帐篷"):
        # Tent 的 Model 按 tier 建，没有模块级 build()；objs/stats 的返回口径与
        # keep_model.build 一致，后面的取景 / 布光直接用。
        import tent_model as tmod
        m = tmod.build_tier(key, smooth=True)
        objs = m.finalize(bevel=True)
        return objs, bslib.stats(objs)
    else:
        import br_model as mod
    objs, st = mod.build(smooth=True, unwrap=False)
    return objs, st


def _unused_contact_shadow(img_path, out_path, res):  # 见 icon_post.py
    """在图底加一片软阴影：没有地面也要"坐得住"。

    Blender 里做 shadow catcher（EEVEE 需要 plane + 材质混合）容易把 alpha 弄脏，
    这里直接在 8 位 alpha 上合成 —— 只影响成品图，不影响剪影本身。
    """
    from PIL import Image, ImageDraw, ImageFilter

    im = Image.open(img_path).convert("RGBA")
    a = im.split()[3]
    bbox = a.getbbox()
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    if bbox:
        x0, y0, x1, y1 = bbox
        w = x1 - x0
        cx = (x0 + x1) * 0.5
        ew = w * 0.86
        eh = max(6, int(res * 0.035))
        cy = y1 - eh * 0.45
        layer = Image.new("L", im.size, 0)
        d = ImageDraw.Draw(layer)
        d.ellipse([cx - ew * 0.5, cy - eh * 0.5, cx + ew * 0.5, cy + eh * 0.5], fill=255)
        layer = layer.filter(ImageFilter.GaussianBlur(radius=eh * 0.55))
        sh.putalpha(layer.point(lambda v: int(v * SHADOW)))
        sh = Image.composite(sh, Image.new("RGBA", im.size, (0, 0, 0, 0)), sh.split()[3])
    out = Image.alpha_composite(sh, im)
    out.save(out_path, "PNG", optimize=True)


def _unused_flatten(img_path, out_path, rgb):  # 见 icon_post.py
    from PIL import Image

    im = Image.open(img_path).convert("RGBA")
    bg = Image.new("RGBA", im.size, rgb + (255,))
    Image.alpha_composite(bg, im).convert("RGB").save(out_path, "PNG", optimize=True)


def run():
    receipt = {"stage": STAGE, "shots": {}, "ok": True}
    targets = ("初级帐篷", "中等帐篷", "豪华帐篷")
    for key in targets:
        clear_scene()
        objs, st = build_target(key)
        if STAGE == "cand":
            for az, el in CANDIDATES:
                ctr, span, size2d = project_fit(objs, az, el)
                make_cam(ctr, span, az, el)
                studio_world()
                studio_lights(ctr, span, az, el)
                p = os.path.join(OUT_CAND, "%s_az%d_el%d.png" % (key, az, el))
                n = render_to(p, RES_CAND, SAMPLES_CAND)
                receipt["shots"]["%s_%d_%d" % (key, az, el)] = n
                print("[cand]", key, az, el, "span %.2f" % span, "silhouette %.1fx%.1f" % size2d)
        else:
            az, el = FINAL
            ctr, span, size2d = project_fit(objs, az, el)
            make_cam(ctr, span, az, el)
            studio_world()
            studio_lights(ctr, span, az, el)
            raw = os.path.join(OUT_ICON, "_raw_%s.png" % key)
            n = render_to(raw, RES_FINAL, SAMPLES_FINAL)
            receipt["shots"][key] = {"bytes": n, "span": round(span, 3),
                                     "silhouette": [round(v, 3) for v in size2d],
                                     "angle": [az, el], "tris": st.get("tris")}
            print("[icon]", key, "span %.2f" % span, "sil %.1fx%.1f" % size2d, n)
    print("ICON_RECEIPT " + json.dumps(receipt, ensure_ascii=False))


run()
