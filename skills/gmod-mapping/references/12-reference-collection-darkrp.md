# Reference collection: "MAP POUR DARK RP" (36 maps)

Source: https://steamcommunity.com/sharedfiles/filedetails/?id=1719226443 (captured 2026-11-06). Machine-readable manifest: `knowledge/reference_maps.json`. **Titles and authors only; third-party map files are not bundled.**

Families (versions of one map are directly comparable): Rockford (10 entries incl. French v3b–v5 alpha), EvoCity (2), UnionCity/SouthSide by Fishke (3), Downtown (`rp_downtown_triton`, `_v2`, `Rp_Downtown_2017`), Uptown (v4 day, v4u 2019), NewExton (2), Pines City (2), plus Florida, Paralake, World, EastCoast, Littletown, Hollywood, Truenorth, Retricity, Starisland, Riverden, Ranoxcity, Chaos City.

## How to study them without redistributing them
1. Subscribe in Steam; the file lands in `steamapps/workshop/content/4000/<id>/` (usually a GMA: extract with `gmad.exe extract` or gmpublisher).
2. Run `bsp_analyze` / `rp_scorecard` on each BSP and save the JSON under `knowledge/profiles/<map>.json` (numbers only, no assets).
3. Compare families: face count, clusters/leaves, static props, pak size, entity classes, I/O health, naming ratio.
4. For layout use in-game top-down screenshots and `mat_wireframe`; record districts, landmarks, loops.

## Checklist
- Block structure and road spine; landmark per district; chokepoints; vertical layers.
- Interior/exterior split; where doors + areaportals cut vis; pak size vs workshop dependency.
- Door naming scheme; trigger zones (safe zones, bank/vault, jail); teleport pairs.
- Performance: static props, leaf/cluster counts, `prop_dynamic` abuse, lightmap size.
Do not assert facts about a specific map from memory: profile it.

## Measured profiles so far (3 of 36; numbers from `knowledge/profiles/`, 2026-11-06)
| Map | BSP | Faces | Vis clusters | Static props | Entities (named) | Cubemaps | Areaportals | Embedded pak | I/O links (broken) | Naming ratio | Closest to a limit* |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rp_florida_v2 | 59 MB | 33.3k | 4309 | 5454 | 2976 (418) | 3 | 25 | 0.4 MB | 246 (2) | 0.97 | BRUSHES 96% |
| rp_truenorth_v1a | 343 MB | 28.1k | 3512 | not decoded | 3450 (676) | 286 | 103 | 316 MB | 170 (0) | 0.12 | DISPINFO 98% |
| rp_unioncity_day | 749 MB | 30.6k | 8310 | 3665 | 2856 (735) | 361 | 227 | 670 MB | 490 (1) | 0.29 | BRUSHES 98% |
\*vs commonly cited reference limits (verify per branch). Static props for Truenorth are not decoded (compressed game lump).

## Lessons these three suggest (observations, not rules)
- Big RP maps cluster at the same ceilings: brush count (~8k) and displacements/texinfo/overlays. Budget these early; push detail into `func_detail`, `prop_static` and displacements sparingly.
- Light entities dominate entity counts (1000+ `light`/`light_spot`); props and doors come next. Entities beyond lights are mostly doors (200-360 `prop_door_rotating`/`func_door_rotating`) which is what DarkRP door ownership needs.
- Visibility strategy differs: Florida 25 areaportals + 3 cubemaps (cheap, flat reflections); UnionCity 227 areaportals + 361 cubemaps (heavy interior culling and reflections, at the cost of a 749 MB file mostly embedded content). A 300-700 MB BSP is a download/join-time problem: prefer a Workshop addon for content.
- Logic is door/light centric (few hundred I/O links; `logic_auto`, `logic_relay`, `logic_timer`, `path_track` for vehicles). Naming discipline varies a lot (0.12 to 0.97 of named entities sharing a prefix): treat Florida's scheme as the model.

## Still to profile (need the file locally)
32 collection items are not on this machine. IDs are in `knowledge/reference_maps.json`. Subscribe or download them, then: `python mcp/profile_gma.py knowledge/profiles <path-to-gma-or-bin>`.
