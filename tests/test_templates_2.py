from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import curkit

WORKFLOW = Path(curkit.__file__).parent / "templates" / "workflow.yml"
SPECIFY = shutil.which("specify")
pytestmark = pytest.mark.skipif(SPECIFY is None, reason="the specify CLI is not installed")
FAKE_AGENT = """#!/bin/sh
for arg; do case "$arg" in /*) printf '%s' "$arg" | tr '\\n' ' ' >> "$FAKE_LOG"; echo >> "$FAKE_LOG";; esac; done
"""
FAKE_CHECK = """#!/bin/sh
echo "cur-kit $*" >> "$FAKE_LOG"
if [ -f "$FAKE_LOG.green" ]; then echo '{"open": 0, "red": false}'; exit 0; fi
touch "$FAKE_LOG.green"
echo '{"open": 1, "red": true, "ids": ["US1/AC2"]}'
"""


def specify(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    base = {"PATH": os.environ["PATH"], "HOME": str(cwd), "TERM": "dumb"}
    return subprocess.run([SPECIFY, *args], cwd=cwd, env={**base, **env}, capture_output=True, text=True,
                          timeout=120, check=False)


def fake_bin(root: Path) -> Path:
    folder = root / "bin"
    folder.mkdir()
    for name, body in (("cursor-agent", FAKE_AGENT), ("cur-kit", FAKE_CHECK)):
        (folder / name).write_text(body, encoding="utf-8")
        (folder / name).chmod(0o755)
    return folder


def step_of(line: str) -> str:
    step = next(word for word in ("implement", "converge", "check") if word in line)
    return f"{step} with check output" if '"red": true' in line else step


def test_ac15_workflow_passes_specify_workflow_add_validation(tmp_path):
    (tmp_path / "project" / ".specify").mkdir(parents=True)
    done = specify(["workflow", "add", str(WORKFLOW)], tmp_path, {"SPECIFY_INIT_DIR": str(tmp_path / "project")})
    assert done.returncode == 0, done.stdout + done.stderr
    installed = tmp_path / "project" / ".specify" / "workflows" / "cur-kit-converge" / "workflow.yml"
    assert installed.read_bytes() == WORKFLOW.read_bytes()


def test_ac15_workflow_loops_until_the_check_is_green_then_pauses_at_the_gate(tmp_path):
    folder, log = fake_bin(tmp_path), tmp_path / "calls.log"
    env = {"PATH": f"{folder}{os.pathsep}{os.environ['PATH']}", "FAKE_LOG": str(log),
           "SPECKIT_INTEGRATION_CURSOR_AGENT_EXECUTABLE": str(folder / "cursor-agent")}
    init = specify(["init", "--here", "--integration", "cursor-agent", "--non-interactive", "--force"], tmp_path, env)
    assert init.returncode == 0, init.stdout + init.stderr
    done = specify(["workflow", "run", str(WORKFLOW), "--json"], tmp_path, env)
    result = json.loads(done.stdout)
    assert (result["status"], result["current_step_id"]) == ("paused", "review"), done.stderr
    steps = [step_of(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert steps == ["implement", "converge", "check", "implement with check output", "converge", "check"]
