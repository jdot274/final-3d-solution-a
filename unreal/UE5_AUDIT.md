# UE5 resource audit — what's already available (use, don't rebuild)

## Studio HDRIs (engine) — for glossy glass reflections (the mood-board look)
- `/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1`  ← studio env, best for product renders
- `/Engine/EditorMaterials/AssetViewer/T_ClearSky`
- `/Engine/MapTemplates/Sky/DaylightAmbientCubemap`, `SunsetAmbientCubemap`, `Desert_Outer_HDR`
Applied: SkyLight source = SLS_SPECIFIED_CUBEMAP = EpicQuadPanorama + a SphereReflectionCapture.

## Glass materials already in the project (43 found) — reusable
- `/Game/M_Glass1`, `M_Glass1_2..6`, `/Game/FrostedGlass`, `/Game/M_Glass_Dirt`, ...

## Material functions in project — reuse for the LED/pixel grid + triplanar
- `/Game/MF/MF_2DGrid`, `MF_TripleGrid`, `MF_WorldGrid`  (grid / pixel cells)
- `/Game/MF/MF_NormalStrength`, `/Game/MF/WorldAlignedTextureMip` (triplanar)

## Plugins enabled (relevant)
- NaniteDisplacedMesh (Nanite tessellation displacement)
- AnimToTexture (VAT), MediaPlate (video textures), GeometryScripting (procedural mesh)
- Interchange + InterchangeOpenUSD + USDImporter (import the unified GLB/USD)

## Best approach (decided)
ONE connected mesh (UnifiedGlassLED) → import as Nanite static mesh → opaque ClearCoat
blue emissive + fresnel + grid functions + studio-HDRI reflections + WPO wave.
(Opaque clearcoat = Nanite-compatible AND glossy; translucent is NOT Nanite-compatible.)

## NvPresent64 crash — definitive fix: run editor on VULKAN
The crash is the NVIDIA **DirectX** present hook (D3D12 only). Launch the editor with
`-vulkan` (config now has +VulkanTargetedShaderFormats=SF_VULKAN_SM6). Vulkan SM6 keeps
Nanite + Lumen but bypasses the DX present path = no NvPresent64 crash.
  UnrealEditor.exe MyProjectTests.uproject -vulkan
