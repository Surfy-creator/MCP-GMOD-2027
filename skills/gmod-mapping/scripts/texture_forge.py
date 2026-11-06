#!/usr/bin/env python3
"""Procedural tileable texture forge with relief for Source / Garry's Mod.

From a pattern (brick, planks, tiles, concrete) produces:
  <name>.tga          albedo (base color)
  <name>_normal.tga   normal map in the DirectX convention (Y-) expected by Source, alpha = specular mask if --pack-alpha
  <name>_height.png   height map (for visual checking and reuse in Blender/Designer)
  <name>.vmt          ready-to-use LightmappedGeneric material (path relative to materials/)

Everything is periodic by construction (FFT noise, integer-period patterns): no seams.
Usage:
  python texture_forge.py brick  -o output/ --name brick_wall --size 512 --folder mymap/walls --seed 3
  python texture_forge.py --selftest
Then convert to VTF with VTFEdit / VTFCmd ("Normal map" checkbox for *_normal).
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

SURFACEPROP = {"brick": "brick", "planks": "wood", "tiles": "tile", "concrete": "concrete"}


# ----------------------------------------------------------------------------- tileable tools

def periodic_noise(n, rng, beta=2.0, fmin=1, fmax=None):
    """1/f^beta noise, periodic (FFT), normalized to [0,1]."""
    fmax = fmax or n // 2
    f = np.fft.fftfreq(n) * n
    fx, fy = np.meshgrid(f, f)
    r = np.hypot(fx, fy)
    amp = np.zeros_like(r)
    mask = (r >= fmin) & (r <= fmax)
    amp[mask] = 1.0 / np.power(r[mask], beta / 2.0)
    spec = amp * np.exp(2j * np.pi * rng.random((n, n)))
    img = np.real(np.fft.ifft2(spec))
    img -= img.min()
    return img / max(img.max(), 1e-9)


def blur(img, sigma):
    """Periodic Gaussian blur (Fourier domain)."""
    n = img.shape[0]
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


def smoothstep(a, b, x):
    t = np.clip((x - a) / max(b - a, 1e-9), 0, 1)
    return t * t * (3 - 2 * t)


def grid(n):
    y, x = np.mgrid[0:n, 0:n].astype(np.float64)
    return x, y


# ----------------------------------------------------------------------------- patterns
# each pattern returns (height [0,1], float RGB color [0,1], specular mask [0,1])

def brick(n, rng, rows=8, cols=4, brick_color=(0.55, 0.27, 0.2), mortar_color=(0.62, 0.6, 0.55), **_):
    rows += rows % 2  # even number: the bond pattern stays periodic
    x, y = grid(n)
    bh, bw = n / rows, n / cols
    # shifted by half a brick: the image border crosses the middle of the bricks (not a joint)
    x, y = (x + bw / 2) % n, (y + bh / 2) % n
    r = np.floor(y / bh).astype(int)
    xs = (x + (r % 2) * bw / 2) % n
    c = np.floor(xs / bw).astype(int)
    u, v = xs - c * bw, y - r * bh
    mortar = max(1.5, min(bw, bh) * 0.14)   # mortar joint proportional to the brick (not to the tile)
    edge = np.minimum.reduce([u, bw - u, v, bh - v])
    body = smoothstep(mortar * 0.5, mortar * 0.5 + max(1.0, mortar * 0.8), edge)
    cell = rng.random((rows, cols))
    cell_h = cell[r % rows, c % cols]
    cell_tint = rng.random((rows, cols, 3))[r % rows, c % cols]
    grain = periodic_noise(n, rng, beta=1.6, fmin=4)
    pores = periodic_noise(n, rng, beta=0.6, fmin=n // 8)
    height = body * (0.78 + 0.12 * cell_h + 0.1 * grain) - 0.03 * pores * body
    base = np.array(brick_color)[None, None, :] * (0.82 + 0.3 * cell_tint) * (0.88 + 0.2 * grain)[..., None]
    mort = np.array(mortar_color)[None, None, :] * (0.8 + 0.25 * pores)[..., None]
    color = body[..., None] * base + (1 - body[..., None]) * mort
    spec = 0.18 + 0.1 * body
    return np.clip(height, 0, 1), np.clip(color, 0, 1), spec


def planks(n, rng, count=8, wood_color=(0.52, 0.34, 0.18), **_):
    x, y = grid(n)
    ph = n / count
    y = (y + ph / 2) % n  # the image border crosses the middle of a plank
    row = np.floor(y / ph).astype(int)
    v = y - row * ph
    # end joints: integer positions, different for each plank
    joint = (rng.integers(n // 4, 3 * n // 4, size=count))
    xs = (x + joint[row % count]) % n
    seam_x = np.minimum(xs, n - xs)
    gap = max(1.5, ph * 0.05)
    edge_v = np.minimum(v, ph - v)
    groove = smoothstep(gap * 0.5, gap * 1.6, edge_v) * smoothstep(gap * 0.5, gap * 1.6, seam_x)
    # grain: sinusoids at integer frequencies (tileable), stretched along x
    grain = np.zeros((n, n))
    for _ in range(9):
        kx = int(rng.integers(0, 3))
        ky = int(rng.integers(n // 12, n // 4))
        grain += rng.random() * np.sin(2 * np.pi * (kx * x / n + ky * y / n) + rng.random() * 6.28)
    grain = (grain - grain.min()) / (grain.max() - grain.min() + 1e-9)
    fine = periodic_noise(n, rng, beta=1.2, fmin=n // 16)
    plank_tint = rng.random(count)[row % count]
    height = groove * (0.8 + 0.12 * grain + 0.04 * fine)
    base = np.array(wood_color)[None, None, :] * (0.78 + 0.35 * grain[..., None] + 0.12 * (plank_tint - 0.5)[..., None])
    color = base * (0.45 + 0.55 * groove[..., None])
    spec = 0.35 + 0.15 * grain
    return np.clip(height, 0, 1), np.clip(color, 0, 1), spec


def tiles(n, rng, count=4, tile_color=(0.82, 0.8, 0.74), grout_color=(0.45, 0.43, 0.4), **_):
    x, y = grid(n)
    s = n / count
    x, y = (x + s / 2) % n, (y + s / 2) % n  # the image border crosses the middle of the tiles
    u, v = x % s, y % s
    edge = np.minimum.reduce([u, s - u, v, s - v])
    grout = max(1.5, s * 0.03)
    body = smoothstep(grout * 0.5, grout * 0.5 + max(1.0, grout * 0.9), edge)
    ci, cj = np.floor(x / s).astype(int), np.floor(y / s).astype(int)
    tint = rng.random((count, count))[cj % count, ci % count]
    wear = periodic_noise(n, rng, beta=2.2, fmin=2)
    height = body * (0.9 + 0.04 * wear)
    base = np.array(tile_color)[None, None, :] * (0.93 + 0.1 * tint[..., None]) * (0.92 + 0.12 * wear[..., None])
    color = body[..., None] * base + (1 - body[..., None]) * np.array(grout_color)[None, None, :]
    spec = 0.6 * body + 0.1
    return np.clip(height, 0, 1), np.clip(color, 0, 1), spec


def concrete(n, rng, concrete_color=(0.5, 0.5, 0.48), **_):
    low = periodic_noise(n, rng, beta=2.6, fmin=1, fmax=10)
    mid = periodic_noise(n, rng, beta=1.8, fmin=6, fmax=n // 4)
    fine = periodic_noise(n, rng, beta=0.8, fmin=n // 6)
    pores = smoothstep(0.78, 0.9, periodic_noise(n, rng, beta=0.4, fmin=n // 4))
    height = np.clip(0.5 + 0.18 * (low - 0.5) + 0.22 * (mid - 0.5) + 0.08 * (fine - 0.5) - 0.12 * pores, 0, 1)
    base = np.array(concrete_color)[None, None, :] * (0.8 + 0.3 * low[..., None]) * (0.92 + 0.14 * mid[..., None])
    color = base * (1 - 0.35 * pores[..., None])
    spec = 0.15 + 0.05 * fine
    return height, np.clip(color, 0, 1), spec


PATTERNS = {"brick": brick, "planks": planks, "tiles": tiles, "concrete": concrete}


# ----------------------------------------------------------------------------- relief

def normal_from_height(h, strength=4.0, convention="directx"):
    """Tangent-space normal map (periodic). Returns uint8 HxWx3.
    OpenGL: green = +slope toward the top of the image. DirectX (Source): green inverted."""
    n = h.shape[0]
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * n / 256.0
    drow = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * n / 256.0
    nx = -dx * strength
    ny = drow * strength  # OpenGL (Y+ = top of the image)
    if convention == "directx":
        ny = -ny
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    out = np.stack([nx / ln, ny / ln, nz / ln], axis=-1) * 0.5 + 0.5
    return np.round(out * 255).astype(np.uint8)


def cavity_ao(h, sigma=None):
    sigma = sigma or h.shape[0] / 128.0
    return np.clip(1.0 - np.clip((blur(h, sigma) - h) * 3.0, 0, 1), 0.0, 1.0)


def preview_sheet(color, normal, convention="directx"):
    """2x2 preview (checks the seams) lit from the top-left: if the relief looks
    carved in instead of raised, the green channel convention is inverted."""
    nrm = normal.astype(np.float64) / 255.0 * 2 - 1
    ny_up = -nrm[..., 1] if convention == "directx" else nrm[..., 1]
    light = np.array([-0.55, 0.55, 0.63])
    light /= np.linalg.norm(light)
    lam = np.clip(nrm[..., 0] * light[0] + ny_up * light[1] + nrm[..., 2] * light[2], 0, 1)
    lit = np.clip(color * (0.25 + 0.95 * lam)[..., None], 0, 1)
    tiled = np.tile(lit, (2, 2, 1))
    return Image.fromarray(np.round(tiled * 255).astype(np.uint8), "RGB")


# ----------------------------------------------------------------------------- export

def vmt_text(folder, name, pattern, pack_alpha, envmap):
    lines = ['"LightmappedGeneric"', "{", '\t"$basetexture" "%s/%s"' % (folder, name),
             '\t"$bumpmap" "%s/%s_normal"' % (folder, name), '\t"$surfaceprop" "%s"' % SURFACEPROP[pattern]]
    if pack_alpha or envmap:
        lines += ['\t"$envmap" "env_cubemap"', '\t"$envmaptint" "[0.08 0.08 0.08]"']
        if pack_alpha:
            lines.append('\t"$normalmapalphaenvmapmask" "1"')
    lines.append("}")
    return "\n".join(lines) + "\n"


def forge(pattern, out_dir, name, size, seed, strength, convention, folder, pack_alpha, envmap, preview=False, **opts):
    if size & (size - 1) or size < 64 or size > 4096:
        raise SystemExit("--size must be a power of 2 between 64 and 4096 (Source).")
    rng = np.random.default_rng(seed)
    height, color, spec = PATTERNS[pattern](size, rng, **opts)
    color = np.clip(color * (0.55 + 0.45 * cavity_ao(height))[..., None], 0, 1)
    normal = normal_from_height(height, strength, convention)
    os.makedirs(out_dir, exist_ok=True)
    albedo_img = Image.fromarray(np.round(color * 255).astype(np.uint8), "RGB")
    albedo_img.save(os.path.join(out_dir, name + ".tga"))
    if pack_alpha:
        rgba = np.dstack([normal, np.round(np.clip(spec, 0, 1) * 255).astype(np.uint8)])
        Image.fromarray(rgba, "RGBA").save(os.path.join(out_dir, name + "_normal.tga"))
    else:
        Image.fromarray(normal, "RGB").save(os.path.join(out_dir, name + "_normal.tga"))
    Image.fromarray(np.round(height * 255).astype(np.uint8), "L").save(os.path.join(out_dir, name + "_height.png"))
    with open(os.path.join(out_dir, name + ".vmt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(vmt_text(folder, name, pattern, pack_alpha, envmap))
    if preview:
        preview_sheet(color, normal, convention).save(os.path.join(out_dir, name + "_preview.png"))
    return height, color, normal


# ----------------------------------------------------------------------------- self-tests

def selftest():
    ok = True

    def report(label, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(("OK    " if cond else "FAIL  ") + label + (" - " + detail if detail else ""))

    # 1) the DirectX convention is the exact inverse of OpenGL on the green channel
    ramp = np.tile(np.linspace(0, 1, 64)[:, None], (1, 64))  # height increasing toward the BOTTOM of the image
    gl = normal_from_height(ramp, 4.0, "opengl")
    dx = normal_from_height(ramp, 4.0, "directx")
    mid = (slice(8, 56), slice(8, 56))
    report("OpenGL: slope rising downward -> green > 128", gl[mid][..., 1].mean() > 128, "G=%.1f" % gl[mid][..., 1].mean())
    report("DirectX (Source): green inverted relative to OpenGL", np.all(np.abs(gl[mid][..., 1].astype(int) + dx[mid][..., 1].astype(int) - 255) <= 1))
    report("Red identical across conventions", np.array_equal(gl[..., 0], dx[..., 0]))
    flat = normal_from_height(np.full((64, 64), 0.5), 4.0)
    report("Flat surface -> (128,128,255)", tuple(flat[5, 5]) == (128, 128, 255), str(tuple(flat[5, 5])))

    # 2) each pattern: shape, range, tileability
    rng_seed = 7
    for pat in PATTERNS:
        h, c, s = PATTERNS[pat](256, np.random.default_rng(rng_seed))
        report("%s: height in [0,1] and RGB albedo" % pat, h.min() >= 0 and h.max() <= 1 and c.shape == (256, 256, 3))
        report("%s: relief present (height standard deviation > 0.03)" % pat, h.std() > 0.03, "std=%.3f" % h.std())
        # seam: difference between opposite edges (column 255 -> 0) compared with internal differences
        seam = np.mean(np.abs(h[:, 0] - h[:, -1])) + np.mean(np.abs(h[0, :] - h[-1, :]))
        inner = np.mean(np.abs(h[:, 1:] - h[:, :-1])) + np.mean(np.abs(h[1:, :] - h[:-1, :]))
        report("%s: tileable (seam <= 2x internal variation)" % pat, seam <= 2.0 * inner + 1e-6, "seam=%.4f internal=%.4f" % (seam, inner))
        nrm = normal_from_height(h)
        seam_n = np.mean(np.abs(nrm[:, 0].astype(int) - nrm[:, -1].astype(int)))
        inner_n = np.mean(np.abs(nrm[:, 1:].astype(int) - nrm[:, :-1].astype(int)))
        report("%s: tileable normal map" % pat, seam_n <= 2.0 * inner_n + 1e-6, "seam=%.2f internal=%.2f" % (seam_n, inner_n))

    # negative control: a ramp is NOT periodic, the seam test must reject it
    ramp2 = np.tile(np.linspace(0, 1, 256)[None, :], (256, 1))
    seam_r = np.mean(np.abs(ramp2[:, 0] - ramp2[:, -1]))
    inner_r = np.mean(np.abs(ramp2[:, 1:] - ramp2[:, :-1]))
    report("negative control: a non-periodic ramp is detected", seam_r > 2.0 * inner_r, "seam=%.3f internal=%.4f" % (seam_r, inner_r))

    # 3) determinism and export
    a = PATTERNS["brick"](128, np.random.default_rng(1))[0]
    b = PATTERNS["brick"](128, np.random.default_rng(1))[0]
    report("same seed -> same texture", np.array_equal(a, b))
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        forge("brick", d, "t", 128, 1, 4.0, "directx", "test/dir", True, False)
        files = sorted(os.listdir(d))
        report("exported files", files == ["t.tga", "t.vmt", "t_height.png", "t_normal.tga"], str(files))
        im = Image.open(os.path.join(d, "t_normal.tga"))
        report("normal TGA in RGBA (alpha = specular mask)", im.mode == "RGBA" and im.size == (128, 128), im.mode)
        vmt = open(os.path.join(d, "t.vmt"), encoding="utf-8").read()
        report("VMT: paths and surfaceprop", '"$basetexture" "test/dir/t"' in vmt and '"$surfaceprop" "brick"' in vmt)
    print("\nALL TESTS OK" if ok else "\nSOME TESTS FAILED")
    return 0 if ok else 1


def describe_scale(pattern, size, scale, opts):
    """Real-world size (Source units, 1 u ~ 1.9 cm) of the pattern elements for the given texture scale."""
    world = size * scale
    msg = "Tile = %.0f x %.0f u (%.1f x %.1f m)" % (world, world, world * 0.019, world * 0.019)
    if pattern == "brick":
        rows, cols = opts.get("rows", 8), opts.get("cols", 4)
        msg += " ; brick ~ %.1f x %.1f u (real: ~11 x 3 u)" % (world / cols, world / (rows + rows % 2))
    elif pattern == "planks":
        msg += " ; plank ~ %.1f u wide (real: 5-10 u)" % (world / opts.get("count", 8))
    elif pattern == "tiles":
        msg += " ; tile ~ %.1f u (real: 8-16 u)" % (world / opts.get("count", 4))
    return msg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pattern", nargs="?", choices=sorted(PATTERNS))
    ap.add_argument("-o", "--out", default="textures_out")
    ap.add_argument("--name")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--strength", type=float, default=4.0, help="relief intensity (default 4)")
    ap.add_argument("--convention", choices=("directx", "opengl"), default="directx", help="Source = directx (default)")
    ap.add_argument("--folder", default="mymap", help="folder under materials/ written into the VMT")
    ap.add_argument("--pack-alpha", action="store_true", help="normal map alpha = specular mask (envmap)")
    ap.add_argument("--envmap", action="store_true", help="adds $envmap env_cubemap to the VMT")
    ap.add_argument("--rows", type=int, help="brick: number of rows per tile (even)")
    ap.add_argument("--cols", type=int, help="brick: bricks per row")
    ap.add_argument("--count", type=int, help="planks: planks per tile; tiles: tiles per side")
    ap.add_argument("--texture-scale", type=float, default=0.25, help="texture scale in Hammer (default 0.25 = 4 texels per unit)")
    ap.add_argument("--preview", action="store_true", help="writes <name>_preview.png (2x2 lit, checks seams and relief)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.pattern:
        ap.error("pattern required (brick, planks, tiles, concrete) or --selftest")
    name = a.name or a.pattern
    opts = {k: v for k, v in (("rows", a.rows), ("cols", a.cols), ("count", a.count)) if v}
    forge(a.pattern, a.out, name, a.size, a.seed, a.strength, a.convention, a.folder, a.pack_alpha, a.envmap, preview=a.preview, **opts)
    print("OK ->", os.path.join(a.out, name + ".tga"), "(+ _normal.tga, _height.png, .vmt)")
    print(describe_scale(a.pattern, a.size, a.texture_scale, opts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
