# MCP-GMOD-2027

A Claude skill plus an MCP server for **Garry's Mod mapping with Hammer / Hammer++**: map structure and architecture, trigger/entity-I/O logic, optimization, and compile planning. Everything is read-only analysis unless you explicitly confirm a compile.

## What is inside
| Path | Content |
|---|---|
| `skills/gmod-mapping/` | The Claude skill (architecture, art direction, props, textures, optimization, tests, US-realism) plus new references `10` (Hammer++/toolchain internals), `11` (triggers and logic), `12` (DarkRP reference collection) |
| `mcp/` | Python MCP server `gmod-hammer` (stdio) |
| `knowledge/reference_maps.json` | Manifest of the 36-map DarkRP collection (titles/authors only) |
| `knowledge/profiles/` | Numeric profiles (no assets) of `gm_construct` and `gm_flatgrass`, for benchmarking |

## MCP tools
`detect_environment`, `fgd_search`, `fgd_entity` (full inherited keys/inputs/outputs from your installed FGDs), `vmf_analyze`, `bsp_analyze` (lumps, limit usage, vis clusters, lighting, pakfile, static props), `io_graph` (trigger/logic graph, broken connections), `trigger_recipe`, `mapping_rules`, `rp_scorecard`, `compile_plan`, `compile_run` (needs `confirm=true`), `compile_log_parse`, `reference_maps`, `reference_profiles`, `corpus_summary`, `benchmark_map` (percentile-rank a BSP against the 37-BSP RP corpus).

## Install
```bash
pip install "mcp>=1.2"
python mcp/tests/test_core.py
```
Register in Claude Code (project `.mcp.json` is included) or run `python -m gmod_hammer_mcp.server` from `mcp/`. Set `GMOD_PATH` if GarrysMod is not in a default Steam library. Copy `skills/gmod-mapping` into your Claude skills folder.

## Honest scope
- **"Training" is not model training.** The server encodes vetted rules and measures real maps; benchmarks come from maps you profile locally.
- **Reverse engineering** was static and non-invasive (file layout, config files, printable strings, BSP header/lump parsing). No decompilation, no redistribution of Valve or third-party binaries/FGDs/maps.
- **Third-party maps** (the Workshop collection) are not downloaded or bundled. all 36 collection items were downloaded locally (anonymous steamcmd), analysed, and deleted from the repo scope: only numbers are committed (`knowledge/profiles/`, `SUMMARY.json`). To add maps: `python mcp/profile_gma.py knowledge/profiles <gma-or-bin>`.
- Engine limits printed by `bsp_analyze` are commonly cited reference values; verify for your branch.
- Not tested: `compile_run` against a real VMF, Hammer++ GUI automation (Hammer has no API; work on the VMF).

## License
MIT for the code and original text in this repository.
