"""Read the Spec Kit files the Linear board mirrors."""

from __future__ import annotations

import re
from pathlib import Path

from curkit import speckit

LINE = re.compile(r"^\s*[-*+]\s+\[([^\]])\]\s*(T\d+)\b")
HEAD = re.compile(r"^##\s+(.+)$")


def feature(root: Path) -> Path | None:
    """The active feature folder, or the last specs directory when Spec Kit is quiet."""
    folder = speckit.feature_dir(root)
    if folder:
        return folder
    specs = root / "specs"
    names = sorted(path for path in specs.iterdir() if path.is_dir()) if specs.is_dir() else []
    return names[-1] if names else None


def text(path: Path | None) -> str:
    try:
        return path.read_text(encoding="utf-8") if path and path.is_file() else ""
    except OSError:
        return ""


def marks(body: str) -> dict[str, tuple[str, bool]]:
    """Task id to checkbox mark and whether it sits under a Convergence heading."""
    phase, found = "", {}
    for line in body.splitlines():
        head, item = HEAD.match(line), LINE.match(line)
        phase = head.group(1) if head else phase
        if item:
            found[item.group(2)] = (item.group(1), "convergence" in phase.lower())
    return found
