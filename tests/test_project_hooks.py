"""Project hooks.json for Cursor Cloud: merge, wrapper, and the files committed in this repo."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from curkit.install import InstallError
from curkit.project_hooks import START_COMMAND, STOP_COMMAND, TEMPLATE, WRAPPER, hook_entries, install_project_hooks


def _place(root: Path) -> None:
    script = root / WRAPPER
    script.parent.mkdir(parents=True)
    script.write_bytes(TEMPLATE.read_bytes())


def _fake(path: Path, word: str, executable: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\nprintf '{word} %s\\n' \"$*\"\n", encoding="utf-8")
    path.chmod(0o755 if executable else 0o644)


def _run(root: Path, path: str) -> subprocess.CompletedProcess[str]:
    script = root / WRAPPER
    env = {**os.environ, "PATH": f"/usr/bin:{path}"}
    argv = ["/usr/bin/bash", str(script), "stop"]
    return subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, check=False)


def test_install_project_hooks_writes_the_cloud_hooks(tmp_path):
    log = install_project_hooks(tmp_path)
    data = json.loads((tmp_path / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
    assert data["hooks"] == {name: [entry] for name, entry in hook_entries().items()}
    assert (tmp_path / WRAPPER).read_bytes() == TEMPLATE.read_bytes()
    assert log == [f"add {WRAPPER}", f"add stop hook: {STOP_COMMAND}", f"add sessionStart hook: {START_COMMAND}"]


def test_install_project_hooks_keeps_other_entries_and_is_idempotent(tmp_path):
    path = tmp_path / ".cursor" / "hooks.json"
    path.parent.mkdir(parents=True)
    other = {"command": "./hooks/format.sh"}
    body = {"version": 1, "hooks": {"stop": [other, {"command": STOP_COMMAND, "timeout": 1}], "preToolUse": [other]}}
    path.write_text(json.dumps(body), encoding="utf-8")
    log = install_project_hooks(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["hooks"]["stop"] == [other, hook_entries()["stop"]]
    assert data["hooks"]["preToolUse"] == [other] and data["hooks"]["sessionStart"] == [hook_entries()["sessionStart"]]
    assert log[1].startswith("replace stop hook:") and log[2].startswith("add sessionStart hook:")
    before = path.read_bytes()
    assert all(line.startswith("skip ") for line in install_project_hooks(tmp_path))
    assert path.read_bytes() == before


def test_install_project_hooks_leaves_an_existing_wrapper(tmp_path):
    target = tmp_path / WRAPPER
    target.parent.mkdir(parents=True)
    target.write_text("custom\n", encoding="utf-8")
    log = install_project_hooks(tmp_path)
    assert target.read_text(encoding="utf-8") == "custom\n"
    assert f"skip {WRAPPER} (exists)" in log


def test_install_project_hooks_refuses_invalid_json(tmp_path):
    path = tmp_path / ".cursor" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(InstallError):
        install_project_hooks(tmp_path)
    assert path.read_text(encoding="utf-8") == "{broken"
    assert not (tmp_path / WRAPPER).exists()


def test_wrapper_uses_bin_then_path_then_exits_127(tmp_path):
    _place(tmp_path)
    _fake(tmp_path / "bin" / "cur-kit", "bin", executable=True)
    empty = tmp_path / "empty"
    empty.mkdir()
    first = _run(tmp_path, str(empty))
    assert (first.returncode, first.stdout) == (0, "bin hook stop\n")
    (tmp_path / "bin" / "cur-kit").chmod(0o644)
    _fake(tmp_path / "elsewhere" / "cur-kit", "path", executable=True)
    second = _run(tmp_path, str(tmp_path / "elsewhere"))
    assert (second.returncode, second.stdout) == (0, "path hook stop\n")
    third = _run(tmp_path, str(empty))
    assert third.returncode == 127 and "hook command not found" in third.stderr


def test_repo_hook_files_match_a_fresh_install(tmp_path):
    install_project_hooks(tmp_path)
    repo = Path(__file__).resolve().parents[1]
    for rel in (".cursor/hooks.json", WRAPPER):
        assert (repo / rel).read_bytes() == (tmp_path / rel).read_bytes()
