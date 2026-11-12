"""User-level install: the Cursor hooks and the cur-kit command."""

from __future__ import annotations

import json
import shlex
from pathlib import Path

HOOK_ENDINGS = (" hook stop", " hook stop --user", " hook session-start")


class InstallError(ValueError):
    """hooks.json exists but cannot be merged without losing the user's entries."""


def hook_entries(command: str) -> dict[str, dict]:
    program = shlex.quote(command)
    return {
        "stop": {"command": f"{program} hook stop --user", "timeout": 900, "loop_limit": 25},
        "sessionStart": {"command": f"{program} hook session-start", "timeout": 10},
    }


def is_cur_kit(item: object, command: str) -> bool:
    text = item.get("command") if isinstance(item, dict) else None
    if not isinstance(text, str):
        return False
    same = text.removesuffix(" --user") == command.removesuffix(" --user")
    return same or ("/bin/cur-kit" in text and text.endswith(HOOK_ENDINGS))


def read_hooks(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "hooks": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise InstallError(f"{path} is not valid JSON, so cur-kit cannot merge its hooks: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.setdefault("hooks", {}), dict):
        raise InstallError(f"{path} has no hooks object cur-kit can merge into")
    data.setdefault("version", 1)
    return data


def merge(hooks: dict, event: str, entry: dict) -> str:
    current = hooks.setdefault(event, [])
    if not isinstance(current, list):
        raise InstallError(f"hooks.{event} in hooks.json is not a list")
    old = [item for item in current if is_cur_kit(item, entry["command"])]
    if old == [entry]:
        return f"skip {event} hook: {entry['command']} (exists)"
    at = current.index(old[0]) if old else len(current)
    current[:] = [item for item in current if item not in old]
    current.insert(at, entry)
    if not old:
        return f"add {event} hook: {entry['command']}"
    replaced = ", ".join(item["command"] for item in old)
    return f"replace {event} hook: {replaced} -> {entry['command']}"


def install_hooks(home: Path, command: str) -> list[str]:
    path = home / ".cursor" / "hooks.json"
    data = read_hooks(path)
    log = [merge(data["hooks"], event, entry) for event, entry in hook_entries(command).items()]
    if any(not line.startswith("skip ") for line in log):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return log


def link_bin(home: Path, target: Path) -> str:
    link = home / ".local" / "bin" / "cur-kit"
    target = target.absolute()
    if link.is_symlink() and link.readlink() == target:
        return f"skip {link} (links to {target})"
    if link.exists() and not link.is_symlink():
        return f"skip {link} (exists and is not a symlink)"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.unlink(missing_ok=True)
    link.symlink_to(target)
    return f"link {link} -> {target}"
