#!/usr/bin/env python3
"""VMF blockout for Garry's Mod (Hammer / Hammer++) from a JSON plan.

Three commands:
  check  plan.json            -> architectural logic tests (doors, windows, connectivity...)
  build  plan.json -o x.vmf   -> generates the VMF (hollow rooms, openings, props, spawns, sky)
  svg    plan.json -o x.svg   -> 2D top-down mock-up

Conventions: Source units (1 unit ~ 1.9 cm). south = -y, north = +y, west = -x, east = +x.
The w/d/h dimensions are those of the INTERIOR of the room; walls are built on the outside.
Two rooms sharing a wall: the first builds it, the second puts it in "skip"
and is placed one wall thickness away.
"""
import argparse
import json
import sys
from collections import deque

SIDES = ("south", "north", "west", "east")
HABITABLE = {"salon", "cuisine", "chambre", "bureau", "sejour", "salle_a_manger", "atelier", "boutique", "bar"}

DEFAULTS = {
    "wall_thickness": 8,
    "floor_thickness": 8,
    "ceiling_thickness": 8,
    "sky": "sky_day01_01",
    "skybox_margin": 512,
    "tex": {
        "wall": "DEV/DEV_MEASUREGENERIC01B",
        "floor": "DEV/GRAYGRID",
        "ceiling": "DEV/DEV_MEASUREGENERIC01B",
        "sky": "TOOLS/TOOLSSKYBOX",
    },
}


# ----------------------------------------------------------------------------- geometry

class Box:
    __slots__ = ("x0", "y0", "z0", "x1", "y1", "z1", "tex")

    def __init__(self, x0, y0, z0, x1, y1, z1, tex):
        self.x0, self.y0, self.z0 = min(x0, x1), min(y0, y1), min(z0, z1)
        self.x1, self.y1, self.z1 = max(x0, x1), max(y0, y1), max(z0, z1)
        self.tex = tex

    def valid(self):
        return self.x1 - self.x0 > 0.01 and self.y1 - self.y0 > 0.01 and self.z1 - self.z0 > 0.01

    def faces(self):
        """6 faces: (outward normal, vertices counter-clockwise seen from outside, uaxis, vaxis)."""
        x0, y0, z0, x1, y1, z1 = self.x0, self.y0, self.z0, self.x1, self.y1, self.z1
        ux, uy = "[1 0 0 0] 0.25", "[0 1 0 0] 0.25"
        vy, vz = "[0 -1 0 0] 0.25", "[0 0 -1 0] 0.25"
        return [
            ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], ux, vy),
            ((0, 0, -1), [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], ux, vy),
            ((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], uy, vz),
            ((-1, 0, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], uy, vz),
            ((0, 1, 0), [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)], ux, vz),
            ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], ux, vz),
        ]


def fmt(v):
    return str(int(v)) if float(v).is_integer() else ("%.3f" % v).rstrip("0").rstrip(".")


def pt(p):
    return "(%s %s %s)" % tuple(fmt(c) for c in p)


# ----------------------------------------------------------------------------- plan

def load_plan(path):
    with open(path, encoding="utf-8") as f:
        plan = json.load(f)
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in plan.items() if k != "tex"})
    merged["tex"] = dict(DEFAULTS["tex"], **plan.get("tex", {}))
    merged.setdefault("rooms", [])
    merged.setdefault("props", [])
    merged.setdefault("spawns", [])
    for r in merged["rooms"]:
        r.setdefault("floor", 0)
        r.setdefault("skip", [])
        r.setdefault("openings", [])
        r.setdefault("kind", "autre")
    return merged


def interior(room):
    return (room["x"], room["y"], room["floor"], room["x"] + room["w"], room["y"] + room["d"], room["floor"] + room["h"])


def contains(room, p, margin=0.0):
    x0, y0, z0, x1, y1, z1 = interior(room)
    return x0 - margin <= p[0] <= x1 + margin and y0 - margin <= p[1] <= y1 + margin and z0 - margin <= p[2] <= z1 + margin


def wall_axis(room, side):
    """(interior length along the wall axis, start coordinate of the interior on that axis)."""
    return (room["w"], room["x"]) if side in ("south", "north") else (room["d"], room["y"])


def opening_center_outside(room, op, t):
    """Point just outside the opening (to guess the neighboring room)."""
    side = op["side"]
    c = (wall_axis(room, side)[1] + op["offset"] + op["width"] / 2.0)
    z = room["floor"] + op.get("sill", 0) + min(16, op.get("height", 16) / 2.0)
    far = t + 4
    if side == "south":
        return (c, room["y"] - far, z)
    if side == "north":
        return (c, room["y"] + room["d"] + far, z)
    if side == "west":
        return (room["x"] - far, c, z)
    return (room["x"] + room["w"] + far, c, z)


