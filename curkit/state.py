"""Run state under .cursor/cur-kit/state/, the red latch, and failure prints."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

STATE_DIR = ".cursor/cur-kit/state"
LAST, LATCH, RUNS = "last-run.json", "latch.json", "runs.jsonl"
REPORTS_PER_FAILURE = 2
PRINT_LINES = 20


@dataclass(frozen=True)
class State:
    """State(root) reads and writes files under root/.cursor/cur-kit/state/. Reads never create the folder."""

    root: Path

    def last(self) -> dict | None:
        return self._read(LAST)

    def save_last(self, record: dict) -> None:
        self._write(LAST, json.dumps(record, indent=2) + "\n")

    def latch(self) -> dict:
        data = self._read(LATCH)
        if data is not None and isinstance(data.get("count"), int):
            return data
        return {"failure": None, "count": 0}

    def save_latch(self, latch: dict) -> None:
        self._write(LATCH, json.dumps(latch) + "\n")

    def clear_latch(self) -> None:
        Path(self.root, STATE_DIR, LATCH).unlink(missing_ok=True)

    def log(self, entry: dict) -> None:
        self._write(RUNS, json.dumps(entry) + "\n", "a")

    def _read(self, name: str) -> dict | None:
        try:
            data = json.loads(Path(self.root, STATE_DIR, name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _write(self, name: str, text: str, mode: str = "w") -> None:
        folder = Path(self.root, STATE_DIR)
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / name).open(mode, encoding="utf-8") as handle:
            handle.write(text)


def should_report(latch: dict, failure: str) -> tuple[bool, dict]:
    """Report a failure at most twice in a row. A different failure starts the count over."""
    count = latch.get("count", 0) + 1 if latch.get("failure") == failure else 1
    return count <= REPORTS_PER_FAILURE, {"failure": failure, "count": count}


def failure_print(names: list[str], output: str) -> str:
    """sha256 of the sorted failing names, else of the last 20 output lines with digits replaced."""
    if names:
        basis = "names\n" + "\n".join(sorted(set(names)))
    else:
        tail = "\n".join(output.splitlines()[-PRINT_LINES:])
        basis = "output\n" + re.sub(r"\d+", "#", tail)
    return hashlib.sha256(basis.encode("utf-8", "replace")).hexdigest()
