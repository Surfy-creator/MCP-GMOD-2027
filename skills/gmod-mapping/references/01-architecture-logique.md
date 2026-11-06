# Logical architecture and gameplay

Contents: 1. Scale · 2. Reference dimensions · 3. Program by building type · 4. Structure and construction · 5. Circulation · 6. Gameplay by game mode · 7. Logic tests

## 1. Scale (know it by heart)
- 16 Source units ≈ 1 foot (30.5 cm), so **1 unit ≈ 1.9 cm** and **1 meter ≈ 52 units**.
- Player: **32 wide, 72 tall standing, 36 crouched** (eyes ≈ 64 standing). Maximum climbable step: **18 u**.
- Hammer grid: work on 8 (fine), 16, 32 or 64; an off-grid brush is the first cause of leaks and tedious adjustments.
- Map limits: **±16384 u** on each axis. If the project reaches them, split into zones or use a 3D skybox.

## 2. Reference dimensions (Source units)
| Element | Recommended value | Useful minimum |
|---|---|---|
| Interior door | 56-64 × 104-112 | 48 × 96 |
| Entrance door / double door | 64-96 × 112 | 64 × 108 |
| Window | 64-96 wide, 56-72 tall, sill at 32-48 | sill 24-56 |
| Housing ceiling | 128-160 | 128 |
| Shop / hall / warehouse ceiling | 192-384 | 160 |
| Hallway | 64-96 wide | 64 (two players can pass each other) |
| Stairs | step 16-18 high × 24-28 deep, width ≥ 64 | step ≤ 18 |
| Guardrail | 40-48 high | 36 |
| Exterior wall | 12-24 | 8 |
| Interior partition | 4-8 | 4 |
| Floor slab (upper floor) | 8-16 | 8 |
| Table, countertop | 32-36 high | 28 |
| Couch (seat) | 16-18 high | 14 |
Windows and doors must line up between floors and between facades; openings at random heights are immediately visible.

## 3. Program by building type
For each type, these elements form the **minimum inventory list**. A missing element must be a choice (and the intent note says so).

**Dwelling house**: entrance (threshold, step, doormat), living room/lounge (seating, coffee table, TV unit or fireplace, bookcase), kitchen (sink, countertop, fridge, stove/oven, hood or window, upper/lower storage, dining table), bedroom(s) (bed, wardrobe, bedside table, window), bathroom (sink, toilet, shower/bathtub, mirror), stairs + guardrail if upper floor, cellar/garage/attic depending on standing. Exterior: roof with a pitch consistent with the climate, chimney if wood heating, gutters, mailbox, driveway, garden or terrace. Utilities: meter, cables or electrical service drop visible on the street side.

**Shop / bar / store**: storefront (display window, sign, door), counter, customer area, stockroom, delivery access, restrooms, signage, commercial lighting. **Garage / workshop**: wide overhead door (≥ 128), pit or lift, workbench, storage, fire extinguisher, drainage. **Bank / police station / hospital**: reception, public vs private circulation, airlock or controlled door, technical rooms, emergency exits. **Warehouse / factory**: loading docks, large doors, catwalks, shelving, overhead cranes if the height allows, marked circulation zones.

**Street / neighborhood**: roadway with crown and gutter, sidewalks (curb 6-8 u), crosswalks, furniture (street lamp, trash can, bench, fire hydrant), utilities (poles, manholes, cables), signage, facades with ground floor vs upper floors differentiated, service alleys, logical dead ends.

## 4. Structure and construction
- Openings (doors, windows) have a **lintel** and a **pier** (solid wall) between them: never two openings stuck together. The skill's checker flags a pier < 16 u.
- Load-bearing walls line up from one floor to the next; a large void requires a post, a beam or a visible cross wall.
- Roof: the framing justifies the thicknesses; a roof overhang (16-24 u) protects the facade; slopes drain toward gutters.
- A door threshold and a plinth separate the exterior floor from the interior floor (step ≤ 18, otherwise a ramp).
- A real building sits **on** something: visible foundations/plinth, not a cube dropped in the void.

## 5. Circulation and readability
- Every space is reachable from the spawn by a path without jumping (unless a gameplay choice). `vmf_blockout.py check` builds the door graph and verifies it.
- **Readability**: a player arriving must identify, without a sign, the entrance, the likely objective, and the exit. Use silhouette, light (brighter toward the objective), color and alignment of leading lines.
- **Width**: two players must be able to pass each other (≥ 64 u), four to stand in a hall (≥ 192 u per side).
- **Sightlines**: define the long lines of sight deliberately; break the others with partitions, furniture, a curve.
- **Verticality**: add height landmarks (visible stairs, mezzanine, accessible roof) rather than a flat floor.
- **Loops**: prefer loops to dead ends (circuit around a core) unless a trap is intended.

## 6. Gameplay by game mode (confirm in the mode's documentation at build time)
| Mode | What matters | Pitfalls |
|---|---|---|
| **Sandbox** (gm_) | large open areas, building zones, spawn far from fragile decor, few detailed brushes | too many physics entities, uneven floor |
| **DarkRP / RP** (rp_) | neighborhoods, rentable buildings with ownable doors (func_door, prop_door_rotating...), civilian/police spawns, commercial zones, bank | doors too close together, lack of interior variety, buildings not worth owning |
| **TTT** (ttt_) | medium maps with loops, stalking spots, hiding places, distributed weapons (mode entities), dark but readable lighting | too open (snipers), dead ends with no exit, unplayable zones with no light |
| **Prop Hunt** | density of "camouflageable" props, variety of scales, fair hiding places | non-convex props, odd collisions |
| **Zombie Survival / Horde** | defense posts, chokepoints, resources, tense lighting | a single path, spawn within shooting range |
| **Scene / screenshots / machinima** | framing, lighting, close-up details, performance secondary | nothing is playable or optimized for multiplayer |
Each mode has its own entities and naming conventions (map prefix, specific spawns). Check the mode's page before promising a behavior.

## 7. Logic tests (automatable)
`scripts/vmf_blockout.py check` flags:
- **Errors**: door < 48 wide or < 96 tall, threshold > 18, room with no door at all, room unreachable from the spawn, openings that overlap or run out of the wall, opening taller than the ceiling, no spawn.
- **Warnings**: habitable room without a window, ceiling < 128, room or hallway too narrow, pier < 16, window sill outside 24-56, prop outside any room, building with no door to the outside.
These rules encode sections 1 to 5. If the project has a valid reason to deviate (windowless cellar, narrow duct), keep the warning visible and justify it in the intent note.