# ----------------------------------------------------------------------------- logic tests

def check(plan):
    errors, warns, infos = [], [], []
    rooms = plan["rooms"]
    t = plan["wall_thickness"]
    ids = [r["id"] for r in rooms]
    if len(set(ids)) != len(ids):
        errors.append("Duplicate room identifiers.")
    graph = {r["id"]: set() for r in rooms}
    exterior_doors = []

    for r in rooms:
        rid = r["id"]
        doors = [o for o in r["openings"] if o["type"] in ("door", "open")]
        windows = [o for o in r["openings"] if o["type"] == "window"]
        if r["kind"] in HABITABLE and not windows:
            warns.append("[%s] habitable room (%s) without a window: no natural light, no view of the outside." % (rid, r["kind"]))
        if r["h"] < 128 and r["kind"] not in ("cave", "vide_sanitaire", "conduit"):
            warns.append("[%s] ceiling at %s u (<128): oppressive and the jump hits the ceiling." % (rid, r["h"]))
        if min(r["w"], r["d"]) < 96 and r["kind"] not in ("conduit", "couloir"):
            warns.append("[%s] very narrow room (%sx%s): two players cannot pass each other." % (rid, r["w"], r["d"]))
        if r["kind"] == "couloir" and min(r["w"], r["d"]) < 64:
            warns.append("[%s] corridor < 64 u wide: two players cannot pass each other." % rid)

        by_side = {}
        for o in r["openings"]:
            if o["side"] not in SIDES:
                errors.append("[%s] unknown side '%s'." % (rid, o["side"]))
                continue
            length, _ = wall_axis(r, o["side"])
            h_open = o.get("height", 0)
            sill = o.get("sill", 0)
            if o["offset"] < 0 or o["offset"] + o["width"] > length:
                errors.append("[%s] opening %s exceeds wall %s (offset %s + width %s > %s)." % (rid, o["type"], o["side"], o["offset"], o["width"], length))
            if sill + h_open > r["h"]:
                errors.append("[%s] opening %s exceeds the ceiling." % (rid, o["type"]))
            if o["type"] == "door":
                if o["width"] < 48:
                    errors.append("[%s] door %s u wide: too narrow for the player (hull 32, minimum margin 48)." % (rid, o["width"]))
                elif o["width"] < 56:
                    warns.append("[%s] door %s u: passable but tight, 56-64 recommended." % (rid, o["width"]))
                if h_open < 96:
                    errors.append("[%s] door %s u tall: the player is 72 (36 crouched), minimum 96 for a credible look." % (rid, h_open))
                if sill != 0:
                    warns.append("[%s] door with a threshold at %s u: impassable step if > 18." % (rid, sill))
                    if sill > 18:
                        errors.append("[%s] door threshold > 18 u: impassable without jumping." % rid)
            if o["type"] == "window" and not (24 <= sill <= 56):
                warns.append("[%s] window sill at %s u: usual range is 32 to 48." % (rid, sill))
            by_side.setdefault(o["side"], []).append(o)

        for side, ops in by_side.items():
            ops = sorted(ops, key=lambda o: o["offset"])
            for a, b in zip(ops, ops[1:]):
                gap = b["offset"] - (a["offset"] + a["width"])
                if gap < 0:
                    errors.append("[%s] two openings overlap on wall %s." % (rid, side))
                elif gap < 16:
                    warns.append("[%s] pier of %s u between two openings (%s): wall too thin to hold." % (rid, gap, side))

        for o in doors:
            p = opening_center_outside(r, o, t)
            neighbor = next((n for n in rooms if n["id"] != rid and contains(n, p)), None)
            if neighbor:
                graph[rid].add(neighbor["id"])
                graph[neighbor["id"]].add(rid)
            else:
                exterior_doors.append(rid)

    for r in rooms:
        if not graph[r["id"]] and r["id"] not in exterior_doors:
            errors.append("[%s] no door (neither its own nor a neighbor's): room unreachable." % r["id"])

    for p in plan["props"]:
        pos = (p["x"], p["y"], p.get("z", 0))
        if not any(contains(r, pos, margin=t + 1) for r in rooms):
            warns.append("Prop %s at (%s, %s) outside any room." % (p["model"].split("/")[-1], p["x"], p["y"]))

    # connectivity from the spawns
    spawns = plan["spawns"]
    if not spawns:
        errors.append("No spawn defined.")
    start = []
    for s in spawns:
        pos = (s["x"], s["y"], s.get("z", 0) + 8)
        room = next((r for r in rooms if contains(r, pos)), None)
        start.append(room["id"] if room else None)
        if room is None:
            infos.append("Spawn (%s, %s) outside the rooms: treated as exterior (check that it is not inside a wall)." % (s["x"], s["y"]))
    seen = set()
    seeds = [i for i in start if i]
    if any(i is None for i in start):
        seeds += exterior_doors
    queue = deque(seeds)
    seen.update(queue)
    while queue:
        cur = queue.popleft()
        for n in graph[cur]:
            if n not in seen:
                seen.add(n)
                queue.append(n)
    for rid in ids:
        if rid not in seen:
            errors.append("[%s] unreachable from a spawn (door graph)." % rid)
    if rooms and not exterior_doors:
        warns.append("No door leading outside: the building is a closed box.")
    infos.append("%d rooms, %d openings, %d doors to the outside, %d props, %d spawns." % (
        len(rooms), sum(len(r["openings"]) for r in rooms), len(exterior_doors), len(plan["props"]), len(spawns)))
    return errors, warns, infos


