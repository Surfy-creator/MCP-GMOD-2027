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

## Corpus statistics (37 profiled BSPs, all 36 collection items; `knowledge/profiles/SUMMARY.json`)
| Metric | min | p25 | median | p75 | max |
|---|---|---|---|---|---|
| BSP size (MB) | 52 | 99 | 187 | 316 | 935 |
| Faces | 21.4k | 27.1k | 31.7k | 33.5k | 37.9k |
| Vis clusters | 1379 | 3846 | 4887 | 7658 | 11112 |
| Entities | 1122 | 2101 | 2749 | 3129 | 5189 |
| Static props | 1149 | 2214 | 3418 | 3940 | 6825 |
| Cubemaps | 0 | 88 | 188 | 303 | 561 |
| Areaportals | 1 | 19 | 87 | 205 | 373 |
| Embedded pak (MB) | 0 | 22 | 110 | 262 | 813 |
| I/O links | 28 | 136 | 216 | 406 | 1060 |
| Lights | 305 | 810 | 990 | 1219 | 2164 |
| Doors (all door classes) | 175 | 253 | 312 | 360 | 552 |

Reading: face count is remarkably tight (most maps 27-34k), so detail budget is spent on props/lighting/cubemaps instead; file size is driven almost entirely by embedded content, not geometry. A new RP map in the same league: ~30k faces, ~3k entities, ~1k lights, ~300 doors, a few thousand static props, areaportals in the tens to low hundreds. Use `benchmark_map` to see where a map sits. Some profiled files are alternate versions of one map (e.g. two Starisland BSPs), so "37" counts BSPs, not distinct maps; static props are missing for the one map whose game lump is compressed.
