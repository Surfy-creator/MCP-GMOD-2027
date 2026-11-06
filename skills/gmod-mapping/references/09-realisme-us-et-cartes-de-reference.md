# American realism, reference maps and documentation

Contents: 1. Research before drawing (mandatory) · 2. What the great RP maps do well · 3. The organic and logical city · 4. American typologies (suburb, retail, industry, downtown) · 5. American street: elements and dimensions · 6. Commercial interiors · 7. US prop kit in Blender · 8. Performance of RP cities · 9. Pitfalls of the "fake American"

## 1. Research before drawing (mandatory)
No art direction and no neighborhood plan starts from the model's memory: it starts from **references actually looked at**. Before the statement of intent (phase 1):
1. **The user's references**: their images and screenshots (the project's `references_visuelles/` folder). They take precedence over everything else.
2. **Reference GMod maps**: RP maps known for their optimization, realism and gameplay (those the user cites; web search and Workshop pages for screenshots and layouts). We study them, we do not copy them.
3. **Real places**: Google Maps and Street View (browser if available; otherwise image search) on a typical place of the target style. Examples of study areas: San Francisco Bay Area suburbs (Daly City, South San Francisco, Pacifica), Queens and the Bronx, Chicago's industrial districts, small Midwest towns, Los Angeles (strip malls).
4. **Free photos** for textures: CC0 sources (Poly Haven, ambientCG). Street View images and map screenshots serve **as reference only**, never as texture or published content.
Produce a short **reference board**: for each image, the source and what is kept from it (one line: "attached garages and cracked concrete driveways", "color stripe at ceiling height in the convenience store"). It goes into the style sheet (`references_visuelles`, at least three entries) and into the project folder. Without it, `fiche_style.py check` warns.

## 2. What the great RP maps do well (noted from the reference layouts and screenshots)
- **Road hierarchy**: a ring road around the city, a few arterials crossing it, then streets and alleys. The player finds their way without a map after ten minutes.
- **Neighborhoods with a readable function**: civic center (city hall, police, hospital, bank), shopping street, industrial waterfront (warehouses, scrapyard, docks), residential on the outskirts (townhouses, single-family homes), city entrance along the arterial (gas station, motel, car dealership).
- **A natural boundary** (river, bay, hill) with bridges: it divides the map, creates crossing points and panoramas, and cuts visibility.
- **Named, well-distributed gameplay locations**: each RP job has its building (police, fire department, hospital, garage, impound lot, gun shop, jewelry store, bank); vacant shops and apartments players can open; hideouts in the corners.
- **No gratuitous dead ends**: loops allow chases and escapes; dead ends exist only if they serve a purpose (hideout, alley).
- **Cheap depth**: 3D skybox and distant skyline, overcast sky that forgives the lighting, light fog.
- **Credible but economical interiors**: simple geometry, detail carried by props, textures and lighting (justified neon, reflective floor with cubemap).

## 3. The organic and logical city
A real city has **grown**: it carries the traces of several eras and of constraints. That is what makes it real.
- **Layers of eras**: an old brick downtown (3-6 story buildings, fire escapes), a postwar ring (single-story houses, garages), recent additions (renovated gas station, new fast-food place between two old buildings).
- **The terrain dictates**: streets following contour lines, retaining walls, houses stepping down the slope, concrete flood channel at the bottom of the valley. A perfectly flat, orthogonal city smells of editor.
- **Deliberate irregularities**: variable building setbacks, plots of different sizes, a street that changes angle, a block cut diagonally. One rule for ten buildings, one exception every five.
- **Continuous networks**: utility poles at regular intervals with cables connected to each house, manholes and grates at low points, lights and signs at intersections, regular streetlights. A network interrupted for no reason shows.
- **Use and maintenance**: trash cans in front of houses, parked cars, graffiti on blind walls and channels, rust under drainpipes, uneven lawns, occasional construction (tape, tarp on a roof). Wear follows foot traffic, rain and sun.
- **Every building has a back**: service door, dumpsters, rooftop air conditioners, meters, deliveries. The facade alone is a movie set.

