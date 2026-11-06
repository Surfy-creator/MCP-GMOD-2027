"""Benchmark a map against the saved reference profiles (knowledge/profiles/*.json)."""
from __future__ import annotations

import json
from pathlib import Path

PROFILES = Path(__file__).resolve().parents[2] / "knowledge" / "profiles"
METRICS = {
    "size_mb": lambda d: d["size_mb"],
    "faces": lambda d: d["faces"],
    "vis_clusters": lambda d: d["visibility"]["clusters"],
    "entities": lambda d: d["entities"],
    "static_props": lambda d: d.get("static_props"),
    "cubemaps": lambda d: d["element_counts"]["CUBEMAPS"]["count"],
    "areaportals": lambda d: d["element_counts"]["AREAPORTALS"]["count"],
    "pak_mb": lambda d: d.get("pakfile_mb"),
    "io_links": lambda d: d["connections"],
    "lights": lambda d: sum(v for k, v in d["class_histogram_top"].items() if k in ("light", "light_spot", "light_dynamic")),
    "doors": lambda d: sum(v for k, v in d["class_histogram_top"].items() if "door" in k),
}


def load_all() -> dict[str, dict]:
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(PROFILES.glob("*.json"))
            if f.stem != "SUMMARY"}


def _pct(vals: list[float], p: float) -> float:
    s = sorted(vals)
    return s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]


def summary(profiles: dict[str, dict] | None = None) -> dict:
    profiles = profiles or load_all()
    rp = {k: v for k, v in profiles.items() if k.startswith("rp_")}
    out = {"maps": len(rp), "metrics": {}}
    for name, fn in METRICS.items():
        vals = [fn(d) for d in rp.values() if fn(d) is not None]
        if vals:
            out["metrics"][name] = {"n": len(vals), "min": min(vals), "p25": _pct(vals, .25),
                                    "median": _pct(vals, .5), "p75": _pct(vals, .75), "max": max(vals)}
    return out


def rank(profile: dict) -> dict:
    rp = {k: v for k, v in load_all().items() if k.startswith("rp_")}
    res = {}
    for name, fn in METRICS.items():
        mine = fn(profile)
        vals = [fn(d) for d in rp.values() if fn(d) is not None]
        if mine is None or not vals:
            continue
        pct = round(100 * sum(v <= mine for v in vals) / len(vals))
        res[name] = {"value": mine, "percentile_vs_rp_corpus": pct, "corpus_median": _pct(vals, .5)}
    return {"corpus_size": len(rp), "metrics": res}
