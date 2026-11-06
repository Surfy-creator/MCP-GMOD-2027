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
