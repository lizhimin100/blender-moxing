# 单体建筑出图提示词 · v2（对齐体素资产包）

> 用途：为 `assets/warband/buildings/` 的六座建筑出**概念 / 展示图**。
> 前提：参考图（`参考图/`）只提供**风格与气氛**，几何必须服从本项目已有的体素语言。

---

## 0. 原提示词与本项目的 6 处硬冲突

先看结论，再看改法。原稿写得很好，但它是为"写实单体场景图"写的，直接套到本项目会产出**做不出来**的图。

| # | 原设定 | 与本项目的冲突 | 改法 |
|---|---|---|---|
| 1 | 中世纪奇幻**写实**、手绘纹理、**8k 电影级渲染** | 资产是**体素**：全部由轴对齐长方体堆叠，贴图 512²、共享一张 2048 图集。写实渲染的微观细节（瓦片破损、铆钉、木纹）在几何和贴图里都没有落点，硬写只会让出图和模型对不上 | 改成 **「体素写实」（voxel realism）**：方块语言 + 写实材质。细节靠**体块节奏**，不靠纹理堆砌 |
| 2 | 圆筒谷仓、锥形瓦顶、圆塔、圆形轮 | 项目硬约束：**禁止任何曲面**，所有"圆"必须由阶梯方块拼（八 / 十二边形） | 明确写"阶梯多边形近似"，并进负面词 |
| 3 | 统一 **蓝底金边**盾形纹章 | 阵营靠 TC1/TC2 遮罩换色。固定蓝金 = 换阵营时徽记不跟色，直接破坏复用 | 徽记改为**单色几何剪影**（狮鹫 / 锤砧 / 麦穗 / 眼 / 锯 / 塔），不指定底色 |
| 4 | 板甲士兵训练、骑士骑马、守卫站岗 | 本包**只含建筑**，单位是独立图层，混进去会让人误以为资产包含角色 | 用**靶人、盾架、兵器架、草垛**承担"军事感"，明确"无人物、无动物" |
| 5 | 赤陶红瓦 / 红色锥顶 | 现有材质只有**深灰板岩 + 茅草**，红色是阵营专用色，不能进固有色 | 统一板岩 / 茅草；红色只允许出现在旗与饰条上 |
| 6 | 大量微观磨损描述（苔藓、雨痕、抛光） | 512² 贴图在 RTS 缩放（建筑约 50–90 px 高）下看不见，反而变成**噪点** | 保留"脏、旧、有使用痕迹"的**大感觉**，删掉逐件描述 |

---

## 1. 统一规范 v2

### 1.1 相机（六张必须完全一致）

- 正交投影，无透视，**正等轴测**
- 水平 45°、垂直**俯角 38°**（比原稿的 35–40° 收窄到单一值，方便系列对齐）
- 出图 **1:1（2048×2048）**；如需横版另出一版 16:9，相机参数不变
- 建筑本体 + 附属场地占画面 **62–70%**，四角留白，**不裁切**
- 构图：主体中心略偏左下，让出右上天空 → 旗杆与塔尖不被压边

### 1.2 造型语言（最关键的一条）

> **一切形体由轴对齐长方体的堆叠构成；圆、斜、弧一律用阶梯方块近似；不出现真正的圆柱、球、锥、斜面。**

- 屋顶 = 阶梯叠瓦，每级向外挑出约 3 cm 形成瓦口
- "圆柱" = 阶梯八边形或十二边形（筒仓、烟囱、水桶、轮、锯片）
- "锥顶" = 3–7 级逐级收分的方形叠板
- 转角、接缝、梁柱交接靠**体块咬合**表现，不靠贴图
- 允许的细节上限：单个构件 ≳ 4 cm（小于这个尺寸在游戏里不可见）

### 1.3 色卡（直接对应 `matlib.py`，出图请往这上面靠）

