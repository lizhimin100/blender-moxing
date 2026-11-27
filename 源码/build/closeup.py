"""closeup.py —— 用 CDP 抓预览台特写（不需要起 HTTP 服务，走 file://）。

用法：
  python build/closeup.py <bid> <out.png> [--cam "px,py,pz,tx,ty,tz"] [--size 900]
  python build/closeup.py townhall .workbuddy/tmp/a.png --cam "9,15,11,0,10.5,0"
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
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PORT = 9240
PROFILE = os.path.join(ROOT, ".workbuddy", "tmp", "chrome-closeup")
BASE = "file:///D:/%E6%B5%8B%E8%AF%95%E4%B8%80/preview/index.html"


def http(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    return json.loads(urllib.request.urlopen(req, timeout=10).read().decode())


def main():
    bid = sys.argv[1]
    out = sys.argv[2]
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 900
    cam = sys.argv[sys.argv.index("--cam") + 1] if "--cam" in sys.argv else None
    # 相对工程根目录写死 URL 编码
    enc = os.path.relpath(ROOT, "D:/").replace(os.sep, "/")
    url = f"file:///D:/{urllib.request.quote(enc)}/preview/index.html?b={bid}"

    proc = subprocess.Popen([
        CHROME, "--headless=new", "--enable-unsafe-swiftshader",
        f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
        f"--user-data-dir={PROFILE}", f"--window-size={size},{size}",
        "--hide-scrollbars", "--no-first-run", "--allow-file-access-from-files",
        "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                http("/json/version")
                break
            except Exception:
                time.sleep(0.2)
        ws = websocket.create_connection(
            http("/json/new?about:blank", "PUT")["webSocketDebuggerUrl"], timeout=60)
        n = [0]

        def send(m, p=None):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": m, "params": p or {}}))
            while True:
                r = json.loads(ws.recv())
                if r.get("id") == n[0]:
                    return r.get("result", {})

        send("Page.enable")
        send("Runtime.enable")
        send("Page.navigate", {"url": url})
        for _ in range(140):
            r = send("Runtime.evaluate", {
                "expression": "!!(window.__preview&&window.__preview.S.root)",
                "returnByValue": True})
            if r.get("result", {}).get("value"):
                break
            time.sleep(0.35)
        time.sleep(0.9)

        setup = """(()=>{
          document.querySelectorAll('aside,.tl,.hud,.foot,.loading').forEach(e=>e&&(e.style.display='none'));
          document.querySelector('main').style.width='100vw';
          window.dispatchEvent(new Event('resize'));
        """
        if cam:
            px, py, pz, tx, ty, tz = [float(v) for v in cam.split(",")]
            setup += f"""
              const P=window.__preview;
              P.camera.position.set({px},{py},{pz});
              P.controls.target.set({tx},{ty},{tz});
              P.controls.update();
            """
        else:
            setup += "window.__preview.fit(214, 1.0);"
        setup += "})()"
        send("Runtime.evaluate", {"expression": setup})
        time.sleep(0.9)

        shot = send("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        with open(out, "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        print("shot", out, os.path.getsize(out))
        ws.close()
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
