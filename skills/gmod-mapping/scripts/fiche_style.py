#!/usr/bin/env python3
"""Style sheet (art direction) for Garry's Mod: validate, apply to a plan, print.

The style sheet is the result of analyzing an image or a sentence (art direction pillar from reference 02).
It becomes concrete Source settings by being injected into a vmf_blockout.py JSON plan.

Commands:
  check  fiche.json                          -> schema and art direction consistency check
  apply  fiche.json plan.json -o plan2.json  -> injects sky, sun, ambient, fog, textures
  card   fiche.json [-o fiche.md]            -> readable sheet (Markdown) to show to the user
  --selftest                                 -> verifies that the checks reject a defective sheet

Exit code: 0 = nothing blocking, 1 = errors.
Format: see assets/fiche_style_exemple.json and references/08-pipeline-et-mcp.md.
"""
import argparse
import copy
import json
import re
import sys

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
ROLES = ("dominante", "secondaire", "accent")
SCHEMA_VERSION = 1


def hex_to_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def luminance(rgb):
    """Approximate relative luminance (0..1), sufficient to judge a value contrast."""
    r, g, b = (c / 255.0 for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def warmth(rgb):
    """> 0: warm (red/yellow dominates blue); < 0: cool."""
    r, _, b = rgb
    return (r - b) / 255.0


# ----------------------------------------------------------------------------- check

def check(fiche):
    """Returns (errors, warnings, infos)."""
    err, warn, info = [], [], []

    if fiche.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        err.append("schema_version %r not supported (expected %d)." % (fiche.get("schema_version"), SCHEMA_VERSION))
    for key in ("nom", "mots", "palette", "materiaux", "lumiere"):
        if key not in fiche:
            err.append("Missing required field: %s." % key)
    if err:
        return err, warn, info

    mots = fiche["mots"]
    if not isinstance(mots, list) or len(mots) != 3:
        err.append("\"mots\" must contain exactly three words (art direction pillar).")

    pal = fiche["palette"]
    if not isinstance(pal, list) or not 3 <= len(pal) <= 5:
        err.append("The palette must have 3 to 5 colors.")
        pal = pal if isinstance(pal, list) else []
    total, roles = 0, set()
    for i, c in enumerate(pal):
        if not HEX.match(str(c.get("hex", ""))):
            err.append("Palette[%d]: invalid hexadecimal color (%r), format #RRGGBB." % (i, c.get("hex")))
            continue
        total += c.get("part", 0)
        if c.get("role") in ROLES:
            roles.add(c["role"])
    if pal and not {"dominante", "accent"} <= roles:
        warn.append("Palette: missing a \"dominante\" and/or \"accent\" role; the accent guides the eye.")
    if pal and total and not 90 <= total <= 110:
        warn.append("Palette: shares add up to %d %% (expected ~100, 60/30/10 guideline)." % total)
    lums = [luminance(hex_to_rgb(c["hex"])) for c in pal if HEX.match(str(c.get("hex", "")))]
    if len(lums) >= 2 and max(lums) - min(lums) < 0.25:
        warn.append("Palette: values too close (luminance gap %.2f); the player reads light/dark first."
                    % (max(lums) - min(lums)))

    mats = fiche["materiaux"]
    if not isinstance(mats, list) or not 1 <= len(mats) <= 4:
        warn.append("Dominant materials: 2-3 recommended (%s provided)." % (len(mats) if isinstance(mats, list) else "?"))

    lum = fiche["lumiere"]
    sol = lum.get("soleil")
    amb = lum.get("ambiant")
    if not sol:
        err.append("lumiere.soleil missing (couleur, intensite, yaw, pitch).")
    else:
        if not HEX.match(str(sol.get("couleur", ""))):
            err.append("lumiere.soleil.couleur invalid (format #RRGGBB).")
        if not 0 < sol.get("intensite", 0) <= 1000:
            err.append("lumiere.soleil.intensite out of range (1-1000; guideline day 200-400, night 10-60).")
        if not -90 <= sol.get("pitch", -50) <= 0:
            err.append("lumiere.soleil.pitch must be between -90 (zenith) and 0 (horizon).")
    if amb:
        if not HEX.match(str(amb.get("couleur", ""))):
            err.append("lumiere.ambiant.couleur invalid (format #RRGGBB).")
        elif sol and HEX.match(str(sol.get("couleur", ""))):
            ws, wa = warmth(hex_to_rgb(sol["couleur"])), warmth(hex_to_rgb(amb["couleur"]))
            if ws * wa > 0 and abs(ws) > 0.1 and abs(wa) > 0.1:
                info.append("Sun and ambient have the same temperature: flatter look than a warm/cool contrast "
                            "(a possible choice, to be owned in the statement of intent).")
        if sol and amb.get("intensite", 0) >= sol.get("intensite", 1):
            warn.append("Ambient as strong as the sun: shadows will disappear.")

    fog = fiche.get("brouillard")
    if fog:
        if not HEX.match(str(fog.get("couleur", ""))):
            err.append("brouillard.couleur invalid (format #RRGGBB).")
        if fog.get("debut", 0) >= fog.get("fin", 1):
            err.append("brouillard: debut must be less than fin (Source units).")
        if not 0 < fog.get("densite_max", 0.8) <= 1:
            err.append("brouillard.densite_max must be in ]0 ; 1].")

    for k in ("textures",):
        for role, path in (fiche.get(k) or {}).items():
            if role not in ("wall", "floor", "ceiling"):
                warn.append("textures.%s: unknown role (wall, floor, ceiling)." % role)
            if str(path).lower().endswith((".vmt", ".vtf")) or str(path).startswith("materials/"):
                err.append("textures.%s: path relative to materials/, without extension (e.g. BRICK/BRICKWALL031A)." % role)
    refs = fiche.get("references_visuelles") or []
    if len(refs) < 3:
        warn.append("references_visuelles: %d entry(ies), at least 3 expected (user images, reference maps, "
                    "Street View, photos); see references/09 section 1." % len(refs))
    for i, r in enumerate(refs):
        if not r.get("source") or not r.get("retenu"):
            warn.append("references_visuelles[%d]: provide \"source\" and \"retenu\" (what is taken from it)." % i)
    if not fiche.get("ciel"):
        info.append("No \"ciel\": the plan will keep its current skyname.")
    info.append("Style sheet \"%s\": %d colors, %d materials." % (fiche["nom"], len(pal), len(mats) if isinstance(mats, list) else 0))
    return err, warn, info


# ----------------------------------------------------------------------------- application

def apply(fiche, plan):
    """Returns a copy of the plan with the style sheet's Source settings."""
    out = copy.deepcopy(plan)
    lum = fiche["lumiere"]
    sol = lum["soleil"]
    sun = dict(out.get("sun", {}))
    sun["light"] = "%d %d %d %d" % (hex_to_rgb(sol["couleur"]) + (sol["intensite"],))
    sun["yaw"] = sol.get("yaw", sun.get("yaw", 205))
    sun["pitch"] = sol.get("pitch", sun.get("pitch", -50))
    amb = lum.get("ambiant")
    if amb:
        sun["ambient"] = "%d %d %d %d" % (hex_to_rgb(amb["couleur"]) + (amb.get("intensite", 25),))
    out["sun"] = sun
    if fiche.get("ciel"):
        out["sky"] = fiche["ciel"]
    if fiche.get("textures"):
        out["tex"] = dict(out.get("tex", {}), **fiche["textures"])
    fog = fiche.get("brouillard")
    if fog:
        out.setdefault("atmosphere", {})["fog"] = {
            "color": "%d %d %d" % hex_to_rgb(fog["couleur"]),
            "start": fog["debut"], "end": fog["fin"], "max_density": fog.get("densite_max", 0.8)}
    out["style"] = fiche["nom"]
    return out


# ----------------------------------------------------------------------------- readable sheet

def card(fiche):
    lum = fiche["lumiere"]
    lines = ["# Style sheet: %s" % fiche["nom"], "",
             "**Pillar**: %s" % ", ".join(fiche["mots"]), ""]
    if fiche.get("source"):
        lines += ["**Source**: %s" % fiche["source"], ""]
    if fiche.get("references"):
        lines += ["**References**: %s" % "; ".join(fiche["references"]), ""]
    if fiche.get("references_visuelles"):
        lines += ["## Reference board", "", "| Source | What is kept |", "|---|---|"]
        lines += ["| %s | %s |" % (r.get("source", "?"), r.get("retenu", "?")) for r in fiche["references_visuelles"]]
        lines.append("")
    lines += ["## Palette", "", "| Color | Role | Share | Usage |", "|---|---|---|---|"]
    for c in fiche["palette"]:
        lines.append("| `%s` | %s | %s %% | %s |" % (c["hex"], c.get("role", "-"), c.get("part", "-"), c.get("usage", "")))
    lines += ["", "## Materials and condition", "", "- Materials: %s" % ", ".join(fiche["materiaux"]),
              "- Condition: %s" % fiche.get("etat", "not specified"), "", "## Lighting and atmosphere", "",
              "- Time: %s, weather: %s" % (lum.get("heure", "?"), lum.get("meteo", "?")),
              "- Sun: %s, intensity %s, yaw %s, pitch %s" % (lum["soleil"]["couleur"], lum["soleil"]["intensite"],
                                                                 lum["soleil"].get("yaw", "-"), lum["soleil"].get("pitch", "-"))]
    if lum.get("ambiant"):
        lines.append("- Ambient: %s, intensity %s" % (lum["ambiant"]["couleur"], lum["ambiant"].get("intensite", "-")))
    if fiche.get("brouillard"):
        f = fiche["brouillard"]
        lines.append("- Fog: %s, from %s to %s u, max density %s" % (f["couleur"], f["debut"], f["fin"], f.get("densite_max", 0.8)))
    if fiche.get("ciel"):
        lines.append("- Sky: `%s`" % fiche["ciel"])
    if fiche.get("props_preferes"):
        lines += ["", "## Props and details", ""] + ["- %s" % p for p in fiche["props_preferes"]]
    if fiche.get("a_eviter"):
        lines += ["", "## To avoid", ""] + ["- %s" % p for p in fiche["a_eviter"]]
    lines += ["", "_Settings to be judged in game (screenshots): the sheet sets an intention, not a guaranteed result._"]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------- CLI

def report(err, warn, info):
    for m in err:
        print("ERROR " + m)
    for m in warn:
        print("WARNING " + m)
    for m in info:
        print("INFO   " + m)
    return 1 if err else 0


def selftest():
    good = {"nom": "test", "mots": ["a", "b", "c"], "materiaux": ["brique", "bois"],
            "palette": [{"hex": "#202020", "role": "dominante", "part": 60},
                        {"hex": "#808080", "role": "secondaire", "part": 30},
                        {"hex": "#F0C040", "role": "accent", "part": 10}],
            "lumiere": {"soleil": {"couleur": "#FFD8A0", "intensite": 300, "yaw": 200, "pitch": -40},
                        "ambiant": {"couleur": "#8090C0", "intensite": 30}},
            "brouillard": {"couleur": "#90A0B0", "debut": 256, "fin": 3000, "densite_max": 0.6},
            "textures": {"wall": "BRICK/BRICKWALL031A"},
            "references_visuelles": [{"source": "s%d" % i, "retenu": "r"} for i in range(3)]}
    e, w, _ = check(good)
    assert not e, e
    assert not any("references_visuelles" in m for m in w), w
    nodoc = copy.deepcopy(good)
    nodoc["references_visuelles"] = [{"source": "x"}]
    _, w, _ = check(nodoc)
    assert sum("references_visuelles" in m for m in w) == 2, w
    bad = copy.deepcopy(good)
    bad["mots"] = ["a"]
    bad["palette"][0]["hex"] = "rouge"
    bad["lumiere"]["soleil"]["pitch"] = 30
    bad["brouillard"]["debut"] = 5000
    bad["textures"]["wall"] = "materials/brick.vmt"
    e, _, _ = check(bad)
    assert len(e) == 5, e
    flat = copy.deepcopy(good)
    for c in flat["palette"]:
        c["hex"] = "#777777"
    _, w, _ = check(flat)
    assert any("values too close" in m for m in w), w
    plan = {"name": "p", "rooms": [], "sun": {"yaw": 1}, "tex": {"floor": "X/Y"}}
    p2 = apply(good, plan)
    assert p2["sun"]["light"] == "255 216 160 300" and p2["sun"]["ambient"] == "128 144 192 30", p2["sun"]
    assert p2["tex"] == {"floor": "X/Y", "wall": "BRICK/BRICKWALL031A"}, p2["tex"]
    assert p2["atmosphere"]["fog"]["color"] == "144 160 176" and plan["sun"] == {"yaw": 1}
    assert "# Style sheet: test" in card(good)
    print("selftest OK: valid sheet accepted, defective sheet rejected (5 errors), flat palette flagged, undocumented sheet flagged, "
          "plan injection correct and free of side effects.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check")
    c.add_argument("fiche")
    a = sub.add_parser("apply")
    a.add_argument("fiche")
    a.add_argument("plan")
    a.add_argument("-o", "--out", required=True)
    k = sub.add_parser("card")
    k.add_argument("fiche")
    k.add_argument("-o", "--out")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.cmd:
        ap.print_help()
        return 1
    with open(args.fiche, encoding="utf-8") as f:
        fiche = json.load(f)
    err, warn, info = check(fiche)
    if args.cmd == "check":
        return report(err, warn, info)
    if err:
        report(err, warn, info)
        print("Style sheet rejected: fix the errors before applying it.")
        return 1
    if args.cmd == "apply":
        with open(args.plan, encoding="utf-8") as f:
            plan = json.load(f)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(apply(fiche, plan), f, ensure_ascii=False, indent=2)
        report([], warn, [])
        print("OK -> %s" % args.out)
        return 0
    text = card(fiche)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("OK -> %s" % args.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
