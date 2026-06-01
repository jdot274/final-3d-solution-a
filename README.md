# final-3d-solution-a — Dynamic Glass LED Volume

A fully dynamic, **engine-agnostic** glassy LED volume mesh: real-time in the browser,
portable as baked 3D files, defined with open-standard materials — runnable **outside UE5
or inside it**. One JSON config drives both the live web preview and the baked exports.

![status](https://img.shields.io/badge/status-working-brightgreen) ![engine](https://img.shields.io/badge/UE5-Interchange%20ready-blue)

---

## What's here

```
web/index.html          Real-time three.js previewer — GPU deformation, live JSON,
                        glass + LED pixels + drag-drop video. The "completely dynamic" view.
materials/glass_led.mtlx  Open-standard MaterialX 1.39 glass material (OpenUSD / UE Interchange / MaterialXView).
scripts/
  build_glass_led.py    JSON-driven Blender builder -> GLB (morph) + USDZ + ABC + .blend.
  build_led_volume.py    3-driver variant builder (math waves / heightmap seq / video).
  preview_open.py        Opens the .blend in Blender with material-preview + autoplay.
config/
  glass_led_config.json  The single source of truth (layers, glass, LED, motion params).
  manifest.json          Build record.
assets/
  GlassLED_Slab.{glb,usdz,abc,blend}   Hero: 4-layer glass slab, soft-body wobble.
  variants/LEDVolume_{Waves,Heightmap,Video}.{glb,usdz,abc}
```

## Quick start

**Live web previewer (most dynamic):**
```bash
cd web && python -m http.server 8791
# open http://localhost:8791  — drag = orbit, top-right panel = live params
```
Switch driver (softbody / waves / heightmap / video), tune glass & LED, **Export JSON**,
or **Load video → LED** to drive the emissive from any local clip in real time.

**Re-bake the files from a config:**
```bash
blender --background --python scripts/build_glass_led.py
# reads config/glass_led_config.json, writes GLB / USDZ / ABC / .blend
```

**Open in tools:**
- `.glb` → any glTF viewer, three.js, Babylon, Windows 3D Viewer, **UE5 Interchange**
- `.usdz` → AirDrop to iPhone → animated in AR Quick Look
- `.abc` → Alembic master cache for Houdini / Maya / Blender
- `.mtlx` → MaterialXView, OpenUSD (UsdMtlx), UE5 Interchange

## Technical specs (verified in-file)

| Property | Value |
|---|---|
| Glass | `KHR_materials_transmission` + IOR 1.45, double-sided, blue emissive LED |
| Hero mesh | 4 stacked layers · 18,576 verts · 40 morph frames/layer · 4 animations |
| Deformation | edge-pinned soft-body jelly wobble (procedural, looping) |
| Standards | glTF 2.0 · OpenUSD · MaterialX 1.39 · Alembic |

## The portability model

```
web (three.js, live)  ──┐
MaterialX / OpenUSD   ──┼──►  one JSON config  ──►  GLB / USDZ / ABC
Blender Python (bake) ──┘                            └─► UE5 via Interchange
```

Built on open standards, so there is no engine lock-in — the same material and mesh
move between the browser, DCC tools, and Unreal.

## Notes
- The baked files capture one config's animation (portable snapshots).
  *Runtime-dynamic* behavior lives in `web/index.html` (and a UE blueprint, if built).
- Glass transmission renders inconsistently in lightweight viewers; the web previewer
  and UE/Blender show it correctly.
