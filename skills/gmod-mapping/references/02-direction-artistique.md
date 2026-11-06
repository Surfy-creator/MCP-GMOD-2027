# Art direction, lighting and mood

Contents: 1. The art direction pillar · 2. Palette and materials · 3. Density consistency · 4. Lighting · 5. Atmosphere · 6. Storytelling · 7. Art direction checklist · 8. Art direction from an image or a sentence · 9. Variants and choices

Why this step exists: on Source, props and textures come from dozens of hands. Without a framework, you get a collage. The art direction pillar is the filter that says yes or no to each asset.

## 1. The art direction pillar (to be written in phase 1, in 6 lines)
- **Three words**: for example "damp, working-class, 1980s" or "bright, coastal, vacation".
- **References**: a real place, a film, a photo; describe them in words (era, country, materials, colors). One concrete reference beats ten adjectives.
- **Palette**: 3 to 5 colors with a role (dominant 60%, secondary 30%, accent 10%). The accent draws the eye: reserve it for the objective, the entrance, what can be manipulated.
- **Dominant materials**: 2-3 (brick + painted wood + rusted metal). Any other material must be justified.
- **State**: new, worn, abandoned, renovated; wear must follow logic (water under gutters, wear around handles and passages).
- **Lighting**: time, weather, dominant source (low sun, neon, yellow lamps).

## 2. Palette and materials
- Keep a **consistent color temperature**: warm light + cool shadows or the reverse, not a random mix.
- Avoid uniform gray: tint grays warm or cool depending on the mood.
- Contrast: the player reads value first (light/dark), then color. A dark floor with light walls, or the reverse, guides the reading; two tones of the same value blur together.
- Materials are distinguished by **relief and response to light** as much as by color: brick (pronounced relief, matte), metal (reflections, little relief), wood (fibers), concrete (grain), tile (sharp joints and gloss). See `04-textures-et-materiaux.md`.
- A single texture can be used everywhere if repetition is broken by: decals, props, tint variations (overlay), displacement blending, and geometry (recesses, cornices).

## 3. Density consistency (texel density) and visual scale
- Textures must have **the same apparent resolution** on all walls: Hammer's default (scale 0.25: 4 texels per unit) suits most surfaces; a brick or parquet that deviates looks "fake" at a glance.
- Patterns (bricks, planks, slabs) have **real sizes**: a brick ≈ 8 × 2.5 inches, i.e. roughly 11 × 3 u including joints; a parquet strip ≈ 10-20 cm wide, i.e. 5-10 u; a 20-30 cm tile, i.e. 10-16 u. "Game" bricks are often enlarged in a stylized way: choose consciously, and stay consistent from wall to wall. Adjust the texture scale so the pattern matches reality, not the other way around.
- Props, on the other hand, must bring **human scale**: handles, switches, outlets, steps. They are what make walls credible.

## 4. Lighting
- **Main source**: `light_environment` (sun + sky). Low angle for long shadows (end-of-day mood), high angle for full midday. Sun tint consistent with the palette.
- **Interior lights**: a visible lamp = a `light` or `light_spot` source at its position. Lit rooms with no visible source feel fake. Reduce the overall ambient to keep contrast.
- **Shadows and penumbra**: an interior with a single window must have a gradient, not uniform lighting.
- **Cubemaps**: one `env_cubemap` per room or zone; without them, shiny materials reflect anything. They are built in-game (see `05`).
- **Lightmapscale**: 16 by default; 32-64 on large featureless surfaces, 8 on zones where the shadow must be sharp (near an important prop). Finer = heavier to compile.
- **Work order**: block out the geometry, set the sun, add interior lights, then the accents (neon, candles, screens).

