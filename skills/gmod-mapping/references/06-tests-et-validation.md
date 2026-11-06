# Tests and validation

Contents: 1. Principle · 2. The test ladder · 3. The skill's automated tests · 4. Tests in Hammer · 5. In-game tests (commands) · 6. Reading an error · 7. Report template · 8. Correction loop

## 1. Principle
A claim without a test is a hypothesis. Each delivery states what was **verified** (and with what), what is **assumed**, and what the user must **test personally**. A test that cannot fail proves nothing: when you write a test, imagine the defective input it must reject, and try it (this is what was done for this skill's scripts: reversed plan, out-of-bounds coordinate, non-periodic ramp, prop without UVs).

## 2. The test ladder (from cheapest to most reliable)
| Level | What | Tool | Who can do it |
|---|---|---|---|
| 1. Logic | doors, windows, connectivity, scale | `vmf_blockout.py check` | Claude |
| 2. Static | well-formed VMF, oriented planes, convex brushes, ±16384 limits, spawns, lighting | `vmf_lint.py` | Claude |
| 3. Visual | 2D plan, lit texture preview, Blender render | `vmf_blockout.py svg`, `texture_forge.py --preview`, Blender MCP | Claude |
| 4. Model | triangles, UVs, origin, scale, materials | `blender_prop_check.py` | Claude (Blender connected) |
| 5. Compilation | `studiomdl`, `vbsp`, `vvis`, `vrad` with no error or leak | the pipeline's `compile_map` / `read_compile_log`, otherwise Crowbar and the SDK tools | Claude via the pipeline or shell access to the computer; otherwise the user sends the log |
| 6. Editor | Hammer "Check for Problems", walking in 3D | Hammer / Hammer++ | User |
| 7. In-game | gamefeel, FPS, collisions, lighting, multiplayer | GMod (the pipeline's `launch_game` to launch the map) | Claude launches, the user plays and sends the screenshots (loop in `08` §7) |
Climb the ladder as high as the session allows, and say where you stopped.

## 3. The skill's automated tests
```
python scripts/vmf_blockout.py check plan.json            # level 1
python scripts/vmf_lint.py carte.vmf                      # level 2
python scripts/texture_forge.py --selftest                # relief, normal convention, tileability
python scripts/blender_prop_check.py                      # inside Blender (level 4)
python scripts/fiche_style.py --selftest                  # style sheet: schema, consistency, injection
python scripts/fiche_style.py check fiche.json            # level 1 for art direction
```
With the pipeline connected, `vmf_analyze` replaces the lint for an existing map, but **still re-run `vmf_lint.py`** on a VMF the pipeline has just written: two independent checks are better than one.
They return a non-zero exit code on error: use them as a safeguard before delivering. A VMF build is refused if the plan has logic errors.

## 4. Tests in Hammer / Hammer++ (to ask the user)
- **Check for Problems** (`Alt+P`): invalid brushes, entities without a name, duplicate names, missing materials, etc.
- Open the generated VMF: it must load without an error message; walk in the 3D view; check that wall corners are sealed (no light passing through).
- Hammer++: light preview, skybox preview, fog preview to check the mood before compilation.

## 5. In-game tests (console commands; `sv_cheats 1` required for most)
| Command | Used for |
|---|---|
| `map <name>` | launch the map |
| `noclip`, `god` | inspect, pass through |
| `mat_fullbright 1` | see colors without lighting (isolate a lighting problem) |
| `mat_wireframe 1` | wireframe (brush/prop density) |
| `mat_bumpmap 0/1` | compare with and without normal maps |
| `mat_specular 0/1` | reflections (disable before `buildcubemaps`) |
| `buildcubemaps` | build the cubemaps |
| `r_novis 1`, `r_lockpvs 1` | test visibility |
| `mat_leafvis 3` | display the visibility zones |
| `r_drawstaticprops 0/1` | isolate the cost of static props |
| `vcollide_wireframe 1` | display model collisions |
| `net_graph 1` | FPS and network |
| `developer 1` | error messages in the console |
**Multiplayer** is tested with several players or a dedicated server: without that, promise nothing about performance under load.

## 6. Reading an error
- **vbsp log**: look for "leaked" first; a leak skews all the following results.
- **vvis log**: abnormally long duration → too many structural brushes: switch to `func_detail`.
- **vrad log**: watch the lighting and prop warnings; a lightmap scale value that is too fine slows everything down.
- **studiomdl log**: missing materials and collision warnings indicate what to fix before going further.
- For each error: probable cause → minimal fix → re-run → check that the error has **disappeared** and that no other has appeared.

## 7. Report template (put at the end of the delivery, concise)
```
Verified:  plan logic (0 errors, 2 warnings), VMF lint (46 brushes, 0 errors), textures (self-tests OK).
Not verified: vbsp/vvis/vrad compilation, in-game rendering, performance.
To test yourself: open the VMF in Hammer++ (Check for Problems), compile in fast mode, walk from the entrance to the kitchen.
Assumptions: prop models to confirm in the model browser; texture scale 0.25.
```

## 8. Correction loop
Test → failure → hypothesis about the cause → minimal fix → re-run of the **same** test → neighboring test to detect a regression. If three attempts fail, change hypothesis (re-read the log, simplify down to the minimal case) instead of changing things at random.
