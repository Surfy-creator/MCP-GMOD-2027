"""Minimal Valve KeyValues (VDF/VMF) parser.

Produces a tree of ``Node`` objects. Duplicate keys and duplicate blocks are
preserved (VMF relies on both), so values are stored as ordered lists.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_TOKEN = re.compile(r'"((?:[^"\\]|\\.)*)"|([{}])|//[^\n]*|([^\s"{}]+)', re.S)


@dataclass
class Node:
    name: str
    props: list[tuple[str, str]] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)

    def get(self, key: str, default: str | None = None) -> str | None:
        k = key.lower()
        for a, b in self.props:
            if a.lower() == k:
                return b
        return default

    def all(self, key: str) -> list[str]:
        k = key.lower()
        return [b for a, b in self.props if a.lower() == k]

    def blocks(self, name: str) -> list["Node"]:
        n = name.lower()
        return [c for c in self.children if c.name.lower() == n]

    def block(self, name: str) -> "Node | None":
        b = self.blocks(name)
        return b[0] if b else None


def parse(text: str) -> list[Node]:
    """Parse text into a list of top-level blocks (a pseudo-root is not added)."""
    root = Node("<root>")
    stack = [root]
    pending: str | None = None  # a key waiting for either a value or a '{'
    for m in _TOKEN.finditer(text):
        quoted, brace, bare = m.group(1), m.group(2), m.group(3)
        if brace == "{":
            node = Node(pending if pending is not None else "")
            stack[-1].children.append(node)
            stack.append(node)
            pending = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            pending = None
        else:
            tok = quoted if quoted is not None else bare
            if tok is None:
                continue
            if pending is None:
                pending = tok
            else:
                stack[-1].props.append((pending, tok))
                pending = None
    return root.children


def parse_entity_lump(text: str) -> list[dict[str, list[str]]]:
    """Parse a BSP entity lump: ``{ "k" "v" ... }`` blocks, repeated keys kept."""
    out = []
    for blk in parse(text):
        d: dict[str, list[str]] = {}
        for k, v in blk.props:
            d.setdefault(k, []).append(v)
        out.append(d)
    return out
