# 建造动画 · Godot 4 接入手册

> **给 agent 的用法**：这份是可照着执行的操作手册，按 §1 → §6 顺序做，§7 用三张图验收，§8 是踩过的坑。
> 需要拷进工程的只有 **4 个文件**，不需要改任何 GLB。
>
> 前置认知：建造表现 = **GLB 里的套件动画**（脚手架逐层立、场件顶出、拆架清场）
> ＋ **引擎里一条高度遮罩**（建筑本体按世界高度被剖开）。两半必须同时在，缺一半就退回
> "整体缩放"或"完整建筑凭空出现"。

---

## 0. 一分钟版

```text
拷 4 个文件 → 拖 GLB 进工程（导入设置不用动）→ 建一个 Node3D，把 GLB 实例挂上去
→ 把 build_reveal.gd 挂在 Node3D 上 → building_name 填建筑名 → 运行
```

建筑本体在 GLB 里是**原始尺寸、零骨骼、零动画**；它会"长大"完全靠 `build_reveal.gdshader`
每帧丢弃高度超过 `reveal_height` 的片元。

---

## 1. 拷文件

| 从仓库 | 到 Godot 工程 | 作用 |
|---|---|---|
| `godot/build_reveal.gdshader` | `res://godot/build_reveal.gdshader` | 高度遮罩（核心） |
| `godot/build_reveal.gd` | `res://godot/build_reveal.gd` | 驱动器：动画时间 → 遮罩高度 |
| `godot/build_reveal_data.gd` | `res://godot/build_reveal_data.gd` | 九座的 `z0/z1/t0/t1` 常量表 |
| `assets/<建筑>/<建筑>_建造.glb` | `res://assets/<建筑>/<建筑>_建造.glb` | 建造期资产 |

> `build_reveal_data.gd` 是 `.gd` 常量表而不是 `.json`，**故意**的：Godot 导出预设默认
> 不打包 `*.json`，忘了加 "Filters to export non-resource files" 就会在发行版里读不到参数。
> 需要改数值请改 `build_reveal_data.gd`，或改源表后跑 `python build/mk_godot_data.py` 重新生成。

---

## 2. 导入 GLB

1. 把 `<建筑>_建造.glb` 拖进 FileSystem 面板（放到 `res://assets/<建筑>/`）。
2. 选中它，看 Import 面板：**只确认 `Animation > Import` 是勾上的**（默认就是勾上的），
   其余全部保持默认，点 **Reimport**。
3. 双击打开场景，节点结构应该是：

```
<建筑>_建造 (Node3D)          ← 场景根
├─ Building (MeshInstance3D)             4 个 surface：team / team_trim / 主体 / 自发光
├─ Skeleton3D                            16 根骨，全部属于工地套件
├─ SiteKit (MeshInstance3D)              8 个 surface：6 个工地色 + team / team_trim
└─ AnimationPlayer                       1 条动画：build
```

- 单位：1 unit = 1 m，模型原点在**占地中心的地面上**，Y 是高度。Godot 和 glTF 都是 Y-up，
  所以**不需要任何旋转**，导入就是站着的。
- `Building` **没有**骨骼、没有动画轨道 —— 这是刻意的，见 §8-③。

---

## 3. 搭场景

```
ConstructionSite (Node3D)      ← 挂 build_reveal.gd，building_name 填「铁匠铺」
└─ 铁匠铺_建造 (实例化的 glTF 场景)
```

做法：新建 Node3D → 把 `铁匠铺_建造.glb` 从 FileSystem 拖到它下面（选"Instantiate Child Scene"）
→ 选中 `ConstructionSite` → 挂 `build_reveal.gd` → Inspector 里 `building_name` 填 `铁匠铺`。

脚本是**向下找节点**的（`find_child("Building")` / `find_child("AnimationPlayer")`），
所以挂在这一层或更上层都行，甚至可以直接挂在 glTF 实例根节点上。

---

## 4. 运行

`auto_play` 默认 `true`，`_ready` 里自动 `play("build")`，你会看到：

