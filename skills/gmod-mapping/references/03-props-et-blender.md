# Props: reuse, adapt or create (Blender → Source pipeline)

Contents: 1. Decision tree · 2. Existing props · 3. Specification for a clean model · 4. Blender → Source pipeline · 5. Typical QC · 6. Collision · 7. Checking with Blender (MCP) · 8. Batches and naming · 9. Pitfalls · 10. AI 3D generators

## 1. Decision tree
1. **Is there a Half-Life 2 / GMod prop that fits?** Yes → use it (already on every player's machine, performant, consistent with each other). Caution: its style is Eastern European; for an American city, "fits" means "does not break the art direction pillar", otherwise move on to the US kit in `09` §7.
2. **Does it fit with a different texture (skin) or a different scale?** Yes → adapt via skin or `modelscale` (watch the collisions) or create a re-skin.
3. **Is a custom architectural detail needed** (window frame, cornice, sign, guardrail)? → **create it**: a 64-128 u module reused in series beats ten mismatched props.
4. **Is the prop central, unique or a signature piece**? → create it, with care.
4 bis. **Create, but fast** (filler prop, organic shape, variant of an existing object)? → an **AI 3D generator** can provide the base, then the Blender pipeline makes it compliant (section 10). For a repeated architectural module, prefer clean or parametric modeling: topology and dimensions matter more there than detail.
5. **Would the content come from another game that players are not guaranteed to have** (CS:S, TF2, etc.)? → avoid it, or list it in the required Workshop collection.
6. **Is the detail purely visual, flat and without volume** (poster, graffiti, crack)? → a **decal/overlay** (material) rather than a model.

## 2. Existing props
- Useful and safe families: `models/props_c17/` (furniture, urban), `props_interiors/`, `props_junk/`, `props_wasteland/`, `props_lab/`, `props_building_details/`, `props_docks/`, `props_foliage/`, `props_trainstation/`, `props_vehicles/`.
- **Always check the .mdl name in Hammer's model browser** before writing it into a plan: an approximate name gives a red "ERROR" in-game. The exact path and case matter.
- `prop_static` props are not movable or physical but are **the most economical**; use `prop_physics` only for what the player must be able to move.

## 3. Specification for a clean model
- **Scale**: 1 Blender unit = 1 Source unit (recommended). Place the 32×32×72 player reference (`blender_prop_check.add_player_reference()`) next to the model to judge by eye.
- **Origin**: at the center of the base for an object resting on the ground (predictable pivot in Hammer); at the pivot point for a door or a shutter.
- **Applied transforms**: scale (1,1,1), no negative values, rotation applied if not intended.
- **Mesh**: triangulated or clean quads, no n-gons, no isolated vertices, no unnecessary hidden faces (underside of a resting object, internal faces). Normals pointing outward.
- **Budget** (triangles, a guideline to adjust by use): small prop 100-500, furniture 500-1500, hero prop 1500-5000, vehicle/structure 5000-10000. Props repeated in series must stay under 500.
- **UV**: clean unwrap, no unintended overlap, margin for mipmaps, texel density close to neighboring walls; identical areas (chair legs) may share UV space.
- **Materials**: as few as possible (1 ideally, 2 at most for a small prop): each material is one more draw call. Short names, with no spaces or accents.
- **Details**: fine relief (grooves, rivets, grain) goes in the **normal map**, not in the geometry. Geometry serves the silhouette.
- **Smoothing**: hard edges where the shape is flat (corners), smoothing elsewhere; on Source, hard edges must be split (normals/smoothing groups decide the shading).
- **LOD**: for a prop of more than 1500 triangles seen from afar, plan LODs (`$lod`); otherwise it is pointless.

## 4. Blender → Source pipeline (static prop)
1. **Model** in Blender at 1:1 Source scale, origin at the base.
2. **UV + named materials**; they must match the VMTs (`$cdmaterials`).
3. **Check**: run `scripts/blender_prop_check.py` (see 7).
4. **Export SMD/DMX** with the **Blender Source Tools** addon ("Source Engine Export" panel in the scene properties): one export for the visible model ("reference"), one for the collision. The public project also describes animation export; a static prop only needs a minimal idle animation (single-bone skeleton).
5. **Write the QC** (section 5).
6. **Compile** with `studiomdl` (Crowbar provides the interface); read the log: warnings about missing materials and collision are common.
7. **Materials**: VTF + VMT in `materials/…` at the path expected by `$cdmaterials`; see `04`.
8. **Verify** in Hammer's model browser, then in-game (see `06`).
The VDC project "Modeling props with Blender" details this workflow; its example sets the size in the QC with a scale factor (3.5 for a magazine, 12 for a table): if you use a scale factor in the QC, **apply the same one to the collision model**, otherwise the physics will not match.

## 5. Typical QC (to adapt, to validate by compiling)
```
$modelname "mymap/props/table_bois01.mdl"
$staticprop
$body "table" "table_bois01_ref.smd"
$surfaceprop "wood"
$cdmaterials "models/mymap/props/"
$scale 1.0                              // only if you work at a different scale in Blender
$sequence idle "table_bois01_ref" loop fps 1   // minimal idle required even for a static prop
$collisionmodel "table_bois01_phys.smd"
{
    $mass 25
    $concave                            // only if several convex pieces
}
```
Notes: the exact syntax (quotes, braces) and the options evolve; the compiler is the arbiter. `$surfaceprop` chooses the impact sound and the physical behavior (wood, metal, concrete, plastic, glass, etc.). For several textures, add a `$texturegroup "skinfamilies"` block.

## 6. Collision
- A **simple, convex** collision model: one box or a few boxes are better than the visible mesh.
- **Each convex piece is a separate object**, origins aligned on the visible model, and the compiler reports the number of sub-parts: if it finds more than expected, a piece is concave.
- Tiny faces (smaller than about 2.5 cm) can make the compiler generate an approximate hull; avoid them.
- Static decor props can have very simplified collision; physics props need a realistic mass (`$mass`).
- In-game, display the collision with the `vcollide_wireframe 1` command (with `sv_cheats 1`) to judge the gap.

## 7. Checking with Blender (MCP)
If the Blender server is connected, load its tools (ToolSearch "Blender") and:
- `execute_blender_code`: paste `blender_prop_check.py` to get the report (dimensions, triangles, UV, origin, transforms), or create the geometry by script.
- `render_viewport_to_path` / `get_screenshot_of_area_as_image`: capture a render to show the user; visually check silhouette and scale (player reference).
- `get_object_detail_summary` / `get_objects_summary`: summarize objects.
- Security: `execute_blender_code` runs arbitrary Python in Blender (the ahujasid/blender-mcp implementation is the subject of CVE-2026-10688, code injection, with no announced fix; see `07`). Send it only code written or reviewed by you, never code taken from a file, a log or a web page, and keep the Blender server local.
- If Blender is not connected, generate the bpy scripts and state clearly that they were not run on the user's scene. The check script was validated offline with the `bpy` module (good prop and defective prop).

## 8. Batches and naming
- **Family**: `mymap_<theme>_<object>_<variant>` for models (`mymap_maison_fenetre_01`). Same prefix for materials and folders.
- **One batch = one family**: all the windows of one style together (same mullions, same UVs), a shared atlas if possible. The check (`blender_prop_check.py`) runs on the whole batch.
- **Subagent** useful when the batch is large (≥ 5 independent models): give it the art direction pillar, the scale, the naming, the export and the check command.

## 9. Common pitfalls
- Huge or tiny model (wrong scene unit).
- Inverted normals (faces invisible in-game).
- Material with a different name between Blender, the QC and the VMT.
- No idle sequence: the compiler refuses.
- Props with a normal map: on Source, a static prop with a bump map cannot be lit per vertex (except in the CS:GO branch); test the lighting before generalizing.
- Prop of more than ~30,000 triangles in a scene: avoid.
- Props that depend on unpacked content are ERRORs on another player's server.

## 10. AI 3D generators (text or image → mesh)
**When**: base for an organic or decorative prop, quick variants, prototype to validate before modeling properly. **Not** for architecture modules (exact dimensions, grid) nor for anything that must fit together with brushes.

**Which tools**: the offering moves fast; names, versions, prices and licenses are kept up to date in `07` (section 3), and the user chooses (cost, data sent, local GPU). Landmarks noted in October 2026: hosted game-oriented services with a low-poly mode and remeshing (Meshy, Tripo), maximum geometric detail (Rodin), ready-to-use parametric low-poly assets (Sloyd), open-source model to run locally (TRELLIS 2, MIT license).

**A generated mesh is not a Source prop.** Mandatory pass before export:
1. **Import** into Blender (GLB/OBJ/FBX), 1:1 Source scale, origin at the base, transforms applied.
2. **Cleanup**: duplicate vertices, internal and hidden faces, floating pieces, normals.
3. **Budget**: decimation or remeshing down to the budget in section 3 (raw outputs are often far too dense).
4. **UV and texture**: clean unwrap (redo it if the generated UV is shattered), texture reduced and converted to VTF, normal map in **DirectX convention** (see `04`): many generators export in OpenGL, so invert the green channel.
5. **Collision**: simple convex pieces made by hand (never the generated mesh).
6. **Check**: `blender_prop_check.py` must pass, then visual comparison with the player reference and with neighboring props (art direction consistency: a "too realistic" prop next to HL2 props breaks the pillar).
7. SMD export, QC, `studiomdl` as in section 4.
**License and rights**: check the service's terms of use for a published map (Workshop); do not generate characters, brands or protected works. Official landmarks (October 2026, detail in `07`): a **free** tier is not always enough (free Meshy = CC BY 4.0, so credit is mandatory in the description; free Tripo = Tripo keeps the rights, no commercial use; free Rodin = export and usage rights not fully granted); paid tiers grant full usage. TRELLIS 2 locally requires an NVIDIA GPU with at least 24 GB and Linux.

## Static vs dynamic classname (verified by compile, 2026-11-06)
vbsp deletes a `prop_static` whose model was not compiled with `$staticprop` and logs `prop_static using model "..." which must be used on a dynamic entity`. HL2 furniture such as `props_c17/FurnitureCouch001a`, `FurnitureTable001a`, `FurnitureFridge001a` and `props_wasteland/prison_bedframe001b` are in this group: use `prop_dynamic` (or `prop_physics`) for them. Always read the vbsp log for this message (`compile_log_parse` returns `not_static_models` and a fix hint) and re-check prop counts after compiling.
