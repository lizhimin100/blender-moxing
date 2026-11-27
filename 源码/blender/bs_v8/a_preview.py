# -*- coding: utf-8 -*-
"""a_preview.py —— 用体检结果重写 预览_微缩建筑.html 的 BUILDINGS 数据块

    python a_preview.py

数据从 docs/_tmp/v8/check.json 来（高度 / 面数 / 队色 / 占地都是真的），
文案手写在 DESC 里。页面本身是通用 three.js 查看器，只换数据。
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CHECK = os.path.join(ROOT, "docs", "_tmp", "v8", "check.json")
HTML = os.path.join(ROOT, "预览_微缩建筑.html")

EN = {
    "城镇大厅": "TOWN HALL", "兵营": "BARRACKS", "农场": "FARM",
    "铁匠铺": "BLACKSMITH", "伐木场": "LUMBER MILL", "哨塔": "WATCH TOWER",
    "箭塔": "ARROW TOWER",
}
KEY = {
    "城镇大厅": "th", "兵营": "bk", "农场": "fm", "铁匠铺": "sm",
    "伐木场": "lm", "哨塔": "wt", "箭塔": "at",
}
TIER = {
    "城镇大厅": ["市政厅 · 钟亭", "主城 Keep · 角楼", "城堡 · 四角塔"],
    "兵营": ["木石营棚 · 大拱门", "石砌营房 · 扶壁", "皇家要塞 · 双门楼"],
    "农场": ["农舍 · 麦田", "谷仓农场 · 筒仓", "风车农场 · 三体量"],
    "铁匠铺": ["敞棚铁铺 · 炉膛", "石砌铁铺 · 烟囱", "大师工坊 · 双炉"],
    "伐木场": ["敞棚锯木 · 原木", "石基磨坊 · 圆锯", "吊木工场 · 扒杆"],
    "哨塔": ["木构哨塔 · 梯", "石基哨塔 · 混构", "石砌哨塔 · 瞭望室"],
    "箭塔": ["石砌箭塔 · 斗堡", "双耳箭塔 · 锥顶", "皇家箭塔 · 弩炮"],
}
DESC = {
    "城镇大厅": [
        "单层半木构 + 厚蓝瓦顶 + 石阶门廊 + 脊上矮钟亭（市政四件套：钟面 / 拱门 / 蓝瓦 / 挂旗）",
        "L 型石砌主体 + 前左角楼（锯齿垛口）+ 竖脊门楼 + 长旗；墙换石、体量分叉",
        "四角塔围合 + 幕墙 + 中央大厅 + 门楼 + 金脊；包络线 0.43→0.55→0.61→0.85 金字塔",
    ],
    "兵营": [
        "矮营棚 + 夸张宽大的半圆拱门 + 平顶垛口 + 木栏；正面没有一片斜瓦",
        "全面石砌 + 拱门两侧阶梯扶壁 + 后半层蓝瓦军械库 + 矮石前庭",
        "双层城门楼 + 双哨堡（蓝锥顶）+ 铁栅 + 金交叉剑盾徽 + 后方蓝瓦营房",
    ],
    "农场": [
        "半木构农舍 + 麦田 + 栅栏 + 草捆",
        "谷仓（双开大门）+ 筒仓 + 农舍 + 前庭",
        "风车塔（四叶队色帆）+ 谷仓 + 筒仓 + 成垄麦田 + 板车 + 稻草人",
    ],
    "铁匠铺": [
        "敞棚 + 石砌炉膛（橙红炉口）+ 铁砧 + 水桶",
        "石砌铺面 + 高烟囱 + 侧挂工作间 + 磨石 + 武器架",
        "双烟囱 + 门前披檐 + 金砧徽章 + 铁锭堆",
    ],
    "伐木场": [
        "敞棚 + 原木堆 + 锯木架",
        "石基磨坊 + 立式圆锯 + 原木坡道 + 木板堆",
        "吊木扒杆 + 大圆锯 + 原木堆 + 板车",
    ],
    "哨塔": [
        "四根外撇木腿 + 横箍 + 梯 + 带栏杆平台 + 蓝锥顶",
        "石砌塔身 + 上段木构瞭望室 + 出挑平台 + 蓝锥顶",
        "全石塔 + 阶梯扶壁 + 挑石垛口 + 木构瞭望室 + 矮四坡顶",
    ],
    "箭塔": [
        "石塔 + 正面木斗堡 + 四垛 + 长垂幔",
        "加高 + 双耳斗堡（蓝锥顶）+ 腰线 + 矮院墙",
        "厚塔 + 四角外挑小塔 + 托石 + 弩炮 + 四面垂幔",
    ],
}
PAL = [["#6B6152", "底座"], ["#8A7E68", "台基"], ["#B8B4A8", "浅灰暖石"],
       ["#D2CEC1", "石亮"], ["#6E4A2E", "深橡木"], ["#E2D8C5", "灰泥"],
       ["#5A6470", "冷铁"], ["#D9A441", "暖金"], ["#FF6A20", "炉火"],
       ["#D8A838", "麦田"]]


def main():
    rows = json.load(io.open(CHECK, encoding="utf-8"))
    by = {}
    for r in rows:
        by.setdefault(r["building"], {})[r["star"]] = r

    out = ["const BUILDINGS = {"]
    for cn in EN:
        if cn not in by:
            continue
        k = KEY[cn]
        out.append("  %s: {" % k)
        out.append("    cn: '%s', en: '%s'," % (cn, EN[cn]))
        out.append("    dir: 'assets/建筑/联盟/%s_微缩/'," % cn)
        out.append("    file: s => `%s_${s}星.glb`," % cn)
        out.append("    slots: '2（Mat_Neutral / Mat_TeamColor）',")
        out.append("    pal: [%s]," % ", ".join(
            "['%s','%s']" % (c, n) for c, n in PAL))
        out.append("    info: {")
        for s in (1, 2, 3):
            r = by[cn][s]
            out.append(
                "      %d: { name: '%s', h: '%.3f m', tris: %d, team: %.1f, "
                "span: '%.2f × %.2f', desc: '%s' },"
                % (s, TIER[cn][s - 1], r["max"][2], r["tris"], r["team_area"],
                   r["span"][0], r["span"][1], DESC[cn][s - 1]))
        out.append("    },")
        out.append("  },")
    out.append("};")
    block = "\n".join(out)

    html = io.open(HTML, encoding="utf-8").read()
    i0 = html.index("const BUILDINGS = {")
    i1 = html.index("\n};", i0) + 3
    html = html[:i0] + block + html[i1:]
    html = html.replace("const wraps = { th: {}, bk: {} };", "const wraps = {};")
    html = html.replace("<title>微缩建筑线 · 1 m 格 · 联盟</title>",
                        "<title>联盟七建筑 · 微缩线 · 1 m 格</title>")
    html = html.replace("联盟建筑 · 微缩线 · 1 m 格",
                        "联盟七建筑 · 微缩线 · 1 m 格 · WC3 体块语法")
    io.open(HTML, "w", encoding="utf-8").write(html)
    print("preview updated:", HTML)


if __name__ == "__main__":
    main()
