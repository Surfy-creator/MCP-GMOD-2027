"""MCP server: Hammer / Hammer++ / GMod knowledge, map analysis and compile planning."""
from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import bsp, compile as comp, corpus, env, fgd, knowledge, logic, vmf

ROOT = Path(__file__).resolve().parents[2]
mcp = FastMCP("gmod-hammer")


def _fgd_db():
    return fgd.load(tuple(env.detect().get("fgds", [])))


def _entities(path: str) -> list[dict]:
    p = Path(path)
    if p.suffix.lower() == ".bsp":
        return bsp.entities(p.read_bytes(), bsp.read_header(p.read_bytes()))
    ents = vmf.extract_entities(vmf.load(p))
    return [{k: v for k, v in e.items() if k != "_node"} for e in ents]


@mcp.tool()
def detect_environment() -> dict:
    """Find GarrysMod, Hammer, Hammer++, vbsp/vvis/vrad, studiomdl, bspzip and FGDs on this machine."""
    return env.detect()


@mcp.tool()
def fgd_search(query: str, limit: int = 25) -> list[dict]:
    """Search entity classes (name or description) in the installed FGDs (garrysmod/base/halflife2/Hammer++)."""
    return fgd.search(_fgd_db(), query, limit)


@mcp.tool()
def fgd_entity(classname: str) -> dict:
    """Full definition of an entity with inherited keyvalues, inputs and outputs resolved."""
    r = fgd.resolve(_fgd_db(), classname)
    return r or {"error": f"{classname} not found in installed FGDs"}


@mcp.tool()
def vmf_analyze(path: str) -> dict:
    """Analyze a .vmf: brush/detail balance, tool textures, entity histogram, I/O graph health, optimization advice."""
    return vmf.analyze(path)


@mcp.tool()
def bsp_analyze(path: str) -> dict:
    """Analyze a compiled .bsp: lump sizes, engine-limit usage, vis clusters, lighting, pakfile, entity/I-O health."""
    r = bsp.analyze(path)
    r["entity_summary"]["static_props"] = bsp.static_prop_count(path)
    r["entity_summary"].pop("prop_static_in_game_lump", None)
    return r


@mcp.tool()
def io_graph(path: str, include_edges: bool = False, entity: str = "") -> dict:
    """Trigger/logic graph of a .vmf or .bsp. Set `entity` (targetname) to list what it fires and what fires it."""
    ents = _entities(path)
    out = logic.analyze(ents)
    flat = []
    for e in ents:
        for o, t, i, p, d, r in e["outputs"]:
            flat.append({"from": e["targetname"] or f"<{e['classname']}>", "output": o, "to": t, "input": i, "param": p, "delay": d, "refire": r})
    if entity:
        out["fires"] = [x for x in flat if x["from"] == entity]
        out["fired_by"] = [x for x in flat if x["to"] == entity]
    elif include_edges:
        out["edges"] = flat[:500]
    return out


@mcp.tool()
def trigger_recipe(name: str = "") -> dict:
    """Vetted trigger/logic patterns (button_door, one_shot_event, filtered_zone, counter_puzzle, teleporter, timed_sequence). Empty name lists them."""
    if not name:
        return {k: v["purpose"] for k, v in knowledge.RECIPES.items()}
    return knowledge.RECIPES.get(name) or {"error": f"unknown recipe; options: {sorted(knowledge.RECIPES)}"}


@mcp.tool()
def mapping_rules(topic: str = "") -> dict:
    """Structure/optimization/Hammer++ workflow rules. topics: naming, io_hygiene, optimization_order, rp_city_structure, hammerpp_workflow."""
    if topic:
        return {topic: knowledge.RULES.get(topic, f"unknown; options: {sorted(knowledge.RULES)}")}
    return knowledge.RULES


