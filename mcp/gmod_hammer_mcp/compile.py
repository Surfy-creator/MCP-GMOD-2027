"""Compile command planning and log parsing (vbsp -> vvis -> vrad)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

PROFILES = {
    # fast: iteration while building. final: release quality.
    "fast": {"vbsp": [], "vvis": ["-fast"], "vrad": ["-fast", "-bounce", "1", "-noextra"]},
    "medium": {"vbsp": [], "vvis": [], "vrad": ["-bounce", "4", "-final"]},
    "final": {"vbsp": [], "vvis": [], "vrad": ["-final", "-StaticPropLighting", "-StaticPropPolys", "-hdr"]},
    "entities_only": {"vbsp": ["-onlyents"], "vvis": None, "vrad": None},
}


def plan(env: dict, vmf: str, profile: str = "fast", threads: int | None = None) -> dict:
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of {sorted(PROFILES)}")
    if not env.get("vbsp"):
        raise ValueError("vbsp not found; set GMOD_PATH")
    game = env["gamedir"]
    base = str(Path(vmf).with_suffix(""))
    steps = []
    for tool in ("vbsp", "vvis", "vrad"):
        flags = PROFILES[profile][tool]
        if flags is None:
            continue
        cmd = [env[tool]] + flags
        if threads and tool != "vbsp":
            cmd += ["-threads", str(threads)]
        cmd += ["-game", game, base]
        steps.append({"tool": tool, "cmd": cmd})
    steps.append({"tool": "copy", "note": f"copy {base}.bsp to {env['maps_dir']} (or compile from Hammer++ which does it)"})
    return {"profile": profile, "steps": steps,
            "notes": ["Always read the vbsp log for 'leaked' before running vvis/vrad.",
                      "Do not rename the BSP after building cubemaps.",
                      "Use -hdr only if you want HDR lighting; GMod players generally run HDR when available."]}


def run(plan_: dict, timeout_s: int = 3600) -> dict:
    results = []
    for s in plan_["steps"]:
        if s["tool"] == "copy":
            continue
        p = subprocess.run(s["cmd"], capture_output=True, text=True, errors="replace", timeout=timeout_s)
        log = p.stdout + p.stderr
        results.append({"tool": s["tool"], "returncode": p.returncode, "summary": parse_log(log)})
        if p.returncode != 0 or results[-1]["summary"]["leaked"]:
            break
    return {"results": results}


def parse_log(text: str) -> dict:
    return {
        "leaked": bool(re.search(r"\*\*\* leaked \*\*\*|map leaked", text, re.I)),
        "leak_hint": (re.search(r"Entity (\S+) \(([^)]*)\) leaked", text) or [None, None, None])[0],
        "errors": re.findall(r"^.*(?:ERROR|Error:|fatal).*$", text, re.M | re.I)[:15],
        "warnings": len(re.findall(r"warning", text, re.I)),
        "overflow": re.findall(r"^.*(?:MAX_MAP_\w+|overflow|exceeded).*$", text, re.M | re.I)[:10],
        "tail": text.strip().splitlines()[-8:],
    }
