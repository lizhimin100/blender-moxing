"""
shoot.py —— 用 Chrome DevTools Protocol 抓预览台单帧（等待 READY 后再截）

用法：
  python build/shoot.py <url> <out.png> [--w 1400] [--h 950] [--timeout 90]
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9222
PROFILE = os.path.join(os.path.dirname(__file__), "..", ".workbuddy", "tmp", "chrome-profile")


def http(path, method="GET"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def main():
    url = sys.argv[1]
    out = sys.argv[2]
    w = int(sys.argv[sys.argv.index("--w") + 1]) if "--w" in sys.argv else 1400
    h = int(sys.argv[sys.argv.index("--h") + 1]) if "--h" in sys.argv else 950
    timeout = float(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 90

    proc = subprocess.Popen([
        CHROME, "--headless=new", "--enable-unsafe-swiftshader",
        f"--remote-debugging-port={PORT}", "--remote-allow-origins=*", f"--user-data-dir={PROFILE}",
        f"--window-size={w},{h}", "--hide-scrollbars", "--no-first-run",
        "--disable-extensions", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                http("/json/version")
                break
            except Exception:
                time.sleep(0.2)
        tab = http("/json/new?about:blank", "PUT")
        ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=30)
        n = [0]

        def send(method, params=None):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": method, "params": params or {}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == n[0]:
                    return msg.get("result", {})

        send("Page.enable")
        send("Runtime.enable")
        send("Network.enable")
        send("Network.setCacheDisabled", {"cacheDisabled": True})
        send("Page.navigate", {"url": url})
        t0 = time.time()
        ready = False
        while time.time() - t0 < timeout:
            r = send("Runtime.evaluate", {"expression": "document.title", "returnByValue": True})
            if r.get("result", {}).get("value") == "READY":
                ready = True
                break
            time.sleep(0.4)
        if not ready:
            print("WARN: 未在超时内 READY，仍尝试截图")
        time.sleep(0.6)
        shot = send("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        with open(out, "wb") as f:
            f.write(base64.b64decode(shot["data"]))
        print(("READY " if ready else "TIMEOUT ") + out, os.path.getsize(out))
        ws.close()
    finally:
        proc.terminate()
        try:
            proc.wait(5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