| 时间 | 画面 |
|---|---|
| 0.00–0.46 s | 放线框、桩绳、料堆、吊桶从地里顶出；建筑只有台基 |
| 0.46–3.8 s | 建筑**从下往上被剖开地长**；脚手架每 2.2 m 一层，比作业面早 0.2 s 立起 |
| 3.8–4.6 s | 从上往下拆架（每层 Z 向收拢 + 抽到地下） |
| 4.6–5.8 s | 场件依次退回地里，场地清空 |

三种驱动方式，按需要选：

```gdscript
# ① 按游戏工期压缩/拉长（RTS 常用：建造耗时 8 秒）
$ConstructionSite.play(8.0)

# ② 定格在 50%（断点续建 / 验收截图）
$ConstructionSite.set_progress(0.5)

# ③ 立刻完工（跳过剩下的动画）
$ConstructionSite.finish_now()
```

> **100% ≠ 收工**：`set_progress(1.0)` 只代表楼盖完，脚手架还在，还要 0.8 s 撤架 + 1.2 s 清场。
> 想直接看干净场地就 `finish_now()`（会把动画拨到末帧）。

---

## 5. 建成后切回普通资产

建造 GLB 是**施工期专用**——它带着脚手架的 4–5k 三角和 16 根骨。
楼盖完就该换成普通的 `<建筑>.glb`（桌面档）或 `<建筑>_手游_近.glb`（手游档）：

```gdscript
func _on_build_finished() -> void:
	var normal: PackedScene = load("res://assets/铁匠铺/铁匠铺.glb")
	var node := normal.instantiate()
	get_parent().add_child(node)
	queue_free()
```

连接方式：`$ConstructionSite.build_finished.connect(_on_build_finished)`。

---

## 6. 换阵营

`team` / `team_trim` 两个 surface 在建造期也被换成了着色器，原来那种"改材质颜色"会失效，
用脚本给的接口：

```gdscript
$ConstructionSite.set_team_color(Color("#B4382E"), Color("#F0C879"))  # 赤刃红
```

> 九座建筑的 4 个 surface 依次是 `team`(0) / `team_trim`(1) / `主体`(2) / `自发光`(3)，
> 脚本按序号认这两个面（GLB 里 prim→material 顺序固定，九座逐座核对过）。

---

## 7. 验收（三张图，缺一不可）

把 `auto_play` 关掉，`start_progress` 分别设 **0 / 0.5 / 1**，各截一张：

| start_progress | 应该看到 | 常见错误 |
|---|---|---|
| **0.0** | 只有台基那一小截 + 第一层脚手架 + 场地道具 | 看到完整建筑 → 遮罩没生效（脚本没挂上 / shader 路径不对） |
| **0.5** | **半截楼**，剖口是横向的、边缘毛糙、往下 0.4 m 是浅色"生料"；脚手架比楼高一层 | 看到"缩小版完整楼" → 你用的是旧版资产，不是 `_建造.glb` |
| **1.0** | 完整建筑，脚手架还围着 | 塔尖被削平 → `reveal_height` 没抬到 `z1 + 5` |

再对一次数值：`0.5` 时建筑可见高度应该 ≈ `z0 + (z1 - z0) × 0.5`（参数见 §9）。

---

## 8. 踩过的坑（都是真踩的）

**① 脚手架被一起裁掉。**
`team` / `team_trim` 是建筑和脚手架**共用的材质**。直接给共享材质加遮罩，脚手架上的队色箍、
挂旗、挂幡会跟着被切。脚本用的是 `set_surface_override_material()`（只覆盖建筑那几个面），
**不要**改成 `material_override` —— 那会用一个材质盖掉建筑全部 4 个 surface，贴图全丢。

**② 阴影还是完整建筑。**
着色器已经开了 `depth_prepass_alpha`，让 `discard` 作用到阴影。若你的 Godot 版本仍不对，
退一步：施工期间把 `Building.cast_shadow` 关掉（影子由脚手架提供，RTS 距离看不出来）。

