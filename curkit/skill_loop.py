"""The stop hook's implement and converge follow-ups."""

from __future__ import annotations

import json
from pathlib import Path

SKILL = ".cursor/cur-kit/state/skill.json"
CONVERGE = "/speckit-converge"
IMPLEMENT = "/speckit-implement"
DONE = ("converged", "no further implement", "implementation is complete")
_COMMANDS = (
    ("/speckit-implement", "implement"),
    ("/speckit.implement", "implement"),
    ("/speckit-converge", "converge"),
    ("/speckit.converge", "converge"),
)


def note_prompt(root: Path, payload: dict) -> dict:
    """Remember the user prompt and allow it through."""
    record = _open(root, payload)
    value = payload.get("prompt")
    record["prompt"] = value if isinstance(value, str) else ""
    record["response"] = ""
    _write(root, record)
    return {"continue": True}


def note_response(root: Path, payload: dict) -> dict:
    """Remember the assistant's final text for the converge decision."""
    record = _open(root, payload)
    value = payload.get("text")
    record["response"] = value if isinstance(value, str) else ""
    _write(root, record)
    return {}


def after_green(root: Path, payload: dict) -> dict:
    """Submit the next skill when the suite is green, or `{}` when the loop is done."""
    record = _open(root, payload)
    kind = _kind(record.get("prompt"))
    message = ""
    if kind == "implement" or (record.get("owed") and kind != "converge"):
        record["owed"] = False
        message = CONVERGE
    elif kind == "converge" and _again(record.get("response")):
        message = IMPLEMENT
    # A follow-up often skips the prompt hook, so the next stop must see this command.
    if message:
        record["prompt"] = message
        record["response"] = ""
    _write(root, record)
    return {"followup_message": message} if message else {}


def note_red(root: Path, payload: dict) -> None:
    """Remember to run converge later when implement finished on a red suite."""
    record = _open(root, payload)
    if _kind(record.get("prompt")) == "implement":
        record["owed"] = True
    _write(root, record)


def _open(root: Path, payload: dict) -> dict:
    record = _read(root)
    chat = payload.get("conversation_id")
    if not isinstance(chat, str) or not chat:
        return record
    previous = record.get("conversation")
    # Cloud stop carries the chat id. The prompt and reply hooks often do not.
    if isinstance(previous, str) and previous and previous != chat:
        return {"conversation": chat}
    record["conversation"] = chat
    return record


def _read(root: Path) -> dict:
    try:
        data = json.loads((root / SKILL).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(root: Path, record: dict) -> None:
    path = root / SKILL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")


def _kind(prompt: object) -> str:
    """A slash command on its own line. Otherwise the first skill name in the text."""
    text = prompt.lower() if isinstance(prompt, str) else ""
    invoked = [name for name in (_line_command(line) for line in text.splitlines()) if name]
    if invoked:
        return invoked[-1]
    found = [(text.find(token), name) for token, name in _COMMANDS if token.strip("/") in text]
    return min(found)[1] if found else ""


def _line_command(line: str) -> str:
    text = line.strip()
    if len(text) >= 2 and text[0] == text[-1] == "`":
        text = text[1:-1].strip()
    for command, name in _COMMANDS:
        if text == command or text.startswith(command + " "):
            return name
    return ""


def _again(text: object) -> bool:
    body = text.lower() if isinstance(text, str) else ""
    if any(phrase in body for phrase in DONE):
        return False
    return "speckit-implement" in body or "speckit.implement" in body