| 部位 | 色值 | 说明 |
|---|---|---|
| 石（亮） | `#8D949B` | 毛面花岗岩，灰中带暖 |
| 石（暗） | `#4B5057` | 勒脚、压顶、台阶侧 |
| 灰泥 | `#CEC3AE` | 半木结构的填充墙 |
| 木（亮） | `#6A4A33` | 梁、柱、板 |
| 木（暗） | `#4B3627` | 桁架、栏杆、箍 |
| 板岩 | `#5F5446` | 屋面主材 |
| 茅草 | `#A98A52` | 农场谷仓 |
| 铁 | `#9AA0A0` / 暗 `#5F666B` | 做旧发黑，边缘微亮 |
| 金 | `#C8A02C` | 只用于钟楼顶、旗杆球头、徽记 |
| 炉火 | `#FF8A2B` | 唯一允许的强饱和暖色 |
| 窗光 | `#8FE6FF` | 冷色点光，与炉火形成冷暖对 |
| 阵营主色 | `#B8352C`（示例） | **可变**，不写死 |
| 阵营副色 | `#FFE08A`（示例） | 徽记 / 描边 |

整体调性：**暖灰 + 深棕 + 低饱和**，饱和度中偏低。不允许出现大红大绿之外的纯色块。

### 1.4 光照

- 主光：左上方 45°，5500K 暖白，强度柔和
- 阴影：软边、统一投向右下；建筑底部与构件缝隙 **AO 明显**（这是体素模型唯一的体积线索）
- 补光：右侧冷色弱补光，只提暗部，不产生第二组阴影
- 禁止：轮廓光、体积雾、镜头光晕、HDR 过曝

### 1.5 阵营色（决定"能不能复用"）

**只染结构线，不染墙。** 具体位置（每座至少 6 处，覆盖低 / 中 / 高三个高度带）：

- 低：门楣横匾、台阶两侧矮墙压顶、门框内嵌条、盾面、围栏大门
- 中：腰线饰条、女儿墙 / 垛口压顶、柱箍、栏板、布篷、筒仓铁箍
- 高：封檐板、脊瓦、烟囱箍、旗、垂幅

硬指标：
- 可见表面染色占比 **6–9%**
- 同一面墙上**不同时**出现"阵营色条 + 固有色条"交替（会糊成噪点）
- 徽记尺寸 = 旗宽的 **0.45**，位于旗面**上 1/3**，不居中
- 徽记必须能被**单色替换**：几何剪影 + 平涂，不要渐变、不要描边发光

### 1.6 环境（压到最低）

- 地面：短草 + 压实土路 + 少量浅灰砾石；土路从画面左下进入
- 植被：外围**仅 3–6 棵**深绿云杉，压暗、降饱和，**不得遮挡建筑轮廓**
- 道具：只放该建筑的功能道具，占地不超过建筑投影的 **1.2 倍**
- 禁止：成片森林、河流、远山、其他建筑、任何人物与动物

### 1.7 出图规格

2048²、单主体、无拼贴、无文字标注。**不要 8k** —— 出图分辨率提高不会让几何更清楚，只会让模型往写实细节上跑偏。

---

## 2. 公共前缀 + 负面词（逐座复用，不要改）

### 2.1 公共前缀

```
orthographic projection, isometric view, 45 degree azimuth, 38 degree pitch,
voxel realism, architecture built entirely from axis-aligned rectangular blocks,
stair-stepped approximation for every curved form, no true cylinders or cones,
medieval fantasy RTS building asset, single building centered, 62-70% of frame,
temperate grass ground with packed dirt path, sparse dark spruce at the edges only,
soft morning daylight from upper left, clear gentle contrast, soft shadow to lower right, strong ambient occlusion, no murky fog,
desaturated warm-grey and dark-brown palette, 512px hand-painted material feel,
team color only on structural trims and banners, 6-9% coverage,
shield emblem as a flat single-color geometric silhouette, high detail, clean edges
```

中文对照（写给不看英文的协作方，实际投喂用英文更稳）：

> 正交投影，等轴测，45° 方位角，38° 俯角；体素写实，全部由轴对齐长方体构成，任何曲面用阶梯方块近似，不出现真圆柱与锥体；中世纪奇幻 RTS 单体建筑，主体居中占 62–70%；温带草地 + 压实土路，外围仅少量深色云杉；左上柔和晨光，阴影朝右下，强 AO；低饱和暖灰 + 深棕；512 手绘材质感；阵营色只在结构饰条与旗帜上，覆盖 6–9%；盾形徽记为平涂单色几何剪影。

