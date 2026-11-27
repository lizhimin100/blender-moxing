// build_reveal.gdshader —— 建造显影：按模型自身高度把建筑剖开
//
// 挂在「建筑」那个 MeshInstance3D 的每个 surface 上（不要挂到脚手架）。
// 高度用**模型自身坐标的 Y**（模型原点在占地中心的地面上），
// 所以整栋楼搬到世界任何位置、绕 Y 转任何角度都不用改参数。
//
// 施工期只用简化 PBR（粗糙度 / 金属度走标量），建成后切回普通资产，画质不受影响。
shader_type spatial;
// cull_disabled：剖开后要看得到内壁，不然从上面看是空心的
// depth_prepass_alpha：让 discard 也作用到阴影，否则半截楼仍投完整影子
render_mode cull_disabled, depth_prepass_alpha;

// ── 原材质（由 build_reveal.gd 从导入的 StandardMaterial3D 抄过来）──
uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform bool  use_albedo_tex = false;
uniform vec4  albedo_color : source_color = vec4(1.0);
uniform float roughness_v : hint_range(0.0, 1.0) = 0.85;
uniform float metallic_v : hint_range(0.0, 1.0) = 0.0;
uniform sampler2D emission_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform bool  use_emission_tex = false;
uniform vec4  emission_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform float emission_energy = 1.0;

// ── 显影（每帧由脚本写 reveal_height）──
uniform float reveal_height : hint_range(-1.0, 60.0) = 100.0; // 米；>= 建筑高 = 完整
uniform float jag = 0.034;          // 剖口毛边幅度，0 = 激光切面
uniform float raw_width = 0.42;     // 剖口往下铺多厚的"生料"
uniform vec4  raw_color : source_color = vec4(0.58, 0.55, 0.48, 1.0);
uniform float raw_mix : hint_range(0.0, 1.0) = 0.58;
uniform float inner_dark : hint_range(0.0, 1.0) = 0.40;

varying vec3 v_local;

void vertex() {
	v_local = VERTEX;
}

void fragment() {
	// 毛边：三个不同频率的正弦叠加，读作"砌到一半"而不是被刀切
	float n = sin(v_local.x * 7.3) * 0.5
			+ sin(v_local.z * 9.1 + 1.7) * 0.35
			+ sin(v_local.x * 23.0 + v_local.z * 17.0) * 0.25;
	float zc = v_local.y + n * jag;

	if (zc > reveal_height) {
		discard;
	}

	vec3 alb = albedo_color.rgb;
	if (use_albedo_tex) {
		alb *= texture(albedo_tex, UV).rgb;
	}
	// 背面 = 内壁：压暗，剖断面才读作"看进没封顶的内部"
	if (!FRONT_FACING) {
		alb *= inner_dark;
	}
	// 剖口往下 raw_width 米铺一层生料色（带颗粒）
	float edge = smoothstep(reveal_height - raw_width, reveal_height, zc);
	float grain = 0.5 + 0.5 * sin(v_local.x * 31.0 + v_local.z * 27.0 + v_local.y * 19.0);
	alb = mix(alb, raw_color.rgb * (0.84 + 0.30 * grain), edge * raw_mix);

	ALBEDO = alb;
	ROUGHNESS = roughness_v;
	METALLIC = metallic_v;

	if (use_emission_tex) {
		EMISSION = emission_color.rgb * texture(emission_tex, UV).rgb * emission_energy;
	} else {
		EMISSION = emission_color.rgb * emission_energy;
	}
}
