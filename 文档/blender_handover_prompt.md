# Blender 精修交接工单 v4

> 接手对象：能在 Blender 里用 Python（bpy）脚本化作业的工程型 Agent。
> 工作目录：`D:/测试一`。本工单自包含，不需要上一轮对话。
> 目标读者是"另一个 Agent"，可直接整段作为提示词投喂。

---

## 0. 角色与边界

你是这个项目的 **技术美术 / 管线工程师**，不是概念设计师。

风格已经拍板：**体素写实（voxel realism）**——一切形体由长方体构成，圆用阶梯近似，
细节靠体块咬合与边缘处理，不靠细碎贴图。本轮不做风格探索。

你的任务：**把现有的程序化资产迁移成可长期手工维护的 Blender 工程，并在保持可测指标的前提下提升细节。**

评判标准不是"看起来更精细"，而是第 8 节的验收脚本仍能跑通。

---

## 1. 现状（动手前先读完，并跑一遍第 8 节的脚本）

### 1.1 资产

```
assets/warband/buildings/*.glb      6 座，每座：1 材质 / 1 primitive / 1 蒙皮网格
assets/warband/textures/           15 套 512² PBR + 4 张 2048² 共享图集
assets/warband/manifest.json       高度 / 构件数 / 块数 / 材质数 / draw call / 阶段时间轴 / roof
assets/warband/team_tint.gdshader  阵营染色 + 顶点 AO + 图集 UV
```

六座与关键尺寸（**不得改动**，它们编码了"一眼区分"）：

| id | 中文 | 高度 | 屋顶类型 | 剪影判据 |
|---|---|---|---|---|
| townhall | 城镇大厅 | 17.52 m | gable_cross | 双坡 + 交叉山墙 + 四柱钟楼 + 金球 |
| barracks | 兵营 | 12.63 m | flat_crenel | 平顶锯齿垛口 + 3 座角楼（唯一无坡顶） |
| blacksmith | 铁匠铺 | 13.98 m | mono_pitch | 低矮单坡 + 一根 13.6 m 方烟囱 |
| farm | 农场 | 9.57 m | gable_steep | 陡坡谷仓 + 9.5 m 阶梯十二边形筒仓 |
| watchtower | 哨塔 | 18.20 m | crown_eave | 全系列最细高 + 顶部外扩方冠 |
| lumbermill | 伐木场 | 8.54 m | open_shed | 门形龙门吊跨在敞棚前 |

### 1.2 坐标系

- 1 unit = 1 m，米制，无缩放
- 模型面朝 **−Z**（Godot `Node3D` 前向），导入后不补 180°
- 原点是占地中心，y = 0 是地面
- Blender 侧用 **+Y up、−Z forward** 的导出设置，否则进 Godot 会躺倒

### 1.3 现行管线

```
build/matlib.py      15 套程序化 PBR 贴图（512²）
build/buildings.py   六座的构件表（每个构件 = 轴对齐 box + 材质 + 施工阶段）
build/weld.py        结构焊接（把 ≤40 cm 的缝补成实体接触）
build/dedup_faces.py 面剔除 + 共面消解 + 收边
build/ao.py          顶点 AO 烘焙 + 每盒色彩扰动
build/chunks.py      2.4 m 网格切块（每座 87–112 块）
build/atlas.py       15 材质 → 4 张 2048² 图集
build/gltf.py        手写 glTF 2.0 导出器
```

命令：

```bash
PY="C:/Users/箭竹/.workbuddy/binaries/python/envs/wb_build/Scripts/python.exe"
$PY build/build_buildings.py   # 重建六座
$PY build/make_manifest.py
$PY build/check_floating.py && $PY build/check_assets.py
$PY build/check_teamcolor.py && $PY build/check_uv.py
```

---

## 2. "源"的规则（**最容易翻车的一条**）

长期维护要人接手，所以本轮起 **`.blend` 就是资产源**，`buildings.py` 降级为"体块生成器"，
只用于初始化或大改轮廓。

规则：

1. 首次迁移：`GLB → Blender`，保留体块、层级、材质槽、动画，**不做任何尺寸修改**。
2. 之后所有人工作业都在 `.blend` 里做。
3. 要改结构（加房间、改体量）→ 回 `buildings.py` 改，重新生成，再 merge 进 `.blend`；
   或者手工在 `.blend` 里改，但必须同步更新 `buildings.py` 的构件表，否则下次重建会覆盖。
   **两边必须有一次明确的取舍，不能长期双写而不对齐。**