### 2.2 负面词

```
perspective distortion, fisheye, curved surfaces, true cylinders, spheres, cones,
realistic photo, photorealistic render, oil painting, watercolor, anime, chibi, cel shading,
characters, people, soldiers, horses, animals, crowds,
bright saturated colors, neon, glossy plastic, chrome, lens flare, volumetric fog,
dense forest, mountains, river, multiple buildings, cluttered props,
text, watermark, logo, UI, border, frame, signature,
moss everywhere, rust everywhere, broken roof holes, floating objects, intersecting geometry
```

---

## 3. 六座逐座提示词

每座先给**剪影判据**（一条能在 64 px 缩略下验证的规则），再给完整提示词。
六座的屋顶类型**互不重复**，这是"一眼区分"的第一手段。

---

### 3.1 城镇大厅 Town Hall · 17.52 m

**剪影判据**：全系列最高的**双坡 + 交叉山墙**，屋脊正中一座四柱钟楼、顶上一颗金球。

**功能符号**：门廊 + 五级石阶 + 公告板 + 两侧火盆 → "行政 / 集会"

```
[公共前缀]，
town hall, two storeys, ashlar stone base with cream plaster upper walls and dark oak half-timbering,
steep dark slate gable roof with a crossing gable on the front facade,
square open bell tower on the ridge, four oak posts, stepped pyramidal cap, small gold finial,
projecting entrance porch with five stone steps, two iron braziers flanking the steps,
long banner hanging on each side of the porch, wooden notice board with three pinned sheets,
team-colored fascia board running along the eaves, team-colored band at the second-floor string course,
lead-downpipes at the four corners, tall narrow windows with warm interior light,
oak doors with iron hinges
```

---

### 3.2 兵营 Barracks · 12.63 m

**剪影判据**：**平顶 + 锯齿垛口**一圈，前右一座 10.5 m 主角楼、后两角 9.4 m 副角楼 —— 全系列唯一没有坡屋顶的建筑。

**功能符号**：垛口 + 闸门槽 + 训练场（靶人 / 盾架 / 兵器架）

```
[公共前缀]，
fortress barracks, ashlar stone base with cream plaster upper walls and dark oak half-timbering,
flat roof, crenellated parapet with 28 merlons around the perimeter,
each merlon capped with a team-colored coping stone,
one tall corner tower at the front right, 10.5 m, stepped octagonal shaft, four arrow slits, stepped pyramidal cap and banner pole,
two shorter corner towers at the rear, 9.4 m, no banner,
main gate with three stone steps, portcullis slot, lintel plaque and two banner poles with swallow-tailed vertical banners,
lean-to annex on the east side with its own chimney, external timber stair on the west wall,
L-shaped timber palisade enclosing a packed-earth training yard,
three pell dummies with straw heads and painted targets, a rack of three kite shields,
two weapon racks with spears and broadswords, two iron braziers, two straw stacks
```

---

### 3.3 铁匠铺 Blacksmith · 13.98 m

**剪影判据**：**低矮单坡**屋顶 + 一根远超屋脊的**方形烟囱**（全系列最高点 13.6 m）。

**功能符号**：外凸炉膛的橙光 + 铁砧 + 淬火桶

```
[公共前缀]，
blacksmith forge, single-pitch slate roof with a low eave, low stone base and dark oak frame,
projecting stone furnace block on the front facade, opening glowing ember orange from inside,
heavy iron lintel above the furnace mouth, stone jambs on both sides,
tall square stone chimney rising far above the ridge, 13.6 m, three team-colored iron hoops, sheet-metal cap,
lean-to timber store on the east side, cloth awning over the work area,
three anvils on timber stumps, a quench barrel with stepped-octagonal staves and two hoops,
a grindstone on a wooden frame, a coal heap, a tool wall with hammers tongs files chisels,
warm orange firelight contrasting with cool daylight, soot-stained stone near the furnace
```

