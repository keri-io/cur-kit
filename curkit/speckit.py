"""Spec Kit layout reader. The only tie to Spec Kit's internals is check-prerequisites."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_KIND = "ps" if os.name == "nt" else "sh"
TIMEOUT = 15
SCRIPTS = {
    "sh": ("bash", ".specify/scripts/bash/check-prerequisites.sh", "--json", "--paths-only"),
    "ps": ("pwsh", ".specify/scripts/powershell/check-prerequisites.ps1", "-Json", "-PathsOnly"),
    "py": (sys.executable, ".specify/scripts/python/check_prerequisites.py", "--json", "--paths-only"),
}
MISSING = object()


def read_json(path: Path) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def active(root: Path) -> bool:
    if not (root / ".specify").is_dir():
        return False
    schema = read_json(root / ".specify" / "integration.json").get("integration_state_schema", MISSING)
    return schema is MISSING or (type(schema) is int and schema == 1)


def prereq_argv(root: Path) -> list[str] | None:
    kind = read_json(root / ".specify" / "init-options.json").get("script", DEFAULT_KIND)
    if not isinstance(kind, str) or kind not in SCRIPTS:
        return None
    exe, rel, *flags = SCRIPTS[kind]
    script = root / rel
    if not script.is_file() or not exe or shutil.which(exe) is None:
        return None
    head = [exe, "-NoProfile", "-File"] if kind == "ps" else [exe]
    return [*head, str(script), *flags]


def prereq_paths(root: Path, argv: list[str]) -> dict:
    env = {**os.environ, "SPECIFY_FEATURE_NO_PERSIST": "1"}
    try:
        done = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, timeout=TIMEOUT, check=False)
        data = json.loads(done.stdout) if done.returncode == 0 else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}
    return data if isinstance(data, dict) else {}


def feature_dir(root: Path) -> Path | None:
    if not active(root):
        return None
    override = os.environ.get("SPECIFY_FEATURE_DIRECTORY", "").strip()
    if override:
        return root / override
    argv = prereq_argv(root)
    value = prereq_paths(root, argv).get("FEATURE_DIR") if argv else None
    return root / value.strip() if isinstance(value, str) and value.strip() else None


def tasks_path(root: Path) -> Path | None:
    folder = feature_dir(root)
    path = folder / "tasks.md" if folder else None
    return path if path and path.is_file() else None
