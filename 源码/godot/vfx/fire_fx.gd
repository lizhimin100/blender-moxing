extends Node3D
## fire_fx.gd —— 给任意导入的 GLB 挂上"会呼吸的火"。
##
## 为什么不在 GLB 里做：glTF 不支持动画材质（KHR_animation_pointer 生态不成熟，
## Godot 的 glTF 导入器也不认序列帧/材质关键帧）。所以**火效一律在 Godot 侧挂**，
## GLB 只负责"火长在哪儿"。
##
## 用法：
##   1. 把本脚本挂到建筑根节点（比如 地牢 的根 Node3D）。
##   2. 保持默认 mode = GEOMETRY —— 直接用 GLB 里那几片火几何，只加自发光脉动 + 点光。
##      （零额外资源，和低模审美完全一致，推荐先用这个。）
##   3. 想要 pixelfx 那种贴片火，把 mode 改成 SPRITE，并把 sheet 指到导出的图集。
##
## 注意：GLB 里的材质是**共享实例**（team / team_trim / flame_* 全建筑共用一份）。
## 直接改 material 会连累场景里所有同类建筑，所以这里一律 duplicate 出独立副本。

enum Mode { GEOMETRY, SPRITE }

@export var mode: Mode = Mode.GEOMETRY
@export var flame_prefix: String = "flame"      ## 节点名以它开头的都算火
@export var light_energy: float = 1.6
@export var light_range: float = 3.2
@export var light_color: Color = Color(1.0, 0.62, 0.28)
@export var pulse_speed: float = 2.6
@export var pulse_depth: float = 0.35           ## 0 = 不闪，0.35 = 明显跳动
@export var emission_scale: float = 3.0
@export var light_per_flame: bool = false        ## 一处火一盏灯（多了会烧性能）
@export var sheet: Texture2D
@export var sheet_columns: int = 10
@export var sheet_frames: int = 90
@export var sheet_fps: float = 30.0
@export var sheet_size: float = 1.2

var _mats: Array[StandardMaterial3D] = []
var _energy0: Array[float] = []
var _lights: Array[OmniLight3D] = []
var _t: float = 0.0


func _ready() -> void:
	randomize()
	_t = randf() * 10.0                     # 每处火错相位，避免整张地图同步呼吸
	var flames := _find_flames(self)
	if mode == Mode.SPRITE and sheet != null:
		for f in flames:
			f.visible = false
			_spawn_billboard(f.global_position + Vector3(0, 0.45, 0))
	else:
		for f in flames:
			var src := f as MeshInstance3D
			if src == null:
				continue
			var base := src.get_active_material(0)
			if base is StandardMaterial3D:
				var m: StandardMaterial3D = (base as StandardMaterial3D).duplicate()
				src.material_override = m
				_mats.append(m)
				_energy0.append(m.emission_energy_multiplier)
		if light_per_flame:
			for f in flames:
				_add_light(f.global_position + Vector3(0, 0.35, 0))
		else:
			# 只给最亮的那处火（一般是火堆中心）配一盏灯
			var best: Node3D = null
			for f in flames:
				if best == null or f.global_position.y > best.global_position.y:
					best = f
			if best != null:
				_add_light(best.global_position + Vector3(0, 0.35, 0))


func _process(delta: float) -> void:
	_t += delta
	var k := 1.0 + pulse_depth * (sin(_t * pulse_speed) * 0.6
			+ sin(_t * pulse_speed * 2.37 + 1.7) * 0.4)
	for i in _mats.size():
		_mats[i].emission_energy_multiplier = _energy0[i] * k
	for l in _lights:
		l.light_energy = light_energy * k
		l.position.y += sin(_t * 7.0) * 0.0006


func _find_flames(root: Node) -> Array[MeshInstance3D]:
	var out: Array[MeshInstance3D] = []
	var stack: Array[Node] = [root]
	while not stack.is_empty():
		var n: Node = stack.pop_back()
		stack.append_array(n.get_children())
		if n is MeshInstance3D and n.name.to_lower().begins_with(flame_prefix):
			out.append(n as MeshInstance3D)
	return out


func _add_light(pos: Vector3) -> void:
	var l := OmniLight3D.new()
	l.light_color = light_color
	l.light_energy = light_energy
	l.omni_range = light_range
	l.omni_attenuation = 1.6
	l.shadow_enabled = false
	add_child(l)
	l.global_position = pos
	_lights.append(l)


func _spawn_billboard(pos: Vector3) -> void:
	var mi := MeshInstance3D.new()
	var q := QuadMesh.new()
	q.size = Vector2(sheet_size, sheet_size)
	mi.mesh = q
	var mat := ShaderMaterial.new()
	mat.shader = load("res://vfx/fire_flipbook.gdshader")
	mat.set_shader_parameter("sheet", sheet)
	mat.set_shader_parameter("columns", sheet_columns)
	mat.set_shader_parameter("frame_count", sheet_frames)
	mat.set_shader_parameter("fps", sheet_fps)
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	mi.global_position = pos
