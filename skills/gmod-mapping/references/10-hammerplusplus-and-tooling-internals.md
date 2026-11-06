# Hammer, Hammer++ and the GMod toolchain: observed internals

Contents: 1. Method and trust level · 2. Installed layout · 3. Hammer++ specifics · 4. Compile chain · 5. BSP anatomy · 6. FGD layering · 7. Practical consequences

## 1. Method and trust level
Findings come from **static inspection of the user's own install** (file listing, plain-text config files, printable strings of `hammerplusplus_compiler.exe` / `hammerplusplus_dll.dll`, header parsing of shipped BSPs) plus public documentation. Nothing was run under a debugger and no code was decompiled. Treat string-derived behavior as *observed hints*; confirm in the UI before relying on it. Checked on a Garry's Mod 64-bit install with a Hammer++ data folder, 2026-11-06.

## 2. Installed layout (Windows, Steam)
| Path (under `GarrysMod/`) | Role |
|---|---|
| `bin/hammer.exe`, `bin/hammer_dll.dll` | Valve Hammer shipped with GMod |
| `bin/win64/hammerplusplus.exe` + `hammerplusplus/` | Hammer++ x64 and its data dir |
| `bin/win64/hammerplusplus/bin/hammerplusplus_compiler.exe`, `hammerplusplus_dll.dll` | compile-window runner and editor DLL |
| `bin/win64/{vbsp,vvis,vrad,studiomdl}.exe` | 64-bit compilers (preferred for big maps) |
| `bin/{garrysmod,base,halflife2}.fgd` | entity definitions |
| `bin/win64/Prefabs`, `hammerplusplus/filters` | prefabs; displacement sculpt filters |
| `sourcesdk_content/garrysmod/mapsrc` | conventional VMF source folder |
| `garrysmod/maps` | compiled BSP output |

## 3. Hammer++ specifics
- `hammerplusplus_gameconfig.txt` is a KeyValues file, one block per game: `GameData0` (FGD), `BSP/Vis/Light/MDL` (compiler paths), `MapDir`, `BSPDir`, `PrefabDir`, `DefaultTextureScale` (0.25), `DefaultLightmapScale` (16), `DefaultSolidEntity` (`func_detail`), `CordonTexture` (`tools/toolsskybox`).
- `hammerplusplus_fgd.fgd` is **mandatory** and version-checked (`@version(9)` observed). It uses `@ExtendClass` to *append* helpers/keyvalues to classes defined in other FGDs (light preview, fog controller, sky camera) without editing Valve's FGDs; extension classes are parsed last.
- Autosave: `*.vmf_autosave`, settings `AutosaveEnabled/Time/MaxPerMap/MaxSpace`; crash recovery file `<name>_crash.vmf_autosave`.
- The compiler runner passes `-game <gamedir> <path>\<file>`; strings show support for `-onlyents`, `-fast`, `-threads`, `-nop4`, `-WaitForKeypress`, `-vproject`, `-MaterialExcludeDir`.
- "Run map" launches the game with `-game <gamedir> +map <file> -steam -insecure`.

## 4. Compile chain
`vmf -> vbsp (geometry, entities, leak check) -> vvis (PVS, optional) -> vrad (lighting) -> bsp`. A leak makes vvis/vrad pointless: read the vbsp output for `leaked` first. `-onlyents` re-injects entities only (fast iteration on I/O, no geometry change). Cubemaps are baked in game afterwards (`buildcubemaps`) and stored in the BSP; do not rename the BSP afterwards. See `05-optimisation-et-compilation.md`.

## 5. BSP anatomy (v20, what the MCP reads)
Header: `VBSP` magic, int version, 64 lump directory entries (offset, length, version, fourCC), map revision. Useful lumps: ENTITIES(0, text), PLANES, VERTEXES, VISIBILITY(4, first int = cluster count), NODES, TEXINFO, FACES(7), LIGHTING(8) / LIGHTING_HDR(53), LEAFS(10; 56-byte records when lump version is 0, else 32), MODELS(14), BRUSHES(18), DISPINFO(26), GAME_LUMP(35, holds `sprp` static props), PAKFILE(40, a ZIP of embedded content), CUBEMAPS(42), OVERLAYS(45). The MCP compares counts to commonly cited per-lump limits (reference values: verify per branch).

Reference profiles of the maps shipped with GMod are in `knowledge/profiles/`: `gm_construct` is 35 MB with 676 vis clusters, ~9.5k faces, 182 static props and 1227 entities (815 of them `info_node` AI nodes); `gm_flatgrass` has 1087 clusters, ~2.9k faces and a large lightmap/pak share.

## 6. FGD layering
`garrysmod.fgd` builds on `base.fgd` and `halflife2.fgd`; Hammer++'s FGD extends them. `@BaseClass` chains carry keyvalues/inputs/outputs (e.g. `Targetname` provides `Kill`, `AddOutput`, `FireUser1..4`). The MCP's `fgd_entity` resolves the full chain so entity keys are never guessed.

## 7. Practical consequences
- Verify entity keys with `fgd_entity` before writing VMF text.
- Use the 64-bit compilers from `bin/win64` for big RP maps.
- Use `-onlyents` for logic iteration; full compile only after geometry changes.
- Keep VMFs under `mapsrc`, let Hammer++ autosave, back up before experiments.
