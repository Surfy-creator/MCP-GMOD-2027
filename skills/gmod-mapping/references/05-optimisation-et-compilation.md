# Optimization, compilation and packing

Contents: 1. Principles · 2. Clean brushes · 3. Visibility (vis) · 4. Props and distance · 5. Lighting and lightmaps · 6. Tool textures · 7. Compilation · 8. Packing and distribution · 9. Common errors

The values on this page are robust guidelines; the exact tool options and engine limits evolve: when in doubt, check the corresponding VDC or GMod wiki page (list in `07`).

## 1. Principles
- The Source engine splits the map into visibility zones (leaves) and computes what can see what (PVS). **The less the player sees at once, the faster the map.** Optimization consists of helping this computation and limiting the cost of each displayed thing.
- Optimize **after** gameplay and art direction are stable, but **build cleanly from the start** (grid, structural vs detail): fixing afterwards costs far more.
- Measure: `net_graph 1` for FPS; `r_novis 1` / `mat_leafvis` to see what visibility cuts (see `06`).

## 2. Clean brushes
- **On the grid** (8/16/32 u), vertices on the grid, right angles; avoid lopsided brushes and vertices off by a fraction.
- **Convex** only; no tiny brushes (< 4 u) unless needed; avoid coplanar overlaps (face flickering).
- A brush is always convex: a wall pierced by a door or a window is therefore an assembly of brushes (lintel, sill piece, two jambs), as `vmf_blockout.py` does. Keep these pieces aligned on the grid.
- **Hidden faces**: apply `tools/toolsnodraw` to every face nobody will see.
- **Structural vs detail**: only the walls, floors, ceilings that define volumes are structural. Everything else (moldings, decorative columns, brush furniture, small reliefs) becomes `func_detail`. Details do not cut visibility and lighten the computation.

## 3. Visibility
- **Sealing**: the map must be closed by an envelope (skybox): otherwise `vbsp` reports a leak ("leaked") and lighting/visibility is not computed. Load the leak pointfile (`File > Load Pointfile` in Hammer).
- **Areaportals**: on every closable door or opening that separates two zones, a `func_areaportal` linked to the door cuts the rendering behind it when it is closed.
- **Hint / skip**: use when the visibility tool cuts poorly; these are precise tools, not a reflex.
- **Occluders**: `func_occluder` (tool texture `occluder`) to hide what is behind large volumes outdoors.
- **3D skybox**: a miniature distant scene (`sky_camera`) costs much less than real geometry; build it in an instance if you use Hammer++'s 3D preview.
- **Fog + distance**: `env_fog_controller` with a cutoff distance (`farz`) to limit outdoor rendering.
- Split into **rooms and hallways**: long straight lines with no occlusion (a big empty street) are expensive; break them with turns, buildings, vegetation.

## 4. Props and distance
- A `prop_static` is **not a networked entity** and costs little; a `prop_physics`/`prop_dynamic` costs more. Prefer static.
- Define **fade distances** (`fademindist`, `fademaxdist`, `fadescale`) on small props so they disappear in the distance.
- Group small details into a single model rather than twenty separate props (fewer draw calls).
- Avoid stacking thousands of small props; measure with `r_drawstaticprops 0/1` to isolate their cost.
- Watch the number of networked entities (doors, dynamic lights, physics props): GMod raises the engine limits to 8192 networked and 8192 non-networked entities (versus 2048 networked on base Source, per the VDC "Entity limit", verified on 2026-10-17); stay well below, since players and addons create some during the game too.

## 5. Lighting and lightmaps
- **Lightmapscale**: 16 by default; 32-64 for large surfaces with no shadow detail; 8 or less only where the shadow must be very sharp. Finer = longer compile time and larger size.
- **A single `light_environment`** per map.
- **Interior lights**: limit the number of overlapping `light`s; a light that is too strong in a small room "burns" the walls.
- **Dynamic lights** (`light_dynamic`, projectors): expensive; reserve them for important effects.
- **Cubemaps**: one `env_cubemap` per room/zone; without a cubemap, reflective materials show the default value. Built **in-game** (see 7).

## 6. Tool textures (to know)
`tools/toolsnodraw` (invisible face), `tools/toolsskybox` (sky), `tools/toolsclip` / `toolsplayerclip` / `toolsnpcclip` (invisible collision), `tools/toolstrigger` (trigger zones), `tools/toolshint` / `toolsskip` (visibility), `tools/toolsareaportal`, `tools/toolsoccluder`, `tools/toolsblack`. Player clip blocks avoid awkward collision faces on complex props.

## 7. Compilation
Chain: **vbsp** (geometry, entities) → **vvis** (visibility) → **vrad** (lighting) → copy into `maps/`.
- While working: **fast** mode (`vvis -fast`, `vrad` without `-final`), to iterate.
- Final version: full `vvis`, `vrad -final`, and for static props the prop lighting options (`-StaticPropLighting`, `-StaticPropPolys`); check the exact names in your version's documentation.
- Hammer++ has a **separate compile window** and an expert mode to tune the parameters of each step.
- After compilation: build the cubemaps in-game (VDC "Cubemaps" procedure): `mat_specular 0` **before** loading the map, `sv_cheats 1`, load the map, `buildcubemaps`, then reload the map; if the map is compiled in HDR (`vrad -both`), build them in LDR (`mat_hdr_level 0`) then in HDR (`mat_hdr_level 2`), reloading in between; finish with `mat_specular 1`. Do not rename the BSP afterwards (cubemaps stop working). The VDC gives no GMod-specific variant; if the method fails, consult it.
- **Always** read the log: it contains the leaks ("leaked"), overlapping brushes, missing materials, limit overruns, etc.; the exact wording varies by tool and version. (see `06`).

## 8. Packing and distribution
- **Custom content** (materials, models, sounds): either **packed into the BSP** (Pakrat, VIDE or `bspzip`; GMod's compresses with `-repack` since the September 2026 update), or distributed in a **Workshop addon** (`gmad` or gmpublisher) with the map in the `maps/` folder. In both cases, list it: a player who does not have the file sees an "ERROR" or a checkerboard.
- **Server**: `resource.AddWorkshop(<id>)` to force the download of a Workshop addon; a FastDL serves the files (BSP compressed as .bz2); the limit and best practices evolve, check the up-to-date page.
- Name the map with the **mode prefix** (`gm_`, `rp_`, `ttt_`...); version suffix (`_v1`, `_v2`) to avoid cache conflicts.
- Provide a small **README**: version, mode, dependencies, credits, compilation commands used.

## 9. Common errors
| Symptom | Probable cause | Response |
|---|---|---|
| "Map is leaked" | hole in the envelope, entity outside the map | load the pointfile, follow the red line |
| Pink/black-purple texture | material missing or not packed | check the path, pack it |
| Red "ERROR" model | model missing or not mounted | check the name in the model browser; pack or mount it |
| Flickering faces | brushes overlapping on the same plane | offset or delete one of the two |
| Strange reflections | no cubemap built | `buildcubemaps` |
| Very long compilation | lightmapscale too fine, too many lights, too many structural detail brushes | raise the scale, switch to `func_detail` |
| Low FPS in an area | too many things visible at once, no areaportal, too many props | `r_novis`, `mat_leafvis`, isolate with `r_drawstaticprops 0` |
| Player stuck | collision of a complex prop | invisible clip, simplify the collision |
