# -*- coding: utf-8 -*-
"""_patch_web.py —— 把状态资产 / 新建筑登记进 预览.html 与 建造系统.html（一次性，可重跑）"""
import glob
import json
import os
import re

ROOT = r"D:/测试一"
PREVIEW = os.path.join(ROOT, "预览.html")
BUILD = os.path.join(ROOT, "建造系统.html")

STATE = [
    ("城镇大厅 · 升级1", [("th_up1", "城镇大厅_升级1", "城镇大厅/城镇大厅_升级1.glb", "升级态 · 一本→二本")]),
    ("城镇大厅 · 升级2", [("th_up2", "城镇大厅_升级2", "城镇大厅/城镇大厅_升级2.glb", "升级态 · 二本→三本")]),
    ("城镇大厅 · 训练", [("th_train", "城镇大厅_训练", "城镇大厅/城镇大厅_训练.glb", "训练态 · 门开")]),
    ("哨塔 · 升级", [("wt_up", "哨塔_升级", "哨塔/哨塔_升级.glb", "升级态 · 通用")]),
    ("兵营 · 训练", [("br_train", "兵营_训练", "兵营/兵营_训练.glb", "训练态 · 武器架点亮")]),
    ("伐木场 · 科研", [("lm_res", "伐木场_科研", "伐木场/伐木场_科研.glb", "科研态 · research clip")]),
    ("铁匠铺 · 科研", [("bs_res", "铁匠铺_科研", "铁匠铺/铁匠铺_科研.glb", "科研态 · research clip")]),
    ("神秘圣地 · 训练", [("ms_train", "神秘圣地_训练", "神秘圣地/神秘圣地_训练.glb", "训练态 · 门前光")]),
    ("蒸汽车坊 · 训练", [("sw_train", "蒸汽车坊_训练", "蒸汽车坊/蒸汽车坊_训练.glb", "训练态 · 门开")]),
    ("初级帐篷", [("tn1", "初级帐篷", "初级帐篷/初级帐篷.glb", "一级 · 单杆单布"),
              ("tn1_up", "初级帐篷_升级", "初级帐篷/初级帐篷_升级.glb", "升级态")]),
    ("中等帐篷", [("tn2", "中等帐篷", "中等帐篷/中等帐篷.glb", "二级 · 脊帐双层"),
              ("tn2_up", "中等帐篷_升级", "中等帐篷/中等帐篷_升级.glb", "升级态")]),
    ("豪华帐篷", [("tn3", "豪华帐篷", "豪华帐篷/豪华帐篷.glb", "三级 · 四柱三层")]),
    ("城镇大厅二本", [("kh_mid", "城镇大厅二本", "城镇大厅二本/城镇大厅二本_手游_近.glb", "手游近景"),
                 ("kh_low", "城镇大厅二本", "城镇大厅二本/城镇大厅二本_低模.glb", "低模"),
                 ("kh_hi", "城镇大厅二本", "城镇大厅二本/城镇大厅二本.glb", "细分")]),
]


def patch_preview():
    s = open(PREVIEW, encoding="utf-8").read()
    if "th_up1" in s:
        print("预览.html 已登记，跳过")
        return
    rows = []
    for title, items in STATE:
        btns = "".join('\n    <button data-m="%s">%s</button>' % (k, lbl % () if "%s" in lbl else lbl)
                       for (k, _n, _f, lbl) in items)
        rows.append('  <div class="row">%s\n  </div>' % btns)
    block = "\n".join(rows)
    anchor = '  <div class="row">\n    <button id="wire">'
    assert anchor in s
    s = s.replace(anchor, block + "\n" + anchor, 1)

    entries = []
    for title, items in STATE:
        for (k, name, rel, kind) in items:
            entries.append('  %s: { file: \'assets/建筑/联盟/%s\', name: \'%s\', kind: \'%s\' },'
                           % (k, rel, name, kind))
    import re as _re
    m2 = _re.search(r"^  fs_lo:.*$", s, _re.M)
    assert m2, "找不到 fs_lo 行"
    s = s[:m2.end()] + "\n" + "\n".join(entries) + s[m2.end():]
    open(PREVIEW, "w", encoding="utf-8").write(s)
    print("预览.html += %d 个状态资产按钮 / %d 条 MODELS" % (sum(len(i) for _t, i in STATE), len(entries)))


def build_entry(cn, path):
    d = json.load(open(path, encoding="utf-8"))
    fp = d.get("footprint") or [0, 0]
    lifts = d.get("lifts") or []
    rel = os.path.relpath(os.path.join(ROOT, "assets", "建筑", "联盟", cn, cn + "_建造.glb"),
                          os.path.join(ROOT)).replace("\\", "/")
    return {
        "id": cn, "cn": cn, "file": rel, "fp": [round(fp[0], 3), round(fp[1], 3)],
        "h": round(d.get("height", 1.0), 3), "z0": d.get("z0", 0.45),
        "t_rev0": d.get("t_rev0", 0.46), "t_rev1": d.get("t_rev1", 3.0),
        "rev": d.get("rev", 2.5), "t_end": d.get("t_end", 4.5),
        "t_clean": d.get("t_clean", 3.5), "lifts": lifts, "nl": d.get("nl") or len(lifts),
        "kb": round(d.get("bytes", 0) / 1024), "tri_body": d.get("tri_body", 0),
        "tri_site": d.get("tri_site", 0),
    }


def patch_build():
    s = open(BUILD, encoding="utf-8").read()
    m = re.search(r"const DATA = (\{.*?\});", s, re.S)
    assert m, "找不到 DATA"
    data = json.loads(m.group(1))
    have = {b["id"] for b in data["buildings"]}
    added = []
    for cn in ("城镇大厅二本", "初级帐篷", "中等帐篷", "豪华帐篷"):
        p = os.path.join(ROOT, "docs", "建造系统", "参数", cn + ".json")
        if not os.path.exists(p) or cn in have:
            continue
        e = build_entry(cn, p)
        if os.path.exists(os.path.join(ROOT, e["file"])):
            data["buildings"].append(e)
            added.append(cn)
    if not added:
        print("建造系统.html 无新增（或已登记）")
        return
    js = json.dumps(data, ensure_ascii=False, separators=(", ", ": "))
    s = s[:m.start(1)] + js + s[m.end(1):]
    open(BUILD, "w", encoding="utf-8").write(s)
    print("建造系统.html += %s" % added)


patch_preview()
patch_build()