@mcp.tool()
def rp_scorecard(path: str) -> dict:
    """Score a .vmf or .bsp (0-100) on structure, logic hygiene, limits and completeness with reasons. Heuristic, not a verdict."""
    p = Path(path)
    score, notes = 100, []

    def hit(pts, msg):
        nonlocal score
        score -= pts
        notes.append(f"-{pts}: {msg}")

    if p.suffix.lower() == ".bsp":
        r = bsp.analyze(p)
        io = r["io"]
        for n, c in r["element_counts"].items():
            if c["pct"] >= 90:
                hit(15, f"{n} at {c['pct']}% of limit")
            elif c["pct"] >= 75:
                hit(6, f"{n} at {c['pct']}%")
        if r["element_counts"]["CUBEMAPS"]["count"] < 3 and r["element_counts"]["FACES"]["count"] > 5000:
            hit(5, "very few cubemaps for a big map")
        if not r["lighting"]["ldr"] and not r["lighting"]["hdr"]:
            hit(15, "no lightmaps compiled (fullbright)")
        if r["visibility"]["clusters"] <= 1 and r["element_counts"]["FACES"]["count"] > 3000:
            hit(15, "no vis data (compiled without vvis?)")
        naming = r["naming"]
    else:
        r = vmf.analyze(p)
        io = r["io"]
        for msg in r["risks"]:
            hit(12, msg)
        for msg in r["advice"]:
            hit(4, msg)
        naming = r["naming"]
    if io["broken_connection_count"]:
        hit(min(15, 3 + io["broken_connection_count"]), f"{io['broken_connection_count']} connections to missing targets")
    if io["dangling_key_count"]:
        hit(min(10, 2 + io["dangling_key_count"]), f"{io['dangling_key_count']} dangling target keys")
    if io["duplicate_targetname_count"] > 20:
        hit(3, "many duplicated targetnames (fine for groups, risky for single targets)")
    if naming["named"] > 30 and naming["convention_ratio"] < 0.5:
        hit(5, f"naming convention ratio {naming['convention_ratio']} (<0.5)")
    return {"score": max(0, score), "deductions": notes, "naming": naming,
            "logic_classes": io["logic_classes_present"][:20],
            "disclaimer": "Heuristic from static data; verify in game."}


@mcp.tool()
def compile_plan(vmf_path: str, profile: str = "fast", threads: int = 0) -> dict:
    """Return the vbsp/vvis/vrad command lines for a profile (fast, medium, final, entities_only). Does not execute."""
    return comp.plan(env.detect(), vmf_path, profile, threads or None)


@mcp.tool()
def compile_run(vmf_path: str, profile: str = "fast", confirm: bool = False) -> dict:
    """Execute the compile plan (writes .bsp/.prt/.lin next to the VMF). Requires confirm=true; stops at the first leak."""
    pl = comp.plan(env.detect(), vmf_path, profile)
    if not confirm:
        return {"dry_run": True, "plan": pl, "hint": "Call again with confirm=true to execute."}
    return comp.run(pl)


@mcp.tool()
def compile_log_parse(log_text: str) -> dict:
    """Extract leaks, errors, overflows and tail from a vbsp/vvis/vrad log."""
    return comp.parse_log(log_text)


@mcp.tool()
def reference_maps() -> dict:
    """Manifest of the 36-map DarkRP reference collection (titles/authors only) and map families."""
    return json.loads((ROOT / "knowledge" / "reference_maps.json").read_text(encoding="utf-8"))


@mcp.tool()
def reference_profiles() -> dict:
    """Saved benchmark profiles (JSON from bsp_analyze) in knowledge/profiles, summarized for comparison."""
    out = {}
    for f in sorted((ROOT / "knowledge" / "profiles").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out[f.stem] = {k: d.get(k) for k in ("size_mb", "visibility", "lighting", "pakfile_files", "entities", "faces", "limits_max_pct", "static_props", "connections")}
    return out


@mcp.tool()
def corpus_summary() -> dict:
    """Min/quartiles/median/max of 37 profiled DarkRP-style maps (size, faces, clusters, entities, props, cubemaps, areaportals, pak, I/O, lights, doors)."""
    return corpus.summary()


@mcp.tool()
def benchmark_map(bsp_path: str) -> dict:
    """Percentile-rank a compiled BSP against the profiled RP corpus on each metric (heuristic: a high rank is not 'bad')."""
    import tempfile  # noqa: F401  (profile built in-memory, nothing written)
    r = bsp.analyze(bsp_path)
    io_ = r["io"]
    prof = {"size_mb": r["size_mb"], "faces": r["element_counts"]["FACES"]["count"], "visibility": r["visibility"],
            "entities": r["entity_summary"]["total"], "static_props": bsp.static_prop_count(bsp_path),
            "element_counts": r["element_counts"], "pakfile_mb": round(r["pakfile"]["bytes"] / 1048576, 1),
            "connections": io_["connections"], "class_histogram_top": io_["class_histogram"]}
    return corpus.rank(prof)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
