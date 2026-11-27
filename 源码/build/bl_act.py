"""bl_act.py -- drive the installed DSH Blender Bridge addon over its TCP socket (9876).

    python build/bl_act.py act path/to/script.py
    python build/bl_act.py expr "print(bpy.app.version_string)"
    python build/bl_act.py ping
"""
import json
import socket
import sys
import time

HOST, PORT = "127.0.0.1", 9876


def call(payload, timeout=3600.0):
    t0 = time.time()
    with socket.create_connection((HOST, PORT), timeout=20) as s:
        s.settimeout(timeout)
        s.sendall(json.dumps(payload).encode("utf-8"))
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode("utf-8")), time.time() - t0
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    return json.loads(buf.decode("utf-8")), time.time() - t0


def run(code, label="code"):
    try:
        res, dt = call({"type": "execute_code", "params": {"code": code}})
    except Exception as exc:
        print("[FAIL %s] transport: %r" % (label, exc), file=sys.stderr)
        return 1
    out = ((res.get("result") or {}).get("result") or "").strip()
    if out:
        print(out)
    if res.get("status") != "success":
        print("[FAIL %s] %s" % (label, res.get("message")), file=sys.stderr)
        return 1
    print("[ok %s] %.1fs" % (label, dt))
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ping"
    if cmd == "ping":
        res, dt = call({"type": "ping"})
        print("ping:", res.get("status"), res.get("result"), "%.2fs" % dt)
        return 0 if res.get("status") == "success" else 1
    if cmd == "act":
        with open(sys.argv[2], encoding="utf-8") as f:
            return run(f.read(), sys.argv[2].split("/")[-1])
    if cmd == "expr":
        return run(sys.argv[2], "expr")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