4. 每次交付都要跑第 8 节脚本。**脚本是契约，不是建议。**

---

## 3. 必须先把这条规范冲突解决掉

现行验收第 14 条：*所有三角形法线只有 6 个方向*。

**这条与"加倒角"直接冲突**——倒角会造出 45° 面。二选一：

- **A（推荐）保留方块语言，用贴图伪造边缘**：不倒角，靠法线贴图 + AO 做边缘高光。验收不变。
- **B 允许倒角，替换判定**：允许 **1–2 mm 的 45° 倒角**，禁止圆角（bevel 段数 > 2）、禁止曲面。

选 B 的话，把第 14 条替换成这条可测规则：

> 所有三角形法线方向数 **≤ 26**（6 主向 + 12 棱倒角 + 8 顶点倒角），
> 且 ±X/±Y/±Z 六个主向仍占**面数 ≥ 85%**。

并在 `docs/` 里写清"为什么放宽、放宽到哪、怎么测"。
**不要默默放宽，也不要默默不满足。**

---

## 4. 硬约束

### 4.1 不可协商

1. **只有长方体 + 可选 1–2 mm 倒角**。禁止曲面、禁止真圆柱/球/锥、禁止斜面屋顶。
   "圆"必须是阶梯八边形或十二边形。
2. **结构必须连通到地面**：`check_floating.py` 输出 0 悬空块。
3. **三段动画的名字与语义不变**：`build` 4.80 s / `destroy` 3.80 s / `static` 1.00 s，均 `LOOP_NONE`。
4. **销毁不得用 `scale.y` 压扁**；chunk 级自由落体 + 3 次回弹 + 末帧废墟 ≥ 2.0 m。
5. **每座导出后仍是 1 个材质、1 个 primitive、1 个蒙皮网格**，draw call ≤ 2（含阴影）。
6. **节点数 ≤ 140 / 座**（含 armature 与骨骼）。这条决定了不能用"每块一个物体"的做法。
7. **单位与朝向**：1 unit = 1 m，面朝 −Z，原点在占地中心，y=0 地面。
8. **不新增人物、动物、载具**。本包只含建筑。

### 4.2 贴图

- 分辨率**不得提升**到 1024 以上（用户已明确：与分辨率无关，只会让包体翻倍）
- 通道约定不能变：
  - `*_BC.png` BaseColor（sRGB）
  - `*_N.png` Normal（+Y，线性）
  - `*_ORM.png` R:AO / G:Roughness / B:Metallic / **A:TC1 主色遮罩**（线性）
  - `*_E.png` 自发光 / TC2（仅 emblem / ember / window）
- 色卡（贴图均值必须落在这些值 ±1 色阶内）：

| 材质 | 值 | 材质 | 值 |
|---|---|---|---|
| stone | `#8D949B` | shingle | `#5F5446` |
| stone_dark | `#4B5057` | thatch | `#A98A52` |
| plaster | `#CEC3AE` | steel | `#9AA0A0` |
| wood | `#6A4A33` | steel_dark | `#5F666B` |
| wood_dark | `#4B3627` | gold | `#C8A02C` |

自发光：`ember #FF8A2B`（暖）/ `window #8FE6FF`（冷）。这两个是全包唯一允许的强饱和色。

### 4.3 阵营色

- 可见表面染色占比 **6–9%**，低（0–30%）/ 中（30–65%）/ 高（65–100%）三个高度带都要有
- 只染结构线：檐口、腰线、垛口压顶、柱箍、栏板、门楣、箍带、旗、垂幅、布篷
- **不染整墙**，不出现"阵营色条与固有色条交替"
- 徽记为**单色平涂几何剪影**（狮鹫 / 锤砧 / 麦穗 / 眼 / 锯 / 塔），尺寸 = 旗宽 0.45，位于旗面上 1/3

---

## 5. Blender 里的具体做法

### 5.1 导入

```
bpy.ops.import_scene.gltf(filepath="assets/warband/buildings/townhall.glb")
```

