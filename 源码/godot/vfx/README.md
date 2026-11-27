# 火效接入（pixelfx / 自发光 / Godot）

> 一句话结论：**pixelfx 能用，但它不是 shader，也不会"附在 GLB 里"**。
> 它是用代码生成 **2D 序列帧**的工具；要显示，必须在 Godot 侧挂一个节点去播它。
> 想让火跟着建筑一起导入、一起显示 —— 能做到；想让火**藏在 GLB 文件内部**自动播放 ——
> glTF 格式根本不支持动画材质，任何引擎都一样。

---

## 1. pixelfx 到底是什么

| | 实际是 | 不是 |
|---|---|---|
| 形态 | 一个 JS 库（`src/core` 是纯函数，299 个特效各是一个小文件） | 不是着色器、不是插件、不是运行时渲染器 |
| 输出 | 序列帧 PNG + Aseprite JSON（帧矩形 / 时长 / 轴心 / fps） | 不是 .glb / .gltf / 不是材质 |
| 依赖 | Node ≥ 18，浏览器 canvas 2D，无 npm 依赖 | 不需要 GPU 计算、不需要 Blender |
| 换色 | 每个特效吃一条 `palette`（暗→亮 6 档十六进制） | 不是给模型"染色"，是**换整套图** |

实测（本机 Node 22，仓库 `main` 分支）：

```
node tools/render.mjs fire/campfire --sheet
→ records/fire/campfire/campfire.png   1280×1152，90 帧，128×128/帧，30 fps
→ records/fire/campfire/campfire.json  meta.pixelfx = {fps:30, frames:90, columns:10, pivot:[64,112]}
```

仓库里 `src/fx/fire/` 正好有 `campfire` / `brazier` / `torch` 三个，跟我们四件火载体对得上；
另外还有 `fire-ring` / `spirit-flame` / `candle`，做魔法火或祭坛火可以直接拿。

---

## 2. 三条路线，选一条

| 路线 | 做法 | 得到什么 | 什么时候选 |
|---|---|---|---|
| **A · 自发光脉动**（默认，已落地） | 不改资源。给 GLB 里现有的火几何复制一份材质，让 `emission_energy` 按噪声呼吸 + 一盏闪烁点光 | 和低模硬边完全一致的火，零额外资源，一处火约 0.02 ms | 想保持现在这套审美 —— **先看这个** |
| **B · 序列帧贴片** | 藏掉火几何，挂一张 billboard Quad 播 pixelfx 图集 | 复古 RTS 那种"贴片火" | 整套美术走像素/复古路线 |
| **C · 贴图烤进图集** | 把某一帧的火焰图塞进 `图集/自发光.png`，用材质 UV 播 | 折中：有像素味但没逐帧动画 | 不推荐，投入产出比最差 |

**我的判断：走 A。** B 的问题不是技术，是风格 —— 128px 的像素火放进低模 3D 场景，
除非全场景（贴图 / UI / 单位）一起降像素密度，否则火会像"贴上去的贴纸"。
现在这套资产是"低模硬边 + 干净平涂"，火应该是**同样硬边的立体火舌 + 呼吸光**，
而不是一张会动的画。

---

## 3. 已落地的两个文件

```
godot/vfx/fire_fx.gd            挂到建筑根节点；默认 GEOMETRY 模式（路线 A）
godot/vfx/fire_flipbook.gdshader 路线 B 用；billboard + 图集取样 + 像素吸附
```

用法：

1. `fire_fx.gd` 拖到建筑根节点（`地牢` / `营火` / `酒馆内部` 都行）。
2. 默认参数即可：`pulse_speed 2.6`、`pulse_depth 0.35`、`light_energy 1.6`、`light_range 3.2`。
3. 一处火一盏灯会烧性能：`light_per_flame = false`（默认）只给最高的那处火配一盏。
4. 要贴片火：`mode = SPRITE`，`sheet` 指到 `vfx/fire/campfire.png`，
   `sheet_columns/frames/fps` 按 json 里的 `meta.pixelfx` 填。

**关键实现细节**（踩过的坑）：

- GLB 里 `team` / `team_trim` / `flame_*` 是**共享材质实例**，直接改会连累全场景同类建筑。
  脚本里一律 `duplicate()` 出独立副本再改 —— 和建模期"换阵营只改 team 材质"是同一条纪律。
- `flame` 节点名匹配用 `begins_with`，因为导出后会被加上 `.001` `.002` 后缀。
- 火不投阴影（`cast_shadow = OFF`），否则整座建筑脚下一团抖动的黑。

---

## 4. 生成别的特效 / 换色

```bash
# 一次拿整套火（3 个），带 GIF 预览
node tools/render.mjs fire --gif

# 蓝火：palette 是 暗→亮 6 档
node tools/render.mjs fire/brazier --sheet \
  --opts '{"palette":["#0b1020","#16224a","#2b4a8c","#5b8fd6","#a8d2ff","#f2fbff"]}'

# 精灵尺寸加倍（像素风小图放大时用 nearest，别用 bilinear）
node tools/render.mjs fire/torch --sheet --scale 2
```

换色只影响**生成期**；已经导出的图集要重新生成。
如果只是"同一套火，不同阵营染不同色"，别用 palette —— 在 Godot 里给 `tint` 传颜色就行
（`fire_flipbook.gdshader` 的 `tint` 参数，或 GEOMETRY 模式里改 `emission` 的色相）。

---

## 5. 边界（别踩）

- **GLB 里不能有动画材质。** glTF 2.0 的动画只覆盖节点 transform / morph / 骨骼；
  材质关键帧要走 `KHR_animation_pointer`，Godot 4 的 glTF 导入器不支持。
  所以"把火效和模型打成一个文件，导进去自己会动"做不到；标准做法就是**场景里挂节点**。
- **序列帧别进图集。** 90 帧 128² 塞进 2048² 图集只剩 16 帧的位置，而且会污染
  `主体.png` 的图集布局（那是按 5×8 材质格切的）。火图集单独一张 PNG 最省心。
- **导出尺寸按屏幕像素算。** 128px 图集在 1080p 里铺 1.2 m，实际屏幕高度约 40–60 px，
  分辨率绰绰有余；如果镜头能拉到很近，用 `--scale 2` 出 256px 版本。