# ----------------------------------------------------------------------------- brush construction

def split_wall(a0, a1, z0, z1, ops, make):
    """Cuts a wall [a0,a1] x [z0,z1] around its openings. make(a0,a1,zlo,zhi) -> Box."""
    boxes = []
    cur = a0
    for o in sorted(ops, key=lambda o: o["abs0"]):
        if o["abs0"] > cur:
            boxes.append(make(cur, o["abs0"], z0, z1))
        sill = o.get("sill", 0)
        head = sill + o.get("height", z1 - z0)
        if sill > 0:
            boxes.append(make(o["abs0"], o["abs1"], z0, z0 + sill))
        if z0 + head < z1:
            boxes.append(make(o["abs0"], o["abs1"], z0 + head, z1))
        cur = o["abs1"]
    if cur < a1:
        boxes.append(make(cur, a1, z0, z1))
    return boxes


def room_boxes(room, plan):
    t, tf, tc = plan["wall_thickness"], plan["floor_thickness"], plan["ceiling_thickness"]
    tex = plan["tex"]
    x, y, w, d, h, f = room["x"], room["y"], room["w"], room["d"], room["h"], room["floor"]
    skip = set(room["skip"])
    ext = {s: (0 if s in skip else t) for s in SIDES}
    fx0, fx1 = x - ext["west"], x + w + ext["east"]
    fy0, fy1 = y - ext["south"], y + d + ext["north"]
    boxes = [
        Box(fx0, fy0, f - tf, fx1, fy1, f, tex["floor"]),
        Box(fx0, fy0, f + h, fx1, fy1, f + h + tc, tex["ceiling"]),
    ]
    for side in SIDES:
        if side in skip:
            continue
        ops = []
        for o in room["openings"]:
            if o["side"] == side:
                o = dict(o)
                start = wall_axis(room, side)[1]
                o["abs0"], o["abs1"] = start + o["offset"], start + o["offset"] + o["width"]
                ops.append(o)
        z0, z1 = f, f + h
        if side in ("south", "north"):
            a0, a1 = fx0, fx1
            y0 = y - t if side == "south" else y + d
            make = lambda p, q, lo, hi, y0=y0: Box(p, y0, lo, q, y0 + t, hi, tex["wall"])
        else:
            a0, a1 = y, y + d
            x0 = x - t if side == "west" else x + w
            make = lambda p, q, lo, hi, x0=x0: Box(x0, p, lo, x0 + t, q, hi, tex["wall"])
        boxes += split_wall(a0, a1, z0, z1, ops, make)
    return [b for b in boxes if b.valid()]


def skybox_boxes(all_boxes, plan):
    m, th = plan["skybox_margin"], 16
    x0 = min(b.x0 for b in all_boxes) - m
    y0 = min(b.y0 for b in all_boxes) - m
    z0 = min(b.z0 for b in all_boxes) - m
    x1 = max(b.x1 for b in all_boxes) + m
    y1 = max(b.y1 for b in all_boxes) + m
    z1 = max(b.z1 for b in all_boxes) + m
    s = plan["tex"]["sky"]
    return [
        Box(x0 - th, y0 - th, z0 - th, x1 + th, y1 + th, z0, s),
        Box(x0 - th, y0 - th, z1, x1 + th, y1 + th, z1 + th, s),
        Box(x0 - th, y0 - th, z0, x0, y1 + th, z1, s),
        Box(x1, y0 - th, z0, x1 + th, y1 + th, z1, s),
        Box(x0, y0 - th, z0, x1, y0, z1, s),
        Box(x0, y1, z0, x1, y1 + th, z1, s),
    ]


