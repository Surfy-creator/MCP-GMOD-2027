#!/usr/bin/env python3
"""Static lint of a VMF (Hammer / Hammer++): what can be checked without launching Hammer.

Checks: block syntax, unique ids, 3 non-collinear plane points, plane orientation
(clockwise seen from outside), convex and closed brushes, map limits (+-16384),
tiny brushes, textures and models used, essential entities.

Usage: python vmf_lint.py map.vmf [--max-coord 16384]
Exit code: 0 = nothing blocking, 1 = errors.
"""
import argparse
import itertools
import re
import sys

TOKEN = re.compile(r'"([^"]*)"|([{}])|([A-Za-z_][\w]*)')
PLANE = re.compile(r"\(([^)]+)\)")


def parse(text):
    """Returns the list of top-level blocks: (name, kv dict, children[])."""
    toks = [(m.group(1), m.group(2), m.group(3)) for m in TOKEN.finditer(re.sub(r"//.*", "", text))]
    pos = 0

    def block(name):
        nonlocal pos
        kv, kids = {}, []
        while pos < len(toks):
            q, brace, word = toks[pos]
            if brace == "}":
                pos += 1
                return (name, kv, kids)
            if q is not None:  # "key" "value" pair
                key = q
                pos += 1
                val = toks[pos][0] if pos < len(toks) and toks[pos][0] is not None else ""
                pos += 1
                kv[key] = val
            elif word is not None:  # block name followed by {
                pos += 1
                if pos < len(toks) and toks[pos][1] == "{":
                    pos += 1
                    kids.append(block(word))
                else:
                    raise ValueError("Block '%s' without a brace." % word)
            else:
                raise ValueError("Unexpected brace.")
        raise ValueError("Missing closing brace in '%s'." % name)

    root = []
    while pos < len(toks):
        q, brace, word = toks[pos]
        if word is None:
            raise ValueError("Unexpected token at top level.")
        pos += 1
        if pos >= len(toks) or toks[pos][1] != "{":
            raise ValueError("Block '%s' without a brace." % word)
        pos += 1
        root.append(block(word))
    return root


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def solve3(planes):
    """Intersection of 3 planes n.x = d (Cramer's rule). None if parallel."""
    (n1, d1), (n2, d2), (n3, d3) = planes
    det = dot(n1, cross(n2, n3))
    if abs(det) < 1e-9:
        return None
    a = cross(n2, n3)
    b = cross(n3, n1)
    c = cross(n1, n2)
    return tuple((d1 * a[i] + d2 * b[i] + d3 * c[i]) / det for i in range(3))


def lint(text, max_coord=16384):
    errors, warns = [], []
    stats = {"solids": 0, "entities": 0, "materials": set(), "models": set(), "classes": {}}
    try:
        root = parse(text)
    except ValueError as e:
        return ["Invalid VMF syntax: %s" % e], [], stats

    seen_ids = set()

    def register(kv, what):
        i = kv.get("id")
        if i is None:
            return
        if i in seen_ids:
            errors.append("%s: duplicate id %s." % (what, i))
        seen_ids.add(i)

    def check_solid(solid, owner):
        stats["solids"] += 1
        sid = solid[1].get("id", "?")
        register(solid[1], "solid")
        planes = []
        for name, kv, _ in solid[2]:
            if name != "side":
                continue
            register(kv, "side")
            stats["materials"].add(kv.get("material", "").upper())
            pts = [tuple(float(c) for c in m.split()) for m in PLANE.findall(kv.get("plane", ""))]
            if len(pts) != 3:
                errors.append("solid %s: malformed plane." % sid)
                continue
            n = cross(sub(pts[1], pts[0]), sub(pts[2], pts[0]))
            ln = dot(n, n) ** 0.5
            if ln < 1e-6:
                errors.append("solid %s: three collinear points." % sid)
                continue
            n = tuple(c / ln for c in n)
            planes.append((n, dot(n, pts[0]), pts))
            if any(abs(c) > max_coord for p in pts for c in p):
                errors.append("solid %s: coordinate out of range +-%d (%s)." % (sid, max_coord, owner))
        if len(planes) < 4:
            errors.append("solid %s: fewer than 4 faces." % sid)
            return
        # vertices = intersections of plane triplets that lie in all half-spaces
        verts = []
        for combo in itertools.combinations(range(len(planes)), 3):
            p = solve3([(planes[i][0], planes[i][1]) for i in combo])
            if p is not None:
                verts.append(p)
        if not verts:
            errors.append("solid %s: planes without intersection." % sid)
            return
        centroid = tuple(sum(v[i] for v in verts) / len(verts) for i in range(3))
        # Hammer convention: (p1-p0)x(p2-p0) points toward the INSIDE
        for n, d, _ in planes:
            if dot(n, centroid) - d < -1e-6:
                errors.append("solid %s: plane facing outward (point order reversed)." % sid)
                break
        # vertices actually inside the solid (inside for all planes)
        real = [v for v in verts if all(dot(n, v) - d >= -0.01 for n, d, _ in planes)]
        if len(real) < 4:
            errors.append("solid %s: brush not closed or concave." % sid)
            return
        ext = [max(v[i] for v in real) - min(v[i] for v in real) for i in range(3)]
        if min(ext) < 1:
            warns.append("solid %s: thickness < 1 u (%s)." % (sid, owner))
        if any(abs(c) > max_coord for v in real for c in v):
            errors.append("solid %s: vertices out of range +-%d." % (sid, max_coord))

    for name, kv, kids in root:
        if name == "world":
            register(kv, "world")
            for n2, kv2, kids2 in kids:
                if n2 == "solid":
                    check_solid((n2, kv2, kids2), "world")
        elif name == "entity":
            stats["entities"] += 1
            register(kv, "entity")
            cls = kv.get("classname", "?")
            stats["classes"][cls] = stats["classes"].get(cls, 0) + 1
            if "model" in kv:
                stats["models"].add(kv["model"])
            for n2, kv2, kids2 in kids:
                if n2 == "solid":
                    check_solid((n2, kv2, kids2), cls)

    c = stats["classes"]
    if not any(k in c for k in ("info_player_start", "info_player_teamspawn", "info_player_terrorist", "info_player_counterterrorist")):
        warns.append("No player spawn (info_player_start or the gamemode equivalent).")
    if not any(k in c for k in ("light_environment", "light", "light_spot")):
        warns.append("No light source: everything will be black after vrad.")
    if "env_cubemap" not in c:
        warns.append("No env_cubemap: default reflections (remember to run buildcubemaps).")
    return errors, warns, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vmf")
    ap.add_argument("--max-coord", type=int, default=16384)
    a = ap.parse_args()
    with open(a.vmf, encoding="utf-8", errors="replace") as f:
        res = lint(f.read(), a.max_coord)
    if len(res) == 3 and isinstance(res[2], dict):
        errors, warns, st = res
    else:
        errors, warns, st = res[0], res[1], res[2]
    print("%d solids, %d entities, %d materials, %d models." % (st["solids"], st["entities"], len(st["materials"]), len(st["models"])))
    for w in warns:
        print("WARN  ", w)
    for e in errors:
        print("ERROR", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