## 5. Atmosphere
- **Fog** (`env_fog_controller`): gives depth and hides view distance; tint = sky color at the horizon.
- **Color correction** (`color_correction`): once the base is clean, to push the mood (warm, desaturated, contrasty).
- **Tonemap** (`env_tonemap_controller`): for adaptive brightness in HDR.
- **Skybox**: choose a sky consistent with the time of day; a 3D skybox (`sky_camera`) extends the horizon with distant geometry.
- **Particles / animated details**: smoke, dust in a beam of light, drips, flags; use sparingly.
- **Ambient sound** (`ambient_generic`, `env_soundscape`): a silent place looks dead.

## 6. Environmental storytelling
A place tells who lives there, what happened there and in what order. Think in **traces**: a half-drunk cup, a bike against the wall, a peeling poster, a worn armchair on the TV side. Apply the rule of three: for each room, three details that say something specific about its occupants.
- Avoid random mess (thrown props): the mess must have a cause.
- Avoid impeccable order in a place meant to be lived in.

## 7. Art direction checklist before delivering
- [ ] Art direction pillar written and respected (palette, materials, state).
- [ ] A single dominant light temperature.
- [ ] Even texture density on neighboring surfaces.
- [ ] Each room has at least three narrative details.
- [ ] No "orphan" material (used only once for no reason).
- [ ] Accents draw toward the objective, not elsewhere.
- [ ] Areas without detail are visual-rest choices, not oversights.

## 8. Art direction from an image or a sentence
**Prerequisite**: the reference board from `09` §1 (at least three sources looked at: the user's images, reference maps, Street View, photos). An art direction made "from memory" gives generic decor.

The goal is to turn a vague intent into a verifiable **style sheet** (format: `references/08-pipeline-et-mcp.md` §4.2, example: `assets/fiche_style_exemple.json`), then into Source settings.

**From an image** (really look at it, do not sum it up in one word):
1. **Values**: where are the lightest and darkest areas? Is the contrast strong (dramatic) or weak (mist, dawn)?
2. **Colors**: pick out 3 to 5 hues with their approximate surface area (dominant, secondary, accent). Note whether shadows lean cool or warm.
3. **Light**: direction and height of the main source (long shadows = low sun = `pitch` close to 0), color of the direct light and of the ambient light, presence of artificial sources.
4. **Air**: mist, dust, rain, visible depth → fog (color = horizon tint, start and end in units).
5. **Material**: 2-3 dominant materials, their state, the logic of the wear.
6. **Architecture**: era, region, building sizes, rhythm of the facades; this is an input for the plan (reference `01`), not only for the art direction.
7. **What does not translate**: a 2004 engine has neither real-time global illumination nor dynamic shadows everywhere. State what will be approximated (lightmaps, cubemaps, fog, overlays) and what will be lost.

**From a sentence**: extract the words that carry the mood (place, era, time, weather, state, emotion), complete with explicit choices ("I'm going with a sunset because...") and propose concrete references described in words.

**Translation into Source settings** (starting points, to be judged on screenshots):
| Intent | Settings |
|---|---|
| Low sun, end of day | `pitch` -5 to -20, orange sun, intensity 150-300, cool and weak ambient |
| Full midday | `pitch` -60 to -80, almost white sun, stronger bluish ambient |
| Night | very weak and blue sun (10-60) or moon, visible artificial sources that carry the scene |
| Mist, dust, depth | fog in the horizon tint, `debut` 256-768, `fin` 2048-6000, density 0.4-0.8 |
| "Pushed" mood (desaturated, warm) | `color_correction` with a color lookup table, once the base is clean |
| Dramatic interior | one visible main source, low ambient, cubemap per room |
Then: `fiche_style.py check fiche.json` → fix → `fiche_style.py apply fiche.json plan.json -o plan_style.json` → blockout → fast compile → screenshots (loop in `08` §7).

## 9. Variants and choices
For an open-ended art direction request, propose **three contrasting sheets** (for example: faithful to the reference, darker and more dramatic, more readable for gameplay) rather than just one. Apply them to the same plan and compile them with the same fast profile, so the user compares on the same views. Once the choice is made, do not mix two sheets: refine the one that won.
