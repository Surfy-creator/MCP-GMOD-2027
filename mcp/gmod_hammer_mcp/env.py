"""Locate Garry's Mod, Hammer, Hammer++ and the Source compilers on this machine."""
from __future__ import annotations

import os
import re
from pathlib import Path


def _steam_libraries() -> list[Path]:
    roots = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Steam",
             Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Steam",
             Path.home() / ".steam" / "steam", Path.home() / ".local/share/Steam"]
    libs = []
    for r in roots:
        if r.exists():
            libs.append(r)
            vdf = r / "steamapps" / "libraryfolders.vdf"
            if vdf.exists():
                for p in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(errors="replace")):
                    libs.append(Path(p.replace("\\\\", "\\")))
    return libs


def find_gmod() -> Path | None:
    e = os.environ.get("GMOD_PATH")
    if e and Path(e).exists():
        return Path(e)
    for lib in _steam_libraries():
        c = lib / "steamapps" / "common" / "GarrysMod"
        if c.exists():
            return c
    return None


def detect() -> dict:
    g = find_gmod()
    if not g:
        return {"gmod": None, "hint": "Set GMOD_PATH to your GarrysMod folder."}
    b = g / "bin"
    b64 = b / "win64"
    comp = b64 if (b64 / "vbsp.exe").exists() else b
    pp = b64 / "hammerplusplus"
    fgds = [p for p in (b / "garrysmod.fgd", b / "base.fgd", b / "halflife2.fgd", pp / "hammerplusplus_fgd.fgd") if p.exists()]
    exe = lambda d, n: str(d / n) if (d / n).exists() else None
    return {
        "gmod": str(g), "gamedir": str(g / "garrysmod"),
        "hammer": exe(b, "hammer.exe"), "hammerplusplus": exe(b64, "hammerplusplus.exe"),
        "hammerplusplus_compiler": exe(pp / "bin", "hammerplusplus_compiler.exe"),
        "vbsp": exe(comp, "vbsp.exe"), "vvis": exe(comp, "vvis.exe"), "vrad": exe(comp, "vrad.exe"),
        "studiomdl": exe(comp, "studiomdl.exe"), "bspzip": exe(b, "bspzip.exe"), "gmad": exe(b, "gmad.exe"),
        "fgds": [str(f) for f in fgds], "maps_dir": str(g / "garrysmod" / "maps"),
        "mapsrc_dir": str(g / "sourcesdk_content" / "garrysmod" / "mapsrc"),
        "compilers_are_64bit": comp == b64,
    }
