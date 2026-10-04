"""`cur-kit --here`: seed a project with Spec Kit and the cur-kit files, never overwriting."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from curkit import config

TEMPLATES = Path(__file__).parent / "templates"
INIT = ["specify", "init", "--here", "--integration", "cursor-agent", "--non-interactive"]
STATE = ".cursor/cur-kit/state/"
AGENTS = ("scout", "writer", "witness", "reviewer", "diagnose")
COPIES = (
    *((f".cursor/agents/cur-kit-{name}.md", f"agents/cur-kit-{name}.md") for name in AGENTS),
    (".cursor/rules/cur-kit.mdc", "rules/cur-kit.mdc"),
    (".cursor/cur-kit/workflow.yml", "workflow.yml"),
)


class SeedError(Exception):
    """The directory cannot be seeded. The message says what to do."""


def init_argv(root: Path) -> list[str] | None:
    if (root / ".specify").is_dir():
        return None
    if shutil.which("specify") is None:
        raise SeedError("specify is not on PATH. Install Spec Kit with: uv tool install specify-cli")
    return [*INIT, "--force"] if any(root.iterdir()) else list(INIT)


def run_init(root: Path, argv: list[str], runner: Callable) -> str:
    done = runner(argv, cwd=root)
    if done.returncode != 0:
        raise SeedError(f"{' '.join(argv)} failed with exit code {done.returncode}")
    return f"run {' '.join(argv)}"


def place(root: Path, rel: str, data: bytes) -> str:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError:
        return f"skip {rel} (exists)"
    return f"add {rel}"


def ignore_state(root: Path) -> str:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    if STATE in (line.strip() for line in text.splitlines()):
        return f"skip .gitignore (lists {STATE})"
    gap = "\n" if text and not text.endswith("\n") else ""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{gap}{STATE}\n")
    return f"add {STATE} to .gitignore"


def seed(root: Path, runner: Callable = subprocess.run) -> list[str]:
    argv = init_argv(root)
    log = [run_init(root, argv, runner)] if argv else []
    settings = {**config.DEFAULTS, "test": config.detect_test(root)}
    log.append(place(root, config.CONFIG_PATH, (json.dumps(settings, indent=2) + "\n").encode()))
    log.extend(place(root, rel, (TEMPLATES / name).read_bytes()) for rel, name in COPIES)
    log.append(ignore_state(root))
    return log
