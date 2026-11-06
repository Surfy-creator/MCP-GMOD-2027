"""Read GMA addon archives (and LZMA-wrapped legacy .bin) and extract BSP files only."""
from __future__ import annotations

import lzma
import struct
from pathlib import Path


def _cstr(b: bytes, p: int) -> tuple[str, int]:
    e = b.index(b"\x00", p)
    return b[p:e].decode("utf-8", "replace"), e + 1


def open_gma(path: str | Path) -> bytes:
    data = Path(path).read_bytes()
    if data[:4] != b"GMAD":
        try:  # legacy workshop .bin is an LZMA-compressed GMA
            data = lzma.decompress(data)
        except lzma.LZMAError as e:
            raise ValueError(f"not a GMA or LZMA GMA: {e}")
    if data[:4] != b"GMAD":
        raise ValueError("not a GMA")
    return data


def list_files(data: bytes) -> list[dict]:
    p = 4 + 1 + 8 + 8  # magic, version, steamid, timestamp
    if data[4] > 1:  # required content list
        while data[p] != 0:
            _, p = _cstr(data, p)
        p += 1
    title, p = _cstr(data, p)
    _, p = _cstr(data, p)
    _, p = _cstr(data, p)
    p += 4
    files, off = [], 0
    while struct.unpack_from("<I", data, p)[0] != 0:
        p += 4
        name, p = _cstr(data, p)
        size = struct.unpack_from("<q", data, p)[0]
        p += 12
        files.append({"name": name, "size": size, "offset": off})
        off += size
    p += 4
    for f in files:
        f["offset"] += p
    return files


def extract_bsps(path: str | Path, out_dir: str | Path) -> list[Path]:
    data = open_gma(path)
    out = []
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for f in list_files(data):
        if f["name"].lower().endswith(".bsp"):
            dest = Path(out_dir) / Path(f["name"]).name  # basename only: no path traversal
            dest.write_bytes(data[f["offset"]: f["offset"] + f["size"]])
            out.append(dest)
    return out
