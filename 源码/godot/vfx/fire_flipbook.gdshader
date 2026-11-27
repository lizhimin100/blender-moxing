// fire_flipbook.gdshader —— 把 pixelfx（或任何序列帧）生成的火焰图集铺到一张 billboard 上
//
// 用法（Godot 4.x）：
//   1. MeshInstance3D → 新建 QuadMesh（size 设成火的实际尺寸，比如 1.2 × 1.2）
//   2. 新建 ShaderMaterial → 载入本 shader → sheet 指到 campfire.png
//   3. columns / frame_count / fps 按图集 json 里的 meta.pixelfx 填（营火是 10 / 90 / 30）
//   4. cast_shadow 关掉；排序用 render_priority 调后一点，避免和建筑 z-fighting
//
// 设计取舍：
//   · unshaded + blend_add —— 火不参与光照，靠自发光叠加，颜色不会被场景灯压暗；
//   · filter_nearest —— 像素风必须最近邻，否则 128px 的图放大会糊成一团光晕；
//   · 时间取 TIME，帧号 = floor(TIME*fps) % frames，循环无接缝（pixelfx 本身保证首尾对齐）。
shader_type spatial;
render_mode blend_add, unshaded, cull_disabled, depth_draw_never, shadows_disabled;

uniform sampler2D sheet : source_color, filter_nearest, repeat_disable;
uniform int columns = 10;
uniform int frame_count = 90;
uniform float fps = 30.0;
uniform vec2 frame_size = vec2(128.0, 128.0);
uniform vec4 tint : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float boost = 2.2;          // 自发光倍率；HDR 管线下 2–4 比较合适
uniform float alpha_cut = 0.03;     // 低于这个 alpha 直接丢弃，省 overdraw
uniform float pixel_snap = 0.5;     // 1 = 死像素对齐；0 = 跟随 UV 插值（更平滑）
uniform bool billboard = true;

void vertex() {
    if (billboard) {
        // Godot 4 官方 billboard 写法：丢掉模型旋转、保留模型位置与缩放
        MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
            INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2],
            MODEL_MATRIX[3]);
        MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(
            vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0),
            vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0),
            vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0),
            vec4(0.0, 0.0, 0.0, 1.0));
    }
}

void fragment() {
    int idx = int(mod(floor(TIME * fps), float(frame_count)));
    int col = idx % columns;
    int row = idx / columns;
    float rows = ceil(float(frame_count) / float(columns));

    vec2 uv = UV;
    if (pixel_snap > 0.0) {
        // 把 UV 吸附到源像素中心，放大后边缘仍然硬
        vec2 px = floor(uv * frame_size) + 0.5;
        uv = mix(uv, px / frame_size, pixel_snap);
    }
    vec2 sheet_uv = (vec2(float(col), float(row)) * frame_size + uv * frame_size)
                    / (vec2(float(columns), rows) * frame_size);

    vec4 c = texture(sheet, sheet_uv);
    if (c.a < alpha_cut) {
        discard;
    }
    ALBEDO = c.rgb * tint.rgb;
    EMISSION = c.rgb * tint.rgb * boost;
    ALPHA = c.a * tint.a;
}