## 4. American typologies (minimal program, to be completed with `01`)
| Type | What makes it recognizable |
|---|---|
| Single-story house ("ranch") | attached garage for 1-2 cars with a sectional door, concrete driveway, lawn, low-pitch shingle roof, wood siding or stucco, sliding or double-hung windows, mailbox, trash cans at the edge of the driveway |
| Small multi-family (duplex, fourplex) | garage on the ground floor and dwelling above, exterior staircase, light stucco, awning or shingle band, satellite dishes |
| Old downtown building | brick, 3-6 stories, fire escapes on the facade, ground-floor shops with roll-down shutters and signs, cornice, rooftop tank or equipment |
| Gas station | flat canopy on posts above the pump islands, price totem tall and visible from afar, small glazed shop, air and water, protective bollards |
| Fast-food "pad" | standalone building on its parking lot, drive-thru that wraps around the building, landscaped islands with curbs, flagpole and totem sign, marked accessible parking spaces |
| Convenience store | see section 6 |
| Industrial warehouse | tilt-up concrete, dock sectional doors, painted pilasters, large street number, yard with trucks, chain-link fence |
| Utilities and infrastructure | concrete flood channel with fence and guardrail, road bridge, poles and transformers, tow trucks and impound lot |

## 5. American street: elements and dimensions (Source units, ~52 u per meter; real-world references converted)
| Element | Real | Units | Note |
|---|---|---|---|
| Traffic lane | 3.3-3.7 m | 170-190 | RP maps often widen by 20-50% for vehicles: decide depending on vehicle addons |
| Sidewalk | 1.5-3 m | 80-160 | wider downtown |
| Curb | 15 cm | 8 | curb painted red or yellow = no parking |
| Curb cut (driveway entrance) | 3-6 m wide | 160-320 | |
| Parking space | 2.7 × 5.5 m | 140 × 285 | white or yellow lines as overlays |
| Single / double garage door | 2.7 / 4.9 × 2.1 m | 140 / 255 × 110 | |
| Utility pole | 9-12 m above ground, every 30-45 m | 470-625 tall, 1560-2340 apart | cables with `move_rope`/`keyframe_rope` |
| Streetlight | 7-9 m | 365-470 | |
| Traffic light, suspended or on a pole | ~5 m clearance | ~260 | |
Ground markings (STOP, crosswalks, lines) are **overlays**, not brushes.

## 6. Commercial interiors (example: convenience store)
- **Program**: entrance with mat, checkout counter with a cigarette display behind and candy in front, central aisles, glass drink fridges at the back, soda and coffee fountain on one side, staff-only door, ceiling surveillance camera.
- **Shell**: drop ceiling with recessed fluorescent fixtures (each fixture = one light source), light checkerboard tile in a regular pattern, continuous color stripe at lintel height (identity of the invented brand), painted baseboard.
- **Lighting**: cool and uniform but not flat (low ambient, visible fixtures carrying the scene), cubemap in the center for floor reflections.
- Other shops follow the same logic: a real program taken from photos, a simple shell, dense and consistent props.

## 7. US prop kit in Blender
Half-Life 2 props are **Eastern European**: used as they are, they break an American city. For this style, create in Blender (pipeline from `03`, in batches, same UVs and texel density) a reusable **US kit**, in priority order:
1. Wooden utility pole + transformer + insulators; ground-level electrical box.
2. Fire hydrant, manhole, storm drain grate, protective bollards.
3. Street signs (green street name plates, octagonal STOP, speed limits) and traffic lights.
4. Residential mailbox, street mailbox, wheeled trash cans (blue, gray, green).
5. Facade modules: fire escape, window air conditioner, roll-down shutter, awning, illuminated sign.
6. Gas station: pump island, modular canopy, price totem (invented brand).
7. Fences: chain-link, wooden fence, white pickets; parking curb stops.
8. Rooftop equipment: air conditioning units, ducts, ladders.
First check what already exists in content mounted by players or in an authorized Workshop collection: do not recreate what is already good and available.

## 8. Performance of RP cities (what the reputable maps do)
- Facades in simple brushes + detailed textures; interiors **only** for openable buildings; the rest as `func_detail`.
- Streets and blocks cut for visibility: bends, bridges and tall buildings break long sight lines; `areaportal` on every shop and apartment door; occluders downtown.
- Static props with fade distances; small details (cans, papers) with a short fade.
- Terrain and slopes as displacements; 3D skybox for the skyline; fog and `farz` tuned together.
- Measure, do not assume: `net_graph`, `mat_wireframe`, `r_drawstaticprops` (see `06`), and compare before/after.

## 9. Pitfalls of the "fake American"
- **Real brands** (chain logos, oil companies, signs): never. Invent plausible brands (name, colors, simple logo); it is also freer for the story.
- Everything new, clean and aligned; no cables; no cars; sidewalks without curb cuts; identical houses in perfect series.
- European scale: narrow streets, small cars, double-casement windows everywhere.
- Uniform blue sky and flat light: the California coast is often overcast or hazy, Chicago gray, Los Angeles scorched by the sun. The chosen climate dictates sky, vegetation (cypress and eucalyptus in Northern California, palms in the south, deciduous trees in the Midwest) and wear.
