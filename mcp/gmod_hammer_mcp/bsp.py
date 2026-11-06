"""Read-only Source BSP (VBSP v19/v20/v21) inspector: header, lumps, limits, entities."""
from __future__ import annotations

import struct
import zipfile
import io as _io
from pathlib import Path

from . import kv, logic

LUMP_NAMES = {
    0: "ENTITIES", 1: "PLANES", 2: "TEXDATA", 3: "VERTEXES", 4: "VISIBILITY", 5: "NODES",
    6: "TEXINFO", 7: "FACES", 8: "LIGHTING", 9: "OCCLUSION", 10: "LEAFS", 12: "EDGES",
    13: "SURFEDGES", 14: "MODELS", 15: "WORLDLIGHTS", 16: "LEAFFACES", 17: "LEAFBRUSHES",
    18: "BRUSHES", 19: "BRUSHSIDES", 20: "AREAS", 21: "AREAPORTALS", 26: "DISPINFO",
    27: "ORIGINALFACES", 29: "PHYSCOLLIDE", 33: "DISP_VERTS", 35: "GAME_LUMP", 40: "PAKFILE",
    42: "CUBEMAPS", 43: "TEXDATA_STRING_DATA", 44: "TEXDATA_STRING_TABLE", 45: "OVERLAYS",
    53: "LIGHTING_HDR", 54: "WORLDLIGHTS_HDR", 57: "XZIPPAKFILE", 58: "FACES_HDR", 59: "MAP_FLAGS",
}
# (struct size, commonly cited engine limit). Limits are from the public VDC
# "BSP" / "Source engine limits" pages; they differ slightly per branch, so
# the report labels them as reference values, not guarantees.
ELEMENTS = {
    "PLANES": (20, 65536), "FACES": (56, 65536), "BRUSHES": (12, 8192), "BRUSHSIDES": (8, 65536),
    "TEXINFO": (72, 12288), "NODES": (32, 65536), "EDGES": (4, 256000), "VERTEXES": (12, 65536),
    "MODELS": (48, 1024), "DISPINFO": (176, 2048), "CUBEMAPS": (16, 1024), "OVERLAYS": (352, 512),
    "WORLDLIGHTS": (88, 8192), "AREAPORTALS": (12, 1024), "OCCLUSION": (None, None),
}


def read_header(data: bytes) -> dict:
    if data[:4] != b"VBSP":
        raise ValueError("not a Source BSP (magic != VBSP)")
    version = struct.unpack_from("<i", data, 4)[0]
    lumps = {}
    for i in range(64):
        off, ln, ver, fcc = struct.unpack_from("<iiii", data, 8 + i * 16)
        lumps[i] = {"offset": off, "length": ln, "version": ver, "uncompressed": fcc}
    revision = struct.unpack_from("<i", data, 8 + 64 * 16)[0]
    return {"version": version, "revision": revision, "lumps": lumps}


def lump_bytes(data: bytes, lump: dict) -> bytes:
    return data[lump["offset"]: lump["offset"] + lump["length"]]


def entities(data: bytes, hdr: dict) -> list[dict]:
    raw = lump_bytes(data, hdr["lumps"][0]).split(b"\x00")[0].decode("utf-8", "replace")
    out = []
    for d in kv.parse_entity_lump(raw):
        keys, outs = {}, []
        for k, vs in d.items():
            if k.lower() in ("classname", "targetname"):
                continue
            for v in vs:
                s = logic.split_output(v) if ("," in v or "\x1b" in v) and k[:2] == "On" else None
                if s:
                    outs.append((k,) + s)
                else:
                    keys[k] = v
        out.append({"classname": (d.get("classname") or [""])[0], "targetname": (d.get("targetname") or [""])[0],
                    "keys": keys, "outputs": outs, "origin": None})
    return out


