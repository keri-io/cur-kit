"""Project config: `.cursor/cur-kit.json`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = ".cursor/cur-kit.json"
DEFAULTS = {"test": "", "lint": "", "typecheck": "", "junit": "", "timeout": 300, "cache": True}
MAX_TIMEOUT = 850.0
COMMAND_KEYS = ("test", "lint", "typecheck")
PYTHON_MARKERS = ("pyproject.toml", "pytest.ini", "setup.py")
# pytest exits 5 when a project has no tests yet. That is not a failure.
PYTEST = "python3 -m pytest -q || test $? -eq 5"


@dataclass(frozen=True)
class Config:
    test: str
    lint: str
    typecheck: str
    junit: str
    timeout: float
    cache: bool


def read_object(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def pick(data: dict, key: str) -> str | float | bool:
    default = DEFAULTS[key]
    value = data.get(key, default)
    if isinstance(default, bool):
        return value if isinstance(value, bool) else default
    if isinstance(default, int):
        number = isinstance(value, (int, float)) and not isinstance(value, bool)
        return float(min(value, MAX_TIMEOUT)) if number and value > 0 else float(default)
    return value.strip() if isinstance(value, str) else default


def inside(root: Path, rel: str) -> bool:
    if not rel or Path(rel).is_absolute():
        return False
    try:
        base = root.resolve()
        target = (base / rel).resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return target != base and target.is_relative_to(base)


def load(root: Path) -> Config | None:
    data = read_object(root / CONFIG_PATH)
    if data is None:
        return None
    values = {key: pick(data, key) for key in DEFAULTS}
    if not inside(root, values["junit"]):
        values["junit"] = ""
    return Config(**values)


def commands(cfg: Config) -> dict[str, str]:
    return {key: value for key in COMMAND_KEYS if (value := getattr(cfg, key).strip())}


def detect_test(root: Path) -> str:
    if any((root / marker).is_file() for marker in PYTHON_MARKERS):
        return PYTEST
    scripts = (read_object(root / "package.json") or {}).get("scripts")
    script = scripts.get("test") if isinstance(scripts, dict) else None
    return "bun test" if isinstance(script, str) and script.strip() else ""