导入后应得到：1 个 `Armature`（137 根骨）+ 1 个 `Skinned Mesh` + 3 个 Action。
**先核对**：顶点数、三角面数、骨骼数、UV 层数（应有 2 层）、颜色属性（应有 1 个 `Color`）。

### 5.2 层级与命名（必须沿用，脚本依赖）

```
Armature
└─ stage_00 … stage_12        13 段施工阶段（骨骼）
   └─ chunk_XX_YYY            87–112 块（骨骼，摧毁动画只动这一层）
```

- 骨骼名、网格名、材质名**不要改**。`check_assets.py` 按名字统计节点与阶段。
- 新增细节几何：**并入同一个 mesh**，顶点权重绑到对应 chunk 骨骼上，不要新建物体
  （新建物体 = 新节点，直接顶破 140 的预算）。

### 5.3 材质

Blender 里可以搭任意节点，但**导出前必须塌成 1 个材质**：

- 采样 UV：第 2 层（图集 UV，导出为 `TEXCOORD_1`）
- 阵营染色：`ORM.a` → mix(base, team_color × luminance)
- 顶点 AO：`Color` 属性 → 乘到 BaseColor
- 粗糙度/金属度：`ORM.G` / `ORM.B`
- 自发光：`E × TC2`

参考实现见 `assets/warband/team_tint.gdshader`，逻辑必须逐条对齐，
**不要"看起来差不多"**——Godot 侧用的就是那份 GLSL。

### 5.4 UV（最容易丢的一步）

- 两层 UV 必须都保留：第 1 层世界平铺（回退用），第 2 层图集
- Blender 导出时，`TEXCOORD_0` 取 **Render 标记**的 UV，`TEXCOORD_1` 取下一层
- 图集打包规则：4×4 格、每格 512（504 美术区 + 4 px 边缘复制）、留 4 px padding
- 新增材质时**禁用**图集里的空格子（3,3 是空的，落进去会采样到黑）

### 5.5 动画

- 三条 clip 分别用三个 Action，放进 **NLA 轨道**（每轨一个 Action、静音、stash），
  导出时勾选 "Group by NLA Track"，否则会被合并成一条
- `destroy` 的保持段用 **CONSTANT** 插值，别用 BEZIER（会滑步）
- Blender 的物体原点天然就是枢轴，**这是相对现有管线最大的好处**——
  不用再处理 glTF `translation` 是绝对值、会覆盖枢轴的问题

### 5.6 导出

```
bpy.ops.export_scene.gltf(
    export_format='GLB',
    export_yup=True,                 # +Y up
    export_apply=True,               # 应用修改器（但不要应用 Armature）
    export_animations=True,
    export_nla_strips=True,
    export_skins=True,
    export_texcoords=True,
    export_colors=True,              # COLOR_0
    export_cameras=False,
    export_lights=False,
    export_extras=True,              # 自定义属性（阶段表等）
    export_optimize_animation_size=False,
)
```

导出后**立刻**跑一遍第 8 节脚本，不要攒到最后。

---

## 6. 本轮要做的细节（P 级）

按投入产出排序，前两项必须做。

### P0-1 边缘处理

- 按第 3 节的 A/B 方案执行
- 若选 B：倒角宽度 **1–2 mm**，段数 2，角度阈值 30°；只对**轮廓相关边**生效，
  内部看不见的接缝不倒角（控制面数）
- 加 weighted normal，避免倒角后出现"肥皂感"

### P0-2 接触 AO

- 现在用的是逐盒顶点 AO（`ao.py`，强度 0.34），缝里偏粗
- 在 Blender 里烘一张 **AO 贴图**（Cycles，512²，per-material 或并入图集），
  替换/叠乘 `ORM.R`
- 验收：墙与地、檐与墙、梁与柱的接缝在 128 px 缩略下仍能看出暗部

### P1 手工细节（这是"长期接手"的价值所在）

- 木构：梁头出挑、榫接处的短木、板缝错位
- 石作：转角石（quoins）交错、勒脚外放
- 铁件：门铰、合页、铆钉（≤4 cm，注意 RTS 缩放看不见，别过度）
- 屋面：瓦口挑出、脊瓦、局部缺瓦（每座 2–3 处，不要成片）

### P2 破坏态

