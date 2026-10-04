"""Quality gates from the project rules: file and function size limits."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

FILE_LINES, FILE_FUNCTIONS = 200, 10
FUNCTION_LINES, PARAMS, NESTING = 20, 3, 2
FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)
BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.TryStar, ast.Match)


def blocks(stmt: ast.stmt) -> list[list[ast.stmt]]:
    if isinstance(stmt, ast.If):
        rest = stmt.orelse
        if len(rest) == 1 and isinstance(rest[0], ast.If):
            return [stmt.body, *blocks(rest[0])]
        return [stmt.body, rest]
    if isinstance(stmt, (ast.Try, ast.TryStar)):
        return [stmt.body, stmt.orelse, stmt.finalbody, *[h.body for h in stmt.handlers]]
    if isinstance(stmt, ast.Match):
        return [case.body for case in stmt.cases]
    return [stmt.body, getattr(stmt, "orelse", [])]


def depth(stmts: list[ast.stmt], level: int = 0) -> int:
    best = level
    for stmt in (s for s in stmts if isinstance(s, BLOCKS)):
        best = max([best, *(depth(block, level + 1) for block in blocks(stmt))])
    return best


def param_count(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    args = func.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    extra = int(args.vararg is not None) + int(args.kwarg is not None)
    free = 1 if names and names[0] in ("self", "cls") else 0
    return len(names) + extra - free


def function_problems(func: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> list[str]:
    lines = func.end_lineno - func.lineno + 1
    found = [(lines > FUNCTION_LINES, f"{lines} lines"), (param_count(func) > PARAMS, f"{param_count(func)} params")]
    found.append((depth(func.body) > NESTING, f"nesting {depth(func.body)}"))
    return [f"{name}:{func.lineno} '{func.name}' has {msg}" for bad, msg in found if bad]


def check_source(text: str, name: str) -> list[str]:
    problems = []
    lines = len(text.splitlines())
    if lines > FILE_LINES:
        problems.append(f"{name} has {lines} lines")
    funcs = [node for node in ast.walk(ast.parse(text)) if isinstance(node, FUNCS)]
    if len(funcs) > FILE_FUNCTIONS:
        problems.append(f"{name} has {len(funcs)} functions")
    for func in funcs:
        problems.extend(function_problems(func, name))
    return problems


def main(argv: list[str]) -> int:
    paths = [p for arg in argv for p in (sorted(Path(arg).rglob("*.py")) if Path(arg).is_dir() else [Path(arg)])]
    problems = [p for path in paths for p in check_source(path.read_text(encoding="utf-8"), str(path))]
    print("\n".join(problems) if problems else f"gates ok: {len(paths)} files")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
