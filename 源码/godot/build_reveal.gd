class_name BuildReveal
extends Node3D
## 建造显影驱动器 —— 挂在 `<建筑>_建造.glb` 实例的**根节点**上。
##
## 它做三件事：
##   1. 把「建筑」那个 MeshInstance3D 的每个 surface 换成显影着色器（不动脚手架）；
##   2. 每帧把 `build` 动画的时间换算成遮罩高度，写进着色器；
##   3. 播完发 `build_finished`，游戏收到后切回普通资产 <建筑>.glb。
##
## 九座的 z0 / z1 / t0 / t1 在 build_reveal_data.gd 的常量表里，按 `building_name` 取。
## 换一座建筑只改 `building_name` 一个字段。

signal build_finished

const SHADER_PATH := "res://godot/build_reveal.gdshader"

@export var building_name: String = "铁匠铺"
@export var clip_name: String = "build"
@export var auto_play: bool = true
## auto_play = false 时停在这一帧（0 = 只露地基，0.5 = 半截，1 = 完整）——验收截图用
@export_range(0.0, 1.0) var start_progress: float = 0.0
## >0 时按指定秒数压缩/拉长整条建造（RTS 里由建造耗时决定）
@export var force_duration: float = -1.0

var _mats: Array[ShaderMaterial] = []
var _team_mats: Array[ShaderMaterial] = []
var _trim_mats: Array[ShaderMaterial] = []
var _anim: AnimationPlayer
var _z0: float = 1.0
var _z1: float = 10.0
var _t0: float = 0.46
var _t1: float = 3.0
var _progress: float = 0.0
var _manual := false   # true = 被 set_progress 定格，_process 不许覆盖


func _ready() -> void:
	_load_data()
	_build_materials()
	_anim = _find_anim()
	if _anim != null:
		_anim.animation_finished.connect(_on_anim_finished)
		if auto_play:
			play(force_duration)
		else:
			set_progress(start_progress)
	else:
		push_warning("BuildReveal: 没找到 AnimationPlayer，建筑会一直停在 0%")


func _process(_dt: float) -> void:
	if _anim == null or _manual:
		return
	var t := _anim.current_animation_position
	_apply((t - _t0) / maxf(_t1 - _t0, 0.001))


# ── 对外 ──────────────────────────────────────────────────────────────────
func play(duration: float = -1.0) -> void:
	if _anim == null:
		return
	_manual = false
	_anim.speed_scale = 1.0
	if duration > 0.0:
		var clip_len := _clip_length()
		if clip_len > 0.0:
			_anim.speed_scale = clip_len / duration
	_anim.play(clip_name)
	_anim.seek(0.0, true)
	_apply(0.0)


## 0..1 定格（暂停施工 / 断点续建）。会同时把动画拨到对应位置。
func set_progress(p: float) -> void:
	_manual = true
	_apply(p)
	if _anim == null:
		return
	if String(_anim.current_animation) != clip_name:
		_anim.play(clip_name)
	_anim.pause()
	_anim.seek(lerpf(_t0, _t1, clampf(p, 0.0, 1.0)), true)


## 立刻完工：脚手架直接退场，建筑完整。
func finish_now() -> void:
	_manual = true
	if _anim != null:
		if String(_anim.current_animation) != clip_name:
			_anim.play(clip_name)
		_anim.pause()
		_anim.seek(_clip_length(), true)
	_apply(1.0)


func get_progress() -> float:
	return _progress


## 换阵营：直接改 team / team_trim 两个 surface 的颜色（原材质是纯色）
func set_team_color(main: Color, trim: Color) -> void:
	for m in _team_mats:
		m.set_shader_parameter("albedo_color", main)
	for m in _trim_mats:
		m.set_shader_parameter("albedo_color", trim)


