"""Check of a Blender prop intended for Source / Garry's Mod.

To be run INSIDE Blender:
  - via the Blender MCP (execute_blender_code) by pasting this file, or
  - from the command line: blender -b file.blend --python blender_prop_check.py -- [--budget 1500] [--unit 1.0]

Working assumption: 1 Blender unit = 1 Source unit (--unit changes this report).
The script modifies nothing: it prints a report and exits with code 1 if there are errors.
Checks: applied transforms, negative scale, plausible dimensions, origin at the base,
triangles vs budget, n-gons, loose vertices, open edges (info), UVs present, number of materials.
"""
import sys

import bpy
import bmesh

# ---- parameters (overridable after the "--" on the command line)
BUDGET_TRIS = 1500      # triangle budget per standard prop; 3000-8000 for a "hero prop"
UNIT = 1.0              # Source units per Blender unit
MAX_DIM = 1024.0        # beyond this, the prop exceeds most uses (Source units)
MAX_MATERIALS = 4       # each material = one more draw call


def parse_args():
    global BUDGET_TRIS, UNIT
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    i = 0
    while i < len(argv):
        if argv[i] == "--budget":
            BUDGET_TRIS = int(argv[i + 1])
            i += 2
        elif argv[i] == "--unit":
            UNIT = float(argv[i + 1])
            i += 2
        else:
            i += 1


def check_object(obj):
    errors, warns, infos = [], [], []
    me = obj.data
    dims = [d * UNIT for d in obj.dimensions]
    infos.append("Source dimensions: %.1f x %.1f x %.1f u (X Y Z)" % tuple(dims))

    if any(abs(s - 1.0) > 1e-4 for s in obj.scale):
        errors.append("scale not applied %s: Ctrl+A > Scale before exporting." % (tuple(round(s, 4) for s in obj.scale),))
    if any(s < 0 for s in obj.scale):
        errors.append("negative scale: normals flipped on export.")
    if any(abs(a) > 1e-4 for a in obj.rotation_euler):
        warns.append("rotation not applied: apply it unless the orientation must stay that of the scene.")
    if max(dims) > MAX_DIM:
        warns.append("dimension > %d u: suspicious scale (wrong unit?)." % MAX_DIM)
    if max(dims) < 2.0:
        warns.append("max dimension < 2 u: tiny prop, suspicious scale.")

    # origin: a prop placed on the ground has its origin at the center of the base
    zs = [v[2] for v in obj.bound_box]
    xs = [v[0] for v in obj.bound_box]
    ys = [v[1] for v in obj.bound_box]
    if abs(min(zs) * UNIT) > 1.0:
        warns.append("origin not placed at the base (local min z = %.1f u): awkward placement in Hammer." % (min(zs) * UNIT))
    if abs((min(xs) + max(xs)) / 2 * UNIT) > 2.0 or abs((min(ys) + max(ys)) / 2 * UNIT) > 2.0:
        warns.append("origin off-center in XY: the prop will pivot around an unexpected point.")

    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    infos.append("%d triangles (budget %d)" % (tris, BUDGET_TRIS))
    if tris > BUDGET_TRIS * 2:
        errors.append("%d triangles: more than double the budget." % tris)
    elif tris > BUDGET_TRIS:
        warns.append("%d triangles: over budget, plan LODs or simplify." % tris)

    ngons = sum(1 for p in me.polygons if len(p.vertices) > 4)
    if ngons:
        warns.append("%d n-gons: triangulate before exporting to control the result." % ngons)

    bm = bmesh.new()
    bm.from_mesh(me)
    loose = sum(1 for v in bm.verts if not v.link_edges)
    open_edges = sum(1 for e in bm.edges if e.is_boundary)
    nonman = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    bm.free()
    if loose:
        errors.append("%d loose vertices: delete them (Mesh > Clean Up > Delete Loose)." % loose)
    if nonman:
        warns.append("%d non-manifold edges (3+ faces): risk of incorrect collision/shading." % nonman)
    if open_edges:
        infos.append("%d open edges (normal for a frame or a wall; avoid on an object meant to be closed)." % open_edges)

    if not me.uv_layers:
        errors.append("no UVs: the texture will not apply.")
    else:
        # UVs outside [0,1]: acceptable for tiling, only flagged
        uv = me.uv_layers.active.data
        out = sum(1 for l in uv if not (-0.001 <= l.uv.x <= 1.001 and -0.001 <= l.uv.y <= 1.001))
        if out:
            infos.append("%d UVs outside [0,1] (tiling: fine if intended)." % out)

    mats = [m for m in obj.material_slots if m.material]
    if not mats:
        warns.append("no material: a material name is required for $cdmaterials / compilation.")
    elif len(mats) > MAX_MATERIALS:
        warns.append("%d materials: merge them (atlas) to limit draw calls." % len(mats))
    if any(len(m.name) > 60 for m in obj.material_slots if m.material):
        warns.append("very long material name: Source requires short paths.")
    return errors, warns, infos


def main():
    parse_args()
    objs = [o for o in (bpy.context.selected_objects or bpy.context.scene.objects) if o.type == "MESH"]
    if not objs:
        print("ERROR No mesh object to check.")
        return 1
    total_err = 0
    for obj in objs:
        e, w, i = check_object(obj)
        print("== %s ==" % obj.name)
        for m in i:
            print("  INFO  ", m)
        for m in w:
            print("  WARN  ", m)
        for m in e:
            print("  ERROR", m)
        total_err += len(e)
    print("\nRESULT: %d object(s), %d error(s)." % (len(objs), total_err))
    return 1 if total_err else 0


def add_player_reference():
    """Adds a player template (32 x 32 x 72 u, crouched = 36) to judge scale by eye."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 36 / UNIT))
    ref = bpy.context.active_object
    ref.name = "REF_Joueur_72u"
    ref.scale = (32 / UNIT, 32 / UNIT, 72 / UNIT)
    ref.display_type = "WIRE"
    bpy.context.view_layer.update()  # without this, ref.dimensions stays at 1 x 1 x 1 until the next refresh
    return ref


if __name__ == "__main__":
    code = main()
    if "--" in sys.argv:  # command-line execution: propagate the return code
        sys.exit(code)
