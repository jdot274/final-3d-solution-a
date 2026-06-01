#!/usr/bin/env python3
"""
param_server.py — live JSON/HTTP parameter bridge for the neural wave asset.
Zero dependencies (Python stdlib only).

Holds the single source of truth for mesh + material parameters and lets any
client read/update them over HTTP.  Pushes live updates to subscribers via
Server-Sent Events (SSE).  Optionally mirrors every change to an Unreal Engine
5 Remote-Control endpoint so a running UE5 editor updates in real time.

Endpoints
---------
  GET  /params         → current params as JSON
  PUT  /params         → merge JSON body into params, broadcast change
  POST /params/reset   → reset to schema defaults
  GET  /schema         → the JSON schema (wave_params_schema.json)
  GET  /events         → SSE stream; emits "param" events on every change
  GET  /               → serves control_panel.html (the web editor)

Usage
-----
  python3 param_server.py                       # localhost:8787
  python3 param_server.py --port 9000
  python3 param_server.py --forward-ue5 http://localhost:30010
                                                # mirror to UE5 Remote Control

Push params from anywhere
-------------------------
  curl -X PUT localhost:8787/params \\
       -H "Content-Type: application/json" \\
       -d '{"material": {"ior": 1.7, "roughness": 0.02},
            "mesh": {"wave_speed": 3.5}}'
"""

import argparse, json, os, threading, queue, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE        = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "wave_params_schema.json")
PANEL_PATH  = os.path.join(HERE, "control_panel.html")

# ── STATE ─────────────────────────────────────────────────────────────────────
_lock        = threading.Lock()
_subscribers = []          # list[queue.Queue] for SSE
FORWARD_UE5  = None        # set from --forward-ue5


def load_defaults():
    """Build the default param dict from the JSON schema."""
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    out = {}
    for group in ("mesh", "material"):
        out[group] = {}
        props = schema["properties"][group]["properties"]
        for k, spec in props.items():
            out[group][k] = spec.get("default")
    out["layers"] = schema["properties"]["layers"]["default"]
    return out


PARAMS = load_defaults()


# ── HELPERS ───────────────────────────────────────────────────────────────────
def deep_merge(dst, src):
    """Recursively merge src into dst (dicts); lists/scalars overwrite."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def broadcast(params):
    """Push the new params to every SSE subscriber + UE5 (if configured)."""
    payload = json.dumps(params)
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except Exception:
            dead.append(q)
    for q in dead:
        if q in _subscribers:
            _subscribers.remove(q)
    if FORWARD_UE5:
        threading.Thread(target=forward_to_ue5, args=(params,),
                         daemon=True).start()


def forward_to_ue5(params):
    """
    Mirror params to a UE5 Remote Control HTTP endpoint.
    Sets each flagged param on a Material Parameter Collection asset named
    'MPC_NeuralWave' via the built-in Remote Control PUT API.
    """
    base = FORWARD_UE5.rstrip("/")
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    def each(group):
        props = schema["properties"][group]["properties"]
        for k, spec in props.items():
            val = params.get(group, {}).get(k)
            if val is None:
                continue
            yield spec.get("mpc") or spec.get("param") or k, val, spec.get("ue5")

    for group in ("mesh", "material"):
        for name, val, kind in each(group):
            # UE5 Remote Control: call SetScalarParameterValue /
            # SetVectorParameterValue on the MPC instance.
            func = ("SetVectorParameterValue" if kind == "vector"
                    else "SetScalarParameterValue")
            if kind == "vector":
                value = {"R": val[0], "G": val[1], "B": val[2], "A": 1.0}
            else:
                value = val
            body = json.dumps({
                "objectPath": "/Game/NeuralWave/MPC_NeuralWave.MPC_NeuralWave",
                "functionName": func,
                "parameters": {"ParameterName": name, "ParameterValue": value},
                "generateTransaction": True,
            }).encode()
            try:
                req = urllib.request.Request(
                    base + "/remote/object/call", data=body,
                    headers={"Content-Type": "application/json"}, method="PUT")
                urllib.request.urlopen(req, timeout=0.5)
            except Exception as e:
                print(f"[UE5] {name}: {e}")


# ── HTTP HANDLER ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,PUT,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if body:
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            if os.path.exists(PANEL_PATH):
                with open(PANEL_PATH, "rb") as f:
                    self._send(200, f.read(), "text/html")
            else:
                self._send(404, b'{"error":"control_panel.html missing"}')
        elif self.path == "/params":
            with _lock:
                self._send(200, json.dumps(PARAMS).encode())
        elif self.path == "/schema":
            with open(SCHEMA_PATH, "rb") as f:
                self._send(200, f.read())
        elif self.path == "/events":
            self._sse()
        else:
            self._send(404, b'{"error":"not found"}')

    def do_PUT(self):
        if self.path == "/params":
            n = int(self.headers.get("Content-Length", 0))
            try:
                patch = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError as e:
                self._send(400, json.dumps({"error": str(e)}).encode()); return
            with _lock:
                deep_merge(PARAMS, patch)
                snapshot = json.loads(json.dumps(PARAMS))
            broadcast(snapshot)
            self._send(200, json.dumps({"ok": True, "params": snapshot}).encode())
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        if self.path == "/params/reset":
            global PARAMS
            with _lock:
                PARAMS = load_defaults()
                snapshot = json.loads(json.dumps(PARAMS))
            broadcast(snapshot)
            self._send(200, json.dumps({"ok": True, "params": snapshot}).encode())
        else:
            self._send(404, b'{"error":"not found"}')

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        q = queue.Queue()
        _subscribers.append(q)
        # send current state immediately
        with _lock:
            init = json.dumps(PARAMS)
        try:
            self.wfile.write(f"event: param\ndata: {init}\n\n".encode())
            self.wfile.flush()
            while True:
                payload = q.get()
                self.wfile.write(f"event: param\ndata: {payload}\n\n".encode())
                self.wfile.flush()
        except Exception:
            pass
        finally:
            if q in _subscribers:
                _subscribers.remove(q)

    def log_message(self, *a):
        pass  # quiet


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    global FORWARD_UE5
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--forward-ue5", default=None,
                    help="UE5 Remote Control base URL, e.g. http://localhost:30010")
    args = ap.parse_args()
    FORWARD_UE5 = args.forward_ue5

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"╔{'═'*54}╗")
    print(f"║  Neural Wave param bridge  →  http://localhost:{args.port}")
    print(f"║  Web editor : http://localhost:{args.port}/")
    print(f"║  Params API : GET/PUT  http://localhost:{args.port}/params")
    print(f"║  Live SSE   : http://localhost:{args.port}/events")
    if FORWARD_UE5:
        print(f"║  UE5 mirror : {FORWARD_UE5}")
    print(f"╚{'═'*54}╝")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
