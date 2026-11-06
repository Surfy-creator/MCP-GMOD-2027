"""FGD (entity definition) reader. Parsed from the user's own GMod install at runtime."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_CLASS = re.compile(r"@(PointClass|SolidClass|NPCClass|KeyFrameClass|MoveClass|FilterClass|BaseClass)"
                    r"(.*?)=\s*([A-Za-z0-9_]+)\s*(?::\s*((?:\"(?:[^\"]*)\"\s*\+?\s*)+))?\s*\[", re.S)
_KEY = re.compile(r"^\s*([A-Za-z0-9_$]+)\s*\(\s*([A-Za-z0-9_]+)\s*\)(?:\s*:\s*\"([^\"]*)\")?"
                  r"(?:\s*:\s*([^:\n]*?))?(?:\s*:\s*\"((?:[^\"]*))\")?\s*(?:=|$)", re.M)
_IO = re.compile(r"^\s*(input|output)\s+([A-Za-z0-9_]+)\s*\(\s*([A-Za-z0-9_]+)\s*\)(?:\s*:\s*\"([^\"]*)\")?", re.M)


def _strip_comments(t: str) -> str:
    return re.sub(r"//[^\n]*", "", t)


def _body(text: str, start: int) -> tuple[str, int]:
    depth, i = 1, start
    while i < len(text) and depth:
        c = text[i]
        depth += (c == "[") - (c == "]")
        i += 1
    return text[start:i - 1], i


def parse_text(text: str) -> dict[str, dict]:
    text = _strip_comments(text)
    out: dict[str, dict] = {}
    for m in _CLASS.finditer(text):
        kind, header, name, desc = m.group(1), m.group(2), m.group(3), m.group(4)
        body, _ = _body(text, m.end())
        bases = re.findall(r"base\(([^)]*)\)", header)
        parents = [b.strip() for g in bases for b in g.split(",") if b.strip()]
        keys = {}
        for k in _KEY.finditer(body):
            keys[k.group(1)] = {"type": k.group(2), "label": k.group(3) or "", "default": (k.group(4) or "").strip()}
        ios = {"inputs": {}, "outputs": {}}
        for io_ in _IO.finditer(body):
            ios["inputs" if io_.group(1) == "input" else "outputs"][io_.group(2)] = {
                "type": io_.group(3), "desc": io_.group(4) or ""}
        out[name.lower()] = {"name": name, "kind": kind, "bases": parents, "keys": keys, **ios,
                             "description": re.sub(r'"\s*\+?\s*"?', " ", desc or "").strip()[:400]}
    return out


@lru_cache(maxsize=4)
def load(paths: tuple[str, ...]) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for p in paths:
        try:
            merged.update(parse_text(Path(p).read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return merged


def resolve(db: dict[str, dict], name: str) -> dict | None:
    e = db.get(name.lower())
    if not e:
        return None
    keys, ins, outs, seen = {}, {}, {}, set()

    def walk(n: str):
        if n.lower() in seen or n.lower() not in db:
            return
        seen.add(n.lower())
        d = db[n.lower()]
        for b in d["bases"]:
            walk(b)
        keys.update(d["keys"]); ins.update(d["inputs"]); outs.update(d["outputs"])

    walk(name)
    return {"name": e["name"], "kind": e["kind"], "description": e["description"], "bases": e["bases"],
            "keys": keys, "inputs": ins, "outputs": outs}


def search(db: dict[str, dict], query: str, limit: int = 25) -> list[dict]:
    q = query.lower()
    hits = [(0 if q == k else 1 if k.startswith(q) else 2, k) for k, v in db.items()
            if v["kind"] != "BaseClass" and (q in k or q in v["description"].lower())]
    hits.sort()
    return [{"name": db[k]["name"], "kind": db[k]["kind"], "description": db[k]["description"][:140]}
            for _, k in hits[:limit]]
