"""gen_bible.py —— 生成《体素建筑生产册》(纯建筑 · 自包含 HTML)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from matlib import MATERIALS
from buildings import BUILD_INDEX, STAGES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs")
REPORT_P = os.path.join(ROOT, "assets", "warband", "buildings", "_buildings_report.json")

try:
    with open(REPORT_P, encoding="utf-8") as _f:
        BREPORT = json.load(_f)
except Exception:
    BREPORT = {}

TEAMS = [("血红", "#b8352c", "#ffcf7a"), ("钴蓝", "#2f5fb0", "#9fd0ff"),
         ("苔绿", "#4a7a34", "#c2e88a"), ("紫晶", "#6b3fa0", "#d9b6ff"),
         ("琥珀", "#c98a1e", "#ffe6a3")]

BUILD_ROWS = [
    ("城镇大厅", "townhall", "屋脊 ∥X · 41°", "双层出挑 + 全高门廊塔 + 前向交叉山墙 + 主脊钟楼",
     "三面旗帜 + 门楣纹章", "青灰石砌 + 灰泥半木构"),
    ("兵营", "barracks", "屋脊 ∥Z · 28°", "单脊 + 阶梯山墙 + 屋顶瞭望塔",
     "营门木栅 + 盾墙 + 长矛束 + 靶桩 ×3", "灰泥填充 + 深木骨"),
    ("铁匠铺", "blacksmith", "单坡 →+X · 25°", "薄壳瓦面 + 两端三角填充 + 高侧实墙",
     "外露炉膛（炉火自发光）+ 独立烟囱 9.3m", "粗石 + 暖光"),
    ("农场", "farm", "屋脊 ∥X · 50°", "陡坡谷仓 + 方形筒仓 7.5m",
     "L 形围栏 + 草垛 + 水槽", "原木竖板 + 麦秸顶"),
    ("哨塔", "watchtower", "方冠 · 双层出檐", "实体基座小屋 + 四柱木构 + 三面观景廊",
     "瞭望平台 + 双梯 + 铜锣 + 挑旗", "深木 + 石基"),
    ("伐木场", "lumbermill", "单坡 →−Z · 30°", "敞棚 + 后墙承脊 + 檐下椽头",
     "锯台 + 原木金字塔堆", "板材 + 木瓦"),
]

TEAM_ZONES = [
    ("城镇大厅", "山墙旗 2 面 + 门廊挂旗 + 檐口饰条 + 门楣纹章（TC2）"),
    ("兵营", "营门双旗 + 屋顶旗 + 盾墙 6 面盾面 + 门侧长矛束绑带 + 门楣盾徽（TC2）"),
    ("铁匠铺", "山墙挑旗 + 门楣横匾 + 檐口饰条"),
    ("农场", "筒仓竖旗 + 谷仓门楣饰带 + 围栏桩顶"),
    ("哨塔", "平台三面垂旗 + 塔顶旗 + 铜锣吊带"),
    ("伐木场", "棚檐饰条 + 锯台挡板 + 原木堆端面标记"),
]

CSS = """
:root{--bg:#0d0f13;--pnl:#14171d;--pnl2:#191d25;--ln:#262c37;--tx:#e6e9ef;--dim:#858d9d;
--acc:#c9a227;--red:#b8352c;--mono:"JetBrains Mono",ui-monospace,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);
font:14px/1.7 "Inter","Sarasa Gothic SC","PingFang SC","Microsoft YaHei",sans-serif;
-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 34px 100px}
header{padding:78px 0 44px;border-bottom:1px solid var(--ln);margin-bottom:12px}
.kicker{font:11px/1 var(--mono);letter-spacing:.34em;color:var(--acc);text-transform:uppercase}
h1{margin:16px 0 10px;font-size:46px;line-height:1.06;font-weight:700;letter-spacing:-.02em}
h1 em{font-style:normal;color:var(--dim);font-weight:300}
.lede{max-width:640px;color:#a8b0be;font-size:15px}
.stat{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--ln);
border:1px solid var(--ln);margin:34px 0 0}
.stat div{background:var(--pnl);padding:16px 18px}
.stat b{display:block;font-size:27px;font-weight:600;letter-spacing:-.02em}
.stat span{font:10px/1.5 var(--mono);letter-spacing:.16em;color:var(--dim);text-transform:uppercase}
h2{margin:64px 0 6px;font-size:11px;letter-spacing:.3em;color:var(--acc);text-transform:uppercase;
font-weight:500}
h3{margin:6px 0 20px;font-size:26px;font-weight:600;letter-spacing:-.01em}
h4{margin:26px 0 8px;font-size:14px;letter-spacing:.02em}
p{color:#b6bdc9;margin:10px 0}
.mono{font-family:var(--mono);font-size:12px}
code{font-family:var(--mono);font-size:12px;background:#1c2129;padding:2px 6px;border-radius:3px;color:#d9c88a}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:26px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.card{background:var(--pnl);border:1px solid var(--ln);padding:18px 20px}
.card b{color:var(--acc);font:11px/1 var(--mono);letter-spacing:.2em}
.card h4{margin:10px 0 6px;font-size:15px}
.card p{margin:0;font-size:13px;color:#98a1b0}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin:14px 0}
th{text-align:left;font:10px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--dim);
padding:9px 10px;border-bottom:1px solid var(--ln)}
td{padding:8px 10px;border-bottom:1px solid #1c212a;color:#b9c0cc}
td.k{color:#e8d79b;font-family:var(--mono);font-size:11.5px}
td.n{font-family:var(--mono);font-size:11.5px;color:#8f98a8;text-align:right}
tr:hover td{background:#141821}
.sw{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
.sw div{flex:1;min-width:140px;border:1px solid var(--ln);background:var(--pnl);overflow:hidden}
.sw i{display:block;height:56px}
.sw p{margin:0;padding:9px 12px;font-size:12px}
.sw span{font-family:var(--mono);font-size:10.5px;color:var(--dim);display:block}
.rule{display:flex;gap:14px;padding:14px 0;border-bottom:1px solid #1a1e26}
.rule em{font:11px/1 var(--mono);color:var(--acc);font-style:normal;padding-top:4px;min-width:26px}
.rule div{flex:1}
.rule>div>b{display:block;font-size:14px;margin-bottom:3px}
.rule p b,.rule p strong{color:#e2d5a8;font-weight:600}
.rule p{margin:0;font-size:12.5px;color:#98a1b0}
.bar{display:flex;height:26px;margin:12px 0;border:1px solid var(--ln);overflow:hidden;font:10px/26px var(--mono)}
.bar i{display:block;text-align:center;color:#0d0f13;font-weight:700;letter-spacing:.1em}
.note{background:#1a1710;border-left:2px solid var(--acc);padding:12px 16px;margin:20px 0;font-size:13px;
color:#cbbf9a}
.note b{color:var(--acc)}
footer{margin-top:80px;padding-top:20px;border-top:1px solid var(--ln);font:11px/1.8 var(--mono);color:#4d5563}
"""


def mat_rows():
    out = []
    for n, (fn, tile) in MATERIALS.items():
        em = "BC / N / ORM / E" if n in ("emblem", "ember", "window") else "BC / N / ORM"
        out.append(f"<tr><td class='k'>{n}</td><td class='n'>{tile:.2f} m</td>"
                   f"<td class='n'>512²</td><td>{em}</td></tr>")
    return "\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)

    build_rows = "\n".join(
        f"<tr><td class='k'>{cn}</td>"
        f"<td class='n'>{BREPORT.get(bid, {}).get('height', '—')} m</td>"
        f"<td class='n'>{BREPORT.get(bid, {}).get('boxes', '—')}</td>"
        f"<td class='n'>{BREPORT.get(bid, {}).get('nodes', '—')}</td>"
        f"<td>{roof}</td><td>{feature}</td></tr>"
        for cn, bid, roof, feature, land, mat in BUILD_ROWS)

    zone_rows = "\n".join(
        f"<tr><td class='k'>{cn}</td><td>{z}</td></tr>" for cn, z in TEAM_ZONES)

    stage_rows = "\n".join(
        f"<tr><td class='k'>{nm}</td><td class='n'>{a:.3f}–{b:.3f}</td>"
        f"<td class='n'>{a * 4.8:.2f}–{b * 4.8:.2f}s</td><td>{desc}</td></tr>"
        for (sid, nm, a, b), desc in zip(STAGES, [
            "场地放线木框落位", "两级台基落座", "脚手架竖起（严格晚于台基）",
            "墙体下段砌筑", "墙体中段 + 门窗洞", "墙体上段 + 隅石",
            "阁楼 / 山墙封板", "楼板、梁架、外露椽木",
            "屋面下段铺瓦", "屋面上段收脊",
            "门窗扇、招牌、脊饰、钟楼", "旗帜与脊顶旗"]))

    st_total = sum(r["boxes"] for r in BREPORT.values()) if BREPORT else 0
    node_total = sum(r["nodes"] for r in BREPORT.values()) if BREPORT else 0
    pal = "\n".join(
        f"<div><i style='background:linear-gradient(90deg,{c},{g})'></i>"
        f"<p>{n}<span>{c} / {g}</span></p></div>" for n, c, g in TEAMS)

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ironbound Legion · 体素建筑生产册</title><style>{CSS}</style></head><body><div class="wrap">

<header>
<div class="kicker">Voxel Buildings · Production Bible</div>
<h1>Ironbound Legion<br><em>铁誓军团 · 体素建筑生产册</em></h1>
<p class="lede">西幻中世纪 / 魔兽争霸三风格的体素建筑。全部几何由轴对齐长方体构成，零曲面零斜面；
坡度用阶梯体块，斜撑用阶梯段。六座建筑合计 {st_total:,} 个长方体，13 个施工阶段驱动
"放线 → 台基 → 脚手架 → 砌墙 → 梁架 → 铺瓦 → 饰件 → 升旗 → 拆架"。
装备 PBR 五贴图与 TC1/TC2 阵营染色遮罩，导出 glTF 2.0 供 Godot 4.7 直接使用。</p>
<div class="stat">
  <div><b>6</b><span>Buildings</span></div>
  <div><b>18</b><span>Clips</span></div>
  <div><b>{st_total:,}</b><span>Axis-aligned Boxes</span></div>
  <div><b>2</b><span>Team-Color Params</span></div>
</div>
</header>

<h2>01 — 造型法则</h2>
<h3>只有长方体，但必须有体积感</h3>
<div class="rule"><em>R1</em><div><b>零曲面</b>
<p>圆柱、球、锥、环一律禁止。屋顶用阶梯体块读坡度，斜撑用阶梯段读角度，角落收头用隅石。
曲面感的替代品是<b>错位</b>：两个盒子在平面上的 1–2 cm 偏移，比一条倒角线更能说明体积。</p></div></div>
<div class="rule"><em>R2</em><div><b>屋顶必须坐实</b>
<p>屋面的起始高度一律等于墙顶高度，不允许"悬在墙上"。双坡用<b>实心阶梯体块</b>逐级落地，
单坡用<b>薄壳瓦面</b>（厚度 = 台阶落差 × 1.75，把踏步立面完全盖住）+ 两端三角山墙填充，
再在高侧补一道砌到脊下的实墙 —— 否则单坡会读成"一块斜立的板"。</p></div></div>
<div class="rule"><em>R3</em><div><b>先定位再记录</b>
<p>每个施工阶段先算出自身最终包围盒，<b>以底面中心定死枢轴</b>，再挂到父节点上。
这样节点不会继承旧坐标，屋顶、顶棚、烟囱不会与墙体错位。构件之间的所有对齐都由同一套坐标常量推导，
不出现手工填的魔法数。</p></div></div>
<div class="rule"><em>R4</em><div><b>剖面四段式</b>
<p>可读的建筑都有同一条剖面节奏：<b>实体基座 → 露明骨架 → 挑出构件 → 收分冠顶</b>。
哨塔是这条法则的原型（石基 → 四柱 → 观景廊 → 方冠），其余五座按自身职责替换这四段的内容。</p></div></div>

<h2>02 — 材质</h2>
<h3>十五套，一套程序化生成</h3>
<p>纹理由程序噪声 + 规则栅格生成，全部无缝平铺：石材按整数行列切缝砌筑并带灰缝与雨渍、
木材按板宽分块并叠加年轮与风化裂缝、金属走拉丝 + 稀疏划痕 + 划痕处氧化偏暖、
布料走经纬交织 + 毛羽噪声、木瓦按错缝排列并压出瓦口阴影。512² 起点，米级平铺尺度写入材质表。</p>
<table>
<tr><th>Material</th><th>平铺尺度</th><th>尺寸</th><th>通道</th></tr>
{mat_rows()}
</table>
<p class="mono" style="color:#7c8595">BC=BaseColor · N=Normal(+Y) · ORM = R:AO / G:Roughness / B:Metallic / <b style="color:#c9a227">A:TC1 遮罩</b> · E=TC2/自发光</p>

<h2>03 — 阵营染色</h2>
<h3>一套材质参数，而不是多套预制贴图</h3>
<p>采用与《奇点灰烬》同构的遮罩方案：把「受阵营色影响」与「保留固有色」在<b>像素级</b>分开。
建筑的染色集中在<b>旗帜、檐口饰条、门楣纹章、盾面</b>这类点睛部位 —— 面积小而位置高，
在 RTS 俯视角下依然能一眼读出阵营。</p>
<div class="bar">
  <i style="background:#b8352c;width:30%">TC1 旗面</i>
  <i style="background:#ffcf7a;width:15%;color:#2a2410">TC2 纹章</i>
  <i style="background:#6a4a33;width:22%;color:#e8dcc8">木构固有色</i>
  <i style="background:#8d949b;width:18%;color:#1a1d22">石 / 金属</i>
  <i style="background:#c98a1e;width:15%;color:#2a1d10">炉火 / 窗光</i>
</div>
<div class="grid2">
<div><h4>遮罩怎么走</h4>
<p>染色遮罩写在 ORM 贴图的 <b>A 通道</b>：1 = 完全染色，0 = 完全保留。运行时着色器用
<code>albedo = mix(base, team_main × luminance, mask)</code> 替换色相但保留织物明暗，
所以换色后布纹、缝线、磨损都还在。</p></div>
<div><h4>为什么不是两套贴图</h4>
<p>每换一个阵营就复制一份贴图，会让 6 座建筑膨胀到 30+ 套贴图，包体与显存翻倍。
现在换色 = 改 2 个 uniform，五个阵营同屏共享同一份贴图与材质实例。</p></div>
</div>
<div class="sw">{pal}</div>
<table>
<tr><th>建筑</th><th>染色部位</th></tr>
{zone_rows}
</table>

<h2>04 — 建筑差异化</h2>
<h3>六座，六种屋顶，六种墙体做法</h3>
<p>职责必须在不看 UI 的情况下被读出来。因此六座建筑在<b>屋顶朝向 / 坡度 / 附属物</b>三个维度上全部分开，
墙体做法也刻意区分：石砌用于市政与冶炼，半木构用于军事，原木竖板用于农业，纯木构用于塔与工棚。</p>
<table>
<tr><th>建筑</th><th>总高</th><th>长方体</th><th>节点</th><th>屋顶</th><th>特征构件</th></tr>
{build_rows}
</table>
<h4 style="margin-top:32px">场院地标（剪影之外的第二识别层）</h4>
<p class="mono" style="color:#7c8595">城镇大厅：三面旗帜 + 门楣纹章 ／ 兵营：营门木栅 + 盾墙 + 长矛束 + 靶桩 ／
铁匠铺：外露炉膛 + 独立烟囱 ／ 农场：L 形围栏 + 草垛 + 水槽 ／ 哨塔：双梯 + 铜锣 ／ 伐木场：锯台 + 原木金字塔</p>

<h2>05 — 施工与摧毁</h2>
<h3>build 4.80s / destroy 3.80s / static 1.00s</h3>
<p>13 个阶段是<b>数据</b>，写在 <code>buildings.STAGES</code> 里；每个构件带一个 stage 编号，
动画由阶段表统一编排。"脚手架什么时候出现""屋面什么时候盖"改一行表就变。</p>
<table>
<tr><th>阶段</th><th>归一化相位</th><th>实际时间</th><th>内容</th></tr>
{stage_rows}
</table>
<div class="note"><b>两条硬约束：</b>①时间轴节点的 translation 通道会<b>覆盖</b>节点枢轴位移，
每条动画都必须把 <code>{{node_id: pivot}}</code> 作为 rest_translation 传进 <code>add_animation</code>，
否则整栋会塌回世界原点。②每个阶段的下移量按<b>构件顶面高度</b>（bbox.max.y + 0.45）计算，
不能按自身厚度，否则高空构件会悬在半空等人。</div>
<p>摧毁是<b>压溃式塌落</b>：自下而上逐层失稳，每层落到地面并按 18%–32% 纵向压缩，
带倾角与偏航错位，落地回弹 6cm 后停住，最终形成约 3m 高的废墟堆。构件不会沉进地下 ——
那看起来像"拆积木"，而不是"被摧毁"。</p>
<p>为什么必须加<b>纵向压缩</b>：动画只能位移节点的 TRS，如果整组只做平移，
组内 11 米高的钟楼相对组底的高度不变，落地后仍然悬着。压缩是把"整组拍扁"，才是塌落。</p>

<h2>06 — 质检</h2>
<h3>量出来的，不是看出来的</h3>
<div class="grid3">
<div class="card"><b>BOXES</b><h4>{st_total:,} 个长方体</h4><p>单座 234–545 个，全部轴对齐，无曲面无斜面。</p></div>
<div class="card"><b>NODES</b><h4>{node_total} 个动画节点</h4><p>按 (阶段 × 材质) 分组，每座 16–32 个，便于逐层编排。</p></div>
<div class="card"><b>FLOAT</b><h4>零悬空</h4><p>屋面起始高度 = 墙顶高度；椽头、檐口、烟囱均由同一套坐标常量推导。</p></div>
<div class="card"><b>SIZE</b><h4>5.2 – 18.2 m</h4><p>统一米制，Godot 1 unit = 1 m，无需缩放。</p></div>
<div class="card"><b>DRAW</b><h4>9–12 材质 / 座</h4><p>按材质分 primitive，同阵营可合批；合批后仍可降到 1–2。</p></div>
<div class="card"><b>ASSETS</b><h4>48 张贴图 / 5.9 MB</h4><p>6 个 GLB 合计 2.5 MB，贴图跨模型共享。</p></div>
</div>

<h2>07 — 交付与接入</h2>
<h3>Godot 4.7 · 直接导入</h3>
<p>模型面朝 <b>−Z</b>（与 Godot 的 Node3D 前向一致），导入后无需补 180°。
<code>team_tint.gdshader</code> + <code>WarbandBuilding.gd</code> 提供一键换色与建造/摧毁状态机。
关键导入项：<b>Ensure Tangents 必须开</b>（否则法线贴图无效）、<b>*_N.png 勾选 Normal Map</b>、
<b>*_ORM.png 关闭 sRGB</b>。详见同级 <code>README.md</code>。</p>
<p class="mono" style="color:#7c8595">res://assets/warband/buildings/*.glb · textures/*.png · manifest.json</p>

<footer>
Ironbound Legion · Building Volume · v2.0<br>
几何 {st_total:,} 个轴对齐长方体 · 建筑 6 座 · 动画 18 条 · 材质 15 套 · 贴图 48 张<br>
生成管线：Python（numpy + Pillow）→ glTF 2.0 / GLB → three.js 预览 / Godot 4.7 运行时
</footer>
</div></body></html>"""

    out = os.path.join(OUT, "art-bible.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("bible ->", out, len(html), "bytes")


if __name__ == "__main__":
    main()
