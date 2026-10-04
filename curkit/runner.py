"""Run the project's commands at the same time, each in its own process group."""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

TAIL_LINES = 200


@dataclass(frozen=True)
class Outcome:
    name: str
    command: str
    code: int | None
    output: str
    timed_out: bool
    seconds: float


def run_all(commands: dict[str, str], cwd: Path, timeout: float) -> list[Outcome]:
    """Run every non-empty command concurrently with shell=True in cwd. Outcomes keep the input order."""
    jobs = [(name, command) for name, command in commands.items() if command.strip()]
    if not jobs:
        return []
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return list(pool.map(lambda job: _run(job, cwd, timeout), jobs))


def _run(job: tuple[str, str], cwd: Path, timeout: float) -> Outcome:
    name, command = job
    start = time.monotonic()
    # A file, not a pipe: a background child holding stdout open must not keep us waiting.
    with tempfile.TemporaryFile() as sink:
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=sink,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        code = _wait(proc, timeout)
        sink.seek(0)
        output = _tail(sink.read())
    return Outcome(name, command, code, output, code is None, round(time.monotonic() - start, 3))


def _wait(proc: subprocess.Popen[bytes], timeout: float) -> int | None:
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        proc.wait()
        return None


def _kill_group(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (AttributeError, OSError):
        proc.kill()


def _tail(raw: bytes) -> str:
    return "\n".join(raw.decode("utf-8", "replace").splitlines()[-TAIL_LINES:])
