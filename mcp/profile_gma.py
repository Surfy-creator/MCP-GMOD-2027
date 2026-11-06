"""Profile BSPs found in GMA/.bin Workshop files (or plain .bsp) and save numbers-only JSON.

Usage: python profile_gma.py <out_dir> <path> [<path> ...]
Extracts BSPs into a temporary directory (deleted afterwards); only statistics are kept.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gmod_hammer_mcp import bsp, gma  # noqa: E402


def profile(path: Path, workshop_id: str = "") -> dict:
    r = bsp.analyze(path)
    io = r["io"]
    top = max(r["element_counts"].items(), key=lambda kv: kv[1]["pct"])
    return {
        "map": path.stem, "workshop_id": workshop_id,
        "source": "analysis numbers only; the BSP is not included",
        "size_mb": r["size_mb"], "bsp_version": r["bsp_version"], "visibility": r["visibility"],
        "lighting": r["lighting"], "pakfile_files": r["pakfile"]["count"],
        "pakfile_mb": round(r["pakfile"]["bytes"] / 1048576, 1), "pak_types": r["pakfile"]["file_types"],
        "entities": r["entity_summary"]["total"], "named_entities": r["entity_summary"]["named"],
        "faces": r["element_counts"]["FACES"]["count"], "limits_max_pct": top[1]["pct"], "limits_max_element": top[0],
        "static_props": bsp.static_prop_count(path), "connections": io["connections"],
        "broken_connections": io["broken_connection_count"], "naming": r["naming"],
        "logic_classes": io["logic_classes_present"], "class_histogram_top": dict(list(io["class_histogram"].items())[:30]),
        "element_counts": r["element_counts"], "advice": r["advice"],
    }


def main(out_dir: str, paths: list[str]) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for p in map(Path, paths):
        wid = p.parent.name if p.parent.name.isdigit() else ""
        with tempfile.TemporaryDirectory() as tmp:
            bsps = [p] if p.suffix.lower() == ".bsp" else gma.extract_bsps(p, tmp)
            for b in bsps:
                prof = profile(b, wid)
                (out / f"{b.stem}.json").write_text(json.dumps(prof, indent=1), encoding="utf-8")
                print(b.stem, prof["size_mb"], "MB", prof["faces"], "faces", prof["entities"], "ents")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
