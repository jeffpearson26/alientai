from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path("alientai_v2")


def names_assigned_in_function(fn: ast.FunctionDef) -> set[str]:
    assigned = set()

    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            assigned.add(node.id)

        if isinstance(node, ast.arg):
            assigned.add(node.arg)

        if isinstance(node, ast.For):
            target = node.target
            if isinstance(target, ast.Name):
                assigned.add(target.id)

    return assigned


def find_engine_id_reads(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        print(f"SYNTAX ERROR {path}: {exc}")
        return

    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        assigned = names_assigned_in_function(fn)

        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id == "engine_id":
                safe = "YES" if "engine_id" in assigned else "NO"
                print(
                    f"{path}:{node.lineno} "
                    f"function={fn.name} "
                    f"engine_id_assigned_in_function={safe}"
                )


def main() -> None:
    for path in sorted(ROOT.rglob("*.py")):
        find_engine_id_reads(path)


if __name__ == "__main__":
    main()

