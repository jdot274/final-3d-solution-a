# SPIN — Full Handoff & Tech Stack Implementation

**Read this first.** It tells any agent exactly what this project is, the full tech stack,
where everything lives, what's done, and how to continue.

---

## 1. What this is
A **dynamic blue glassy-reflective animated LED volume + tennis (SPIN) scene**, delivered
across web, portable 3D (GLB/USDZ), and Unreal Engine 5 — built on open standards so the
same look moves between tools with no reinvention.

## 2. The pipeline (THE definitive architecture)
```
ASSET SOURCES                  HUB: BLENDER (look-dev + render)        OUTPUTS
Vectary    ─┐  export GLB/USDZ                                      ┌─ UE5  (OpenUSD/MaterialX → Substrate, Nanite, MRQ)
Drive/OneDrive ─┼────────────►  SPIN_Master.blend (organized) ──────┼─ Web  (three.js, deployed)
Adobe Substance ┘  .sbsar→maps   collections · glass mats · lights  └─ AR   (USDZ / GLB)
                                  · cameras · render · export USD
```
**Blender is the hub.** Assets flow in from the libraries; the finished look flows out to
UE5 + web + AR via **OpenUSD + MaterialX + GLB/USDZ**. Blender is reliable for rendering;
UE5 is the game/runtime layer (import the USD, don't rebuild).

## 3. Full tech stack (implemented)
| Layer | Tech | Where |
|---|---|---|
| Real-time web | three.js (WebGL/Vulkan-class), InstancedMesh, GLSL deform | `web/` (live: https://final-3d-deploy.vercel.app) |
| Portable 3D | glTF 2.0 (GLB), OpenUSD (.usdc/.usdz), Alembic | `assets/` |
| Materials | Principled BSDF / OpenPBR / **MaterialX 1.39** | `core/materials/*.mtlx`, Blender glass mats |
| Look-dev + render | **Blender 5.1 EEVEE Next** (raytraced) | `blender/`, `renders/` |
| Engine | **UE5.7** — Nanite, Lumen, ClearCoat glass, Interchange(USD/MaterialX), Movie Render Queue, HDRIBackdrop | `unreal/`, project `/Game/FinalSolution/` |
| Bridge | web→UE5 JSON (param_server) | `bridge/` |
| Source control | Git + **Git LFS** | GitHub: jdot274/final-3d-solution-a |

## 4. How to bring in Vectary & Adobe Substance files
### Vectary
1. In Vectary: open the project → **Export → GLB** (or USDZ).
2. Save to Drive/OneDrive/Downloads.
3. In Blender: `File → Import → glTF 2.0 (.glb)`. (Headless: `bpy.ops.import_scene.gltf(filepath=...)`.)
Vectary has no API/MCP here, so it's export-GLB → import. The court already came this way
(`OneDrive/.../TennisCourt.glb`).

### Adobe Substance (.sbsar / material)
Blender can't read `.sbsar` natively. Two supported routes:
- **A. Adobe Substance 3D Add-on for Blender** (official): install it, then
  `File → Import → Substance (.sbsar)` loads the parametric material directly. Best fidelity.
- **B. Bake-and-import (no add-on):** in Substance 3D Sampler/Painter/Designer, export the
  texture set (basecolor / roughness / metallic / normal / height as PNG), then in Blender
  wire them into a Principled BSDF (or a MaterialX graph). Portable to UE5 via MaterialX.
Your Substance assets are on Drive: folders `SBSAR`, `0000AdobeSubstanceMaterials`,
`SubstanceLibrary` (×3); UE material-instances `MI_SBSAR_AcidEtchedGlass`,
`MI_SBSAR_3DGradient`, `MI_SBSAR_AnodizedAluminium`. Point the next step at a specific
`.sbsar` to apply it to the court glass.

## 5. Your assets (audited)
- **Court (portable):** `OneDrive/EverythingExisting/1New Ready Models OneDrive/TennisCourt.glb` ✅ used
- **Racket:** `OneDrive/EverythingExisting/TennisRacket v1.fbx`
- **Ball:** `OneDrive/.../tennis_ball.glb`, `TennisBall.usdz` (59 MB)
- **Arena:** `OneDrive/.../o2_arenalondon.glb`
- **Drive:** UE `.uasset` backups (CourtBP, Racket22, RacketSurroundLEDLightsBP, TennisBall600…),
  Substance libraries, `FresnelNeonDotSphere.usdz`. NOTE: Drive "GLB" folders contain UE
  `.uasset` (not portable) — use the OneDrive GLB/FBX for Blender.

## 6. Key files (organized)
```
HANDOFF.md  (this)            README.md   VERSIONS.md
web/        index.html (master/instanced) · cube · layered · neural viewers · hub
blender/    build_master_blend.py  ← THE scene · build_real_court.py · build_lookdev_pipeline.py
            build_blender_hero.py · build_unified_glass.py · build_textures.py
unreal/     build_ue_spin_level.py · build_ue_arena_bp.py · build_ue_master_aaa.py
            UE5_AUDIT.md (plugins+HDRIs) · INTERCHANGE.md · AAA_PLAYBOOK.md
core/       materials/*.mtlx · shaders/deform.glsl       config/ scene.json + presets
bridge/     param_server.py · control_panel.html · ue5_remote_apply.py
assets/     scene/SPIN_Master.blend (+ .usdc/.glb/.usdz)  unified/ hero/ variants/ voxel/ textures/
renders/    SPIN_master_final.png · SPIN_realcourt_final.png · hero shots
```
**Big binaries** (SPIN_Master.* are 96–159 MB because the court is high-poly) are gitignored —
regenerate with the scripts. Smaller assets are in Git LFS.

## 7. Current state
- ✅ **Web** built + deployed (Vercel).
- ✅ **Blender master** scene with your real court/racket/ball, organized, rendered, USD-exported.
- ✅ **UE5** assets built: `BP_SPIN_Arena` (level-independent reusable), `M_GlassLED`,
  `MPC_GlassLED`, `L_SPIN_Black`, textures. **Blocked render verification** by the NVIDIA
  DX12 `NvPresent64` crash — **fix: run editor with `-vulkan`** (config has Vulkan SM6).
- ✅ Pipeline + handoff documented.

## 8. How to continue (next agent)
1. **Open** `assets/scene/SPIN_Master.blend` — all assets/lights/cameras in named collections.
2. **Refine look** in Blender (glass, lighting, HDRI, post) — it renders reliably.
3. **Apply a Substance** glass: import a `.sbsar` (route A or B above) onto `M_Court`.
4. **Export** USD via the script → **import into UE5** (Interchange; MaterialX→Substrate).
5. **UE5 render:** launch editor `-vulkan` (avoids NvPresent64), use **Movie Render Queue**
   (NOT HighResShot — that was the blind-render failure mode) for the cinematic.
6. **Web/AR:** GLB/USDZ already export from the same scene.

## 9. Hard-won lessons (don't repeat)
- `NvPresent64` crash = NVIDIA **DX12** present hook → run UE on **Vulkan**.
- **HighResShot over the bridge does NOT converge** to a good render — use **Movie Render Queue**.
- **Nanite ≠ translucent** — for Nanite use opaque **ClearCoat** glass.
- Drive "GLB" folders are UE `.uasset`, not portable — use OneDrive GLB/FBX for Blender.
- Toggling UE plugins + "Restart Now" kills the MCP bridge each time.