**③ 建筑本体没有骨、没有动画 —— 别去加。**
"长大"如果是靠 `scale` 或骨骼位移做的，50% 时看到的一定是"缩小版完整楼"。
本体零骨零动画是这套系统的**设计前提**，也是资产体检里的硬指标
（`BODY_RIG = 0`、`BODY_TRIS = 0`）。要改表现只能改遮罩，不能改几何。

**④ 一进去就"全套件都在"。**
AnimationPlayer 没 `play` 时，模型停在**绑定姿势（rest pose）= 全部脚手架立好的状态**。
脚本 `_ready` 里已经自动播了；如果你是手动搭场景，记得 `play("build")`。

**⑤ 楼不是从地面长，而是整体浮在空中 / 整体消失。**
遮罩高度是**模型自身坐标的 Y**（原点在地面），所以整栋楼可以随便平移、绕 Y 旋转。
但**不能给实例设 scale**——缩放会让"米"这个单位和参数表对不上。
另外旋转只能绕 Y；绕 X/Z 转会把"上"转歪。

**⑥ 剖面看起来是空心的。**
着色器是 `cull_disabled`（双面），剖开后能看到内壁并被压暗到 40%。
如果还是透，检查是不是被别的材质覆盖了（见 ①）。

**⑦ 动画名不是 `build`。**
脚本会兜底取 `AnimationPlayer` 的第一条并打警告。真要改名，改 `clip_name` 字段。

---

## 9. 九座参数（也是 `build_reveal_data.gd` 的内容）

| 建筑 | 高 h | z0（0%） | z1（100%） | t0 | t1 | 整条时长 |
|---|---|---|---|---|---|---|
| 铁匠铺 | 11.83 | 1.00 | 11.83 | 0.46 | 3.40 | 5.17 s |
| 兵营 | 11.60 | 1.00 | 11.60 | 0.46 | 3.38 | 5.15 s |
| 城镇大厅 | 25.15 | 1.00 | 25.15 | 0.46 | 4.01 | 5.96 s |
| 哨塔 | 17.34 | 1.00 | 17.34 | 0.46 | 3.81 | 5.76 s |
| 农场 | 10.11 | 1.00 | 10.11 | 0.46 | 3.27 | 5.04 s |
| 伐木场 | 7.72 | 0.77 | 7.72 | 0.46 | 3.09 | 4.77 s |
| 神秘圣地 | 16.18 | 1.00 | 16.18 | 0.46 | 3.72 | 5.67 s |
| 蒸汽车坊 | 10.04 | 1.00 | 10.04 | 0.46 | 3.26 | 5.03 s |
| 箭塔 | 17.46 | 1.00 | 17.46 | 0.46 | 3.82 | 5.77 s |

引擎里只要这一条公式，和预览台完全一致（线性，没有缓动）：

```text
reveal_height(t) = z0 + (z1 - z0) * clamp((t - t0) / (t1 - t0), 0, 1)
```

---

## 10. 加一座新建筑

1. 建模脚本跑完，`assets/<新建筑>/` 下有 `<新建筑>_手游_近.glb`（或 `_低模.glb`）。
2. `python build/bl_act.py act blender/bs_v6/cs_one.py <新建筑>` —— 首次会自动量体、
   生成契约、切脚手架、导出 `_建造.glb`、体检（要 Blender 开着桥接插件）。
3. `python build/mk_godot_data.py` —— 把新的一座补进 `godot/build_reveal_data.gd`。
4. 工程里重复 §2–§4，`building_name` 填新名字。

---

## 11. 开销

| 项 | 数量 |
|---|---|
| GLB | 1.0–1.8 MB / 座（九座合计 11.9 MB） |
| 三角 | 建筑 7k–17k + 套件 4k–5.6k |
| surface / draw call | 12（建筑 4 + 套件 8） |
| 骨骼 | 16 根，全在套件上 |
| 着色器 | 1 个，2 张贴图 uniform（albedo / emissive），一次额外的深度 prepass |
| 建成后 | 切回普通资产 → 脚手架、骨、遮罩全部归零 |

施工期用的是**简化 PBR**（粗糙度 / 金属度走标量，不吃 ORM 贴图），因为只演 5 秒；
建成切回普通资产后画质不受影响。
