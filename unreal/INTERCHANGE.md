# Unreal Engine 5 — import & instancing

The same assets and material move into UE5 with no re-authoring, via **Interchange**.

## Import the mesh
1. Drag `assets/instanced/glass_led_volume.usd` (or `.glb`) into the Content Browser.
   Interchange reads the instancing and the morph animation.
2. For the hero variants use `assets/hero/GlassLED_Slab.glb` or `assets/voxel/voxel_wave.glb`.

## Material — open standard, not re-built
`core/materials/glass_openpbr.mtlx` is **OpenPBR Surface** (MaterialX 1.39). UE5 imports it
through Interchange MaterialX → **Substrate**. Enable in Project Settings:
- `Substrate` (Rendering)
- `Interchange` + `InterchangeMaterialX` (on by default in 5.7)

This gives true glass (transmission + IOR + coat) without hand-wiring a material graph.

## Instancing in UE
Three paths, pick by need:
- **ISM / HISM** — `InstancedStaticMeshComponent`: add instances from `config/scene.json`
  grid (countX·countY·countZ, spacing). Cheapest for many static-topology copies.
- **Nanite + WPO** — enable Nanite on the slab; drive the deform in the material's World
  Position Offset using the same field as `core/shaders/deform.glsl`. Per-instance phase via
  `PerInstanceRandom`. This is the live, non-baked equivalent of the web editor.
- **Niagara mesh renderer** — for thousands of fully GPU-driven instances.

## Runtime-dynamic (matches the web editor)
Recreate the editor's live behavior with a Blueprint:
1. Material: WPO = `deform.glsl` field; expose Amp/Freq/Speed/Softness as a **Material
   Parameter Collection** so one actor drives all instances.
2. `PerInstanceRandom` → phase offset, so instances shimmer instead of marching in lockstep.
3. Read `config/scene.json` at BeginPlay (JSON Blueprint Utilities) to spawn the ISM grid.

That makes UE consume the exact same `scene.json` the web editor exports — one source of truth.