---

### 3.4 农场 Farmstead · 9.57 m

**剪影判据**：一座**圆筒状阶梯塔**（筒仓，9.5 m）紧邻**陡坡**谷仓 —— 全系列唯一有"塔 + 陡坡"组合的体量。

**功能符号**：筒仓 + 田垄 + 稻草人 + 水槽

```
[公共前缀]，
farmstead, steep thatched gable barn with a stone base, dark oak frame and plank doors,
a tall stepped-dodecagonal stone silo, 9.5 m, seven-step conical cap, ventilation cap,
three team-colored iron hoops around the silo, external ladder with a safety cage,
L-shaped timber and stone fence with a double-leaf gate,
three round straw stacks, a stone water trough with a windlass, a two-wheel hand cart with a team-colored canopy,
a scarecrow with a straw head and a team-colored belt,
three cultivated strips in front right: wheat, cabbages and pumpkins in rows,
a small cow shed attached to the west wall
```

---

### 3.5 哨塔 Watchtower · 18.20 m

**剪影判据**：全系列最**细高**，塔身笔直，顶部一圈**外扩方冠**（双层出檐），冠上立旗。

**功能符号**：观景廊栏板 + 火盆 + 箭袋

```
[公共前缀]，
watchtower, tall and slender, stone base with an arched doorway, dark oak tower shaft,
a viewing gallery near the top with three sides of team-colored parapet panels,
a square double-eave crown above the gallery, stepped stone cornice,
banner pole on the crown with a long triangular pennant,
three swallow-tailed vertical banners hanging on the shaft,
an iron brazier burning on the gallery, four quivers hanging on the parapet inner side,
two water buckets, a winch at the base, a small guard shed and a firewood stack beside the base,
low timber fence around the foot
```

---

### 3.6 伐木场 Lumbermill · 8.54 m

**剪影判据**：一座**门形龙门吊**（8.6 m 双柱 + 横梁）跨在低矮敞棚前 —— 全系列唯一的"框架式"剪影。

**功能符号**：龙门吊 + 立式锯片 + 原木堆端面年轮

```
[公共前缀]，
lumber mill, open-sided timber shed with a low pitched slate roof on six oak posts,
a tall timber gantry crane in front, two posts 8.6 m with a cross beam, pulley block, rope and hook,
a sawing platform under the eaves, 3.2 m wide, with a large stepped-octagonal circular saw blade and 24 teeth,
a pyramid stack of logs, 4-3-2-1, stepped-octagonal ends showing growth rings, two team-colored binding ropes,
a team-colored board across the front of the saw platform,
sawdust piles and scattered offcuts, a timber drying rack on the west, a tool shed on the east,
a small sawdust burner tower behind the shed
```

---

## 4. 三原则如何落地

### 4.1 能区分建筑

| 手段 | 做法 | 验收 |
|---|---|---|
| 屋顶类型唯一 | 平顶垛口 / 双坡交叉山墙 / 单坡+高烟囱 / 陡坡+筒仓 / 方冠塔 / 门形吊架 | 六座两两不同，写成一句话能说清 |
| 高宽比分层 | 17.5 / 12.6 / 14.0 / 9.6 / 18.2 / 8.5 m | 相邻两座高差 ≥ 1.5 m |
| 剪影留缺口 | 塔、烟囱、吊架、旗杆形成"凸起" | 128 px 缩略下轮廓 IoU < 40% |

### 4.2 突出职责

每座必须有一个**主功能道具**出现在画面中央 1/3 区域，且体量 ≥ 主体的 1/6：

- 兵营 → 训练场（靶人组）
- 铁匠铺 → 炉口橙光
- 农场 → 筒仓
- 哨塔 → 观景廊
- 伐木场 → 锯台
- 大厅 → 门廊台阶

出图时如果这个道具被挡住或被环境吃掉，**直接重出**，不要靠后期调。

### 4.3 不同阵营复用

出图阶段就要保证"换色即可换阵营"：

