# AAA Playbook — using this stack to make AAA-quality things

This repo is the **engine-agnostic core** (real-time web + portable open-standard assets +
the live param bridge). That core is the right *foundation*, but **AAA visual fidelity is
earned in the engine**. Here is the honest division of labor and the path.

## What "AAA" actually needs — and where each lives

| AAA requirement | Where it comes from | Status here |
|---|---|---|
| Real-time authoring / iteration | `web/` editors (three.js) | ✅ done |
| Portable assets (AR, share, DCC) | `assets/` GLB/USDZ/ABC | ✅ done |
| Live param control across tools | `bridge/` (HTTP/JSON → MPC) | ✅ done |
| **Nanite** micro-detail geometry | Unreal Engine 5 | ⬜ UE leg (not built) |
| **Lumen** GI + reflections | Unreal Engine 5 | ⬜ UE leg |
| **Substrate** layered glass (from OpenPBR) | UE5 Interchange ← `core/materials/glass_openpbr.mtlx` | ⬜ import step |
| **Chaos Flesh** true soft-body | UE5 (plugin) | ⬜ UE leg (replaces procedural wobble) |
| Packaged shippable build | UE5 | ⬜ UE leg |

**Conclusion:** keep authoring/preview/export outside UE (fast, portable). Bring the result
into UE for the AAA *render + physics + ship*. The bridge already connects them.

## The AAA pipeline (end to end)

1. **Author** in `web/index.html` — design the look live; drag sliders; tune glass/LED/motion.
2. **Export** `scene.json` (the single source of truth) + a web/Blender GLB.
3. **Bake** production geometry: `blender/build_instanced.py` → GLB(EXT_mesh_gpu_instancing) + USD.
4. **Import into UE5** (`unreal/INTERCHANGE.md`):
   - USD/GLB → mesh; enable **Nanite**.
   - `glass_openpbr.mtlx` → **Substrate** glass via Interchange MaterialX (no hand-wiring).
   - Deformation → material **World Position Offset** using `core/shaders/deform.glsl`;
     per-instance variation via `PerInstanceRandom`.
   - Many copies → **ISM/HISM** or **Niagara** mesh renderer.
5. **Go live**: run `bridge/param_server.py`; `bridge/ue5_remote_apply.py` pushes the same
   `scene.json` params into a UE5 **Material Parameter Collection** — tune the AAA scene from
   the browser in real time.
6. **Real physics** (optional): enable **Chaos Flesh**, convert the slab to a flesh asset →
   true soft-body, then bake back to Alembic for portable AR if needed.
7. **Ship**: package the UE5 project; the portable GLB/USDZ remain for web/AR distribution.

## Honest gaps to close for true AAA
- **Procedural wobble ≠ real soft-body.** Closed only by the UE Chaos Flesh step (6).
- **Glass in lightweight viewers** renders inconsistently; UE Substrate / the web editor are accurate.
- **LED-pixel fidelity** is best in `assets/voxel/voxel_wave.glb` (geometric pixels) — use that mesh
  as the AAA base when you want discrete emitters rather than a texture grid.
- **`textures/` layers** (heightmap/normal/flipbook) from the parallel build are not on disk; they can
  be regenerated from the math in `blender/` if needed.

## One-line recommendation
**Outside-UE authors and previews; UE5 renders, simulates, and ships.** This repo is the
authoring core; the UE leg (steps 4–7) is what turns it AAA. Build that leg next.
