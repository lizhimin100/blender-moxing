"""
bl_rt.py —— Blender 实时通道客户端（本机适配层）

DSH 插件暴露的是一条本地 HTTP 通道（后端 127.0.0.1:9877 → Blender addon 9876）。
这个脚本把它包成命令行：不需要 DSH 宿主，也能在 Blender 里跑任意 bpy 代码。

    python build/bl_rt.py ping
    python build/bl_rt.py act path/to/script.py      # 在 Blender 主线程执行
    python build/bl_rt.py expr "print(bpy.app.version_string)"
    python build/bl_rt.py shot out.png               # 视口截图

所有请求都走 /act（与插件工具 blender_rt_do 同一条路由），因此写租约、
错误回传、持久内核 K 的行为与在 DSH 里调用完全一致。
"""
import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("BL_RT", "http://127.0.0.1:9877")


def post(path, payload, timeout=1800):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path, timeout=60):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def run(code, label="code"):
    t0 = time.time()
    # addon 侧的 execute_code 有自己的超时（默认 120 s）；长活（渲染 / 批量细分）要显式放宽。
    payload = {"code": code}
    try:
        payload["timeoutMs"] = int(os.environ.get("BL_TIMEOUT_MS", "0")) or 120000
    except ValueError:
        payload["timeoutMs"] = 120000
    r = post("/act", payload)
    dt = time.time() - t0
    out = (r.get("stdout") or "").strip()
    if out:
        print(out)
    if r.get("stderr"):
        print("[stderr]", r["stderr"].strip(), file=sys.stderr)
    if not r.get("ok"):
        print(f"[FAIL {label}] {r.get('error')}", file=sys.stderr)
        tb = r.get("traceback")
        if tb:
            print(tb[-1800:], file=sys.stderr)
        return 1
    print(f"[ok {label}] {dt:.1f}s")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ping"
    if cmd == "ping":
        r = json.loads(get("/doctor").decode())
        print("doctor ok:", r.get("ok"), r.get("addon", {}).get("kind"))
        return 0 if r.get("ok") else 1
    if cmd == "act":
        with open(sys.argv[2], encoding="utf-8") as f:
            return run(f.read(), os.path.basename(sys.argv[2]))
    if cmd == "expr":
        return run(sys.argv[2], "expr")
    if cmd == "shot":
        png = get(f"/frame.png?size={sys.argv[3] if len(sys.argv) > 3 else 900}")
        with open(sys.argv[2], "wb") as f:
            f.write(png)
        print("saved", sys.argv[2], len(png), "bytes")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