- 瓦砾堆补 2–3 处大块残墙，末帧废墟高度仍 ≥ 2.0 m
- 扬尘方块保留（`dust_XX` 骨骼），不要删

---

## 7. 禁止事项

1. 不要重新建模。以现有 GLB 为体块基础，只加细节。
2. 不要改高度、屋顶类型、占地尺寸——它们编码了建筑身份。
3. 不要用"每块一个物体"的做法（节点预算瞬间破）。
4. 不要提升贴图分辨率。
5. 不要引入曲面几何。
6. 不要把阵营色刷到整面墙上。
7. 不要在 Blender 里用 `Apply → Armature`（会毁掉骨骼绑定）。
8. 不要跳过第 8 节的脚本直接交付。
9. 不要默默放宽验收标准；要改就改脚本 + 写进 CHANGELOG。

---

## 8. 验收（脚本即契约）

```bash
PY="C:/Users/箭竹/.workbuddy/binaries/python/envs/wb_build/Scripts/python.exe"
$PY build/check_floating.py    # 悬空连通块 = 0
$PY build/check_assets.py      # 节点≤140 / 1 材质 / 3 clip / 高度 / 体量 / 屋顶类型唯一 / 废墟≥2.0
$PY build/check_teamcolor.py   # 6 座都在 6–9%，三档高度都有
$PY build/check_uv.py          # 每个面的图集 UV 落在自己的格子里（当前 0 异常）
$PY build/check_visual.py      # 轮廓 IoU < 40%；共面 ≤0.3 mm 判定
```

| # | 项目 | 阈值 |
|---|---|---|
| 1 | 结构连通 | 0 悬空块 |
| 2 | 节点预算 | ≤ 140 / 座 |
| 3 | 材质 | 1 个 / 座，draw call ≤ 2 |
| 4 | 三 clip | 4.80 / 3.80 / 1.00 s，LOOP_NONE |
| 5 | 无压扁摧毁 | `destroy` 里无 `scale.y < 0.85` |
| 6 | 废墟厚度 | 末帧 ≥ 2.0 m |
| 7 | 阵营色 | 6–9%，三档高度齐全 |
| 8 | 屋顶类型 | 六座两两不同 |
| 9 | UV | 0 个异常顶点 |
| 10 | 单位朝向 | 1 unit = 1 m，面朝 −Z |

---

## 9. 交付物

```
blend/<id>.blend                 6 个工程文件（集合按 stage 命名，无游离物体、无孤立数据）
assets/warband/buildings/*.glb   6 个，更新后
assets/warband/textures/*.png    新增/修改
assets/warband/manifest.json     高度 / 节点 / 三角形 / 材质 / draw call 同步
assets/warband/team_tint.gdshader 若材质逻辑有变，同步改
CHANGELOG.md                     按 P0–P2 分组，每项写"改了什么/为什么/实测值"
```

---

## 10. 已知坑（省你半天）

1. **glTF `translation` 是绝对值**，会覆盖枢轴。Blender 里不成问题，但**回写脚本**时要注意。
2. **PIL 缩放 RGBA 会清空 alpha=0 的 RGB**。ORM 的 A 是 TC1 遮罩、绝大多数为 0，
   必须 RGB 与 A 分开缩放，否则整张 ORM 变黑。
3. **共面剔除**有两个坑：两块完全相同的面会互相"完全覆盖"导致都删掉；
   "面中心被盒子覆盖"不能用来剔除整面（一根箍带会误杀整面墙）。只删"整面完全被覆盖"。
4. **图集 UV 落在空格子（3,3）**会采样到黑，表现为莫名其妙的黑块。
5. 预览台 `yaw=214` 才是正面（−Z 朝向镜头）。
6. 本地预览必须走 HTTP，`file://` 会被 CORS 拦掉 GLB。

---

## 11. 建议的推进顺序

1. **先只迁移一座**（建议城镇大厅，构件最多、最考验管线）。
   跑通"导入 → 加倒角 → 导出 → 五项脚本全绿"，再铺开。
2. 第二座选**兵营**（唯一的平顶，最能暴露"倒角后剪影糊掉"的问题）。
3. 剩下四座批量。
4. 最后统一做接触 AO 与手工细节，避免每座重复调参。

每完成一座，跑一次脚本 + 出一张同角度截图（相机：正交，45° 方位，38° 俯角）。
