# Versions — all kept separate, none overwritten

Every distinct build lives as its own file/asset. Nothing is replaced when a new one is added.

| # | Version | Real-time editor | Baked assets | Notes |
|---|---|---|---|---|
| 1 | **Layered Slab** (hero) | — | `assets/hero/GlassLED_Slab.{glb,usdz,abc,blend}` | 4 stacked glass layers, 40-frame soft-body morph |
| 2 | **Driver Variants** | — | `assets/variants/LEDVolume_{Waves,Heightmap,Video}.{glb,usdz,abc}` | math waves / image heightmap / video drivers |
| 3 | **Instanced Volume** | `web/index.html` | `assets/instanced/glass_led_volume.{glb,usd,usdz,abc}` | GPU InstancedMesh grid · glTF EXT_mesh_gpu_instancing · bridge-wired |
| 4 | **Single Block** | `web/cube.html` | (bake via `blender/build_glass_led.py` retargeted) | one solid subdivided glass rectangle, triplanar LED |
| 5 | **Voxel Wave** (from parallel build) | — | `assets/voxel/voxel_wave.glb` | 1600-bar LED-volume, OpenPBR glass |
| 6 | **Neural Wave** (from parallel build) | `viewers` (n/a) | `assets/voxel/neural_wave_animated.{glb,abc}`, `neural_wave.glb` | morph-animated glass sheet + Alembic |

**Landing hub:** `web/hub.html` links them all.

## Rule
When iterating, add a **new** file (e.g. `web/v5_xxx.html`, `assets/<name>/`) — never overwrite an
existing version. The bridge (`bridge/`) and core (`core/`) are shared infrastructure used by all.
