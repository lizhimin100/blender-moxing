"""assemble.py —— 一条命令跑完一套资产的流水线

    python build/assemble.py            # 全跑
    python build/assemble.py --only 图标 # 只跑名字里带"图标"的步骤

顺序是**有依赖的**，不要打乱：

    ① 手游档导出   图集 + 近/中/远 GLB      ← 后面 .blend 要用它生成的图集
    ② 交付 .blend  打包贴图 + 相对路径
    ③ 体检         穿模 / 悬空 / 共面        （只读，不改文件）
    ④ 出图         主图 / 正面 / 侧面 / 俯视 …
    ⑤ 图标         Blender 出 raw
    ⑥ 图标合成     系统 Python（Blender 里没有 PIL）

前提：Blender 开着，DSH 插件在 9876（`build/bl_act.py ping` 应返回 pong）。
每个步骤单独一次 Blender 调用；任一步失败就停，退出码非 0。
"""
import argparse
import subprocess
import sys
import time

ROOT = r"D:/测试一"
PY = sys.executable
BL_ACT = "build/bl_act.py"

# (显示名, 脚本, 用哪个解释器：bl=Blender 通道 / py=系统 Python)
STEPS = [
    ("手游档导出", "blender/bs_v6/export_mobile.py", "bl"),
    ("交付 .blend", "blender/bs_v6/export_blend.py", "bl"),
    ("铁匠铺体检", "blender/bs_v6/bs_align.py", "bl"),
    ("兵营体检", "blender/bs_v6/br_align.py", "bl"),
    ("城镇大厅体检", "blender/bs_v6/th_align.py", "bl"),
    ("哨塔体检", "blender/bs_v6/wt_align.py", "bl"),
    ("农场体检", "blender/bs_v6/fm_align.py", "bl"),
    ("铁匠铺出图", "blender/bs_v6/bs_shots.py", "bl"),
    ("兵营出图", "blender/bs_v6/br_shots.py", "bl"),
    ("城镇大厅出图", "blender/bs_v6/th_shots.py", "bl"),
    ("哨塔出图", "blender/bs_v6/wt_shots.py", "bl"),
    ("农场出图", "blender/bs_v6/fm_shots.py", "bl"),
    ("图标渲染", "blender/bs_v6/icon_shots.py", "bl"),
    ("图标合成", "blender/bs_v6/icon_post.py", "py"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只跑名字里含该关键词的步骤")
    ap.add_argument("--list", action="store_true", help="只列步骤")
    args = ap.parse_args()

    steps = [s for s in STEPS if args.only in s[0]]
    if args.list:
        for i, (name, script, kind) in enumerate(steps, 1):
            print("%d. %-12s %-34s [%s]" % (i, name, script, kind))
        return 0
    if not steps:
        print("没有匹配的步骤")
        return 1

    t_all = time.time()
    for i, (name, script, kind) in enumerate(steps, 1):
        cmd = ([PY, BL_ACT, "act", script] if kind == "bl" else [PY, script])
        print("\n=== [%d/%d] %s  (%s)" % (i, len(steps), name, script))
        t0 = time.time()
        r = subprocess.run(cmd, cwd=ROOT)
        dt = time.time() - t0
        if r.returncode != 0:
            print("!!! %s 失败（退出码 %d，用时 %.0fs）" % (name, r.returncode, dt))
            return r.returncode
        print("--- %s 完成 %.0fs" % (name, dt))

    print("\n全部完成，用时 %.1f 分钟" % ((time.time() - t_all) / 60.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
