# -*- coding: utf-8 -*-
"""把预览页打成"双击就能看"的单文件 HTML。

为什么要这么绕：
  · 现有 预览.html 用 importmap + ES module 引 three，模型走 fetch 拉 GLB —— 这两件事
    在 file:// 协议下都会被浏览器的同源策略拦掉，双击打开必定白屏。
  · 发到别人电脑上又不能假设有 Python 起 http server。
所以：three / GLTFLoader / OrbitControls 改成普通 <script>（去掉 import/export，
挂到 window 上），GLB 走 base64 内嵌，GLTFLoader.parse 直接吃 ArrayBuffer。

产物：dist/…/预览/预览.html（自包含，6 MB 左右）
生成：python build/make_preview_bundle.py
"""
import base64
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "preview", "vendor")

# 三个建筑：只内嵌"手游近"档（1.0 – 1.3 MB），完整多档在 assets/ 里
MODELS = [
    ("bs", "铁匠铺", "assets/铁匠铺/铁匠铺_手游_近.glb", "手游近档"),
    ("br", "兵营", "assets/兵营/兵营_手游_近.glb", "手游近档"),
    ("th", "城镇大厅", "assets/城镇大厅/城镇大厅_手游_近.glb", "手游近档"),
]

RE_IMPORT = re.compile(r"^import\s*\{([^}]*)\}\s*from\s*'three';\s*", re.M | re.S)
RE_REL_IMPORT = re.compile(
    r"^import\s*\{([^}]*)\}\s*from\s*'\./([A-Za-z0-9_.]+)\.js';\s*", re.M | re.S)
RE_EXPORT_NAMED = re.compile(r"^export\s*\{([^}]*)\};\s*$", re.M)
RE_EXPORT_DECL = re.compile(r"^export\s+(function|class|const|let|var)\s+", re.M)


def to_plain(path, global_name, dep_globals=()):
    """ES module → 普通脚本：import 换成从 window 解构，export 换成挂 window。"""
    src = io.open(path, encoding="utf-8").read()

    def _imp(m):
        names = " ".join(m.group(1).split())
        return "const { %s } = window.THREE;\n" % names

    REL_MAP = {"BufferGeometryUtils": "BGU"}

    def _rel(m):
        names = " ".join(m.group(1).split())
        key = REL_MAP.get(m.group(2), m.group(2).upper())
        return "const { %s } = window.%s;\n" % (names, key)

    src, n_imp = RE_IMPORT.subn(_imp, src, count=1)
    src, _ = RE_REL_IMPORT.subn(_rel, src, count=1)
    src = RE_EXPORT_DECL.sub(r"\1 ", src)

    def _exp(m):
        names = [x.strip() for x in m.group(1).split(",") if x.strip()]
        # 只导出一个（GLTFLoader / OrbitControls）就直接挂函数，多个（BGU）挂成对象
        if len(names) == 1:
            return "window.%s = %s;\n" % (global_name, names[0])
        return "window.%s = { %s };\n" % (global_name, ", ".join(names))

    src, n_exp = RE_EXPORT_NAMED.subn(_exp, src, count=1)
    if n_imp == 0 and "window.THREE" not in src and dep_globals:
        src = "const { %s } = window.THREE;\n" % ", ".join(dep_globals) + src
    return src


def three_plain():
    """three.module.js → window.THREE（末尾那条 export 直接变成对象字面量）。"""
    src = io.open(os.path.join(VENDOR, "three.module.js"), encoding="utf-8").read()

    def _exp(m):
        body = " ".join(m.group(1).split())
        body = body.rstrip(",")
        return "window.THREE = { %s };\n" % body

    src, n = RE_EXPORT_NAMED.subn(_exp, src, count=1)
    assert n == 1, "three.module.js 的 export 段没匹配到"
    return src


def main():
    out_dir = os.path.join(ROOT, "build", "_bundle")
    os.makedirs(out_dir, exist_ok=True)

    parts = {
        "three": three_plain(),
        "bgu": to_plain(os.path.join(VENDOR, "BufferGeometryUtils.js"), "BGU"),
        "gltf": to_plain(os.path.join(VENDOR, "GLTFLoader.js"), "GLTFLoader"),
        "orbit": to_plain(os.path.join(VENDOR, "OrbitControls.js"), "OrbitControls"),
    }

    blobs = {}
    for key, name, rel, kind in MODELS:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        raw = open(p, "rb").read()
        blobs[key] = base64.b64encode(raw).decode("ascii")
        print("  %-6s %-8s %7.1f KB -> base64 %7.1f KB" % (key, name, len(raw) / 1024, len(blobs[key]) / 1024))

    meta = [{"key": k, "name": n, "kind": kind} for k, n, _, kind in MODELS]

    html = io.open(os.path.join(ROOT, "build", "preview_shell.html"), encoding="utf-8").read()
    html = html.replace("/*__THREE__*/", parts["three"])
    html = html.replace("/*__BGU__*/", parts["bgu"])
    html = html.replace("/*__GLTF__*/", parts["gltf"])
    html = html.replace("/*__ORBIT__*/", parts["orbit"])
    html = html.replace("/*__META__*/", "const MODELS = %r;" % meta)
    for k, v in blobs.items():
        html = html.replace("/*__GLB_%s__*/" % k, v)

    out = os.path.join(out_dir, "预览.html")
    io.open(out, "w", encoding="utf-8").write(html)
    print("written", out, "%.1f MB" % (os.path.getsize(out) / 1048576))


if __name__ == "__main__":
    main()