1. 主体材质（石 / 木 / 板岩 / 茅草）**不含**阵营色
2. 阵营色只出现在 1.5 节列的结构线位置
3. 徽记是**单色平涂剪影**，不含渐变与描边
4. 旗帜、垂幅、布篷用**同一形制**，只改颜色
5. 出图时给一版"血红"、一版"钴蓝"对照，验证换色后仍成立

---

## 5. 生成流程建议

1. **先出兵营**。它的平顶垛口剪影最特殊，定调最稳；定下来之后再批量出其余五座。
2. **固定 seed**，只改"建筑主体"那一段，公共前缀与负面词完全冻结。
3. 参考图作为 **style reference，权重 0.35–0.45**。权重过高会把参考图的写实曲面（圆筒仓、圆锥顶、人物）带进来。
4. 每座出 **3 张**，挑"剪影最清楚、功能道具没被挡"的那张，而不是挑最漂亮的那张。
5. 出完先做三件事：缩到 128 px 看能不能认出是哪座；转成灰度看体块是否成立；把阵营色 P 成蓝色看会不会崩。
6. **不要用出图去反推模型**。图是风格锚点，几何以 `buildings.py` 为准。

---

## 6. 与现有模型的对应关系

| 建筑 | 模型高度 | 模型的独特构件（出图必须出现） |
|---|---|---|
| 城镇大厅 | 17.52 m | 四柱钟楼 + 金球、交叉山墙、五级石阶、公告板 |
| 兵营 | 12.63 m | 28 垛口、前右主角楼、外挂楼梯、三靶人、盾架 |
| 铁匠铺 | 13.98 m | 外凸炉膛 + 13.6 m 方烟囱、东侧披屋、三铁砧 |
| 农场 | 9.57 m | 阶梯十二边形筒仓 + 爬梯护笼、三条田垄、稻草人 |
| 哨塔 | 18.20 m | 观景廊三面栏板、双层方冠、三垂旗 + 顶旗 |
| 伐木场 | 8.54 m | 8.6 m 龙门吊、φ1.2 锯齿、4-3-2-1 原木堆 |

---

*本规范与 `docs/art-bible.html`、`assets/warband/manifest.json` 同源；高度与构件数改动后需同步。*
---

## 7. 首轮出图实测（兵营，用于校准后续五座）

用本规范的兵营提示词实出两版，对比见 `docs/prompt-test/`。

| 版本 | 结果 | 结论 |
|---|---|---|
| v1 | 整座纯石砌，少了灰泥与半木结构；画面偏灰闷 | 只写"stone base"会让模型吃掉上部墙体。**材质必须按"基座 / 上部 / 骨架"三层分别写** |
| v2 | 基座石砌 + 上部灰泥 + 深色木构，平顶垛口、三塔、营门、L 形木栅、外挂楼梯、东侧披屋全部出现 | 可作为兵营的风格锚点 |

**已验证成立的部分**

- 平顶 + 锯齿垛口 + 三塔的剪影，与其余五座不会混
- 阵营色只落在垛口压顶、门楣、旗面，占比目测在 6–8%
- 训练场道具（靶人、盾架、兵器架、草垛）位置正确，没有抢主体
- 无人物、无曲面、无透视畸变

**需要二次修正的三点（下一轮直接改这几处）**

1. **相机俯角偏陡**：模型给到了约 50°，比要求的 38° 更俯。改法是在前缀里把角度写死为 `camera pitch 38 degrees, low enough to see the front facade clearly`，并删掉可能被理解成"俯视"的词。
2. **画面偏灰闷**：`no murky fog` 没有完全生效。改为正向描述 `clean mid-tones, bright grass, clear sky`，负面词再加 `haze, dust in the air, low contrast`。
3. **靶人被画成"盾牌立架"**：`pell dummies with straw heads` 被简化了。改法是把结构写全：`wooden stake with a crossbar, straw bundle head, burlap torso, painted target disc on the chest`。

**流程结论**：先出兵营定调 → 用同一 seed 批量出其余五座 → 每座只改"建筑主体"段。一轮 2 张即可收敛，不需要反复抽卡。