def analyze(path: str | Path) -> dict:
    p = Path(path)
    data = p.read_bytes()
    hdr = read_header(data)
    L = hdr["lumps"]
    counts = {}
    for name, (size, limit) in ELEMENTS.items():
        idx = next(i for i, n in LUMP_NAMES.items() if n == name)
        ln = L[idx]["length"]
        if size:
            n = ln // size
            counts[name] = {"count": n, "limit": limit, "pct": round(100 * n / limit, 1)}
    ents = entities(data, hdr)
    io = logic.analyze(ents)
    vis_len = L[4]["length"]
    clusters = struct.unpack_from("<i", data, L[4]["offset"])[0] if vis_len >= 4 else 0
    leafs_v = L[10]["version"]
    leaf_size = 56 if leafs_v == 0 else 32
    leafs = L[10]["length"] // leaf_size
    pak_len = L[40]["length"]
    pak_files = []
    if pak_len:
        try:
            with zipfile.ZipFile(_io.BytesIO(lump_bytes(data, L[40]))) as z:
                pak_files = [(i.filename, i.file_size) for i in z.infolist()]
        except zipfile.BadZipFile:
            pass
    pak_kinds: dict[str, int] = {}
    for f, _ in pak_files:
        ext = f.rsplit(".", 1)[-1].lower() if "." in f else "?"
        pak_kinds[ext] = pak_kinds.get(ext, 0) + 1
    hdr_lighting = L[53]["length"] > 0
    ldr_lighting = L[8]["length"] > 0
    cls = io["class_histogram"]
    ent_names = sum(1 for e in ents if e["targetname"])
    advice = []
    if clusters and leafs / clusters > 8:
        advice.append("High leaves-per-cluster ratio: many leaves share a cluster; fine, but check detail brush use.")
    if cls.get("prop_dynamic", 0) > 300:
        advice.append("Many prop_dynamic: prefer prop_static where no animation/physics is needed.")
    if not L[40]["length"]:
        advice.append("No embedded pakfile: custom content (if any) must be shipped via workshop addon.")
    if L[40]["length"] > 60 * 1024 * 1024:
        advice.append("Pakfile > 60 MB: consider moving content to a workshop addon and using bspzip -repack.")
    for name, c in counts.items():
        if c["pct"] >= 75:
            advice.append(f"{name} at {c['pct']}% of its commonly cited limit.")
    return {
        "file": str(p), "size_mb": round(len(data) / 1048576, 2), "bsp_version": hdr["version"],
        "map_revision": hdr["revision"],
        "lumps": {LUMP_NAMES.get(i, f"LUMP_{i}"): {"bytes": v["length"], "version": v["version"]}
                  for i, v in L.items() if v["length"]},
        "element_counts": counts, "visibility": {"clusters": clusters, "leafs": leafs},
        "lighting": {"ldr": ldr_lighting, "hdr": hdr_lighting},
        "lighting_bytes": L[8]["length"] + L[53]["length"],
        "entity_summary": {"total": len(ents), "named": ent_names,
                           "prop_static_in_game_lump": None},
        "pakfile": {"bytes": pak_len, "file_types": pak_kinds, "count": len(pak_files)},
        "io": io, "naming": logic.naming_convention_report(ents), "advice": advice,
        "compiled_with_hdr": hdr_lighting,
    }


def static_prop_count(path: str | Path) -> int | None:
    """Count static props from the game lump ('sprp'). Returns None if absent."""
    data = Path(path).read_bytes()
    hdr = read_header(data)
    gl = hdr["lumps"][35]
    if not gl["length"]:
        return None
    base = gl["offset"]
    n = struct.unpack_from("<i", data, base)[0]
    for i in range(n):
        gid, flags, ver, off, ln = struct.unpack_from("<iHHii", data, base + 4 + i * 16)
        if gid == 0x73707270:  # 'sprp'
            if ln == 0:
                return None
            dict_n = struct.unpack_from("<i", data, off)[0]
            p = off + 4 + dict_n * 128
            leaf_n = struct.unpack_from("<i", data, p)[0]
            p += 4 + leaf_n * 2
            return struct.unpack_from("<i", data, p)[0]
    return None
