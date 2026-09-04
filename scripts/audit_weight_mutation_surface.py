#!/usr/bin/env python3
"""Fail if production code writes scoring weights outside the gateway."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ALLOWED_WRITE_FILES = {
    "scripts/research/weight_mutation.py",
}
SCAN_SKIP = {
    "scripts/audit_weight_mutation_surface.py",
    "scripts/xiaomei_production_release_audit.py",
}


class WeightWriteVisitor(ast.NodeVisitor):
    def __init__(self, rel: str) -> None:
        self.rel = rel
        self.hits: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name in {"write_text", "dump", "dumps"}:
            dump = ast.dump(node)
            if "scoring_weights" in dump or "WEIGHTS_FILE" in dump:
                self.hits.append(f"{self.rel}:{getattr(node, 'lineno', 0)}:{name}")
        self.generic_visit(node)


def audit(root: Path | None = None) -> list[str]:
    base = root or ROOT
    hits: list[str] = []
    for path in (base / "scripts").rglob("*.py"):
        rel = str(path.relative_to(base)).replace("\\", "/")
        if rel in ALLOWED_WRITE_FILES or rel in SCAN_SKIP or "/__pycache__/" in rel:
            continue
        source = path.read_text(encoding="utf-8")
        if "scoring_weights.json" in source and any(token in source for token in ("write_text", "json.dump", "open(")):
            tree = ast.parse(source)
            visitor = WeightWriteVisitor(rel)
            visitor.visit(tree)
            hits.extend(visitor.hits)
            if "WEIGHTS_FILE.write_text" in source or "scoring_weights.json" in source and "write_text" in source:
                if not visitor.hits:
                    if "WEIGHTS_FILE.write_text" in source:
                        hits.append(f"{rel}:WEIGHTS_FILE.write_text")
    return sorted(set(hits))


def main() -> int:
    hits = audit()
    if hits:
        print("WEIGHT_WRITE_BYPASS")
        for item in hits:
            print(item)
        return 1
    print("WEIGHT_WRITE_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