# ── 内部 ──────────────────────────────────────────────────────────────────
func _apply(p: float) -> void:
	_progress = clampf(p, 0.0, 1.0)
	var h: float
	if _progress >= 0.9999:
		h = _z1 + 5.0          # 抬到楼顶之上，否则毛边会把塔尖削掉 3 cm
	else:
		h = lerpf(_z0, _z1, _progress)
	for m in _mats:
		m.set_shader_parameter("reveal_height", h)


func _load_data() -> void:
	var r: Dictionary = BuildRevealData.TABLE.get(building_name, {})
	if r.is_empty():
		push_warning("BuildReveal: BuildRevealData 里没有「%s」，用量体默认值" % building_name)
		return
	_z0 = float(r.get("z0", _z0))
	_z1 = float(r.get("z1", _z1))
	_t0 = float(r.get("t0", _t0))
	_t1 = float(r.get("t1", _t1))


func _build_materials() -> void:
	var mi := _find_mesh("Building")
	if mi == null:
		push_warning("BuildReveal: 没找到名为 Building 的 MeshInstance3D")
		return
	var sh: Shader = load(SHADER_PATH)
	if sh == null:
		push_error("BuildReveal: 缺 " + SHADER_PATH)
		return
	var mesh := mi.mesh
	if mesh == null:
		return
	for i in mesh.get_surface_count():
		var src := mi.get_active_material(i)
		var m := ShaderMaterial.new()
		m.shader = sh
		_copy_params(m, src)
		# 关键：用 surface_override，**不能改导入的材质本身** ——
		# team / team_trim 是建筑和脚手架共用的，改了会连脚手架旗幡一起裁掉
		mi.set_surface_override_material(i, m)
		_mats.append(m)
		# 九座统一：建筑 4 个 surface 依次是 team / team_trim / 主体 / 自发光
		# （GLB 里 prim→material 顺序固定，九座逐座核对过）
		if i == 0:
			_team_mats.append(m)
		elif i == 1:
			_trim_mats.append(m)


func _copy_params(dst: ShaderMaterial, src: Material) -> void:
	dst.set_shader_parameter("reveal_height", _z0)
	if src is BaseMaterial3D:
		var b := src as BaseMaterial3D
		dst.set_shader_parameter("albedo_color", b.albedo_color)
		dst.set_shader_parameter("albedo_tex", b.albedo_texture)
		dst.set_shader_parameter("use_albedo_tex", b.albedo_texture != null)
		dst.set_shader_parameter("roughness_v", b.roughness)
		dst.set_shader_parameter("metallic_v", b.metallic)
		dst.set_shader_parameter("use_emission_tex", b.emission_texture != null)
		dst.set_shader_parameter("emission_tex", b.emission_texture)
		dst.set_shader_parameter("emission_color", b.emission)
		dst.set_shader_parameter("emission_energy",
			b.emission_energy_multiplier if b.emission_enabled else 0.0)
	else:
		dst.set_shader_parameter("albedo_color", Color(0.6, 0.6, 0.6))
		push_warning("BuildReveal: 有 surface 不是 StandardMaterial3D，已用中性灰兜底")


func _find_mesh(name_: String) -> MeshInstance3D:
	var n := find_child(name_, true, false)
	if n is MeshInstance3D:
		return n as MeshInstance3D
	return null


func _find_anim() -> AnimationPlayer:
	var n := find_child("AnimationPlayer", true, false)
	if n is AnimationPlayer:
		var ap := n as AnimationPlayer
		if ap.has_animation(clip_name):
			return ap
		var list := ap.get_animation_list()
		if list.size() > 0:
			push_warning("BuildReveal: 没有 %s，改用 %s" % [clip_name, list[0]])
			clip_name = list[0]
			return ap
	return null


func _clip_length() -> float:
	if _anim == null or not _anim.has_animation(clip_name):
		return 0.0
	return _anim.get_animation(clip_name).length


func _on_anim_finished(anim: StringName) -> void:
	if String(anim) == clip_name:
		_apply(1.0)
		build_finished.emit()
