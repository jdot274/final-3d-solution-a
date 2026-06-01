"""
ue5_remote_apply.py — run inside Unreal Engine 5's Python console
(Window ▸ Python, or via the Python Editor Script Plugin).

Polls the param bridge (param_server.py) over HTTP and applies the JSON
parameters live to:
  • a Material Parameter Collection  'MPC_NeuralWave'   (global wave params)
  • a Material Instance Dynamic created from 'M_NeuralWaveGlass'  (per-mesh)

This is the UE5 side of the web → 3D bridge: edit sliders in the browser,
see the material update in the running UE5 viewport.

Setup in UE5 (once)
-------------------
1. Enable plugins: "Python Editor Script Plugin", "Remote Control API".
2. Create a Material Parameter Collection at  /Game/NeuralWave/MPC_NeuralWave
   with Scalar params: WaveSpeed, WaveAmplitude, WaveDecay, WaveFrequency,
   Displacement, IOR, Roughness, Metallic, Transmission, Thickness,
   Clearcoat, Iridescence, IridThickness, EmissionStrength, Opacity
   and Vector params: BaseColor, EmissionColor.
3. Create material  /Game/NeuralWave/M_NeuralWaveGlass  that reads the MPC.
4. Run this script.  It spawns a slate-tick poller (non-blocking).
"""

import unreal
import json
import urllib.request

BRIDGE_URL   = "http://localhost:8787/params"
MPC_PATH     = "/Game/NeuralWave/MPC_NeuralWave"
POLL_SECONDS = 0.15

# Map JSON keys → MPC parameter names (scalar vs vector)
SCALARS = {
    ("mesh", "wave_speed"):        "WaveSpeed",
    ("mesh", "wave_amplitude"):    "WaveAmplitude",
    ("mesh", "wave_decay"):        "WaveDecay",
    ("mesh", "wave_frequency"):    "WaveFrequency",
    ("mesh", "displacement"):      "Displacement",
    ("material", "ior"):           "IOR",
    ("material", "roughness"):     "Roughness",
    ("material", "metallic"):      "Metallic",
    ("material", "transmission"):  "Transmission",
    ("material", "thickness"):     "Thickness",
    ("material", "clearcoat"):     "Clearcoat",
    ("material", "iridescence"):   "Iridescence",
    ("material", "irid_thickness"):"IridThickness",
    ("material", "emission_strength"): "EmissionStrength",
    ("material", "opacity"):       "Opacity",
}
VECTORS = {
    ("material", "base_color"):     "BaseColor",
    ("material", "emission_color"): "EmissionColor",
}

_last_hash = [None]


def fetch_params():
    try:
        with urllib.request.urlopen(BRIDGE_URL, timeout=0.5) as r:
            return json.loads(r.read())
    except Exception as e:
        unreal.log_warning(f"[NeuralWave] bridge unreachable: {e}")
        return None


def apply_params(params):
    mpc = unreal.load_asset(MPC_PATH)
    if not mpc:
        unreal.log_warning(f"[NeuralWave] MPC not found at {MPC_PATH}")
        return
    world = unreal.EditorLevelLibrary.get_editor_world()
    lib   = unreal.KismetMaterialLibrary

    for (group, key), pname in SCALARS.items():
        val = params.get(group, {}).get(key)
        if val is not None:
            lib.set_scalar_parameter_value(world, mpc, pname, float(val))

    for (group, key), pname in VECTORS.items():
        v = params.get(group, {}).get(key)
        if v and len(v) >= 3:
            color = unreal.LinearColor(v[0], v[1], v[2], 1.0)
            lib.set_vector_parameter_value(world, mpc, pname, color)


def tick(delta_time):
    params = fetch_params()
    if not params:
        return
    h = hash(json.dumps(params, sort_keys=True))
    if h != _last_hash[0]:
        _last_hash[0] = h
        apply_params(params)
        unreal.log("[NeuralWave] params applied")


# Register a non-blocking editor tick
def start():
    global _handle
    _handle = unreal.register_slate_post_tick_callback(_throttled_tick)
    unreal.log("[NeuralWave] live bridge poller started")


_accum = [0.0]
def _throttled_tick(delta_time):
    _accum[0] += delta_time
    if _accum[0] >= POLL_SECONDS:
        _accum[0] = 0.0
        tick(delta_time)


if __name__ == "__main__":
    start()