class Ids:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return self.n


def solid_text(box, ids):
    out = ["\tsolid", "\t{", '\t\t"id" "%d"' % ids()]
    for normal, verts, u, v in box.faces():
        p = list(reversed(verts))[:3]  # Hammer expects clockwise order seen from outside
        out += ["\t\tside", "\t\t{", '\t\t\t"id" "%d"' % ids(), '\t\t\t"plane" "%s %s %s"' % tuple(pt(q) for q in p),
                '\t\t\t"material" "%s"' % box.tex, '\t\t\t"uaxis" "%s"' % u, '\t\t\t"vaxis" "%s"' % v,
                '\t\t\t"rotation" "0"', '\t\t\t"lightmapscale" "16"', '\t\t\t"smoothing_groups" "0"', "\t\t}"]
    out.append("\t}")
    return "\n".join(out)


def entity_text(classname, kv, ids):
    lines = ["entity", "{", '\t"id" "%d"' % ids(), '\t"classname" "%s"' % classname]
    lines += ['\t"%s" "%s"' % (k, v) for k, v in kv.items()]
    lines.append("}")
    return "\n".join(lines)


def build(plan):
    ids = Ids()
    boxes = []
    for r in plan["rooms"]:
        boxes += room_boxes(r, plan)
    if not boxes:
        raise SystemExit("Empty plan: no rooms.")
    boxes += skybox_boxes(boxes, plan)

    world = ["world", "{", '\t"id" "%d"' % ids(), '\t"mapversion" "1"', '\t"classname" "worldspawn"',
             '\t"skyname" "%s"' % plan["sky"], '\t"maxpropscreenwidth" "-1"', '\t"detailvbsp" "detail.vbsp"',
             '\t"detailmaterial" "detail/detailsprites"']
    world += [solid_text(b, ids) for b in boxes]
    world.append("}")

    ents = []
    sun = plan.get("sun", {})
    ents.append(entity_text("light_environment", {
        "_ambient": sun.get("ambient", "190 205 255 25"), "_ambientHDR": "-1 -1 -1 1", "_AmbientScaleHDR": "1",
        "_light": sun.get("light", "255 240 215 220"), "_lightHDR": "-1 -1 -1 1", "_lightscaleHDR": "1",
        "angles": "0 %s 0" % sun.get("yaw", 205), "pitch": sun.get("pitch", -50), "SunSpreadAngle": "0",
        "origin": "0 0 %s" % (max(b.z1 for b in boxes) - 64)}, ids))
    fog = (plan.get("atmosphere") or {}).get("fog")
    if fog:
        # Global fog (spawnflags 1 = master controller). Values to be judged in game.
        top = max(b.z1 for b in boxes) - 64
        ents.append(entity_text("env_fog_controller", {
            "fogenable": "1", "fogblend": "0", "spawnflags": "1",
            "fogcolor": fog.get("color", "128 128 128"), "fogcolor2": fog.get("color", "128 128 128"),
            "fogstart": str(fog.get("start", 512)), "fogend": str(fog.get("end", 4096)),
            "fogmaxdensity": str(fog.get("max_density", 0.8)), "farz": str(fog.get("farz", -1)),
            "origin": "0 0 %s" % top}, ids))
    for s in plan["spawns"]:
        ents.append(entity_text("info_player_start", {
            "angles": "0 %s 0" % s.get("yaw", 0), "origin": "%s %s %s" % (fmt(s["x"]), fmt(s["y"]), fmt(s.get("z", 0) + 8))}, ids))
    for r in plan["rooms"]:
        cx, cy = r["x"] + r["w"] / 2.0, r["y"] + r["d"] / 2.0
        ents.append(entity_text("env_cubemap", {"cubemapsize": "0", "sides": "",
                                                 "origin": "%s %s %s" % (fmt(cx), fmt(cy), fmt(r["floor"] + min(r["h"] / 2.0, 64)))}, ids))
    for p in plan["props"]:
        kv = {"angles": "0 %s 0" % p.get("yaw", 0), "fadescale": "1", "model": p["model"], "skin": str(p.get("skin", 0)),
              "solid": "6", "origin": "%s %s %s" % (fmt(p["x"]), fmt(p["y"]), fmt(p.get("z", 0)))}
        ents.append(entity_text(p.get("classname", "prop_static"), kv, ids))

    head = ('versioninfo\n{\n\t"editorversion" "400"\n\t"editorbuild" "8000"\n\t"mapversion" "1"\n\t"formatversion" "100"\n\t"prefab" "0"\n}\n'
            'visgroups\n{\n}\nviewsettings\n{\n\t"bSnapToGrid" "1"\n\t"bShowGrid" "1"\n\t"nGridSpacing" "8"\n}\n')
    tail = 'cameras\n{\n\t"activecamera" "-1"\n}\ncordons\n{\n\t"active" "0"\n}\n'
    return head + "\n".join(world) + "\n" + "\n".join(ents) + "\n" + tail


