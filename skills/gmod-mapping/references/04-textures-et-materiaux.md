# Textures, relief and materials (VTF / VMT)

Contents: 1. The maps of a material · 2. Normal map convention (pitfall no. 1) · 3. Producing a texture with relief · 4. Typical VMTs · 5. VTF and formats · 6. Real relief: displacements and geometry · 7. Variety without repetition · 8. Visual check

## 1. The maps of a Source material
| Map | Use | Notes |
|---|---|---|
| Albedo (`$basetexture`) | base color | no baked shadows or light; lighting is done by the engine |
| Normal (`$bumpmap`) | fine relief | **DirectX** convention (see 2); file named `<name>_normal` |
| Specular mask / envmap | gloss, reflections | often in the **alpha of the normal map** (`$normalmapalphaenvmapmask 1`) or in the albedo alpha (`$basealphaenvmapmask 1`) |
| Phong (models) | specular highlight | `$phong 1`, `$phongexponent`, `$phongboost` (VertexLitGeneric) |
| Self-illumination | screens, neon | `$selfillum 1` (+ mask in the alpha) |
| Detail | fine grain at close range | `$detail`, `$detailscale`, `$detailblendfactor` |
One well-made map beats five approximate ones. Start with albedo + normal; add the rest if the material needs it (metal, glass, varnish).

## 2. Normal map convention (pitfall no. 1)
The Valve documentation (VDC, "Normal Map Creation", verified on 2026-10-17) states that Source expects the **DirectX (Y−)** green channel: green at 0 = up, 255 = down. **Blender, Substance Designer/Painter and most tools output OpenGL (Y+) by default**: the green channel must be inverted on export, otherwise the relief is "carved in" instead of bumped out, which is the first visible mistake of a texture set.
- `texture_forge.py` outputs **DirectX** by default; `--convention opengl` for the other.
- A flat normal map is `(128, 128, 255)` (the engine provides `dev/flat_normal`).
- Visual check test: apply the material to a cube, light it at a grazing angle; a brick must look raised, a joint recessed. Otherwise, invert the green.
- `--preview` writes a 2×2 preview lit from the top left that serves exactly this purpose.

## 3. Producing a texture with relief
### 3.1 Generate (skill script)
```
python scripts/texture_forge.py brick  -o sortie/ --name mur_brique --size 512 --cols 12 --rows 36 --folder mymap/murs --preview --pack-alpha
python scripts/texture_forge.py planks -o sortie/ --name parquet   --size 512 --count 16 --folder mymap/sols
python scripts/texture_forge.py tiles  -o sortie/ --name carrelage --size 512 --count 8  --folder mymap/sols
python scripts/texture_forge.py concrete -o sortie/ --name beton   --size 512 --folder mymap/murs
```
What the script does: height → normal map (periodic, seamless), albedo with per-element variation and darkening of recesses (cavity AO), specular mask in the normal's alpha if `--pack-alpha`, ready VMT (`$basetexture`, `$bumpmap`, `$surfaceprop`). It prints **the real size of the elements in units**: adjust `--cols/--rows/--count` to aim for real-world sizes (brick ≈ 11 × 3 u, plank 5-10 u, tile 8-16 u) or keep a deliberately enlarged style, but choose.
Self-tests: `python scripts/texture_forge.py --selftest` (normal convention, tileability with a negative control, export).

### 3.2 Tile size
Size in units = **size in pixels × texture scale** (0.25 by default in Hammer). A 512 px texture at scale 0.25 covers 128 u (≈ 2.4 m). For finer detail, go to 1024 px (256 u), not to a smaller scale that would stretch the pixels.

### 3.3 Other sources
- Photos + derived height (Materialize, Designer, Krita/GIMP with filters): same inverted-green export rule.
- Hand-painted variations: keep the height in a separate file and rebuild the normal from it to keep everything consistent.
- Blender generators: bake height/normal from a procedural material (OpenGL by default → invert the green).

## 4. Typical VMTs (paths relative to `materials/`, without extension)
**Brush (walls, floors)**:
```
"LightmappedGeneric"
{
    "$basetexture" "mymap/murs/mur_brique"
    "$bumpmap"     "mymap/murs/mur_brique_normal"
    "$surfaceprop" "brick"
    "$envmap" "env_cubemap"                 // only if the material reflects
    "$envmaptint" "[0.08 0.08 0.08]"
    "$normalmapalphaenvmapmask" "1"         // if the normal map's alpha carries the mask
}
```
**Model**: `"VertexLitGeneric"` with `$basetexture`, `$bumpmap` if needed, `$phong`... and `$surfaceprop`.
**Displacement blend**: `"WorldVertexTransition"` with `$basetexture`, `$basetexture2`, `$bumpmap`, `$bumpmap2`, `$surfaceprop`, `$surfaceprop2`.
**Glass / water / refraction**: dedicated shaders (`Refract`, `Water`), to be checked in the documentation before writing them from memory.
`$surfaceprop`: brick, concrete, wood, metal, plaster, tile, glass, carpet, dirt, grass, gravel, sand, snow, rock, plastic... (full list in the `surfaceproperties.txt` file in the game's `scripts` folder). It drives impact sounds, bullet marks and physics: a brick with `$surfaceprop "wood"` sounds wrong.

## 5. VTF and formats
- Convert TGA/PNG → VTF with **VTFEdit** (or its command-line version). Check the "Normal map" flag for `*_normal`.
- Dimensions **in powers of two**. In practice: 256-1024 for walls, 512-2048 for important textures; beyond that, measure the impact (map size, memory).
- Compression: **DXT1** (no alpha) for opaque color, **DXT5** when there is an alpha (mask, transparency). For normal maps, an uncompressed format (BGR888) gives the best quality but weighs more (VDC); compare with DXT5 on a large flat area before deciding.
- Mipmaps enabled except for the interface.
- Folder: `materials/<map_name>/...` to avoid conflicts; same names in the VMT.

## 6. Real relief: displacements and geometry
The normal map gives the illusion of **fine** relief (< a few units). Beyond that, move to geometry:
- **Displacements** (terrain, ruin floors, cracked walls): power 3 most of the time, 4 if indispensable (very heavy); paint the alpha to blend two materials (`WorldVertexTransition`).
- **Brush recesses**: lintels, cornices, baseboards, sills, wall joints in brush, so that light draws out the shapes. Four units of recess give more credibility than a perfect texture.
- To my knowledge, Source/GMod has no native parallax in standard materials; do not promise it without checking (see monitoring).

## 7. Variety without repetition
Break repetition with: decals and overlays (stains, cracks, graffiti), `info_overlay`, tint variation (`$color`), displacement blending, props that break the lines, alternating two versions of the same texture, and geometry (pillars, recesses).

## 8. Visual check
1. `--preview` (lit 2×2): seams, direction of the relief.
2. Test cube in Hammer with the material: scale (is a brick the right size next to a door?), grazing light.
3. In-game: `mat_bumpmap 0/1` to compare, `mat_specular 0/1`, `mat_fullbright 1` to see color alone (see `06`).
