"""Project hooks Cursor Cloud loads from the repository."""

from __future__ import annotations

import json
from pathlib import Path

from curkit.install import merge, read_hooks

WRAPPER = ".cursor/hooks/cur-kit"
STOP_COMMAND = f"bash {WRAPPER} stop"
START_COMMAND = f"bash {WRAPPER} session-start"
BEFORE_COMMAND = f"bash {WRAPPER} before-submit"
AFTER_COMMAND = f"bash {WRAPPER} after-response"
TEMPLATE = Path(__file__).parent / "templates" / "hooks" / "cur-kit"


def hook_entries() -> dict[str, dict]:
    return {
        "stop": {"command": STOP_COMMAND, "timeout": 900, "loop_limit": 25},
        "sessionStart": {"command": START_COMMAND, "timeout": 10},
        "beforeSubmitPrompt": {"command": BEFORE_COMMAND, "timeout": 10},
        "afterAgentResponse": {"command": AFTER_COMMAND, "timeout": 10},
    }


def install_project_hooks(root: Path) -> list[str]:
    path = root / ".cursor" / "hooks.json"
    data = read_hooks(path)
    log = [merge(data["hooks"], event, entry) for event, entry in hook_entries().items()]
    if any(not line.startswith("skip ") for line in log):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return [_write_wrapper(root), *log]


def has_project_stop(root: Path) -> bool:
    """True when the project hooks file already runs a cur-kit stop command."""
    return any(_is_stop(item) for item in _stop_entries(root))


def _write_wrapper(root: Path) -> str:
    target = root / WRAPPER
    if target.exists():
        return f"skip {WRAPPER} (exists)"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(TEMPLATE.read_bytes())
    return f"add {WRAPPER}"


def _stop_entries(root: Path) -> list:
    try:
        data = json.loads((root / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    entries = hooks.get("stop") if isinstance(hooks, dict) else None
    return entries if isinstance(entries, list) else []


def _is_stop(item: object) -> bool:
    text = item.get("command") if isinstance(item, dict) else None
    if not isinstance(text, str) or "cur-kit" not in text:
        return False
    return text.endswith((" stop", "stop --user"))
