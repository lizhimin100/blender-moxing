"""
probe.py —— 交互回归探针：验证预览台的「切换建筑 / 旋转视角 / 切换动画 / 帧率」。

用法：
  python build/probe.py [--url http://127.0.0.1:8904/preview/index.html] [--outdir .workbuddy/tmp]

退出码：全部通过 0，否则 1。
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9223
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROFILE = os.path.join(ROOT, ".workbuddy", "tmp", "chrome-probe")
DEFAULT_URL = "http://127.0.0.1:8904/preview/index.html"


def http(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


class CDP:
    def __init__(self):
        self.proc = subprocess.Popen([
            CHROME, "--headless=new", "--enable-unsafe-swiftshader",
            f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
            f"--user-data-dir={PROFILE}", "--window-size=1440,960",
            "--hide-scrollbars", "--no-first-run", "--disable-extensions",
            "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                http("/json/version")
                break
            except Exception:
                time.sleep(0.2)
        tab = http("/json/new?about:blank", "PUT")
        self.ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=40)
        self.n = 0
        self.send("Page.enable")
        self.send("Runtime.enable")
        self.send("Network.enable")
        self.send("Network.setCacheDisabled", {"cacheDisabled": True})

    def send(self, method, params=None):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                return msg.get("result", {})

    def js(self, expr, timeout=40):
        r = self.send("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": True,
        })
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("text", "js error") + " | " + expr[:120])
        return r.get("result", {}).get("value")

    def wait(self, expr, timeout=40, interval=0.25):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if self.js(expr):
                    return True
            except Exception:
                pass
            time.sleep(interval)
        return False

    def shot(self, path):
        r = self.send("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path

    def drag(self, x0, y0, x1, y1, steps=12):
        self.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x0, "y": y0, "button": "left", "clickCount": 1})
        for i in range(1, steps + 1):
            x = x0 + (x1 - x0) * i / steps
            y = y0 + (y1 - y0) * i / steps
            self.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": x, "y": y, "button": "left", "buttons": 1})
            time.sleep(0.016)
        self.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x1, "y": y1, "button": "left", "clickCount": 1})

    def close(self):
        try:
            self.ws.close()
        finally:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except Exception:
                self.proc.kill()


def main():
    url = DEFAULT_URL
    outdir = os.path.join(ROOT, ".workbuddy", "tmp")
    if "--url" in sys.argv:
        url = sys.argv[sys.argv.index("--url") + 1]
    if "--outdir" in sys.argv:
        outdir = sys.argv[sys.argv.index("--outdir") + 1]
    os.makedirs(outdir, exist_ok=True)

    c = CDP()
    results = []
    try:
        c.send("Page.navigate", {"url": url})
        c.js("window.__preview = window.__preview || null")

        ok = c.wait("!!(window.__preview && window.__preview.S.root)", timeout=60)
        if not ok:
            err = c.js("document.getElementById('loading')?.textContent") or ""
            print("FAIL 首屏未完成装载：", err)
            return 1

        entry0 = c.js("window.__preview.S.entry.id")
        cam0 = c.js("window.__preview.camera.position.toArray()")
        clips0 = c.js("Object.keys(window.__preview.S.actions)")
        meshes = c.js(
            "(()=>{let n=0,skin=0;window.__preview.scene.traverse(o=>{if(o.isMesh){n++;if(o.isSkinnedMesh)skin++;}});return [n,skin];})()")
        c.shot(os.path.join(outdir, "probe_1_init.png"))
        results.append(("首屏装载", True, f"{entry0} · clips={clips0} · meshes={meshes}"))

        # ---- 帧率
        fps = c.js("""(()=>new Promise(res=>{let n=0;const t0=performance.now();
            const f=()=>{n++;if(performance.now()-t0<1200)requestAnimationFrame(f);
            else res(+(n/((performance.now()-t0)/1000)).toFixed(1));};requestAnimationFrame(f);}))()""")
        results.append(("帧率 ≥50", fps >= 50, f"{fps} fps"))

        # ---- 切换建筑
        c.js("document.querySelectorAll('.mod')[1].click()")
        swapped = c.wait("window.__preview.S.entry.id !== %r && !window.__preview.S.busy" % entry0, timeout=45)
        entry1 = c.js("window.__preview.S.entry.id")
        title1 = c.js("document.getElementById('hTitle').textContent")
        c.shot(os.path.join(outdir, "probe_2_switch.png"))
        results.append(("切换建筑", swapped and entry1 != entry0, f"{entry0} → {entry1}（{title1}）"))

        # ---- 旋转视角
        cam_before = c.js("window.__preview.camera.position.toArray()")
        c.drag(820, 460, 1040, 380)
        time.sleep(0.5)
        cam_after = c.js("window.__preview.camera.position.toArray()")
        moved = sum(abs(a - b) for a, b in zip(cam_before, cam_after))
        c.shot(os.path.join(outdir, "probe_3_orbit.png"))
        results.append(("旋转视角", moved > 2.0, f"相机位移 {moved:.2f} m"))

        # ---- 切换动画
        names = c.js("Array.from(document.querySelectorAll('.an')).map(e=>e.dataset.clip)")
        idx = names.index("build") if "build" in names else 0
        c.js(f"document.querySelectorAll('.an')[{idx}].click()")
        time.sleep(0.9)
        clip_name = c.js("window.__preview.S.clip.name")
        t_now = c.js("window.__preview.S.time")
        playing = c.js("window.__preview.S.playing")
        tl = c.js("document.getElementById('tlName').textContent")
        c.shot(os.path.join(outdir, "probe_4_anim.png"))
        results.append(("切换动画", clip_name == "build" and t_now > 0.05,
                        f"{tl} · t={t_now:.2f}s · playing={playing}"))

        # ---- 动画推进（再等 0.6 s 应继续走）
        time.sleep(0.6)
        t2 = c.js("window.__preview.S.time")
        results.append(("动画推进", t2 > t_now + 0.2, f"{t_now:.2f}s → {t2:.2f}s"))

        # ---- 播放/暂停
        c.js("document.getElementById('btnPlay').click()")
        time.sleep(0.45)
        tp1 = c.js("window.__preview.S.time")
        time.sleep(0.45)
        tp2 = c.js("window.__preview.S.time")
        c.js("document.getElementById('btnPlay').click()")
        results.append(("暂停生效", abs(tp2 - tp1) < 0.02, f"{tp1:.2f}s → {tp2:.2f}s"))

        # ---- 切换回第一座（验证重复选择不炸）
        c.js("document.querySelectorAll('.mod')[0].click()")
        back = c.wait("!window.__preview.S.busy", timeout=45)
        entry2 = c.js("window.__preview.S.entry.id")
        results.append(("切回原建筑", back and entry2 == entry0, f"→ {entry2}"))

    finally:
        c.close()

    print("\n交互回归")
    bad = 0
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:8s} {detail}")
        bad += 0 if ok else 1
    print(f"\n{'全部通过' if bad == 0 else str(bad) + ' 项未通过'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
