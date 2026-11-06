"""VMF analysis: structure, optimization advice and trigger/logic graph."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from . import kv, logic

TOOL_TEX = {
    "tools/toolsnodraw": "nodraw", "tools/toolsskip": "skip", "tools/toolshint": "hint",
    "tools/toolsareaportal": "areaportal", "tools/toolsoccluder": "occluder",
    "tools/toolsclip": "clip", "tools/toolsplayerclip": "playerclip",
    "tools/toolsnpcclip": "npcclip", "tools/toolstrigger": "trigger",
    "tools/toolsskybox": "skybox", "tools/toolsskybox2d": "skybox2d",
    "tools/toolsblocklight": "blocklight", "tools/toolsinvisible": "invisible",
    "tools/toolsfog": "fog", "tools/toolsblockbullets": "blockbullets",
    "tools/toolsdotted": "dotted", "tools/toolsorigin": "origin",
}
MAP_LIMIT = 16384.0


def _vec(s: str | None):
    m = re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", s or "")
    return [float(x) for x in m[:3]] if len(m) >= 3 else None


def _plane_pts(s: str):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", s)]


def _solid_info(solid: kv.Node):
    mats, bounds_min, bounds_max, disp = Counter(), [1e9] * 3, [-1e9] * 3, False
    for side in solid.blocks("side"):
        mats[(side.get("material") or "").lower()] += 1
        if side.block("dispinfo"):
            disp = True
        p = _plane_pts(side.get("plane") or "")
        for i in range(0, len(p) - 2, 3):
            for a in range(3):
                bounds_min[a] = min(bounds_min[a], p[i + a])
                bounds_max[a] = max(bounds_max[a], p[i + a])
    return mats, bounds_min, bounds_max, disp


def load(path: str | Path) -> list[kv.Node]:
    return kv.parse(Path(path).read_text(encoding="utf-8", errors="replace"))


def extract_entities(roots: list[kv.Node]) -> list[dict]:
    out = []
    for e in (r for r in roots if r.name.lower() == "entity"):
        if True:
            conns = []
            cb = e.block("connections")
            if cb:
                for o, v in cb.props:
                    s = logic.split_output(v)
                    if s:
                        conns.append((o,) + s)
            keys = {k: v for k, v in e.props}
            out.append({"classname": e.get("classname") or "", "targetname": e.get("targetname") or "",
                        "origin": _vec(e.get("origin")), "keys": keys, "outputs": conns,
                        "solids": len(e.blocks("solid")), "id": e.get("id"), "_node": e})
    return out


def analyze(path: str | Path) -> dict:
    roots = load(path)
    world = next((r for r in roots if r.name.lower() == "world"), None)
    if world is None:
        return {"error": "no world block: not a VMF?"}
    ents = extract_entities(roots)
    mats = Counter()
    brushes = disp = 0
    mn, mx = [1e9] * 3, [-1e9] * 3
    for s in world.blocks("solid"):
        m, a, b, d = _solid_info(s)
        mats.update(m)
        brushes += 1
        disp += int(d)
        for i in range(3):
            mn[i], mx[i] = min(mn[i], a[i]), max(mx[i], b[i])
    detail_brushes = tool_counts = None
    detail_brushes = 0
    ent_brushes = Counter()
    for e in ents:
        if e["solids"]:
            ent_brushes[e["classname"]] += e["solids"]
        if e["classname"] == "func_detail":
            detail_brushes += e["solids"]
    tools = Counter()
    for m, c in mats.items():
        if m in TOOL_TEX:
            tools[TOOL_TEX[m]] += c
    classes = Counter(e["classname"] for e in ents)
    structural = brushes
    total_brushes = structural + sum(ent_brushes.values())
    advice, risks = [], []
    spawns = classes.get("info_player_start", 0) + classes.get("info_player_teamspawn", 0)
    if not spawns:
        risks.append("No info_player_start: map cannot be played.")
    if not classes.get("light_environment") and not classes.get("light_directional"):
        advice.append("No light_environment: outdoor lighting will be wrong.")
    if not classes.get("env_cubemap"):
        advice.append("No env_cubemap: reflective materials fall back to the default cubemap.")
    if not classes.get("sky_camera"):
        advice.append("No sky_camera: no 3D skybox (fine for pure 2D sky maps).")
    if structural and detail_brushes / max(1, structural + detail_brushes) < 0.5 and structural > 200:
        advice.append(f"Only {detail_brushes} of {structural + detail_brushes} world-ish brushes are func_detail. "
                      "Everything non-structural (props-as-brushes, trim, stairs, clutter) should be func_detail "
                      "to cut vis leaves and vvis time.")
    if structural > 200 and not classes.get("func_areaportal") and not classes.get("func_areaportalwindow"):
        advice.append("No areaportals: interiors cannot be culled; add func_areaportal in door frames.")
    if structural > 600 and not tools.get("hint"):
        advice.append("No hint brushes: large maps often need hint/skip to cut long sightlines (verify with r_visocclusion / PVS in game).")
    if classes.get("prop_dynamic", 0) > 300:
        advice.append(f"{classes['prop_dynamic']} prop_dynamic: convert non-animated ones to prop_static (huge render + entity saving).")
    if classes.get("func_brush", 0) > 150:
        advice.append("Many func_brush: each is an entity and a render batch; merge or use func_detail if not toggled.")
    if sum(1 for a, b in zip(mn, mx) if b - a > 2 * MAP_LIMIT) or any(v > MAP_LIMIT or v < -MAP_LIMIT for v in mn + mx if abs(v) < 1e8):
        risks.append("Geometry outside +/-16384: compile will fail or brushes get dropped.")
    nodraw_ratio = tools.get("nodraw", 0) / max(1, sum(mats.values()))
    ents_clean = [{k: v for k, v in e.items() if k != "_node"} for e in ents]
    io = logic.analyze(ents_clean)
    if io["broken_connection_count"]:
        risks.append(f"{io['broken_connection_count']} I/O connections target a name that does not exist.")
    if io["dangling_key_count"]:
        risks.append(f"{io['dangling_key_count']} entity keys (target/parentname/...) point to missing names.")
    return {
        "file": str(path),
        "world_brushes": brushes, "displacements": disp, "entity_brushes": dict(ent_brushes),
        "func_detail_brushes": detail_brushes,
        "world_bounds": {"min": mn if brushes else None, "max": mx if brushes else None},
        "tool_textures": dict(tools), "nodraw_face_ratio": round(nodraw_ratio, 3),
        "distinct_materials": len(mats), "top_materials": mats.most_common(15),
        "entity_total": len(ents), "prop_static": classes.get("prop_static", 0),
        "spawns": spawns, "io": io, "naming": logic.naming_convention_report(ents_clean),
        "risks": risks, "advice": advice,
    }


def _kv_fmt(n: kv.Node, depth=0) -> str:
    t = "\t" * depth
    s = f'{t}{n.name}\n{t}{{\n'
    for k, v in n.props:
        s += f'{t}\t"{k}" "{v}"\n'
    for c in n.children:
        s += _kv_fmt(c, depth + 1)
    return s + f"{t}}}\n"


def entity_vmf_text(path: str | Path, targetname: str) -> str:
    roots = load(path)
    out = [_kv_fmt(e["_node"]) for e in extract_entities(roots) if e["targetname"] == targetname]
    return "\n".join(out) or f"no entity named {targetname!r}"
