# UE5 Master Solution — every plugin mapped to its job

Run `build_ue_master_solution.py` from **Tools → Execute Python File** once the editor is
stable (after the clean driver reinstall). Each plugin we audited has a role:

## Import & data
| Plugin | Role |
|---|---|
| **Interchange + InterchangeOpenUSD** | Bring in the master USD (all 1,212 assets) as a live USD Stage |
| **glTFRuntime** | Runtime GLB import (load assets in-game, no editor import) |
| **DatasmithRuntime** | Runtime scene import |
| **JsonBlueprintUtilities** | Read/write `config/scene.json` in Blueprints |
| **HttpBlueprint** | HTTPS calls from Blueprints (the web↔UE bridge) |
| **BlueprintFileUtils / EditorScriptingUtilities** | File I/O + editor automation |

## Geometry & procedural
| Plugin | Role |
|---|---|
| **Nanite** | Virtualized geometry on all imported meshes (auto-performance) |
| **GeometryScripting** | Procedural mesh in BP/Python (the glass cell volume) |
| **PCG + PCGBiomeCore** | Procedural level generation / scatter the scene |
| **MeshModelingToolset** | In-editor mesh editing |
| **Mutable** | Runtime-customizable meshes |

## Materials & rendering
| Plugin | Role |
|---|---|
| **Substrate** | Layered glass material (the real glossy glass) |
| **Lumen** | Real-time GI + reflections (no baking) |
| **MaterialX (Interchange)** | Import the `.mtlx` glass → Substrate |
| **Composure** | Compositing passes |

## Physics & FX
| Plugin | Role |
|---|---|
| **ChaosFlesh / ChaosCloth / Fracture** | Real soft-body / cloth / destruction |
| **Niagara + NiagaraFluids + NiagaraNanite** | Particle FX, fluids, energy |

## Cameras, cinematics, output
| Plugin | Role |
|---|---|
| **CineCamera + Sequencer** | Cinematic cameras + animation |
| **MovieRenderPipeline (Movie Render Queue)** | The AAA cinematic render (replaces HighResShot) |
| **RenderGrid** | Batch render variations |
| **Image Plate / Media Plate** | Reference images / video on planes |

## Connectivity (your "LiveLink / Blender LiveLink" ask)
| Plugin | Role |
|---|---|
| **LiveLink + LiveLinkControlRig** | Stream animation/data from external apps (incl. the **Blender LiveLink** add-on) into UE live |
| **Pixel Streaming** | Stream the finished UE game to a **browser** = web-playable UE (the unifier) |
| **Remote Control + RemoteControlWebInterface** | Drive UE params from a web panel (pairs with `bridge/`) |

## The one prerequisite
UE 5.7 is unstable on the **RTX 5070 Ti (50-series)** with the current driver. **Clean
driver reinstall** (NVIDIA App → Drivers → ⋯ → Reinstall → "Perform a clean installation")
→ editor stays open → run the script above → master solution assembles.
