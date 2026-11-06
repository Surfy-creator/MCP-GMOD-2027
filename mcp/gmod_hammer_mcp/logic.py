"""Entity I/O (trigger/logic) graph analysis shared by the VMF and BSP readers.

An *entity* here is ``{"classname", "targetname", "outputs": [(output, target,
input, param, delay, refire)], "keys": {...}}``.
"""
from __future__ import annotations

from collections import Counter, defaultdict

# Keys whose value is a reference to another entity's targetname.
TARGET_KEYS = {
    "target", "parentname", "filtername", "lightingorigin", "landmark",
    "newtargetname", "targetentityname", "attach1", "attach2", "viewtarget",
    "destination", "teleport_destination", "master", "movewith", "glowtarget",
}
SPECIAL_TARGETS = {"!self", "!activator", "!caller", "!player", "!picker", "!pvsplayer", "!speaker", ""}


def split_output(value: str) -> tuple[str, str, str, float, int] | None:
    sep = "\x1b" if "\x1b" in value else ","
    p = value.split(sep)
    if len(p) < 2:
        return None
    p += [""] * (5 - len(p))
    try:
        delay = float(p[3] or 0)
    except ValueError:
        delay = 0.0
    try:
        refire = int(float(p[4] or -1))
    except ValueError:
        refire = -1
    return p[0], p[1], p[2], delay, refire


def analyze(entities: list[dict]) -> dict:
    names = Counter(e["targetname"] for e in entities if e.get("targetname"))
    defined = set(names)
    classes = Counter(e["classname"] for e in entities)
    edges = []
    for e in entities:
        for out, tgt, inp, par, delay, refire in e.get("outputs", []):
            edges.append({"from": e.get("targetname") or f"<{e['classname']}>",
                          "from_class": e["classname"], "output": out,
                          "to": tgt, "input": inp, "param": par,
                          "delay": delay, "refire": refire})
    broken = []
    for ed in edges:
        t = ed["to"]
        if t in SPECIAL_TARGETS or t in defined:
            continue
        if "*" in t:  # wildcard
            prefix = t.replace("*", "")
            if any(n.startswith(prefix) or n.endswith(prefix) for n in defined):
                continue
        broken.append(ed)
    dangling_keys = []
    for e in entities:
        for k, v in e.get("keys", {}).items():
            if k.lower() in TARGET_KEYS and v and v not in SPECIAL_TARGETS and v not in defined:
                if "*" in v:
                    continue
                dangling_keys.append({"entity": e.get("targetname") or e["classname"], "key": k, "value": v})
    referenced = {ed["to"] for ed in edges}
    for e in entities:
        for k, v in e.get("keys", {}).items():
            if k.lower() in TARGET_KEYS and v:
                referenced.add(v)
    unreferenced = sorted(n for n in defined if n not in referenced)
    dup = sorted(n for n, c in names.items() if c > 1)
    fan_out = defaultdict(int)
    for ed in edges:
        fan_out[ed["from"]] += 1
    hubs = sorted(fan_out.items(), key=lambda kv: -kv[1])[:10]
    long_delays = [ed for ed in edges if ed["delay"] >= 30]
    triggers = sorted(c for c in classes if c.startswith("trigger_") or c.startswith("logic_")
                      or c in ("func_button", "func_door", "func_door_rotating", "func_movelinear",
                               "func_rotating", "func_tracktrain", "func_brush", "func_breakable",
                               "func_areaportal", "func_areaportalwindow", "env_fade", "point_template",
                               "math_counter", "game_text", "ambient_generic", "prop_door_rotating"))
    return {
        "entity_count": len(entities),
        "class_histogram": dict(classes.most_common()),
        "named_entities": len(defined),
        "connections": len(edges),
        "broken_connections": broken[:50],
        "broken_connection_count": len(broken),
        "dangling_target_keys": dangling_keys[:50],
        "dangling_key_count": len(dangling_keys),
        "unreferenced_named_entities": unreferenced[:50],
        "unreferenced_count": len(unreferenced),
        "duplicate_targetnames_sample": dup[:30],
        "duplicate_targetname_count": len(dup),
        "io_hubs": hubs,
        "connections_with_delay_ge_30s": long_delays[:20],
        "logic_classes_present": triggers,
    }


def naming_convention_report(entities: list[dict]) -> dict:
    """Heuristic: do targetnames follow a prefix convention (e.g. bank_door_01)?"""
    names = [e["targetname"] for e in entities if e.get("targetname")]
    if not names:
        return {"named": 0, "convention_ratio": 0.0, "prefixes": {}}
    pref = Counter(n.split("_")[0].lower() for n in names if "_" in n)
    structured = sum(c for p, c in pref.items() if c >= 2)
    return {"named": len(names), "convention_ratio": round(structured / len(names), 2),
            "prefixes": dict(pref.most_common(12))}