# ----------------------------------------------------------------------------- SVG mock-up

def svg(plan, scale=0.6):
    t = plan["wall_thickness"]
    rooms = plan["rooms"]
    if not rooms:
        raise SystemExit("Empty plan: no rooms.")
    xs = [r["x"] - t for r in rooms] + [r["x"] + r["w"] + t for r in rooms]
    ys = [r["y"] - t for r in rooms] + [r["y"] + r["d"] + t for r in rooms]
    xs += [e["x"] for e in plan["spawns"] + plan["props"]]
    ys += [e["y"] for e in plan["spawns"] + plan["props"]]
    minx, maxx, miny, maxy = min(xs) - 40, max(xs) + 40, min(ys) - 40, max(ys) + 40
    W, H = max((maxx - minx) * scale, 640), (maxy - miny) * scale + 44

    def X(v):
        return (v - minx) * scale

    def Y(v):  # north at the top
        return (maxy - v) * scale

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="sans-serif" font-size="11">' % (W, H, W, H),
           '<rect width="100%" height="100%" fill="#f4f1ea"/>']
    for r in rooms:
        x, y, w, d = r["x"], r["y"], r["w"], r["d"]
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fff" stroke="#333" stroke-width="%.1f"/>' % (X(x), Y(y + d), w * scale, d * scale, t * scale))
        out.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="#555">%s (%s)</text>' % (X(x + w / 2), Y(y + d / 2), r["id"], r["kind"]))
        for o in r["openings"]:
            start = wall_axis(r, o["side"])[1] + o["offset"]
            end = start + o["width"]
            col = {"door": "#a0642d", "window": "#5aa9e6", "open": "#cfe8c0"}.get(o["type"], "#999")
            if o["side"] in ("south", "north"):
                yy = y - t if o["side"] == "south" else y + d
                out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (X(start), Y(yy + t), (end - start) * scale, t * scale, col))
            else:
                xx = x - t if o["side"] == "west" else x + w
                out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>' % (X(xx), Y(end), t * scale, (end - start) * scale, col))
    for p in plan["props"]:
        out.append('<circle cx="%.1f" cy="%.1f" r="3" fill="#c0392b"><title>%s</title></circle>' % (X(p["x"]), Y(p["y"]), p["model"]))
    for s in plan["spawns"]:
        out.append('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="#2e8b57"/>' % (X(s["x"]), Y(s["y"]) - 7, X(s["x"]) - 6, Y(s["y"]) + 5, X(s["x"]) + 6, Y(s["y"]) + 5))
    out.append('<text x="8" y="%.0f" fill="#333" font-weight="bold">%s</text>' % (H - 26, plan.get("name", "plan")))
    out.append('<text x="8" y="%.0f" fill="#555">brown: door - blue: window - light green: passage - triangle: spawn - red: prop - north at the top</text>' % (H - 10))
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("check", "build", "svg"))
    ap.add_argument("plan")
    ap.add_argument("-o", "--output")
    args = ap.parse_args(argv)
    plan = load_plan(args.plan)

    if args.command == "check":
        errors, warns, infos = check(plan)
        for m in infos:
            print("INFO  ", m)
        for m in warns:
            print("WARN  ", m)
        for m in errors:
            print("ERROR", m)
        return 1 if errors else 0

    if args.command in ("build", "svg") and not args.output:
        ap.error("-o is required")
    if args.command == "build":
        errors, warns, _ = check(plan)
        for m in warns:
            print("WARN  ", m)
        if errors:
            for m in errors:
                print("ERROR", m)
            print("Build cancelled: fix the plan (or use 'check' for details).")
            return 1
        with open(args.output, "w", encoding="utf-8", newline="\n") as f:
            f.write(build(plan))
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(svg(plan))
    print("OK ->", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
